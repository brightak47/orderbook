import streamlit as st
from binance.client import Client

# Streamlit App Title
st.title("🔍 Binance API Connectivity Test")

# Section 1: Public Endpoint Test (No API Key Required)
st.subheader("Public API Test: Ping and Order Book")

# Test Public API (Ping)
def test_public_api():
    try:
        client = Client()  # Public client, no API keys required
        client.ping()
        order_book = client.get_order_book(symbol="BTCUSDT", limit=5)
        return {"status": "success", "order_book": order_book}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Button to Test Public API
if st.button("Test Public API"):
    with st.spinner("Testing Binance public API..."):
        result = test_public_api()
        if result["status"] == "success":
            st.success("✅ Public API connection successful!")
            st.write("Sample Order Book Data (Top 5):")
            st.json(result["order_book"])
        else:
            st.error(f"❌ Failed to connect to Binance Public API: {result['message']}")

# Divider
st.markdown("---")

# Section 2: Authenticated API Test (Requires API Key and Secret)
st.subheader("Authenticated API Test")

# Sidebar Input for API Key and Secret
st.sidebar.header("Binance API Configuration")
api_key = st.sidebar.text_input("API Key", help="Enter your Binance API Key", key="api_key")
api_secret = st.sidebar.text_input("API Secret", type="password", help="Enter your Binance API Secret", key="api_secret")

# Test Authenticated API
def test_authenticated_api(api_key, api_secret):
    try:
        client = Client(api_key, api_secret)  # Authenticated client
        client.ping()  # Test connection
        account_info = client.get_account()
        return {"status": "success", "account_info": account_info}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Button to Test Authenticated API
if st.sidebar.button("Test Authenticated API"):
    if not api_key or not api_secret:
        st.sidebar.error("❌ API Key and Secret are required for this test.")
    else:
        with st.spinner("Testing authenticated Binance API..."):
            result = test_authenticated_api(api_key, api_secret)
            if result["status"] == "success":
                st.success("✅ Authenticated API connection successful!")
                st.write("Account Information:")
                st.json(result["account_info"])
            else:
                st.error(f"❌ Failed to connect to Binance Authenticated API: {result['message']}")

# Footer
st.markdown("---")
st.caption("Powered by Binance API | Built with Streamlit")
