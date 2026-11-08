"""
phonetic_evaluator.py
Local, word-by-word and phoneme-level evaluation module for Sanskrit mantra chanting.
Specialized for the Ganesha Shloka (Vakratuṇḍa Mahākāya):
  "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा"

Evaluates:
  1. Word-level alignment and acoustic match score (local DTW cosine similarity)
  2. Short vs. long vowel duration ratios (e.g. ma vs hā, ku vs me, va vs dā)
  3. Consonant aspiration (/bh/ in samaprabha, /gh/ in nirvighnam)
  4. Retroflex articulation (/ṇḍ/ in vakratuṇḍa, /ṭi/ in sūryakoṭi, /ṣu/ in sarvakāryeṣu)
  5. Safe-failure logic: acceptable / review / inconclusive
"""

import os
import sys
import json
import copy
import warnings
import numpy as np
import librosa
from sklearn.preprocessing import StandardScaler
from librosa.sequence import dtw
from scipy.signal import butter, sosfiltfilt

warnings.filterwarnings('ignore', module='librosa')

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ANNOTATION_FILE = os.path.join(BASE_DIR, "ganesha_shloka.json")
DEFAULT_REF_AUDIO = os.path.join(BASE_DIR, "mantra.wav")

# =============================================================================
# CONFIGURATION & THRESHOLDS
# =============================================================================
CONFIG = {
    # Alignment thresholds
    "MIN_SEGMENT_DURATION_MS": 30.0,       # Segments shorter than 30ms -> inconclusive
    "MIN_ALIGNMENT_CONFIDENCE": 0.20,      # Only extreme outliers (< 0.20) -> inconclusive

    # Word-level score thresholds
    "WORD_ACCEPTABLE_THRESHOLD": 48.0,     # >= 48% is acceptable (natural human variation)
    "WORD_REVIEW_THRESHOLD": 30.0,         # 30% - 47% needs review, < 30% needs practice

    # Phonetic contrast thresholds (tolerant to microphone EQ and vocal tract differences)
    "VOWEL_RATIO_TOLERANCE": 0.50,         # Measured ratio within ±50% of target/ref -> acceptable
    "CONSONANT_SIMILARITY_THRESHOLD": 0.50,# Spectral similarity >= 0.50 -> acceptable
    "ASPIRATION_ENERGY_RATIO_MIN": 0.05,   # Minimum high-freq breathiness ratio for aspirated stops
    "RETROFLEX_CENTROID_DIFF_HZ": 1500,    # Maximum allowable deviation in spectral centroid
}


def preprocess_for_analysis(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Lightweight zero-phase bandpass filter (80 Hz - 4200 Hz) and conditional
    spectral noise floor reduction if BGM/hum is detected. Clean audio is untouched.
    """
    if y is None or len(y) == 0:
        return y

    # 4th-order zero-phase Butterworth bandpass (80 Hz - 4200 Hz)
    nyq = 0.5 * sr
    low = max(20.0, min(80.0, nyq - 100))
    high = min(4200.0, nyq - 100)
    if high > low:
        sos = butter(4, [low / nyq, high / nyq], btype='bandpass', output='sos')
        y_filt = sosfiltfilt(sos, y)
    else:
        y_filt = y.copy()

    rms = librosa.feature.rms(y=y_filt, frame_length=1024, hop_length=256)[0]
    if len(rms) > 0:
        p10 = float(np.percentile(rms, 10))
        p90 = float(np.percentile(rms, 90))
        # If background noise/music floor is elevated
        if p90 > 1e-6 and (p10 / p90) > 0.12:
            n_fft = 1024
            hop_length = 256
            stft = librosa.stft(y_filt, n_fft=n_fft, hop_length=hop_length)
            mag, phase = np.abs(stft), np.angle(stft)

            p20 = np.percentile(rms, 20)
            noise_mask = (rms <= p20)
            if np.sum(noise_mask) >= 3:
                noise_profile = np.mean(mag[:, noise_mask], axis=1, keepdims=True)
            else:
                noise_profile = np.percentile(mag, 10, axis=1, keepdims=True)

            mag_clean = np.maximum(mag - 0.9 * noise_profile, 0.05 * mag)
            stft_clean = mag_clean * np.exp(1j * phase)
            y_clean = librosa.istft(stft_clean, hop_length=hop_length, length=len(y_filt))
            return y_clean.astype(y.dtype)

    return y_filt.astype(y.dtype)


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

    is_partial_chant = user_duration < 4.0

    aligned_words = []
    for w in ref_words:
        r_start = w["start_sec"]
        r_end = w["end_sec"]

        if is_partial_chant and precomputed_wp is None:
            # Subsequence DTW: match individual reference word anywhere in short user recording
            r_s_frame = int(r_start * ref_sr / hop_length)
            r_e_frame = max(r_s_frame + 2, int(r_end * ref_sr / hop_length))
            ref_w_comb = ref_comb[:, r_s_frame:r_e_frame]

            if ref_w_comb.shape[1] >= 2 and user_comb.shape[1] >= 2:
                D_sub, wp_sub = dtw(X=ref_w_comb, Y=user_comb, subseq=True)
                sub_cost = float(D_sub[-1, -1] / max(1, len(wp_sub)))
                matched_u_frames = wp_sub[:, 1]
                u_s = float(librosa.frames_to_time(np.min(matched_u_frames), sr=user_sr, hop_length=hop_length))
                u_e = float(librosa.frames_to_time(np.max(matched_u_frames), sr=user_sr, hop_length=hop_length))

                # Allow human variability in subseq cost (< 4.2)
                if sub_cost < 4.2:
                    u_start = u_s
                    u_end = u_e
                    confidence = float(np.clip(1.0 - (sub_cost / 4.2), 0.35, 1.0))
                else:
                    u_start = 0.0
                    u_end = 0.0
                    confidence = 0.0
            else:
                u_start = 0.0
                u_end = 0.0
                confidence = 0.0
        else:
            # Full recitation: global DTW mapping
            mask = (ref_times_arr >= r_start) & (ref_times_arr <= r_end)
            if np.any(mask):
                matched_user_times = user_times_arr[mask]
                u_start = float(np.min(matched_user_times))
                u_end = float(np.max(matched_user_times))

                expected_user_dur = (r_end - r_start) * (user_duration / (ref_duration + 1e-9))
                actual_user_dur = u_end - u_start
                dur_ratio = actual_user_dur / (expected_user_dur + 1e-9)
                if 0.25 <= dur_ratio <= 3.5:
                    confidence = float(np.clip(1.0 - 0.20 * abs(1.0 - dur_ratio), 0.50, 1.0))
                else:
                    confidence = float(np.clip(1.0 - 0.40 * abs(1.0 - dur_ratio), 0.25, 0.75))
            else:
                u_start = float(r_start * (user_duration / ref_duration))
                u_end = float(r_end * (user_duration / ref_duration))
                confidence = 0.50

        # Bound checks
        if u_end > u_start:
            u_start = max(0.0, min(u_start, user_duration))
            u_end = max(u_start, min(u_end, user_duration))
            u_dur_ms = (u_end - u_start) * 1000.0
            if u_dur_ms < CONFIG["MIN_SEGMENT_DURATION_MS"]:
                confidence = min(confidence, 0.25)
            u_start_val = round(u_start, 3)
            u_end_val = round(u_end, 3)
            u_dur_val = round(u_end - u_start, 3)
        else:
            u_start_val = None
            u_end_val = None
            u_dur_val = 0.0
            confidence = 0.0

        aligned_words.append({
            "index": w["index"],
            "devanagari": w["devanagari"],
            "iast": w["iast"],
            "raw_ref_start_sec": w.get("raw_start_sec", r_start),
            "raw_ref_end_sec": w.get("raw_end_sec", r_end),
            "ref_start_sec": r_start,
            "ref_end_sec": r_end,
            "ref_duration_sec": r_end - r_start,
            "user_start_sec": u_start_val,
            "user_end_sec": u_end_val,
            "user_duration_sec": u_dur_val,
            "alignment_confidence": round(confidence, 2),
            "phonetic_contrasts": w.get("phonetic_contrasts", [])
        })

    # Prevent overlap between adjacent words and resolve continuous transitions
    for i in range(len(aligned_words) - 1):
        curr_w = aligned_words[i]
        next_w = aligned_words[i+1]
        if (curr_w["user_start_sec"] is not None and curr_w["user_end_sec"] is not None and
            next_w["user_start_sec"] is not None and next_w["user_end_sec"] is not None):
            
            if curr_w["user_end_sec"] < curr_w["user_start_sec"] + 0.05:
                curr_w["user_end_sec"] = round(curr_w["user_start_sec"] + 0.05, 3)

            curr_r_end = ref_words[i]["end_sec"]
            next_r_start = ref_words[i+1]["start_sec"]
            is_continuous = (next_r_start - curr_r_end) < 0.05

            if next_w["user_start_sec"] <= curr_w["user_start_sec"] + 0.05:
                next_w["user_start_sec"] = round(curr_w["user_end_sec"], 3)
                if next_w["user_end_sec"] < next_w["user_start_sec"] + 0.05:
                    next_w["user_end_sec"] = round(next_w["user_start_sec"] + 0.05, 3)
            elif curr_w["user_end_sec"] > next_w["user_start_sec"]:
                midpoint = round(0.5 * (curr_w["user_end_sec"] + next_w["user_start_sec"]), 3)
                midpoint = max(curr_w["user_start_sec"] + 0.05, min(midpoint, next_w["user_end_sec"] - 0.05))
                curr_w["user_end_sec"] = midpoint
                next_w["user_start_sec"] = midpoint

            curr_w["user_duration_sec"] = round(max(0.05, curr_w["user_end_sec"] - curr_w["user_start_sec"]), 3)
            next_w["user_duration_sec"] = round(max(0.05, next_w["user_end_sec"] - next_w["user_start_sec"]), 3)

    # Special pause-valley splitting strictly between Word 7 (sarvakāryeṣu) and Word 8 (sarvadā)
    # ONLY if Word 8 duration is less than 0.40s
    if len(aligned_words) >= 8:
        w7 = aligned_words[6]
        w8 = aligned_words[7]
        if (w7["user_start_sec"] is not None and w7["user_end_sec"] is not None and
            w8["user_start_sec"] is not None and w8["user_end_sec"] is not None and
            w8["user_duration_sec"] < 0.40):
            r_end_7 = ref_words[6]["end_sec"]
            r_start_8 = ref_words[7]["start_sec"]
            pause_mask = (ref_times_arr >= r_end_7) & (ref_times_arr <= r_start_8)
            if np.any(pause_mask) and len(user_audio) > 512:
                u_pause_start = float(np.min(user_times_arr[pause_mask]))
                u_pause_end = float(np.max(user_times_arr[pause_mask]))
                if u_pause_end > u_pause_start + 0.05:
                    rms = librosa.feature.rms(y=user_audio, frame_length=512, hop_length=128)[0]
                    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=user_sr, hop_length=128)
                    in_pause = (rms_times >= u_pause_start) & (rms_times <= u_pause_end)
                    if np.any(in_pause):
                        val_idx = np.where(in_pause)[0][np.argmin(rms[in_pause])]
                        t_valley = float(rms_times[val_idx])
                        if t_valley > w7["user_start_sec"] + 0.35:
                            w7["user_end_sec"] = round(t_valley, 3)
                            w7["user_duration_sec"] = round(w7["user_end_sec"] - w7["user_start_sec"], 3)
                            w8["user_start_sec"] = round(t_valley, 3)
                            w8["user_duration_sec"] = round(w8["user_end_sec"] - w8["user_start_sec"], 3)

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
    if u_end <= u_start or (u_end - u_start) < 0.04:
        return 0.0

    u_s_sample = int(u_start * user_sr)
    u_e_sample = max(u_s_sample + 64, int(u_end * user_sr))
    r_s_sample = int(r_start * ref_sr)
    r_e_sample = max(r_s_sample + 64, int(r_end * ref_sr))

    u_seg = user_audio[u_s_sample:u_e_sample]
    r_seg = ref_audio[r_s_sample:r_e_sample]

    u_rms = float(np.mean(librosa.feature.rms(y=u_seg)[0])) if len(u_seg) > 0 else 0.0
    if len(u_seg) < 256 or len(r_seg) < 256 or u_rms < 0.008:
        return 0.0

    # Extract MFCCs — DROP mfcc[0] (overall energy) for speaker loudness independence
    u_mfcc = librosa.feature.mfcc(y=u_seg, sr=user_sr, n_mfcc=13)[1:, :]  # shape (12, T)
    r_mfcc = librosa.feature.mfcc(y=r_seg, sr=ref_sr, n_mfcc=13)[1:, :]

    # Per-segment normalization and delta trajectories
    u_scaled = StandardScaler().fit_transform(u_mfcc.T).T
    r_scaled = StandardScaler().fit_transform(r_mfcc.T).T

    try:
        u_width = 9
        if u_scaled.shape[1] < u_width:
            u_width = u_scaled.shape[1] if u_scaled.shape[1] % 2 != 0 else u_scaled.shape[1] - 1
        if u_width >= 3:
            u_delta = librosa.feature.delta(u_scaled, width=u_width)
        else:
            u_delta = np.zeros_like(u_scaled)

        r_width = 9
        if r_scaled.shape[1] < r_width:
            r_width = r_scaled.shape[1] if r_scaled.shape[1] % 2 != 0 else r_scaled.shape[1] - 1
        if r_width >= 3:
            r_delta = librosa.feature.delta(r_scaled, width=r_width)
        else:
            r_delta = np.zeros_like(r_scaled)

        u_comb = np.vstack([u_scaled, u_delta])
        r_comb = np.vstack([r_scaled, r_delta])
    except Exception:
        u_comb = u_scaled
        r_comb = r_scaled

    try:
        D, wp = dtw(u_comb, r_comb, metric="euclidean")
        dist = D[-1, -1] / max(1, len(wp))
        if dist >= 7.5:
            score = 0.0
        else:
            score = float(100.0 * np.exp(-dist / 5.2))
        return float(np.clip(score, 0.0, 100.0))
    except Exception:
        return 0.0


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

    # Count voiced/high-energy samples with hop_length=128
    fl_s = min(512, max(64, len(s_seg)))
    hl_s = min(128, max(32, fl_s // 4))
    s_rms = librosa.feature.rms(y=s_seg, frame_length=fl_s, hop_length=hl_s)[0]

    fl_l = min(512, max(64, len(l_seg)))
    hl_l = min(128, max(32, fl_l // 4))
    l_rms = librosa.feature.rms(y=l_seg, frame_length=fl_l, hop_length=hl_l)[0]

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
    Evaluates user audio against the reference Ganesha Shloka annotations.
    """
    annotations = load_ref_annotations(annotation_path)
    ref_words_raw = annotations.get("words", [])

    # Load, trim on raw audio first for exact sample offset, then bandpass/denoise
    user_audio_raw, user_sr = librosa.load(user_audio_path, sr=16000)
    user_audio_trimmed, user_trim_idx = librosa.effects.trim(user_audio_raw, top_db=30)
    user_trim_offset_sec = float(user_trim_idx[0]) / user_sr
    user_audio = preprocess_for_analysis(user_audio_trimmed, user_sr)

    ref_audio_raw, ref_sr = librosa.load(ref_audio_path, sr=16000)
    ref_audio_trimmed, ref_trim_idx = librosa.effects.trim(ref_audio_raw, top_db=30)
    ref_trim_offset_sec = float(ref_trim_idx[0]) / ref_sr
    ref_audio = preprocess_for_analysis(ref_audio_trimmed, ref_sr)

    # Shift reference timestamps by ref_trim_offset_sec so they align with trimmed ref_audio
    ref_words = copy.deepcopy(ref_words_raw)
    for w in ref_words:
        w["raw_start_sec"] = float(w["start_sec"])
        w["raw_end_sec"]   = float(w["end_sec"])
        w["start_sec"]     = max(0.0, w["raw_start_sec"] - ref_trim_offset_sec)
        w["end_sec"]       = max(0.0, w["raw_end_sec"]   - ref_trim_offset_sec)
        for c in w.get("phonetic_contrasts", []):
            if "sub_start_sec" in c:
                c["sub_start_sec"] = max(0.0, c["sub_start_sec"] - ref_trim_offset_sec)
                c["sub_end_sec"]   = max(0.0, c["sub_end_sec"]   - ref_trim_offset_sec)
            if "short_vowel_sub_span" in c:
                c["short_vowel_sub_span"] = [
                    max(0.0, c["short_vowel_sub_span"][0] - ref_trim_offset_sec),
                    max(0.0, c["short_vowel_sub_span"][1] - ref_trim_offset_sec),
                ]
            if "long_vowel_sub_span" in c:
                c["long_vowel_sub_span"] = [
                    max(0.0, c["long_vowel_sub_span"][0] - ref_trim_offset_sec),
                    max(0.0, c["long_vowel_sub_span"][1] - ref_trim_offset_sec),
                ]

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

        raw_r_start = round(word_info.get("raw_ref_start_sec", r_start + ref_trim_offset_sec), 3)
        raw_r_end   = round(word_info.get("raw_ref_end_sec", r_end + ref_trim_offset_sec), 3)

        if u_start is None or u_end is None or u_end <= u_start:
            word_status = "inconclusive"
            inconclusive_count += 1
            match_scores.append(0.0)
            evaluated_words.append({
                "index": word_info["index"],
                "devanagari": word_info["devanagari"],
                "iast": word_info["iast"],
                "word_match_score": 0.0,
                "status": "inconclusive",
                "user_start_sec": None,
                "user_end_sec": None,
                "ref_start_sec": raw_r_start,
                "ref_end_sec": raw_r_end,
                "trimmed_user_start_sec": None,
                "trimmed_user_end_sec": None,
                "duration_sec": 0.0,
                "alignment_confidence": 0.0,
                "contrasts": []
            })
            continue

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

        # Check segment energy (detect silence / unvoiced segments)
        u_seg_for_vad = user_audio[int(u_start * user_sr):max(int(u_start * user_sr) + 64, int(u_end * user_sr))]
        u_seg_rms = float(np.mean(librosa.feature.rms(y=u_seg_for_vad)[0])) if len(u_seg_for_vad) > 0 else 0.0

        # Word status determination
        # Inconclusive ONLY when there is pure silence or essentially zero segment duration
        if (u_dur * 1000.0) < CONFIG["MIN_SEGMENT_DURATION_MS"] or u_seg_rms < 0.003 or match_score < 15.0 or conf < 0.20:
            word_status = "inconclusive"
            inconclusive_count += 1
        elif match_score >= CONFIG["WORD_ACCEPTABLE_THRESHOLD"]:
            word_status = "acceptable"
            acceptable_count += 1
        else:
            word_status = "review"
            review_count += 1

        raw_u_start = round(u_start + user_trim_offset_sec, 3)
        raw_u_end   = round(u_end + user_trim_offset_sec, 3)
        raw_r_start = round(word_info.get("raw_ref_start_sec", r_start + ref_trim_offset_sec), 3)
        raw_r_end   = round(word_info.get("raw_ref_end_sec", r_end + ref_trim_offset_sec), 3)

        evaluated_words.append({
            "index": word_info["index"],
            "devanagari": word_info["devanagari"],
            "iast": word_info["iast"],
            "word_match_score": round(match_score, 1),
            "status": word_status,
            "user_start_sec": raw_u_start,
            "user_end_sec": raw_u_end,
            "ref_start_sec": raw_r_start,
            "ref_end_sec": raw_r_end,
            "trimmed_user_start_sec": round(u_start, 3),
            "trimmed_user_end_sec": round(u_end, 3),
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
            "words": evaluated_words,
            "ref_trim_offset_sec": ref_trim_offset_sec,
            "user_trim_offset_sec": user_trim_offset_sec,
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
