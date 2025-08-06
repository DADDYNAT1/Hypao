from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from PIL import Image
from io import BytesIO
from typing import Optional

# Your local helpers
from compose import remove_bg, add_outline_and_shadow, place_on_base

app = FastAPI(title="PFP Sticker Composer")

# ----------------------------------------------------------------
# CORS for local dev, Vercel previews, and your custom domain
# ----------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://hypao.fun",
        "https://www.hypao.fun",
    ],
    # Allow any *.vercel.app (production + preview deployments)
    allow_origin_regex=r"https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: avoid PIL DecompressionBomb warnings on large inputs
# Set to None (no limit) or a large number you’re comfortable with.
Image.MAX_IMAGE_PIXELS = None


# ----------------------------------------------------------------
# Health & warmup
# ----------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

@app.on_event("startup")
def warm_model_on_start():
    """
    Render free instances can be cold on first call.
    Do a tiny warm-up so the first real user call is faster.
    This is best-effort and non-fatal if it fails.
    """
    try:
        tiny = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        _ = remove_bg(tiny)
    except Exception:
        # Don't crash app on warmup issues
        pass


# ----------------------------------------------------------------
# New: prepare only the cutout (no placement)
# Client composes & drags on <canvas> for lag-free UX
# ----------------------------------------------------------------
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
        data = await sticker.read()
        if not data:
            return JSONResponse({"error": "Empty upload"}, status_code=400)

        src = Image.open(BytesIO(data))
        cut = remove_bg(src)
        cut = add_outline_and_shadow(cut, stroke_px=stroke_px, add_shadow=shadow)

        # Ensure RGBA output
        cut = cut.convert("RGBA")
        buf = BytesIO()
        cut.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ----------------------------------------------------------------
# Old: full compose (kept for compatibility / batch mode)
# Not used for live dragging now.
# ----------------------------------------------------------------
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
    Returns a PNG with the sticker placed on the PFP.
    Useful for batch/automation, but for interactive use the /cutout route + canvas is preferred.
    """
    try:
        base_bytes = await pfp.read()
        st_bytes = await sticker.read()
        if not base_bytes or not st_bytes:
            return JSONResponse({"error": "Missing base or sticker image"}, status_code=400)

        base_img = Image.open(BytesIO(base_bytes)).convert("RGBA")
        st_img   = Image.open(BytesIO(st_bytes))

        cut = remove_bg(st_img)
        cut = add_outline_and_shadow(cut, stroke_px=stroke_px, add_shadow=shadow)

        xy = (x_pct, y_pct) if (x_pct is not None and y_pct is not None) else None
        result = place_on_base(base_img, cut, scale=scale, anchor=anchor, xy_pct=xy)

        result = result.convert("RGBA")
        buf = BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
