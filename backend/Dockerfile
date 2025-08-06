FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire backend folder (includes app.py, compose.py, requirements.txt)
COPY . .

# Install dependencies AFTER files are copied, so requirements.txt is definitely present
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
