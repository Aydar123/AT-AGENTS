FROM python:3.12-slim

WORKDIR /app/

RUN apt-get update --allow-insecure-repositories
RUN apt-get update && apt-get install -y build-essential wget procps

COPY pyproject.toml .

# RUN pip install poetry && poetry config virtualenvs.create false
RUN pip install poetry
RUN poetry install --no-root

COPY userdata ./userdata
COPY logic ./logic
COPY static ./static
COPY templates ./templates
COPY .env .
COPY data.py .
COPY main.py .