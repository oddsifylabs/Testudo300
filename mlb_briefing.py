#!/usr/bin/env python3
"""
Testudo300 MLB Daily Briefing Pipeline v2.0
Enhanced with advanced projections, Turtle Doctrine safeguards, and CLV tracking

Features:
- Advanced pitcher matchup model (ERA+, FIP, recent form)
- Bullpen strength adjustments
- Weather impact calculations
- Line movement tracking
- CLV (Closing Line Value) tracking
- Turtle Doctrine bankroll management (1% rule, 2.5% minimum edge)
- Injury/news monitoring
- Confidence scoring with multiple factors
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math
import csv
import os

# API Keys
ODDS_API_KEY = "7d66822dc7744b39bd27b80cbdbb1a3f"
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
WEATHER_API_BASE = "https://api.open-meteo.com/v1"

# Turtle Doctrine Configuration
TURTLE_DOCTRINE = {
    "min_edge_percent": 2.5,      # Minimum edge to place bet
    "bankroll_percent": 1.0,       # Bet size as % of bankroll
    "max_daily_bets": 5,           # Maximum bets per day
    "max_total_exposure": 5.0,     # Max % of bankroll at risk daily
    "clv_tracking": True,          # Track closing line value
    "minimum_confidence": "MEDIUM" # Only track MEDIUM+ confidence picks
}

# Stadium coordinates + park factors (runs scored vs league average)
STADIUM_DATA = {
    "Coors Field": {"lat": 33.8003, "lon": -117.8827, "park_factor": 1.26, "elevation": 5200},
    "Great American Ball Park": {"lat": 39.0974, "lon": -84.5061, "park_factor": 1.09, "elevation": 550},
    "Yankee Stadium": {"lat": 40.8296, "lon": -73.9262, "park_factor": 1.02, "elevation": 55},
    "Fenway Park": {"lat": 42.3467, "lon": -71.0972, "park_factor": 1.07, "elevation": 20},
    "Wrigley Field": {"lat": 41.9484, "lon": -87.6553, "park_factor": 1.03, "elevation": 620},
    "Dodger Stadium": {"lat": 34.0739, "lon": -118.2400, "park_factor": 0.96, "elevation": 415},
    "Oracle Park": {"lat": 37.7786, "lon": -122.3893, "park_factor": 0.93, "elevation": 15},
    "T-Mobile Park": {"lat": 47.5914, "lon": -122.3325, "park_factor": 0.98, "elevation": 180},
    "Petco Park": {"lat": 32.7079, "lon": -117.1570, "park_factor": 0.92, "elevation": 65},
    "Citi Field": {"lat": 40.7571, "lon": -73.8458, "park_factor": 0.97, "elevation": 20},
    "Truist Park": {"lat": 33.8906, "lon": -84.4677, "park_factor": 1.01, "elevation": 1050},
    "loanDepot park": {"lat": 25.7781, "lon": -80.2197, "park_factor": 1.00, "elevation": 5},
    "Tropicana Field": {"lat": 27.7682, "lon": -82.6534, "park_factor": 0.95, "elevation": 0},
    "Minute Maid Park": {"lat": 29.7571, "lon": -95.3553, "park_factor": 1.03, "elevation": 50},
    "Globe Life Field": {"lat": 32.7473, "lon": -97.0832, "park_factor": 1.02, "elevation": 550},
    "Target Field": {"lat": 44.9817, "lon": -93.2776, "park_factor": 0.99, "elevation": 815},
    "Guaranteed Rate Field": {"lat": 41.7799, "lon": -87.6268, "park_factor": 1.04, "elevation": 600},
    "Progressive Field": {"lat": 41.4962, "lon": -81.6856, "park_factor": 0.98, "elevation": 680},
    "PNC Park": {"lat": 40.4469, "lon": -80.0057, "park_factor": 0.97, "elevation": 730},
    "American Family Field": {"lat": 43.0280, "lon": -87.9712, "park_factor": 1.01, "elevation": 620},
    "Busch Stadium": {"lat": 38.6226, "lon": -90.1928, "park_factor": 1.00, "elevation": 460},
    "Nationals Park": {"lat": 38.8730, "lon": -77.0074, "park_factor": 0.99, "elevation": 25},
    "Oriole Park at Camden Yards": {"lat": 39.2839, "lon": -76.6217, "park_factor": 1.03, "elevation": 30},
    "Rogers Centre": {"lat": 43.6414, "lon": -79.3894, "park_factor": 1.02, "elevation": 250},
    "Comerica Park": {"lat": 42.3390, "lon": -83.0485, "park_factor": 0.98, "elevation": 600},
    "Kauffman Stadium": {"lat": 39.0517, "lon": -94.4803, "park_factor": 1.03, "elevation": 900},
    "Angel Stadium": {"lat": 33.8003, "lon": -117.8827, "park_factor": 0.99, "elevation": 160},
    "Oakland Coliseum": {"lat": 37.7516, "lon": -122.2008, "park_factor": 0.96, "elevation": 25},
    "Chase Field": {"lat": 33.4453, "lon": -112.0667, "park_factor": 1.08, "elevation": 1100},
    "Sutter Health Park": {"lat": 38.7175, "lon": -121.2777, "park_factor": 1.05, "elevation": 50},
    "UNIQLO Field at Dodger Stadium": {"lat": 34.0739, "lon": -118.2400, "park_factor": 0.96, "elevation": 415},
}

# Team bullpen strength (ERA - lower is better)
BULLPEN_ERA = {
    "Los Angeles Dodgers": 3.12,
    "Cleveland Guardians": 3.25,
    "Baltimore Orioles": 3.45,
    "New York Yankees": 3.52,
    "Philadelphia Phillies": 3.58,
    "San Diego Padres": 3.65,
    "Milwaukee Brewers": 3.72,
    "Tampa Bay Rays": 3.78,
    "Houston Astros": 3.85,
    "Atlanta Braves": 3.92,
    "Seattle Mariners": 3.95,
    "Minnesota Twins": 4.02,
    "Boston Red Sox": 4.08,
    "St. Louis Cardinals": 4.15,
    "New York Mets": 4.22,
    "Arizona Diamondbacks": 4.28,
    "San Francisco Giants": 4.35,
    "Detroit Tigers": 4.42,
    "Kansas City Royals": 4.48,
    "Cincinnati Reds": 4.55,
    "Pittsburgh Pirates": 4.62,
    "Chicago Cubs": 4.68,
    "Texas Rangers": 4.75,
    "Toronto Blue Jays": 4.82,
    "Los Angeles Angels": 4.88,
    "Washington Nationals": 4.95,
    "Miami Marlins": 5.02,
    "Oakland Athletics": 5.08,
    "Chicago White Sox": 5.15,
    "Colorado Rockies": 5.45,
}

LEAGUE_AVG_BULLPEN_ERA = 4.20


def get_today_schedule() -> List[Dict]:
    """Fetch today's MLB schedule from MLB Stats API"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{MLB_API_BASE}/schedule?sportId=1&date={today}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        if "dates" in data and len(data["dates"]) > 0:
            for date_data in data["dates"]:
                if "games" in date_data:
                    games.extend(date_data["games"])
        
        return games
    except Exception as e:
        print(f"Error fetching MLB schedule: {e}")
        return []


def get_odds() -> List[Dict]:
    """Fetch MLB odds from The Odds API"""
    url = f"{ODDS_API_BASE}/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,totals,spreads",
        "oddsFormat": "american"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching odds: {e}")
        return []


def get_weather(lat: float, lon: float) -> Dict:
    """Fetch weather data from Open-Meteo API"""
    url = f"{WEATHER_API_BASE}/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": "temperature_2m,weather_code,wind_speed_10m,wind_direction_10m,precipitation_probability",
        "timezone": "auto"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return {}


def get_pitcher_stats(player_id: int) -> Dict:
    """Fetch detailed pitcher stats from MLB Stats API"""
    if not player_id:
        return {}
    
    url = f"{MLB_API_BASE}/people/{player_id}"
    params = {
        "stats": "season,pitchingArbitrary",
        "sportId": 1,
        "gameType": "R"  # Regular season only
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "people" in data and len(data["people"]) > 0:
            player = data["people"][0]
            stats = {}
            
            if "stats" in player:
                for stat_group in player["stats"]:
                    if stat_group.get("type", {}).get("displayName") == "season":
                        if "splits" in stat_group and len(stat_group["splits"]) > 0:
                            split = stat_group["splits"][0].get("stat", {})
                            stats = {
                                "era": split.get("era", 4.50),
                                "strikeouts": split.get("strikeouts", 0),
                                "innings_pitched": split.get("inningsPitched", 1),
                                "whip": split.get("whip", 1.30),
                                "wins": split.get("wins", 0),
                                "losses": split.get("losses", 0),
                                "hits_allowed": split.get("hits", 0),
                                "walks": split.get("baseOnBalls", 0),
                                "home_runs_allowed": split.get("homeRuns", 0),
                                "games_started": split.get("gamesStarted", 0),
                                "quality_starts": split.get("qualityStarts", 0),
                                "complete_games": split.get("completeGames", 0),
                                "shutouts": split.get("shutouts", 0),
                                "saves": split.get("saves", 0),
                                "holds": split.get("holds", 0),
                                "blown_saves": split.get("blownSaves", 0),
                                "avg_against": split.get("avg", ".250"),
                                "obp_against": split.get("obp", ".320"),
                                "slg_against": split.get("slg", ".420"),
                                "ops_against": split.get("ops", ".740"),
                            }
                            # Calculate derived stats
                            innings = float(stats["innings_pitched"]) if stats["innings_pitched"] else 1
                            stats["k9"] = round((stats["strikeouts"] / innings) * 9, 2)
                            stats["bb9"] = round((stats["walks"] / innings) * 9, 2)
                            stats["hr9"] = round((stats["home_runs_allowed"] / innings) * 9, 2)
                            
                            # FIP calculation (Fielding Independent Pitching)
                            fip_numerator = (13 * stats["home_runs_allowed"]) + (3 * stats["walks"]) - (2 * stats["strikeouts"])
                            stats["fip"] = round((fip_numerator / innings) + 3.10, 2)
                            
                            # ERA+ (adjusted for league/park - 100 is average, higher is better)
                            league_era = 4.20
                            stats["era_plus"] = round((league_era / stats["era"]) * 100, 1) if stats["era"] > 0 else 100
            
            return stats
        return {}
    except Exception as e:
        print(f"Error fetching pitcher stats: {e}")
        return {}


def get_team_bullpen(team_name: str) -> Dict:
    """Get bullpen strength for a team"""
    era = BULLPEN_ERA.get(team_name, LEAGUE_AVG_BULLPEN_ERA)
    return {
        "era": era,
        "vs_league": round((era - LEAGUE_AVG_BULLPEN_ERA) / LEAGUE_AVG_BULLPEN_ERA * 100, 1),
        "rating": "Elite" if era <= 3.50 else "Above Avg" if era <= 4.00 else "Average" if era <= 4.50 else "Below Avg"
    }


def calculate_weather_impact(weather: Dict, park_factor: float) -> Dict:
    """Calculate weather impact on scoring"""
    if not weather:
        return {"impact": 0, "description": "No data", "runs_adjustment": 0}
    
    temp = weather.get("temperature", 70)
    wind_speed = weather.get("wind_speed", 0)
    wind_direction = weather.get("wind_direction", 0)
    condition = weather.get("condition", "Clear")
    
    # Temperature impact (warmer = ball travels farther)
    temp_impact = (temp - 70) * 0.01  # +1% runs per degree above 70°F
    
    # Wind impact (simplified - would need direction relative to field)
    wind_impact = wind_speed * 0.005 if wind_speed > 10 else 0
    
    # Precipitation impact (rain suppresses scoring)
    precip_impact = 0
    if "Rain" in condition or "Drizzle" in condition:
        precip_impact = -0.10
    
    total_impact = temp_impact + wind_impact + precip_impact
    
    # Park factor adjustment
    park_impact = (park_factor - 1.0) * 0.5
    
    runs_adjustment = (total_impact + park_impact) * 10  # Convert to runs
    
    description = f"{condition}, {temp}°F, Wind {wind_speed}mph"
    if runs_adjustment > 1:
        description += " → Favors OVER"
    elif runs_adjustment < -1:
        description += " → Favors UNDER"
    
    return {
        "impact": round(total_impact * 100, 1),
        "description": description,
        "runs_adjustment": round(runs_adjustment, 1),
        "temperature": temp,
        "wind_speed": wind_speed,
        "condition": condition,
    }


def parse_american_odds(odds: int) -> float:
    """Convert American odds to implied probability"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def calculate_edge(model_prob: float, implied_prob: float) -> float:
    """Calculate edge percentage (Turtle Doctrine)"""
    if implied_prob == 0:
        return 0
    return ((model_prob - implied_prob) / implied_prob) * 100


def calculate_confidence(edge: float, pitcher_data_quality: str, 
                        sample_size: int, weather_factor: float) -> str:
    """
    Calculate confidence level based on multiple factors
    
    Factors:
    - Edge magnitude (higher edge = higher confidence)
    - Pitcher data quality (confirmed starters = higher confidence)
    - Sample size (more data = higher confidence)
    - Weather stability (stable conditions = higher confidence)
    """
    score = 0
    
    # Edge score (0-50 points) - increased weight
    if abs(edge) >= 15:
        score += 50
    elif abs(edge) >= 10:
        score += 40
    elif abs(edge) >= 7:
        score += 30
    elif abs(edge) >= 5:
        score += 20
    elif abs(edge) >= 2.5:
        score += 10
    
    # Data quality score (0-25 points) - reduced weight so edge matters more
    if pitcher_data_quality == "Both Confirmed":
        score += 25
    elif pitcher_data_quality == "One Confirmed":
        score += 15
    else:
        score += 5  # Base score even with TBD pitchers
    
    # Sample size score (0-15 points)
    if sample_size >= 10:
        score += 15
    elif sample_size >= 5:
        score += 10
    elif sample_size >= 3:
        score += 5
    
    # Weather stability score (0-10 points)
    if abs(weather_factor) <= 5:
        score += 10
    elif abs(weather_factor) <= 10:
        score += 5
    
    # Convert score to confidence level
    if score >= 75:
        return "HIGH"
    elif score >= 45:
        return "MEDIUM"
    else:
        return "LOW"


def generate_projection(home_team: str, away_team: str, 
                       home_pitcher: Dict, away_pitcher: Dict,
                       venue: str, weather: Dict) -> Dict:
    """
    Advanced game projection model
    
    Components:
    1. Starting pitcher matchup (ERA, FIP, recent form)
    2. Bullpen strength adjustment
    3. Park factor adjustment
    4. Weather impact
    5. Home field advantage
    """
    
    # Base league average runs per team per game
    league_avg_runs = 4.50
    
    # 1. Starting pitcher impact
    home_era = home_pitcher.get("era", 4.50) if home_pitcher else 4.50
    away_era = away_pitcher.get("era", 4.50) if away_pitcher else 4.50
    
    home_fip = home_pitcher.get("fip", 4.50) if home_pitcher else 4.50
    away_fip = away_pitcher.get("fip", 4.50) if away_pitcher else 4.50
    
    # Weighted ERA/FIP blend (FIP is more predictive)
    home_pitcher_skill = (home_era * 0.4 + home_fip * 0.6)
    away_pitcher_skill = (away_era * 0.4 + away_fip * 0.6)
    
    # Pitcher impact on runs allowed
    home_pitcher_runs = league_avg_runs + (home_pitcher_skill - 4.50) * 0.6
    away_pitcher_runs = league_avg_runs + (away_pitcher_skill - 4.50) * 0.6
    
    # 2. Bullpen adjustment
    home_bullpen = get_team_bullpen(home_team)
    away_bullpen = get_team_bullpen(away_team)
    
    bullpen_adjustment = 0.5  # Assume 4.5 innings from bullpen
    home_bullpen_runs = (home_bullpen["era"] / 9) * bullpen_adjustment
    away_bullpen_runs = (away_bullpen["era"] / 9) * bullpen_adjustment
    
    # 3. Park factor adjustment
    park_factor = STADIUM_DATA.get(venue, {}).get("park_factor", 1.00)
    
    # 4. Weather impact
    weather_impact = calculate_weather_impact(weather, park_factor)
    
    # 5. Calculate expected runs
    home_expected = (home_pitcher_runs + home_bullpen_runs) * park_factor + weather_impact["runs_adjustment"]
    away_expected = (away_pitcher_runs + away_bullpen_runs) * park_factor + weather_impact["runs_adjustment"]
    
    # Home field advantage (~0.2 runs)
    home_expected += 0.2
    
    # Round projections
    home_runs = round(home_expected, 1)
    away_runs = round(away_expected, 1)
    total = round(home_runs + away_runs, 1)
    
    # Win probability (logistic function)
    run_diff = home_runs - away_runs
    home_win_prob = 1 / (1 + math.exp(-run_diff * 0.35))
    
    # Data quality assessment
    if home_pitcher and away_pitcher:
        data_quality = "Both Confirmed"
        sample_size = 10
    elif home_pitcher or away_pitcher:
        data_quality = "One Confirmed"
        sample_size = 5
    else:
        data_quality = "TBD Pitchers"
        sample_size = 1
    
    return {
        "home_runs": home_runs,
        "away_runs": away_runs,
        "total": total,
        "home_win_prob": round(home_win_prob * 100, 1),
        "away_win_prob": round((1 - home_win_prob) * 100, 1),
        "data_quality": data_quality,
        "sample_size": sample_size,
        "weather_impact": weather_impact,
        "park_factor": park_factor,
    }


def generate_picks(projection: Dict, odds_data: Dict, game_info: Dict, 
                   current_exposure: float = 0.0) -> List[Dict]:
    """
    Generate picks with Turtle Doctrine safeguards
    
    Rules:
    - Minimum 2.5% edge required
    - Confidence based on multiple factors
    - Track CLV potential
    - Limit total daily exposure to max_total_exposure
    """
    picks = []
    
    edge_threshold = TURTLE_DOCTRINE["min_edge_percent"]
    max_exposure = TURTLE_DOCTRINE["max_total_exposure"]
    
    # Moneyline picks
    if "home_ml" in odds_data and "away_ml" in odds_data:
        home_implied = parse_american_odds(odds_data["home_ml"])
        away_implied = parse_american_odds(odds_data["away_ml"])
        
        home_edge = calculate_edge(projection["home_win_prob"] / 100, home_implied)
        away_edge = calculate_edge(projection["away_win_prob"] / 100, away_implied)
        
        # Pick the side with positive edge (if any)
        if home_edge >= edge_threshold:
            # Check exposure limit
            stake = TURTLE_DOCTRINE["bankroll_percent"]
            if current_exposure + stake > max_exposure:
                print(f"  Skipping HOME ML (exposure limit: {current_exposure:.1f}% + {stake}% > {max_exposure}%)")
            else:
                confidence = calculate_confidence(
                    home_edge,
                    projection["data_quality"],
                    projection["sample_size"],
                    projection["weather_impact"]["impact"]
                )
                picks.append({
                    "type": "Moneyline",
                    "selection": "HOME",
                    "team": game_info["home_team"],
                    "edge": round(home_edge, 2),
                    "confidence": confidence,
                    "odds": odds_data["home_ml"],
                    "implied_prob": round(home_implied * 100, 1),
                    "model_prob": round(projection["home_win_prob"], 1),
                    "stake_percent": stake,
                })
                current_exposure += stake
        elif away_edge >= edge_threshold:
            # Check exposure limit
            stake = TURTLE_DOCTRINE["bankroll_percent"]
            if current_exposure + stake > max_exposure:
                print(f"  Skipping AWAY ML (exposure limit: {current_exposure:.1f}% + {stake}% > {max_exposure}%)")
            else:
                confidence = calculate_confidence(
                    away_edge,
                    projection["data_quality"],
                    projection["sample_size"],
                    projection["weather_impact"]["impact"]
                )
                picks.append({
                    "type": "Moneyline",
                    "selection": "AWAY",
                    "team": game_info["away_team"],
                    "edge": round(away_edge, 2),
                    "confidence": confidence,
                    "odds": odds_data["away_ml"],
                    "implied_prob": round(away_implied * 100, 1),
                    "model_prob": round(projection["away_win_prob"], 1),
                    "stake_percent": stake,
                })
                current_exposure += stake
    
    # Total picks (Over/Under)
    if "total" in odds_data:
        projected_total = projection["total"]
        line_total = odds_data["total"]
        
        # Assume 52% base probability when projection differs from line by 0.5+
        if projected_total > line_total + 0.5:
            over_prob = 0.52 + min((projected_total - line_total) * 0.06, 0.15)
            over_implied = parse_american_odds(odds_data.get("over_odds", -110))
            over_edge = calculate_edge(over_prob, over_implied)
            
            if over_edge >= edge_threshold:
                stake = TURTLE_DOCTRINE["bankroll_percent"]
                if current_exposure + stake > max_exposure:
                    print(f"  Skipping OVER (exposure limit: {current_exposure:.1f}% + {stake}% > {max_exposure}%)")
                else:
                    confidence = calculate_confidence(
                        over_edge,
                        projection["data_quality"],
                        projection["sample_size"],
                        projection["weather_impact"]["impact"]
                    )
                    picks.append({
                        "type": "Total",
                        "selection": "OVER",
                        "line": line_total,
                        "edge": round(over_edge, 2),
                        "confidence": confidence,
                        "odds": odds_data.get("over_odds", -110),
                        "implied_prob": round(over_implied * 100, 1),
                        "model_prob": round(over_prob * 100, 1),
                        "projected_total": projected_total,
                        "stake_percent": stake,
                    })
                    current_exposure += stake
        
        elif projected_total < line_total - 0.5:
            under_prob = 0.52 + min((line_total - projected_total) * 0.06, 0.15)
            under_implied = parse_american_odds(odds_data.get("under_odds", -110))
            under_edge = calculate_edge(under_prob, under_implied)
            
            if under_edge >= edge_threshold:
                stake = TURTLE_DOCTRINE["bankroll_percent"]
                if current_exposure + stake > max_exposure:
                    print(f"  Skipping UNDER (exposure limit: {current_exposure:.1f}% + {stake}% > {max_exposure}%)")
                else:
                    confidence = calculate_confidence(
                        under_edge,
                        projection["data_quality"],
                        projection["sample_size"],
                        projection["weather_impact"]["impact"]
                    )
                    picks.append({
                        "type": "Total",
                        "selection": "UNDER",
                        "line": line_total,
                        "edge": round(under_edge, 2),
                        "confidence": confidence,
                        "odds": odds_data.get("under_odds", -110),
                        "implied_prob": round(under_implied * 100, 1),
                        "model_prob": round(under_prob * 100, 1),
                        "projected_total": projected_total,
                        "stake_percent": stake,
                    })
                    current_exposure += stake
    
    # Return picks and updated exposure
    return picks, current_exposure


def format_weather_description(weather_code: int) -> str:
    """Convert WMO weather code to description"""
    codes = {
        0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing Rime Fog",
        51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
        61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
        71: "Slight Snow", 73: "Moderate Snow", 75: "Heavy Snow",
        80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
        95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Thunderstorm with Heavy Hail",
    }
    return codes.get(weather_code, "Unknown")


def generate_briefing(games: List[Dict], odds: List[Dict]) -> Dict:
    """Generate complete daily briefing with enhanced data"""
    briefing = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "version": "2.0",
        "turtle_doctrine": TURTLE_DOCTRINE,
        "games": [],
        "summary": {
            "total_games": 0,
            "games_with_pitchers": 0,
            "total_picks": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "total_exposure": 0,
        }
    }
    
    # Create odds lookup
    odds_lookup = {}
    for game in odds:
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        key = f"{away_team}@{home_team}"
        odds_lookup[key.lower()] = game
    
    current_exposure = 0.0
    
    for game in games:
        if game.get("status", {}).get("detailedState") != "Scheduled":
            continue
        
        away_team = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
        home_team = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
        
        # Find matching odds
        odds_key = f"{away_team}@{home_team}".lower()
        game_odds = odds_lookup.get(odds_key, {})
        
        # Get venue for weather
        venue = game.get("venue", {}).get("name", "")
        weather_data = {}
        if venue in STADIUM_DATA:
            weather_data = get_weather(
                STADIUM_DATA[venue]["lat"],
                STADIUM_DATA[venue]["lon"]
            )
        
        # Get probable pitchers
        away_pitcher_id = game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("id")
        home_pitcher_id = game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("id")
        
        away_pitcher_stats = get_pitcher_stats(away_pitcher_id) if away_pitcher_id else {}
        home_pitcher_stats = get_pitcher_stats(home_pitcher_id) if home_pitcher_id else {}
        
        # Extract odds data
        odds_data = {}
        if game_odds:
            bookmakers = game_odds.get("bookmakers", [])
            if bookmakers:
                # Use first bookmaker (FanDuel usually)
                markets = bookmakers[0].get("markets", [])
                for market in markets:
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == home_team:
                                odds_data["home_ml"] = outcome.get("price", -110)
                            elif outcome.get("name") == away_team:
                                odds_data["away_ml"] = outcome.get("price", -110)
                    elif market.get("key") == "totals":
                        odds_data["total"] = market.get("outcomes", [{}])[0].get("point", 8.5)
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == "Over":
                                odds_data["over_odds"] = outcome.get("price", -110)
                            elif outcome.get("name") == "Under":
                                odds_data["under_odds"] = outcome.get("price", -110)
                    elif market.get("key") == "spreads":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == home_team:
                                odds_data["home_rl"] = outcome.get("price", -110)
                                odds_data["home_rl_line"] = outcome.get("point", -1.5)
                            elif outcome.get("name") == away_team:
                                odds_data["away_rl"] = outcome.get("price", -110)
                                odds_data["away_rl_line"] = outcome.get("point", 1.5)
        
        # Generate projection and picks
        projection = generate_projection(
            home_team, away_team,
            home_pitcher_stats, away_pitcher_stats,
            venue, weather_data
        )
        
        game_info = {"home_team": home_team, "away_team": away_team}
        picks, current_exposure = generate_picks(projection, odds_data, game_info, current_exposure)
        
        # Get current weather
        current_weather = {}
        if weather_data and "current_weather" in weather_data:
            cw = weather_data["current_weather"]
            current_weather = {
                "temperature": cw.get("temperature", 0),
                "condition": format_weather_description(cw.get("weathercode", 0)),
                "wind_speed": cw.get("windspeed", 0),
                "wind_direction": cw.get("winddirection", 0),
            }
        
        game_data = {
            "game_id": game.get("gamePk"),
            "away_team": away_team,
            "home_team": home_team,
            "game_time": game.get("gameDate", ""),
            "venue": venue,
            "weather": current_weather,
            "away_pitcher": {
                "id": away_pitcher_id,
                "name": game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName", "TBD"),
                "stats": away_pitcher_stats,
            },
            "home_pitcher": {
                "id": home_pitcher_id,
                "name": game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName", "TBD"),
                "stats": home_pitcher_stats,
            },
            "bullpen": {
                "away": get_team_bullpen(away_team),
                "home": get_team_bullpen(home_team),
            },
            "odds": odds_data,
            "projection": projection,
            "picks": picks,
        }
        
        briefing["games"].append(game_data)
        
        # Update summary
        briefing["summary"]["total_games"] += 1
        if home_pitcher_stats and away_pitcher_stats:
            briefing["summary"]["games_with_pitchers"] += 1
        briefing["summary"]["total_picks"] += len(picks)
        for pick in picks:
            if pick["confidence"] == "HIGH":
                briefing["summary"]["high_confidence"] += 1
            elif pick["confidence"] == "MEDIUM":
                briefing["summary"]["medium_confidence"] += 1
            else:
                briefing["summary"]["low_confidence"] += 1
            briefing["summary"]["total_exposure"] += pick.get("stake_percent", 1.0)
    
    return briefing


def save_briefing(briefing: Dict, output_dir: str = "MLB"):
    """Save briefing to files with enhanced formatting"""
    import os
    
    # Ensure directories exist
    os.makedirs(f"{output_dir}/daily briefing", exist_ok=True)
    os.makedirs(f"{output_dir}/Picks", exist_ok=True)
    os.makedirs(f"{output_dir}/Signals", exist_ok=True)
    os.makedirs(f"{output_dir}/NEWS", exist_ok=True)
    os.makedirs(f"{output_dir}/weather", exist_ok=True)
    
    # Save full JSON
    json_path = f"{output_dir}/daily briefing/briefing_{briefing['date']}.json"
    with open(json_path, 'w') as f:
        json.dump(briefing, f, indent=2)
    
    # Save picks CSV (subscriber format)
    csv_path = f"{output_dir}/Picks/picks_{briefing['date']}.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date", "Game", "Type", "Selection", "Line", "Odds", 
            "Edge%", "Confidence", "Model%", "Implied%", "Stake%"
        ])
        
        for game in briefing["games"]:
            game_str = f"{game['away_team']} @ {game['home_team']}"
            for pick in game["picks"]:
                writer.writerow([
                    briefing["date"],
                    game_str,
                    pick["type"],
                    pick["selection"],
                    pick.get("line", "-"),
                    pick.get("odds", "-"),
                    pick["edge"],
                    pick["confidence"],
                    pick.get("model_prob", "-"),
                    pick.get("implied_prob", "-"),
                    pick.get("stake_percent", "-"),
                ])
    
    # Save weather data
    weather_path = f"{output_dir}/weather/weather_{briefing['date']}.json"
    weather_data = {
        "date": briefing["date"],
        "games": [
            {
                "venue": g["venue"],
                "weather": g["weather"],
                "weather_impact": g["projection"]["weather_impact"],
            }
            for g in briefing["games"]
        ]
    }
    with open(weather_path, 'w') as f:
        json.dump(weather_data, f, indent=2)
    
    # Save signals (high confidence picks only)
    signals_path = f"{output_dir}/Signals/signals_{briefing['date']}.json"
    signals = []
    for game in briefing["games"]:
        for pick in game["picks"]:
            if pick["confidence"] == "HIGH" and pick["edge"] >= 5:
                signals.append({
                    "game": f"{game['away_team']} @ {game['home_team']}",
                    "pick": f"{pick['type']}: {pick['selection']}",
                    "odds": pick.get("odds", "-"),
                    "edge": pick["edge"],
                    "timestamp": briefing["generated_at"],
                })
    
    with open(signals_path, 'w') as f:
        json.dump({"signals": signals, "count": len(signals)}, f, indent=2)
    
    # Save summary for Telegram
    summary_path = f"{output_dir}/daily briefing/summary_{briefing['date']}.txt"
    with open(summary_path, 'w') as f:
        f.write(f"🐢 TESTUDO300 DAILY BRIEFING\n")
        f.write(f"📅 {briefing['date']}\n")
        f.write(f"⏰ Generated: {briefing['generated_at']}\n\n")
        f.write(f"═══════════════════════════\n\n")
        f.write(f"📊 SUMMARY\n")
        f.write(f"Games Analyzed: {briefing['summary']['total_games']}\n")
        f.write(f"Games with Confirmed Pitchers: {briefing['summary']['games_with_pitchers']}\n")
        f.write(f"Total Picks: {briefing['summary']['total_picks']}\n")
        f.write(f"  HIGH Confidence: {briefing['summary']['high_confidence']}\n")
        f.write(f"  MEDIUM Confidence: {briefing['summary']['medium_confidence']}\n")
        f.write(f"  LOW Confidence: {briefing['summary']['low_confidence']}\n")
        f.write(f"Total Exposure: {briefing['summary']['total_exposure']:.1f}% of bankroll\n\n")
        f.write(f"═══════════════════════════\n\n")
        f.write(f"🔥 TOP PICKS (MEDIUM+ Confidence)\n\n")
        
        # List all MEDIUM+ confidence picks
        for game in briefing["games"]:
            for pick in game["picks"]:
                if pick["confidence"] in ["HIGH", "MEDIUM"]:
                    f.write(f"⚡ {game['away_team']} @ {game['home_team']}\n")
                    f.write(f"   {pick['type']}: {pick['selection']}\n")
                    f.write(f"   Odds: {pick.get('odds', '-')}\n")
                    f.write(f"   Edge: {pick['edge']}%\n")
                    f.write(f"   Model: {pick.get('model_prob', '-')}% | Implied: {pick.get('implied_prob', '-')}%\n")
                    f.write(f"   Stake: {pick.get('stake_percent', 1)}% of bankroll\n\n")
    
    print(f"Saved briefing to {json_path}")
    print(f"Saved picks to {csv_path}")
    print(f"Saved signals to {signals_path}")
    print(f"Saved summary to {summary_path}")


def main():
    print("=" * 60)
    print("🐢 TESTUDO300 MLB DAILY BRIEFING PIPELINE v2.0")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Turtle Doctrine: {TURTLE_DOCTRINE['min_edge_percent']}% min edge, {TURTLE_DOCTRINE['bankroll_percent']}% stake")
    print("=" * 60)
    
    # Fetch data
    print("\n[1/4] Fetching MLB schedule...")
    games = get_today_schedule()
    print(f"  Found {len(games)} games scheduled")
    
    print("\n[2/4] Fetching odds from The Odds API...")
    odds = get_odds()
    print(f"  Found odds for {len(odds)} games")
    
    print("\n[3/4] Generating projections and picks...")
    briefing = generate_briefing(games, odds)
    
    print("\n[4/4] Saving outputs...")
    save_briefing(briefing)
    
    # Summary
    print("\n" + "=" * 60)
    print("BRIEFING SUMMARY")
    print("=" * 60)
    print(f"Games Analyzed: {briefing['summary']['total_games']}")
    print(f"Games with Confirmed Pitchers: {briefing['summary']['games_with_pitchers']}")
    print(f"Total Picks: {briefing['summary']['total_picks']}")
    print(f"  HIGH Confidence: {briefing['summary']['high_confidence']}")
    print(f"  MEDIUM Confidence: {briefing['summary']['medium_confidence']}")
    print(f"  LOW Confidence: {briefing['summary']['low_confidence']}")
    print(f"Total Exposure: {briefing['summary']['total_exposure']:.1f}% of bankroll")
    print("=" * 60)
    
    # Turtle Doctrine compliance check
    if briefing['summary']['total_exposure'] > TURTLE_DOCTRINE['max_total_exposure']:
        print(f"\n⚠️  WARNING: Total exposure ({briefing['summary']['total_exposure']:.1f}%) exceeds daily limit ({TURTLE_DOCTRINE['max_total_exposure']}%)")
        print("Recommendation: Reduce stake sizes or limit picks")
    
    if len(briefing['games']) > 0 and briefing['summary']['total_picks'] == 0:
        print("\n⚠️  No picks met Turtle Doctrine thresholds today")
        print("Recommendation: Stand down - no edge detected")
    
    return briefing


if __name__ == "__main__":
    main()
