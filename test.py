import streamlit as st

from binance.client import Client

API_KEY = "your_actual_api_key"
API_SECRET = "your_actual_api_secret"

try:
    client = Client(API_KEY, API_SECRET)
    client.ping()
    print("Binance client initialized successfully.")
except Exception as e:
    print(f"Error initializing Binance client: {e}")
