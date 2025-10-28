"""
Phase C: Smart Prediction Engine
Adds context-aware adjustments to improve accuracy
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta

class SmartPredictor:
    """
    Improved prediction engine that considers:
    - Opponent strength
    - Home vs Away
    - Rest days
    - Recent form (trending up/down)
    - Minutes played
    """
    
    def __init__(self):
        # Defensive ratings (estimated - will improve with real data)
        # Higher = worse defense (easier to score on)
        self.team_defensive_ratings = {
            'ATL': 112, 'BOS': 108, 'BKN': 114, 'CHA': 116, 'CHI': 113,
            'CLE': 107, 'DAL': 110, 'DEN': 111, 'DET': 115, 'GSW': 112,
            'HOU': 109, 'IND': 117, 'LAC': 111, 'LAL': 113, 'MEM': 110,
            'MIA': 109, 'MIL': 112, 'MIN': 108, 'NOP': 118, 'NYK': 108,
            'OKC': 106, 'ORL': 107, 'PHI': 114, 'PHX': 113, 'POR': 119,
            'SAC': 117, 'SAS': 120, 'TOR': 115, 'UTA': 118, 'WAS': 121
        }
        
        # League average for normalization
        self.league_avg_rating = 112
    
    def predict_with_context(
        self, 
        games: List[Dict], 
        stat: str,
        opponent: Optional[str] = None,
        is_home: bool = True,
        days_rest: int = 1
    ) -> tuple:
        """
        Make context-aware prediction
        
        Returns: (prediction, confidence, breakdown)
        """
        if not games or len(games) < 3:
            return None, None, None
        
        # Step 1: Calculate base prediction from recent games
        base_pred, base_confidence = self._calculate_base(games, stat)
        
        if base_pred is None:
            return None, None, None
        
        # Step 2: Apply adjustments
        adjustments = {}
        final_pred = base_pred
        
        # Opponent adjustment
        if opponent and stat == 'PTS':
            opp_adj = self._opponent_adjustment(opponent, base_pred)
            final_pred += opp_adj
            adjustments['opponent'] = round(opp_adj, 2)
        
        # Home/Away adjustment
        home_adj = self._home_away_adjustment(games, stat, is_home)
        final_pred += home_adj
        adjustments['home_away'] = round(home_adj, 2)
        
        # Rest adjustment
        rest_adj = self._rest_adjustment(days_rest, stat)
        final_pred += rest_adj
        adjustments['rest'] = round(rest_adj, 2)
        
        # Recent form adjustment (trending up/down)
        form_adj = self._form_adjustment(games, stat)
        final_pred += form_adj
        adjustments['form'] = round(form_adj, 2)
        
        # Minutes adjustment
        minutes_adj = self._minutes_adjustment(games, base_pred)
        final_pred += minutes_adj
        adjustments['minutes'] = round(minutes_adj, 2)
        
        # Adjust confidence based on consistency and sample size
        adjusted_confidence = self._adjust_confidence(
            base_confidence, 
            len(games),
            adjustments
        )
        
        breakdown = {
            'base_prediction': round(base_pred, 1),
            'adjustments': adjustments,
            'total_adjustment': round(final_pred - base_pred, 2)
        }
        
        return round(final_pred, 1), round(adjusted_confidence, 1), breakdown
    
    def _calculate_base(self, games: List[Dict], stat: str) -> tuple:
        """Calculate base prediction (weighted recent average)"""
        # Get last 5 games, weight recent games more heavily
        recent = []
        weights = []
        
        for i, g in enumerate(games[:5]):
            try:
                val = float(g.get(stat, 0))
                recent.append(val)
                # Weight: most recent = 1.0, oldest = 0.6
                weights.append(1.0 - (i * 0.1))
            except (ValueError, TypeError):
                continue
        
        if len(recent) < 3:
            return None, None
        
        # Weighted average
        weighted_avg = sum(r * w for r, w in zip(recent, weights)) / sum(weights)
        
        # Calculate confidence
        variance = sum((x - weighted_avg) ** 2 for x in recent) / len(recent)
        std_dev = variance ** 0.5
        confidence = max(50, 100 - (std_dev * 5))
        
        return weighted_avg, confidence
    
    def _opponent_adjustment(self, opponent: str, base_pred: float) -> float:
        """
        Adjust based on opponent defensive strength
        Better defense = lower prediction
        """
        opp_rating = self.team_defensive_ratings.get(opponent, self.league_avg_rating)
        league_avg = self.league_avg_rating
        
        # If opponent allows 10 more points than average, player gets +3-5% boost
        rating_diff = opp_rating - league_avg
        
        # Scale: Every 5 points of rating diff = ~2% adjustment
        adjustment_pct = (rating_diff / 5) * 0.02
        
        return base_pred * adjustment_pct
    
    def _home_away_adjustment(self, games: List[Dict], stat: str, is_home: bool) -> float:
        """
        Adjust based on home vs away performance
        Players typically perform better at home
        """
        home_games = []
        away_games = []
        
        for g in games[:10]:
            matchup = g.get('MATCHUP', '')
            stat_val = g.get(stat)
            
            if stat_val is None:
                continue
            
            try:
                val = float(stat_val)
                if 'vs.' in matchup:  # Home game
                    home_games.append(val)
                elif '@' in matchup:  # Away game
                    away_games.append(val)
            except (ValueError, TypeError):
                continue
        
        # Calculate home vs away differential
        if home_games and away_games:
            home_avg = sum(home_games) / len(home_games)
            away_avg = sum(away_games) / len(away_games)
            diff = home_avg - away_avg
            
            # Apply the differential in the appropriate direction
            return diff * 0.5 if is_home else -diff * 0.5
        
        # Default: small home court advantage
        return 0.5 if is_home else -0.5
    
    def _rest_adjustment(self, days_rest: int, stat: str) -> float:
        """
        Adjust based on rest days
        Back-to-back games = fatigue
        """
        if days_rest == 0:  # Back-to-back (same day doubleheader - rare)
            return -2.0 if stat == 'PTS' else -0.5
        elif days_rest == 1:  # Back-to-back
            return -1.5 if stat == 'PTS' else -0.3
        elif days_rest >= 3:  # Well rested
            return 0.5 if stat == 'PTS' else 0.1
        else:  # Normal (2 days)
            return 0.0
    
    def _form_adjustment(self, games: List[Dict], stat: str) -> float:
        """
        Adjust based on recent trend (hot streak vs slump)
        Compare last 3 games to previous 3-5 games
        """
        if len(games) < 6:
            return 0.0
        
        recent_3 = []
        previous_3 = []
        
        for i, g in enumerate(games[:6]):
            try:
                val = float(g.get(stat, 0))
                if i < 3:
                    recent_3.append(val)
                else:
                    previous_3.append(val)
            except (ValueError, TypeError):
                continue
        
        if len(recent_3) < 3 or len(previous_3) < 3:
            return 0.0
        
        recent_avg = sum(recent_3) / len(recent_3)
        previous_avg = sum(previous_3) / len(previous_3)
        
        # Trending adjustment (cap at ±2 for points, ±0.5 for others)
        trend = (recent_avg - previous_avg) * 0.3
        max_adj = 2.0 if stat == 'PTS' else 0.5
        
        return max(-max_adj, min(max_adj, trend))
    
    def _minutes_adjustment(self, games: List[Dict], base_pred: float) -> float:
        """
        Adjust based on minutes played trend
        More minutes = more opportunities
        """
        recent_minutes = []
        
        for g in games[:5]:
            mins = g.get('MIN')
            if mins:
                try:
                    recent_minutes.append(float(mins))
                except (ValueError, TypeError):
                    continue
        
        if len(recent_minutes) < 3:
            return 0.0
        
        avg_minutes = sum(recent_minutes) / len(recent_minutes)
        
        # If playing < 25 min, penalize slightly
        # If playing > 35 min, boost slightly
        if avg_minutes < 25:
            return base_pred * -0.05  # -5%
        elif avg_minutes > 35:
            return base_pred * 0.03   # +3%
        
        return 0.0
    
    def _adjust_confidence(
        self, 
        base_confidence: float, 
        sample_size: int,
        adjustments: Dict[str, float]
    ) -> float:
        """
        Adjust confidence based on data quality and adjustment magnitude
        """
        confidence = base_confidence
        
        # More games = more confidence
        if sample_size >= 10:
            confidence += 5
        elif sample_size < 5:
            confidence -= 10
        
        # Large adjustments = less confidence
        total_adj = sum(abs(v) for v in adjustments.values())
        if total_adj > 3:
            confidence -= 5
        
        return max(50, min(95, confidence))


# ============================================================================
# HELPER: Parse opponent from matchup string
# ============================================================================

def parse_opponent_and_location(matchup: str) -> tuple:
    """
    Parse matchup string to get opponent and home/away
    
    Examples:
    'LAL vs. GSW' -> ('GSW', True)   # Home game
    'LAL @ BOS'   -> ('BOS', False)  # Away game
    """
    if not matchup:
        return None, True
    
    if 'vs.' in matchup:
        # Home game: "TEAM vs. OPPONENT"
        parts = matchup.split('vs.')
        if len(parts) == 2:
            opponent = parts[1].strip()
            return opponent, True
    
    elif '@' in matchup:
        # Away game: "TEAM @ OPPONENT"
        parts = matchup.split('@')
        if len(parts) == 2:
            opponent = parts[1].strip()
            return opponent, False
    
    return None, True


def calculate_days_rest(games: List[Dict]) -> int:
    """Calculate days rest since last game"""
    if len(games) < 2:
        return 2  # Default
    
    try:
        last_game_date = games[0].get('GAME_DATE')
        prev_game_date = games[1].get('GAME_DATE')
        
        if last_game_date and prev_game_date:
            last = datetime.strptime(last_game_date, '%b %d, %Y')
            prev = datetime.strptime(prev_game_date, '%b %d, %Y')
            
            days = (last - prev).days
            return max(0, days - 1)  # Subtract 1 for the game day itself
    except:
        pass
    
    return 2  # Default to normal rest


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("Phase C: Smart Predictions Demo")
    print("="*60)
    
    # Example mock data
    mock_games = [
        {'PTS': 28, 'REB': 5, 'AST': 7, 'MIN': 35, 'GAME_DATE': 'Oct 26, 2025', 'MATCHUP': 'LAL vs. GSW'},
        {'PTS': 24, 'REB': 4, 'AST': 6, 'MIN': 33, 'GAME_DATE': 'Oct 24, 2025', 'MATCHUP': 'LAL @ BOS'},
        {'PTS': 31, 'REB': 6, 'AST': 8, 'MIN': 37, 'GAME_DATE': 'Oct 22, 2025', 'MATCHUP': 'LAL vs. MIA'},
        {'PTS': 26, 'REB': 5, 'AST': 5, 'MIN': 34, 'GAME_DATE': 'Oct 20, 2025', 'MATCHUP': 'LAL @ PHX'},
        {'PTS': 22, 'REB': 4, 'AST': 9, 'MIN': 32, 'GAME_DATE': 'Oct 18, 2025', 'MATCHUP': 'LAL vs. DEN'},
    ]
    
    predictor = SmartPredictor()
    
    # Scenario 1: Home game vs weak defense, well rested
    print("\nScenario 1: Home vs WAS (weak defense), 2 days rest")
    pred, conf, breakdown = predictor.predict_with_context(
        mock_games, 'PTS', 
        opponent='WAS', 
        is_home=True, 
        days_rest=2
    )
    print(f"Prediction: {pred} pts (Confidence: {conf}%)")
    print(f"Base: {breakdown['base_prediction']}")
    print(f"Adjustments: {breakdown['adjustments']}")
    print(f"Total adjustment: {breakdown['total_adjustment']}")
    
    # Scenario 2: Away vs strong defense, back-to-back
    print("\n\nScenario 2: Away @ OKC (strong defense), back-to-back")
    pred, conf, breakdown = predictor.predict_with_context(
        mock_games, 'PTS',
        opponent='OKC',
        is_home=False,
        days_rest=1
    )
    print(f"Prediction: {pred} pts (Confidence: {conf}%)")
    print(f"Base: {breakdown['base_prediction']}")
    print(f"Adjustments: {breakdown['adjustments']}")
    print(f"Total adjustment: {breakdown['total_adjustment']}")
    
    print("\n" + "="*60)
    print("Phase C Smart Predictions Ready!")