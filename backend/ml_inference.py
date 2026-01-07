import pickle
import numpy as np
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
from tensorflow.keras.models import load_model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
sys.path.append(BASE_DIR)

from database import SessionLocal
from models_db import AQICleaned

def calculate_aqi_only(pm25):
    if pm25 is None: return 0
    breakpoints = [(0, 30, 0, 50), (30, 60, 51, 100), (60, 90, 101, 200), (90, 120, 201, 300), (120, 250, 301, 400)]
    for (pm_min, pm_max, aqi_min, aqi_max) in breakpoints:
        if pm_min <= pm25 <= pm_max:
            width_pm = pm_max - pm_min
            width_aqi = aqi_max - aqi_min
            return int(aqi_min + ((pm25 - pm_min) / width_pm) * width_aqi)
    if pm25 > 250: return 401 + (pm25 - 250)
    return 0

def load_persistence_forecast(city, hours=72):
    session = SessionLocal()
    last_record = session.query(AQICleaned).filter_by(city=city).order_by(AQICleaned.timestamp.desc()).first()
    session.close()
    
    if not last_record: return []
        
    forecasts = []
    current_time = last_record.timestamp
    for i in range(1, hours + 1):
        future_time = current_time + timedelta(hours=i)
        forecasts.append({
            "timestamp": future_time,
            "pm25": last_record.pm25,
            "aqi": last_record.aqi,
            "model": "Persistence",
            "city": city
        })
    return forecasts

def load_arima_forecast(city, hours=72):
    try:
        model_path = os.path.join(MODELS_DIR, f"arima_{city}.pkl")
        if not os.path.exists(model_path): return []
        
        from statsmodels.tsa.arima.model import ARIMAResults
        model_fit = ARIMAResults.load(model_path)
        forecast = model_fit.forecast(steps=hours)
        
        session = SessionLocal()
        last_record = session.query(AQICleaned).filter_by(city=city).order_by(AQICleaned.timestamp.desc()).first()
        session.close()
        start_time = last_record.timestamp if last_record else datetime.now()
        
        forecasts = []
        for i, val in enumerate(forecast):
            future_time = start_time + timedelta(hours=i+1)
            forecasts.append({
                "timestamp": future_time,
                "pm25": max(0, val),
                "aqi": calculate_aqi_only(max(0, val)),
                "model": "ARIMA",
                "city": city
            })
        return forecasts
    except Exception as e:
        print(f"Error loading ARIMA for {city}: {e}")
        return []

def load_lstm_forecast(city, hours=72):
    try:
        model_path = os.path.join(MODELS_DIR, f"lstm_{city}.h5")
        scaler_path = os.path.join(MODELS_DIR, f"scaler_{city}.pkl")
        
        if not os.path.exists(model_path): return []
        
        model = load_model(model_path)
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
            
        session = SessionLocal()
        records = session.query(AQICleaned).filter_by(city=city).order_by(AQICleaned.timestamp.desc()).limit(24).all()
        session.close()
        
        if len(records) < 24: return []
            
        data = np.array([r.pm25 for r in reversed(records)]).reshape(-1, 1)
        current_input = scaler.transform(data).reshape(1, 24, 1)
        
        forecasts = []
        current_time = records[0].timestamp
        
        for i in range(hours):
            pred_scaled = model.predict(current_input, verbose=0)
            pred = scaler.inverse_transform(pred_scaled)[0][0]
            
            future_time = current_time + timedelta(hours=i+1)
            forecasts.append({
                "timestamp": future_time,
                "pm25": max(0, pred),
                "aqi": calculate_aqi_only(max(0, pred)),
                "model": "LSTM",
                "city": city
            })
            
            new_step = pred_scaled.reshape(1, 1, 1)
            current_input = np.concatenate([current_input[:, 1:, :], new_step], axis=1)
            
        return forecasts
    except Exception as e:
        print(f"Error loading LSTM for {city}: {e}")
        return []

def get_combined_forecast(city):
    lstm = load_lstm_forecast(city)
    if lstm: return lstm
    arima = load_arima_forecast(city)
    if arima: return arima
    return load_persistence_forecast(city)
