from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from models_db import AQICleaned, AQIForecast
import ml_inference

import asyncio
from backend.scripts.ingest_data import ingest_data

app = FastAPI(title="AQI Insight Dashboard API")

# Background Task for Auto-Ingestion (Every 30 mins)
async def periodic_ingest():
    while True:
        print("🔄 Auto-Ingestion: Starting...")
        try:
            # Run ingestion in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, ingest_data)
            print("✅ Auto-Ingestion: Complete.")
        except Exception as e:
            print(f"❌ Auto-Ingestion Failed: {e}")
        
        # Wait for 30 minutes (30 * 60 seconds)
        await asyncio.sleep(30 * 60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_ingest())

@app.get("/cities")
def get_cities(db: Session = Depends(get_db)):
    """Get list of available cities."""
    cities = db.query(AQICleaned.city).distinct().all()
    return {"cities": [c[0] for c in cities]}

@app.get("/live-data")
def get_live_data(city: str = Query(..., description="City name"), db: Session = Depends(get_db)):
    # Get the record closest to now, but not in the future
    current_time = datetime.now().replace(microsecond=0)
    latest = db.query(AQICleaned).filter(
        AQICleaned.city == city,
        AQICleaned.timestamp <= current_time
    ).order_by(AQICleaned.timestamp.desc()).first()
    
    if not latest:
        # Fallback: just get the absolute last if "now" logic fails (e.g. timezone mismatch)
        # But for this specific issue, we want to avoid the future.
        # Let's try to get ANY data if the above returns nothing (e.g. old data)
        latest = db.query(AQICleaned).filter_by(city=city).order_by(AQICleaned.timestamp.desc()).first()
        
    if not latest:
        raise HTTPException(status_code=404, detail="No data found for this city")
    
    return {
        "timestamp": latest.timestamp,
        "pm25": latest.pm25,
        "aqi": latest.aqi,
        "category": latest.category,
        "city": latest.city
    }

@app.get("/history")
def get_history(city: str = Query(..., description="City name"), period: str = "24h", db: Session = Depends(get_db)):
    end_time = datetime.now()
    if period == "3d":
        start_time = end_time - timedelta(days=3)
    elif period == "7d":
        start_time = end_time - timedelta(days=7)
    else:
        start_time = end_time - timedelta(hours=24)
        
    records = db.query(AQICleaned).filter(
        AQICleaned.city == city,
        AQICleaned.timestamp >= start_time
    ).order_by(AQICleaned.timestamp.asc()).all()
    
    return [
        {
            "timestamp": r.timestamp,
            "pm25": r.pm25,
            "aqi": r.aqi,
            "category": r.category
        }
        for r in records
    ]

@app.get("/forecast")
def get_forecast(city: str = Query(..., description="City name")):
    """Get 72h forecast for a specific city."""
    forecasts = ml_inference.get_combined_forecast(city)
    return forecasts
