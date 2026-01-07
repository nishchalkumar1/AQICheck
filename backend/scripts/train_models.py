import pandas as pd
import numpy as np
import pickle
import os
import sys
from datetime import timedelta
from sqlalchemy.orm import Session
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
from statsmodels.tsa.arima.model import ARIMA
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator
from sklearn.preprocessing import MinMaxScaler

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
MODELS_DIR = os.path.join(BASE_DIR, "models")
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

from database import SessionLocal
from models_db import AQICleaned

def load_data(city=None):
    session = SessionLocal()
    query = session.query(AQICleaned.timestamp, AQICleaned.pm25).filter_by(city=city).order_by(AQICleaned.timestamp.asc())
    df = pd.read_sql(query.statement, session.bind)
    session.close()
    
    if df.empty: return df
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df = df.asfreq('H')
    df['pm25'] = df['pm25'].interpolate(method='linear')
    return df

def save_model(model, filename):
    path = os.path.join(MODELS_DIR, filename)
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to {path}")

def train_arima(train, test, city):
    print(f"[{city}] Training ARIMA...")
    try:
        model = ARIMA(train, order=(2, 1, 2)) 
        model_fit = model.fit()
        model_fit.save(os.path.join(MODELS_DIR, f"arima_{city}.pkl"))
    except Exception as e:
        print(f"[{city}] ARIMA Failed: {e}")

def train_lstm(train_data, test_data, city):
    print(f"[{city}] Training LSTM...")
    try:
        scaler = MinMaxScaler()
        train_scaled = scaler.fit_transform(train_data.values.reshape(-1, 1))
        
        with open(os.path.join(MODELS_DIR, f"scaler_{city}.pkl"), 'wb') as f:
            pickle.dump(scaler, f)
            
        n_input = 24
        n_features = 1
        generator = TimeseriesGenerator(train_scaled, train_scaled, length=n_input, batch_size=32)
        
        model = Sequential([
            LSTM(50, activation='relu', input_shape=(n_input, n_features)),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        model.fit(generator, epochs=2, verbose=0) # Reduced epochs for speed
        
        model.save(os.path.join(MODELS_DIR, f"lstm_{city}.h5"))
    except Exception as e:
        print(f"[{city}] LSTM Failed: {e}")

def main():
    session = SessionLocal()
    cities = [r[0] for r in session.query(AQICleaned.city).distinct().all()]
    session.close()
    
    print(f"Found {len(cities)} cities to train models for.")
    
    for city in cities:
        print(f"\nProcessing {city}...")
        df = load_data(city)
        if len(df) < 100:
            print(f"Not enough data for {city}. Skipping.")
            continue
            
        train_size = int(len(df) * 0.8)
        train, test = df['pm25'].iloc[:train_size], df['pm25'].iloc[train_size:]
        
        train_arima(train, test, city)
        train_lstm(train, test, city)

if __name__ == "__main__":
    main()
