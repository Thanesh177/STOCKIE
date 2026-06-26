# STOCKIE - AI-Powered Stock Market Prediction & Analysis

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue.svg" />
  <img src="https://img.shields.io/badge/Flask-Web%20Framework-green.svg" />
  <img src="https://img.shields.io/badge/TensorFlow-Deep%20Learning-orange.svg" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
</p>

##  Overview

**STOCKIE** is an AI-powered web application that provides **real-time stock market monitoring, financial news aggregation, and stock price prediction** through a user-friendly dashboard.

The application combines live market data, machine learning, and interactive visualizations to help users analyze stock performance and make informed investment decisions.

---

##  Features

*  Real-time stock price monitoring
*  AI-powered stock price prediction using LSTM
*  Historical stock price visualization
*  Latest financial news aggregation
*  Company summary and market information
*  Live price updates using AJAX
*  Responsive web interface
*  Color-coded gain/loss indicators
*  Automatic stock price refresh

---

# Project Architecture

```
                +----------------------+
                |      User Browser    |
                +----------+-----------+
                           |
                    HTML/CSS/JavaScript
                           |
                     AJAX Requests
                           |
                  +--------▼--------+
                  |     Flask API    |
                  +--------+---------+
                           |
        +------------------+------------------+
        |                  |                  |
        ▼                  ▼                  ▼
 Stock API         Web Scraping         AI Prediction
(Alpha Vantage)   (Yahoo/Barrons)      (TensorFlow LSTM)
        |                  |                  |
        +------------------+------------------+
                           |
                    Data Processing
                           |
                     Matplotlib Charts
                           |
                     Rendered Dashboard
```

---

# Technologies Used

## Backend

* Python
* Flask
* Gunicorn
* Requests
* BeautifulSoup
* Pandas
* NumPy

## Machine Learning

* TensorFlow
* Keras
* LSTM Neural Network
* Scikit-learn
* MinMaxScaler

## Frontend

* HTML5
* CSS3
* JavaScript
* jQuery
* AJAX

## Data Sources

* Alpha Vantage API
* Yahoo Finance
* Barron's News

## Visualization

* Matplotlib

---

# Machine Learning Model

The application uses a **Long Short-Term Memory (LSTM)** neural network trained on historical stock prices.

### Workflow

1. Historical stock prices are collected.
2. Data is normalized using MinMaxScaler.
3. Time-series sequences are generated.
4. LSTM predicts future prices.
5. Predictions are compared against historical trends.
6. Results are displayed as interactive charts.

---

# Project Structure

```
STOCKIE/
│
├── static/
│   ├── app.js
│   ├── style.css
│   └── images/
│
├── templates/
│   ├── index.html
│   ├── mid.html
│   └── new.html
│
├── prediction.py
├── web_scrapping.py
├── RT_price.py
├── stoc.h5
├── requirements.txt
├── Procfile
└── README.md
```

---

# Installation

## Clone the Repository

```bash
git clone https://github.com/yourusername/STOCKIE.git

cd STOCKIE
```

---

## Create a Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
python RT_price.py
```

Open:

```
http://127.0.0.1:5000
```

---

# Deployment

The application is configured for deployment using **Render**.

### Procfile

```
web: gunicorn RT_price:app
```

---

# Screenshots

```
Home Page

Live Stock Dashboard

Prediction Graph

News Section

Company Summary
```

*(Replace this section with actual screenshots once available.)*

---

# Future Improvements

* User authentication
* Portfolio management
* Watchlists
* Cryptocurrency support
* Sentiment analysis from news
* Email alerts
* Technical indicators (MACD, RSI, Bollinger Bands)
* Candlestick charts
* Multiple AI prediction models
* Cloud database integration

---

# Learning Outcomes

This project demonstrates practical experience with:

* Full-stack web development
* REST API integration
* Web scraping
* Deep learning using TensorFlow
* Time-series forecasting
* Data visualization
* AJAX-based frontend updates
* Deployment on cloud platforms
* Machine learning model integration into web applications

---

# Acknowledgements

* Alpha Vantage
* Yahoo Finance
* Barron's
* TensorFlow
* Flask
* Scikit-learn
* Matplotlib

---

# License

This project is licensed under the MIT License.

---

# Author

**Thanesh N. T.**

* GitHub: **[https://github.com/Thanesh177](https://github.com/Thanesh177)**
* LinkedIn: *(Add your LinkedIn profile here if you'd like)*

---

##  If you found this project useful, consider giving it a star!
