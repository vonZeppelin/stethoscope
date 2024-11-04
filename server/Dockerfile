FROM python:3.13

COPY . /app
WORKDIR /app

RUN apt-get update && \
    apt-get install --yes ffmpeg && \
    apt-get clean
RUN pip install --no-cache-dir --requirement requirements.txt

ENTRYPOINT ["gunicorn", \
            "--bind=:80", \
            "--worker-class=aiohttp.GunicornWebWorker", \
            "app:build_app"]
