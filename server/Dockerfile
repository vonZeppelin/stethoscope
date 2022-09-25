FROM python:3.10-slim

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["gunicorn", \
            "--bind=:443", \
            "--keyfile=/etc/letsencrypt/live/api.stethoscope.lbogdanov.dev/privkey.pem", \
            "--certfile=/etc/letsencrypt/live/api.stethoscope.lbogdanov.dev/fullchain.pem", \
            "--worker-class=aiohttp.GunicornWebWorker", \
            "app:build_app"]
