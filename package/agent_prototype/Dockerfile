FROM python:3.12-slim

WORKDIR /app/

RUN apt-get update --allow-insecure-repositories
RUN apt-get install -y build-essential gcc libc6-dev wget git
RUN apt-get update && apt-get install -y procps

COPY pyproject.toml .

RUN pip install poetry
RUN poetry install

COPY data ./data
COPY logic ./logic
COPY static ./static
COPY templates ./templates
COPY data.py .
COPY main.py .
