from sqlalchemy import Column, Integer, Float, String, DateTime
from database import Base
import datetime

class AQIRaw(Base):
    __tablename__ = "aqi_raw"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String)
    parameter = Column(String)  # PM2.5
    value = Column(Float)
    unit = Column(String)
    timestamp = Column(DateTime)
    source = Column(String)

class AQICleaned(Base):
    __tablename__ = "aqi_cleaned"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)  # Added city column
    timestamp = Column(DateTime, index=True) # Removed unique constraint on just timestamp, uniqueness is (city, timestamp)
    pm25 = Column(Float)
    aqi = Column(Integer)
    category = Column(String)
    hour = Column(Integer)
    day_of_week = Column(Integer)

class AQIForecast(Base):
    __tablename__ = "aqi_forecast"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True) # Added city column
    model_name = Column(String)  # Persistence, ARIMA, LSTM
    forecast_timestamp = Column(DateTime)
    predicted_pm25 = Column(Float)
    predicted_aqi = Column(Integer)
    horizon = Column(String)  # 1h, 6h, 12h, 24h
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
