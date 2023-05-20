FROM python:3.11

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir --requirement requirements.txt

ENTRYPOINT ["gunicorn", \
            "--bind=:80", \
            "--worker-class=aiohttp.GunicornWebWorker", \
            "app:build_app"]
