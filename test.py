import streamlit as st
from binance.client import Client

# Streamlit App Title
st.title("🔍 Binance API UK Connectivity Test")

# Sidebar for API Key and Secret Input
st.sidebar.header("Binance API Configuration")
api_key = st.sidebar.text_input("API Key", help="Enter your Binance API Key", key="api_key")
api_secret = st.sidebar.text_input("API Secret", type="password", help="Enter your Binance API Secret", key="api_secret")

# Initialize Binance Client
def test_binance_connection(api_key, api_secret):
    try:
        # Initialize the Binance client
        client = Client(api_key, api_secret)
        
        # Test the connection using the ping endpoint
        client.ping()
        
        # Fetch public order book data as a further test
        order_book = client.get_order_book(symbol="BTCUSDT", limit=5)
        return {"status": "success", "order_book": order_book}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Button to Test Binance API Connectivity
if st.sidebar.button("Test Binance API"):
    if not api_key or not api_secret:
        st.error("API Key and Secret are required to test the Binance API.")
    else:
        result = test_binance_connection(api_key, api_secret)
        if result["status"] == "success":
            st.success("✅ Connection to Binance API successful!")
            st.write("Sample Order Book Data:")
            st.json(result["order_book"])  # Display order book data
        else:
            st.error(f"❌ Failed to connect to Binance API: {result['message']}")
