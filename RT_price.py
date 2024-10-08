
from flask import Flask, render_template, jsonify, request
import pandas as pd
import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup
import yfinance as yf
from keras.initializers import glorot_uniform
import matplotlib

matplotlib.use('agg')  # Set the backend to 'agg'

from io import BytesIO
import base64

import numpy as np
import matplotlib.pyplot as plt
import pandas_datareader as web
import datetime as dt
import pickle
from keras.models import load_model

from sklearn.preprocessing import MinMaxScaler

app = Flask(__name__)
    

def fetch_stock_data(ticker):
    # Download historical stock data
    start = dt.datetime(2012, 1, 1)
    end = dt.datetime.now()  # Set end date to the current day
    data = yf.download(tickers=[ticker], start=start, end=end)
    return data

def make_prediction(ticker, prediction_day=30):
    data = fetch_stock_data(ticker)

    # Scaling the data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))

    # Prepare test data
    test_start = dt.datetime(2020, 1, 1)
    test_end = dt.datetime.now()
    test_data = yf.download(tickers=[ticker], start=test_start, end=test_end)
    actual_prices = test_data['Close'].values

    total_dataset = pd.concat((data['Close'], test_data['Close']), axis=0)

    model_inputs = total_dataset[len(total_dataset) - len(test_data) - prediction_day:].values
    model_inputs = model_inputs.reshape(-1, 1)
    model_inputs = scaler.transform(model_inputs)

    real_data = [model_inputs[len(model_inputs) - prediction_day:len(model_inputs), 0]]
    real_data = np.array(real_data)
    real_data = np.reshape(real_data, (real_data.shape[0], real_data.shape[1], 1))

    # Make predictions
    prediction = model.predict(real_data)
    predicted_prices = scaler.inverse_transform(prediction)

    return actual_prices, predicted_prices

#page 2
def web_div(web_content, class_path):
    web_div = web_content.find_all('section', {'class':class_path})
    try:
        p = web_div[0].find_all('p')
        texts = [ps.get_text() for ps in p]
    except IndexError:
        texts=[]
    return texts


def summary(stock_code):
    url = f'https://ca.finance.yahoo.com/quote/{stock_code}/profile'
    headers = {
    'User-agent': 'Mozilla/5.0',
    }
    try:
        r = requests.get(url, headers=headers)
        web_content = BeautifulSoup(r.text, 'html.parser')
        texts = web_div(web_content, 'quote-sub-section Mt(30px)')
        if texts != []:
            summ = texts[0]
        else:
            summ = []
    except ConnectionError:
        summ = None

    return summ


def web(web_content, class_path):
    web = web_content.find_all('section', {'class':class_path})
    try:
        p = web[0].find_all('div')
        texts = [ps.get_text() for ps in p]
    except IndexError:
        texts=[]
    return texts


def event(stock_code):
    url = f'https://ca.finance.yahoo.com/quote/{stock_code}/profile'  # Correctly format the URL
    headers = {
        'User-agent': 'Mozilla/5.0',
    }
    try:
        r = requests.get(url, headers=headers)
        web_content = BeautifulSoup(r.text, 'html.parser')
        texts = web(web_content, 'Pb(30px) smartphone_Px(20px)')
        if texts:
            summ = texts[0]
            summ = summ.split(':')
        else:
            summ = ["nill"]  # Handle case where no data is found
    except ConnectionError:
        summ = ["nill"]  # Handle case where the request fails

    return summ



def ne(web_content, custom_stop_words=None):
    articles = web_content.find_all('article')
    texts = []
    if custom_stop_words is None:
        custom_stop_words = set()  # Default to empty set if custom_stop_words is not provided
    if articles:
        for article in articles:
            spans_in_article = article.find_all('span')
            texts.extend([span.get_text() for span in spans_in_article if span.get_text() not in custom_stop_words])
            paragraphs_in_article = article.find_all('p')
            texts.extend([p.get_text() for p in paragraphs_in_article if p.get_text() not in custom_stop_words])
    return texts


def data(stock_code):
    url = 'https://www.barrons.com/topics/markets?mod=BOL_TOPNAV'
    headers = {
        'User-agent': 'Mozilla/5.0',
    }
    r = requests.get(url, headers=headers)
    web_content = BeautifulSoup(r.text, 'html.parser')
    
    # Define custom stop words
    custom_stop_words = {'Long read', '3 min read', '2 min read', '3 min read', '4 min read', '4 min read', '1 min read'}  # Add or remove words as needed
    
    texts = ne(web_content, custom_stop_words)
    if texts:
        summ = texts
    else:
        summ = None
    return summ


def predict_prices(company):

    start = dt.datetime(2012, 1, 1)
    end = dt.datetime.now()  # Set end date to the current day

    # Download historical stock data
    dataa = yf.download(tickers=[company], start=start, end=end)

    scaler = MinMaxScaler(feature_range=(0, 1))

    scaled_data = scaler.fit_transform(dataa['Close'].values.reshape(-1, 1))

    prediction_day = 30

    test_start = dt.datetime(2020, 1, 1)
    test_end = dt.datetime.now()

    test_data = yf.download(tickers=[company], start=test_start, end=test_end)
    actual_prices = test_data['Close'].values

    total_dataset = pd.concat((dataa['Close'], test_data['Close']), axis=0)




    model_inputs = total_dataset[len(total_dataset) - len(test_data) - prediction_day:].values
    model_inputs = model_inputs.reshape(-1, 1)
    model_inputs = scaler.transform(model_inputs)

    real_data = [model_inputs[len(model_inputs) - prediction_day:len(model_inputs), 0]]  # Adjusted indexing
    real_data = np.array(real_data)
    real_data = np.reshape(real_data, (real_data.shape[0], real_data.shape[1], 1))

    x_test = []
    for x in range(prediction_day, len(model_inputs)):
        x_test.append(model_inputs[x - prediction_day:x, 0])

    x_test = np.array(x_test)
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

    predicted_prices = model.predict(x_test)

# Inverse transform the predicted prices
    predicted_prices = scaler.inverse_transform(predicted_prices)

    return predicted_prices



#model
model = load_model('stoc.h5')


@app.route('/')
def index():
    return render_template('index.html')  

@app.route('/middle')
def middle():
    return render_template('mid.html')  


@app.route('/new/<ticker>')
def second_page(ticker):
    # Make predictions
    actual_prices, predicted_prices = make_prediction(ticker)
    predict_price = predict_prices(ticker)

    # Fetch additional data
    stock_data = summary(ticker)
    event_data = event(ticker)
    news_data = data(ticker)

    # Plotting the actual vs predicted prices
    plt.figure(figsize=(10, 6))  # Optional: Set figure size
    plt.plot(actual_prices, color='black', label='Actual Prices')
    plt.plot(predict_price, color='green', label='Predicted Prices')
    plt.legend()
    plt.title(f'Price Prediction for {ticker}')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.grid(True)

    # Save plot to a BytesIO object
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()  # Close the plot to free up resources

    # Encode plot image to base64
    plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Render the template with the plot and prediction results
    return render_template('new.html', stock_data=stock_data, news=news_data, s=event_data, predictions=predicted_prices, plot_data=plot_data)

'''
@app.route('/')
def third():
    predictions = []
    prediction = model.predict(real_data)  # Make sure real_data is defined correctly
    predictionn = scaler.inverse_transform(prediction)  # Assuming you're scaling back predictions
    predictions.append(predictionn)
    return render_template('third.html',predictions=predictions )
'''

@app.route ('/get_stock_data', methods=['POST'])
def get_stock_data():
    ticker = request.get_json()['ticker']
    data = yf.Ticker(ticker).history(period='1Y')
    return jsonify({
        'currentPrice': data.iloc[-1].Close, 
        'openPrice': data.iloc[-1].Open
    })


if __name__ == '__main__':
    app.run(debug=True)
    


'''
Stock = ['Shop', 'AAPL', 'AMZN']
while (True):
    info = []
    col =[]
    time_stamp = datetime.datetime.now() - datetime.timedelta(hours=13)
    time_stamp = time_stamp.strftime('%Y-%m-%d %H:%M:%S')
    for stock_code in Stock:
        stock_code, price, change, per, volume, close, one_year_target = real_time_price(stock_code)
        info.append(stock_code)
        info.append(price)
        info.append(change)
        info.append(per)
        info.append(volume)
        info.append(close)
        info.append(one_year_target)
    col = [time_stamp]
    col.extend(info)
    df = pd.DataFrame(col)
    df = df.T
    df.to_csv(str(time_stamp[0:11])+'stock data.csv', mode = 'a', header = False)
    print(col)
'''

