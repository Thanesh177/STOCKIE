import datetime as dt
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from keras.models import load_model
import boto3, os
from botocore.exceptions import NoCredentialsError, ClientError

# --- AWS S3 CONFIG ---
S3_BUCKET = "stockie-models"
S3_KEY = "stoc.h5"
MODEL_PATH = "/tmp/stoc.h5"
model = None


def load_model_from_s3():
    """Download and cache model from S3."""
    global model
    if model is None:
        try:
            s3 = boto3.client("s3")
            if not os.path.exists(MODEL_PATH):
                print("⏬ Downloading model from S3...")
                s3.download_file(S3_BUCKET, S3_KEY, MODEL_PATH)
            model = load_model(MODEL_PATH)
            print("✅ Model loaded successfully from S3.")
        except (NoCredentialsError, ClientError) as e:
            print(f"❌ S3 error: {e}")
            model = None
    return model


def fetch_stock_data(ticker, start_date="2012-01-01"):
    """Fetch stock data or fallback to cached CSV."""
    try:
        data = yf.download(tickers=[ticker], start=start_date, end=dt.datetime.now())
        if not data.empty:
            data.to_csv(f"{ticker}_data.csv")
            return data
    except Exception as e:
        print(f"⚠️ Error fetching data: {e}")
    try:
        return pd.read_csv(f"{ticker}_data.csv", index_col=0, parse_dates=True)
    except FileNotFoundError:
        print("❌ No cached data found.")
        return None


def prepare_model_inputs(data, prediction_days=30):
    """Scale the data and create input sequences for LSTM."""
    scaler = MinMaxScaler(feature_range=(0, 1))
    if len(data) < prediction_days:
        print(f"⚠️ Not enough data ({len(data)} rows). Need {prediction_days}.")
        return None, None
    scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))
    model_inputs = scaled_data[-prediction_days:].reshape(1, prediction_days, 1)
    return model_inputs, scaler


def predict_prices(ticker, prediction_days=30):
    """Predict next prices iteratively."""
    model = load_model_from_s3()
    if model is None:
        print("❌ Model not loaded.")
        return None

    data = fetch_stock_data(ticker)
    if data is None or data.empty:
        print("❌ No stock data.")
        return None

    model_inputs, scaler = prepare_model_inputs(data, prediction_days)
    if model_inputs is None:
        return None

    predictions = []
    for _ in range(prediction_days):
        prediction = model.predict(model_inputs)
        predicted_price = scaler.inverse_transform(prediction)[0, 0]
        predictions.append(predicted_price)
        model_inputs[0, :-1, 0] = model_inputs[0, 1:, 0]
        model_inputs[0, -1, 0] = scaler.transform(np.array([[predicted_price]]))[0, 0]

    return np.array(predictions)


def make_prediction(ticker, prediction_days=30):
    """Return recent actual prices and predicted prices."""
    data = fetch_stock_data(ticker)
    if data is None or data.empty:
        return None, None

    actual = data['Close'].values[-prediction_days:]
    predicted = predict_prices(ticker, prediction_days)
    return actual, predicted
