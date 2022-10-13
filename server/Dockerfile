FROM python:3.10-slim

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["gunicorn", \
            "--bind=:443", \
            "--certfile=/etc/letsencrypt/live/api.stethoscope.lbogdanov.dev/fullchain.pem", \
            "--keyfile=/etc/letsencrypt/live/api.stethoscope.lbogdanov.dev/privkey.pem", \
            "--worker-class=aiohttp.GunicornWebWorker", \
            "app:build_app"]
