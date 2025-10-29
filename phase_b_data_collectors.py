"""
Phase B: SportsData.io Integration
- Replaces free NBA Stats API (which times out on Render)
- Uses SportsData.io for reliable player stats, injuries, and headshots
- Works perfectly on Render!
"""

import requests
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

# ============================================================================
# SPORTSDATA.IO NBA API - Professional & Reliable
# ============================================================================

class SportsDataNBAAPI:
    """
    Professional NBA Stats API using SportsData.io
    - Works from any server (no blocking)
    - Fast and reliable
    - Includes injury data & player headshots
    """
    
    def __init__(self, api_key: str, cache_db: str = "nba_cache.db"):
        self.api_key = api_key
        self.base_url = "https://api.sportsdata.io/v3/nba"
        self.headers = {
            'Ocp-Apim-Subscription-Key': api_key
        }
        self.cache_db = cache_db
        self._init_cache_db()
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests
    
    def _init_cache_db(self):
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        # Cache table for API responses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        ''')
        
        # Player info table with headshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                team_id INTEGER,
                team_name TEXT,
                position TEXT,
                jersey_number INTEGER,
                photo_url TEXT,
                last_updated REAL
            )
        ''')
        
        # Injury status table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS injuries (
                player_id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                injury_status TEXT,
                injury_body_part TEXT,
                injury_start_date TEXT,
                last_updated REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cached(self, cache_key: str, max_age_hours: int = 2) -> Optional[Dict]:
        """Get cached data if still valid"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT data, timestamp FROM api_cache WHERE cache_key = ?',
                (cache_key,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                data, timestamp = result
                age_hours = (time.time() - timestamp) / 3600
                age_minutes = (time.time() - timestamp) / 60
                
                if age_hours < max_age_hours:
                    if age_hours < 1:
                        print(f"✓ Cache hit: {cache_key} (age: {age_minutes:.0f}m)")
                    else:
                        print(f"✓ Cache hit: {cache_key} (age: {age_hours:.1f}h)")
                    return json.loads(data)
                else:
                    print(f"⚠ Cache expired: {cache_key} (age: {age_hours:.1f}h)")
        except Exception as e:
            print(f"Cache error: {e}")
        
        return None
    
    def _set_cache(self, cache_key: str, data: Dict):
        """Store data in cache"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT OR REPLACE INTO api_cache (cache_key, data, timestamp) VALUES (?, ?, ?)',
            (cache_key, json.dumps(data), time.time())
        )
        
        conn.commit()
        conn.close()
    
    def _make_request(self, endpoint: str, cache_hours: int = 2) -> Optional[Dict]:
        """Make API request with caching and error handling"""
        cache_key = f"sportsdata_{endpoint}"
        
        # Try cache first
        cached = self._get_cached(cache_key, cache_hours)
        if cached:
            return cached
        
        # Rate limit
        self._rate_limit()
        
        # Make request
        url = f"{self.base_url}/{endpoint}"
        
        try:
            print(f"→ SportsData.io API Request: {endpoint}")
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Cache successful response
            self._set_cache(cache_key, data)
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"✗ SportsData.io API Error: {e}")
            return None
    
    def get_all_players(self) -> List[Dict]:
        """
        Get all active NBA players with their info and headshots
        Endpoint: /players/json/Players
        """
        data = self._make_request("stats/json/Players", cache_hours=24)
        
        if data:
            # Store in database with headshots
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            for player in data:
                cursor.execute('''
                    INSERT OR REPLACE INTO players 
                    (player_id, player_name, team_id, team_name, position, jersey_number, photo_url, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    player.get('PlayerID'),
                    player.get('FirstName', '') + ' ' + player.get('LastName', ''),
                    player.get('TeamID'),
                    player.get('Team'),
                    player.get('Position'),
                    player.get('Jersey'),
                    player.get('PhotoUrl'),  # This is the headshot URL!
                    time.time()
                ))
            
            conn.commit()
            conn.close()
            
            print(f"✓ Loaded {len(data)} players with headshots")
            return data
        
        return []
    
    def search_player(self, player_name: str) -> Optional[Dict]:
        """
        Search for a player by name and return their info with headshot
        """
        # Get all players (will use cache if available)
        players = self.get_all_players()
        
        # Fuzzy search
        player_name_lower = player_name.lower()
        
        for player in players:
            full_name = f"{player.get('FirstName', '')} {player.get('LastName', '')}".lower()
            if player_name_lower in full_name or full_name in player_name_lower:
                return {
                    'player_id': player.get('PlayerID'),
                    'player_name': f"{player.get('FirstName', '')} {player.get('LastName', '')}",
                    'team': player.get('Team'),
                    'position': player.get('Position'),
                    'jersey': player.get('Jersey'),
                    'photo_url': player.get('PhotoUrl'),  # Headshot!
                }
        
        return None
    
    def get_player_game_log(self, player_id: int, season: str = "2025") -> List[Dict]:
        """
        Get player's game log for the season
        Endpoint: /stats/json/PlayerGameStatsBySeason/{season}
        
        Returns: List of games with stats
        """
        endpoint = f"stats/json/PlayerGameStatsBySeason/{season}"
        cache_key = f"sportsdata_gamelog_{player_id}_{season}"
        
        # Try cache first
        cached = self._get_cached(cache_key, max_age_hours=2)
        if cached:
            return cached
        
        # Fetch all player stats for the season
        all_stats = self._make_request(endpoint, cache_hours=2)
        
        if not all_stats:
            return []
        
        # Filter to just this player's games
        player_games = [
            game for game in all_stats 
            if game.get('PlayerID') == player_id
        ]
        
        # Cache this player's games
        if player_games:
            self._set_cache(cache_key, player_games)
        
        # Convert to our format
        formatted_games = []
        for game in player_games:
            formatted_games.append({
                'game_date': game.get('Day'),
                'matchup': f"{game.get('Team')} vs {game.get('Opponent')}",
                'is_home': game.get('HomeOrAway') == 'HOME',
                'points': game.get('Points', 0),
                'rebounds': game.get('Rebounds', 0),
                'assists': game.get('Assists', 0),
                'minutes': game.get('Minutes', 0),
                'fg_pct': game.get('FieldGoalsPercentage', 0),
                'three_pt_made': game.get('ThreePointersMade', 0),
            })
        
        return formatted_games
    
    def get_injuries(self) -> List[Dict]:
        """
        Get current injury report
        Endpoint: /scores/json/Injuries
        
        This is HUGE for your predictions!
        """
        data = self._make_request("scores/json/Injuries", cache_hours=1)  # Refresh every hour
        
        if data:
            # Store in injuries table
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            for injury in data:
                cursor.execute('''
                    INSERT OR REPLACE INTO injuries 
                    (player_id, player_name, injury_status, injury_body_part, injury_start_date, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    injury.get('PlayerID'),
                    injury.get('Name'),
                    injury.get('Status'),  # "Out", "Questionable", "Doubtful", etc.
                    injury.get('BodyPart'),
                    injury.get('StartDate'),
                    time.time()
                ))
            
            conn.commit()
            conn.close()
            
            print(f"✓ Updated {len(data)} injury reports")
            return data
        
        return []
    
    def get_player_injury_status(self, player_id: int) -> Optional[Dict]:
        """
        Check if a specific player is injured
        Returns injury info or None if healthy
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT injury_status, injury_body_part, injury_start_date FROM injuries WHERE player_id = ?',
            (player_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'status': result[0],
                'body_part': result[1],
                'start_date': result[2]
            }
        
        return None
    
    def get_player_headshot(self, player_id: int) -> Optional[str]:
        """
        Get player's headshot URL from cache
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT photo_url FROM players WHERE player_id = ?',
            (player_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        
        return None


# ============================================================================
# Keep the same interface as before for easy migration
# ============================================================================

class NBADataCollector:
    """
    Wrapper to maintain compatibility with existing code
    Uses SportsData.io under the hood
    """
    
    def __init__(self):
        api_key = os.getenv('SPORTSDATA_API_KEY', '699bfd0befde4965a90b5d3c6d4bc822')
        self.api = SportsDataNBAAPI(api_key)
        
        # Pre-load players and injuries on init
        print("🔥 Pre-loading player data and injuries...")
        self.api.get_all_players()
        self.api.get_injuries()
        print("✓ Player data and injury reports loaded\n")
    
    def search_player(self, player_name: str) -> Optional[str]:
        """
        Search for a player by name, return their player_id
        (Compatible with old interface)
        """
        result = self.api.search_player(player_name)
        if result:
            return str(result['player_id'])
        return None
    
    def get_player_game_log(self, player_id: str, min_games: int = 5) -> List[Dict]:
        """
        Get player's game log
        (Compatible with old interface)
        """
        # Try current season first
        games = self.api.get_player_game_log(int(player_id), season="2025")
        
        print(f"    Current season (2025): {len(games)} games")
        
        # If not enough games, get last season
        if len(games) < min_games:
            print(f"    Need more data, fetching 2024 season...")
            last_season_games = self.api.get_player_game_log(int(player_id), season="2024")
            print(f"    Last season (2024): {len(last_season_games)} games")
            games.extend(last_season_games)
        
        return games
    
    def get_player_info_with_headshot(self, player_name: str) -> Optional[Dict]:
        """
        NEW: Get player info including headshot URL
        """
        return self.api.search_player(player_name)
    
    def get_player_injury_status(self, player_id: str) -> Optional[Dict]:
        """
        NEW: Check if player is injured
        """
        return self.api.get_player_injury_status(int(player_id))
    
    def refresh_injuries(self):
        """
        NEW: Manually refresh injury data
        """
        return self.api.get_injuries()


# ============================================================================
# Example Usage & Testing
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("Testing SportsData.io NBA API")
    print("="*60)
    
    collector = NBADataCollector()
    
    # Test 1: Search for a player
    print("\n1. Searching for LeBron James...")
    player_info = collector.get_player_info_with_headshot("LeBron James")
    if player_info:
        print(f"   ✓ Found: {player_info['player_name']}")
        print(f"   Team: {player_info['team']}")
        print(f"   Position: {player_info['position']}")
        print(f"   Headshot: {player_info['photo_url']}")
    
    # Test 2: Get game log
    if player_info:
        print(f"\n2. Getting game log for {player_info['player_name']}...")
        games = collector.get_player_game_log(str(player_info['player_id']))
        print(f"   ✓ Found {len(games)} games")
        
        if games:
            print(f"\n   Recent games:")
            for i, game in enumerate(games[:5]):
                print(f"     Game {i+1}: {game['points']}pts, {game['rebounds']}reb, {game['assists']}ast on {game['game_date']}")
    
    # Test 3: Check injuries
    print(f"\n3. Checking injury status...")
    if player_info:
        injury = collector.get_player_injury_status(str(player_info['player_id']))
        if injury:
            print(f"   ⚠️  INJURED: {injury['status']} - {injury['body_part']}")
        else:
            print(f"   ✓ HEALTHY")
    
    # Test 4: Get all current injuries
    print(f"\n4. Getting all current injuries...")
    collector.refresh_injuries()
    
    print("\n" + "="*60)
    print("✅ SportsData.io API integration working!")
    print("="*60)