# app.py

import streamlit as st
import pandas as pd
import numpy as np
import requests  # Use requests for synchronous HTTP requests
from datetime import datetime, timedelta
import plotly.graph_objs as go
from threading import Thread
import logging
import time

# -----------------------------
# Configuration and Constants
# -----------------------------
SYMBOL = 'BTCUSDT'  # Trading pair
DEPTH = 20          # Number of price levels
DAYS_AVG_VOLUME = 30  # Days to calculate average daily volume

# -----------------------------
# Setup Logging
# -----------------------------
logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# -----------------------------
# Initialize Session State
# -----------------------------
for var in ['avg_daily_volume', 'bids', 'asks', 'signal', 'liquidity_bid', 'liquidity_ask', 'liquidity_bid_pct', 'liquidity_ask_pct']:
    if var not in st.session_state:
        st.session_state[var] = 0.0 if 'liquidity' in var else ([] if var in ['bids', 'asks'] else 'Neutral')

# -----------------------------
# Helper Functions
# -----------------------------

def fetch_avg_daily_volume(symbol: str, days: int = 30, retries: int = 3, delay: int = 5):
    """Fetches the average daily trading volume for a given symbol over a specified number of days."""
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': '1d',
        'limit': days
    }
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            if not klines:
                raise ValueError("No kline data received.")
            volumes = [float(kline[5]) for kline in klines]  # Volume is the 6th element
            avg_volume = sum(volumes) / len(volumes)
            logging.info(f"Fetched average daily volume for {symbol}: {avg_volume}")
            return avg_volume
        except Exception as e:
            logging.error(f"Attempt {attempt} - Error fetching average daily volume: {e}")
            if attempt < retries:
                st.warning(f"Attempt {attempt} failed. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                st.error(f"Failed to fetch average daily volume after {retries} attempts.")
                return 0.0

def calculate_liquidity(bids, asks, levels, avg_daily_volume):
    """Calculates liquidity metrics based on the top 'levels' bids and asks."""
    try:
        selected_bids = bids[:levels]
        selected_asks = asks[:levels]
        
        liquidity_bid = sum([float(q) for _, q in selected_bids])
        liquidity_ask = sum([float(q) for _, q in selected_asks])
        
        liquidity_bid_pct = (liquidity_bid / avg_daily_volume) * 100 if avg_daily_volume > 0 else 0
        liquidity_ask_pct = (liquidity_ask / avg_daily_volume) * 100 if avg_daily_volume > 0 else 0
        
        return liquidity_bid, liquidity_ask, liquidity_bid_pct, liquidity_ask_pct
    except Exception as e:
        logging.error(f"Error calculating liquidity: {e}")
        return 0.0, 0.0, 0.0, 0.0

def generate_signal(liquidity_bid_pct, liquidity_ask_pct, threshold):
    """Generates Buy/Sell/Neutral signals based on liquidity percentages and a threshold."""
    try:
        if liquidity_bid_pct > threshold and liquidity_ask_pct <= threshold:
            return 'Buy'
        elif liquidity_ask_pct > threshold and liquidity_bid_pct <= threshold:
            return 'Sell'
        else:
            return 'Neutral'
    except Exception as e:
        logging.error(f"Error generating signal: {e}")
        return 'Neutral'

def listen_order_book(symbol, depth, levels, threshold):
    """Listens to the Binance WebSocket for order book updates and processes liquidity signals."""
    url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@depth@100ms"
    import websocket
    import json

    def on_message(ws, message):
        try:
            data = json.loads(message)
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            
            liquidity_bid, liquidity_ask, liquidity_bid_pct, liquidity_ask_pct = calculate_liquidity(
                bids, asks, levels, st.session_state.avg_daily_volume
            )
            
            signal = generate_signal(liquidity_bid_pct, liquidity_ask_pct, threshold)
            
            # Update session state
            st.session_state.bids = bids[:levels]
            st.session_state.asks = asks[:levels]
            st.session_state.signal = signal
            st.session_state.liquidity_bid = liquidity_bid
            st.session_state.liquidity_ask = liquidity_ask
            st.session_state.liquidity_bid_pct = liquidity_bid_pct
            st.session_state.liquidity_ask_pct = liquidity_ask_pct
            
            logging.info(f"Updated Liquidity - Bid: {liquidity_bid} ({liquidity_bid_pct:.2f}%), Ask: {liquidity_ask} ({liquidity_ask_pct:.2f}%) - Signal: {signal}")
        except Exception as e:
            logging.error(f"Error processing WebSocket message: {e}")
    
    def on_error(ws, error):
        logging.error(f"WebSocket error: {error}")
        st.error(f"WebSocket encountered an error: {error}")
    
    def on_close(ws):
        logging.info("WebSocket connection closed.")
    
    def on_open(ws):
        logging.info("WebSocket connection established.")
    
    ws = websocket.WebSocketApp(url,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()

def run_order_book_listener(symbol, depth, levels, threshold):
    """Runs the WebSocket listener in a separate thread."""
    listen_order_book(symbol, depth, levels, threshold)

# -----------------------------
# Streamlit App Layout
# -----------------------------

st.set_page_config(page_title="Liquidity Detection Trading App", layout="wide")

st.title("🔍 Liquidity Detection Trading App")

# Sidebar for User Inputs
st.sidebar.header("Settings")
price_levels = st.sidebar.slider("Select Price Levels", min_value=1, max_value=20, value=10, key='price_levels')
threshold = st.sidebar.slider("Liquidity Threshold (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key='threshold')

# Display Average Daily Volume
if st.session_state.avg_daily_volume == 0 and price_levels > 0 and threshold > 0:
    avg_volume = fetch_avg_daily_volume(SYMBOL, DAYS_AVG_VOLUME)
    st.session_state.avg_daily_volume = avg_volume
    if avg_volume > 0.0:
        st.sidebar.write(f"**Avg Daily Volume ({DAYS_AVG_VOLUME} days):** {st.session_state.avg_daily_volume:.2f}")

# Start WebSocket Listener in a Separate Thread
if 'thread' not in st.session_state and st.session_state.avg_daily_volume > 0.0:
    thread = Thread(target=run_order_book_listener, args=(SYMBOL, DEPTH, price_levels, threshold), daemon=True)
    thread.start()
    st.session_state.thread = thread
    st.info("Connected to Binance WebSocket and listening for order book updates.")

# Display Liquidity Metrics
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Bid Side Liquidity")
    st.write(f"**Total Liquidity:** {st.session_state.liquidity_bid:.2f}")
    st.write(f"**Percentage of Avg Daily Volume:** {st.session_state.liquidity_bid_pct:.2f}%")

with col2:
    st.subheader("📉 Ask Side Liquidity")
    st.write(f"**Total Liquidity:** {st.session_state.liquidity_ask:.2f}")
    st.write(f"**Percentage of Avg Daily Volume:** {st.session_state.liquidity_ask_pct:.2f}%")

# Display Buy/Sell/Neutral Signal
st.subheader("⚠️ Trading Signal")
if st.session_state.signal == 'Buy':
    st.success("✅ **Buy Signal**")
elif st.session_state.signal == 'Sell':
    st.error("❌ **Sell Signal**")
else:
    st.info("ℹ️ **Neutral**")

# Display Order Book Chart
st.subheader("📊 Order Book Liquidity Chart")

# Prepare data for plotting
levels = st.session_state.price_levels
bids = st.session_state.bids
asks = st.session_state.asks

bid_prices = [float(bid[0]) for bid in bids]
bid_quantities = [float(bid[1]) for bid in bids]

ask_prices = [float(ask[0]) for ask in asks]
ask_quantities = [float(ask[1]) for ask in asks]

fig = go.Figure()

# Add Bids
fig.add_trace(go.Bar(
    x=bid_prices,
    y=bid_quantities,
    name='Bids',
    marker_color='green',
    opacity=0.6
))

# Add Asks
fig.add_trace(go.Bar(
    x=ask_prices,
    y=ask_quantities,
    name='Asks',
    marker_color='red',
    opacity=0.6
))

fig.update_layout(
    barmode='overlay',
    title='Order Book Liquidity',
    xaxis_title='Price',
    yaxis_title='Quantity',
    legend=dict(x=0.01, y=0.99),
    template='plotly_white'
)

st.plotly_chart(fig, use_container_width=True)
