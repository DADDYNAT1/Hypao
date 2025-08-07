from PIL import Image, ImageFilter, ImageOps
from typing import Tuple
import numpy as np
from rembg import remove, new_session

# Use the most precise model for complex game characters
# isnet-general-use is best for precision, u2netp is lighter but still good
session = new_session('isnet-general-use')  # Most precise model

def has_transparency(img: Image.Image) -> bool:
    """Check if an image already has transparency (useful alpha channel)."""
    if img.mode != "RGBA":
        return False
    alpha = img.split()[-1]
    # Check if alpha channel has any non-255 values (actual transparency)
    return any(px < 255 for px in alpha.getdata())

def remove_bg(img: Image.Image) -> Image.Image:
    """
    Use rembg with the most precise model and settings for game characters.
    Automatically handles complex designs like Majora's Mask.
    """
    # Convert to RGBA first
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    # If already has transparency, just return it
    if has_transparency(img):
        return img
    
    # Use the precise session with optimized settings
    # These settings are tuned for maximum precision on game characters
    result = remove(
        img,
        session=session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=270,  # High threshold to keep all character details
        alpha_matting_background_threshold=0,    # Remove all background
        alpha_matting_erode_size=0,             # No erosion to preserve fine details
        post_process_mask=True,                  # Clean up the mask for better edges
        only_mask=False
    )
    
    # Additional cleanup: remove any semi-transparent pixels that shouldn't be there
    result = result.convert("RGBA")
    data = result.getdata()
    new_data = []
    
    for item in data:
        # If pixel is mostly transparent but not fully, make it fully transparent
        # This helps with edge artifacts
        if item[3] < 30:  # Alpha threshold
            new_data.append((item[0], item[1], item[2], 0))
        else:
            new_data.append(item)
    
    result.putdata(new_data)
    return result

def add_outline_and_shadow(im: Image.Image, stroke_px: int = 3, add_shadow: bool = True) -> Image.Image:
    """
    Add a white sticker-style outline and a soft shadow.
    Returns a new RGBA image with a larger canvas to fit the effects.
    """
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    
    alpha = im.split()[-1]
    
    # Stroke (white border)
    stroke = ImageOps.expand(alpha, border=stroke_px, fill=255)
    stroke = stroke.filter(ImageFilter.GaussianBlur(1))
    stroke_img = Image.new("RGBA", stroke.size, (255, 255, 255, 0))
    stroke_img.putalpha(stroke)
    
    # Shadow (soft, slightly larger)
    base = Image.new("RGBA", stroke.size, (0, 0, 0, 0))
    if add_shadow:
        shadow = ImageOps.expand(alpha, border=stroke_px * 2, fill=255)
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        sh_img = Image.new("RGBA", shadow.size, (0, 0, 0, 0))
        # Colorize the alpha mask to black and use as alpha
        sh_img.putalpha(shadow)
        # Blend shadow under everything
        base.alpha_composite(sh_img, (0, 0))
    
    # Put stroke, then original image centered
    base.alpha_composite(stroke_img, (0, 0))
    cx = (stroke_img.width - im.width) // 2
    cy = (stroke_img.height - im.height) // 2
    base.alpha_composite(im, (cx, cy))
    
    return base

def place_on_base(
    base: Image.Image,
    sticker: Image.Image,
    scale: float = 0.25,
    anchor: str = "left_shoulder",
    xy_pct: Tuple[float, float] | None = None,
) -> Image.Image:
    """
    scale: sticker width as a fraction of base width (0.05 - 0.8 is sensible)
    anchor: preset logical spots
    xy_pct: (x%, y%) override in 0..1; centers sticker on that point
    """
    W, H = base.size
    
    # Resize sticker to target width
    target_w = int(W * scale)
    ratio = target_w / sticker.width
    sticker = sticker.resize((target_w, int(sticker.height * ratio)), Image.LANCZOS)
    
    # Manual placement (percent of base image)
    if xy_pct is not None:
        x = int(W * xy_pct[0]) - sticker.width // 2
        y = int(H * xy_pct[1]) - sticker.height // 2
    else:
        anchors = {
            "left_shoulder":  (int(W * 0.33) - sticker.width // 2, int(H * 0.62) - sticker.height // 2),
            "right_shoulder": (int(W * 0.67) - sticker.width // 2, int(H * 0.62) - sticker.height // 2),
            "chest":          (int(W * 0.50) - sticker.width // 2, int(H * 0.70) - sticker.height // 2),
            "lower_left":     (int(W * 0.25) - sticker.width // 2, int(H * 0.78) - sticker.height // 2),
            "lower_right":    (int(W * 0.75) - sticker.width // 2, int(H * 0.78) - sticker.height // 2),
        }
        x, y = anchors.get(anchor, anchors["left_shoulder"])
    
    out = base.convert("RGBA").copy()
    out.alpha_composite(sticker, (x, y))
    return out
