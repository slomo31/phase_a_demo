"""
Phase B: NBA Prediction API with Real Data
- Integrates NBA Stats API
- Integrates The Odds API
- Stores predictions in database
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import os

# Import Phase A logic
import sys
sys.path.append('.')

# Import Phase C smart predictions
try:
    from phase_c_smart_predictions import SmartPredictor, parse_opponent_and_location, calculate_days_rest
    SMART_PREDICTIONS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Phase C smart predictions not available: {e}")
    SMART_PREDICTIONS_AVAILABLE = False
    SmartPredictor = None
    parse_opponent_and_location = None
    calculate_days_rest = None

# Import Phase D injury data
try:
    from phase_d_injury_data import InjuryDataCollector, SmartPredictorWithInjuries
    INJURY_DATA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Phase D injury data not available: {e}")
    INJURY_DATA_AVAILABLE = False
    InjuryDataCollector = None
    SmartPredictorWithInjuries = None

# Response models
class PlayerPropResponse(BaseModel):
    player: str
    player_id: str
    stat_type: str
    prediction: float
    confidence: float
    betting_line: Optional[float] = None
    has_value: bool
    recommendation: Optional[str] = None
    edge: Optional[float] = None
    recent_games: List[float]

class GameResponse(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    game_time: str
    status: str

class AccuracyResponse(BaseModel):
    total_predictions: int
    correct: int
    accuracy: float
    avg_error: float
    days_tracked: int

# ============================================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize data sources on startup"""
    global nba_api, odds_api, pred_db, smart_predictor, injury_collector, smart_predictor_with_injuries

    # Import here to avoid circular imports
    from phase_b_data_collectors import NBAStatsAPI, OddsAPI, PredictionDatabase

    print("\n" + "="*60)
    print("Initializing Phase D API...")
    print("="*60)

    # Initialize NBA Stats API
    nba_api = NBAStatsAPI()
    print("✓ NBA Stats API initialized")

    # Initialize Odds API (if key provided)
    odds_api_key = os.getenv('ODDS_API_KEY')
    if odds_api_key:
        odds_api = OddsAPI(odds_api_key)
        print("✓ Odds API initialized")
    else:
        print("⚠ ODDS_API_KEY not set - betting lines disabled")

    # Initialize database
    pred_db = PredictionDatabase()
    print("✓ Prediction database initialized")

    # Initialize smart predictor (Phase C)
    if SMART_PREDICTIONS_AVAILABLE:
        smart_predictor = SmartPredictor()
        print("✓ Smart predictor initialized (Phase C)")
    else:
        smart_predictor = None

    # Initialize injury data collector (Phase D)
    if INJURY_DATA_AVAILABLE:
        injury_collector = InjuryDataCollector()
        print("✓ Injury data collector initialized (Phase D)")

        if smart_predictor:
            smart_predictor_with_injuries = SmartPredictorWithInjuries(
                smart_predictor, injury_collector
            )
            smart_predictor_with_injuries.refresh_injury_data()
            print("✓ Smart predictor with injuries ready (Phase D)")
    else:
        injury_collector = None
        smart_predictor_with_injuries = None

    print("="*60 + "\n")

    yield  # Application runs

    print("Shutting down...")

# Initialize FastAPI
app = FastAPI(
    title="NBA Prediction API - Phase D",
    version="0.4.0",
    description="Real NBA data + betting lines + smart predictions + injury data",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# GLOBAL INSTANCES (initialized on startup)
# ============================================================================

nba_api = None
odds_api = None
pred_db = None
smart_predictor = None
injury_collector = None
smart_predictor_with_injuries = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_naive_prediction(games: List[Dict], stat: str) -> tuple:
    """Calculate naive prediction from recent games"""
    if not games or len(games) < 3:
        return None, None
    
    # Get last 5 games - make sure stat exists
    recent = []
    for g in games[:5]:
        try:
            stat_value = g.get(stat)
            if stat_value is not None:
                recent.append(float(stat_value))
        except (ValueError, TypeError):
            continue
    
    if len(recent) < 3:
        return None, None
    
    avg = sum(recent) / len(recent)
    
    # Calculate confidence based on consistency
    variance = sum((x - avg) ** 2 for x in recent) / len(recent)
    std_dev = variance ** 0.5
    confidence = max(50, 100 - (std_dev * 5))
    
    return round(avg, 1), round(confidence, 1)

def find_betting_line(player_name: str, stat_type: str) -> Optional[float]:
    """Find betting line for player prop from cached odds data"""
    if not odds_api:
        return None
    
    # Map stat types
    stat_map = {
        'PTS': 'points',
        'REB': 'rebounds',
        'AST': 'assists'
    }
    
    market_name = stat_map.get(stat_type)
    if not market_name:
        return None
    
    try:
        # Get player props from cache or API
        all_props = odds_api.get_all_player_props_for_today()
        
        # Find matching player (fuzzy match)
        player_name_lower = player_name.lower()
        for prop_player_name, props in all_props.items():
            if player_name_lower in prop_player_name.lower():
                line = props.get(market_name)
                if line:
                    print(f"✓ Found betting line for {player_name} {stat_type}: {line}")
                    return float(line)
        
        print(f"✗ No betting line found for {player_name} {stat_type}")
        return None
        
    except Exception as e:
        print(f"✗ Error fetching betting line: {e}")
        return None

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "name": "NBA Prediction API - Phase B",
        "version": "0.2.0",
        "status": "Real data integration",
        "features": [
            "✓ Real NBA player stats",
            "✓ Real game schedules",
            "✓ Real betting lines (game totals)",
            "✓ Real player prop lines (PAID API)",
            "✓ Prediction tracking"
        ],
        "endpoints": {
            "search": "/search/player?name=LeBron",
            "player_props": "/predict/player/{player_id}/{stat_type}",
            "today_games": "/games/today",
            "accuracy": "/accuracy?days=7"
        }
    }

@app.get("/search/player")
async def search_player(name: str = Query(..., description="Player name to search")):
    """Search for a player by name"""
    if not nba_api:
        raise HTTPException(status_code=503, detail="NBA API not initialized")
    
    result = nba_api.search_player(name)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Player '{name}' not found")
    
    return result

@app.get("/predict/player/{player_id}/{stat_type}", response_model=PlayerPropResponse)
async def predict_player_prop(
    player_id: str,
    stat_type: str
):
    """
    Predict player prop using real game data
    
    stat_type: PTS (points), REB (rebounds), AST (assists)
    """
    # Validate stat_type
    if stat_type not in ['PTS', 'REB', 'AST']:
        raise HTTPException(status_code=400, detail="stat_type must be PTS, REB, or AST")
    
    if not nba_api:
        raise HTTPException(status_code=503, detail="NBA API not initialized")
    
    # Get player game log
    games = nba_api.get_player_game_log(player_id)
    
    if not games:
        raise HTTPException(status_code=404, detail="No game data found for player")
    
    player_name = games[0].get('PLAYER_NAME', f'Player {player_id}')
    
    # Calculate prediction
    prediction, confidence = calculate_naive_prediction(games, stat_type)
    
    if prediction is None:
        raise HTTPException(status_code=500, detail="Insufficient data for prediction")
    
    # Get recent values for context
    recent_values = [float(g[stat_type]) for g in games[:5] if g.get(stat_type)]
    
    # Try to get betting line (will be None in Phase B free tier)
    betting_line = find_betting_line(player_name, stat_type)
    
    # Determine value
    has_value = False
    recommendation = None
    edge = None
    
    if betting_line:
        edge = round(prediction - betting_line, 1)
        if abs(edge) >= 2.0:
            has_value = True
            recommendation = f"Bet {'OVER' if edge > 0 else 'UNDER'} {betting_line}"
    
    # Save prediction
    if pred_db and betting_line:
        pred_db.save_prediction({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'player_id': player_id,
            'player_name': player_name,
            'stat_type': stat_type,
            'predicted_value': prediction,
            'confidence': confidence,
            'betting_line': betting_line
        })
    
    return PlayerPropResponse(
        player=player_name,
        player_id=player_id,
        stat_type=stat_type,
        prediction=prediction,
        confidence=confidence,
        betting_line=betting_line,
        has_value=has_value,
        recommendation=recommendation,
        edge=edge,
        recent_games=recent_values
    )

@app.get("/predict/player/{player_id}/all")
async def predict_all_props(player_id: str):
    """Get predictions for all stat types (points, rebounds, assists)"""
    results = {}
    
    for stat in ['PTS', 'REB', 'AST']:
        try:
            result = await predict_player_prop(player_id, stat)
            results[stat.lower()] = result.dict()
        except HTTPException:
            results[stat.lower()] = {"error": "Unable to predict"}
    
    return {
        "player_id": player_id,
        "predictions": results,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/games/today", response_model=List[GameResponse])
async def get_todays_games():
    """Get today's NBA games"""
    if not nba_api:
        raise HTTPException(status_code=503, detail="NBA API not initialized")
    
    games = nba_api.get_todays_games()
    
    if not games:
        return []
    
    game_list = []
    for game in games:
        game_list.append(GameResponse(
            game_id=game.get('GAME_ID', ''),
            home_team=game.get('HOME_TEAM_NAME', 'TBD'),
            away_team=game.get('VISITOR_TEAM_NAME', 'TBD'),
            game_time=game.get('GAME_STATUS_TEXT', 'TBD'),
            status=game.get('GAME_STATUS_TEXT', 'Scheduled')
        ))
    
    return game_list

@app.get("/odds/player-props")
async def get_player_props_lines():
    """
    Get all available player prop betting lines for today
    Shows which players have lines available
    """
    if not odds_api:
        return {
            "error": "Odds API not configured",
            "message": "Set ODDS_API_KEY environment variable"
        }
    
    try:
        all_props = odds_api.get_all_player_props_for_today()
        
        if not all_props:
            return {
                "message": "No player props available",
                "note": "Check if there are games today"
            }
        
        return {
            "total_players": len(all_props),
            "props": all_props,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching props: {str(e)}")

@app.get("/value-bets/today")
async def get_todays_value_bets(
    min_edge: float = Query(2.0, ge=0.5, le=10.0),
    show_all: bool = Query(False, description="Show all comparisons, not just value bets"),
    force_refresh: bool = Query(False, description="Force refresh all data (ignore cache)"),
    use_smart: bool = Query(True, description="Use Phase C smart predictions (vs naive)")
):
    """
    Find all value bets for today
    Compares predictions vs betting lines for all available props
    
    min_edge: Minimum edge in points to consider a value bet (default 2.0)
    show_all: If true, shows all predictions even without value (for debugging)
    force_refresh: If true, clears cache and fetches fresh data
    """
    if force_refresh:
        print("🔄 FORCE REFRESH: Clearing all caches...")
        import os
        try:
            if os.path.exists('nba_cache.db'):
                os.remove('nba_cache.db')
                print("  ✓ Deleted nba_cache.db")
        except Exception as e:
            print(f"  ⚠ Could not delete cache: {e}")
    global smart_predictor, smart_predictor_with_injuries, injury_collector
    if not odds_api or not nba_api:
        raise HTTPException(status_code=503, detail="APIs not initialized")
    
    try:
        # Get all player props
        all_props = odds_api.get_all_player_props_for_today()
        
        if not all_props:
            return {
                "message": "No props available today",
                "value_bets": []
            }
        
        value_bets = []
        all_comparisons = []  # For debugging
        players_processed = 0
        players_with_data = 0
        
        # Check each player
        for player_name, props in all_props.items():
            players_processed += 1
            
            # Search for player
            player_info = nba_api.search_player(player_name)
            
            if not player_info:
                print(f"  ⚠ Could not find NBA data for: {player_name}")
                continue
            
            player_id = player_info['player_id']
            
            # Get game log
            games = nba_api.get_player_game_log(player_id)
            
            if not games or len(games) < 3:
                print(f"  ⚠ Insufficient games for: {player_name} ({len(games) if games else 0} games)")
                continue
            
            players_with_data += 1
            
            # Debug: Show sample of recent games for first few players
            if players_with_data <= 3:
                print(f"  ℹ️  {player_name} recent games:")
                for i, g in enumerate(games[:5]):
                    game_date = g.get('GAME_DATE', 'Unknown')
                    # Determine if current or last season
                    season_label = "🆕" if "2025" in game_date or "Oct" in game_date or "Nov" in game_date else "📅"
                    print(f"     {season_label} Game {i+1}: {g.get('PTS')}pts, {g.get('REB')}reb, {g.get('AST')}ast on {game_date}")
            
            # Check each stat type
            for stat_type, betting_line in props.items():
                if not betting_line:
                    continue
                
                stat_code = {'points': 'PTS', 'rebounds': 'REB', 'assists': 'AST'}.get(stat_type)
                
                if not stat_code:
                    continue
                
                # Get context for smart prediction
                opponent, is_home = parse_opponent_and_location(games[0].get('MATCHUP', '')) if games else (None, True)
                days_rest = calculate_days_rest(games) if len(games) >= 2 else 2
                
                # Calculate prediction (smart or naive)
                if use_smart and smart_predictor:
                    prediction, confidence, breakdown = smart_predictor.predict_with_context(
                        games, stat_code,
                        opponent=opponent,
                        is_home=is_home,
                        days_rest=days_rest
                    )
                else:
                    prediction, confidence = calculate_naive_prediction(games, stat_code)
                    breakdown = None
                
                if prediction is None:
                    continue
                
                # Calculate edge
                edge = prediction - betting_line
                
                comparison = {
                    'player': player_name,
                    'stat_type': stat_type,
                    'prediction': prediction,
                    'betting_line': betting_line,
                    'edge': round(edge, 1),
                    'confidence': confidence,
                    'game': props.get('game', 'Unknown'),
                    'method': 'smart' if use_smart else 'naive'
                }
                
                # Add breakdown if using smart predictions
                if breakdown:
                    comparison['breakdown'] = breakdown
                
                all_comparisons.append(comparison)
                
                # Is it a value bet?
                if abs(edge) >= min_edge:
                    comparison['recommendation'] = f"Bet {'OVER' if edge > 0 else 'UNDER'} {betting_line}"
                    value_bets.append(comparison)
                    print(f"  🎯 VALUE: {player_name} {stat_type} - Pred: {prediction}, Line: {betting_line}, Edge: {edge:+.1f}")
        
        # Sort by absolute edge (biggest edges first)
        value_bets.sort(key=lambda x: abs(x['edge']), reverse=True)
        all_comparisons.sort(key=lambda x: abs(x['edge']), reverse=True)
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total players with props: {players_processed}")
        print(f"  Players with NBA data: {players_with_data}")
        print(f"  Total comparisons: {len(all_comparisons)}")
        print(f"  Value bets found (edge ≥{min_edge}): {len(value_bets)}")
        
        if not value_bets and all_comparisons:
            print(f"\n💡 Top 5 closest (adjust min_edge lower to see these):")
            for comp in all_comparisons[:5]:
                print(f"  {comp['player']} {comp['stat_type']}: Edge {comp['edge']:+.1f}")
        
        response = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "total_value_bets": len(value_bets),
            "min_edge": min_edge,
            "value_bets": value_bets,
            "timestamp": datetime.now().isoformat()
        }
        
        if show_all:
            response['all_comparisons'] = all_comparisons[:50]  # Limit to 50 for readability
            response['stats'] = {
                'players_processed': players_processed,
                'players_with_data': players_with_data,
                'total_comparisons': len(all_comparisons)
            }
        
        return response
        
    except Exception as e:
        import traceback
        print(f"✗ Error finding value bets: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error finding value bets: {str(e)}")

@app.get("/odds/games")
async def get_game_odds():
    """Get current betting odds for NBA games"""
    if not odds_api:
        return {
            "error": "Odds API not configured",
            "message": "Set ODDS_API_KEY environment variable",
            "get_key": "https://the-odds-api.com/"
        }
    
    odds = odds_api.get_nba_odds()
    
    if not odds:
        return {
            "message": "No odds available",
            "note": "Might be off-season or no games scheduled"
        }
    
    return {
        "games": odds,
        "count": len(odds),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/accuracy", response_model=AccuracyResponse)
async def get_accuracy_stats(days: int = Query(7, ge=1, le=30)):
    """Get prediction accuracy statistics"""
    if not pred_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    stats = pred_db.get_accuracy_stats(days)
    stats['days_tracked'] = days
    
    return AccuracyResponse(**stats)

@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "phase": "B - Real data integration",
        "nba_api": "ready" if nba_api else "not initialized",
        "odds_api": "ready" if odds_api else "not configured",
        "database": "ready" if pred_db else "not initialized",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("Starting NBA Prediction API - Phase B")
    print("="*60)
    print("\n⚠ IMPORTANT: Set environment variable before running:")
    print("  export ODDS_API_KEY='your_key_here'")
    print("\nGet free API key: https://the-odds-api.com/")
    print("\nEndpoints:")
    print("  http://localhost:8000/docs")
    print("  http://localhost:8000/search/player?name=LeBron")
    print("  http://localhost:8000/games/today")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)