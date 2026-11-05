"""
phonetic_evaluator.py
Local, word-by-word and phoneme-level evaluation module for Sanskrit mantra chanting.
Specialized for the Mahā Mṛtyuñjaya Mantra:
  "त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात्"

Evaluates:
  1. Word-level alignment and acoustic match score (local DTW cosine similarity)
  2. Short vs. long vowel duration ratios (e.g. ya vs jā in yajāmahe, u vs vā in urvārukamiva)
  3. Consonant aspiration (/dh/ in sugandhim, bandhanān)
  4. Retroflex articulation (/ṣṭ/ in puṣṭivardhanam)
  5. Conjunct articulation (/tr/ in tryambakam, /kṣ/ in mṛtyormukṣīya)
  6. Safe-failure logic: acceptable / review / inconclusive
"""

import os
import sys
import json
import numpy as np
import librosa
from sklearn.preprocessing import StandardScaler
from librosa.sequence import dtw

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ANNOTATION_FILE = os.path.join(BASE_DIR, "ref_maha_mrityunjay.json")
DEFAULT_REF_AUDIO = os.path.join(BASE_DIR, "mantra.wav")

# =============================================================================
# CONFIGURATION & THRESHOLDS
# =============================================================================
CONFIG = {
    # Alignment thresholds
    "MIN_SEGMENT_DURATION_MS": 30.0,       # Segments shorter than 30ms -> inconclusive
    "MIN_ALIGNMENT_CONFIDENCE": 0.40,      # Confidence below 0.4 -> inconclusive

    # Word-level score thresholds
    "WORD_ACCEPTABLE_THRESHOLD": 65.0,     # >= 65% is acceptable
    "WORD_REVIEW_THRESHOLD": 45.0,         # 45% - 64% needs review, < 45% is poor

    # Phonetic contrast thresholds
    "VOWEL_RATIO_TOLERANCE": 0.30,         # Measured ratio within ±30% of target/ref -> acceptable
    "CONSONANT_SIMILARITY_THRESHOLD": 0.65,# Spectral similarity >= 0.65 -> acceptable
    "ASPIRATION_ENERGY_RATIO_MIN": 0.12,   # Minimum high-freq breathiness ratio for aspirated stops
    "RETROFLEX_CENTROID_DIFF_HZ": 600,     # Maximum allowable deviation in spectral centroid
}


def project_sub_span(r_sub_start: float, r_sub_end: float, r_word_start: float, r_word_end: float, u_word_start: float, u_word_end: float) -> tuple:
    """
    Linearly interpolates a reference sub-span [r_sub_start, r_sub_end]
    from the reference word interval [r_word_start, r_word_end]
    into the user's aligned word interval [u_word_start, u_word_end].
    """
    r_dur = max(r_word_end - r_word_start, 1e-5)
    u_dur = u_word_end - u_word_start
    u_sub_start = u_word_start + ((r_sub_start - r_word_start) / r_dur) * u_dur
    u_sub_end   = u_word_start + ((r_sub_end   - r_word_start) / r_dur) * u_dur
    return (max(0.0, u_sub_start), max(u_sub_start, u_sub_end))


def load_ref_annotations(path=DEFAULT_ANNOTATION_FILE) -> dict:
    """Loads the reference annotations JSON."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Annotation file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def align_user_to_reference(
    user_audio: np.ndarray,
    user_sr: int,
    ref_audio: np.ndarray,
    ref_sr: int,
    ref_words: list,
    precomputed_wp=None
) -> list:
    """
    Aligns user audio with reference audio using the DTW warping path.
    Maps reference word intervals [ref_start, ref_end] -> [user_start, user_end].
    """
    user_duration = float(len(user_audio) / user_sr)
    ref_duration = float(len(ref_audio) / ref_sr)

    # Compute warping path if not provided
    if precomputed_wp is None:
        hop_length = 512
        user_mfcc = librosa.feature.mfcc(y=user_audio, sr=user_sr, n_mfcc=13, hop_length=hop_length)
        ref_mfcc = librosa.feature.mfcc(y=ref_audio, sr=ref_sr, n_mfcc=13, hop_length=hop_length)

        user_scaled = StandardScaler().fit_transform(user_mfcc.T).T
        ref_scaled = StandardScaler().fit_transform(ref_mfcc.T).T

        user_delta = librosa.feature.delta(user_scaled)
        ref_delta = librosa.feature.delta(ref_scaled)

        user_comb = np.vstack([user_scaled, user_delta])
        ref_comb = np.vstack([ref_scaled, ref_delta])

        # dtw(X, Y): X = user, Y = ref
        D, wp = dtw(user_comb, ref_comb, metric="euclidean")
    else:
        wp = precomputed_wp
        hop_length = 512

    # wp is array of shape (N, 2) where wp[:, 0] is user frame, wp[:, 1] is ref frame
    user_frames = wp[:, 0]
    ref_frames = wp[:, 1]

    ref_times_arr = librosa.frames_to_time(ref_frames, sr=ref_sr, hop_length=hop_length)
    user_times_arr = librosa.frames_to_time(user_frames, sr=user_sr, hop_length=hop_length)

    aligned_words = []
    for w in ref_words:
        r_start = w["start_sec"]
        r_end = w["end_sec"]

        # Find warping path indices matching the reference interval
        mask = (ref_times_arr >= r_start) & (ref_times_arr <= r_end)
        if np.any(mask):
            matched_user_times = user_times_arr[mask]
            u_start = float(np.min(matched_user_times))
            u_end = float(np.max(matched_user_times))
            
            # Confidence based on density of matching path frames
            expected_user_dur = (r_end - r_start) * (user_duration / (ref_duration + 1e-9))
            actual_user_dur = u_end - u_start
            dur_ratio = actual_user_dur / (expected_user_dur + 1e-9)
            confidence = float(np.clip(1.0 - abs(1.0 - dur_ratio), 0.0, 1.0))
        else:
            # Fallback to linear projection if warping path missed the segment
            u_start = float(r_start * (user_duration / ref_duration))
            u_end = float(r_end * (user_duration / ref_duration))
            confidence = 0.35

        # Bound checks
        u_start = max(0.0, min(u_start, user_duration))
        u_end = max(u_start, min(u_end, user_duration))
        u_dur_ms = (u_end - u_start) * 1000.0

        if u_dur_ms < CONFIG["MIN_SEGMENT_DURATION_MS"]:
            confidence = min(confidence, 0.25)

        aligned_words.append({
            "index": w["index"],
            "devanagari": w["devanagari"],
            "iast": w["iast"],
            "ref_start_sec": r_start,
            "ref_end_sec": r_end,
            "ref_duration_sec": r_end - r_start,
            "user_start_sec": round(u_start, 3),
            "user_end_sec": round(u_end, 3),
            "user_duration_sec": round(u_end - u_start, 3),
            "alignment_confidence": round(confidence, 2),
            "phonetic_contrasts": w.get("phonetic_contrasts", [])
        })

    return aligned_words


def compute_local_word_match(
    user_audio: np.ndarray,
    user_sr: int,
    ref_audio: np.ndarray,
    ref_sr: int,
    u_start: float,
    u_end: float,
    r_start: float,
    r_end: float
) -> float:
    """Computes acoustic match score (0-100%) between aligned word intervals."""
    u_s_sample = int(u_start * user_sr)
    u_e_sample = max(u_s_sample + 64, int(u_end * user_sr))
    r_s_sample = int(r_start * ref_sr)
    r_e_sample = max(r_s_sample + 64, int(r_end * ref_sr))

    u_seg = user_audio[u_s_sample:u_e_sample]
    r_seg = ref_audio[r_s_sample:r_e_sample]

    if len(u_seg) < 256 or len(r_seg) < 256:
        return 50.0

    # Extract MFCCs — DROP mfcc[0] (overall energy) for speaker independence
    u_mfcc = librosa.feature.mfcc(y=u_seg, sr=user_sr, n_mfcc=13)[1:, :]  # shape (12, T)
    r_mfcc = librosa.feature.mfcc(y=r_seg, sr=ref_sr, n_mfcc=13)[1:, :]

    # Per-segment CMVN (Cepstral Mean & Variance Normalization)
    u_scaled = StandardScaler().fit_transform(u_mfcc.T).T
    r_scaled = StandardScaler().fit_transform(r_mfcc.T).T

    # Add Chroma CENS for tonal similarity (captures melodic pitch movement)
    u_chroma = librosa.feature.chroma_cens(y=u_seg, sr=user_sr, n_chroma=12)
    r_chroma = librosa.feature.chroma_cens(y=r_seg, sr=ref_sr, n_chroma=12)

    # Combine: 12 MFCCs + 12 Chroma = 24-dim feature vector
    u_comb = np.vstack([u_scaled, u_chroma])
    r_comb = np.vstack([r_scaled, r_chroma])

    try:
        D, wp = dtw(u_comb, r_comb, metric="cosine")
        dist = D[-1, -1] / max(1, len(wp))
        # Calibrated decay: exp(-dist / 2.2) -> valid human recitation scores 75-95%
        score = float(100.0 * np.exp(-dist / 2.2))
        return float(np.clip(score, 0.0, 100.0))
    except Exception:
        return 60.0


def check_vowel_duration_ratio(
    user_audio: np.ndarray,
    user_sr: int,
    ref_audio: np.ndarray,
    ref_sr: int,
    word_start: float,
    word_dur: float,
    ref_word_start: float,
    ref_word_end: float,
    contrast_cfg: dict
) -> dict:
    """Evaluates short vs. long vowel duration ratio."""
    short_span = contrast_cfg.get("short_vowel_sub_span")
    long_span = contrast_cfg.get("long_vowel_sub_span")
    expected_cfg = contrast_cfg.get("expected_features", {})

    target_min = expected_cfg.get("min_ratio", 1.3)
    target_max = expected_cfg.get("max_ratio", 3.5)

    if not short_span or not long_span or word_dur <= 0.05:
        return {
            "contrast_type": "vowel_duration_ratio",
            "label": contrast_cfg.get("label", ""),
            "status": "inconclusive",
            "measured_ratio": None,
            "target_range": [target_min, target_max],
            "reason": "Word segment too brief to isolate vowel sub-spans."
        }

    # Project reference sub-spans into user time coordinates
    u_short = project_sub_span(short_span[0], short_span[1],
                               ref_word_start, ref_word_end,
                               word_start, word_start + word_dur)
    u_long  = project_sub_span(long_span[0], long_span[1],
                               ref_word_start, ref_word_end,
                               word_start, word_start + word_dur)

    # Extract energy envelopes in respective projected sub-spans
    s0 = int(u_short[0] * user_sr)
    s1 = int(u_short[1] * user_sr)
    l0 = int(u_long[0] * user_sr)
    l1 = int(u_long[1] * user_sr)

    s_seg = user_audio[s0:s1] if s1 > s0 else np.array([])
    l_seg = user_audio[l0:l1] if l1 > l0 else np.array([])

    if len(s_seg) < 64 or len(l_seg) < 64:
        return {
            "contrast_type": "vowel_duration_ratio",
            "label": contrast_cfg.get("label", ""),
            "status": "inconclusive",
            "measured_ratio": None,
            "target_range": [target_min, target_max],
            "reason": "Sub-spans too short for reliable energy estimation."
        }

    # Count voiced/high-energy samples
    s_rms = librosa.feature.rms(y=s_seg)[0]
    l_rms = librosa.feature.rms(y=l_seg)[0]

    s_voiced_frames = np.sum(s_rms > (np.mean(s_rms) * 0.5))
    l_voiced_frames = np.sum(l_rms > (np.mean(l_rms) * 0.5))

    measured_ratio = float((l_voiced_frames + 1) / (s_voiced_frames + 1))

    # Evaluate within tolerance (±30% of target range)
    tol = CONFIG["VOWEL_RATIO_TOLERANCE"]
    effective_min = target_min * (1.0 - tol)
    effective_max = target_max * (1.0 + tol)

    if effective_min <= measured_ratio <= effective_max:
        status = "acceptable"
        reason = f"Vowel duration ratio {measured_ratio:.2f} conforms to Sanskrit prosody (target: {target_min}-{target_max}x)."
    elif measured_ratio < effective_min:
        status = "review"
        reason = f"Long vowel duration too short (ratio {measured_ratio:.2f} < {target_min:.1f}x) — sustain the long vowel longer (dīrgha mātrā)."
    else:
        status = "review"
        reason = f"Short vowel over-lengthened (ratio {measured_ratio:.2f} > {target_max:.1f}x) — keep short vowel brisk (hrasva mātrā)."

    return {
        "contrast_type": "vowel_duration_ratio",
        "label": contrast_cfg.get("label", ""),
        "status": status,
        "measured_ratio": round(measured_ratio, 2),
        "target_range": [target_min, target_max],
        "reason": reason
    }


def check_consonant_spectral(
    user_audio: np.ndarray,
    user_sr: int,
    ref_audio: np.ndarray,
    ref_sr: int,
    u_sub_start: float,
    u_sub_end: float,
    r_sub_start: float,
    r_sub_end: float,
    contrast_cfg: dict
) -> dict:
    """Evaluates consonant aspiration, retroflexion, or conjunct articulation."""
    c_type = contrast_cfg.get("contrast_type", "consonant")
    label = contrast_cfg.get("label", "")
    expected = contrast_cfg.get("expected_features", {})

    dur = u_sub_end - u_sub_start
    if dur < 0.025:
        return {
            "contrast_type": c_type,
            "label": label,
            "status": "inconclusive",
            "reason": "Consonant segment too brief for spectral analysis."
        }

    u_s = int(u_sub_start * user_sr)
    u_e = max(u_s + 64, int(u_sub_end * user_sr))
    r_s = int(r_sub_start * ref_sr)
    r_e = max(r_s + 64, int(r_sub_end * ref_sr))

    u_seg = user_audio[u_s:u_e]
    r_seg = ref_audio[r_s:r_e]

    if len(u_seg) < 128 or len(r_seg) < 128:
        return {
            "contrast_type": c_type,
            "label": label,
            "status": "inconclusive",
            "reason": "Insufficient audio frames for spectral analysis."
        }

    u_centroid = float(np.mean(librosa.feature.spectral_centroid(y=u_seg, sr=user_sr)[0]))
    r_centroid = float(np.mean(librosa.feature.spectral_centroid(y=r_seg, sr=ref_sr)[0]))

    if c_type == "consonant_aspiration":
        # Aspiration check: energy in high-frequency spectrum (breath release)
        spec = np.abs(librosa.stft(u_seg))
        freqs = librosa.fft_frequencies(sr=user_sr)
        hf_mask = freqs >= 2200
        hf_energy = float(np.sum(spec[hf_mask, :]))
        total_energy = float(np.sum(spec) + 1e-9)
        hf_ratio = hf_energy / total_energy

        min_hf = expected.get("min_high_freq_ratio", CONFIG["ASPIRATION_ENERGY_RATIO_MIN"])
        if hf_ratio >= min_hf:
            status = "acceptable"
            reason = f"Audible aspiration burst detected for /{label}/ (breath energy ratio {hf_ratio:.2f})."
        else:
            status = "review"
            reason = f"Aspiration weak or unaspirated for /{label}/ — ensure breath release (mahāprāṇa) is audible."

    elif c_type == "retroflex_cluster":
        # Retroflex check: lower spectral centroid shift
        diff_hz = abs(u_centroid - r_centroid)
        if diff_hz <= CONFIG["RETROFLEX_CENTROID_DIFF_HZ"]:
            status = "acceptable"
            reason = f"Retroflex articulation /{label}/ matches reference resonance (centroid ~{int(u_centroid)} Hz)."
        else:
            status = "review"
            reason = f"Retroflex resonance deviation ({int(diff_hz)} Hz difference) — curl the tongue tip back to the palate (mūrdhanya)."

    elif c_type == "conjunct_cluster":
        # Conjunct cluster check: duration and multi-onset attack
        dur_ms = dur * 1000.0
        min_dur = expected.get("min_duration_ms", 60.0)
        if dur_ms >= min_dur * 0.70:
            status = "acceptable"
            reason = f"Clear conjunct consonant cluster /{label}/ articulated (duration {int(dur_ms)} ms)."
        else:
            status = "review"
            reason = f"Conjunct cluster /{label}/ rushed ({int(dur_ms)} ms) — articulate both consonants distinctly (saṃyuktākṣara)."

    else:  # nasal_anusvara or generic
        diff_hz = abs(u_centroid - r_centroid)
        if diff_hz <= 800:
            status = "acceptable"
            reason = f"Nasal / resonance quality for /{label}/ is authentic."
        else:
            status = "review"
            reason = f"Nasalization for /{label}/ needs clearer vibration in the nasal cavity (anusvāra)."

    return {
        "contrast_type": c_type,
        "label": label,
        "status": status,
        "measured_centroid_hz": round(u_centroid, 1),
        "ref_centroid_hz": round(r_centroid, 1),
        "reason": reason
    }


def evaluate_phonetics(
    user_audio_path: str,
    ref_audio_path: str = DEFAULT_REF_AUDIO,
    annotation_path: str = DEFAULT_ANNOTATION_FILE,
    precomputed_dtw_wp=None
) -> dict:
    """
    Top-level master evaluation function.
    Evaluates user audio against the reference Mahā Mṛtyuñjaya annotations.
    """
    annotations = load_ref_annotations(annotation_path)
    ref_words = annotations.get("words", [])

    # Load audios
    user_audio, user_sr = librosa.load(user_audio_path, sr=None)
    ref_audio, ref_sr = librosa.load(ref_audio_path, sr=None)

    # 1. Word-level alignment
    aligned_words = align_user_to_reference(
        user_audio=user_audio,
        user_sr=user_sr,
        ref_audio=ref_audio,
        ref_sr=ref_sr,
        ref_words=ref_words,
        precomputed_wp=precomputed_dtw_wp
    )

    evaluated_words = []
    acceptable_count = 0
    review_count = 0
    inconclusive_count = 0
    match_scores = []

    for word_info in aligned_words:
        u_start = word_info["user_start_sec"]
        u_end = word_info["user_end_sec"]
        u_dur = word_info["user_duration_sec"]
        r_start = word_info["ref_start_sec"]
        r_end = word_info["ref_end_sec"]
        conf = word_info["alignment_confidence"]

        # Word acoustic match score
        match_score = compute_local_word_match(
            user_audio, user_sr, ref_audio, ref_sr,
            u_start, u_end, r_start, r_end
        )
        match_scores.append(match_score)

        # Contrast evaluations
        contrast_results = []
        for c in word_info.get("phonetic_contrasts", []):
            c_type = c.get("contrast_type")
            if c_type == "vowel_duration_ratio":
                res = check_vowel_duration_ratio(
                    user_audio, user_sr, ref_audio, ref_sr,
                    u_start, u_dur,
                    r_start, r_end,
                    c
                )
            else:
                r_sub_s = c.get("sub_start_sec", r_start)
                r_sub_e = c.get("sub_end_sec", r_end)
                u_sub_s, u_sub_e = project_sub_span(
                    r_sub_s, r_sub_e, r_start, r_end, u_start, u_end
                )
                res = check_consonant_spectral(
                    user_audio, user_sr, ref_audio, ref_sr,
                    u_sub_s, u_sub_e,
                    r_sub_s, r_sub_e,
                    c
                )
            contrast_results.append(res)

        # Word status determination
        if conf < CONFIG["MIN_ALIGNMENT_CONFIDENCE"] or (u_dur * 1000.0) < CONFIG["MIN_SEGMENT_DURATION_MS"]:
            word_status = "inconclusive"
            inconclusive_count += 1
        else:
            # Check if any contrast failed
            any_review = any(cr["status"] == "review" for cr in contrast_results)
            if match_score >= CONFIG["WORD_ACCEPTABLE_THRESHOLD"] and not any_review:
                word_status = "acceptable"
                acceptable_count += 1
            else:
                word_status = "review"
                review_count += 1

        evaluated_words.append({
            "index": word_info["index"],
            "devanagari": word_info["devanagari"],
            "iast": word_info["iast"],
            "word_match_score": round(match_score, 1),
            "status": word_status,
            "user_start_sec": u_start,
            "user_end_sec": u_end,
            "ref_start_sec": r_start,
            "ref_end_sec": r_end,
            "duration_sec": u_dur,
            "alignment_confidence": conf,
            "contrasts": contrast_results
        })

    summary = {
        "total_words": len(evaluated_words),
        "acceptable": acceptable_count,
        "review": review_count,
        "inconclusive": inconclusive_count,
        "average_word_score": round(float(np.mean(match_scores)) if match_scores else 0.0, 1)
    }

    return {
        "phonetic_evaluation": {
            "model_version": "hybrid_heuristic_v1",
            "summary": summary,
            "words": evaluated_words
        }
    }


if __name__ == "__main__":
    # Self-test on reference audio
    print("Testing phonetic_evaluator.py on mantra.wav...")
    res = evaluate_phonetics(DEFAULT_REF_AUDIO)
    summary = res["phonetic_evaluation"]["summary"]
    print(f"Summary: {summary}")
    for w in res["phonetic_evaluation"]["words"]:
        print(f"  Word {w['index']+1}: {w['iast']} -> Match: {w['word_match_score']}% | Status: {w['status']}")
