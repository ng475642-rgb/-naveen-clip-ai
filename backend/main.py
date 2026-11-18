import os, uuid, shutil, subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

BASE = Path(__file__).resolve().parent.parent
UPLOADS = BASE / "backend" / "uploads"
OUTPUTS = BASE / "backend" / "outputs"
UPLOADS.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="NAVEEN CLIP AI")

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "Processing failed")[-1800:])
    return p.stdout

def duration_of(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return max(0.0, float(out.strip()))

def make_clip(src: Path, start: float, length: float, dest: Path):
    # Vertical crop, scaled to 1080x1920; uses center crop.
    run(["ffmpeg", "-y", "-ss", str(start), "-i", str(src), "-t", str(length),
         "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dest)])

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "NAVEEN CLIP AI is running"}

@app.post("/api/clip")
async def clip_video(
    video: UploadFile = File(...),
    clip_seconds: int = Form(30),
    clip_count: int = Form(3)
):
    allowed = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, "Please upload an MP4, MOV, MKV, WEBM or M4V video.")
    if clip_seconds not in (15, 30, 45, 60, 90):
        raise HTTPException(400, "Choose a supported clip duration.")
    clip_count = max(1, min(5, clip_count))
    job = uuid.uuid4().hex[:10]
    src = UPLOADS / f"{job}{suffix}"
    try:
        with src.open("wb") as f:
            shutil.copyfileobj(video.file, f)
        total = duration_of(src)
        if total < 3:
            raise HTTPException(400, "This video is too short.")
        actual = min(float(clip_seconds), total)
        # Spread clips across the source video. This is a basic MVP selector,
        # not semantic AI highlight detection.
        starts = []
        if clip_count == 1 or total <= actual + 1:
            starts = [max(0, (total-actual)/2)]
        else:
            usable = max(0, total-actual)
            starts = [usable*i/(clip_count-1) for i in range(clip_count)]
        results = []
        for i, start in enumerate(starts, 1):
            dest = OUTPUTS / f"{job}_clip_{i}.mp4"
            make_clip(src, start, min(actual, total-start), dest)
            results.append({
                "name": f"Clip {i}",
                "url": f"/api/download/{dest.name}",
                "start_seconds": round(start, 1),
                "duration_seconds": round(min(actual, total-start), 1)
            })
        return {"clips": results, "note": "MVP mode: clips are sampled across the video. AI highlight ranking and subtitles need additional model integration."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Video processing failed: {str(e)}")
    finally:
        try: src.unlink(missing_ok=True)
        except Exception: pass

@app.get("/api/download/{filename}")
def download(filename: str):
    # Only serve generated mp4 files from OUTPUTS.
    if "/" in filename or "\\" in filename or not filename.endswith(".mp4"):
        raise HTTPException(404, "File not found")
    path = OUTPUTS / filename
    if not path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)

class FilmRequest(BaseModel):
    prompt: str
    duration_seconds: int = 30
    style: str = "3D animation"

@app.post("/api/film/plan")
def film_plan(req: FilmRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "Enter a story idea.")
    # A useful storyboard draft; actual rendered video requires a connected video-generation provider.
    n = max(3, min(8, round(req.duration_seconds / 8)))
    scenes = []
    for i in range(n):
        scenes.append({
            "scene": i+1,
            "duration_seconds": round(req.duration_seconds/n),
            "visual_prompt": f"{req.style}, cinematic shot. Story idea: {req.prompt.strip()}. Scene {i+1} of {n}; maintain consistent characters and setting.",
            "voiceover": f"Scene {i+1}: continue the story of {req.prompt.strip()}."
        })
    return {
        "title": "Your short-film storyboard",
        "scenes": scenes,
        "status": "storyboard_ready",
        "notice": "This creates a storyboard only. To render actual 3D video, connect a video-generation API and configure its credentials."
    }

app.mount("/", StaticFiles(directory=str(BASE / "frontend"), html=True), name="frontend")
