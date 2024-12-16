import streamlit as st
from binance.client import Client
import logging

# Logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Streamlit Header
st.title("🔍 Binance Client Initialization Test")

# Sidebar Input for API Key and Secret
st.sidebar.header("Binance API Configuration")
api_key = st.sidebar.text_input("API Key", help="Enter your Binance API Key")
api_secret = st.sidebar.text_input("API Secret", type="password", help="Enter your Binance API Secret")

# Function to Test Binance Client Initialization
def test_client(api_key, api_secret):
    try:
        client = Client(api_key, api_secret)
        client.ping()
        return "Client initialized successfully. Connection to Binance API is active."
    except Exception as e:
        return f"Error initializing Binance client: {e}"

# Button to Trigger Test
if st.sidebar.button("Test Binance Client"):
    if not api_key or not api_secret:
        st.error("API Key and Secret are required to test the Binance client.")
    else:
        result = test_client(api_key, api_secret)
        if "successfully" in result:
            st.success(result)
        else:
            st.error(result)
