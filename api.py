"""
api.py — FastAPI wrapper for compare_chant.py
Run:  uvicorn api:app --host 0.0.0.0 --port 10000
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import tempfile, shutil, os, sys, traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── compare_chant is imported lazily on first request ──
# This lets uvicorn bind the port immediately, before heavy libs load.
compare_chant = None

app = FastAPI(title="Svara Vaidya API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_compare_chant():
    """Import compare_chant once, on first use."""
    global compare_chant
    if compare_chant is None:
        print("Loading compare_chant module (first request)...")
        import compare_chant as _cc
        compare_chant = _cc
        print("compare_chant loaded.")
    return compare_chant


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/warmup")
def warmup():
    """
    Optional: call this endpoint once after deploy to trigger model loading.
    Returns immediately — loading happens in background via first /analyze call.
    """
    return {"status": "warming up — send an /analyze request to fully load models"}


@app.get("/reference-audio")
def reference_audio():
    """Serves the reference mantra.wav for frontend audio slicing/playback."""
    audio_path = os.path.join(BASE_DIR, "mantra.wav")
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Reference audio not found")
    return FileResponse(audio_path, media_type="audio/wav", filename="mantra.wav")


@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    """
    Upload user chant audio → returns full feedback JSON.
    """
    print(f"--> Received /analyze request with file: {file.filename}", flush=True)
    allowed = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm")
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail=f"Audio file required: {allowed}")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    print(f"--> Wrote upload to temporary file: {tmp_path}", flush=True)

    try:
        cc = get_compare_chant()
        print("--> Starting cc.analyze_chant...", flush=True)
        result = cc.analyze_chant(tmp_path)
        print("--> cc.analyze_chant completed successfully!", flush=True)
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        err_msg = str(e) if str(e).strip() else f"{type(e).__name__}: Audio format decoding or analysis failed"
        raise HTTPException(status_code=500, detail=err_msg)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                print("--> Unlinked tmp file", flush=True)
            except Exception as ue:
                print(f"--> Could not unlink tmp file: {ue}", flush=True)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, log_level="info")
