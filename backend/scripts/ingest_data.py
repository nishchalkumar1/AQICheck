import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models_db import AQIRaw, AQICleaned

# List of 25 Major Indian Cities with approximate coordinates
CITIES = {
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Bengaluru": (12.9716, 77.5946),
    "Kolkata": (22.5726, 88.3639),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Pune": (18.5204, 73.8567),
    "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
    "Patna": (25.5941, 85.1376),
    "Nagpur": (21.1458, 79.0882),
    "Indore": (22.7196, 75.8577),
    "Thane": (19.2183, 72.9781),
    "Bhopal": (23.2599, 77.4126),
    "Visakhapatnam": (17.6868, 83.2185),
    "Surat": (21.1702, 72.8311),
    "Kanpur": (26.4499, 80.3319),
    "Ghaziabad": (28.6692, 77.4538),
    "Ludhiana": (30.9010, 75.8573),
    "Agra": (27.1767, 78.0081),
    "Nashik": (19.9975, 73.7898),
    "Vadodara": (22.3072, 73.1812),
    "Faridabad": (28.4089, 77.3178),
    "Meerut": (28.9845, 77.7064)
}

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

def fetch_data(lat, lon):
    """Fetch last 90 days of PM2.5 data from OpenMeteo."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "timezone": "auto"
    }
    
    try:
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error: {e}")
    return None

def calculate_aqi(pm25):
    if pm25 is None: return None
    breakpoints = [(0, 30, 0, 50), (30, 60, 51, 100), (60, 90, 101, 200), 
                   (90, 120, 201, 300), (120, 250, 301, 400), (250, float('inf'), 401, 500)]
    for (pm_min, pm_max, aqi_min, aqi_max) in breakpoints:
        if pm_min <= pm25 <= pm_max:
            if pm_max == float('inf'): return 401 + (pm25 - 250)
            width_pm = pm_max - pm_min
            width_aqi = aqi_max - aqi_min
            return int(aqi_min + ((pm25 - pm_min) / width_pm) * width_aqi)
    return 500

def get_aqi_category(aqi):
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Satisfactory"
    if aqi <= 200: return "Moderate"
    if aqi <= 300: return "Poor"
    if aqi <= 400: return "Very Poor"
    return "Severe"

def ingest_data():
    session = SessionLocal()
    
    for city, (lat, lon) in CITIES.items():
        print(f"Fetching data for {city}...")
        data = fetch_data(lat, lon)
        
        if not data:
            print(f"Skipping {city} due to fetch error.")
            continue
            
        hourly = data.get("hourly", {})
        timestamps = hourly.get("time", [])
        pm25_values = hourly.get("pm2_5", [])
        
        count = 0
        for i in range(len(timestamps)):
            ts_str = timestamps[i]
            pm25 = pm25_values[i]
            if pm25 is None: continue
                
            timestamp = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M")
            
            # Check existing to avoid duplication (slower but safer)
            existing = session.query(AQICleaned).filter_by(city=city, timestamp=timestamp).first()
            if existing: continue

            aqi = calculate_aqi(pm25)
            category = get_aqi_category(aqi)
            
            cleaned_record = AQICleaned(
                city=city,
                timestamp=timestamp,
                pm25=pm25,
                aqi=aqi,
                category=category,
                hour=timestamp.hour,
                day_of_week=timestamp.weekday()
            )
            session.add(cleaned_record)
            count += 1
            
        if count > 0:
            print(f" -> Added {count} records for {city}.")
        session.commit() # Commit per city to save progress
        if count > 0: time.sleep(1) # Be nice to API only if we hit it hard

    session.close()
    print("Ingestion Complete.")

if __name__ == "__main__":
    ingest_data()
