import streamlit as st
import pandas as pd
import numpy as np
import asyncio
import json
from binance import AsyncClient, BinanceSocketManager
from datetime import datetime, timedelta
import plotly.graph_objs as go
from threading import Thread

# -----------------------------
# Configuration and Constants
# -----------------------------
SYMBOL = 'BTCUSDT'  # Trading pair
DEPTH = 20  # Number of price levels
DAYS_AVG_VOLUME = 30  # Days to calculate average daily volume

# Initialize session state
if 'avg_daily_volume' not in st.session_state:
    st.session_state.avg_daily_volume = 0

if 'bids' not in st.session_state:
    st.session_state.bids = []

if 'asks' not in st.session_state:
    st.session_state.asks = []

if 'signal' not in st.session_state:
    st.session_state.signal = 'Neutral'

# -----------------------------
# Helper Functions
# -----------------------------

async def fetch_avg_daily_volume(symbol: str, days: int = 30):
    """Fetches the average daily trading volume for a given symbol over a specified number of days."""
    client = await AsyncClient.create()
    klines = await client.get_historical_klines(symbol, AsyncClient.KLINE_INTERVAL_1DAY, f"{days} day ago UTC")
    await client.close_connection()
    volumes = [float(kline[5]) for kline in klines]  # Volume is the 6th element
    avg_volume = sum(volumes) / len(volumes)
    return avg_volume

def calculate_liquidity(bids, asks, levels, avg_daily_volume):
    """Calculates liquidity metrics based on the top 'levels' bids and asks."""
    selected_bids = bids[:levels]
    selected_asks = asks[:levels]
    
    liquidity_bid = sum([float(q) for _, q in selected_bids])
    liquidity_ask = sum([float(q) for _, q in selected_asks])
    
    liquidity_bid_pct = (liquidity_bid / avg_daily_volume) * 100
    liquidity_ask_pct = (liquidity_ask / avg_daily_volume) * 100
    
    return liquidity_bid, liquidity_ask, liquidity_bid_pct, liquidity_ask_pct

def generate_signal(liquidity_bid_pct, liquidity_ask_pct, threshold):
    """Generates Buy/Sell/Neutral signals based on liquidity percentages and a threshold."""
    if liquidity_bid_pct > threshold and liquidity_ask_pct <= threshold:
        return 'Buy'
    elif liquidity_ask_pct > threshold and liquidity_bid_pct <= threshold:
        return 'Sell'
    else:
        return 'Neutral'

async def listen_order_book(symbol, depth, levels, threshold):
    """Listens to the Binance WebSocket for order book updates and processes liquidity signals."""
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    socket = bm.depth_socket(symbol, depth)
    
    async with socket as s:
        while True:
            res = await s.recv()
            bids = res.get('bids', [])
            asks = res.get('asks', [])
            
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

            await asyncio.sleep(0.5)  # Control update frequency

    await client.close_connection()

def run_asyncio(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_order_book(SYMBOL, DEPTH, st.session_state.price_levels, st.session_state.threshold))

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
if st.session_state.avg_daily_volume == 0:
    st.session_state.avg_daily_volume = asyncio.run(fetch_avg_daily_volume(SYMBOL, DAYS_AVG_VOLUME))
    st.sidebar.write(f"**Avg Daily Volume ({DAYS_AVG_VOLUME} days):** {st.session_state.avg_daily_volume:.2f}")

# Start WebSocket Listener in a Separate Thread
if 'thread' not in st.session_state:
    loop = asyncio.new_event_loop()
    thread = Thread(target=run_asyncio, args=(loop,), daemon=True)
    thread.start()
    st.session_state.thread = thread

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
