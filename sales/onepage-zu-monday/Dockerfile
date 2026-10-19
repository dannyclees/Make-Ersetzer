# Build-Kontext ist die Repo-Wurzel:
#   docker build -f sales/onepage-zu-monday/Dockerfile .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY sales/onepage-zu-monday/requirements.txt /app/flow/requirements.txt
RUN pip install --no-cache-dir -r /app/flow/requirements.txt

COPY shared /app/shared
COPY sales/onepage-zu-monday /app/flow

WORKDIR /app/flow
ENV PYTHONPATH=/app
CMD exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 4 --timeout 120 main:app
