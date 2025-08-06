from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from PIL import Image
from io import BytesIO
from typing import Optional
from compose import remove_bg, add_outline_and_shadow, place_on_base

app = FastAPI(title="PFP Sticker Composer")

# --- CORS ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://hypao.vercel.app",      # Your main Vercel deployment
    "https://*.vercel.app",           # All Vercel preview deployments
    "https://hypao.fun",              # If you plan to use custom domain
    "https://www.hypao.fun",          # www version of custom domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: Add a root endpoint for easy checking
@app.get("/")
def root():
    return {"message": "PFP Sticker API is running!", "docs": "/docs"}

# -------- New: prepare only the cutout (no placement) --------
@app.post("/cutout")
async def cutout(
    sticker: UploadFile = File(..., description="Sticker image; background will be removed"),
    stroke_px: int = Form(0),          # default: no outline
    shadow: bool = Form(True),         # optional soft shadow baked into sticker
):
    """
    Returns RGBA PNG of the sticker with background removed and effects applied.
    Use this once, then do all movement client-side on a <canvas>.
    """
    try:
        src = Image.open(BytesIO(await sticker.read()))
        cut = remove_bg(src)
        cut = add_outline_and_shadow(cut, stroke_px=stroke_px, add_shadow=shadow)
        buf = BytesIO()
        cut.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# -------- Old: full compose (kept for compatibility / batch mode) --------
@app.post("/compose")
async def compose(
    pfp: UploadFile = File(..., description="Base PFP image"),
    sticker: UploadFile = File(..., description="Sticker image (bg will be removed)"),
    scale: float = Form(0.25),
    anchor: str = Form("left_shoulder"),
    x_pct: Optional[float] = Form(None),
    y_pct: Optional[float] = Form(None),
    stroke_px: int = Form(0),           # default: no outline
    shadow: bool = Form(True),
):
    """
    Returns a PNG with the sticker placed on the PFP. (Not used for live dragging now.)
    """
    try:
        base_img = Image.open(BytesIO(await pfp.read())).convert("RGBA")
        st_img = Image.open(BytesIO(await sticker.read()))
        cut = remove_bg(st_img)
        cut = add_outline_and_shadow(cut, stroke_px=stroke_px, add_shadow=shadow)
        xy = (x_pct, y_pct) if (x_pct is not None and y_pct is not None) else None
        result = place_on_base(base_img, cut, scale=scale, anchor=anchor, xy_pct=xy)
        buf = BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/health")
def health():
    return {"ok": True}
