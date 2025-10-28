"""
NBA Prediction API - Enhanced for Deployment
Serves both API endpoints and static dashboard
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

# Import your existing modules
# from phase_b_data_collectors import NBADataCollector, OddsAPICollector
# from phase_c_smart_predictions import SmartPredictor
# from phase_d_injury_data import InjuryDataCollector

app = FastAPI(
    title="NBA Prediction System API",
    description="Smart NBA betting predictions with real-time data",
    version="1.0.0"
)

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (dashboard)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "NBA Prediction API is running", "docs": "/docs"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NBA Prediction API",
        "version": "1.0.0"
    }

@app.get("/api/predictions/today")
async def get_today_predictions():
    """Get all predictions for today's games"""
    try:
        # Your existing prediction logic here
        # predictor = SmartPredictor()
        # predictions = await predictor.get_today_predictions()
        
        # Placeholder response
        return {
            "status": "success",
            "data": {
                "games": [],
                "last_updated": "2025-10-28T00:00:00Z"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/player/{player_id}/props")
async def get_player_props(player_id: int):
    """Get betting props for a specific player"""
    try:
        # Your existing odds fetching logic
        return {
            "status": "success",
            "player_id": player_id,
            "props": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/injuries")
async def get_injury_reports():
    """Get current injury reports"""
    try:
        # Your existing injury data logic
        return {
            "status": "success",
            "injuries": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/teams/{team_id}/stats")
async def get_team_stats(team_id: int):
    """Get team statistics"""
    try:
        # Your existing team stats logic
        return {
            "status": "success",
            "team_id": team_id,
            "stats": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
