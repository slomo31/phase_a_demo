"""
Phase A: Simple NBA Prediction System
- Naive rule-based predictions (no ML)
- Real betting lines integration
- Basic value identification
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================================================
# BETTING LINES - THE ACTUAL BUSINESS LOGIC
# ============================================================================

class BettingLinesAPI:
    """Fetch real betting lines from The Odds API"""
    
    def __init__(self, api_key: str):
        """
        Get free API key from: https://the-odds-api.com/
        Free tier: 500 requests/month
        """
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
    
    def get_todays_games(self) -> List[Dict]:
        """Get today's NBA games with betting lines"""
        endpoint = f"{self.base_url}/sports/basketball_nba/odds"
        
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'h2h,spreads,totals,player_points,player_rebounds,player_assists',
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching betting lines: {e}")
            return []
    
    def get_player_props(self, game_id: str = None) -> Dict:
        """Get player prop betting lines"""
        # Player props endpoint
        endpoint = f"{self.base_url}/sports/basketball_nba/events/{game_id}/odds" if game_id else None
        
        # For now, return from main odds call with player markets
        return self.get_todays_games()


# ============================================================================
# NAIVE PREDICTION RULES - Start Simple
# ============================================================================

class NaivePredictions:
    """Simple rule-based predictions using basic stats"""
    
    @staticmethod
    def predict_player_points(player_name: str, recent_games: List[float]) -> Dict:
        """
        Naive Rule: Use simple average of last 5 games
        No ML, no complexity - just basic math
        """
        if not recent_games or len(recent_games) < 3:
            return None
        
        # Simple average
        last_5 = recent_games[-5:] if len(recent_games) >= 5 else recent_games
        prediction = sum(last_5) / len(last_5)
        
        # Naive "confidence" based on consistency
        std_dev = (sum((x - prediction) ** 2 for x in last_5) / len(last_5)) ** 0.5
        confidence = max(50, 100 - (std_dev * 5))  # Lower std = higher confidence
        
        return {
            'player': player_name,
            'prediction': round(prediction, 1),
            'confidence': round(confidence, 1),
            'method': 'naive_average_last_5'
        }
    
    @staticmethod
    def predict_game_total(team1_avg: float, team2_avg: float) -> Dict:
        """
        Naive Rule: Sum of team averages
        """
        predicted_total = team1_avg + team2_avg
        
        return {
            'predicted_total': round(predicted_total, 1),
            'method': 'naive_team_averages'
        }
    
    @staticmethod
    def predict_winner(team1_avg: float, team2_avg: float) -> Dict:
        """
        Naive Rule: Team with higher average wins
        """
        margin = abs(team1_avg - team2_avg)
        
        # Simple probability based on margin
        if margin < 2:
            confidence = 55
        elif margin < 5:
            confidence = 65
        elif margin < 10:
            confidence = 75
        else:
            confidence = 85
        
        winner = 'team1' if team1_avg > team2_avg else 'team2'
        
        return {
            'predicted_winner': winner,
            'confidence': confidence,
            'predicted_margin': round(margin, 1),
            'method': 'naive_point_differential'
        }


# ============================================================================
# VALUE FINDER - Core Business Logic
# ============================================================================

class ValueFinder:
    """Find discrepancies between naive predictions and betting lines"""
    
    @staticmethod
    def compare_player_prop(prediction: float, betting_line: float, 
                           threshold: float = 3.0) -> Optional[Dict]:
        """
        Compare naive prediction to betting line
        Identify potential value bets
        """
        difference = prediction - betting_line
        
        if abs(difference) >= threshold:
            edge_type = 'OVER' if difference > 0 else 'UNDER'
            
            return {
                'has_value': True,
                'edge_type': edge_type,
                'prediction': prediction,
                'betting_line': betting_line,
                'difference': round(difference, 1),
                'recommendation': f"{edge_type} {betting_line}"
            }
        
        return {
            'has_value': False,
            'prediction': prediction,
            'betting_line': betting_line,
            'difference': round(difference, 1)
        }
    
    @staticmethod
    def compare_game_total(prediction: float, betting_line: float,
                          threshold: float = 5.0) -> Optional[Dict]:
        """Compare game total prediction to betting line"""
        difference = prediction - betting_line
        
        if abs(difference) >= threshold:
            edge_type = 'OVER' if difference > 0 else 'UNDER'
            
            return {
                'has_value': True,
                'edge_type': edge_type,
                'prediction': prediction,
                'betting_line': betting_line,
                'difference': round(difference, 1)
            }
        
        return {
            'has_value': False,
            'prediction': prediction,
            'betting_line': betting_line
        }


# ============================================================================
# MOCK DATA FOR TESTING (Replace with real data in Phase B)
# ============================================================================

class MockDataProvider:
    """Simulate player stats until we integrate real NBA API"""
    
    @staticmethod
    def get_player_recent_games(player_name: str) -> List[float]:
        """Mock recent game scores"""
        mock_data = {
            'LeBron James': [25, 28, 22, 30, 26, 24, 27],
            'Stephen Curry': [31, 28, 35, 24, 29, 33, 30],
            'Giannis Antetokounmpo': [32, 28, 34, 30, 27, 31, 29]
        }
        return mock_data.get(player_name, [20, 22, 21, 23, 20])
    
    @staticmethod
    def get_team_average(team_name: str) -> float:
        """Mock team scoring average"""
        mock_averages = {
            'Lakers': 112.5,
            'Warriors': 118.3,
            'Bucks': 115.8,
            'Celtics': 117.2
        }
        return mock_averages.get(team_name, 110.0)


# ============================================================================
# MAIN APPLICATION - Phase A Demo
# ============================================================================

def main():
    """
    Phase A Demo: Show how naive predictions compare to real betting lines
    This is the CORE business logic - everything else supports this
    """
    
    print("=" * 60)
    print("NBA PREDICTION SYSTEM - Phase A")
    print("Naive Predictions vs Real Betting Lines")
    print("=" * 60)
    
    # Initialize components
    naive = NaivePredictions()
    value_finder = ValueFinder()
    mock_data = MockDataProvider()
    
    # ========== PLAYER PROPS EXAMPLE ==========
    print("\n--- PLAYER PROPS ANALYSIS ---")
    
    player = "LeBron James"
    recent_games = mock_data.get_player_recent_games(player)
    
    # Our naive prediction
    prediction = naive.predict_player_points(player, recent_games)
    print(f"\nPlayer: {player}")
    print(f"Our Prediction: {prediction['prediction']} points")
    print(f"Confidence: {prediction['confidence']}%")
    print(f"Method: {prediction['method']}")
    
    # Compare to betting line (mock for now, will be real in Phase B)
    betting_line = 23.5  # This would come from BettingLinesAPI
    print(f"\nBetting Line: {betting_line}")
    
    # Find value
    value = value_finder.compare_player_prop(
        prediction['prediction'], 
        betting_line,
        threshold=2.0
    )
    
    print(f"\nValue Analysis:")
    print(f"Has Value: {value['has_value']}")
    if value['has_value']:
        print(f"⭐ RECOMMENDATION: {value['recommendation']}")
        print(f"Edge: {value['difference']} points")
    else:
        print("No significant edge found")
    
    # ========== GAME TOTALS EXAMPLE ==========
    print("\n\n--- GAME TOTALS ANALYSIS ---")
    
    team1 = "Lakers"
    team2 = "Warriors"
    
    team1_avg = mock_data.get_team_average(team1)
    team2_avg = mock_data.get_team_average(team2)
    
    # Our naive prediction
    total_pred = naive.predict_game_total(team1_avg, team2_avg)
    print(f"\nGame: {team1} vs {team2}")
    print(f"Our Predicted Total: {total_pred['predicted_total']}")
    print(f"Method: {total_pred['method']}")
    
    # Compare to betting line
    betting_total = 225.5  # This would come from BettingLinesAPI
    print(f"\nBetting Line Total: {betting_total}")
    
    value = value_finder.compare_game_total(
        total_pred['predicted_total'],
        betting_total,
        threshold=4.0
    )
    
    print(f"\nValue Analysis:")
    print(f"Has Value: {value['has_value']}")
    if value['has_value']:
        print(f"⭐ RECOMMENDATION: {value['edge_type']} {betting_total}")
        print(f"Edge: {value['difference']} points")
    
    # ========== WINNER PREDICTION EXAMPLE ==========
    print("\n\n--- GAME WINNER ANALYSIS ---")
    
    winner_pred = naive.predict_winner(team1_avg, team2_avg)
    print(f"Predicted Winner: {winner_pred['predicted_winner']}")
    print(f"Confidence: {winner_pred['confidence']}%")
    print(f"Expected Margin: {winner_pred['predicted_margin']} points")
    
    print("\n" + "=" * 60)
    print("Phase A Complete: Basic system working with naive rules")
    print("Next: Phase B - Integrate real NBA Stats API")
    print("=" * 60)


if __name__ == "__main__":
    main()