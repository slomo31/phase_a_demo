"""
Automated Data Refresh Job
Runs daily to update NBA player stats, team data, injuries, and odds
"""

import asyncio
from datetime import datetime
from phase_b_data_collectors import NBADataCollector, OddsAPICollector
from phase_d_injury_data import InjuryDataCollector

async def refresh_all_data():
    """Refresh all NBA data sources"""
    print(f"🔄 Starting data refresh at {datetime.now()}")
    
    try:
        # Initialize collectors
        nba_collector = NBADataCollector()
        odds_collector = OddsAPICollector()
        injury_collector = InjuryDataCollector()
        
        # Refresh NBA data
        print("📊 Fetching NBA stats...")
        await nba_collector.fetch_player_season_stats()
        await nba_collector.fetch_team_standings()
        
        # Refresh odds data
        print("💰 Fetching odds data...")
        await odds_collector.fetch_player_props()
        await odds_collector.fetch_game_odds()
        
        # Refresh injury data
        print("🏥 Fetching injury reports...")
        await injury_collector.fetch_injury_reports()
        
        print(f"✅ Data refresh completed successfully at {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during data refresh: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(refresh_all_data())
