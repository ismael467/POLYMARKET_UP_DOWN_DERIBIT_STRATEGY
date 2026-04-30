FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

COPY data_collector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY btc_pricer/ btc_pricer/
COPY scripts/ scripts/
COPY data_collector/ data_collector/
COPY data_collector/telegram_alerts.py ./

RUN mkdir -p data_collector/results

CMD ["sh", "-c", "python -m data_collector.collector & python telegram_alerts.py"]
