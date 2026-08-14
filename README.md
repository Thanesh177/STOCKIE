# STOCKIE

Production-ready Flask frontend for stock quotes, news, and an external prediction service.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
export PREDICTION_API_URL=https://your-service.example.com/predict
gunicorn --config gunicorn.conf.py RT_price:app
```

Open `http://localhost:8080`. Run tests with `python -m unittest discover -s tests -v`.

## Container

```bash
docker build -t stockie .
docker run --rm -p 8080:8080 -e PREDICTION_API_URL=https://your-service.example.com/predict stockie
```

The container runs as a non-root user and exposes `/health` for platform health checks.

## Production checklist

- Set `PREDICTION_API_URL`; there is intentionally no baked-in production endpoint.
- Terminate TLS at the hosting platform or load balancer.
- Send logs to the platform log service and alert on 5xx responses.
- Restrict the prediction service so only this application can call it, if supported.
- Add uptime monitoring for `/health` and a synthetic test for a known ticker.
- Treat predictions as informational only; validate the model independently before financial use.
