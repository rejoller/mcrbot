# syntax=docker/dockerfile:1.3

FROM --platform=$BUILDPLATFORM debian:stable-slim

RUN apt-get update && \
    apt-get install -y wget gnupg2 lsb-release sudo python3 python3-pip python3-venv


WORKDIR /app
COPY requirements.txt .



RUN python3 -m venv venv
ENV PATH="/app/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .


CMD ["python3", "bot.py"]