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
import queue  # Import queue for thread-safe communication

# -----------------------------
# Configuration and Constants
# -----------------------------
SYMBOL = 'BTCUSDT'          # Trading pair
DEPTH = 20                  # Number of price levels
DAYS_AVG_VOLUME = 30        # Days to calculate average daily volume

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

# Initialize a queue for thread-safe communication
if 'data_queue' not in st.session_state:
    st.session_state.data_queue = queue.Queue()

# -----------------------------
# Helper Functions
# -----------------------------

def fetch_avg_daily_volume_sync(symbol: str, days: int = 30, retries: int = 3, delay: int = 5):
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
            logging.info(f"Fetched average daily volume for {symbol}: {avg_volume} (type: {type(avg_volume)})")
            return avg_volume
        except Exception as e:
            logging.error(f"Attempt {attempt} - Error fetching average daily volume: {e}")
            if attempt < retries:
                st.warning(f"Attempt {attempt} failed. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                st.error(f"Failed to fetch average daily volume after {retries} attempts.")
                return 0.0  # Ensure that 0.0 is returned as a float

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

def listen_order_book(symbol, depth, levels, threshold, data_queue):
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

            # Put the data into the queue
            data_queue.put({
                'bids': bids[:levels],
                'asks': asks[:levels],
                'signal': signal,
                'liquidity_bid': liquidity_bid,
                'liquidity_ask': liquidity_ask,
                'liquidity_bid_pct': liquidity_bid_pct,
                'liquidity_ask_pct': liquidity_ask_pct
            })

            logging.info(f"Updated Liquidity - Bid: {liquidity_bid} ({liquidity_bid_pct:.2f}%), Ask: {liquidity_ask} ({liquidity_ask_pct:.2f}%) - Signal: {signal}")
        except Exception as e:
            logging.error(f"Error processing WebSocket message: {e}")

    def on_error(ws, error):
        logging.error(f"WebSocket error: {error}")
        data_queue.put({'error': f"WebSocket encountered an error: {error}"})

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

def run_order_book_listener(symbol, depth, levels, threshold, data_queue):
    """Runs the WebSocket listener."""
    listen_order_book(symbol, depth, levels, threshold, data_queue)
