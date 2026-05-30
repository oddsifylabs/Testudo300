#!/usr/bin/env bash
# Testudo300 Daily MLB Briefing Cron Job
# Runs every day at 10 AM ET to generate daily briefing

cd /home/markusbot/Testudo300
python3 mlb_briefing.py

# Push to GitHub
git add -A
git commit -m "Daily briefing $(date +%Y-%m-%d)"
git push origin main
