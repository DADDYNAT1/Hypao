FROM python:3.11-slim

# System deps needed by Pillow/onnxruntime/rembg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# If requirements.txt is at repo root; change the path if yours is different
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code (adjust path if your backend lives elsewhere)
COPY . .

# Optional but reduces cold-start + avoids runtime download
ENV U2NET_HOME=/app/models
RUN mkdir -p /app/models
# Pull and cache the default rembg model during build
RUN python - <<'PY'
from rembg import new_session
new_session("isnet-general-use")
print("rembg model cached")
PY

ENV PORT=8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
