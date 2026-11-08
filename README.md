# Svara Vaidya · स्वर वैद्य
### "Duolingo for Mantras" Hybrid Phonetic & Vedic Chanting Evaluation System

**Svara Vaidya** is an intelligent, dual-layer audio evaluation engine for Vedic Sanskrit mantra chanting. Built specifically for the **Shri Ganesha Shloka** (*Vakratuṇḍa Mahākāya*), the system pairs a 4-dimensional macro acoustic assessment pipeline with a fine-grained, word-by-word and phoneme-level evaluation module.

---

## The Target Mantra
> **वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा**  
> *vakratuṇḍa mahākāya sūryakoṭi samaprabha nirvighnaṃ kuru me deva sarvakāryeṣu sarvadā*

The 8 target words analyzed by the system:
1. **वक्रतुण्ड** (*vakratuṇḍa*) — Retroflex nasal + stop cluster `/ṇḍ/`
2. **महाकाय** (*mahākāya*) — Short vowel `/ma/` vs. long vowel `/hā/` duration ratio
3. **सूर्यकोटि** (*sūryakoṭi*) — Retroflex conjunct `/ṭi/` & semivowel articulation
4. **समप्रभ** (*samaprabha*) — Bilabial aspirated stop `/bh/` burst release
5. **निर्विघ्नं** (*nirvighnam*) — Velar aspirated stop `/gh/` & labial anusvāra
6. **कुरुमेदेव** (*kuru me deva*) — Short `/u/` vowel duration ratio & continuous pada flow
7. **सर्वकार्येषु** (*sarvakāryeṣu*) — Retroflex sibilant `/ṣu/` & liquid cluster `/rv/`
8. **सर्वदा** (*sarvadā*) — Liquid glide `/r/` & terminal lengthened vowel `/dā/`

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
├── mantra.wav                        # Clean reference audio (Ganesha Shloka)
├── reference_features.json           # Precomputed reference pitch, MFCC, tempo features
├── ganesha_shloka.json               # Reference timestamps & phonetic contrast schema
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

The repository already ships with precomputed `reference_features.json` and `ganesha_shloka.json`. If you want to regenerate `reference_features.json` from `mantra.wav`:

```bash
# Extract pitch, tempo, and MFCC reference features
python create_reference.py
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
  Word 1: vakratuṇḍa -> Match: 98.5% | Status: acceptable
  Word 2: mahākāya -> Match: 97.3% | Status: acceptable
  Word 3: sūryakoṭi -> Match: 98.4% | Status: acceptable
  Word 4: samaprabha -> Match: 99.0% | Status: acceptable
  Word 5: nirvighnam -> Match: 98.7% | Status: acceptable
  Word 6: kuru me deva -> Match: 98.5% | Status: acceptable
  Word 7: sarvakāryeṣu -> Match: 97.9% | Status: acceptable
  Word 8: sarvadā -> Match: 98.2% | Status: acceptable
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
  "overall_grade": "Uttama",
  "mantra": "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा",
  "is_valid_mantra": true,
  "gate_message": "✓ Mantra verified: 8/8 words strong, 0/8 partial. Duration ratio: 1.0x.",
  "duration_ratio": 1.0,
  "word_alignment": [
    {
      "index": 0,
      "expected_devanagari": "वक्रतुण्ड",
      "expected_iast": "vakratuṇḍa",
      "heard_token": "वक्रतुण्ड",
      "lexical_score": 100.0,
      "acoustic_score": 97.3,
      "combined_score": 98.7,
      "status": "green",
      "user_start_sec": 0.544,
      "user_end_sec": 1.632,
      "ref_start_sec": 0.470,
      "ref_end_sec": 1.663
    }
  ],
  "user_transcript": "...",
  "dimensions": {
    "uccharana": {
      "score": 97.5,
      "char_sim": 98.0,
      "word_sim": 96.5,
      "syl_sim": 97.0,
      "issues": [],
      "fixes": []
    },
    "svara": { "score": 100.0, "issues": [], "fixes": [] },
    "laya": { "score": 100.0, "duration_ratio": 1.0, "issues": [], "fixes": [] },
    "nada": { "score": 100.0, "issues": [], "fixes": [] }
  },
  "svara_word_detail": [
    {
      "word": "वक्रतुण्ड",
      "word_num": 1,
      "ref_accent": "udatta",
      "user_accent": "udatta",
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
      "average_word_score": 98.9
    },
    "words": [
      {
        "index": 0,
        "devanagari": "वक्रतुण्ड",
        "iast": "vakratuṇḍa",
        "word_match_score": 97.3,
        "status": "acceptable",
        "user_start_sec": 0.544,
        "user_end_sec": 1.632,
        "duration_sec": 1.088,
        "alignment_confidence": 0.98,
        "contrasts": [
          {
            "contrast_type": "retroflex_cluster",
            "label": "ṇḍ",
            "status": "acceptable",
            "reason": "Clear retroflex conjunct articulated."
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
