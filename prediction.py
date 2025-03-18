import datetime as dt
import pandas as pd
import numpy as np
import yfinance as yf
import time
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# Load the pre-trained model
try:
    model = load_model('stoc.h5')
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

def fetch_stock_data(ticker, start_date="2012-01-01", max_retries=3):
    """Fetch historical stock data with retries."""
    for attempt in range(max_retries):
        try:
            data = yf.download(tickers=ticker, start=start_date, end=dt.datetime.now())

            if data.empty:
                print(f"Warning: No data found for {ticker}. Attempt {attempt+1}/{max_retries}")
                time.sleep(2)  # Wait before retrying
                continue

            return data  # Successfully fetched data

        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}. Attempt {attempt+1}/{max_retries}")
            time.sleep(2)  # Wait before retrying

    return None  # Return None after all retries fail

def prepare_model_inputs(data, prediction_days=30):
    """Prepare scaled model inputs for the LSTM model."""
    scaler = MinMaxScaler(feature_range=(0, 1))

    if len(data) < prediction_days:
        print(f"Error: Not enough data to make predictions. Required: {prediction_days}, Available: {len(data)}")
        return None, None

    scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))

    model_inputs = scaled_data[-prediction_days:]
    model_inputs = model_inputs.reshape(1, prediction_days, 1)  # Reshape for LSTM model

    return model_inputs, scaler

def make_prediction(ticker, prediction_days=30):
    data = fetch_stock_data(ticker)
    if data is None or data.empty:
        print(f"No data available for {ticker}.")
        return None, None

    model_inputs, scaler = prepare_model_inputs(data, prediction_days)
    if model_inputs is None:
        return None, None

    prediction = model.predict(model_inputs)
    predicted_price = scaler.inverse_transform(prediction)

    if predicted_price is None or len(predicted_price) == 0:
        print("Prediction failed.")
        return None, None

    return data['Close'].values, predicted_price

def predict_prices(company, prediction_days=30):
    """Generate multiple-day predictions using an LSTM model."""
    if model is None:
        print("Error: Model not loaded.")
        return None

    data = fetch_stock_data(company)
    if data is None or data.empty:
        print(f"Error: No data available for {company}.")
        return None

    model_inputs, scaler = prepare_model_inputs(data, prediction_days)
    if model_inputs is None:
        return None

    predictions = []
    for day in range(prediction_days):
        try:
            prediction = model.predict(model_inputs)
            predicted_price = scaler.inverse_transform(prediction)[0, 0]
            predictions.append(predicted_price)

            # Correctly shift model inputs for next prediction
            model_inputs[0, :-1, 0] = model_inputs[0, 1:, 0]  # Shift left
            model_inputs[0, -1, 0] = scaler.transform([[predicted_price]])[0, 0]  # Insert new prediction

        except Exception as e:
            print(f"Error in day {day + 1} prediction: {e}")
            break

    return np.array(predictions) if predictions else None