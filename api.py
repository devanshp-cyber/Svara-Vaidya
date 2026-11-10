"""
api.py — FastAPI wrapper for compare_chant.py
Run:  uvicorn api:app --host 0.0.0.0 --port 10000
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
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


@app.get("/mantras")
def list_mantras():
    """Returns available mantras and their metadata."""
    cc = get_compare_chant()
    return JSONResponse(content=list(cc.MANTRAS.values()))


@app.get("/reference-audio")
def reference_audio(mantra_id: str = "ganesha"):
    """Serves the reference audio for frontend audio slicing/playback."""
    cc = get_compare_chant()
    minfo = cc.MANTRAS.get(mantra_id, cc.MANTRAS["ganesha"])
    audio_path = os.path.join(BASE_DIR, minfo["audio_file"])
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Reference audio not found for {mantra_id}")
    return FileResponse(audio_path, media_type="audio/wav", filename=minfo["audio_file"])


@app.post("/analyze")
def analyze(
    file: UploadFile = File(...),
    mantra_id: Optional[str] = Query(None),
    mantra_id_form: Optional[str] = Form(None, alias="mantra_id")
):
    """
    Upload user chant audio → returns full feedback JSON for the selected mantra.
    """
    chosen_mantra = "ganesha"
    if isinstance(mantra_id_form, str) and mantra_id_form.strip():
        chosen_mantra = mantra_id_form.strip().lower()
    elif isinstance(mantra_id, str) and mantra_id.strip():
        chosen_mantra = mantra_id.strip().lower()
    print(f"--> Received /analyze request with file: {file.filename}, mantra: {chosen_mantra} (form={mantra_id_form}, query={mantra_id})", flush=True)
    allowed = (".wav", ".mp3", ".mpeg", ".mpga", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".mov", ".mp4", ".m4v", ".3gp")
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail=f"Audio file required: {allowed}")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    print(f"--> Wrote upload to temporary file: {tmp_path}", flush=True)

    try:
        cc = get_compare_chant()
        print(f"--> Starting cc.analyze_chant for mantra: {chosen_mantra}...", flush=True)
        result = cc.analyze_chant(tmp_path, mantra_id=chosen_mantra)
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
