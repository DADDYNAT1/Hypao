"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/* ---------- Helpers to load images into <canvas> ---------- */
function loadImageFromFile(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new window.Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

function loadImageFromBlob(blob: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new window.Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

/* --------------------------------------------------------- */

export default function Page() {
  // Inputs
  const [pfpFile, setPfpFile] = useState<File | null>(null);
  const [stickerFile, setStickerFile] = useState<File | null>(null);

  // Loaded images
  const [pfpImg, setPfpImg] = useState<HTMLImageElement | null>(null);
  const [cutoutImg, setCutoutImg] = useState<HTMLImageElement | null>(null);

  // Controls
  const [scale, setScale] = useState<number>(0.30); // 20%–50%, default 30%
  const [anchor, setAnchor] = useState("left_shoulder");
  const [shadow, setShadow] = useState(true);       // applied once during cutout
  const [flipHorizontal, setFlipHorizontal] = useState(false); // NEW: flip state

  // Canvas + dragging
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState<{ dx: number; dy: number }>({ dx: 0, dy: 0 });

  // Sticker position (top-left in canvas pixels)
  const [stickerPos, setStickerPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  /* Redraw whenever inputs change */
  useEffect(() => {
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pfpImg, cutoutImg, scale, stickerPos, flipHorizontal]); // Added flipHorizontal to dependencies

  /* Draw base + sticker on the canvas */
  function draw() {
    if (!pfpImg) return;
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;

    // Use PFP's natural resolution so downloads are crisp
    canvas.width = pfpImg.naturalWidth;
    canvas.height = pfpImg.naturalHeight;

    // Base
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(pfpImg, 0, 0);

    // Sticker with flip support
    if (cutoutImg) {
      const targetW = Math.round(canvas.width * scale);
      const ratio = targetW / cutoutImg.naturalWidth;
      const targetH = Math.round(cutoutImg.naturalHeight * ratio);
      
      ctx.save(); // Save the current context state
      
      if (flipHorizontal) {
        // Flip horizontally around the center of the sticker
        ctx.translate(stickerPos.x + targetW / 2, stickerPos.y + targetH / 2);
        ctx.scale(-1, 1);
        ctx.drawImage(cutoutImg, -targetW / 2, -targetH / 2, targetW, targetH);
      } else {
        ctx.drawImage(cutoutImg, stickerPos.x, stickerPos.y, targetW, targetH);
      }
      
      ctx.restore(); // Restore the context state
    }
  }

  /* Compute a nice starting position by "anchor" */
  function computeAnchorPosition(currentScale: number): { x: number; y: number } {
    const canvas = canvasRef.current!;
    const W = canvas.width || (pfpImg?.naturalWidth ?? 0);
    if (!cutoutImg || !W || !pfpImg) return { x: 0, y: 0 };

    const H = canvas.height || (pfpImg?.naturalHeight ?? 0);
    const targetW = Math.round(W * currentScale);
    const ratio = targetW / cutoutImg.naturalWidth;
    const targetH = Math.round(cutoutImg.naturalHeight * ratio);

    const anchors: Record<string, { cx: number; cy: number }> = {
      left_shoulder:  { cx: Math.round(W * 0.33), cy: Math.round(H * 0.62) },
      right_shoulder: { cx: Math.round(W * 0.67), cy: Math.round(H * 0.62) },
      chest:          { cx: Math.round(W * 0.50), cy: Math.round(H * 0.70) },
      lower_left:     { cx: Math.round(W * 0.25), cy: Math.round(H * 0.78) },
      lower_right:    { cx: Math.round(W * 0.75), cy: Math.round(H * 0.78) },
    };

    const a = anchors[anchor] || anchors.left_shoulder;
    return { x: a.cx - Math.round(targetW / 2), y: a.cy - Math.round(targetH / 2) };
  }

  /* Prepare once: load PFP locally + ask backend to cut out the sticker */
  async function prepare() {
    if (!pfpFile || !stickerFile) {
      alert("Please choose both a PFP and a Hypao image.");
      return;
    }

    // Load PFP locally
    const pfpElement = await loadImageFromFile(pfpFile);
    setPfpImg(pfpElement);

    // Get transparent cutout from backend once
    const fd = new FormData();
    fd.append("sticker", stickerFile);
    fd.append("stroke_px", String(0));       // never outline
    fd.append("shadow", String(shadow));     // bake a soft shadow if checked

    const res = await fetch(`${API_BASE}/cutout`, { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert("Cutout error: " + (err.error || res.statusText));
      return;
    }

    const blob = await res.blob();
    const cutoutElement = await loadImageFromBlob(blob);
    setCutoutImg(cutoutElement);

    // Place at the selected anchor
    setTimeout(() => setStickerPos(computeAnchorPosition(scale)), 0);
  }

  /* Convert mouse coords to canvas pixel coords */
  function getMouseCanvasXY(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const xPct = (e.clientX - rect.left) / rect.width;
    const yPct = (e.clientY - rect.top) / rect.height;
    return { x: xPct * canvas.width, y: yPct * canvas.height };
  }

  /* Drag handlers */
  function onMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!cutoutImg) return;
    const { x, y } = getMouseCanvasXY(e);

    const W = canvasRef.current!.width;
    const targetW = Math.round(W * scale);
    const ratio = targetW / cutoutImg.naturalWidth;
    const targetH = Math.round(cutoutImg.naturalHeight * ratio);

    if (
      x >= stickerPos.x && x <= stickerPos.x + targetW &&
      y >= stickerPos.y && y <= stickerPos.y + targetH
    ) {
      setIsDragging(true);
      setDragOffset({ dx: x - stickerPos.x, dy: y - stickerPos.y });
    }
  }

  function onMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!isDragging || !cutoutImg) return;
    const { x, y } = getMouseCanvasXY(e);
    setStickerPos({ x: Math.round(x - dragOffset.dx), y: Math.round(y - dragOffset.dy) });
  }

  function onMouseUp()    { setIsDragging(false); }
  function onMouseLeave() { setIsDragging(false); }

  /* Keep sticker center fixed when changing size */
  function onScaleChange(next: number) {
    if (!cutoutImg || !pfpImg) { setScale(next); return; }

    const canvas = canvasRef.current!;
    const W = canvas.width || pfpImg.naturalWidth;

    const oldW = Math.round(W * scale);
    const oldH = Math.round(cutoutImg.naturalHeight * (oldW / cutoutImg.naturalWidth));
    const cx = stickerPos.x + oldW / 2;
    const cy = stickerPos.y + oldH / 2;

    const newW = Math.round(W * next);
    const newH = Math.round(cutoutImg.naturalHeight * (newW / cutoutImg.naturalWidth));
    const newX = Math.round(cx - newW / 2);
    const newY = Math.round(cy - newH / 2);

    setScale(next);
    setStickerPos({ x: newX, y: newY });
  }

  /* Toggle flip and auto-switch shoulder anchor */
  function toggleFlip() {
    setFlipHorizontal(!flipHorizontal);
    
    // Auto-switch between left and right shoulder when flipping
    if (anchor === "left_shoulder") {
      setAnchor("right_shoulder");
      setTimeout(() => setStickerPos(computeAnchorPosition(scale)), 0);
    } else if (anchor === "right_shoulder") {
      setAnchor("left_shoulder");
      setTimeout(() => setStickerPos(computeAnchorPosition(scale)), 0);
    }
  }

  /* Download composed PNG directly from the canvas */
  function downloadPNG() {
    const canvas = canvasRef.current!;
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "composite.png";
      a.click();
      URL.revokeObjectURL(url);
    }, "image/png");
  }

  return (
    <>
      {/* Centered logo at the very top */}
      <header className="site-header">
        <Image
          src="/images/HCC.png"
          alt="Hypao Companion Composer"
          width={6000}
          height={800}
          className="site-logo"
          priority
        />
      </header>

      <div className="wrapper">
        <div className="row">
          {/* Left controls */}
          <div className="col card">
            <label>PFP</label>
            <input type="file" accept="image/*" onChange={(e) => setPfpFile(e.target.files?.[0] || null)} />

            <label>Hypao</label>
            <input type="file" accept="image/*" onChange={(e) => setStickerFile(e.target.files?.[0] || null)} />

            <hr />

            <label>Sticker size</label>
            {/* 20% — 50% (no percentage text shown) */}
            <input
              type="range"
              min={0.20}
              max={0.50}
              step={0.01}
              value={scale}
              onChange={(e) => onScaleChange(parseFloat(e.target.value))}
            />

            <label>Anchor (starting position)</label>
            <select value={anchor} onChange={(e) => setAnchor(e.target.value)}>
              <option value="left_shoulder">Left shoulder</option>
              <option value="right_shoulder">Right shoulder</option>
              <option value="chest">Chest</option>
              <option value="lower_left">Lower left</option>
              <option value="lower_right">Lower right</option>
            </select>

            <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
              <input
                type="checkbox"
                checked={shadow}
                onChange={(e) => setShadow(e.target.checked)}
              />
              Add shadow (applied once when you press Compose)
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
              <input
                type="checkbox"
                checked={flipHorizontal}
                onChange={(e) => setFlipHorizontal(e.target.checked)}
              />
              Flip Hypao horizontally
            </label>

            <button className="primary" onClick={prepare} style={{ marginTop: 10 }}>
              Compose
            </button>

            <button 
              onClick={toggleFlip} 
              style={{ marginTop: 10 }}
              disabled={!cutoutImg}
            >
              Flip & Switch Shoulder
            </button>

            <p className="small" style={{ marginTop: 10 }}>
              Tip: drag the sticker on the preview to position it. Use Download PNG below to save.
            </p>
          </div>

          {/* Right preview + download */}
          <div className="col card">
            <div className="preview">
              {pfpImg ? (
                <canvas
                  ref={canvasRef}
                  style={{ width: "100%", height: "auto", cursor: isDragging ? "grabbing" : "grab" }}
                  onMouseDown={onMouseDown}
                  onMouseMove={onMouseMove}
                  onMouseUp={onMouseUp}
                  onMouseLeave={onMouseLeave}
                />
              ) : (
                <span className="small">Your composed image will appear here after you click "Compose".</span>
              )}
            </div>

            <hr />
            <button className="primary" onClick={downloadPNG}>Download PNG</button>
          </div>
        </div>
      </div>
    </>   
  );
}
