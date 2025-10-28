"""
Phase D: Injury Data Integration
Scrapes injury reports and adjusts predictions accordingly
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import time

class InjuryDataCollector:
    """
    Collects NBA injury data from various sources
    Adjusts predictions when key players are out
    """
    
    def __init__(self, cache_db: str = "nba_cache.db"):
        self.cache_db = cache_db
        # Team abbreviation mapping
        self.team_abbrev_map = {
            'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
            'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
            'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
            'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'LA Lakers': 'LAL', 
            'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
            'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
        }
    
    def get_injury_report(self) -> Dict[str, List[Dict]]:
        """
        Scrape current NBA injury report
        Returns: {team_abbrev: [{'player': name, 'status': status, 'injury': injury}]}
        """
        injuries_by_team = {}
        
        try:
            # ESPN Injury Report (free, no API key needed)
            url = "https://www.espn.com/nba/injuries"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            print("→ Fetching NBA injury report...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find injury tables (ESPN structure)
            injury_tables = soup.find_all('div', class_='ResponsiveTable')
            
            for table in injury_tables:
                # Get team name
                team_header = table.find_previous('div', class_='Table__Title')
                if not team_header:
                    continue
                
                team_name = team_header.get_text(strip=True)
                team_abbrev = self.team_abbrev_map.get(team_name, team_name[:3].upper())
                
                # Get injured players
                rows = table.find_all('tr')[1:]  # Skip header
                team_injuries = []
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        player_name = cols[0].get_text(strip=True)
                        injury_type = cols[1].get_text(strip=True)
                        status = cols[2].get_text(strip=True)
                        
                        team_injuries.append({
                            'player': player_name,
                            'injury': injury_type,
                            'status': status
                        })
                
                if team_injuries:
                    injuries_by_team[team_abbrev] = team_injuries
            
            print(f"✓ Found injuries for {len(injuries_by_team)} teams")
            return injuries_by_team
            
        except Exception as e:
            print(f"✗ Error fetching injury data: {e}")
            return {}
    
    def is_player_out(self, injuries_by_team: Dict, team: str, player_name: str) -> bool:
        """Check if a specific player is out"""
        team_injuries = injuries_by_team.get(team, [])
        
        for injury in team_injuries:
            if player_name.lower() in injury['player'].lower():
                status = injury['status'].lower()
                if 'out' in status or 'doubtful' in status:
                    return True
        
        return False
    
    def get_team_key_injuries(self, injuries_by_team: Dict, team: str) -> List[Dict]:
        """
        Get OUT players for a team
        Returns list of players who are OUT (not questionable/probable)
        """
        team_injuries = injuries_by_team.get(team, [])
        
        out_players = []
        for injury in team_injuries:
            status = injury['status'].lower()
            if 'out' in status:
                out_players.append(injury)
        
        return out_players
    
    def calculate_usage_boost(
        self, 
        injuries_by_team: Dict,
        player_team: str,
        opponent_team: str,
        player_name: str
    ) -> Dict[str, float]:
        """
        Calculate prediction adjustments based on injuries
        
        Returns: {
            'own_team_boost': float,  # When own teammates are out
            'opponent_boost': float    # When opponent's defenders are out
        }
        """
        adjustments = {
            'own_team_boost': 0.0,
            'opponent_boost': 0.0
        }
        
        # Check own team injuries (usage boost if stars are out)
        own_injuries = self.get_team_key_injuries(injuries_by_team, player_team)
        
        # Count significant injuries (starters/key players)
        # In a real system, you'd have a database of player importance
        # For now, simple heuristic: any OUT player = small boost
        if own_injuries:
            # Small boost per missing teammate (usage goes up)
            adjustments['own_team_boost'] = len(own_injuries) * 0.3
        
        # Check opponent injuries (easier scoring if their defense is weak)
        opp_injuries = self.get_team_key_injuries(injuries_by_team, opponent_team)
        
        if opp_injuries:
            # Small boost per missing opponent (easier to score)
            adjustments['opponent_boost'] = len(opp_injuries) * 0.2
        
        return adjustments


class SmartPredictorWithInjuries:
    """
    Enhanced predictor that includes injury adjustments
    """
    
    def __init__(self, base_predictor, injury_collector):
        self.base_predictor = base_predictor
        self.injury_collector = injury_collector
        self.injuries_by_team = {}
    
    def refresh_injury_data(self):
        """Fetch latest injury report"""
        self.injuries_by_team = self.injury_collector.get_injury_report()
    
    def predict_with_injuries(
        self,
        games: List[Dict],
        stat: str,
        player_name: str,
        player_team: str,
        opponent: Optional[str] = None,
        is_home: bool = True,
        days_rest: int = 1
    ) -> tuple:
        """
        Make prediction including injury adjustments
        
        Returns: (prediction, confidence, breakdown)
        """
        # Get base prediction with context
        base_pred, confidence, breakdown = self.base_predictor.predict_with_context(
            games, stat, opponent, is_home, days_rest
        )
        
        if base_pred is None:
            return None, None, None
        
        # Check if player themselves is injured (reduce confidence)
        if self.injury_collector.is_player_out(self.injuries_by_team, player_team, player_name):
            print(f"⚠️  {player_name} is listed as OUT - skipping prediction")
            return None, None, None
        
        # Calculate injury-based adjustments
        injury_adj = self.injury_collector.calculate_usage_boost(
            self.injuries_by_team,
            player_team,
            opponent if opponent else player_team,
            player_name
        )
        
        # Apply injury adjustments
        injury_boost = injury_adj['own_team_boost'] + injury_adj['opponent_boost']
        
        if injury_boost > 0:
            final_pred = base_pred + injury_boost
            breakdown['adjustments']['injuries'] = round(injury_boost, 2)
            breakdown['total_adjustment'] += injury_boost
            
            print(f"  💊 Injury boost for {player_name}: +{injury_boost:.1f}")
        else:
            final_pred = base_pred
            breakdown['adjustments']['injuries'] = 0
        
        return round(final_pred, 1), confidence, breakdown


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("Phase D: Injury Data Integration Demo")
    print("="*60)
    
    # Initialize
    injury_collector = InjuryDataCollector()
    
    # Fetch current injuries
    injuries = injury_collector.get_injury_report()
    
    print(f"\n📋 Current Injury Report:")
    print(f"Teams with injuries: {len(injuries)}")
    
    # Show sample injuries
    for team, team_injuries in list(injuries.items())[:3]:
        print(f"\n{team}:")
        for inj in team_injuries:
            print(f"  • {inj['player']}: {inj['status']} ({inj['injury']})")
    
    # Example usage calculation
    print("\n\n🧮 Example: Usage boost calculation")
    print("Scenario: Lakers player, 2 Lakers starters OUT, 1 opponent OUT")
    
    # Mock scenario
    test_injuries = {
        'LAL': [
            {'player': 'Anthony Davis', 'status': 'Out', 'injury': 'Ankle'},
            {'player': 'DAngelo Russell', 'status': 'Out', 'injury': 'Knee'}
        ],
        'GSW': [
            {'player': 'Draymond Green', 'status': 'Out', 'injury': 'Back'}
        ]
    }
    
    boost = injury_collector.calculate_usage_boost(
        test_injuries, 'LAL', 'GSW', 'LeBron James'
    )
    
    print(f"Own team boost: +{boost['own_team_boost']:.1f} pts")
    print(f"Opponent boost: +{boost['opponent_boost']:.1f} pts")
    print(f"Total boost: +{boost['own_team_boost'] + boost['opponent_boost']:.1f} pts")
    
    print("\n" + "="*60)
    print("Phase D Injury Integration Ready!")