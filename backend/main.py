
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import subprocess, uuid, shutil, os

from faster_whisper import WhisperModel

app = FastAPI(title="NAVEEN CLIP AI")

OUT = Path("backend/outputs")
OUT.mkdir(parents=True, exist_ok=True)

model = None

def get_model():
    global model
    if model is None:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return model

@app.get("/api/health")
def health():
    return {"status": "NAVEEN CLIP AI is running"}

@app.post("/api/clip")
async def clip(video: UploadFile = File(...)):
    ext = Path(video.filename or "").suffix.lower()

    if ext not in [".mp4", ".mov", ".mkv", ".webm"]:
        raise HTTPException(400, "Unsupported video format")

    job = uuid.uuid4().hex[:10]
    source = OUT / f"{job}{ext}"

    try:
        with source.open("wb") as f:
            shutil.copyfileobj(video.file, f)

        if source.stat().st_size > 500_000_000:
            raise HTTPException(413, "Video must be under 500 MB")

        whisper = get_model()
        segments, info = whisper.transcribe(
            str(source), vad_filter=True
        )
        segments = list(segments)

        if not segments:
            raise HTTPException(400, "No speech detected")

        duration = float(subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0", str(source)
        ]).decode().strip())

        candidates = []
        for start in range(0, max(1, int(duration) - 29), 10):
            end = min(start + 60, duration)
            if end - start < 30:
                continue

            text = " ".join(
                s.text for s in segments
                if s.end > start and s.start < end
            ).lower()

            if not text.strip():
                continue

            keywords = [
                "secret", "amazing", "finally", "but then",
                "because", "why", "how", "crazy",
                "never", "best", "worst", "impossible"
            ]

            score = len(text) / 150
            score += sum(k in text for k in keywords) * 2
            candidates.append((score, start, end))

        candidates.sort(reverse=True)
        results = []
        chosen = []

        for score, start, end in candidates:
            if any(abs(start - old) < 60 for old in chosen):
                continue

            chosen.append(start)
            name = f"{job}_clip_{len(results)+1}.mp4"
            target = OUT / name

            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start),
                "-i", str(source), "-t", str(end-start),
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac", "-movflags", "+faststart",
                str(target)
            ], check=True, stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL)

            results.append({
                "name": name,
                "url": "/outputs/" + name,
                "score": round(score, 2)
            })

            if len(results) == 5:
                break

        return {"message": "Clips created", "clips": results}

    finally:
        source.unlink(missing_ok=True)

app.mount(
    "/outputs",
    StaticFiles(directory=str(OUT)),
    name="outputs"
)

app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)
