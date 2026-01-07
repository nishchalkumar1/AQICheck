import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AQI Insight Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    div.stMetric {
        background-color: #262730;
        border: 1px solid #464b5c;
        padding: 10px;
        border-radius: 5px;
    }
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
    h1, h2, h3 {
        color: #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def get_aqi_color(aqi):
    if aqi <= 50: return "#00e400"
    if aqi <= 100: return "#ffff00"
    if aqi <= 200: return "#ff7e00"
    if aqi <= 300: return "#ff0000"
    if aqi <= 400: return "#99004c"
    return "#7e0023"

def get_health_advisory(category):
    advisories = {
        "Good": "Air quality is good. Enjoy your outdoor activities!",
        "Satisfactory": "Minor breathing discomfort to sensitive people.",
        "Moderate": "Breathing discomfort to the people with lungs, asthma and heart diseases.",
        "Poor": "Breathing discomfort to most people on prolonged exposure.",
        "Very Poor": "Respiratory illness on prolonged exposure.",
        "Severe": "Affects healthy people and seriously impacts those with existing diseases."
    }
    return advisories.get(category, "Consult health advisory.")

def fetch_cities():
    try:
        response = requests.get(f"{API_URL}/cities")
        if response.status_code == 200:
            return response.json().get("cities", [])
    except:
        pass
    return ["Delhi"]

@st.cache_data(ttl=0)
def fetch_live_data(city):
    try:
        response = requests.get(f"{API_URL}/live-data", params={"city": city})
        return response.json() if response.status_code == 200 else None
    except:
        return None

@st.cache_data(ttl=300)
def fetch_history(city, period="24h"):
    try:
        response = requests.get(f"{API_URL}/history", params={"city": city, "period": period})
        return pd.DataFrame(response.json()) if response.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_forecast(city):
    try:
        response = requests.get(f"{API_URL}/forecast", params={"city": city})
        return pd.DataFrame(response.json()) if response.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

# Sidebar
st.sidebar.image("https://img.icons8.com/clouds/100/000000/air-quality.png", width=100)
st.sidebar.title("VayuTel Insight")

cities = fetch_cities()
if not cities:
    cities = ["Delhi", "Mumbai", "Bengaluru"]
    
selected_city = st.sidebar.selectbox("Select City", cities, index=0)

start_server = st.sidebar.button("Refresh Data")

# Auto-Refresh Logic (Every 30 Minutes)
st.sidebar.markdown("---")
refresh_interval = st.sidebar.slider("Auto-Refresh Interval (min)", 5, 60, 30)
if refresh_interval:
    st.components.v1.html(
        f"""
            <script>
                var time = new Date().getTime();
                var interval = {refresh_interval * 60 * 1000};
                function refresh() {{
                    window.location.reload();
                }}
                setTimeout(refresh, interval);
            </script>
        """,
        height=0
    )


# Main Layout
st.title(f"🌫️ AQI Dashboard: {selected_city}")
st.markdown("### Hyperlocal Pollution Monitoring & Forecasting")

# 1. Live Data
live_data = fetch_live_data(selected_city)

col1, col2, col3 = st.columns(3)

if live_data:
    aqi = live_data['aqi']
    pm25 = live_data['pm25']
    category = live_data['category']
    timestamp = datetime.fromisoformat(live_data['timestamp'])
    
    color = get_aqi_color(aqi)
    
    with col1:
        st.metric("Current AQI", f"{aqi}", f"{category}")
    with col2:
        st.metric("PM2.5", f"{pm25} µg/m³")
    with col3:
        st.write(f"**Last Updated:** {timestamp.strftime('%H:%M %d-%b')}")
        st.markdown(f"<div style='padding:10px; background-color:{color}; color:black; border-radius:5px; text-align:center;'><b>{category}</b></div>", unsafe_allow_html=True)
    
    st.info(f"💡 **Health Advisory**: {get_health_advisory(category)}")
else:
    st.error(f"No data available for {selected_city}. Please ensure backend is running.")

st.divider()

# 2. Historical Trends
st.subheader("📉 Historical Trends")
period = st.selectbox("Select History Period", ["24 Hours", "3 Days", "7 Days"])
period_map = {"24 Hours": "24h", "3 Days": "3d", "7 Days": "7d"}
period_param = period_map[period]

history_df = fetch_history(selected_city, period_param)

if not history_df.empty:
    history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
    
    spike_threshold = 250
    spikes = history_df[history_df['pm25'] > spike_threshold]
    
    fig = px.area(history_df, x='timestamp', y='pm25', title=f"PM2.5 Trend ({period})", 
                  template="plotly_dark", color_discrete_sequence=['#00CC96'])
    
    if not spikes.empty:
        fig.add_trace(go.Scatter(x=spikes['timestamp'], y=spikes['pm25'], mode='markers', 
                                 marker=dict(color='red', size=10), name='Spike Detected'))
        
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No historical data found.")

st.divider()

# 3. Forecasts
st.subheader("🔮 Predictive Analytics (Next 3 Days)")
forecast_df = fetch_forecast(selected_city)

if not forecast_df.empty:
    forecast_df['timestamp'] = pd.to_datetime(forecast_df['timestamp'])
    
    fig_forecast = px.line(forecast_df, x='timestamp', y='pm25', color='model', 
                           title=f"72-Hour Forecast for {selected_city}", template="plotly_dark")
    st.plotly_chart(fig_forecast, use_container_width=True)
    
    horizons = [6, 12, 24, 48, 72]
    st.write("#### Forecast Snapshot")
    
    # Prioritize LSTM, then ARIMA, then Persistence
    model_to_show = 'Persistence'
    if 'LSTM' in forecast_df['model'].values: model_to_show = 'LSTM'
    elif 'ARIMA' in forecast_df['model'].values: model_to_show = 'ARIMA'
    
    model_data = forecast_df[forecast_df['model'] == model_to_show].reset_index(drop=True)
    
    if not model_data.empty:
        cols = st.columns(len(horizons))
        for i, h in enumerate(horizons):
            if h <= len(model_data):
                row = model_data.iloc[h-1]
                with cols[i]:
                    st.metric(f"+{h} Hours", f"{row['pm25']:.1f}", f"AQI: {row['aqi']}")
else:
    st.info("No forecast data available.")

st.markdown("---")
st.caption("Powered by VayuTel Intelligence")
