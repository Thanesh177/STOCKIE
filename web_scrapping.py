from flask import Flask, render_template, jsonify, request
import pandas as pd
import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup
import yfinance as yf
import matplotlib


matplotlib.use('agg')  # Set the backend to 'agg'

import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
from sklearn.preprocessing import MinMaxScaler


# Helper to extract all <p> tags from a section with a specific class
def web_div(web_content, class_path):
    web_divs = web_content.find_all('section', {'class': class_path})
    try:
        p_tags = web_divs[0].find_all('p')
        texts = [p.get_text(strip=True) for p in p_tags]
    except IndexError:
        texts = []
    return texts

def summary(stock_code):
    url = f'https://finance.yahoo.com/quote/{stock_code}'
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        overview = {}

        description_block = soup.find('div', class_='description yf-1ja4ll8')
        if description_block:
            desc = description_block.find('p')
            overview["Description"] = desc.text.strip() if desc else "N/A"

            link_tag = description_block.find('a', href=True)
            overview["Website"] = link_tag['href'].strip() if link_tag else "N/A"

        info_sections = soup.find_all('div', class_='infoSection yf-1ja4ll8')
        for section in info_sections:
            label = section.find('h3')
            value = section.find('p')
            if label and value:
                overview[label.get_text(strip=True)] = value.get_text(strip=True)

        return overview if overview else {"error": "No overview data found."}

    except Exception as e:
        return {"error": str(e)}

# Store results here

# Helper function to extract data from specific divs
def web(web_content, class_path):
    web = web_content.find_all('div', {'class': class_path})
    try:
        p = web[0].find_all('span')
        texts = [ps.get_text() for ps in p]
    except IndexError:
        texts = []
    return texts


def event(stock_code):
    url = f"https://finance.yahoo.com/quote/{stock_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find all statistic blocks (each is a <li>)
        stat_items = soup.find_all('li')

        summary_data = {}
        for item in stat_items:
            label = item.find('span', class_='label')
            value = item.find('span', class_='value')

            if label and value:
                summary_data[label.text.strip()] = value.text.strip()

        return summary_data if summary_data else {"error": "No data found"}

    except requests.exceptions.ConnectionError:
        return {"error": "Connection error"}

# Extract news articles, filtering out unwanted content
def ne(web_content):
    articles = web_content.find_all('article')
    headlines = []

    for article in articles:
        h3 = article.find('h3')
        a = article.find('a', href=True)

        if h3 and a:
            headlines.append({
                "title": h3.get_text(strip=True),
                "url": a['href']
            })

    return headlines

# Fetch market-related news
def data(ticker):
    url = f'https://query1.finance.yahoo.com/v1/finance/search?q={ticker}'
    headers = {'User-Agent': 'Mozilla/5.0'}

    response = requests.get(url, headers=headers)
    data = response.json()

    news = []
    if 'news' in data:
        for item in data['news']:
            news.append({
                'title': item.get('title', 'No Title'),
                'url': item.get('link', '#')
            })
    return news