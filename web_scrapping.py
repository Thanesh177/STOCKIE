from flask import Flask, render_template, jsonify, request
import pandas as pd
import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup
import yfinance as yf
from keras.initializers import glorot_uniform
import matplotlib
from prediction import predict_prices
from prediction import make_prediction

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

# Helper function to extract specific sections of web content
def web_div(web_content, class_path):
    web_div = web_content.find_all('section', {'class': class_path})
    try:
        p = web_div[0].find_all('p')
        texts = [ps.get_text() for ps in p]
    except IndexError:
        texts = []
    return texts
"""
# Fetch summary of a stock from Yahoo Finance
def summary(stock_code):
    url = f'https://ca.finance.yahoo.com/quote/{stock_code}/'
    web_content = fetch_page(url)
    if not web_content:
        return None

    texts = web_div(web_content, 'card yf-1d08kze')
    return texts[0] if texts else "No summary available"
    """

def summary(stock_code):
    url = f'https://ca.finance.yahoo.com/quote/{stock_code}/'  
    headers = {
    'User-agent': 'Mozilla/5.0',
    }
    try:
        r = requests.get(url, headers=headers)
        web_content = BeautifulSoup(r.text, 'html.parser')
        texts = web_div(web_content, 'card yf-1d08kze')
        if texts != []:
            summ = texts[0]
        else:
            summ = []
    except ConnectionError:
        summ = None

    return summ

# Helper function to extract data from specific divs
def web(web_content, class_path):
    web = web_content.find_all('div', {'class': class_path})
    try:
        p = web[0].find_all('span')
        texts = [ps.get_text() for ps in p]
    except IndexError:
        texts = []
    return texts

# Fetch event-related data for a stock
def event(stock_code):
    url = f'https://ca.finance.yahoo.com/quote/{stock_code}'
    headers = {
        'User-agent': 'Mozilla/5.0',
    }
    try:
        r = requests.get(url, headers=headers)
        web_content = BeautifulSoup(r.text, 'html.parser')
        texts = web(web_content, 'container yf-1jj98ts')
        if texts:
            summ = texts
        else:
            summ = ["nill"]
    except ConnectionError:
        summ = ["nill"]

    chunked_summ = [summ[i:i + 2] for i in range(0, len(summ), 2)]
    return chunked_summ

# Extract news articles, filtering out unwanted content
def ne(web_content, custom_stop_words=None):
    articles = web_content.find_all('article')
    texts = []
    if custom_stop_words is None:
        custom_stop_words = set()
    if articles:
        for article in articles:
            spans_in_article = article.find_all('span')
            texts.extend([span.get_text() for span in spans_in_article if span.get_text() not in custom_stop_words])
            paragraphs_in_article = article.find_all('p')
            texts.extend([p.get_text() for p in paragraphs_in_article if p.get_text() not in custom_stop_words])
    return texts

# Fetch market-related news
def data(stock_code=None):
    url = 'https://www.barrons.com/topics/markets?mod=BOL_TOPNAV'
    headers = {
        'User-agent': 'Mozilla/5.0',
    }
    r = requests.get(url, headers=headers)
    web_content = BeautifulSoup(r.text, 'html.parser')

    custom_stop_words = {'Long read', '3 min read', '2 min read', '4 min read', '1 min read'}
    texts = ne(web_content, custom_stop_words)
    if texts:
        summ = texts
    else:
        summ = None
    return summ

