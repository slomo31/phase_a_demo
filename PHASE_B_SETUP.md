# Phase B: Paid Odds API - Complete Guide

## 🎉 You Have the GOOD STUFF!

With a paid Odds API key, you get **the entire business model working**:

✅ Real NBA player stats  
✅ **Real player prop betting lines** (the key feature!)  
✅ Automated value bet discovery  
✅ Compare your predictions vs Vegas instantly  

## 🚀 Quick Start

### 1. Set your API key
```bash
export ODDS_API_KEY='your_paid_key_here'
```

### 2. Run the updated code
```bash
# Test data collectors
python phase_b_data_collectors.py

# Start API
python phase_b_api.py
```

### 3. Open browser
Go to: **http://localhost:8000/docs**

## 🎯 NEW Endpoints (Paid API Only)

### 1. `/odds/player-props` - See ALL available props
```bash
GET http://localhost:8000/odds/player-props
```

**Returns:**
```json
{
  "total_players": 150,
  "props": {
    "LeBron James": {
      "points": 23.5,
      "rebounds": 7.5,
      "assists": 7.5
    },
    "Stephen Curry": {
      "points": 28.5,
      "rebounds": 4.5,
      "assists": 6.5
    },
    ...
  }
}
```

### 2. `/value-bets/today` - **THE MONEY MAKER** 💰
```bash
GET http://localhost:8000/value-bets/today?min_edge=2.0
```

This endpoint:
1. Gets ALL player props from sportsbooks
2. Gets NBA stats for each player
3. Calculates predictions
4. **Finds discrepancies between prediction and betting line**
5. Returns ranked list of value bets!

**Example Response:**
```json
{
  "date": "2024-10-28",
  "total_value_bets": 12,
  "min_edge": 2.0,
  "value_bets": [
    {
      "player": "LeBron James",
      "stat_type": "points",
      "prediction": 26.8,
      "betting_line": 23.5,
      "edge": 3.3,
      "confidence": 86.4,
      "recommendation": "Bet OVER 23.5"
    },
    {
      "player": "Draymond Green",
      "stat_type": "rebounds",
      "prediction": 6.2,
      "betting_line": 8.5,
      "edge": -2.3,
      "confidence": 78.5,
      "recommendation": "Bet UNDER 8.5"
    }
  ]
}
```

### 3. Individual player predictions now have REAL betting lines

**Before (free API):**
```json
{
  "prediction": 25.8,
  "betting_line": null,  // ❌ No line
  "has_value": false
}
```

**After (paid API):**
```json
{
  "prediction": 25.8,
  "betting_line": 23.5,  // ✅ Real line!
  "has_value": true,
  "edge": 2.3,
  "recommendation": "Bet OVER 23.5"
}
```

## 💡 How to Use This

### Morning Routine (Game Days):
```bash
# 1. Check what games are today
curl http://localhost:8000/games/today

# 2. Get all value bets for today
curl http://localhost:8000/value-bets/today?min_edge=2.5

# 3. Review the recommendations
# Focus on high confidence (>80%) + big edge (>3 points)
```

### Individual Player Analysis:
```bash
# Search for player
curl "http://localhost:8000/search/player?name=LeBron"

# Get all props
curl http://localhost:8000/predict/player/2544/all

# Or specific stat
curl http://localhost:8000/predict/player/2544/PTS
```

## 📊 Real-World Example Workflow

Let's say today is game day:

**Step 1: Find value bets**
```
GET /value-bets/today?min_edge=2.0
```

Returns 15 potential value bets.

**Step 2: Filter by confidence**
Look for:
- Edge ≥ 3.0 points
- Confidence ≥ 80%
- Recent games show consistency

**Step 3: Verify manually**
```
GET /predict/player/{player_id}/PTS
```

Check the "recent_games" array - do the last 5 games support the prediction?

**Step 4: Track results**
The system automatically saves predictions to database.

Next day:
```
GET /accuracy?days=7
```

See how accurate your predictions were!

## ⚙️ Configuration Options

### Adjust minimum edge for value bets:
```bash
# More conservative (only show big edges)
GET /value-bets/today?min_edge=4.0

# More aggressive (show smaller edges)
GET /value-bets/today?min_edge=1.5
```

### API caching:
- Player props: 30 minutes
- NBA stats: 6 hours
- Player roster: 1 week

This saves your API quota!

## 📈 What You Can Build With This

### 1. **Daily Value Bet Alert System**
```python
# Every morning at 10am, run:
value_bets = get_todays_value_bets(min_edge=2.5)

# Send email/SMS with top 5 value bets
# Filter by high confidence only
```

### 2. **Telegram/Discord Bot**
```python
# Post to channel:
"🎯 TODAY'S VALUE BETS:
1. LeBron James OVER 23.5 pts (Edge: +3.3, Conf: 86%)
2. Curry UNDER 28.5 pts (Edge: -2.8, Conf: 82%)
..."
```

### 3. **Web Dashboard**
- Show all today's games
- Display value bets with color coding
- Track accuracy over time
- Compare vs Vegas success rate

### 4. **Mobile App Push Notifications**
When a high-confidence value bet appears (edge >3, confidence >85%)

## 🎓 Understanding the Data

### What is "Edge"?
```
Edge = Your Prediction - Betting Line

Positive edge = Bet OVER
Negative edge = Bet UNDER
```

### What is "Confidence"?
Based on recent performance consistency:
- 90%+ = Very consistent (low variance)
- 80-89% = Consistent
- 70-79% = Somewhat consistent
- <70% = Inconsistent (be careful!)

### What markets are available?
With paid API:
- `player_points` ✅
- `player_rebounds` ✅
- `player_assists` ✅
- `player_threes`
- `player_blocks`
- `player_steals`
- `player_turnovers`

Currently implemented: points, rebounds, assists. Easy to add more!

## 🔍 Monitoring Your API Usage

The API returns remaining requests in headers:
```
x-requests-remaining: 8543
```

Check your dashboard: https://the-odds-api.com/account/

## 🚨 Important Notes

### 1. **Line Shopping**
The API returns lines from multiple sportsbooks. In production, you'd want to:
- Show best available line
- Compare across all bookmakers
- Find the biggest edge

### 2. **Timing**
Betting lines change throughout the day. Best to:
- Check morning (lines first posted)
- Re-check 1-2 hours before game
- Lines move based on public betting

### 3. **Bankroll Management**
Even with value bets:
- Start small (1-2% of bankroll per bet)
- Track long-term results
- Need 100+ bets to evaluate system

### 4. **Current Limitations (Phase B)**
- Still using naive predictions (simple averages)
- No opponent adjustments yet
- No injury data yet
- No home/away splits yet

**Phase C will fix all of these!**

## 🎯 Success Metrics for Phase B

After 1-2 weeks of games, you should have:

✅ 50+ predictions logged  
✅ Real betting lines for all predictions  
✅ Can see which predictions were correct  
✅ Can calculate actual edge vs predicted edge  
✅ System running reliably with no errors  

## ⏭️ What's Next (Phase C)

Once Phase B is stable, Phase C adds:
- Better prediction models (opponent defense, pace, etc.)
- Injury data integration
- Home/away adjustments
- Rest days / back-to-back penalties
- Compare naive model vs improved model

The goal: **Beat Vegas consistently** (>52.4% accuracy to break even)

---

## 💰 Real Business Value

With paid API, you now have:

1. **Data Collection** ✅ (Real stats + lines)
2. **Prediction Engine** ✅ (Naive but working)
3. **Value Detection** ✅ (Compare pred vs line)
4. **Tracking System** ✅ (Database saves results)

This is a **complete MVP** for a sports betting analytics platform!

You could literally:
- Sell subscriptions to daily value bets
- Build a SaaS dashboard
- Create a betting bot
- Partner with sportsbooks

The foundation is SOLID. Now we just improve the predictions!

---

**Ready to test?** Try the `/value-bets/today` endpoint and see what it finds! 🎰