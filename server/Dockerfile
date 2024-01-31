FROM python:3.12

COPY . /app
WORKDIR /app

RUN echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/backports.list
RUN apt-get update && \
    apt-get install --yes yt-dlp/bookworm-backports && \
    apt-get clean
RUN pip install --no-cache-dir --requirement requirements.txt

ENTRYPOINT ["gunicorn", \
            "--bind=:80", \
            "--worker-class=aiohttp.GunicornWebWorker", \
            "app:build_app"]
