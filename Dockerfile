FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ⬇️ FIX: copy files and folders to the right places
COPY RT_price.py web_scrapping.py ./
COPY templates ./templates
COPY static ./static

COPY gunicorn.conf.py ./
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl --fail http://127.0.0.1:8080/health || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "RT_price:app"]
