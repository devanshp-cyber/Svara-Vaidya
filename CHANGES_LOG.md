# Swara Vaidya · Comprehensive System Changes & Architecture Log
**Document Version:** 2.0  
**Project:** Swara Vaidya (Vedic Sanskrit Chanting & Phonetic Evaluation Engine)  
**Target Reference Mantra:** Shri Ganesha Shloka (*Vakratuṇḍa Mahākāya*)

---

## 1. Executive Summary

This document provides a comprehensive, chronological, and file-by-file log of all architectural improvements, bug fixes, algorithmic calibrations, and UI redesigns implemented in **Swara Vaidya**.

The primary objective was transforming the legacy single-layer acoustic matcher into an authentic, dual-layer Vedic Sanskrit evaluation system featuring:
- **Macro-level Vedic Telemetry:** Ucchāraṇa (Pronunciation), Svara (Pitch & Accent Zones), Laya (Rhythm & Tempo), and Nāda (Vocal Timbre & Harmonic Richness).
- **Micro-level Phonetic Studio:** Word-by-word segmentation, acoustic Dynamic Time Warping (DTW), and targeted phonemic contrast analysis (vowel duration ratios, consonant aspiration bursts, and retroflex articulation).
- **Robust Anti-Spoofing & Cross-Mantra Protection:** Instant rejection of silence, ambient noise, non-mantric audio, or unrelated chants (e.g., Mahā Mṛtyuñjaya Mantra recited against Ganesha Shloka), with clear, non-contradictory diagnostics.
- **Fair Human Chanting Scoring:** Timbre and loudness normalization (dropping MFCC[0], CMVN), tolerant spectral distance decay, and multi-word Sanskrit n-gram handling so that authentic human recitations receive accurate, encouraging scores (75%–98%) instead of being falsely penalized as 0% or inconclusive.

---

## 2. Target Mantra Switch & Golden Reference Calibration

### 2.1 Transition to Shri Ganesha Shloka (*Vakratuṇḍa Mahākāya*)
- **Target Devanagari:**
  `वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा`
- **Target IAST Transliteration:**
  `vakratuṇḍa mahākāya sūryakoṭi samaprabha nirvighnaṃ kuru me deva sarvakāryeṣu sarvadā`
- **English Meaning:**
  *"O Lord with the curved trunk and immense body, whose brilliance equals ten million suns, please make all my endeavors free from obstacles, always."*

### 2.2 Golden Timestamp Annotation (`ganesha_shloka.json`)
- Manually verified Audacity word timestamps on the clean studio recording `mantra.wav`:
  1. **वक्रतुण्ड** (`vakratuṇḍa`): `[0.470s, 1.663s]`, Udātta accent, retroflex cluster `ṇḍ`.
  2. **महाकाय** (`mahākāya`): `[1.663s, 2.608s]`, Svarita accent, vowel duration ratio `ma` vs `hā` (1.5x–6.0x).
  3. **सूर्यकोटि** (`sūryakoṭi`): `[2.950s, 3.977s]`, Udātta accent, retroflex cluster `ṭi`.
  4. **समप्रभ** (`samaprabha`): `[3.977s, 4.900s]`, Anudātta accent, aspirated bilabial burst `bh`.
  5. **निर्विघ्नं** (`nirvighnam`): `[5.393s, 6.312s]`, Udātta accent, aspirated velar stop `gh`.
  6. **कुरुमेदेव** (`kuru me deva`): `[6.394s, 7.690s]`, Svarita accent, continuous pada flow.
  7. **सर्वकार्येषु** (`sarvakāryeṣu`): `[8.091s, 9.550s]`, Neutral accent, retroflex sibilant `ṣu`.
  8. **सर्वदा** (`sarvadā`): `[9.831s, 10.860s]`, Udātta/Anudātta accent, elongated terminal vowel.
- Reference feature cache (`reference_features.json`) auto-regenerated from `mantra.wav` containing pyin pitch contours, 13 MFCCs, beat frames, and tempo metadata.

---

## 3. Audio Trimming & Coordinate Offset Math

### 3.1 Silence Trimming on Reference and User Audio
- Leading and trailing dead air distort dynamic time warping paths. We implemented:
  ```python
  ref_trimmed, ref_trim_idx = librosa.effects.trim(ref_audio_raw, top_db=30)
  ref_trim_offset_sec = float(ref_trim_idx[0]) / ref_sr

  user_trimmed, user_trim_idx = librosa.effects.trim(user_audio_raw, top_db=30)
  user_trim_offset_sec = float(user_trim_idx[0]) / user_sr
  ```
- **Automatic Offset Compensation:**
  - Shifting all reference timestamps from `ganesha_shloka.json` to trimmed space: `r_trimmed = max(0.0, r_raw - ref_trim_offset_sec)`.
  - Running DTW alignment and feature slicing strictly on trimmed audio.
  - Adding `user_trim_offset_sec` and `ref_trim_offset_sec` back when building JSON payloads so the browser HTML5 audio player slices the exact raw audio files.

---

## 4. Phonetic Evaluation Engine (`phonetic_evaluator.py`)

### 4.1 Sub-Span Timestamp Projection (`project_sub_span`)
- **Bug Fixed:** Previously, internal contrast sub-spans (e.g., retroflex `ṇḍ` or vowel ratios) directly used raw reference timestamps. If a user chanted faster or slower, the evaluator sliced the wrong user audio region.
- **Formula Implemented:**
  $$\text{scale} = \frac{u_{\text{dur}}}{\max(r_{\text{dur}}, 10^{-5})}$$
  $$u_{\text{sub\_start}} = u_{\text{start}} + (r_{\text{sub\_start}} - r_{\text{start}}) \times \text{scale}$$
  $$u_{\text{sub\_end}} = u_{\text{start}} + (r_{\text{sub\_end}} - r_{\text{start}}) \times \text{scale}$$

### 4.2 Timbre Normalization & Calibrated Acoustic Match
- **Loudness Independence:** Dropped `mfcc[0]` (overall energy), using `mfcc[1:13]` scaled with `StandardScaler` + first-order delta trajectories (24-dimensional feature vector).
- **Dynamic Delta Width:** Safely handled short phonetic segments by calculating dynamic frame window `min(9, frames)` to prevent librosa interpolation crashes.
- **Exponential Distance Scaling:** Replaced steep DTW cutoff (`dist >= 4.2 -> 0%`) with broad human-calibrated decay:
  $$\text{Score} = 100 \times \exp\left(-\frac{\text{dist}}{5.2}\right) \quad (\text{for } \text{dist} < 7.5, \text{ else } 0)$$
- **Tolerant Spectral Contours:**
  - `RETROFLEX_CENTROID_DIFF_HZ` raised to 1500 Hz to account for male/female fundamental frequency differences and microphone EQ curves.
  - `ASPIRATION_ENERGY_RATIO_MIN` lowered to 0.05 to capture gentle breath release on phone/laptop microphones.
  - `VOWEL_RATIO_TOLERANCE` expanded to ±50% to accommodate natural chant elongation.

### 4.3 Word Status Determination
- Recalibrated `Acceptable (✓)` threshold to `match_score >= 48.0%`.
- `Inconclusive (?)` is strictly reserved for unvoiced silence (`RMS < 0.003`), near-zero durations (`< 30ms`), or unrecited segments.

---

## 5. Lexical & Acoustic Fusion (`compare_chant.py`)

### 5.1 Devanagari Normalization & Compound Word N-Gram Matching
- `normalize_sanskrit_phonetic`:
  - Homorganic nasals vs. anusvāra: `म्ब ↔ ंब`, `न्ध ↔ ंध`, `ण्ड ↔ ंड`.
  - Sibilant merging (`ष ↔ श`).
  - Halant/schwa handling.
- **Sliding Window N-Grams:** MMS-1B ASR frequently splits Sanskrit compound words into multiple tokens (e.g., `कुरु मे देव` for `कुरुमेदेव`, `सूर्य कोटि` for `सूर्यकोटि`, `सर्व कार्येषु` for `सर्वकार्येषु`). We implemented:
  - 1-word, 2-word, and 3-word concatenated sliding windows.
  - Normalized substring matching against `user_clean.replace(" ", "")`.
  - Restored lexical matches from ~50% to 95%–100% on valid recitations.

### 5.2 Elimination of Artificial Score Zeroing
- Removed legacy logic that wiped out `combined_score` and `lexical_score` to 0.0% whenever a card was red. The UI now displays the honest, measured score.

### 5.3 Cross-Mantra Protection & False-Positive Elimination
- **Bug Fixed:** Previously, if a user recited a completely different mantra (e.g. Mahā Mṛtyuñjaya Mantra), generic speech resonance caused DTW acoustic scores of ~45%, which automatically triggered `status = "white"` for all 8 words, producing the contradictory message `"Recitation does not match... Only 8/8 words matched (need >= 3)"`.
- **Solution Implemented:**
  - If words are spoken in the audio, a word cannot be considered green or white if lexical evidence is absent (`lexical_score < 20.0`).
  - If overall text similarity is low (`< 25.0%`), the system recognizes that an unrelated text was chanted; all coincidental sub-word overlaps are clamped to red (0.0%).
  - Non-contradictory gate message:
    `"Different chant detected. Text similarity with Ganesha Shloka is only 21.0% (0/8 words verified). Heard: '...'"`

### 5.4 Overall Score Weighting
- Dominant **80% weight** assigned to legacy Vedic dimensions and **20%** to micro-phonetic evaluation:
  $$\text{Legacy} = 0.40 \times \text{Ucchāraṇa} + 0.25 \times \text{Nāda} + 0.20 \times \text{Svara} + 0.15 \times \text{Laya}$$
  $$\text{Overall} = 0.80 \times \text{Legacy} + 0.20 \times \text{Phonetic Word Score}$$

---

## 6. Frontend UI/UX Modernization (`frontend/src/App.jsx`)

### 6.1 Audio Playback Freedom
- Relaxed playback constraints in `PhoneticWordCard`: whenever the audio slice interval exists (`user_end_sec > user_start_sec`), the button activates as **"Play My Word"** so users can always hear their voice.

### 6.2 English Translations for Sanskrit Terms
- Added English translations in brackets for all proficiency grades:
  - `Uttama (Excellent)`
  - `Madhyama (Intermediate)`
  - `Ādi (Foundation)`
  - `Prārambhika (Beginner)`
- Added Vedic accent translations in word cards:
  - `Udātta (High Pitch Accent)`
  - `Anudātta (Low Pitch Accent)`
  - `Svarita (Falling Pitch Accent)`
  - `Sādhāraṇa (Neutral)`
- Updated Tab navigation labels:
  - `Ucchāraṇa (Pronunciation)`
  - `Svara (Pitch & Accent)`
  - `Laya & Nāda (Rhythm & Timbre)`
  - `🪔 Daily Sādhana (Spiritual Practice) Recommendation`
- Added English meaning of Ganesha Shloka to the top hero banner.

### 6.3 Safe Tab Rendering
- Fixed crash (`TypeError: Cannot read properties of null`) when clicking tabs prior to audio analysis by introducing safe empty-state placeholders.

---

## 7. File Modification Summary

| File | Changes Made |
|---|---|
| `compare_chant.py` | Silence trimming offset math; `normalize_sanskrit_phonetic`; sliding n-gram matching; removed score zeroing; cross-mantra protection gate; 80/20 overall score blending; English translations for grades. |
| `phonetic_evaluator.py` | Silence trimming on ref & user audio; `project_sub_span` linear interpolation; dropped MFCC[0]; dynamic delta width; relaxed DTW decay (`-dist/5.2`); broadened spectral tolerances (1500 Hz retroflex, 0.05 aspiration, 50% vowel ratio); 48% acceptable threshold. |
| `frontend/src/App.jsx` | Unlocked "Play My Word" audio playback; added English translations for all Sanskrit terms, grades, and Vedic accents; added English mantra meaning in hero banner; safe empty states preventing null-pointer crashes; rebuilt production bundle (`dist/`). |
| `ganesha_shloka.json` | Golden Audacity reference timestamps (0.470s–10.860s), phonetic contrast schemas, and IAST transliterations for Shri Ganesha Shloka. |
| `create_reference.py` | Reference feature generation updated to Ganesha Shloka text and `mantra.wav`. |
| `README.md` | Complete architectural documentation updated to Shri Ganesha Shloka. |
| `test_pipeline.py` | Automated 5-point test suite validating silence, noise, short "Om", reference chanting, and cross-mantra rejection. |
