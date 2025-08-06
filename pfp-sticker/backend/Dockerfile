FROM python:3.11-slim

# System deps for Pillow/onnxruntime/rembg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# === install Python deps (path is from REPO ROOT) ===
COPY pfp-sticker/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# === copy backend app code only ===
COPY pfp-sticker/backend/ .

# Cache the rembg model at build-time (optional but helps)
ENV U2NET_HOME=/app/models
RUN mkdir -p /app/models && python - <<'PY'
from rembg import new_session
new_session("isnet-general-use")
print("rembg model cached")
PY

ENV PORT=8000
# If your entry file is app.py and FastAPI app is `app`, keep this.
# If it's main.py, change to: "uvicorn", "main:app", ...
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
