from flask import Flask, render_template, jsonify, request
from functools import lru_cache
import pandas as pd
import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup
import yfinance as yf
from keras.initializers import glorot_uniform
import matplotlib
from io import BytesIO
import base64
import numpy as np
import matplotlib.pyplot as plt
import pandas_datareader as web
import datetime as dt
import pickle
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

from prediction import predict_prices
from prediction import make_prediction

from web_scrapping import summary, event, data

matplotlib.use('agg')  # Set the backend to 'agg'

app = Flask(__name__)

# Model loading
model = load_model('stoc.h5')


@app.route('/fetch_stock/<ticker>', methods=['GET'])
def fetch_stock(ticker):
    try:
        data = fetch_stock_data(ticker)
        if data.empty:
            return jsonify({"error": "No data available for the given ticker."}), 404
        return jsonify({"message": "Stock data fetched successfully.", "data": data.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/check_status/<task_id>', methods=['GET'])
def check_status(task_id):
    return jsonify({"error": "Task monitoring functionality not implemented."})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/middle')
def middle():
    return render_template('mid.html')

@app.route('/new/<ticker>')
def second_page(ticker):
    try:
        actual_prices, predicted_prices = make_prediction(ticker)
        predict_price = predict_prices(ticker)

        stock_data = summary(ticker)
        event_data = event(ticker)
        news_data = data(ticker)

        plt.figure(figsize=(10, 6))
        plt.plot(actual_prices, color='black', label='Actual Prices')
        plt.plot(predict_price, color='green', label='Predicted Prices')
        plt.legend()
        plt.title(f'Price Prediction for {ticker}')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.grid(True)

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()

        plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return render_template('new.html', 
            stock_data=stock_data, 
            news=news_data, 
            s=event_data, 
            predictions=predicted_prices, 
            plot_data=plot_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_stock_data', methods=['POST'])
def get_stock_data():
    try:
        ticker = request.get_json()['ticker']
        data = yf.Ticker(ticker).history(period='1Y')
        if data.empty:
            return jsonify({"error": "No data available for the given ticker."}), 404
        return jsonify({
            'currentPrice': data.iloc[-1].Close,
            'openPrice': data.iloc[-1].Open
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@lru_cache(maxsize=100)
def fetch_stock_data(ticker):
    start = dt.datetime(2012, 1, 1)
    end = dt.datetime.now()
    return yf.download(tickers=[ticker], start=start, end=end)

if __name__ == '__main__':
    app.run(debug=True)
