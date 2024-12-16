import streamlit as st
import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
import os

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()  # Load from .env file
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# -----------------------------
# Initialize Binance Client
# -----------------------------
client = Client(API_KEY, API_SECRET)

# -----------------------------
# Helper Functions
# -----------------------------

def fetch_order_book(symbol: str, limit: int = 10):
    """
    Fetch real-time order book data for a given symbol.
    :param symbol: Trading pair symbol (e.g., BTCUSDT)
    :param limit: Number of price levels to fetch (default: 10)
    :return: Bids and asks
    """
    try:
        order_book = client.get_order_book(symbol=symbol, limit=limit)
        bids = order_book["bids"]  # Top bid prices and quantities
        asks = order_book["asks"]  # Top ask prices and quantities
        return bids, asks
    except Exception as e:
        raise RuntimeError(f"Error fetching order book data: {e}")

def display_order_book(bids, asks, symbol):
    """
    Display the real-time order book in the Streamlit app.
    :param bids: List of bid price levels
    :param asks: List of ask price levels
    :param symbol: Trading pair symbol
    """
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

# -----------------------------
# Streamlit App Layout
# -----------------------------

st.set_page_config(page_title="Binance Real-Time Order Book", layout="wide")

st.title("🔍 Binance Real-Time Order Book")

# Sidebar for User Input
st.sidebar.header("Order Book Settings")
symbol = st.sidebar.text_input("Enter Symbol", value="BTCUSDT", help="Enter the trading pair symbol (e.g., BTCUSDT)")
limit = st.sidebar.slider("Price Levels", min_value=5, max_value=50, value=10, help="Select the number of price levels to display")

# Fetch and Display Order Book Data
try:
    bids, asks = fetch_order_book(symbol, limit)
    display_order_book(bids, asks, symbol)
except Exception as e:
    st.error(f"Unable to fetch order book data: {e}")

# -----------------------------
# Footer
# -----------------------------
st.markdown("---")
st.caption("Powered by Binance API | Built with Streamlit")
