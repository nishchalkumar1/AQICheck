# Cloud-based AQI Insight Dashboard 🌫️

A complete end-to-end web application for hyperlocal pollution monitoring and forecasting in New Delhi using Deep Learning (LSTM) and Public APIs.

## 📁 Project Structure

```
d:/aqicheck/
├── backend/
│   ├── data/               # SQLite database (aqi_v2.db)
│   ├── models/             # Saved ML models (LSTM, ARIMA)
│   ├── scripts/
│   │   ├── init_db.py      # Initialize DB tables
│   │   ├── ingest_data.py  # Fetch OpenMeteo data
│   │   └── train_models.py # Train ML models
│   ├── database.py         # DB connection
│   ├── ml_inference.py     # Inference logic for API
│   ├── models_db.py        # SQLAlchemy models
│   └── main.py             # FastAPI App
├── frontend/
│   └── app.py              # Streamlit Dashboard
├── requirements.txt
└── README.md
```

## 🚀 Setup & Run

### Prerequisites
- Python 3.8+
- SQLite (built-in)

### 1. Install Dependencies
```bash
pip install fastapi uvicorn sqlalchemy requests pandas numpy scikit-learn statsmodels tensorflow streamlit plotly
```

### 2. Initialize System
Run these commands in order:

```bash
# Initialize Database
python backend/scripts/init_db.py

# Ingest Historical Data (OpenMeteo)
python backend/scripts/ingest_data.py

# Train ML Models (Persistence, ARIMA, LSTM)
python backend/scripts/train_models.py
```

### 3. Run Application
Open two terminals:

**Terminal 1: Backend API**
```bash
uvicorn backend.main:app --reload
```
API docs available at: `http://localhost:8000/docs`

**Terminal 2: Frontend Dashboard**
```bash
streamlit run frontend/app.py
```
Dashboard available at: `http://localhost:8501`

## 🧠 Machine Learning Approach

### Models Implemented
1. **Persistence Baseline**: Naive forecast ($t+1 = t$).
2. **ARIMA**: Statistical time-series baseline.
3. **LSTM**: Deep learning sequence model (Lookback: 24h).

### Evaluation
Models are evaluated on RMSE, MAE, and MAPE. Run `train_models.py` to see the latest metrics.

## 📊 Dashboard Features
- **Real-time Monitoring**: Hourly updated AQI & PM2.5.
- **Forecasting**: 24-hour ahead predictions comparing robust/simple models.
- **Spike Detection**: Visual alerts for PM2.5 > 250 µg/m³.
- **Health Advisory**: Dynamic recommendations based on CPCB standards.

## ⚠️ Limitations
- **Data Source**: Relies on OpenMeteo Public API (might have gaps).
- **Model Storage**: Simple pickling/H5; production should use a model registry.
- **Scale**: SQLite is good for single-city demo; use PostgreSQL for scale.
