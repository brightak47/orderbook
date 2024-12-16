import streamlit as st
import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
import os
import time

# -----------------------------
# Load Environment Variables
# -----------------------------

print(f"API_KEY: {os.getenv('BINANCE_API_KEY')}")
print(f"API_SECRET: {os.getenv('BINANCE_API_SECRET')}")


# -----------------------------
# Initialize Binance Client
# -----------------------------
client = Client(API_KEY, API_SECRET)

# -----------------------------
# Helper Functions
# -----------------------------

def fetch_order_book(symbol: str, limit: int = 10):
    """Fetch real-time order book data for a given symbol."""
    try:
        order_book = client.get_order_book(symbol=symbol, limit=limit)
        bids = order_book["bids"]  # Top bid prices and quantities
        asks = order_book["asks"]  # Top ask prices and quantities
        return bids, asks
    except Exception as e:
        raise RuntimeError(f"Error fetching order book data: {e}")

def fetch_historical_data(symbol: str, interval: str = '1d', limit: int = 30):
    """Fetch historical candlestick data for a given symbol."""
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "Open time", "Open", "High", "Low", "Close", "Volume",
            "Close time", "Quote asset volume", "Number of trades",
            "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"
        ])
        # Convert timestamp columns to readable dates
        df["Open time"] = pd.to_datetime(df["Open time"], unit="ms")
        df["Close time"] = pd.to_datetime(df["Close time"], unit="ms")
        return df[["Open time", "Open", "High", "Low", "Close", "Volume"]]
    except Exception as e:
        raise RuntimeError(f"Error fetching historical data: {e}")

def calculate_liquidity_imbalance(bids, asks):
    """Calculate liquidity imbalance and generate trading signals."""
    try:
        bid_liquidity = sum(float(bid[1]) for bid in bids)
        ask_liquidity = sum(float(ask[1]) for ask in asks)
        imbalance = bid_liquidity - ask_liquidity

        signal = "Neutral"
        if imbalance > 0.1 * bid_liquidity:  # Example threshold: 10%
            signal = "Buy"
        elif imbalance < -0.1 * ask_liquidity:
            signal = "Sell"

        return bid_liquidity, ask_liquidity, imbalance, signal
    except Exception as e:
        raise RuntimeError(f"Error calculating liquidity imbalance: {e}")

def display_order_book(bids, asks, symbol):
    """Display the real-time order book in the Streamlit app."""
    st.subheader(f"Order Book for {symbol}")

    # Convert bids and asks to DataFrames
    bids_df = pd.DataFrame(bids, columns=["Price", "Quantity"])
    asks_df = pd.DataFrame(asks, columns=["Price", "Quantity"])

    # Format price and quantity as floats
    bids_df["Price"] = bids_df["Price"].astype(float)
    bids_df["Quantity"] = bids_df["Quantity"].astype(float)
    asks_df["Price"] = asks_df["Price"].astype(float)
    asks_df["Quantity"] = asks_df["Quantity"].astype(float)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Bids**")
        st.dataframe(bids_df.style.format({"Price": "{:.2f}", "Quantity": "{:.6f}"}))

    with col2:
        st.write("**Asks**")
        st.dataframe(asks_df.style.format({"Price": "{:.2f}", "Quantity": "{:.6f}"}))

def display_historical_chart(df, symbol):
    """Display a candlestick chart for historical data."""
    import plotly.graph_objs as go

    st.subheader(f"Historical Data for {symbol}")
    fig = go.Figure(data=[go.Candlestick(
        x=df["Open time"],
        open=df["Open"].astype(float),
        high=df["High"].astype(float),
        low=df["Low"].astype(float),
        close=df["Close"].astype(float)
    )])
    fig.update_layout(
        title=f"{symbol} Candlestick Chart",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Streamlit App Layout
# -----------------------------

st.set_page_config(page_title="Binance Trading App", layout="wide")

st.title("🔍 Binance Real-Time Trading App")
