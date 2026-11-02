FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 STATE_FILE=/data/state.json TZ=America/Mexico_City
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot ./bot
COPY main.py .
CMD ["python", "main.py"]
