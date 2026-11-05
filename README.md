# Svara Vaidya · स्वर वैद्य
### "Duolingo for Mantras" Hybrid Phonetic & Vedic Chanting Evaluation System

**Svara Vaidya** is an intelligent, dual-layer audio evaluation engine for Vedic Sanskrit mantra chanting. Built specifically for the **Mahā Mṛtyuñjaya Mantra** (Rigveda 7.59.12), the system pairs a 4-dimensional macro acoustic assessment pipeline with a fine-grained, word-by-word and phoneme-level evaluation module.

---

## The Target Mantra
> **त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात्**  
> *tryambakaṃ yajāmahe sugandhiṃ puṣṭivardhanam urvārukamiva bandhanān mṛtyormukṣīya māmṛtāt*

The 8 target words analyzed by the system:
1. **त्र्यम्बकं** (*tryambakam*) — Tri-consonant conjunct onset `/tr/` & labial anusvāra closure
2. **यजामहे** (*yajāmahe*) — Short vowel `/ya/` vs. long vowel `/jā/` duration ratio
3. **सुगन्धिं** (*sugandhim*) — Voiced dental aspirated stop `/dh/` breath release
4. **पुष्टिवर्धनम्** (*puṣṭivardhanam*) — Voiceless retroflex sibilant + stop cluster `/ṣṭ/`
5. **उर्वारुकमिव** (*urvārukamiva*) — Short vowel `/u/` vs. long vowel `/vā/` duration ratio
6. **बन्धनान्** (*bandhanān*) — Medial aspirated dental `/dh/` & terminal lengthened vowel `/nān/`
7. **मृत्योर्मुक्षीय** (*mṛtyormukṣīya*) — Velar + retroflex conjunct `/kṣ/` & long `/ī/`
8. **मामृतात्** (*māmṛtāt*) — Initial long vowel `/mā/` vs. vocalic `/ṛ/` & final stop closure

---

## Dual-Layer Architecture

```
User Audio Recording (WAV/MP3/M4A)
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (/analyze)                │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌───────────────────────────────┐ ┌───────────────────────────┐
│  Layer 1: Macro Svara Vaidya   │ │ Layer 2: Micro Phonetics  │
│  - Ucchāraṇa (MMS-1B CTC ASR) │ │ - Local DTW Warping Path  │
│  - Svara (Pitch & Accent Zone)│ │ - Word Match Score (0-100)│
│  - Laya (Onset Envelope DTW)  │ │ - Vowel Length Ratio (±30)│
│  - Nāda (Z-Normalized MFCCs)  │ │ - Consonant Aspiration/   │
│  - Aggregate Resonance Score  │ │   Retroflexion/Conjuncts  │
└──────────────┬────────────────┘ └───────────┬───────────────┘
               │                              │
               └──────────────┬───────────────┘
                              │
                              ▼
           JSON Response & Duolingo-style UI Cards
  [Green = Acceptable | Orange = Review | Gray = Inconclusive]
```

### 1. Macro Evaluation Pipeline (4 Dimensions)
- **Ucchāraṇa (उच्चारण — Pronunciation):** Evaluated using Facebook MMS-1B (`facebook/mms-1b-all`) multilingual speech model with Devanagari CTC decoding and character/word/syllable sequence matching.
- **Svara (स्वर — Pitch & Vedic Accent):** Estimates F0 contour via Librosa pYIN, detects Vedic accent zones (*udātta*, *anudātta*, *svarita*), classifies intra-syllable pitch trajectories, and matches pitch slopes.
- **Laya (लय — Rhythm & Tempo):** Extracts syllable onset strength envelopes and computes rhythm alignment against the reference using Dynamic Time Warping (DTW).
- **Nāda (नाद — Voice Quality):** Computes z-score normalized MFCCs + delta spectral features with DTW distance to measure vocal resonance and timbre fidelity.
- **Resonance Score:** Weighted aggregate proficiency metric mapped to traditional Vedic performance tiers (*Uttama*, *Madhyama*, *Ādi*, *Prārambhika*).

### 2. Micro Phonetic & Word-Level Module (`phonetic_evaluator.py`)
- Reuses the global MFCC DTW warping path to map user time frames directly to reference word spans without redundant computation.
- Computes individual `word_match_score` (0-100%) for each of the 8 words.
- Checks short-to-long vowel duration ratios (target ratio 1.3× to 3.5× with a ±30% tolerance).
- Measures high-frequency energy ratio and spectral centroid shifts for aspiration (`/dh/`), retroflex clusters (`/ṣṭ/`), and conjuncts (`/tr/`, `/kṣ/`).
- Includes safe-failure logic: outputs `acceptable`, `review`, or `inconclusive` (if duration < 30ms or alignment confidence < 0.40).

---

## Repository Structure

```
Swara-Vaidya/
├── api.py                            # FastAPI server entry point (/analyze, /health)
├── compare_chant.py                  # Core audio analysis & macro feedback engine
├── phonetic_evaluator.py             # Word-level & phoneme-level evaluation module
├── create_reference.py               # Generates reference_features.json from mantra.wav
├── generate_ref_annotations.py       # Auto-detects 8 word boundaries & phonetic spans
├── mantra.wav                        # Clean 16-second reference audio (Mahā Mṛtyuñjaya)
├── reference_features.json           # Precomputed reference pitch, MFCC, tempo features
├── ref_maha_mrityunjay.json          # Reference timestamps & phonetic contrast schema
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Container configuration
├── Procfile                          # Deployment web process definition
├── frontend/                         # Modern React + Vite frontend
│   ├── src/
│   │   ├── App.jsx                   # Main UI with Duolingo-style word cards & tabs
│   │   └── main.jsx
│   └── package.json
└── README.md
```

---

## Local Setup & Quickstart

### Prerequisites
- **Python 3.10+** (64-bit)
- **Node.js 18+ & npm** (for the frontend)
- **FFmpeg & libsndfile** (standard system libraries)

---

### Step 1: Clone and Set Up Python Backend

#### Windows (PowerShell):
```powershell
# 1. Clone repository and navigate inside
cd c:\projects\Swara-Vaidya

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### macOS / Linux (Terminal):
```bash
# 1. Clone repository and navigate inside
cd Swara-Vaidya

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 2: (Optional) Re-Generate Reference Features & Annotations

The repository already ships with precomputed `reference_features.json` and `ref_maha_mrityunjay.json`. If you want to regenerate them from `mantra.wav`:

```bash
# Extract pitch, tempo, and MFCC reference features
python create_reference.py

# Detect word boundaries and phonetic contrast sub-spans
python generate_ref_annotations.py
```

---

### Step 3: Run Standalone Verification

To verify that the phonetic evaluator is working properly on the reference chant:

```bash
python phonetic_evaluator.py
```

Expected output:
```text
Testing phonetic_evaluator.py on mantra.wav...
Summary: {'total_words': 8, 'acceptable': 8, 'review': 0, 'inconclusive': 0, 'average_word_score': 98.9}
  Word 1: tryambakam -> Match: 100.0% | Status: acceptable
  Word 2: yajāmahe -> Match: 97.3% | Status: acceptable
  Word 3: sugandhim -> Match: 98.4% | Status: acceptable
  Word 4: puṣṭivardhanam -> Match: 99.9% | Status: acceptable
  Word 5: urvārukamiva -> Match: 98.7% | Status: acceptable
  Word 6: bandhanān -> Match: 100.0% | Status: acceptable
  Word 7: mṛtyormukṣīya -> Match: 100.0% | Status: acceptable
  Word 8: māmṛtāt -> Match: 97.3% | Status: acceptable
```

---

### Step 4: Start the Backend API

```bash
python -m uvicorn api:app --host 0.0.0.0 --port 10000 --reload
```

The API will be available at `http://localhost:10000`. You can test health:
```bash
curl http://localhost:10000/health
# Output: {"status":"ok"}
```

---

### Step 5: Start the React Frontend

Open a second terminal window:

```bash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

Open your browser at `http://localhost:5173` (or the URL printed by Vite).

1. Click **● Record** to record your chant through your microphone (or click **Upload Audio** to upload a WAV/MP3 recording).
2. Click **Analyse Chant**.
3. View the **Resonance Score**, the 4 macro dimension scores, and click the **Phonetic Words** tab to view the Duolingo-style word cards with color-coded feedback for all 8 words!

---

## API Reference

### `GET /reference-audio`
Streams the master reference audio file (`mantra.wav`) for playback and per-word slicing on the frontend.

### `POST /analyze`
Accepts an audio file upload and returns complete macro and micro chanting evaluation.

**Parameters:**
- `file`: Multipart audio file (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`, `.webm`).

**Sample Response Structure:**
```json
{
  "overall_score": 73.35,
  "overall_grade": "Madhyama",
  "mantra": "त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात्",
  "is_valid_mantra": true,
  "gate_message": "✓ Mantra verified: 8/8 words strong, 0/8 partial. Duration ratio: 1.0x.",
  "duration_ratio": 1.0,
  "word_alignment": [
    {
      "index": 0,
      "expected_devanagari": "त्र्यम्बकं",
      "expected_iast": "tryambakam",
      "heard_token": "त्रियमबकम",
      "lexical_score": 76.1,
      "acoustic_score": 100.0,
      "combined_score": 85.7,
      "status": "green",
      "user_start_sec": 0.0,
      "user_end_sec": 1.872,
      "ref_start_sec": 0.0,
      "ref_end_sec": 1.872
    }
  ],
  "user_transcript": "...",
  "dimensions": {
    "uccharana": {
      "score": 60.8,
      "char_sim": 76.1,
      "word_sim": 67.6,
      "syl_sim": 50.6,
      "issues": ["..."],
      "fixes": ["..."]
    },
    "svara": { "score": 77.5, "issues": [], "fixes": [] },
    "laya": { "score": 91.5, "duration_ratio": 1.0, "issues": [], "fixes": [] },
    "nada": { "score": 79.2, "issues": [], "fixes": [] }
  },
  "svara_word_detail": [
    {
      "word": "त्र्यम्बकं",
      "word_num": 1,
      "ref_accent": "neutral",
      "user_accent": "neutral",
      "accent_ok": true
    }
  ],
  "phonetic_evaluation": {
    "model_version": "hybrid_heuristic_v1",
    "summary": {
      "total_words": 8,
      "acceptable": 8,
      "review": 0,
      "inconclusive": 0,
      "average_word_score": 99.4
    },
    "words": [ ... ]
  }
}
```
      "inconclusive": 0,
      "average_word_score": 91.2
    },
    "words": [
      {
        "index": 0,
        "devanagari": "त्र्यम्बकं",
        "iast": "tryambakam",
        "word_match_score": 94.5,
        "status": "acceptable",
        "user_start_sec": 0.05,
        "user_end_sec": 1.88,
        "duration_sec": 1.83,
        "alignment_confidence": 0.94,
        "contrasts": [
          {
            "contrast_type": "conjunct_cluster",
            "label": "tryambakam_tr_cluster",
            "status": "acceptable",
            "reason": "Clear conjunct consonant cluster /tryambakam_tr_cluster/ articulated (duration 655 ms)."
          }
        ]
      }
    ]
  }
}
```

---

## License & Attribution
Derived from the Svara-Vaidya research architecture, extended with localized phonetic contrast analysis for Sanskrit pedagogy.
