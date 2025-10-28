"""
Phase B: NBA Prediction API with Real Data - DEPLOYMENT VERSION
- Integrates NBA Stats API
- Integrates The Odds API
- Stores predictions in database
- Serves static dashboard
- Production-ready for deployment
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    print("Initializing NBA Prediction API for Deployment...")
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
    title="NBA Prediction API - Production",
    version="1.0.0",
    description="Real NBA data + betting lines + smart predictions + injury data - Deployed",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# SERVE STATIC FILES (Dashboard)
# ============================================================================

# Serve the dashboard at root
@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard HTML"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "message": "NBA Prediction API is running",
        "docs": "/docs",
        "endpoints": {
            "value_bets": "/value-bets/today",
            "health": "/health",
            "games": "/games/today"
        }
    }

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

@app.get("/api/status")
async def api_status():
    """Get API status and capabilities"""
    return {
        "name": "NBA Prediction API",
        "version": "1.0.0",
        "status": "Production",
        "phase": "D - Full integration with deployment",
        "features": {
            "nba_stats": nba_api is not None,
            "betting_odds": odds_api is not None,
            "smart_predictions": SMART_PREDICTIONS_AVAILABLE,
            "injury_data": INJURY_DATA_AVAILABLE
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/search/player")
async def search_player(name: str = Query(..., min_length=2)):
    """Search for a player by name"""
    if not nba_api:
        raise HTTPException(status_code=503, detail="NBA API not initialized")
    
    player = nba_api.search_player(name)
    
    if not player:
        raise HTTPException(status_code=404, detail=f"Player '{name}' not found")
    
    return player

@app.get("/player/{player_id}/games")
async def get_player_games(player_id: int, season: str = "2024-25", limit: int = 10):
    """Get recent games for a player"""
    if not nba_api:
        raise HTTPException(status_code=503, detail="NBA API not initialized")
    
    games = nba_api.get_player_game_log(player_id, season)
    
    if not games:
        raise HTTPException(status_code=404, detail="No games found")
    
    return {
        "player_id": player_id,
        "season": season,
        "games": games[:limit],
        "total_games": len(games)
    }

@app.get("/player/{player_id}/predict/{stat_type}", response_model=PlayerPropResponse)
async def predict_player_prop(
    player_id: int, 
    stat_type: str,
    season: str = "2024-25",
    use_smart: bool = Query(True, description="Use Phase C smart predictions")
):
    """Generate prediction for a player's stat line"""
    if not nba_api:
        raise HTTPException(status_code=503, detail="NBA API not initialized")
    
    # Validate stat type
    valid_stats = ['PTS', 'REB', 'AST']
    stat_type = stat_type.upper()
    if stat_type not in valid_stats:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid stat_type. Must be one of: {', '.join(valid_stats)}"
        )
    
    # Get player info
    player_info = nba_api.get_player_info(player_id)
    if not player_info:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Get game log
    games = nba_api.get_player_game_log(player_id, season)
    if not games or len(games) < 3:
        raise HTTPException(
            status_code=400, 
            detail="Insufficient game data (need at least 3 games)"
        )
    
    # Get prediction (smart or naive)
    if use_smart and smart_predictor:
        opponent, is_home = parse_opponent_and_location(games[0].get('MATCHUP', ''))
        days_rest = calculate_days_rest(games) if len(games) >= 2 else 2
        
        prediction, confidence, breakdown = smart_predictor.predict_with_context(
            games, stat_type,
            opponent=opponent,
            is_home=is_home,
            days_rest=days_rest
        )
    else:
        prediction, confidence = calculate_naive_prediction(games, stat_type)
        breakdown = None
    
    if prediction is None:
        raise HTTPException(status_code=500, detail="Could not generate prediction")
    
    # Get betting line
    betting_line = find_betting_line(player_info['full_name'], stat_type)
    
    # Check if there's value
    has_value = False
    edge = None
    recommendation = None
    
    if betting_line:
        edge = prediction - betting_line
        has_value = abs(edge) >= 2.0
        if has_value:
            direction = "OVER" if edge > 0 else "UNDER"
            recommendation = f"Bet {direction} {betting_line}"
    
    # Get recent stat values
    recent_games = [float(g.get(stat_type, 0)) for g in games[:5]]
    
    response = PlayerPropResponse(
        player=player_info['full_name'],
        player_id=str(player_id),
        stat_type=stat_type,
        prediction=prediction,
        confidence=confidence,
        betting_line=betting_line,
        has_value=has_value,
        recommendation=recommendation,
        edge=edge,
        recent_games=recent_games
    )
    
    return response

@app.get("/games/today", response_model=List[GameResponse])
async def get_todays_games():
    """Get today's NBA games"""
    if not nba_api:
        raise HTTPException(status_code=503, detail="NBA API not initialized")
    
    games = nba_api.get_todays_games()
    
    if not games:
        return []
    
    return [
        GameResponse(
            game_id=g['game_id'],
            home_team=g['home_team'],
            away_team=g['away_team'],
            game_time=g['game_time'],
            status=g['status']
        )
        for g in games
    ]

@app.get("/value-bets/today")
async def find_value_bets(
    min_edge: float = Query(2.0, description="Minimum edge to consider"),
    show_all: bool = Query(False, description="Show all comparisons (debug)"),
    force_refresh: bool = Query(False, description="Force refresh all data"),
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
        "version": "1.0.0",
        "environment": "production" if os.getenv("RENDER") else "development",
        "nba_api": "ready" if nba_api else "not initialized",
        "odds_api": "ready" if odds_api else "not configured",
        "database": "ready" if pred_db else "not initialized",
        "smart_predictions": "enabled" if SMART_PREDICTIONS_AVAILABLE else "disabled",
        "injury_data": "enabled" if INJURY_DATA_AVAILABLE else "disabled",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print("\n" + "="*60)
    print("Starting NBA Prediction API - Production Mode")
    print("="*60)
    print("\n⚠ IMPORTANT: Set environment variables:")
    print("  export ODDS_API_KEY='your_key_here'")
    print("\nGet free API key: https://the-odds-api.com/")
    print(f"\nServer will run on: http://0.0.0.0:{port}")
    print("\nEndpoints:")
    print(f"  http://localhost:{port}/         (Dashboard)")
    print(f"  http://localhost:{port}/docs     (API Docs)")
    print(f"  http://localhost:{port}/health   (Health Check)")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)