import librosa
import numpy as np
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REFERENCE_AUDIO = os.environ.get("REFERENCE_AUDIO", os.path.join(BASE_DIR, "mantra.wav"))

print(f"Loading reference audio: {REFERENCE_AUDIO}")
# Load audio at native sampling rate (16kHz)
audio, sr = librosa.load(REFERENCE_AUDIO, sr=None)
print(f"Loaded audio with sample rate {sr} Hz and duration {len(audio)/sr:.2f}s")

# -------------------------
# 1. Pitch detection
# -------------------------
print("Extracting pitch contour via pyin...")
pitch, voiced_flag, voiced_probs = librosa.pyin(
    audio,
    sr=sr,
    fmin=librosa.note_to_hz('C2'),
    fmax=librosa.note_to_hz('C7')
)

pitch_clean = np.nan_to_num(pitch)

# -------------------------
# 2. Tempo detection
# -------------------------
print("Detecting tempo and beat tracking...")
tempo, beats = librosa.beat.beat_track(y=audio, sr=sr)
tempo_val = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)

# -------------------------
# 3. MFCC extraction
# -------------------------
print("Computing MFCC features...")
mfccs = librosa.feature.mfcc(
    y=audio,
    sr=sr,
    n_mfcc=13
)

# Convert numpy arrays → list (required for JSON)
features = {
    "mantra_text": "त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात्",
    "mantra_text_iast": "tryambakam yajāmahe sugandhim puṣṭivardhanam urvārukamiva bandhanān mṛtyormukṣīya māmṛtāt",
    "pitch_contour": pitch_clean.tolist(),
    "tempo": tempo_val,
    "beat_times": beats.tolist(),               
    "duration": len(audio) / sr,               
    "mfcc": mfccs.tolist()
}

# -------------------------
# Save features
# -------------------------
output_path = os.path.join(BASE_DIR, "reference_features.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(features, f, indent=4, ensure_ascii=False)

print(f"Reference features saved successfully to {output_path}!")
