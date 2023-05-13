FROM python:3.11

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir --requirement requirements.txt

ENTRYPOINT ["gunicorn", \
            "--bind=:443", \
            "--certfile=/etc/letsencrypt/live/lbogdanov.dev/fullchain.pem", \
            "--keyfile=/etc/letsencrypt/live/lbogdanov.dev/privkey.pem", \
            "--worker-class=aiohttp.GunicornWebWorker", \
            "app:build_app"]
