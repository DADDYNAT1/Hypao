FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install deps inline (avoids requirements.txt)
RUN pip install --no-cache-dir \
    "fastapi==0.111.0" \
    "uvicorn[standard]==0.30.0" \
    "pillow==10.4.0" \
    "rembg==2.0.57" \
    "onnxruntime==1.16.3" \
    "numpy<2" \
    "python-multipart==0.0.9"

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]

