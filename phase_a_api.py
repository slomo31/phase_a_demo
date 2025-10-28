"""
Phase A: Simple REST API
- Returns naive predictions vs betting lines
- No over-engineering
- Focuses on core business value
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

app = FastAPI(title="NBA Prediction API - Phase A", version="0.1.0")

# Enable CORS for web/mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class PlayerPropResponse(BaseModel):
    player: str
    stat_type: str  # 'points', 'rebounds', 'assists'
    prediction: float
    confidence: float
    betting_line: float
    has_value: bool
    recommendation: Optional[str] = None
    edge: float

class GameTotalResponse(BaseModel):
    home_team: str
    away_team: str
    predicted_total: float
    betting_line_total: float
    has_value: bool
    recommendation: Optional[str] = None
    edge: float

class TodaysGamesResponse(BaseModel):
    games: List[Dict]
    last_updated: str

# ============================================================================
# MOCK DATA STORE (Replace with database in Phase B)
# ============================================================================

# Mock player stats - in Phase B this comes from NBA Stats API
MOCK_PLAYER_DATA = {
    'lebron-james': {
        'name': 'LeBron James',
        'recent_points': [25, 28, 22, 30, 26, 24, 27],
        'recent_rebounds': [7, 8, 6, 9, 7, 8, 7],
        'recent_assists': [8, 7, 9, 6, 8, 7, 8]
    },
    'stephen-curry': {
        'name': 'Stephen Curry',
        'recent_points': [31, 28, 35, 24, 29, 33, 30],
        'recent_rebounds': [5, 4, 6, 5, 5, 4, 5],
        'recent_assists': [6, 7, 5, 8, 6, 7, 6]
    }
}

# Mock betting lines - in Phase B this comes from The Odds API
MOCK_BETTING_LINES = {
    'lebron-james': {
        'points': 23.5,
        'rebounds': 7.5,
        'assists': 7.5
    },
    'stephen-curry': {
        'points': 28.5,
        'rebounds': 4.5,
        'assists': 6.5
    }
}

MOCK_TODAYS_GAMES = [
    {
        'game_id': 'lal-gsw-2025-10-25',
        'home_team': 'Lakers',
        'away_team': 'Warriors',
        'time': '19:30',
        'betting_total': 225.5,
        'home_avg': 112.5,
        'away_avg': 118.3
    },
    {
        'game_id': 'mil-bos-2025-10-25',
        'home_team': 'Bucks',
        'away_team': 'Celtics',
        'time': '20:00',
        'betting_total': 233.0,
        'home_avg': 115.8,
        'away_avg': 117.2
    }
]

# ============================================================================
# HELPER FUNCTIONS - Naive Prediction Logic
# ============================================================================

def calculate_naive_average(recent_games: List[float]) -> tuple:
    """Calculate simple average and confidence"""
    if not recent_games or len(recent_games) < 3:
        return None, None
    
    last_5 = recent_games[-5:] if len(recent_games) >= 5 else recent_games
    avg = sum(last_5) / len(last_5)
    
    # Calculate standard deviation for confidence
    variance = sum((x - avg) ** 2 for x in last_5) / len(last_5)
    std_dev = variance ** 0.5
    confidence = max(50, 100 - (std_dev * 5))
    
    return round(avg, 1), round(confidence, 1)

def find_value(prediction: float, betting_line: float, threshold: float = 2.0) -> Dict:
    """Determine if there's betting value"""
    difference = prediction - betting_line
    
    if abs(difference) >= threshold:
        edge_type = 'OVER' if difference > 0 else 'UNDER'
        return {
            'has_value': True,
            'recommendation': f"Bet {edge_type} {betting_line}",
            'edge': round(difference, 1)
        }
    
    return {
        'has_value': False,
        'recommendation': None,
        'edge': round(difference, 1)
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "NBA Prediction API - Phase A",
        "version": "0.1.0",
        "status": "Naive predictions only",
        "endpoints": {
            "today's games": "/games/today",
            "player props": "/predict/player/{player_slug}/{stat_type}",
            "all player props": "/predict/player/{player_slug}/all"
        },
        "note": "Phase A uses naive averaging. Phase B will add real data sources."
    }

@app.get("/games/today", response_model=TodaysGamesResponse)
async def get_todays_games():
    """Get today's NBA games with betting lines"""
    return TodaysGamesResponse(
        games=MOCK_TODAYS_GAMES,
        last_updated=datetime.now().isoformat()
    )

@app.get("/predict/player/{player_slug}/{stat_type}", response_model=PlayerPropResponse)
async def predict_player_prop(player_slug: str, stat_type: str):
    """
    Predict single player prop and compare to betting line
    
    player_slug examples: 'lebron-james', 'stephen-curry'
    stat_type: 'points', 'rebounds', 'assists'
    """
    
    # Validate inputs
    if player_slug not in MOCK_PLAYER_DATA:
        raise HTTPException(status_code=404, detail=f"Player '{player_slug}' not found")
    
    if stat_type not in ['points', 'rebounds', 'assists']:
        raise HTTPException(status_code=400, detail="stat_type must be: points, rebounds, or assists")
    
    # Get player data
    player = MOCK_PLAYER_DATA[player_slug]
    recent_games = player[f'recent_{stat_type}']
    
    # Calculate naive prediction
    prediction, confidence = calculate_naive_average(recent_games)
    
    if prediction is None:
        raise HTTPException(status_code=500, detail="Insufficient data for prediction")
    
    # Get betting line
    betting_line = MOCK_BETTING_LINES[player_slug][stat_type]
    
    # Find value
    value_analysis = find_value(prediction, betting_line, threshold=2.0)
    
    return PlayerPropResponse(
        player=player['name'],
        stat_type=stat_type,
        prediction=prediction,
        confidence=confidence,
        betting_line=betting_line,
        has_value=value_analysis['has_value'],
        recommendation=value_analysis['recommendation'],
        edge=value_analysis['edge']
    )

@app.get("/predict/player/{player_slug}/all")
async def predict_all_player_props(player_slug: str):
    """Get all prop predictions for a player"""
    
    if player_slug not in MOCK_PLAYER_DATA:
        raise HTTPException(status_code=404, detail=f"Player '{player_slug}' not found")
    
    results = {}
    
    for stat_type in ['points', 'rebounds', 'assists']:
        player = MOCK_PLAYER_DATA[player_slug]
        recent_games = player[f'recent_{stat_type}']
        
        prediction, confidence = calculate_naive_average(recent_games)
        betting_line = MOCK_BETTING_LINES[player_slug][stat_type]
        value_analysis = find_value(prediction, betting_line, threshold=2.0)
        
        results[stat_type] = {
            'prediction': prediction,
            'confidence': confidence,
            'betting_line': betting_line,
            'has_value': value_analysis['has_value'],
            'recommendation': value_analysis['recommendation'],
            'edge': value_analysis['edge']
        }
    
    return {
        'player': player['name'],
        'props': results,
        'timestamp': datetime.now().isoformat()
    }

@app.get("/predict/game/{game_id}", response_model=GameTotalResponse)
async def predict_game_total(game_id: str):
    """Predict game total and compare to betting line"""
    
    # Find game
    game = next((g for g in MOCK_TODAYS_GAMES if g['game_id'] == game_id), None)
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Naive prediction: sum of team averages
    predicted_total = game['home_avg'] + game['away_avg']
    betting_line = game['betting_total']
    
    # Find value
    value_analysis = find_value(predicted_total, betting_line, threshold=4.0)
    
    return GameTotalResponse(
        home_team=game['home_team'],
        away_team=game['away_team'],
        predicted_total=round(predicted_total, 1),
        betting_line_total=betting_line,
        has_value=value_analysis['has_value'],
        recommendation=value_analysis['recommendation'],
        edge=value_analysis['edge']
    )

@app.get("/health")
async def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "phase": "A - Naive predictions",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("Starting NBA Prediction API - Phase A")
    print("="*60)
    print("\nEndpoints:")
    print("  http://localhost:8000/docs  (Interactive API docs)")
    print("  http://localhost:8000/games/today")
    print("  http://localhost:8000/predict/player/lebron-james/points")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)