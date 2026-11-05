# Sanskrit Phonetic Pronunciation Evaluation for Vedic Chanting
## Standalone Project Specification and Implementation Plan

**Status:** Proposed project design  
**Approach:** Build a new codebase from scratch. Do not depend on or modify the seniors' Svara Vaidya implementation.  
**Recommended first milestone:** A small, measurable pronunciation-evaluation prototype for one selected Sanskrit mantra.

---

## 1. Executive Summary

The project will develop a system that analyzes a user's recording of a Sanskrit mantra and provides **localized, phoneme-level pronunciation feedback**.

The system will not merely transcribe speech and compare the resulting text. It will use a verified reference text to derive an expected phonetic-unit sequence, align relevant audio regions with those units, extract acoustic evidence, and evaluate selected pronunciation distinctions.

For the first version, focus on a **small number of carefully selected phonetic contrasts** in one mantra. Candidate examples include short versus long vowels, aspirated versus unaspirated stops, dental versus retroflex consonants, and selected nasal distinctions. These are possible research targets, not capabilities that should be assumed to work before evaluation. Consult a qualified Sanskrit/phonetics expert to define the sound inventory, accepted realizations, and annotation rules.

### Proposed contribution

> Build an independent Sanskrit phonetic-evaluation pipeline that localizes selected pronunciation distinctions and evaluates its predictions against expert-annotated examples.

### What the project is not

- It is not initially a general-purpose Sanskrit speech recognizer.
- It is not initially a complete evaluator of Vedic svara or prosody.
- It should not treat every acoustic difference as a pronunciation error.
- It should not claim reliable Sanskrit phoneme evaluation until tested against annotated data.

**Research question:** Can acoustic features and/or pretrained speech representations identify selected Sanskrit pronunciation distinctions in mantra recordings, with measurable agreement against expert annotation?

---

## 2. Problem Statement

Speech recognition asks, “What words were spoken?” Pronunciation evaluation asks, “Were the relevant sounds produced in an acceptable way?”

A transcript can match the expected text even when a sound is pronounced differently. Conversely, a speech recognizer may produce an incorrect transcript when the speaker's pronunciation is acceptable, particularly if the recognizer has limited support for the language, register, or chanting style.

For this project, the Sanskrit text will be known in advance. The goal is not to solve unrestricted speech recognition first. Instead, the known text will determine the expected phonetic sequence, and the system will evaluate selected sound-level distinctions in the audio.

For example, the system might investigate whether it can distinguish a target dental consonant from a retroflex consonant. To make that assessment, it must know the expected sound, locate its audio interval, extract relevant acoustic evidence, and compare the result with examples whose labels have been verified.

A system that only compares complete recordings or recognized text does not, by itself, establish sound-level pronunciation evaluation.

---

## 3. Objectives and Scope

### 3.1 Primary objectives

1. Build a standalone and reproducible audio-processing application.
2. Define a verified Sanskrit text-to-phonetic-unit representation for one selected mantra.
3. Create or obtain a small dataset of recordings with reliable annotations.
4. Implement audio preprocessing and phoneme/segment alignment.
5. Establish an interpretable baseline for selected pronunciation distinctions.
6. Evaluate the baseline against expert-annotated data.
7. Provide localized feedback with an `inconclusive` outcome when evidence is insufficient.
8. Document limitations and avoid overstating capability.

### 3.2 Minimum viable project (MVP)

- One selected mantra or a small set of short phrases.
- Verified Devanagari text and a documented phonetic representation.
- Multiple speakers where possible.
- One or two target phonetic contrasts initially.
- Reference examples, preferably from more than one acceptable speaker.
- Manual verification of at least a subset of phoneme boundaries.
- A baseline model and reproducible evaluation script.
- A simple upload interface or command-line demo.

### 3.3 Out of scope for the first version

Do not attempt all of the following simultaneously: unrestricted Sanskrit ASR, every Sanskrit phoneme, all Vedic recitation traditions, full `udātta`/`anudātta`/`svarita` evaluation, speaker identification, training a large speech model from scratch, real-time streaming, mobile deployment, or a universal chanting-correctness score.

These could be future extensions, but each adds data, modelling, and validation requirements.

### 3.4 Separate phonetics from Vedic svara

The first model should focus on **segmental phonetics**: consonants, vowels, aspiration, place of articulation, duration, and related sound-level properties.

Vedic svara and chant prosody are distinct, although related. Correct phoneme production does not automatically imply correct Vedic accent. Pitch deviation alone does not prove a phonetic error. Treat svara evaluation as a separate future module unless the team explicitly chooses it as a second objective.

---

## 4. Proposed System Architecture

Build each module independently so it can be tested in isolation.

```text
User
 |
 | Sanskrit text + audio recording
 v
Frontend (upload / record / results)
 |
 v
Backend API
 |
 +--> Audio validation and preprocessing
 |
 +--> Sanskrit text normalization
 |       |
 |       v
 |    Phonetic-unit sequence
 |
 +--> Alignment module
 |       |
 |       v
 |    Time spans for relevant units
 |
 +--> Feature extraction
 |       |
 |       v
 |    Acoustic features / speech embeddings
 |
 +--> Pronunciation evaluator
 |       |
 |       v
 |    Per-unit scores, confidence, explanation
 |
 +--> Report generation
         |
         v
    Results returned to frontend
```

### Design principles

- **Independent modules:** normalization, alignment, feature extraction, scoring, and reporting should have separate interfaces.
- **Known text first:** use a verified target transcript for the MVP instead of depending on automatic transcription as the only source of truth.
- **Reproducibility:** record configurations, model versions, and data splits.
- **Transparent output:** separate acoustic measurements from the final interpretation.
- **Safe failure:** poor audio or alignment should return a warning or an inconclusive result rather than an invented score.
- **Versioned rules:** document thresholds and scoring logic.

---

## 5. Recommended Technology Stack

| Component | Candidate technology | Purpose |
|---|---|---|
| Language | Python | Audio analysis, modelling, API |
| Numerical processing | NumPy | Arrays and calculations |
| Audio analysis | Librosa | Loading, resampling, spectrograms, pitch/onset features |
| Signal processing | SciPy | Filters and additional signal processing |
| Audio I/O | SoundFile | Reading/writing audio |
| Baseline features | Librosa / SciPy | MFCCs, energy, spectral features, durations |
| Classical ML | scikit-learn | Baseline classifiers, scaling, metrics, cross-validation |
| Deep learning, if justified | PyTorch | Training/fine-tuning a small model |
| Pretrained encoders, optional | Hugging Face Transformers | Testing speech representations |
| Backend | FastAPI + Uvicorn | Upload endpoint and analysis service |
| Frontend | React + Vite, or Streamlit | Recording/uploading audio and showing feedback |
| Annotation | Praat or a suitable waveform/TextGrid editor | Manual phoneme boundaries and expert labels |
| Testing | pytest | Unit and integration tests |
| Version control | Git | Code history and collaboration |

### Important model-selection rule

Do not start with a large model by default. First test whether an acoustic-feature baseline can solve the narrow task. Add a pretrained encoder only if it is suitable for the data and can be compared fairly.

A multilingual speech model may provide useful representations, but multilingual coverage does not guarantee reliable Sanskrit phoneme discrimination. A model trained for transcription is not automatically a pronunciation evaluator. Test the candidate model on the exact target task before committing to it.

---

## 6. Dataset and Annotation Plan

The quality of the annotations and the diversity of recordings are central to project success.

### 6.1 Metadata to store

For each recording, store:

- unique recording ID;
- audio path and format;
- sample rate and channel count;
- pseudonymous speaker ID;
- verified Sanskrit text;
- normalized text used by the pipeline;
- phonetic-unit sequence;
- target sound/contrast;
- start and end time for annotated units where available;
- expert label and notes;
- annotation confidence or uncertainty;
- recording conditions where known;
- split assignment (`train`, `validation`, or `test`).

Keep personally identifying information out of the dataset. Obtain consent to record, store, and evaluate participants' voices.

### 6.2 Annotation types

**Alignment labels** state where a unit begins and ends in the waveform:

```json
{
  "recording_id": "rec_001",
  "unit": "target_phone",
  "start_seconds": 1.24,
  "end_seconds": 1.39
}
```

**Pronunciation labels** describe the relevant sound according to an explicit annotation guide. A small label set might be:

- `acceptable`
- `target_deviation`
- `uncertain`

A qualified annotator must define these labels for the chosen contrast. Do not use the model's own predictions as ground truth.

### 6.3 Data collection process

1. Select one mantra with stable, verified text.
2. Choose one or two feasible phonetic contrasts.
3. Record repetitions from multiple consenting speakers.
4. Include clear examples and natural variation; avoid culturally inappropriate or unsafe recording instructions.
5. Have a qualified annotator review the relevant segments.
6. Double-annotate a subset and measure agreement.
7. Split by **speaker**, not just random recording, so the test set contains voices not used for training.

A small dataset may support a proof of concept, but not necessarily a robust deep model. Report sample counts and limitations honestly.

### 6.4 Train, validation, and test data

- **Training:** fit model parameters.
- **Validation:** select hyperparameters and thresholds.
- **Test:** final evaluation only.

Keep speakers separated across splits whenever feasible. Do not tune thresholds against test results.

---

## 7. Sanskrit Text Normalization and Phonetic Representation

The system needs a text-to-phonetic-unit module before it can evaluate individual sounds.

### 7.1 Input normalization

Sanskrit text can include Unicode combining marks, vowel signs, punctuation, spaces, and orthographic conventions. Implement normalization cautiously.

The module should:
1. normalize Unicode consistently;
2. preserve meaningful Devanagari distinctions;
3. normalize irrelevant punctuation/whitespace without changing phonetic content;
4. handle vowel signs, conjunct consonants, and virāma/halant consistently;
5. preserve relevant nasalization, visarga, aspiration-related distinctions, and Vedic notation;
6. report unsupported or ambiguous input rather than silently deleting it.

Do not remove diacritics or map distinct sounds to the same symbol merely for convenience.

### 7.2 Grapheme-to-phonetic-unit conversion

Build a documented rule-based mapping for the selected mantra and phonetic inventory, reviewed by a Sanskrit expert. It should explicitly define handling for:

- independent vowels;
- consonants and inherent vowels;
- dependent vowel signs;
- virāma/halant;
- conjunct consonants;
- anusvāra and candrabindu;
- visarga;
- word boundaries;
- relevant Vedic accent marks.

A simple character-by-character split is not a reliable phonetic transcription. Orthography and actual pronunciation require a documented mapping.

### 7.3 Keep three layers separate

1. **Orthographic unit:** what is written in Devanagari.
2. **Phonetic unit:** the expected sound or sound sequence under the chosen convention.
3. **Acoustic segment:** the time interval in the recording.

The pipeline must link these layers transparently.

---

## 8. Audio Preprocessing

Build preprocessing as a deterministic module and record every transformation.

### Steps

1. Validate supported audio types.
2. Reject files outside configured size or duration limits.
3. Decode audio safely.
4. Convert to mono for the initial baseline if required by the selected method.
5. Resample to the documented sample rate where necessary.
6. Detect empty audio, clipping, extreme low level, and excessive silence.
7. Preserve the original file for replay/audit and analyze a processed copy.
8. Store preprocessing metadata with results.

Do not treat a noisy recording as a pronunciation error. When quality is too poor, return a warning or inconclusive status.

Example processing metadata:

```json
{
  "original_sample_rate": 48000,
  "analysis_sample_rate": 16000,
  "channels": 1,
  "duration_seconds": 8.42,
  "clipping_detected": false,
  "quality_status": "usable"
}
```

These values illustrate a schema; select the actual sample rate based on the method or model being used.

---

## 9. Alignment: Mapping Audio to Expected Sounds

Alignment is one of the hardest components. Features must be extracted from the correct part of the recording.

### 9.1 Manual reference boundaries first

For a small initial dataset, manually annotate a subset of reference recordings in a waveform tool. This provides a trusted baseline to test automated alignment against. Store start/end times, annotation notes, and expert-reviewed boundaries.

### 9.2 Alignment options to investigate

- **Manual alignment:** slow but valuable for ground truth.
- **Forced alignment:** aligns a known transcript using a pronunciation dictionary and acoustic model. A suitable Sanskrit acoustic model/dictionary may need to be created or trained; do not assume that a ready-made model exists.
- **Feature-based sequence alignment:** Dynamic Time Warping (DTW) can align two acoustic feature sequences with different timing. DTW alone does not identify phoneme boundaries and does not prove that pronunciation is correct.
- **Custom alignment model:** a later option if a suitable annotated dataset becomes available.

### 9.3 Track alignment confidence

If a segment is implausibly short/long, unvoiced unexpectedly, or inconsistent with manual annotation, mark the evaluation low confidence or inconclusive. Do not turn uncertain alignment into a confident error label.

---

## 10. Feature Extraction

No single feature evaluates every phoneme. Select features to match the chosen contrast.

### 10.1 MFCCs

Mel-Frequency Cepstral Coefficients summarize aspects of the short-time spectral envelope. They can provide a general acoustic baseline.

Possible uses:
- compare the same target segment in reference and user audio;
- train a small classifier on annotated segments;
- establish a baseline before testing pretrained embeddings.

Limitations: MFCCs are not phoneme labels, and speaker/microphone variation can be substantial. Two acceptable speakers can differ acoustically.

### 10.2 Formants

Formants can help characterize vowel quality. Candidate features include formant frequencies and trajectories during stable vowel regions.

Limitations: automatic formant tracking may fail with noisy audio or some voices. Formants are primarily useful for vowel analysis, not a universal solution for consonants. Check measurements against known examples and expert annotation.

### 10.3 Voice Onset Time (VOT)

VOT describes timing between a stop-consonant release and the onset of voicing. It may help investigate aspiration-related distinctions.

Limitations: boundaries can be difficult to detect automatically, and expected patterns vary with context, speaker, and pronunciation convention. Thresholds must be learned or validated on actual data, not guessed.

### 10.4 Duration

Duration can help examine short/long vowel distinctions and selected timing properties. Normalize carefully: a slower recitation may lengthen many units. Compare local durations with suitable references without assuming that all slow chanting is incorrect.

### 10.5 Pitch

Pitch/F0 can be useful for separate prosodic or Vedic svara work. It should not be treated as the primary evidence for most segmental consonant distinctions.

### 10.6 Pretrained embeddings (optional)

A pretrained speech encoder may provide useful representations. Compare it with the acoustic baseline using the same speaker-independent split. Check language/phonetic compatibility, licensing, preprocessing, memory use, latency, and whether the training objective suits phonetic assessment.

---

## 11. Model Strategy: From Baseline to ML

Do not train a large neural network from scratch at the beginning. Implement a measurable baseline first.

### Stage A — Deterministic feature baseline

For the chosen contrast, calculate interpretable acoustic measurements and apply documented rules. For instance, a narrowly defined task might use duration and relevant acoustic measurements to distinguish two classes. The appropriate features depend on the contrast and must be verified on actual data.

### Stage B — Classical machine-learning baseline

Train a small classifier on annotated segments. Possible candidates include logistic regression, support vector machines, or random forests, depending on the dataset and features.

1. Extract feature vectors for annotated segments.
2. Fit normalization on training data only.
3. Train using training speakers.
4. Tune hyperparameters and thresholds using validation speakers.
5. Evaluate once on held-out test speakers.
6. Compare with the rule-based baseline.

### Stage C — Pretrained speech representations

If the classical baseline is limited and the dataset supports a fair experiment, extract embeddings from a suitable pretrained speech encoder and train a small classifier on top.

Before selecting a model, check:
- supported language/adapter and phonetic inventory;
- model and dataset licenses;
- sample rate and preprocessing requirements;
- inference memory and latency;
- performance on relevant Sanskrit speech/chanting;
- suitability of the training objective for pronunciation assessment.

### Stage D — Fine-tuning (optional)

Fine-tune only if you have enough well-annotated data and a clear reason. Keep a frozen-encoder baseline for comparison.

### Suggested output per unit

- target phonetic unit;
- predicted class/assessment;
- confidence or calibrated probability where available;
- relevant acoustic measurements;
- alignment confidence;
- final status: `acceptable`, `review`, or `inconclusive`;
- explanation of the method used.

Never display a hard correctness score when the model is uncertain.

---

## 12. Scoring and Feedback

Do not assign arbitrary weights to multiple signals before validating them.

### Unit-level assessment

Keep these fields separate:
- alignment confidence;
- raw acoustic features;
- predicted class/probability;
- decision threshold and model version;
- final feedback status.

### User-facing outcomes

- **No major deviation detected:** evidence is consistent with accepted examples for the selected task.
- **Needs review:** the model detects a pattern associated with the target deviation.
- **Inconclusive:** alignment, audio quality, or confidence is insufficient.

Define these labels in the annotation and evaluation protocol. Do not suggest more certainty than the system has earned.

### Avoid a universal score in the MVP

A single overall Sanskrit pronunciation score can hide differences among sound classes and create false confidence. Start with per-contrast metrics and localized feedback. Consider an aggregate score only after component-level performance and calibration are understood.

---

## 13. Evaluation Plan

Evaluation must be part of development, not an afterthought.

### 13.1 Alignment metrics

Compare predicted boundaries with manually verified timestamps. Report:
- mean absolute boundary error in milliseconds;
- median absolute boundary error;
- percentage of boundaries within predefined tolerances, such as 20 ms or 50 ms if appropriate for the task.

Choose tolerances before inspecting the held-out test results.

### 13.2 Classification metrics

For each target contrast, report:
- precision;
- recall;
- F1-score;
- confusion matrix;
- count/support for each class;
- per-speaker performance where possible.

Accuracy alone can mislead when one class is much more common.

### 13.3 Calibration and abstention

Check whether confidence tracks correctness. Report performance at different abstention rates. An `inconclusive` result may be preferable to confidently incorrect feedback.

### 13.4 Expert agreement

Have qualified annotators label the same subset independently. Report agreement and resolve conflicts using a documented procedure. Preserve ambiguous cases rather than forcing consensus without explanation.

### 13.5 Baseline comparisons

At minimum, compare:
1. a rule-based acoustic baseline;
2. a classical classifier;
3. a pretrained-embedding model only if feasible.

Use the same split for all methods.

### 13.6 Prevent data leakage

- Split by speaker rather than splitting frames from the same speaker across train and test.
- Keep repeated versions of the same recording in one split.
- Fit scalers and feature selection only on training data.
- Tune thresholds only on validation data.
- Keep the test set untouched until final evaluation.

---

## 14. API Contract

Keep the first endpoint simple.

### Endpoint

`POST /analyze`

Input:
- audio file;
- target mantra ID or verified target text;
- optional analysis profile.

The backend validates the request, runs the pipeline, and returns a structured result.

Example response (illustrative schema, not a real prediction):

```json
{
  "analysis_id": "analysis_example_001",
  "status": "completed",
  "target_id": "mantra_001",
  "audio_quality": {
    "status": "usable",
    "warnings": []
  },
  "phonetic_evaluation": {
    "model_version": "baseline_0.1",
    "units": [
      {
        "unit_id": "unit_001",
        "expected_phoneme": "example_phone",
        "start_seconds": 1.24,
        "end_seconds": 1.39,
        "alignment_confidence": 0.88,
        "status": "review",
        "reason": "Illustrative explanation only"
      }
    ],
    "summary": {
      "evaluated_units": 1,
      "review_units": 1,
      "inconclusive_units": 0
    }
  }
}
```

The example values are not model outputs or performance claims.

### Error handling

Handle invalid/unsupported audio, files that are too short/long, missing text, unsupported characters, alignment failure, model-loading failure, poor audio quality, and internal errors.

If the module cannot evaluate a recording, return a clear error or inconclusive status. Do not silently return a perfect score.

---

## 15. Suggested Repository Structure

```text
sanskrit-phonetic-evaluator/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── configs/
│   ├── audio.yaml
│   ├── phonetic_inventory.yaml
│   └── evaluation.yaml
├── data/
│   ├── README.md
│   ├── raw/                  # consented recordings; keep private by default
│   ├── processed/
│   ├── annotations/
│   └── splits/
├── docs/
│   ├── problem_definition.md
│   ├── annotation_guidelines.md
│   ├── phonetic_inventory.md
│   ├── model_card.md
│   └── experiment_log.md
├── notebooks/
│   ├── 01_audio_exploration.ipynb
│   ├── 02_feature_baseline.ipynb
│   └── 03_error_analysis.ipynb
├── scripts/
│   ├── validate_dataset.py
│   ├── extract_features.py
│   ├── train_baseline.py
│   └── evaluate_model.py
├── src/
│   └── sanskrit_phonetics/
│       ├── __init__.py
│       ├── audio_io.py
│       ├── preprocessing.py
│       ├── text_normalization.py
│       ├── grapheme_to_phoneme.py
│       ├── alignment.py
│       ├── features.py
│       ├── dataset.py
│       ├── labels.py
│       ├── baseline.py
│       ├── scoring.py
│       ├── reporting.py
│       └── api/
│           ├── main.py
│           └── schemas.py
├── frontend/                 # optional; add after the CLI baseline works
├── tests/
│   ├── test_audio_io.py
│   ├── test_normalization.py
│   ├── test_grapheme_to_phoneme.py
│   ├── test_alignment.py
│   ├── test_scoring.py
│   └── test_api.py
└── outputs/
    ├── metrics/
    └── error_analysis/
```

Keep raw voice recordings out of public repositories unless participants explicitly consent to public release and the license permits it. Never commit secret keys or private participant information.

---

## 16. Module Responsibilities

### `audio_io.py`
Load supported files, validate duration/channels, reject invalid files safely, and retain metadata.

### `preprocessing.py`
Resample if needed, prepare the analysis signal, detect clipping/silence/quality issues, and return preprocessing metadata.

### `text_normalization.py`
Normalize Unicode and whitespace while preserving meaningful phonetic and Vedic notation. Explicitly flag unsupported input.

### `grapheme_to_phoneme.py`
Convert selected Sanskrit text to the defined phonetic inventory, apply documented orthographic rules, and provide unit tests for supported cases.

### `alignment.py`
Align audio with expected units, track confidence, and support manual reference boundaries for early experiments.

### `features.py`
Extract features relevant to the selected contrast, return timestamps/configuration, and avoid embedding final correctness decisions in feature extraction.

### `dataset.py`
Load annotations, verify IDs/labels, create speaker-independent splits, and detect duplicates or leakage.

### `baseline.py`
Train and run the rule-based/classical baseline with correct training-only fitting of preprocessing steps.

### `scoring.py`
Convert predictions and thresholds into cautious feedback categories and support uncertain results.

### `reporting.py`
Return JSON and interpretable explanations, separating measured features from model judgments.

### `api/main.py`
Define the upload endpoint, validate requests, invoke the pipeline, and return schema-validated responses.

---

## 17. Development Roadmap

Use milestone gates. Do not move to complex modelling until earlier work has a functioning test and documented output.

### Phase 1 — Define the task
- Select one mantra.
- Select one or two phonetic contrasts.
- Define target labels and what they mean.
- Consult a Sanskrit/phonetics expert.
- Specify the evaluation protocol.

**Deliverable:** `problem_definition.md` and `annotation_guidelines.md`.

### Phase 2 — Dataset and annotations
- Collect consented recordings.
- Verify text and phonetic representation.
- Manually annotate a small set of segments.
- Have a second annotator review a subset.
- Create speaker-separated splits.

**Deliverable:** dataset manifest, annotations, and annotation-quality report.

### Phase 3 — Audio and text pipeline
- Implement loading and validation.
- Implement normalization and phonetic conversion.
- Extract features and create plots for manual inspection.
- Add unit tests.

**Deliverable:** a reproducible command-line script that produces validated features from audio.

### Phase 4 — Alignment baseline
- Establish manual reference boundaries.
- Investigate suitable alignment methods.
- Compare automated alignment with annotations.
- Reject low-confidence alignments.

**Deliverable:** boundary-alignment report.

### Phase 5 — Pronunciation baseline
- Implement contrast-specific features/rules.
- Train a classical classifier if labels support it.
- Tune on validation speakers.
- Evaluate once on held-out test speakers.

**Deliverable:** model, metrics, confusion matrix, and error analysis.

### Phase 6 — Application interface
- Implement the API.
- Return localized feedback and confidence.
- Add a minimal UI.
- Test invalid audio and failure paths.

**Deliverable:** end-to-end prototype.

### Phase 7 — Improvement and comparison
- Identify dominant error sources.
- Add pretrained embeddings only if justified.
- Compare methods using the same data split.
- Document improved, unchanged, and degraded cases.

**Deliverable:** experiment report, model card, and reproducible scripts.

---

## 18. Three-Person Team Division

Adapt this to team strengths, but assign each person concrete outputs.

### Member 1 — Sanskrit representation and dataset
- choose target mantra and contrast;
- define text normalization and phonetic inventory;
- coordinate expert review;
- manage recording metadata and annotations;
- create dataset-validation tests.

**Deliverables:** verified text, phonetic mapping, annotation guide, dataset manifest.

### Member 2 — Audio, alignment, and features
- implement audio I/O and preprocessing;
- inspect waveforms and spectrograms;
- extract features relevant to the target contrast;
- test alignment methods;
- calculate boundary-error metrics.

**Deliverables:** feature extraction module, alignment module, boundary report.

### Member 3 — Model, evaluation, API/interface
- implement rule-based or classical baseline;
- build speaker-independent training/evaluation scripts;
- track metrics and error analysis;
- implement FastAPI and output schema;
- build a minimal result view or CLI report.

**Deliverables:** baseline model, evaluation report, API, demonstration.

All members should review the task definition and evaluation protocol together. Consistent labels and usable annotations are essential to model performance.

---

## 19. Risks and Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Too little annotated data | Model may overfit examples or speakers | Narrow the task and report limitations |
| Inconsistent expert labels | Unreliable ground truth | Document guidelines; double-annotate a subset |
| Incorrect text-to-phoneme mapping | All downstream scoring becomes unreliable | Expert review and unit tests |
| Poor alignment | Features may be extracted from the wrong interval | Measure boundary error; allow inconclusive results |
| Speaker/microphone variation | Acceptable speech may be flagged | Record multiple speakers; test unseen speakers |
| ASR model used as evaluator | Transcription ability does not guarantee pronunciation evaluation | Test the actual target task |
| No suitable Sanskrit pretrained model | Integration could waste time without improvement | Maintain a rule-based/classical baseline |
| False feedback | Users may be told correct pronunciation is wrong | Calibrate, allow abstention, seek expert validation |
| Scope creep | Too many distinctions make evaluation infeasible | Start with one mantra and one or two contrasts |
| Voice-data privacy | Recordings can identify speakers | Consent, access control, retention rules, secure storage |

---

## 20. What Counts as Success?

### Minimum successful outcome
- Working pipeline from audio to localized output.
- Verified phonetic representation for the selected target.
- Expert-annotated evaluation data.
- Speaker-independent baseline evaluation.
- Alignment and classification metrics.
- Documented failure cases and limitations.
- Reproducible setup and scripts.

### Stronger outcome
- Fair comparison of multiple methods.
- Better results on held-out speakers.
- Confidence-aware feedback with an inconclusive state.
- Agreement analysis against expert labels.
- Error analysis explaining when and why the system fails.

### Claims to avoid unless supported by evidence
- “The model understands Sanskrit perfectly.”
- “It detects every pronunciation error.”
- “A high score means chanting is completely correct.”
- “It works for all Vedic traditions and all speakers.”
- “A pretrained multilingual model guarantees Sanskrit accuracy.”
- “The system is better than previous projects” without a fair, direct evaluation.

---

## 21. Immediate Next Steps

Before writing the main model, complete these decisions:

1. Select the exact mantra and one or two target contrasts.
2. Confirm the phonetic convention with a qualified expert.
3. Check that annotators can consistently label the chosen contrasts.
4. Collect a small, consented pilot dataset from more than one speaker.
5. Build the dataset validator and audio pipeline.
6. Create manually verified reference boundaries.
7. Implement the simplest baseline.
8. Measure errors, then choose what model to try next.

**The first concrete milestone should be a small end-to-end experiment for one contrast—not a full application or a large model.**

---

## 22. Technical References

These docs explain relevant tools and methods; they do **not** establish that a tool already supports Sanskrit chanting or will perform well for this project.

1. **Librosa `pyin` documentation** — F0 estimation, voiced flags, and voiced probabilities:  
   https://librosa.org/doc/main/generated/librosa.pyin.html

2. **Librosa F0 tutorial** — examples and limitations of pitch estimation:  
   https://librosa.org/doc/main/auto_tutorials/01-intro/03-f0.html

3. **Hugging Face Transformers — MMS documentation** — multilingual speech models and language adapters; verify actual language/phonetic suitability:  
   https://huggingface.co/docs/transformers/model_doc/mms

4. **Montreal Forced Aligner documentation** — forced alignment uses a transcript, pronunciation dictionary, and acoustic model; do not assume ready-made Sanskrit support:  
   https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/index.html

5. **Praat documentation** — useful for inspecting speech signals and checking phonetic measurements:  
   https://www.fon.hum.uva.nl/praat/manual/

Before using a model, tool, or dataset in a public project, check its current license, dependencies, and compatibility.

---

## Final Project Definition

Build a **standalone Sanskrit phonetic pronunciation evaluator** in a new codebase. For a carefully selected mantra and a small number of sound distinctions, create a verified text-to-phonetic representation, obtain annotated recordings, align and analyze the audio, develop a transparent baseline, and measure its performance against expert labels. Expand to more sounds, pretrained embeddings, and broader Vedic chanting evaluation only after the first experiment works and its limitations are understood.
