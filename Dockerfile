FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ⬇️ FIX: copy files and folders to the right places
COPY RT_price.py web_scrapping.py ./
COPY templates ./templates
COPY static ./static

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "RT_price:app"]