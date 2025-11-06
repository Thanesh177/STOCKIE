from flask import Flask, render_template, jsonify, request
from functools import lru_cache
import pandas as pd
import yfinance as yf
import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import numpy as np
import datetime as dt
import boto3, os
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
from botocore.exceptions import NoCredentialsError, ClientError

# Internal modules
from prediction import predict_prices, make_prediction
from web_scrapping import summary, event, data as fetch_news

# --- AWS S3 CONFIG ---
MODEL_PATH = "/tmp/stoc.h5"        # EB temp directory (writable)
S3_BUCKET = "stockie-models"       # replace with your actual bucket name
S3_KEY = "stoc.h5"                 # file name inside the bucket

model = None


def load_model_from_s3():
    """Download and cache the model from S3 once."""
    global model
    if model is None:
        try:
            s3 = boto3.client("s3")
            if not os.path.exists(MODEL_PATH):
                print("⏬ Downloading model from S3...")
                s3.download_file(S3_BUCKET, S3_KEY, MODEL_PATH)
            model = load_model(MODEL_PATH)
            print("✅ Model loaded successfully from S3.")
        except (NoCredentialsError, ClientError, Exception) as e:
            print(f"❌ Error loading model from S3: {e}")
            model = None
    return model


# --- Matplotlib config ---
matplotlib.use('agg')

# --- Flask setup ---
app = Flask(__name__)


# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/middle')
def middle():
    return render_template('mid.html')


@app.route('/fetch_stock/<ticker>', methods=['GET'])
def fetch_stock(ticker):
    """Fetch historical stock data."""
    try:
        df = fetch_stock_data(ticker)
        if df is None or df.empty:
            return jsonify({"error": "No data returned for the given ticker."}), 404
        return jsonify({
            "message": "Stock data fetched successfully.",
            "data": df.to_dict(orient="records")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_stock_data', methods=['POST'])
def get_stock_data():
    """Return last open/close price."""
    try:
        ticker = request.get_json()['ticker']
        data = yf.Ticker(ticker).history(period='1Y')
        if data.empty:
            return jsonify({"error": "No data available."}), 404
        return jsonify({
            'currentPrice': float(data.iloc[-1].Close),
            'openPrice': float(data.iloc[-1].Open)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/predict/<ticker>')
def predict(ticker):
    """Generate and visualize predictions for a ticker."""
    model = load_model_from_s3()
    if model is None:
        return jsonify({"error": "Model not available"}), 500

    actual_prices, predicted_prices = make_prediction(ticker)
    if actual_prices is None or predicted_prices is None:
        return jsonify({"error": "Prediction failed"}), 500

    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(actual_prices)), actual_prices, color='black', label='Actual')
    plt.plot(range(len(actual_prices), len(actual_prices) + len(predicted_prices)),
             predicted_prices, color='green', label='Predicted')
    plt.axvline(x=len(actual_prices) - 1, color='red', linestyle='--', label='Prediction Start')
    plt.title(f'Price Prediction for {ticker}')
    plt.xlabel('Days')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)

    # Encode plot as base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

    stock_data = summary(ticker)
    event_data = event(ticker)
    news_data = fetch_news(ticker)

    return render_template(
        'new.html',
        stock_data=stock_data,
        news=news_data,
        next_day_prediction=predicted_prices[0],
        s=event_data,
        predictions=predicted_prices.tolist(),
        plot_data=plot_data
    )


@app.route('/health')
def health():
    """Elastic Beanstalk health-check endpoint."""
    return jsonify({"status": "running"}), 200


# --- Cached stock data helper ---
@lru_cache(maxsize=100)
def fetch_stock_data(ticker):
    start = dt.datetime(2012, 1, 1)
    end = dt.datetime.now()
    try:
        return yf.download(tickers=[ticker], start=start, end=end, threads=False)
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None


# --- Start app (for local testing only) ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
