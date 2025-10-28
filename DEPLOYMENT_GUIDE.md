# 🚀 NBA Prediction System - Deployment Guide

## Overview
This guide will help you deploy your NBA prediction system so it runs 24/7 automatically without needing to manually start it each day.

---

## 📋 Prerequisites

1. Your code pushed to GitHub
2. API keys (NBA API, Odds API)
3. Free Render.com account (or Railway, Heroku alternatives)

---

## 🎯 Deployment Options Comparison

| Platform | Free Tier | Auto-Updates | Ease | Best For |
|----------|-----------|--------------|------|----------|
| **Render.com** | ✅ Yes | ✅ Yes | ⭐⭐⭐⭐⭐ | Best overall |
| **Railway** | ✅ $5 credit | ✅ Yes | ⭐⭐⭐⭐ | Simple setup |
| **Heroku** | ❌ Paid only | ✅ Yes | ⭐⭐⭐ | Established |
| **PythonAnywhere** | ✅ Limited | ❌ Manual | ⭐⭐⭐ | Python-focused |

---

## 🔥 Option 1: Render.com (RECOMMENDED)

### Step 1: Prepare Your Project

1. **Update your project structure:**
```
phase_a_demo/
├── phase_a_core.py
├── phase_b_api.py                 # Your main API
├── phase_b_data_collectors.py
├── phase_c_smart_predictions.py
├── phase_d_injury_data.py
├── data_refresh_job.py            # NEW - Auto data updates
├── index.html
├── requirements.txt
├── Procfile                       # NEW - Tells Render how to run
├── render.yaml                    # NEW - Auto deployment config
└── runtime.txt                    # NEW - Python version
```

2. **Update requirements.txt** to include:
```txt
fastapi
uvicorn[standard]
httpx
python-dotenv
nba_api
requests
pandas
numpy
```

3. **Create a .gitignore** (if you don't have one):
```
__pycache__/
*.pyc
.env
.DS_Store
venv/
.vscode/
```

### Step 2: Push to GitHub

```bash
cd phase_a_demo
git init
git add .
git commit -m "Initial deployment setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/nba-prediction.git
git push -u origin main
```

### Step 3: Deploy on Render

1. Go to [render.com](https://render.com) and sign up
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `nba-prediction-api`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn phase_b_api:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

5. Add Environment Variables:
   - `NBA_API_KEY` = your NBA API key
   - `ODDS_API_KEY` = your Odds API key

6. Click **"Create Web Service"**

### Step 4: Set Up Automated Data Updates

1. In Render dashboard, click **"New +"** → **"Cron Job"**
2. Configure:
   - **Name:** `daily-data-refresh`
   - **Schedule:** `0 11 * * *` (6 AM EST daily)
   - **Command:** `python data_refresh_job.py`
   - Same environment variables as above

---

## 🔄 How Auto-Updates Work

### Your System Will:

1. **API Runs 24/7**
   - Automatically restarts if it crashes
   - Always available at your Render URL

2. **Data Refreshes Daily**
   - Cron job runs at 6 AM EST every day
   - Updates player stats, injuries, odds
   - No manual intervention needed

3. **Website Auto-Updates**
   - Dashboard polls API every 30 seconds (configurable)
   - Shows fresh data automatically
   - Users just refresh browser

### Data Flow:
```
6:00 AM EST Daily:
  ↓
Cron Job Runs → data_refresh_job.py
  ↓
Fetches: NBA Stats + Injuries + Odds
  ↓
Updates Database/Cache
  ↓
API serves fresh data
  ↓
Dashboard polls API → Shows new data
```

---

## 🌐 Accessing Your Deployed App

After deployment, you'll get a URL like:
```
https://nba-prediction-api.onrender.com
```

Your dashboard will be at:
```
https://nba-prediction-api.onrender.com/
```

API endpoints:
```
https://nba-prediction-api.onrender.com/api/predictions/today
https://nba-prediction-api.onrender.com/api/injuries
https://nba-prediction-api.onrender.com/docs  (interactive API docs)
```

---

## 💾 Option 2: Add Database (for Better Performance)

Currently, you're probably storing data in memory. For production:

### Quick PostgreSQL Setup on Render:

1. In Render, create a **PostgreSQL database** (free tier available)
2. Install database libraries:
```bash
pip install sqlalchemy psycopg2-binary
```

3. Update your collectors to save to database instead of memory

---

## 📱 Option 3: Make It a Mobile App (Future)

Once deployed as a website, you can:

1. **Progressive Web App (PWA)**
   - Add manifest.json to your dashboard
   - Users can "Add to Home Screen"
   - Works like native app

2. **Convert to Native App**
   - Use React Native or Flutter
   - Connect to your deployed API
   - Publish to App Store/Play Store

---

## 🔧 Troubleshooting

### API Won't Start?
```bash
# Check logs in Render dashboard
# Common issues:
- Missing environment variables
- Wrong Python version
- Missing dependencies in requirements.txt
```

### Data Not Updating?
```bash
# Check cron job logs
# Verify:
- Cron schedule syntax correct
- API keys valid
- Network access working
```

### Free Tier Limitations?
- Render free tier: API sleeps after 15 min inactivity
- Solution: Upgrade to paid ($7/mo) or use UptimeRobot to ping every 14 min

---

## ✅ Final Checklist

- [ ] Code pushed to GitHub
- [ ] requirements.txt complete
- [ ] Deployment files added (Procfile, render.yaml)
- [ ] Environment variables set on Render
- [ ] Web service deployed and running
- [ ] Cron job scheduled for daily updates
- [ ] Dashboard accessible via public URL
- [ ] API endpoints tested

---

## 🎉 You're Done!

Your NBA prediction system now:
- ✅ Runs 24/7 automatically
- ✅ Updates data daily without you
- ✅ Accessible from anywhere
- ✅ No need to run `python phase_b_api.py` manually!

Just share your Render URL with anyone, and they can use it!

---

## 📞 Next Steps

Want to add:
- User authentication?
- Betting history tracking?
- Email alerts for hot picks?
- Premium features?

Let me know what you want to build next!
