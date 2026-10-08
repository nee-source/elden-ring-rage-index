# Image for the pipeline steps (ingestion + transform). The orchestrator runs
# the same image, one step per task.
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion/ ingestion/
COPY transform/ transform/
COPY sql/ sql/
COPY seeds/ seeds/

# raw files land here; docker-compose mounts ./data so they survive the container
ENV RAW_DATA_DIR=/app/data/raw
# no CMD: docker-compose (and later the orchestrator) says which step to run
