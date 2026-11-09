# Svara Vaidya · स्वर वैद्य
### Vedic Phonetic and Svara Telemetry Engine for Sanskrit Mantra Chanting

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-orange.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![Vite 6](https://img.shields.io/badge/Vite-6.0-646cff.svg)](https://vitejs.dev/)
[![Meta MMS](https://img.shields.io/badge/Meta%20MMS-1B--All-blue.svg)](https://huggingface.co/facebook/mms-1b-all)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Svara Vaidya (स्वर वैद्य)** is an intelligent, dual-layer audio telemetry and pedagogical evaluation engine for classical Vedic Sanskrit mantra chanting. Specifically calibrated for the canonical **Shri Ganesha Shloka** (*Vakratuṇḍa Mahākāya*), the system pairs a 4-dimensional macro acoustic assessment pipeline with fine-grained, word-by-word articulatory phonetics, Vedic pitch contour tracking, and non-overlapping acoustic slice playback.

The system features a **2-Page Application** styled in a vibrant **"Sacred Ivory and Warm Saffron"** design language, complete with a real-time 60 FPS HTML5 Canvas audio waveform visualizer, drag-and-drop video and audio ingestion, and an illuminated Vedic manuscript coaching dashboard.

---

## The Target Mantra: Shri Ganesha Shloka

> **वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा**  
> *vakratuṇḍa mahākāya sūryakoṭi samaprabha nirvighnaṃ kuru me deva sarvakāryeṣu sarvadā*

| # | Word (Devanagari) | IAST | Target Vedic Svara | Key Articulatory and Phonetic Contrasts |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **वक्रतुण्ड** | *vakratuṇḍa* | **Udātta ↗** (High Pitch) | Retroflex nasal + stop conjunct cluster ṇḍ |
| **2** | **महाकाय** | *mahākāya* | **Anudātta _** (Low Pitch) | Short ma vs. elongated long hā vowel duration ratio |
| **3** | **सूर्यकोटि** | *sūryakoṭi* | **Udātta ↗** (High Pitch) | Liquid semivowel rya and retroflex stop closure ṭi |
| **4** | **समप्रभ** | *samaprabha* | **Anudātta _** (Low Pitch) | Bilabial aspirated stop bha burst release |
| **5** | **निर्विघ्नं** | *nirvighnaṃ* | **Svarita ⌒** (Falling Pitch) | Velar aspirated stop gha and terminal labial anusvāra ṃ |
| **6** | **कुरुमेदेव** | *kuru me deva* | **Udātta ↗** (High Pitch) | Short u vowel duration ratio and continuous pada flow |
| **7** | **सर्वकार्येषु** | *sarvakāryeṣu* | **Anudātta _** (Low Pitch) | Retroflex sibilant ṣu and velar conjunct cluster kārye |
| **8** | **सर्वदा** | *sarvadā* | **Svarita ⌒** (Falling Pitch) | Liquid glide r and terminal lengthened vowel dā |

---

## Dual-Layer Telemetry Architecture

```
                       User Audio or Video Ingestion
           (Microphone, WAV, MP3, M4A, OGG, FLAC, MOV, MP4)
                                  │
      ┌───────────────────────────┴───────────────────────────┐
      ▼                                                       ▼
[Client-Side PCM Engine]                             [FastAPI Backend (Analyze Endpoint)]
- 60 FPS HTML5 Canvas Visualizer                     - Multi-format Audio Ingestion
- QuickTime and MP4 24-bit LPCM Demuxer              - Pure-Python MP4 and MOV Container Parser
- Peak Normalization (0.92)                          - MMS-1B CTC Sanskrit Speech ASR
- Lossless 16-bit WAV Encoding                       - Dynamic Time Warping (DTW) Alignment
      │                                                       │
      └───────────────────────────┬───────────────────────────┘
                                  ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                     MANTRA VERIFICATION GATE (Pre-Filter)                     │
│  - Rejects pure silence and ambient noise (< 1.0s or max RMS < 0.012)         │
│  - Rejects single syllables or isolated tones (Om, humming)                   │
│  - Rejects unrelated chants (Gayatri Mantra, Shiva Stotram, text sim < 30%)   │
│  - Verifies full recitation: flags 8 of 8 canonical words (Strong vs Partial) │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐
│        LAYER 1: MACRO DIMENSIONS        │   │        LAYER 2: MICRO PHONETICS         │
│ 1. Ucchāraṇa (ASR Character & Syllables)│   │ - Local DTW Warping Path Projection     │
│ 2. Svara (F0 pYIN, Accents, Contour)    │   │ - 8-Word Non-Overlapping Alignment      │
│ 3. Laya (Onset Envelope & Tempo Ratio)  │   │ - Vowel Length Ratio (Short vs Long)    │
│ 4. Nāda (MFCC Vocal Timbre & Resonance) │   │ - Articulatory Contrasts (Retroflexion, │
│ - Overall Weighted Composite Score      │   │   Aspiration, Conjuncts, Sibilants)     │
└─────────────────────────────────────────┘   └─────────────────────────────────────────┘
                                        │
                                        ▼
             ┌─────────────────────────────────────────────────────────┐
             │       LIGHT "SACRED IVORY & WARM SAFFRON" UI            │
             │ - Page 1: Interactive Chanting Studio                   │
             │ - Page 2: Executive Telemetry & 8-Word Alignment Strip  │
             │ - 4 Diagnostic Studios + Dual-Audio Slice Playback      │
             │ - Priority Focus Areas & Daily Sādhanā Callout Card     │
             └─────────────────────────────────────────────────────────┘
```

### 1. Macro Evaluation Pipeline (4 Dimensions)
- **Ucchāraṇa (उच्चारण — Pronunciation):** Uses Meta's multilingual MMS-1B (`facebook/mms-1b-all`) CTC acoustic model for Sanskrit phoneme decoding, calculating Character Similarity, Word Similarity, and Syllable (Akṣara) Similarity.
- **Svara (स्वर — Pitch and Vedic Accent):** Estimates fundamental frequency (F0) via Librosa pYIN, classifies Vedic accent zones (*Udātta* ↗, *Anudātta* _, *Svarita* ⌒), verifies intra-syllable pitch trajectories, and matches pitch contour slopes.
- **Laya (लय — Rhythm and Tempo):** Computes syllable onset strength envelopes and aligns chant cadence against the reference master chant using Dynamic Time Warping (DTW). Measures Chant Tempo and Duration Ratio (0.85x to 1.35x ideal range).
- **Nāda (नाद — Vocal Resonance and Timbre):** Computes z-score normalized Mel-Frequency Cepstral Coefficients (MFCCs) with delta spectral features to measure vocal warmth, placement, and harmonics.
- **Resonance Score:** Computes a weighted Vedic composite metric mapped to traditional Vedic performance tiers (*Uttama*, *Madhyama*, *Ādi*, *Prārambhika*).

### 2. Micro Phonetic and Word-Level Module (`phonetic_evaluator.py`)
- **Zero-Bleed Word Boundaries:** Adjacent words with continuous speech boundaries (vakratuṇḍa -> mahākāya, sūryakoṭi -> samaprabha, nirvighnaṃ -> kuru me deva) are bound to a strict non-overlapping midpoint `u_end[i] = u_start[i+1]`, preventing audio bleed.
- **Natural Breath Pause Preservation:** Pairs separated by natural breath pauses in `ganesha_shloka.json` (mahākāya -> sūryakoṭi, samaprabha -> nirvighnaṃ, kuru me deva -> sarvakāryeṣu, sarvakāryeṣu -> sarvadā) preserve natural silence intervals.
- **Articulatory Phonetic Contrasts:** Evaluates short-to-long vowel duration ratios (target 1.5x to 6.0x), consonant aspiration high-frequency bursts, retroflex consonant closures (ṇḍ, ṭi), and conjunct consonant clusters (tr, kṣ).
- **Dual-Audio Word Comparison:** Provides slice timestamps (`[user_start_sec, user_end_sec]` vs. `[ref_start_sec, ref_end_sec]`) for interactive playback on every word card.

### 3. Universal Container Support (QuickTime, MP4, and MOV Demuxing)
- Files recorded on mobile devices (e.g., iPhone video recordings or QuickTime exports containing video tracks and 24-bit or 32-bit LPCM audio) are automatically demuxed:
  - **In-Browser:** `extractQuickTimeLPCM` parses the container in ~90ms, converts samples into `Float32Array`, normalizes peaks to 0.92, and encodes standard 16-bit PCM WAV.
  - **Backend:** `load_audio_safely` in `compare_chant.py` includes a zero-dependency Python and NumPy QuickTime container audio demuxer that parses `stsc`, `stco`, and `stsd` atoms and resamples to 16 kHz without requiring external system dependencies.

---

## User Interface and Design System

The application is built in a modern **"Sacred Ivory and Warm Saffron"** light theme:
- **Sacred Typography:** Google Fonts `'Cormorant Garamond'` (sacred serif headings), `'Noto Serif Devanagari'` (classical Sanskrit script), and `'Plus Jakarta Sans'` (clean UI metrics).
- **Sacred Canvas:** Warm ivory background (`#FAF6F0`) with warm saffron-amber radial mesh gradients, card lift micro-animations, and soft elevations.
- **Page 1: The Interactive Recording Studio:**
  - Real-time 60 FPS HTML5 Canvas waveform visualizer driven by an `AudioContext` `AnalyserNode`.
  - Recording button with pulse glow animation + drag-and-drop audio and video upload card.
  - Live technical telemetry pills (16 kHz, PCM Mono, uncompressed dynamic range).
  - Canonical 8-word Ganesha Shloka recitation guide card with Devanagari, IAST, and accent marks.
- **Page 2: Executive Telemetry and Analysis Studio:**
  - `"← Back to Chanting Studio"` navigation bar + quick full audio comparison buttons.
  - Mantra Verification Gate alert banner (Emerald for verified, Crimson for invalid or unrelated audio).
  - 180px animated SVG circular ring gauge with Sanskrit proficiency grade badge.
  - 4-Macro Vedic Dimension cards (Ucchāraṇa, Svara, Laya, Nāda) with one-click tab switching.
  - Interactive 8-Word Alignment Ribbon with tactile color-coded pill cards (Green, Amber, Red) and direct slice playback.
  - **Tab 1 (Phonetic Studio):** Responsive 2-column grid of 8 `PhoneticWordCard` components with side-by-side audio playback (`Play My Word` vs `Play Reference Word`), acoustic match progress bars, and articulatory contrast chips.
  - **Tab 2 (Ucchāraṇa Studio):** KPI stat cards for Character, Word, and Syllable similarities, heard transcript comparison, and specific pronunciation fixes.
  - **Tab 3 (Svara Studio):** 5-bar pitch sub-metric telemetry (Contour, Zone, Accent, Shape, Slope) and 8-word expected vs. sung pitch accent badges.
  - **Tab 4 (Laya and Nāda Studio):** Rhythmic pace gauge, vocal timbre resonance gauge, and a visual 3-zone **Tempo Meter** (`Fast < 0.85x` | `Ideal 0.85x–1.35x` | `Vilambita Slow > 1.35x`).
  - **Executive Coaching Row:** 2-column layout displaying **Priority Focus Areas** (ranked by impact) and **Sādhu Praises** (accurate recitation aspects).
  - **Daily Sādhanā (दैनिक साधना):** Illuminated Vedic manuscript scroll callout card with tailored practice regimens.

---

## Repository Structure

```
Swara-Vaidya/
├── api.py                            # FastAPI backend entry point (/analyze, /health, /reference-audio)
├── compare_chant.py                  # Core audio analysis, macro feedback engine & robust audio loader
├── phonetic_evaluator.py             # Word-level & phoneme-level evaluation module
├── mantra.wav                        # Master reference audio (Golden Male Chanting, 16kHz Clean)
├── reference_features.json           # Precomputed reference pitch, MFCC, and onset features
├── ganesha_shloka.json               # Word timestamp boundaries & phonetic contrast schema
├── test_pipeline.py                  # 5-test automated pipeline validation suite
├── test_audio_suite.py               # 10-audio comprehensive stress test suite
├── requirements.txt                  # Python dependencies
├── CHANGES_LOG.md                    # Detailed changelog of bug fixes & enhancements
├── README.md                         # Project documentation
├── test_audio/                       # Test recordings (silence, noise, slow chant, BGM variants, etc.)
└── frontend/                         # Modern React 19 + Vite frontend application
    ├── src/
    │   ├── App.jsx                   # Vibrant 2-page application with Canvas visualizer & telemetry
    │   └── main.jsx                  # React application entry point
    ├── dist/                         # Compiled production distribution assets
    ├── package.json                  # Node dependencies & build scripts
    └── vite.config.js                # Vite build configuration
```

---

## Local Setup and Quickstart

### Prerequisites
- **Python 3.10+** (64-bit)
- **Node.js 18+ and npm** (for frontend)

---

### Option 1: Quickstart Using VS Code (Recommended)

This is the easiest and recommended way to set up and run Svara Vaidya:

1. **Open the Project Folder:**
   - Launch Visual Studio Code.
   - Click **File > Open Folder...** and select the `Swara-Vaidya` root folder.

2. **Open the Integrated Terminal:**
   - Open the terminal inside VS Code by pressing ``Ctrl + ` `` (or select **Terminal > New Terminal** from the menu).

3. **Create the Python Virtual Environment:**
   - In the terminal, run:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   *(Optional for NVIDIA GPU users: run `.\.venv\Scripts\python.exe -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu124` for Tensor Core acceleration).*

4. **Select the Python Interpreter in VS Code:**
   - Press `Ctrl + Shift + P` (or `Cmd + Shift + P` on macOS) to open the Command Palette.
   - Type and select **Python: Select Interpreter**.
   - Choose the project environment: `Python 3.11 (.venv) .\.venv\Scripts\python.exe`.
   - VS Code will now automatically use `.venv` for code intelligence and terminal sessions.

5. **Install Frontend Dependencies:**
   - In the terminal, navigate to `frontend` and install Node packages:
   ```powershell
   cd frontend
   npm install
   cd ..
   ```

6. **Start the Backend API Server (Terminal 1):**
   - Start the FastAPI backend:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn api:app --reload --port 10000
   ```
   - You will see:
     ```text
     Uvicorn running on http://127.0.0.1:10000 (Press CTRL+C to quit)
     ```
   - On first chant analysis, the backend automatically prints whether it detected a GPU or CPU:
     - On GPU: `MMS Sanskrit model loaded on GPU: NVIDIA GeForce RTX 3050 Laptop GPU (FP16 Tensor Core acceleration)`
     - On CPU: `MMS Sanskrit model loaded on CPU.`

7. **Start the Frontend Application (Terminal 2):**
   - In the VS Code terminal header, click the **+ (New Terminal)** or **Split Terminal** button to open a second terminal tab.
   - Run:
   ```powershell
   cd frontend
   npm run dev
   ```
   - Vite will display:
     ```text
     VITE ready in 250 ms
     Local: http://localhost:5173/
     ```

8. **Open the Web Application:**
   - Open your browser to `http://localhost:5173`.
   - Click **Start Chanting** to test your microphone, or drag-and-drop an audio file to analyze.

---

### Option 2: Quickstart Using Standalone Terminals (PowerShell, Command Prompt, macOS, Linux)

If you prefer to run the project using standard operating system terminals:

#### 1. Backend Setup and Execution

##### Windows (PowerShell):
```powershell
# 1. Navigate to project root
cd c:\projects\Swara-Vaidya

# 2. Create virtual environment
python -m venv .venv

# 3. Allow script execution in current PowerShell window (fixes PSSecurityException)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 4. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 5. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 6. Start backend server
python -m uvicorn api:app --host 0.0.0.0 --port 10000 --reload
```

##### Windows (Command Prompt - cmd.exe):
```cmd
cd c:\projects\Swara-Vaidya
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn api:app --host 0.0.0.0 --port 10000 --reload
```

##### Windows Direct Execution (No activation needed, avoids script execution blocks):
```powershell
cd c:\projects\Swara-Vaidya
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api:app --host 0.0.0.0 --port 10000 --reload
```

##### macOS and Linux (Terminal):
```bash
# 1. Navigate to project root
cd Swara-Vaidya

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Start backend server
python -m uvicorn api:app --host 0.0.0.0 --port 10000 --reload
```

#### 2. Frontend Setup and Execution (In a Second Terminal Window)

```bash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

Open your browser at `http://localhost:5173`.

---

### Hardware Compatibility (CPU and GPU Support)

Svara Vaidya runs seamlessly on any machine:
- **CPU Mode (Universal for all PCs):** If your computer has no dedicated graphics card, the application automatically runs on your CPU in standard FP32 mode. No special drivers or NVIDIA setup are required.
- **NVIDIA GPU Acceleration (Optional):** If your machine has an NVIDIA graphics card (GeForce RTX, GTX, or Quadro), you can enable FP16 Tensor Core acceleration by installing the CUDA PyTorch wheel:
```powershell
.\.venv\Scripts\python.exe -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu124
```
*(On GPU, inference automatically uses 16-bit half precision, speeding up analysis to approximately 2 seconds).*

---

## Validation and Test Suites

The repository includes automated test suites to ensure zero regressions:

### 1. 5-Point Core Pipeline Suite (`test_pipeline.py`)
Validates silence rejection, ambient noise filtering, single-syllable rejection, golden reference verification, and unrelated chant gating:

```bash
python test_pipeline.py
```

Expected output:
```text
==================================================
RUNNING 4-POINT VALIDATION SUITE FOR AUDIO PIPELINE
==================================================
[TEST 1: Pure Silence]                                  -> PASSED (0.0% score, 0 words matched)
[TEST 2: Ambient Noise]                                  -> PASSED (0.0% score, 0 words matched)
[TEST 3: Short 'Om' Tone or Syllable]                   -> PASSED (5.0% score, 0 words matched, all red)
[TEST 4: Reference Chanting (mantra.wav)]                 -> PASSED (90.76% score, 8 of 8 green words, exact alignment)
[TEST 5: Unrelated Chant (user_chant2.wav)]              -> PASSED (5.0% score, 0 words matched, all red)
==================================================
ALL 5 TESTS COMPLETED SUCCESSFULLY!
==================================================
```

### 2. 10-Audio Stress Test Suite (`test_audio_suite.py`)
Validates real-world acoustic variations across slow female chanting (vilambita laya), background music, speech preambles, and non-canonical chants:

```bash
python test_audio_suite.py
```

| Audio File | Description | Gate Result | Overall Score | Words Matched | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `mantra.wav` | Golden Male Reference (16kHz Clean) | **VERIFIED** | **90.8%** | 8 of 8 | **PASS** |
| `correct_with_startingandendingextrawords.mp3` | MP3 with Intro and Outro Speech | **VERIFIED** | **73.7%** | 8 of 8 | **PASS** |
| `femalevoicewithoutbgm.wav` | Slow Female Chant (23s, Vilambita Laya) | **VERIFIED** | **70.6%** | 8 of 8 | **PASS** |
| `femalevoicewithbgm.wav` | Female Chant with BGM (28s) | **VERIFIED** | **68.3%** | 8 of 8 | **PASS** |
| `femalevoicewithbgm2.wav` | Female Chant with BGM Variant (23s) | **VERIFIED** | **65.5%** | 7 of 8 | **PASS** |
| `femalevoicelatestart.wav` | Female Chant with Late Start (28s) | **VERIFIED** | **68.0%** | 8 of 8 | **PASS** |
| `user_chant1.wav` | Non-Shloka Chant (*Om Gan Ganapataye*, 3.6s) | **REJECTED** | **5.0%** | 0 of 8 | **PASS** |
| `user_chant2.wav` | Short Chant (*Om Ganeshaya Namaha*, 5.4s) | **REJECTED** | **5.0%** | 0 of 8 | **PASS** |
| `user_chant3.wav` | Non-Shloka Chant (*Om Namah Shivaya*, 3.0s) | **REJECTED** | **5.0%** | 0 of 8 | **PASS** |
| `another_mantra2.wav` | QuickTime MP4 or MOV Gayatri Mantra (16.5s) | **REJECTED** | **7.1%** | 0 of 8 | **PASS** |

### 3. Frontend Quality and Linting
```bash
cd frontend
npm run lint    # 0 errors, 0 warnings
npm run build   # Production bundle compiled in <400ms
```

---

## API Reference

### `GET /health`
Returns backend service availability status.
```json
{
  "status": "ok"
}
```

### `GET /reference-audio`
Streams the master reference audio file (`mantra.wav`) as WAV audio for direct in-browser playback and per-word reference slice comparison.

### `POST /analyze`
Accepts multipart audio and video file upload and returns complete macro and micro chanting evaluation.

**Supported Formats:** `.wav`, `.mp3`, `.mpeg`, `.mpga`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.webm`, `.mov`, `.mp4`, `.m4v`, `.3gp`.

**Sample Response:**
```json
{
  "overall_score": 90.76,
  "overall_grade": "Uttama",
  "is_valid_mantra": true,
  "matched_words_count": 8,
  "gate_message": "✓ Mantra verified: 8 of 8 words strong, 0 of 8 partial. Duration ratio: 1.0x.",
  "duration_ratio": 1.0,
  "word_alignment": [
    {
      "index": 0,
      "expected_devanagari": "वक्रतुण्ड",
      "expected_iast": "vakratuṇḍa",
      "heard_token": "वक्रतुण्ड",
      "status": "green",
      "score": 96.8,
      "user_start_sec": 0.624,
      "user_end_sec": 1.627,
      "ref_start_sec": 0.470,
      "ref_end_sec": 1.663
    }
  ],
  "dimensions": {
    "uccharana": {
      "score": 97.5,
      "char_sim": 98.0,
      "word_sim": 96.5,
      "syl_sim": 97.0,
      "issues": [],
      "fixes": [],
      "praises": ["Accurate retroflex consonant articulation throughout."]
    },
    "svara": {
      "score": 92.4,
      "contour_score": 95.0,
      "zone_score": 90.0,
      "accent_score": 92.0,
      "shape_score": 94.0,
      "slope_score": 89.0,
      "issues": [],
      "fixes": [],
      "praises": ["Exemplary Udātta accent elevation."]
    },
    "laya": {
      "score": 91.2,
      "duration_ratio": 1.0,
      "issues": [],
      "fixes": [],
      "praises": ["Steady rhythmic cadence in Madhya Laya."]
    },
    "nada": {
      "score": 88.6,
      "issues": [],
      "fixes": [],
      "praises": ["Clear vocal resonance and harmonic fidelity."]
    }
  },
  "priority": [
    { "dimension": "Nāda (Voice Quality)", "score": 89, "weight": 0.25, "impact": 2.8 }
  ],
  "all_praises": [
    "Accurate retroflex consonant articulation throughout.",
    "Exemplary Udātta accent elevation.",
    "Steady rhythmic cadence in Madhya Laya."
  ],
  "sadhana_tip": "Chant the Ganesha Shloka 11 times daily with attention to Pada-pāṭha (word separation) and Svara melody.",
  "phonetic_evaluation": {
    "summary": {
      "total_words": 8,
      "acceptable": 8,
      "review": 0,
      "inconclusive": 0,
      "average_word_score": 94.5
    },
    "words": [
      {
        "index": 0,
        "devanagari": "वक्रतुण्ड",
        "iast": "vakratuṇḍa",
        "word_match_score": 96.8,
        "status": "acceptable",
        "user_start_sec": 0.624,
        "user_end_sec": 1.627,
        "ref_start_sec": 0.470,
        "ref_end_sec": 1.663,
        "contrasts": [
          {
            "contrast_type": "retroflex_cluster",
            "label": "ṇḍ",
            "status": "acceptable",
            "reason": "Retroflex cluster articulated with clear closure."
          }
        ]
      }
    ]
  }
}
```

---

## License and Attribution

Distributed under the **MIT License**.

- **Acoustic ASR Backbone:** Meta Multilingual Speech (`facebook/mms-1b-all`).
- **Pitch Estimation:** Librosa pYIN probabilistic fundamental frequency tracker.
- **Vedic Phonetics and Svara Theory:** Calibrated according to traditional *Śīkṣā* (Vedic Phonetics) and *Prātiśākhya* recitation rules.
