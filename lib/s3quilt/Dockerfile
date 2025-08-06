FROM python:3.9-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY s3quilt_pure.py __init__.py ./
RUN mkdir -p /usr/local/lib/python3.9/site-packages/s3quilt && \
    cp *.py /usr/local/lib/python3.9/site-packages/s3quilt/

WORKDIR /root