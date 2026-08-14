import datetime as dt
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 10
HEADERS = {"User-Agent": "STOCKIE/1.0"}
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
FINNHUB_CACHE_SECONDS = 300
finnhub_cache: dict[tuple[str, str], tuple[float, object]] = {}


def load_local_finnhub_config() -> None:
    """Load the ignored local Finnhub key without overriding deployed configuration."""
    env_path = Path(__file__).with_name(".env")
    if not env_path.is_file() or os.environ.get("FINNHUB_API_KEY"):
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "FINNHUB_API_KEY":
            os.environ[key.strip()] = value.strip().strip('"').strip("'")
            return


load_local_finnhub_config()
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")


def _finnhub_get(endpoint: str, ticker: str, **params):
    if not FINNHUB_API_KEY:
        raise RuntimeError("Finnhub is not configured")

    cache_key = (endpoint, ticker)
    now = dt.datetime.now().timestamp()
    cached = finnhub_cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]

    response = requests.get(
        f"{FINNHUB_BASE_URL}/{endpoint}",
        params={"symbol": ticker, "token": FINNHUB_API_KEY, **params},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError("Finnhub returned an error")
    finnhub_cache[cache_key] = (now + FINNHUB_CACHE_SECONDS, payload)
    return payload


def _format_market_cap(value):
    try:
        return f"${float(value):,.0f}M"
    except (TypeError, ValueError):
        return "N/A"


def _finnhub_summary(ticker):
    profile = _finnhub_get("stock/profile2", ticker)
    if not profile or not profile.get("name"):
        raise RuntimeError("Finnhub profile unavailable")
    return {
        "Company": profile.get("name", "N/A"),
        "Industry": profile.get("finnhubIndustry", "N/A"),
        "Exchange": profile.get("exchange", "N/A"),
        "Country": profile.get("country", "N/A"),
        "Market Capitalization": _format_market_cap(profile.get("marketCapitalization")),
        "Website": profile.get("weburl", "N/A"),
    }


def _finnhub_metrics(ticker):
    payload = _finnhub_get("stock/metric", ticker, metric="all")
    metric = payload.get("metric", {}) if isinstance(payload, dict) else {}
    if not metric:
        raise RuntimeError("Finnhub metrics unavailable")
    mappings = {
        "P/E Ratio (TTM)": "peBasicExclExtraTTM",
        "EPS (TTM)": "epsBasicExclExtraItemsTTM",
        "Beta": "beta",
        "52 Week High": "52WeekHigh",
        "52 Week Low": "52WeekLow",
        "Dividend Yield": "dividendYieldIndicatedAnnual",
        "10 Day Avg. Volume": "10DayAverageTradingVolume",
    }
    return {label: metric.get(key, "N/A") for label, key in mappings.items()}


def _finnhub_news(ticker):
    today = dt.date.today()
    payload = _finnhub_get(
        "company-news", ticker,
        **{"from": (today - dt.timedelta(days=14)).isoformat(), "to": today.isoformat()},
    )
    if not isinstance(payload, list):
        raise RuntimeError("Finnhub news unavailable")
    return [
        {"title": item.get("headline", "No Title"), "url": item.get("url", "#")}
        for item in payload[:8]
        if item.get("headline") and item.get("url")
    ]


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
    try:
        return _finnhub_summary(stock_code)
    except Exception:
        pass

    url = f'https://finance.yahoo.com/quote/{stock_code}'
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        overview = {}

        description_block = soup.find('div', class_='description yf-z5w6qk')
        if description_block:
            desc = description_block.find('p')
            overview["Description"] = desc.text.strip() if desc else "N/A"

            link_tag = description_block.find('a', href=True)
            if link_tag:
                href = link_tag.get('href')
                overview["Website"] = href.strip() if isinstance(href, str) else "N/A"
            else:
                overview["Website"] = "N/A"

        info_sections = soup.find_all('div', class_='infoSection yf-z5w6qk')
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
    try:
        return _finnhub_metrics(stock_code)
    except Exception:
        pass

    url = f"https://finance.yahoo.com/quote/{stock_code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
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
    try:
        return _finnhub_news(ticker)
    except Exception:
        pass

    url = f'https://query1.finance.yahoo.com/v1/finance/search?q={ticker}'
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()

    news = []
    if 'news' in payload:
        for item in payload['news'][:20]:
            news.append({
                'title': item.get('title', 'No Title'),
                'url': item.get('link', '#')
            })
    return news
