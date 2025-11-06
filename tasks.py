import yfinance as yf
from celery_config import celery

@celery.task
def fetch_stock_data(ticker):
    """Fetch stock data from Yahoo Finance."""
    start_date = "2022-01-01"
    data = yf.Ticker(ticker).history(start=start_date, period='1y')
    return data.to_dict()  # Serialize DataFrame to JSON-compatible format
