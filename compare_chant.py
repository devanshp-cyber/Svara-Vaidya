import librosa

import numpy as np

import json

import unicodedata

from transformers import Wav2Vec2ForCTC, AutoProcessor

from sklearn.preprocessing import StandardScaler

from librosa.sequence import dtw

from difflib import SequenceMatcher

import re

from scipy.ndimage import uniform_filter1d         # Smooth pitch curve

from scipy.signal import find_peaks, resample, butter, sosfiltfilt      # Peak detection, resamp, filtering

import torch

import soundfile as sf

import os

import sys

import warnings

warnings.filterwarnings('ignore', module='librosa')



os.environ.setdefault('HF_HUB_OFFLINE', '1')

os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Global reference models and feature caches (loaded lazily in _load_references) ──

MMS_MODEL = None

MMS_FEATURE_EXTRACTOR = None

MMS_TOKENIZER         = {}

ref_pitch     = None

ref_tempo     = None

ref_mfcc      = None

ref_audio     = None

ref_sr        = None

ref_mantra    = None

ref_trim_offset_sec = 0.0

from mantras import MANTRAS, DEFAULT_MANTRA_ID
active_mantra_id = None



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
        # If noise floor is elevated (typical of BGM / tanpura / hum)
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


def _load_references(mantra_id="ganesha"):
    """
    Loads MMS model and reference chant features for the selected mantra.
    MMS model is cached in memory; reference features are cached per mantra.
    """
    global MMS_MODEL, MMS_FEATURE_EXTRACTOR, MMS_TOKENIZER, ref_pitch, ref_tempo, ref_mfcc
    global ref_audio, ref_sr, ref_mantra, ref_trim_offset_sec, active_mantra_id

    # 1. Load MMS Model once
    if MMS_MODEL is None:
        print("Loading MMS model and tokenizer...")
        target_language = "urd-script_devanagari"
        model_id = "facebook/mms-1b-all"
        try:
            mms_proc = AutoProcessor.from_pretrained(model_id, local_files_only=True)
        except Exception:
            mms_proc = AutoProcessor.from_pretrained(model_id)
        mms_proc.tokenizer.set_target_lang(target_language)

        try:
            MMS_MODEL = Wav2Vec2ForCTC.from_pretrained(
                model_id,
                ignore_mismatched_sizes=True,
                local_files_only=True
            )
        except Exception:
            MMS_MODEL = Wav2Vec2ForCTC.from_pretrained(
                model_id,
                ignore_mismatched_sizes=True
            )

        try:
            MMS_MODEL.load_adapter(target_language, local_files_only=True)
        except Exception:
            MMS_MODEL.load_adapter(target_language)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            print(f"MMS Sanskrit model loaded on GPU: {gpu_name} (FP16 Tensor Core acceleration)")
            MMS_MODEL = MMS_MODEL.half()
        else:
            print("MMS Sanskrit model loaded on CPU.")
        MMS_MODEL = MMS_MODEL.to(device)
        MMS_MODEL.eval()

        MMS_TOKENIZER = mms_proc.tokenizer
        MMS_FEATURE_EXTRACTOR = mms_proc.feature_extractor
        print("MMS Sanskrit configuration loaded successfully.")

    # 2. Check if reference data for requested mantra is already loaded
    if mantra_id not in MANTRAS:
        mantra_id = DEFAULT_MANTRA_ID

    if active_mantra_id == mantra_id and ref_pitch is not None and ref_audio is not None:
        return

    active_mantra_id = mantra_id
    minfo = MANTRAS[mantra_id]
    audio_path = os.path.join(BASE_DIR, minfo["audio_file"])
    features_path = os.path.join(BASE_DIR, minfo["features_file"])

    ref_audio_raw, ref_sr_raw = librosa.load(audio_path, sr=16000)
    ref_audio_raw = ref_audio_raw.astype(float)
    if ref_audio_raw.ndim > 1:
        ref_audio_raw = ref_audio_raw.mean(axis=1)  # stereo to mono

    ref_audio_trimmed, ref_trim_idx = librosa.effects.trim(ref_audio_raw, top_db=45)
    ref_trim_offset_sec = float(ref_trim_idx[0]) / 16000.0

    ref_audio = ref_audio_trimmed
    ref_sr    = 16000

    need_regen = True
    if os.path.exists(features_path):
        try:
            with open(features_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("sr") == 16000 and "pitch_contour" in existing:
                need_regen = False
        except Exception:
            need_regen = True

    if need_regen:
        print(f"Regenerating {minfo['features_file']} at 16000 Hz from {minfo['audio_file']}...")
        _pitch, _, _ = librosa.pyin(
            ref_audio, sr=ref_sr,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7')
        )
        _pitch = np.nan_to_num(_pitch)
        _mfcc  = librosa.feature.mfcc(y=ref_audio, sr=ref_sr, n_mfcc=13)
        _tempo_arr, _ = librosa.beat.beat_track(y=ref_audio, sr=ref_sr)
        _tempo = float(_tempo_arr[0]) if isinstance(_tempo_arr, np.ndarray) else float(_tempo_arr)

        ref_data = {
            "mantra_text": minfo["default_text"],
            "sr": 16000,
            "pitch_contour": _pitch.tolist(),
            "mfcc": _mfcc.tolist(),
            "tempo": _tempo,
        }
        with open(features_path, "w", encoding="utf-8") as f:
            json.dump(ref_data, f, ensure_ascii=False)
        print(f"{minfo['features_file']} regenerated successfully at 16000 Hz.")

    with open(features_path, "r", encoding="utf-8") as f:
        reference = json.load(f)

    ref_pitch  = np.array(reference["pitch_contour"])
    ref_tempo  = reference["tempo"]
    ref_mfcc   = np.array(reference["mfcc"])
    ref_mantra = reference.get("mantra_text", minfo["default_text"])
    print(f"Reference data loaded for [{minfo['name']}].")

# -----------------------

# 1. Pitch similarity

# -----------------------

# We compare how similar the pitch movements are between reference and user.

# Steps:

#   1. Keep only voiced frames (where pitch > 0, i.e. voice is active)

#   2. Convert to log scale (human ears hear pitch on a log scale)

#   3. Z-score normalize (removes gender/voice type difference)

#   4. Resample to same length (DTW works better with equal length)

#   5. DTW comparison

#   6. Convert distance to similarity score

 

# =============================================================================

# 1-a PITCH ZONE ANALYSIS (Vedic Accent: Udatta / Anudatta / Svarita)

# =============================================================================

# Based on research by Begus (2016) and BHASHA 2025 paper.

#

# Vedic Sanskrit has 3 pitch accent zones:

#   Anudatta  = low flat region (before the accent)

#   Udatta    = rising region   (the accent peak)

#   Svarita   = falling region  (after the peak)

#

# Instead of comparing just the pitch numbers,

# we detect WHICH ZONE is happening at each moment using slope:

#   slope > 0  → pitch is rising  → Udatta

#   slope < 0  → pitch is falling → Svarita

#   slope ≈ 0  → pitch is flat    → Anudatta

 

def extract_pitch_zones(pitch_contour):

    """

    IMPROVED VERSION — from Document 8 (upgraded pitch zone extraction).

    

    Takes a raw pitch array.

    Returns list of zones detected: anudatta / udatta / svarita

    and the normalized pitch array.

    

    Upgrades over old version:

      - Uses find_peaks() for robust peak detection (handles multiple peaks)

      - Finds dominant peak near CENTER of contour (more reliable for mantras)

      - Handles plateau shapes (long flat sections don't confuse the detector)

      - Slope threshold prevents noise from creating false zone switches

    """

    # Only keep voiced frames (where pitch > 0)

    voiced = [(i, p) for i, p in enumerate(pitch_contour) if p > 0]

 

    if len(voiced) < 6:

        return [], np.array([])

 

    pitches = np.array([v[1] for v in voiced])

 

    # --- Step 1: Smooth pitch ---

    # Moving average with window=5 removes frame-to-frame jitter

    # without destroying the overall shape of the curve

    smoothed = uniform_filter1d(pitches, size=5)

 

    # --- Step 2: Z-score normalize (speaker/gender independent) ---

    # After this step: mean=0, std=1 for both male and female voices

    # DTW comparison becomes gender-neutral

    norm = (smoothed - np.mean(smoothed)) / (np.std(smoothed) + 1e-9)

 

    # --- Step 3: Compute slope (gradient) ---

    # np.gradient = rate of change at each point

    # slope[i] > 0  → pitch rising at frame i

    # slope[i] < 0  → pitch falling at frame i

    # slope[i] ≈ 0  → pitch flat at frame i

    slope = np.gradient(norm)

 

    # --- Step 4: Find dominant peak near center ---

    # find_peaks() finds ALL local maxima in the array

    # We then pick the one closest to the CENTER of the contour

    # Why center? Because in most mantras the main accent peak

    # falls roughly in the middle of the phrase, not at the edges.

    # This is more robust than just taking np.argmax() which can

    # pick an edge artifact.

    peaks, _ = find_peaks(norm)

    if len(peaks) == 0:

        # No peaks found — fall back to global maximum

        peak_idx = int(np.argmax(norm))

    else:

        center   = len(norm) // 2

        # Pick the peak closest to center

        peak_idx = peaks[int(np.argmin(np.abs(peaks - center)))]

 

    # --- Step 5: Classify each frame into a zone using slope ---

    # threshold=0.05 means slope must be meaningfully positive/negative

    # to count as rising/falling. This prevents noise spikes from

    # creating spurious zone changes.

    zones        = []

    current_zone = None

    start        = 0

    threshold    = 0.05

 

    for i in range(len(norm)):

        if slope[i] > threshold:

            zone = "udatta"      # rising → Udatta accent region

        elif slope[i] < -threshold:

            zone = "svarita"     # falling → Svarita (post-peak fall)

        else:

            zone = "anudatta"    # flat/low → Anudatta (pre-accent region)

 

        if current_zone is None:

            current_zone = zone

            start        = i

        elif zone != current_zone:

            zones.append({

                "zone":      current_zone,

                "avg_pitch": float(np.mean(norm[start:i])),

                "length":    i - start

            })

            current_zone = zone

            start        = i

 

    # Save last zone

    zones.append({

        "zone":      current_zone,

        "avg_pitch": float(np.mean(norm[start:])),

        "length":    len(norm) - start

    })

 

    return zones, norm

 

 

def compare_pitch_zones(ref_zones, user_zones):

    """

    Compares Vedic accent zones between reference and user.

    Returns: zone_similarity (0-100), list of feedback messages

    """

    if not ref_zones or not user_zones:

        return 0.0, ["Could not detect pitch zones — recording may be too quiet"]

 

    feedback = []

    scores   = []

 

    # Convert list of zones to dict for easy lookup

    # Note: if same zone appears multiple times, last one wins

    # This is fine for a first pass

    ref_dict  = {z["zone"]: z for z in ref_zones}

    user_dict = {z["zone"]: z for z in user_zones}

 

    for zone in ["anudatta", "udatta", "svarita"]:

        if zone not in ref_dict:

            continue   # reference doesn't have this zone, skip

 

        if zone not in user_dict:

            feedback.append(f"Missing {zone} section in your chant")

            scores.append(0.0)

            continue

 

        ref_z  = ref_dict[zone]

        user_z = user_dict[zone]

 

        # Compare normalized pitch levels

        # Since both are normalized, difference should be small for good match

        pitch_diff = abs(ref_z["avg_pitch"] - user_z["avg_pitch"])

        zone_score = max(0.0, 1.0 - pitch_diff)

        scores.append(zone_score)

 

        # Generate specific feedback

        if zone == "udatta" and zone_score < 0.7:

            feedback.append("Udatta (rising accent) is not rising high enough")

        elif zone == "svarita" and zone_score < 0.7:

            feedback.append("Svarita (falling tone after peak) is not dropping correctly")

        elif zone == "anudatta" and zone_score < 0.7:

            feedback.append("Anudatta (low starting region) pitch is unstable")

 

    # Check peak timing

    # The Beguš paper shows that WHEN the peak happens matters —

    # independent svarita peaks earlier (compressed udatta)

    ref_total  = sum(z["length"] for z in ref_zones)

    user_total = sum(z["length"] for z in user_zones)

 

    if ref_total > 0 and user_total > 0:

        ref_peak_ratio  = ref_dict.get("udatta",  {}).get("length", 0) / ref_total

        user_peak_ratio = user_dict.get("udatta", {}).get("length", 0) / user_total

        timing_diff     = abs(ref_peak_ratio - user_peak_ratio)

 

        if timing_diff > 0.2:

            feedback.append(

                f"Pitch peak timing is off — "

                f"reference peaks at {round(ref_peak_ratio * 100)}% of chant, "

                f"you peaked at {round(user_peak_ratio * 100)}%"

            )

 

    zone_similarity = float(np.mean(scores)) * 100 if scores else 0.0

    return zone_similarity, feedback

 

# =============================================================================

# 1-b — ACCENT LEVEL CLASSIFIER (BHASHA 2025 paper)

# =============================================================================

# The BHASHA paper found that Rigvedic Sanskrit has 3 pitch accent levels:

#   Anudatta = low    (label 1)

#   Neutral  = medium (label 2)

#   Udatta   = high   (label 3)

#

# A wrong accent CHANGES THE MEANING of the Sanskrit word.

# Your pitch contour DTW catches overall shape, but a user could follow

# the general melody while placing the HIGH tone on the WRONG syllable.

# This classifier catches that specific error.

#

# How it works:

#   - Take all voiced (non-zero) pitch values

#   - Find the 33rd percentile (low_thresh) and 66th percentile (high_thresh)

#   - Classify every frame: below low_thresh=Anudatta, above high_thresh=Udatta

#   - Compare the sequence of labels using SequenceMatcher

 

def classify_accent_levels(pitch_contour, low_thresh=None, high_thresh=None):

    """

    Classifies each pitch frame into one of 3 Vedic accent levels.

    Returns array of labels: 0=silence, 1=Anudatta(low), 2=neutral, 3=Udatta(high)

    

    Based on BHASHA 2025 paper — accent placement is linguistically meaningful.

    A wrong label at a syllable = wrong accent = possibly wrong meaning.

    """

    voiced = pitch_contour[pitch_contour > 0]

    if len(voiced) == 0:

        return np.array([])

 

    # Percentile thresholds divide pitch range into 3 equal parts

    # 33rd percentile = lower third of pitch range = Anudatta region

    # 66th percentile = upper third of pitch range = Udatta region

    if low_thresh is None:

        low_thresh  = np.percentile(voiced, 33)

    if high_thresh is None:

        high_thresh = np.percentile(voiced, 66)

 

    levels = []

    for p in pitch_contour:

        if p == 0:

            levels.append(0)    # silence — not voiced

        elif p < low_thresh:

            levels.append(1)    # Anudatta — low pitch

        elif p < high_thresh:

            levels.append(2)    # neutral — middle pitch

        else:

            levels.append(3)    # Udatta — high pitch (accent peak)

    return np.array(levels)

 

 

# =============================================================================

# 1-c — INTRA-SYLLABLE PITCH SHAPE DETECTOR (Beguš 2016 paper)

# =============================================================================

# The Beguš paper explains that within a single syllable,

# the DIRECTION of pitch movement identifies the accent type:

#

#   Udatta   = rising pitch within the syllable     (low → high)

#   Anudatta = falling pitch within the syllable    (high → low)

#   Svarita  = rising-then-falling (circumflex)     (low → high → low)

#   Flat     = sustained note, no clear direction

#

# This is DIFFERENT from the zone analysis (Section 5a) which looks at

# the full contour. This looks at small windows (individual syllables).

#

# Why does this matter?

# Example: user chants a syllable with a flat tone where

# reference has a rising (Udatta) tone. Zone analysis might miss this

# if the overall contour shape is similar. This detector catches it.

 

def detect_pitch_shape(pitch_segment):

    """

    Classifies the pitch movement WITHIN a short segment (one syllable).

    

    Returns one of: 'rising', 'falling', 'rising_falling', 'flat'

    

    Based on Beguš 2016:

      rising        = Udatta accent

      falling       = Anudatta accent  

      rising_falling = Svarita (independent svarita = compressed udatta)

      flat          = sustained, no accent

    """

    # Need at least 3 frames to detect a shape

    if len(pitch_segment) < 3:

        return 'flat'

 

    mid   = len(pitch_segment) // 2

    first = np.mean(pitch_segment[:mid])    # average pitch in first half

    last  = np.mean(pitch_segment[mid:])    # average pitch in second half

    peak  = np.max(pitch_segment)           # highest point in the segment

 

    # 1.05 threshold = must be 5% higher to count as meaningful change

    # This prevents tiny fluctuations from being classified as movement

    rising          = last  > first * 1.05

    falling         = first > last  * 1.05

    # Peak in middle = pitch went up then came down within this segment

    has_peak_middle = (peak > first * 1.05) and (peak > last * 1.05)

 

    if has_peak_middle:

        return 'rising_falling'   # Svarita — circumflex shape

    elif rising:

        return 'rising'           # Udatta — accent rising

    elif falling:

        return 'falling'          # Anudatta — falling after accent

    else:

        return 'flat'             # sustained, no clear accent

 

 

def analyze_syllable_shapes(pitch_contour, n_segments=8):

    """

    Divides the pitch contour into n_segments equal windows

    and classifies the pitch shape of each window.

    

    Returns list of shape labels like:

    ['flat', 'rising', 'rising_falling', 'falling', 'flat', ...]

    

    n_segments=8 approximates syllable-level analysis for a short mantra.

    For longer mantras you can increase this.

    """

    voiced = pitch_contour[pitch_contour > 0]

    if len(voiced) < n_segments:

        return []

 

    # Split voiced frames into n equal windows

    segments = np.array_split(voiced, n_segments)

    shapes   = [detect_pitch_shape(seg) for seg in segments]

    return shapes

 

 

def shape_sequence_similarity(ref_shapes, user_shapes):

    """

    Compares the sequence of pitch shapes between reference and user.

    Returns similarity score 0-100 and list of feedback messages.

    

    Example:

      ref:  ['flat', 'rising', 'rising_falling', 'falling']

      user: ['flat', 'flat',   'rising_falling', 'falling']

      → segment 2 is wrong: user has 'flat' where ref has 'rising' (Udatta)

    """

    if not ref_shapes or not user_shapes:

        return 0.0, []

 

    # Compare shape sequences using SequenceMatcher

    score    = SequenceMatcher(None, ref_shapes, user_shapes).ratio() * 100

    feedback = []

 

    # Find specific segments that differ

    matcher = SequenceMatcher(None, ref_shapes, user_shapes)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == 'replace':

            ref_shape  = ref_shapes[i1]

            user_shape = user_shapes[j1] if j1 < len(user_shapes) else 'unknown'

 

            # Give specific Vedic accent feedback

            if ref_shape == 'rising' and user_shape != 'rising':

                feedback.append(

                    f"Syllable group {i1+1}: should have an Udatta (rising accent) "

                    f"but yours sounds {user_shape}"

                )

            elif ref_shape == 'rising_falling' and user_shape != 'rising_falling':

                feedback.append(

                    f"Syllable group {i1+1}: should have a Svarita "

                    f"(rising-then-falling circumflex) but yours sounds {user_shape}"

                )

            elif ref_shape == 'falling' and user_shape != 'falling':

                feedback.append(

                    f"Syllable group {i1+1}: should have an Anudatta "

                    f"(falling tone) but yours sounds {user_shape}"

                )

 

    return score, feedback

 

 

# --- Pitch slope similarity ---

# The Beguš paper: independent svarita = same pitch targets but STEEPER slope

# So we also compare the rate of pitch change (velocity/slope)

 

def pitch_slope_similarity(ref_p, user_p):

    """

    Compares how fast pitch rises and falls.

    Captures steepness difference between udatta and independent svarita.

    """

    def get_slopes(p):

        voiced = p[p > 0]

        if len(voiced) < 2:

            return np.array([0.0])

        log_p = np.log2(voiced)

        return np.diff(log_p)   # differences between consecutive pitch values

 

    ref_slopes  = get_slopes(ref_p)
    user_slopes = get_slopes(user_p)

    if len(ref_slopes) == 0 or len(user_slopes) == 0:
        return 0.0

    slope_ratio = len(user_slopes) / max(len(ref_slopes), 1)
    scaled_user_slopes = user_slopes * slope_ratio

    D, wp = dtw(
        ref_slopes.reshape(1, -1),
        scaled_user_slopes.reshape(1, -1),
        metric='euclidean'
    )

    slope_dist = D[-1, -1] / len(wp)

    return 100 * np.exp(-slope_dist / 0.5)

 

# --- Combined pitch score ---

# We now have 5 pitch measurements, each from a different research insight:

#

#   pitch_similarity  — DTW on z-scored pitch contour (overall shape)

#                       catches: melody wrong, wrong key relative movement

#

#   zone_sim          — Udatta/Anudatta/Svarita zone presence & levels

#                       catches: missing the rising/falling arc of the mantra

#                       (from Beguš + BHASHA papers)

#

#   slope_sim         — rate of pitch change (steepness)

#                       catches: svarita compressed vs expanded wrong

#                       (from Beguš 2016 — independent svarita = steeper udatta)

#

#   accent_sim        — frame-level Anudatta/Neutral/Udatta label sequence

#                       catches: Udatta placed on WRONG syllable

#                       (from BHASHA 2025 — wrong accent = wrong meaning)

#

#   shape_sim         — intra-syllable pitch shape (rising/falling/circumflex)

#                       catches: wrong shape on individual syllables

#                       (from Beguš 2016 — svarita = circumflex within syllable)



# =============================================================================

# WORD-LEVEL SVARA MAP

# Maps pitch analysis back to actual words so feedback says:

# "On 'gam' (word 2): expected udatta (rising), you sang anudatta (flat)"

# =============================================================================



HOP_LENGTH = 512  # default librosa hop length



def build_word_svara_map(pitch_contour, word_timestamps, audio_sr):

    """

    For each word, slices the pitch contour using word alignment timestamps

    and classifies dominant_accent + pitch_shape for that word.

    """

    if not word_timestamps or len(pitch_contour) == 0:

        return []



    voiced_vals = pitch_contour[pitch_contour > 0]

    if len(voiced_vals) == 0:

        return []



    p_mean      = np.mean(voiced_vals)

    p_std       = np.std(voiced_vals) + 1e-9

    low_thresh  = np.percentile(voiced_vals, 33)

    high_thresh = np.percentile(voiced_vals, 66)



    word_map = []

    for wt in word_timestamps:

        start_frame = int(wt["start"] * audio_sr / HOP_LENGTH)

        end_frame   = min(int(wt["end"] * audio_sr / HOP_LENGTH), len(pitch_contour) - 1)



        if start_frame >= end_frame:

            word_map.append({"word": wt["word"], "start": wt["start"], "end": wt["end"],

                             "dominant_accent": "silence", "pitch_shape": "flat", "avg_pitch_norm": 0.0})

            continue



        segment    = pitch_contour[start_frame:end_frame]

        voiced_seg = segment[segment > 0]



        if len(voiced_seg) < 3:

            dominant_accent, pitch_shape, avg_norm = "silence", "flat", 0.0

        else:

            counts = {"anudatta": 0, "neutral": 0, "udatta": 0}

            for p in voiced_seg:

                if p < low_thresh:       counts["anudatta"] += 1

                elif p < high_thresh:    counts["neutral"]  += 1

                else:                    counts["udatta"]   += 1

            dominant_accent = max(counts, key=counts.get)

            pitch_shape     = detect_pitch_shape(voiced_seg)  # reuses existing function

            avg_norm        = float((np.mean(voiced_seg) - p_mean) / p_std)



        word_map.append({"word": wt["word"], "start": wt["start"], "end": wt["end"],

                         "dominant_accent": dominant_accent, "pitch_shape": pitch_shape,

                         "avg_pitch_norm": avg_norm})

    return word_map





def build_ref_word_svara_map(ref_pitch_contour, ref_word_list, ref_audio_array, ref_sample_rate):

    """

    Reference has no Whisper timestamps, so divide equally across known words.

    """

    if not ref_word_list or len(ref_pitch_contour) == 0:

        return []

    duration_sec  = len(ref_audio_array) / ref_sample_rate

    word_duration = duration_sec / len(ref_word_list)

    synthetic_ts  = [{"word": w, "start": i * word_duration, "end": (i+1) * word_duration}

                     for i, w in enumerate(ref_word_list)]

    return build_word_svara_map(ref_pitch_contour, synthetic_ts, ref_sample_rate)





def compare_word_svara_maps(ref_map, user_map):

    """

    Compares reference and user word-by-word.

    Returns list of per-word feedback dicts with exact fix messages.

    """

    if not ref_map or not user_map:

        return []



    ACCENT_MEANING = {

        "udatta":   "udatta — pitch must RISE on this syllable",

        "anudatta": "anudatta — pitch stays LOW and flat",

        "neutral":  "neutral — steady middle pitch",

        "silence":  "silence",

    }

    SHAPE_MEANING = {

        "rising":         "rising / udatta (vowel climbs upward)",

        "falling":        "falling / anudatta (vowel descends)",

        "rising_falling": "svarita — rise then fall within the vowel (circumflex)",

        "flat":           "flat / sustained (no accent movement)",

    }



    items = []

    total = max(len(ref_map), len(user_map))



    for i in range(min(len(ref_map), len(user_map))):

        rw, uw = ref_map[i], user_map[i]

        word   = uw["word"]

        wnum   = i + 1



        accent_wrong = rw["dominant_accent"] != uw["dominant_accent"]

        shape_wrong  = rw["pitch_shape"]     != uw["pitch_shape"]



        accent_fix = shape_fix = None



        if accent_wrong:

            ra, ua = rw["dominant_accent"], uw["dominant_accent"]

            if ra == "udatta":

                accent_fix = (f"On '{word}' (word {wnum}/{total}): lift your pitch upward on the vowel. "

                              f"This syllable carries the udatta accent — it must rise clearly. "

                              f"You sang {ACCENT_MEANING.get(ua, ua)} instead.")

            elif ra == "anudatta":

                accent_fix = (f"On '{word}' (word {wnum}/{total}): keep pitch LOW and even. "

                              f"Anudatta is the quiet ground before the accent. "

                              f"You sang {ACCENT_MEANING.get(ua, ua)} instead.")

            elif ra == "neutral":

                accent_fix = (f"On '{word}' (word {wnum}/{total}): hold a steady middle pitch. "

                              f"You sang {ACCENT_MEANING.get(ua, ua)} instead.")



        if shape_wrong:

            rs, us = rw["pitch_shape"], uw["pitch_shape"]

            if rs == "rising_falling":

                shape_fix = (f"On '{word}' (word {wnum}/{total}): this is a SVARITA syllable — "

                             f"your voice must rise then fall within the vowel (circumflex shape). "

                             f"Sing it in two movements: up then immediately down. "

                             f"You sang {SHAPE_MEANING.get(us, us)} instead.")

            elif rs == "rising":

                shape_fix = (f"On '{word}' (word {wnum}/{total}): vowel should climb upward (udatta shape). "

                             f"Let pitch rise as you hold the vowel. "

                             f"You sang {SHAPE_MEANING.get(us, us)} instead.")

            elif rs == "falling":

                shape_fix = (f"On '{word}' (word {wnum}/{total}): vowel should descend (anudatta shape). "

                             f"Let pitch gently fall through the vowel. "

                             f"You sang {SHAPE_MEANING.get(us, us)} instead.")



        items.append({"word": word, "word_num": wnum,

                      "ref_accent": rw["dominant_accent"], "user_accent": uw["dominant_accent"],

                      "ref_shape":  rw["pitch_shape"],     "user_shape":  uw["pitch_shape"],

                      "accent_ok": not accent_wrong, "shape_ok": not shape_wrong,

                      "accent_fix": accent_fix, "shape_fix": shape_fix})

    return items

# -------------------------

# 2. Rhythm similarity

# (Onset envelope — works for slow chants, no beat needed)

# -------------------------

def get_onset_envelope(y, sr):

    """

    Captures syllable attack patterns over time.

    Much better than beat_track for mantras/chants

    which have no drum beats.

    """

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    if onset_env.max() > 0:

        onset_env = onset_env / onset_env.max()

    return onset_env

# --------------------------------------------------------

# 4. Text similarity (No eSpeak / No phonemizer needed)

# --------------------------------------------------------

# -------------------------

# Clean text

# -------------------------

def clean_text(text):

    text = text.lower()

    text = re.sub(r'[^\u0900-\u097Fa-z\s]', '', text)  # keep Devanagari + latin + spaces

    text = re.sub(r'\s+', ' ', text).strip()

    return text





def normalize_sanskrit_phonetic(text):

    """

    Normalizes MMS-1B urd-script_devanagari output for Sanskrit comparison.

    Handles anusvāra/nasal equivalences, sibilant merging, schwa/halant cleanup.

    """

    t = text
    t = unicodedata.normalize("NFC", t)

    # 1. Homorganic nasal ↔ Anusvāra equivalences (Pāṇini 8.4.58 anusvārasya yayi parasavarṇaḥ)
    t = t.replace("म्ब", "ंब").replace("म्प", "ंप")
    t = t.replace("न्द", "ंद").replace("न्ध", "ंध").replace("न्त", "ंत").replace("न्न", "ंन")
    t = t.replace("ण्ड", "ंड").replace("ण्ट", "ंट")
    t = t.replace("ङ्क", "ंक").replace("ङ्ग", "ंग")
    t = t.replace("ञ्ज", "ंज").replace("ञ्च", "ंच")
    t = t.replace("ग्न", "घ्न")

    # 2. Sibilant equivalence (Śar pratyāhāra: ष ↔ श)
    t = t.replace("ष", "श")

    # 3. Retroflex ↔ dental nasal equivalence (ण ↔ न)
    t = t.replace("ण", "न")

    # 4. Semivowel ↔ labial stop (Pāṇinian ba/va abheda: ब ↔ व)
    t = t.replace("ब", "व")

    # 5. Visarga & post-vocalic aspiration (ASR ending -फ़ or -ह for ः)
    t = re.sub(r'([अ-ह])फ़\b', r'\1ः', t)
    t = re.sub(r'([अ-ह])ह\b', r'\1ः', t)

    # 6. Halant / ZWNJ / ZWJ cleanup
    t = t.replace("्\u200d", "").replace("्\u200c", "")
    t = re.sub(r'्+', '्', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def clean_for_match(text: str) -> str:
    """
    Generalized Paninian consonant skeleton normalizer.
    Strips matras, viramas, and visargas, mapping homorganic sounds
    (sibilants, nasals, labials, aspirates) to their base classes so that
    MMS ASR dialect spelling variations match canonical Sanskrit words
    universally across any mantra without overfitting to hardcoded phrases.
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text.lower())
    # Strip matras, halants, anusvaras, visargas to extract consonant skeleton
    t = re.sub(r'[्ािीुूृॄेैोौंःँ]', '', t)
    # Sibilants (Śar प्रत्याहार: श, ष, स -> स)
    t = t.replace('ष', 'स').replace('श', 'स')
    # Nasals (Ñam प्रत्याहार: ण, ङ, ञ, म -> न)
    t = t.replace('ण', 'न').replace('ङ', 'न').replace('ञ', 'न').replace('म', 'न')
    # Dental / Retroflex normalization (ट, ठ -> त; ड, ढ -> द)
    t = t.replace('ट', 'त').replace('ठ', 'त').replace('ड', 'द').replace('ढ', 'द')
    # Labial normalization (ब ↔ व)
    t = t.replace('ब', 'व')
    # Aspirate / stop normalization
    t = t.replace('ध', 'द').replace('थ', 'त').replace('भ', 'व').replace('ख', 'क')
    t = t.replace('घ', 'ग').replace('छ', 'च').replace('झ', 'ज').replace('फ', 'प').replace('फ़', 'प')
    t = re.sub(r'[^a-z\u0900-\u097F]', '', t)
    return t.strip()





# -------------------------

# Sanskrit syllable splitter

# (much better than eSpeak for mantras)

# -------------------------

def split_syllables(text):

    """

    Splits Devanagari or romanized Sanskrit/mantra text into syllables.

    """

    if re.search(r'[\u0900-\u097F]', text):

        pattern = r'(?:[\u0915-\u0939][\u094D])*[\u0915-\u0939][\u093E-\u094C\u0902\u0903\u0901]*|[\u0905-\u0914][\u0902\u0903\u0901]*'

        syllables = re.findall(pattern, text)

        return syllables if syllables else list(text.replace(" ", ""))

    else:

        return re.findall(r'[bcdfghjklmnpqrstvwxyz]*[aeiou]+[bcdfghjklmnpqrstvwxyz]*', text)



# =============================================================================

# 6. FEEDBACK ENGINE

# =============================================================================

# Generates structured, actionable feedback in Vedic chanting terminology.

# Covers all 4 dimensions: pronunciation (ucchāraṇa), pitch (svara),

# rhythm (laya), and voice quality (nāda).

#

# Feedback structure:

#   - overall_grade    : Uttama / Madhyama / Ādi / Prārambhika

#   - dimension_report : per-dimension score + what went wrong + how to fix

#   - priority_issues  : top 3 things to fix first (sorted by impact)

#   - praise           : what the user did well (keeps motivation high)

#   - sadhana_tip      : one focused practice suggestion

# =============================================================================





def score_to_grade(score):
    """Map 0-100 score to a traditional Sanskrit proficiency label with English translation in brackets."""
    if score >= 80:
        return "Uttama (Excellent)"
    elif score >= 60:
        return "Madhyama (Intermediate)"
    elif score >= 40:
        return "Ādi (Foundation)"
    else:
        return "Prārambhika (Beginner)"


# ---------- per-dimension feedback builders ----------------------------------

 

def pronunciation_feedback(text_sim, ref_syllables, user_syllables, ref_words, user_words,  ref_clean="", user_clean=""):

    """

    Ucchāraṇa (उच्चारण) — Pronunciation feedback.

    Finds exactly which syllables or words differ and explains them.

    """

    issues   = []

    praises  = []

    tips     = []

 

    # --- find mismatched words ---

    matcher    = SequenceMatcher(None, ref_words, user_words)

    wrong_words = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag in ('replace', 'delete'):

            wrong_words.extend(ref_words[i1:i2])

    if wrong_words:

        issues.append(

            f"Incorrect ucchāraṇa (pronunciation) detected for: "

            f"'{', '.join(wrong_words[:4])}'"

            + (" and more..." if len(wrong_words) > 4 else "")

        )

 

    # --- find mismatched syllables ---

    syl_matcher   = SequenceMatcher(None, ref_syllables, user_syllables)

    wrong_syls    = []

    for tag, i1, i2, j1, j2 in syl_matcher.get_opcodes():

        if tag in ('replace', 'delete'):

            wrong_syls.extend(ref_syllables[i1:i2])

    if wrong_syls:

        issues.append(

            f"Akṣara (syllable) errors in: '{', '.join(wrong_syls[:5])}'"

            + (" and more..." if len(wrong_syls) > 5 else "")

        )

 

    # --- specific Sanskrit pronunciation tips for common errors ---

    user_flat = user_clean.replace(" ", "")

    ref_flat  = ref_clean.replace(" ", "")

 

    # Check visarga (ḥ sound) — often dropped by beginners

    if 'h' in ref_flat and 'h' not in user_flat:

        issues.append("Visarga (ḥ) sounds are missing — the soft 'h' at syllable ends must be audible")

        tips.append(

            "Visarga sādhana: practice each visarga syllable in isolation — "

            "e.g., 'namaḥ' → breathe out on the 'ḥ' like a soft echo"

        )

 

    # Check anusvara (ṃ/ṅ nasals) — often replaced with plain 'm'

    if 'ng' in ref_flat or 'nm' in ref_flat:

        if 'ng' not in user_flat and 'nm' not in user_flat:

            issues.append(

                "Anusvāra (ṃ) nasalization is missing — "

                "syllables like 'aṃ', 'oṃ' need a nasal resonance, not a hard 'm'"

            )

            tips.append(

                "Anusvāra sādhana: hum 'mmm' and feel the vibration in your skull — "

                "that nasal resonance is the anusvāra quality"

            )

 

    # Praise if text similarity is high

    if text_sim >= 75:

        praises.append("Your mantra words and syllables are clearly recognizable — shuddha ucchāraṇa (pure pronunciation) foundation is present")

 

    how_to_fix = []

    if wrong_words:

        how_to_fix.append(

            "Repeat each incorrect word 10× in isolation before rejoining it to the mantra — "

            "this is called 'pada-abhyāsa' (word-level practice)"

        )

    if wrong_syls:

        how_to_fix.append(

            "Break the mantra into individual akṣaras (syllables) and chant them with a pause between each — "

            "'krama-pāṭha' technique"

        )

    how_to_fix += tips

 

    return issues, praises, how_to_fix

 

 

def pitch_feedback(pitch_combined, pitch_similarity, zone_sim, accent_sim,

                   shape_sim, slope_sim, zone_feedback, shape_feedback,

                   word_svara_feedback=None):

    """

    Svara feedback — now word-level aware.

    Returns 4 values: issues, per_word_issues, praises, fixes

    """

    issues          = []

    per_word_issues = []  # NEW — word-by-word breakdown

    praises         = []

    fixes           = []



    # A. Overall contour

    if pitch_similarity < 50:

        issues.append("Svara-krama (melodic arc) diverges significantly from reference")

        fixes.append("Listen to reference 3x with eyes closed, trace the pitch mentally, "

                     "then hum melody on 'aa' before adding words")

    elif pitch_similarity < 75:

        issues.append("Svara-krama is partially correct but drifts in some sections")

        fixes.append("Sa-grama sadhana: hum the pitch curve on 'aa' first, then add mantra text")



    # B. Word-by-word svara breakdown  ← THE KEY NEW SECTION

    accent_errors = 0

    shape_errors  = 0

    correct_words = []



    if word_svara_feedback:

        for item in word_svara_feedback:

            if item["accent_ok"] and item["shape_ok"]:

                correct_words.append(item["word"])

                continue

            if not item["accent_ok"]:

                accent_errors += 1

            if not item["shape_ok"]:

                shape_errors += 1



            detail = f"Word {item['word_num']}: '{item['word']}'"

            if not item["accent_ok"]:

                detail += (f"\n     Accent  — expected: {item['ref_accent']}  |  "

                           f"you sang: {item['user_accent']}")

                if item["accent_fix"]:

                    detail += f"\n     Fix: {item['accent_fix']}"

            if not item["shape_ok"]:

                detail += (f"\n     Shape   — expected: {item['ref_shape']}  |  "

                           f"you sang: {item['user_shape']}")

                if item["shape_fix"]:

                    detail += f"\n     Fix: {item['shape_fix']}"

            per_word_issues.append(detail)



        if accent_errors:

            issues.append(f"Svara-sthana errors on {accent_errors} word(s) — "

                          f"wrong udatta/anudatta/svarita placement changes the meaning. "

                          f"See word-by-word breakdown below.")

        if shape_errors:

            issues.append(f"Svara-akrti errors on {shape_errors} word(s) — "

                          f"pitch shape within vowel (rising/falling/circumflex) incorrect.")

        if correct_words:

            praises.append(f"Correct svara on: {', '.join(correct_words)}")

    else:

        # Fallback if word-level detail unavailable

        if accent_sim < 60:

            issues.append("Svara-sthana errors detected — udatta on wrong syllables "

                          "(word-level detail unavailable)")

            fixes.append("Learn svara markers from printed text with accent notation")



    # C. Zone-level (supplementary context)

    for fb in zone_feedback:

        if "Udatta" in fb and "not rising" in fb:

            issues.append("Udatta zone too flat — raised accent must lift above anudatta base")

            fixes.append("On each accented word (see list above): push pitch up suddenly, "

                         "not gradually. The lift must be clear.")

        elif "Svarita" in fb and "not dropping" in fb:

            issues.append("Svarita zone not falling after peak")

            fixes.append("After the peak word: let voice glide DOWN. "

                         "Like a ball thrown up — the fall is part of the accent.")

        elif "Anudatta" in fb and "unstable" in fb:

            issues.append("Anudatta region unsteady — low section before accent must be calm")

            fixes.append("Hold a drone at natural speaking pitch for 1 min — "

                         "this is your anudatta baseline.")

        elif "timing" in fb.lower():

            issues.append("Accent peak timing is off — udatta arriving too early or late")

            fixes.append("Chant at half speed with hand-clap on each syllable. "

                         "Mark the udatta clap and practice landing on it.")



    # D. Slope

    if slope_sim < 50:

        issues.append("Svara-vega (pitch transition speed) is incorrect")

        fixes.append("Mimic reference 5x focusing ONLY on how fast pitch moves, not words")



    # E. Praises

    if pitch_combined >= 75:

        praises.append("Overall svara-sadhana shows good understanding of the melodic arc")

    if zone_sim >= 80:

        praises.append("All three svara zones (anudatta, udatta, svarita) present and well-shaped")



    return issues, per_word_issues, praises, fixes  # now 4 return values

 

 

def rhythm_feedback(tempo_similarity, ref_audio, audio, sr):

    """

    Laya (लय) — Rhythm / Tempo feedback.

    """

    issues  = []

    praises = []

    fixes   = []

 

    ref_duration  = len(ref_audio) / ref_sr

    user_duration = len(audio)     / sr

    duration_ratio = user_duration / (ref_duration + 1e-9)

 

    if tempo_similarity < 50:
        if duration_ratio > 3.2:
            issues.append(
                f"Laya is excessively prolonged ({round(duration_ratio, 1)}× longer than reference). "
                "In Vedic recitation, dragging the laya excessively dilutes the mantra's śakti."
            )
            fixes.append(
                "Aim for a steady cadence — practice keeping full recitation between 10s and 30s."
            )
        elif duration_ratio > 1.35:
            praises.append(
                f"Vilambita laya: Meditative, serene pacing ({round(duration_ratio, 1)}× reference duration)."
            )
        elif duration_ratio < 0.7:

            issues.append(

                f"Laya is too fast — your chant is compressed to {round(duration_ratio, 1)}× the reference length. "

                "Rushing (druta-laya) causes syllable merging and loss of mantra clarity"

            )

            fixes.append(

                "Practice in vilambita-laya (slow tempo) — chant at half your current speed, "

                "holding each vowel for its full mātrā (mora) count before moving on"

            )

        else:

            issues.append(

                "Laya (rhythmic flow) is irregular — syllable durations are uneven "

                "even though the overall length is close"

            )

            fixes.append(

                "Krama-pāṭha sādhana: chant with a steady hand-clap on every syllable — "

                "each clap forces equal duration for each akṣara"

            )

    elif tempo_similarity < 75:

        issues.append(

            "Minor laya deviations detected — some syllables are stretched or compressed "

            "beyond the natural mātrā (mora) proportion"

        )

        fixes.append(

            "Record yourself and listen back counting mātrās: "

            "short vowels = 1 mātrā, long vowels = 2 mātrās. "

            "Ensure this ratio is maintained throughout"

        )

    else:

        praises.append("Laya (rhythmic timing) is well-maintained — syllable flow follows the reference closely")

 

    # Check onset pattern regularity

    user_onset_local = get_onset_envelope(audio, sr)

    onset_std = float(np.std(np.diff(np.where(user_onset_local > 0.5)[0]))) if np.any(user_onset_local > 0.5) else 0

    if onset_std > 20:

        issues.append(

            "Syllable onset pattern is irregular — some syllables attack too hard or too softly, "

            "breaking the samatvam (evenness) of the chant"

        )

        fixes.append(

            "Practice 'mṛdu-pāṭha' (soft reading): chant very softly so you cannot force hard attacks — "

            "this trains even onset strength"

        )

 

    return issues, praises, fixes

 

 

def voice_quality_feedback(mfcc_similarity):

    """

    Nāda (नाद) — Voice quality / timbre feedback.

    """

    issues  = []

    praises = []

    fixes   = []

 

    if mfcc_similarity < 40:

        issues.append(

            "Nāda-guṇa (voice quality / resonance) is significantly different from the reference — "

            "the timbral character of your voice needs adjustment for this mantra"

        )

        fixes.append(

            "Warm up with 'Nāda-sādhana': hum 'mmm' for 2 minutes feeling chest resonance, "

            "then 'nnn' feeling nasal resonance, then 'ṅṅṅ' feeling skull resonance — "

            "find which resonance mode matches the reference chant"

        )

        fixes.append(

            "Check your posture: sit in sukhāsana (comfortable cross-legged position) with spine erect — "

            "slouching compresses the svara-yantra (voice box) and changes the nāda quality"

        )

    elif mfcc_similarity < 65:

        issues.append(

            "Nāda-guṇa has room for improvement — some formants (vowel resonances) "

            "do not match the reference mantra's tonal character"

        )

        fixes.append(

            "Focus on vowel openness: Sanskrit 'a' is an open, round sound (like 'aum' prefix) — "

            "do not collapse it to the English schwa 'uh'"

        )

        fixes.append(

            "Practice the mantra in a bathroom or tile room to hear your resonance clearly — "

            "a rich, ringing nāda indicates correct throat/mouth shaping"

        )

    elif mfcc_similarity < 80:

        issues.append(

            "Minor nāda inconsistencies — vowel quality drifts slightly in the middle of the chant"

        )

        fixes.append(

            "Maintain 'jihvā-mūla' (tongue root) position consistently — "

            "do not let the tongue tense or retreat mid-chant"

        )

    else:

        praises.append(

            "Nāda-guṇa (voice quality) is authentic — your resonance closely mirrors the reference chant's timbral signature"

        )

 

    if mfcc_similarity >= 70:

        praises.append("Voice consistency is good throughout the chant — no major tonal breaks detected")

 

    return issues, praises, fixes

 

 

# ---------- priority ranking -------------------------------------------------

 

def rank_priority_issues(text_sim, pitch_combined, tempo_similarity, mfcc_similarity):

    """

    Identifies which dimension needs the most work,

    ranked by impact on overall score × severity of the gap.

    """

    # weight mirrors the overall score formula

    dimensions = [

    ("Uccharana (Pronunciation)",  text_sim,         0.40),

    ("Nada (Voice Quality)",        mfcc_similarity,  0.25),

    ("Svara (Pitch / Accent)",      pitch_combined,   0.20),

    ("Laya (Rhythm)",               tempo_similarity, 0.15),

    ]

    # Store impact as explicit 4th element — prevents unstable sort ordering

    dimensions = [(name, score, weight, round(weight * (100 - score), 2))

                 for name, score, weight in dimensions]

    ranked = sorted(dimensions, key=lambda x: x[3], reverse=True)

    return ranked  # (name, score, weight, impact)

 

 

# ---------- sadhana tip generator --------------------------------------------

 

def generate_sadhana_tip(overall, text_sim, pitch_combined, tempo_similarity, mfcc_similarity):

    """

    Returns one focused daily-practice recommendation based on the biggest gap.

    """

    priority = rank_priority_issues(text_sim, pitch_combined, tempo_similarity, mfcc_similarity)

    weakest_dim, weakest_score, _, _ = priority[0]

 

    if overall >= 85:

        return (

            "Siddhi-sādhana: you are at Uttama level. Now focus on 'bhāvopāsanā' — "

            "chant with full meditative intention. Correct form + intention = complete mantra-sādhana"

        )

    elif "Pronunciation" in weakest_dim:

        return (

            "Daily sādhana: 10 minutes of 'pada-pāṭha' — chant the mantra word-by-word, "

            "pause after each word and verify it against the reference before continuing. "

            "Do this for 21 days to build correct saṃskāra (mental impression)"

        )

    elif "Svara" in weakest_dim:

        return (

            "Daily sādhana: 10 minutes of 'svara-abhyāsa' — chant only the pitch melody "

            "on a single vowel 'ā' first (no words), then overlay the mantra text. "

            "This isolates svara training from ucchāraṇa"

        )

    elif "Rhythm" in weakest_dim:

        return (

            "Daily sādhana: 10 minutes of 'tāla-pāṭha' — clap on every syllable while chanting. "

            "Use vilambita-laya (slow tempo) for the first 5 minutes, "

            "then madhya-laya (medium) for the next 5"

        )

    else:  # Nāda

        return (

            "Daily sādhana: 10 minutes of 'nāda-dhyāna' — before chanting, hum 'Aum' for 3 minutes "

            "feeling the vibration in chest, throat, and head. "

            "This opens the three resonance chambers needed for authentic mantra nāda"

        )

 

 

# ---------- master feedback function -----------------------------------------

 

def generate_full_feedback(

    text_sim, pitch_combined, tempo_similarity, mfcc_similarity,

    pitch_similarity, zone_sim, accent_sim, shape_sim, slope_sim,

    zone_feedback, shape_feedback,

    ref_syllables, user_syllables, ref_words, user_words,

    overall,

    word_svara_feedback=None,

    char_sim_raw=0.0, word_sim_raw=0.0, syl_sim_raw=0.0,

    duration_ratio=1.0

):

    """

    Master feedback generator.

    Returns a structured dict with all feedback data,

    and prints a formatted report.

    """

 

    # --- collect per-dimension feedback ---

    uc_issues, uc_praises, uc_fixes = pronunciation_feedback(

        text_sim, ref_syllables, user_syllables, ref_words, user_words, ref_clean=clean_text(ref_mantra), user_clean=" ".join(user_words)

    )

    sv_issues, sv_per_word, sv_praises, sv_fixes = pitch_feedback(

        pitch_combined, pitch_similarity, zone_sim, accent_sim,

        shape_sim, slope_sim, zone_feedback, shape_feedback,

        word_svara_feedback=word_svara_feedback

    )

    la_issues, la_praises, la_fixes = rhythm_feedback(

        tempo_similarity, ref_audio, audio, sr

    )

    na_issues, na_praises, na_fixes = voice_quality_feedback(mfcc_similarity)

 

    # --- overall grade ---

    overall_grade = score_to_grade(overall)

 

    # --- priority ranking ---

    priority_dims = rank_priority_issues(text_sim, pitch_combined, tempo_similarity, mfcc_similarity)

 

    # --- sadhana tip ---

    sadhana_tip = generate_sadhana_tip(overall, text_sim, pitch_combined, tempo_similarity, mfcc_similarity)
    all_praises = uc_praises + sv_praises + la_praises + na_praises

    # Return structured dict for programmatic use / UI display
    return {

        "overall_score" : round(overall, 2),

        "overall_grade" : overall_grade,

        "mantra"        : ref_mantra,

        "dimensions": {

            "uccharana"  : {

                "score": round(text_sim, 2),

                "char_sim": round(char_sim_raw * 100, 1),

                "word_sim": round(word_sim_raw * 100, 1),

                "syl_sim": round(syl_sim_raw * 100, 1),

                "issues": uc_issues, "fixes": uc_fixes, "praises": uc_praises

            },

            "svara"      : {"score": round(pitch_combined, 2),  "issues": sv_issues, "fixes": sv_fixes, "praises": sv_praises},

            "laya"       : {

                "score": round(tempo_similarity, 2),

                "duration_ratio": duration_ratio,

                "issues": la_issues, "fixes": la_fixes, "praises": la_praises

            },

            "nada"       : {"score": round(mfcc_similarity, 2), "issues": na_issues, "fixes": na_fixes, "praises": na_praises},

        },

        "priority_order"  : [d[0] for d in priority_dims],

        "sadhana_tip"     : sadhana_tip,

        "all_praises"     : all_praises,

    }

def _build_empty_or_silence_response(msg, mantra_id="ganesha"):
    minfo = MANTRAS.get(mantra_id, MANTRAS["ganesha"])
    _ref_json_path = os.path.join(BASE_DIR, minfo["config_file"])
    try:
        with open(_ref_json_path, "r", encoding="utf-8") as _rjf:
            _ref_annot = json.load(_rjf)
        ref_words_list = _ref_annot.get("words", [])
    except Exception:
        ref_words_list = []

    dev_words = [w.get("devanagari", "") for w in ref_words_list] if ref_words_list else minfo["default_text"].split()
    iast_words = [w.get("iast", "") for w in ref_words_list] if ref_words_list else ["" for _ in dev_words]
    num_words = len(dev_words)

    word_align = [
        {
            "index": i,
            "expected_devanagari": dev_words[i],
            "expected_iast": iast_words[i],
            "heard_token": "",
            "lexical_score": 0.0,
            "acoustic_score": 0.0,
            "combined_score": 0.0,
            "status": "red",
            "user_start_sec": 0.0,
            "user_end_sec": 0.0,
            "ref_start_sec": ref_words_list[i]["start_sec"] if i < len(ref_words_list) else 0.0,
            "ref_end_sec": ref_words_list[i]["end_sec"] if i < len(ref_words_list) else 0.0,
        }
        for i in range(num_words)
    ]

    pe_words = [
        {
            "index": i,
            "devanagari": dev_words[i],
            "iast": iast_words[i],
            "word_match_score": 0.0,
            "status": "inconclusive",
            "user_start_sec": 0.0,
            "user_end_sec": 0.0,
            "ref_start_sec": ref_words_list[i]["start_sec"] if i < len(ref_words_list) else 0.0,
            "ref_end_sec": ref_words_list[i]["end_sec"] if i < len(ref_words_list) else 0.0,
            "trimmed_user_start_sec": 0.0,
            "trimmed_user_end_sec": 0.0,
            "duration_sec": 0.0,
            "alignment_confidence": 0.0,
            "contrasts": []
        }
        for i in range(num_words)
    ]

    return {
        "overall_score": 0.0,
        "overall_grade": "Prārambhika (Beginner)",
        "mantra_id": mantra_id,
        "mantra_name": minfo["name"],
        "mantra": ref_mantra or minfo["default_text"],
        "user_transcript": "",
        "is_valid_mantra": False,
        "matched_words_count": 0,
        "gate_message": msg,
        "word_alignment": word_align,
        "phonetic_evaluation": {
            "model_version": "hybrid_heuristic_v1",
            "summary": {"total_words": num_words, "acceptable": 0, "review": 0, "inconclusive": num_words, "average_word_score": 0.0},
            "words": pe_words
        },
        "svara_word_detail": [],
        "duration_ratio": 0.0,
        "dimensions": {
            "uccharana": {"score": 0.0, "char_sim": 0.0, "word_sim": 0.0, "syl_sim": 0.0, "issues": [msg], "fixes": [f"Record in a quiet environment and chant the full {minfo['name']} clearly."], "praises": []},
            "svara": {"score": 0.0, "issues": ["No pitch contour detected in silence"], "fixes": [], "praises": []},
            "laya": {"score": 0.0, "duration_ratio": 0.0, "issues": ["No rhythm detected"], "fixes": [], "praises": []},
            "nada": {"score": 0.0, "issues": ["No vocal timbre detected"], "fixes": [], "praises": []},
        },
        "priority_order": ["Uccharana (Pronunciation)", "Svara (Pitch / Accent)", "Laya (Rhythm)", "Nada (Voice Quality)"],
        "sadhana_tip": "Check your microphone connection and ensure your voice is clearly audible.",
        "all_praises": [],
        "scores": {
            "text_similarity": 0.0,
            "pitch_combined": 0.0,
            "tempo_similarity": 0.0,
            "mfcc_similarity": 0.0,
            "overall": 0.0,
            "pitch_breakdown": {
                "contour_shape": 0.0,
                "zone_accuracy": 0.0,
                "accent_placement": 0.0,
                "syllable_shape": 0.0,
                "slope_steepness": 0.0,
            }
        },
        "priority": []
    }


# =============================================================================

# 8. ENTRY POINT — called by api.py per request

# =============================================================================

def load_audio_safely(path: str, target_sr: int = 16000):
    """
    Robust audio loader supporting standard audio formats (WAV, MP3, FLAC, OGG)
    via librosa/soundfile, with zero-dependency fallbacks for scipy.io.wavfile
    and QuickTime/MOV/MP4 video/audio containers (LPCM 16/24/32-bit).
    """
    try:
        y, sr = librosa.load(path, sr=target_sr)
        return y.astype(float), sr
    except Exception:
        pass

    try:
        import scipy.io.wavfile as wavfile
        sr_native, data = wavfile.read(path)
        if data.dtype == np.int16:
            y = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            y = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.uint8:
            y = (data.astype(np.float32) - 128.0) / 128.0
        else:
            y = data.astype(np.float32)
        if y.ndim > 1:
            y = y.mean(axis=1)
        if sr_native != target_sr:
            y = librosa.resample(y, orig_sr=sr_native, target_sr=target_sr)
        return y.astype(float), target_sr
    except Exception:
        pass

    try:
        import struct
        with open(path, 'rb') as f:
            data = f.read()

        trak_soun = data.find(b'mhlrsoun')
        if trak_soun != -1:
            sr_native = 44100
            mdhd_pos = data.find(b'mdhd', max(0, trak_soun - 400), trak_soun + 400)
            if mdhd_pos != -1:
                sr_native = int.from_bytes(data[mdhd_pos+20:mdhd_pos+24], 'big')

            stsd_idx = data.find(b'stsd', trak_soun)
            num_channels = 2
            bits_per_sample = 16
            is_big_endian = False

            lpcm_idx = data.find(b'lpcm', stsd_idx, stsd_idx + 300)
            if lpcm_idx != -1:
                ver = int.from_bytes(data[lpcm_idx+12:lpcm_idx+14], 'big')
                if ver == 2:
                    sr_native = int(struct.unpack('>d', data[lpcm_idx+36:lpcm_idx+44])[0])
                    num_channels = int.from_bytes(data[lpcm_idx+44:lpcm_idx+48], 'big')
                    bits_per_sample = int.from_bytes(data[lpcm_idx+52:lpcm_idx+56], 'big')
                    flags = int.from_bytes(data[lpcm_idx+56:lpcm_idx+60], 'big')
                    is_big_endian = bool(flags & 2)
                else:
                    num_channels = int.from_bytes(data[lpcm_idx+20:lpcm_idx+22], 'big')
                    bits_per_sample = int.from_bytes(data[lpcm_idx+22:lpcm_idx+24], 'big')

            stsc_idx = data.find(b'stsc', trak_soun)
            stsc_entries = int.from_bytes(data[stsc_idx+8:stsc_idx+12], 'big')
            stsc_table = []
            for i in range(stsc_entries):
                fc, spc, desc = struct.unpack('>III', data[stsc_idx+12+i*12:stsc_idx+24+i*12])
                stsc_table.append((fc, spc))

            stco_idx = data.find(b'stco', trak_soun)
            chunk_offsets = []
            if stco_idx != -1:
                entries = int.from_bytes(data[stco_idx+8:stco_idx+12], 'big')
                for i in range(entries):
                    chunk_offsets.append(int.from_bytes(data[stco_idx+12+i*4:stco_idx+16+i*4], 'big'))
            else:
                co64_idx = data.find(b'co64', trak_soun)
                if co64_idx != -1:
                    entries = int.from_bytes(data[co64_idx+8:co64_idx+12], 'big')
                    for i in range(entries):
                        chunk_offsets.append(int.from_bytes(data[co64_idx+12+i*8:co64_idx+20+i*8], 'big'))

            bytes_per_sample = (bits_per_sample // 8) * num_channels
            audio_bytes = bytearray()
            for chunk_idx, offset in enumerate(chunk_offsets, 1):
                spc = 0
                for fc, samples_in_c in reversed(stsc_table):
                    if chunk_idx >= fc:
                        spc = samples_in_c
                        break
                chunk_len = spc * bytes_per_sample
                audio_bytes.extend(data[offset:offset+chunk_len])

            raw = bytes(audio_bytes)
            if bits_per_sample == 16:
                dtype = '>i2' if is_big_endian else '<i2'
                arr = np.frombuffer(raw, dtype=dtype).astype(np.float32) / 32768.0
            elif bits_per_sample == 24:
                u = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
                if is_big_endian:
                    i32 = (u[:, 0].astype(np.int32) << 16) | (u[:, 1].astype(np.int32) << 8) | u[:, 2].astype(np.int32)
                else:
                    i32 = u[:, 0].astype(np.int32) | (u[:, 1].astype(np.int32) << 8) | (u[:, 2].astype(np.int32) << 16)
                i32[i32 >= 0x800000] -= 0x1000000
                arr = i32.astype(np.float32) / 8388608.0
            elif bits_per_sample == 32:
                dtype = '>i4' if is_big_endian else '<i4'
                arr = np.frombuffer(raw, dtype=dtype).astype(np.float32) / 2147483648.0
            else:
                raise ValueError(f'Unsupported bits per sample: {bits_per_sample}')

            if num_channels > 1:
                arr = arr.reshape(-1, num_channels).mean(axis=1)

            if sr_native != target_sr:
                arr = librosa.resample(arr, orig_sr=sr_native, target_sr=target_sr)
            return arr.astype(float), target_sr
    except Exception as e:
        raise RuntimeError(f"Could not decode audio from {path}: {e}")

    raise RuntimeError(f"Unsupported audio format in {path}")


def refine_canonical_word_slices(
    canonical_words_meta,
    ctc_tokens,
    audio_duration,
    y_audio=None,
    sr=16000
):
    """
    Globally aligns canonical words C_0..C_{M-1} to CTC speech tokens T_0..T_{N-1}
    using monotonic Dynamic Programming, resolving compounds, and refines boundaries:
    - Expands Word 0 onset backward to natural speech onset (captures initial plosive/vowel).
    - Expands Word M-1 coda forward to natural decay (captures trailing visarga/vowel decay).
    - Identifies silence / RMS energy valleys between adjacent words to split gaps cleanly.
    - Preserves minimum word duration (~200ms) for audible playback.
    """
    M = len(canonical_words_meta)
    N = len(ctc_tokens)

    canon_texts = [w["devanagari"] for w in canonical_words_meta]
    ref_durs = [max(0.2, float(w.get("end_sec", 1.0) - w.get("start_sec", 0.0))) for w in canonical_words_meta]

    if N == 0:
        tot_ref = sum(ref_durs)
        curr_t = 0.1
        results = []
        for i, cw in enumerate(canonical_words_meta):
            dur = (ref_durs[i] / max(1e-6, tot_ref)) * max(0.5, audio_duration - 0.2)
            results.append({
                'index': i,
                'devanagari': cw["devanagari"],
                'user_start_sec': round(curr_t, 3),
                'user_end_sec': round(curr_t + dur, 3),
                'duration_sec': round(dur, 3),
                'status': 'review',
                'matched_text': '(interpolated)',
                'sim': 0.0,
                's_tok': None,
                'e_tok': None
            })
            curr_t += dur
        return results

    def calc_token_sim(cw_text, sp_text):
        c_norm = normalize_sanskrit_phonetic(clean_text(cw_text)).replace(" ", "")
        c_skel = clean_for_match(cw_text).replace(" ", "")
        sp_norm = normalize_sanskrit_phonetic(clean_text(sp_text)).replace(" ", "")
        sp_skel = clean_for_match(sp_text).replace(" ", "")

        s_norm = SequenceMatcher(None, c_norm, sp_norm).ratio()
        s_skel = SequenceMatcher(None, c_skel, sp_skel).ratio() if (c_skel and sp_skel) else 0.0

        if (c_norm in sp_norm or sp_norm in c_norm) and len(sp_norm) >= 2:
            s_norm = max(s_norm, 0.75)
        if (c_skel in sp_skel or sp_skel in c_skel) and len(sp_skel) >= 2:
            s_skel = max(s_skel, 0.75)

        if cw_text == "ॐ":
            om_full_words = {
                "ॐ", "ओम", "ओम्", "ऊम", "उम", "औम", "अउम", "आउम", "गोम",
                "om", "oom", "oum", "aum", "ohm",
                "ऊँ", "ऊं", "ओं", "ओँ", "ओ", "ऊ", "अम", "अों", "हूँ"
            }
            sp_clean = sp_text.lower().strip()
            if sp_clean in om_full_words:
                return 1.0
            om_prefixes = (
                "ॐ", "ओम", "ओम्", "ऊम", "औम", "अउम", "om", "oom", "oum", "aum",
                "ऊं", "ओं", "ओँ", "ओ", "ऊ"
            )
            if any(sp_clean.startswith(p) for p in om_prefixes) and len(sp_clean) <= 8:
                return 0.95
            return 0.0

        return max(s_norm, s_skel * 0.95)

    dp = np.full((M + 1, N + 1), -1e9)
    parent = {}
    dp[0, 0] = 0.0
    for i in range(1, M + 1):
        dp[i, 0] = dp[i - 1, 0] - 0.08
        parent[(i, 0)] = (i - 1, 0, None)

    for i in range(1, M + 1):
        cw = canon_texts[i - 1]
        for end_tok in range(1, N + 1):
            skip_val = dp[i - 1, end_tok] - 0.08
            if skip_val > dp[i, end_tok]:
                dp[i, end_tok] = skip_val
                parent[(i, end_tok)] = (i - 1, end_tok, None)

            max_tok_lookback = 1 if cw == "ॐ" else 3
            for start_tok in range(max(0, end_tok - max_tok_lookback), end_tok):
                group_text = " ".join(ctc_tokens[t]['text'] for t in range(start_tok, end_tok))
                sim = calc_token_sim(cw, group_text)

                prev_best = -1e9
                prev_best_tok = -1
                for prev_tok in range(0, start_tok + 1):
                    val = dp[i - 1, prev_tok]
                    if val > prev_best:
                        prev_best = val
                        prev_best_tok = prev_tok

                if prev_best > -1e8:
                    cand_val = prev_best + sim
                    if cand_val > dp[i, end_tok]:
                        dp[i, end_tok] = cand_val
                        parent[(i, end_tok)] = (i - 1, prev_best_tok, (start_tok, end_tok - 1, sim, group_text))

            # Compound sharing: allow canonical word i to share token end_tok - 1 with word i - 1
            cur_tok_text = ctc_tokens[end_tok - 1]['text']
            sim_single = calc_token_sim(cw, cur_tok_text)
            c_norm = normalize_sanskrit_phonetic(clean_text(cw)).replace(" ", "")
            sp_norm = normalize_sanskrit_phonetic(clean_text(cur_tok_text)).replace(" ", "")
            c_skel = clean_for_match(cw).replace(" ", "")
            sp_skel = clean_for_match(cur_tok_text).replace(" ", "")
            is_subword = (c_norm in sp_norm) or (c_skel in sp_skel) or (sp_norm in c_norm) or (sp_skel in c_skel) or (sim_single >= 0.50)

            if is_subword and dp[i - 1, end_tok] > -1e8:
                cand_val = dp[i - 1, end_tok] + sim_single * 0.98
                if cand_val > dp[i, end_tok]:
                    dp[i, end_tok] = cand_val
                    parent[(i, end_tok)] = (i - 1, end_tok, (end_tok - 1, end_tok - 1, sim_single, cur_tok_text))

    best_end = int(np.argmax(dp[M, :]))
    curr = (M, best_end)
    anchors = [None] * M

    while curr in parent:
        prev_i, prev_tok, match_info = parent[curr]
        w_idx = curr[0] - 1
        if match_info is not None and match_info[2] >= 0.35:
            s_tok, e_tok, sim, txt = match_info
            anchors[w_idx] = {
                'start_sec': ctc_tokens[s_tok]['start_sec'],
                'end_sec': ctc_tokens[e_tok]['end_sec'],
                'sim': sim,
                'text': txt,
                's_tok': s_tok,
                'e_tok': e_tok
            }
        curr = (prev_i, prev_tok)

    # Multi-word compound span partitioning across any group of consecutive words sharing the same token span
    k = 0
    while k < M:
        if anchors[k]:
            k_end = k
            while (k_end + 1 < M and anchors[k_end + 1] and
                   anchors[k_end + 1]['s_tok'] == anchors[k]['s_tok'] and
                   anchors[k_end + 1]['e_tok'] == anchors[k]['e_tok']):
                k_end += 1

            if k_end > k:
                # Group k..k_end share the exact same token span
                tot_r = sum(ref_durs[j] for j in range(k, k_end + 1))
                s_t = anchors[k]['start_sec']
                e_t = anchors[k]['end_sec']
                curr_t = s_t
                for j in range(k, k_end + 1):
                    dur_j = (ref_durs[j] / max(1e-6, tot_r)) * (e_t - s_t)
                    anchors[j]['start_sec'] = curr_t
                    anchors[j]['end_sec'] = curr_t + dur_j
                    curr_t += dur_j
            k = k_end + 1
        else:
            k += 1

    final_slices = [None] * M
    for i in range(M):
        if anchors[i]:
            final_slices[i] = [anchors[i]['start_sec'], anchors[i]['end_sec']]

    # First anchored index
    first_anchored_idx = None
    for i in range(M):
        if final_slices[i] is not None:
            first_anchored_idx = i
            break

    if first_anchored_idx is None:
        first_anchored_idx = 0
        final_slices[0] = [0.1, 0.1 + ref_durs[0]]

    if first_anchored_idx > 0:
        first_s = final_slices[first_anchored_idx][0]
        avail_start = min(0.1, max(0.0, first_s - 0.05))
        avail_end = first_s
        tot_ref = sum(ref_durs[:first_anchored_idx])
        curr_t = avail_start
        for i in range(first_anchored_idx):
            dur = (ref_durs[i] / max(1e-6, tot_ref)) * max(0.0, avail_end - avail_start)
            final_slices[i] = [curr_t, curr_t + dur]
            curr_t += dur

    # Last anchored index
    last_anchored_idx = None
    for i in range(M - 1, -1, -1):
        if final_slices[i] is not None:
            last_anchored_idx = i
            break

    if last_anchored_idx < M - 1:
        avail_start = final_slices[last_anchored_idx][1]
        avail_end = max(avail_start + 0.5, audio_duration - 0.1)
        tot_ref = sum(ref_durs[last_anchored_idx + 1:])
        curr_t = avail_start
        for i in range(last_anchored_idx + 1, M):
            dur = (ref_durs[i] / max(1e-6, tot_ref)) * (avail_end - avail_start)
            final_slices[i] = [curr_t, curr_t + dur]
            curr_t += dur

    # Interpolate gaps between anchors
    i = 0
    while i < M:
        if final_slices[i] is None:
            gap_start_idx = i
            while i < M and final_slices[i] is None:
                i += 1
            gap_end_idx = i
            prev_end = final_slices[gap_start_idx - 1][1]
            next_start = final_slices[gap_end_idx][0] if gap_end_idx < M else audio_duration

            if next_start <= prev_end + 0.1:
                next_start = prev_end + sum(ref_durs[gap_start_idx:gap_end_idx]) * 0.7

            tot_ref = sum(ref_durs[gap_start_idx:gap_end_idx])
            curr_t = prev_end
            for k in range(gap_start_idx, gap_end_idx):
                dur = (ref_durs[k] / max(1e-6, tot_ref)) * (next_start - prev_end)
                final_slices[k] = [curr_t, curr_t + dur]
                curr_t += dur
        else:
            i += 1

    # Acoustic Boundary Relaxation using audio energy and silence valleys
    if y_audio is not None and len(y_audio) > 1024:
        hop = 64
        rms = librosa.feature.rms(y=y_audio, frame_length=256, hop_length=hop)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)

        def find_energy_valley(t_start, t_end):
            """Finds time of minimum energy within [t_start, t_end]."""
            if t_end <= t_start:
                return t_start
            m = (rms_times >= t_start) & (rms_times <= t_end)
            if np.any(m):
                sub_rms = rms[m]
                sub_times = rms_times[m]
                min_i = np.argmin(sub_rms)
                return float(sub_times[min_i])
            return 0.5 * (t_start + t_end)

        # 1. Expand Word 0 onset backward to capture initial consonant / vowel onset
        w0_s, w0_e = final_slices[0]
        search_back_start = max(0.0, w0_s - 0.20)
        v0 = find_energy_valley(search_back_start, max(search_back_start + 0.02, w0_s - 0.03))
        final_slices[0][0] = round(max(0.0, min(w0_s, v0)), 3)

        # 2. Refine inter-word boundaries by searching for true energy valley between words
        for k in range(M - 1):
            e_k = final_slices[k][1]
            s_next = final_slices[k + 1][0]

            if s_next > e_k:
                v_start = max(final_slices[k][0] + 0.15, e_k - 0.15)
                v_end = min(final_slices[k + 1][1] - 0.15, s_next + 0.15)
            elif s_next < e_k:
                v_start = max(final_slices[k][0] + 0.15, s_next - 0.15)
                v_end = min(final_slices[k + 1][1] - 0.15, e_k + 0.15)
            else:
                v_start = max(final_slices[k][0] + 0.15, e_k - 0.25)
                v_end = min(final_slices[k + 1][1] - 0.15, e_k + 0.25)

            if v_end > v_start:
                t_valley = find_energy_valley(v_start, v_end)
                final_slices[k][1] = round(t_valley, 3)
                final_slices[k + 1][0] = round(t_valley, 3)

        # 3. Expand final Word M-1 coda forward to capture trailing vowel decay / visarga
        w_last_s, w_last_e = final_slices[M - 1]
        search_forward_end = min(audio_duration, w_last_e + 0.35)
        v_last = find_energy_valley(max(w_last_s + 0.15, w_last_e + 0.05), search_forward_end)
        final_slices[M - 1][1] = round(min(audio_duration, max(w_last_e, v_last)), 3)

    min_word_dur = 0.20
    for i in range(M - 1):
        s_i, e_i = final_slices[i]
        s_next, e_next = final_slices[i + 1]

        if e_i < s_i + min_word_dur:
            e_i = s_i + min_word_dur
            final_slices[i][1] = round(e_i, 3)

        if s_next < e_i:
            if anchors[i] is None and anchors[i + 1] is not None:
                final_slices[i][1] = round(s_next, 3)
            else:
                mid = (e_i + s_next) / 2.0
                if mid - s_i >= min_word_dur and e_next - mid >= min_word_dur:
                    final_slices[i][1] = round(mid, 3)
                    final_slices[i+1][0] = round(mid, 3)
                else:
                    final_slices[i][1] = round(s_next, 3) if s_next - s_i >= min_word_dur else round(s_i + min_word_dur, 3)
                    final_slices[i+1][0] = final_slices[i][1]
                    if final_slices[i+1][1] < final_slices[i+1][0] + min_word_dur:
                        final_slices[i+1][1] = round(final_slices[i+1][0] + min_word_dur, 3)

    if final_slices[M - 1][1] < final_slices[M - 1][0] + min_word_dur:
        final_slices[M - 1][1] = min(audio_duration, round(final_slices[M - 1][0] + min_word_dur, 3))

    evaluated_words = []
    for i in range(M):
        raw_s = round(final_slices[i][0], 3)
        raw_e = round(final_slices[i][1], 3)
        dur = round(raw_e - raw_s, 3)
        evaluated_words.append({
            'index': i,
            'devanagari': canon_texts[i],
            'user_start_sec': raw_s,
            'user_end_sec': raw_e,
            'duration_sec': dur,
            'status': 'acceptable' if (anchors[i] and anchors[i]['sim'] >= 0.50) else 'review',
            'matched_text': anchors[i]['text'] if anchors[i] else '(interpolated)',
            'sim': round(anchors[i]['sim'], 2) if anchors[i] else 0.0,
            's_tok': anchors[i]['s_tok'] if anchors[i] else None,
            'e_tok': anchors[i]['e_tok'] if anchors[i] else None
        })

    return evaluated_words


def analyze_chant(user_audio_path: str, mantra_id: str = "ganesha") -> dict:

    """

    Runs the full analysis on a user audio file for the specified mantra.

    All functions above are used as-is — nothing is changed.

    Returns the feedback_result dict for the API to serve as JSON.

    """

    if mantra_id not in MANTRAS:
        mantra_id = DEFAULT_MANTRA_ID

    _load_references(mantra_id)
    minfo = MANTRAS[mantra_id]

    global audio, sr, pitch, tempo, mfcc   # make these available to feedback functions

                                            # that reference them (e.g. rhythm_feedback)



    # ── Load user chant ──
    audio_raw, sr = load_audio_safely(user_audio_path, target_sr=16000)

    user_dur = float(len(audio_raw) / sr)

    # Voice Activity / Silence detection
    rms = librosa.feature.rms(y=audio_raw, frame_length=1024, hop_length=256)[0]
    max_rms = float(np.max(rms)) if len(rms) > 0 else 0.0
    mean_rms = float(np.mean(rms)) if len(rms) > 0 else 0.0

    if user_dur < 1.0 or max_rms < 0.012 or mean_rms < 0.002:
        return _build_empty_or_silence_response("No audible chanting detected. The recording is silent or too quiet. Please check your microphone.", mantra_id=mantra_id)

    audio_trimmed, user_trim_idx = librosa.effects.trim(audio_raw, top_db=45)
    user_trim_offset_sec = float(user_trim_idx[0]) / sr
    audio = preprocess_for_analysis(audio_trimmed, sr)

    # ── CTC Word Segmentation & Active Analysis Window ──
    audio_16k = audio
    inputs = MMS_FEATURE_EXTRACTOR(audio_16k, sampling_rate=16000, return_tensors="pt")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
    else:
        inputs = inputs.to(device)

    with torch.inference_mode():
        logits = MMS_MODEL(**inputs).logits.cpu()
    predicted_ids = torch.argmax(logits, dim=-1)
    user_text = MMS_TOKENIZER.decode(predicted_ids[0].tolist(), skip_special_tokens=True).strip().lower()
    print(f"MMS transcript: {user_text}")

    num_frames = logits.shape[1]
    sec_per_frame = (len(audio_16k) / 16000.0) / max(1, num_frames)

    pred_list = predicted_ids[0].tolist()
    collapsed = []
    for t, pid in enumerate(pred_list):
        if pid != 0:
            if len(collapsed) == 0 or collapsed[-1]['id'] != pid or (t - collapsed[-1]['end_frame'] > 1):
                collapsed.append({'id': pid, 'start_frame': t, 'end_frame': t})
            else:
                collapsed[-1]['end_frame'] = t

    ctc_words = []
    curr_tokens = []
    curr_start = None
    curr_end = None
    for item in collapsed:
        pid = item['id']
        if pid == 4:
            if curr_tokens:
                text = MMS_TOKENIZER.decode(curr_tokens, skip_special_tokens=True).strip()
                n = normalize_sanskrit_phonetic(clean_text(text)).replace(" ", "")
                if n:
                    ctc_words.append({'text': text, 'norm': n, 'start_sec': curr_start * sec_per_frame, 'end_sec': (curr_end + 1) * sec_per_frame})
                curr_tokens = []
                curr_start = None
        else:
            if curr_start is None:
                curr_start = item['start_frame']
            curr_end = item['end_frame']
            curr_tokens.append(pid)
    if curr_tokens:
        text = MMS_TOKENIZER.decode(curr_tokens, skip_special_tokens=True).strip()
        n = normalize_sanskrit_phonetic(clean_text(text)).replace(" ", "")
        if n:
            ctc_words.append({'text': text, 'norm': n, 'start_sec': curr_start * sec_per_frame, 'end_sec': (curr_end + 1) * sec_per_frame})

    spans = []
    for i in range(len(ctc_words)):
        for w_len in (1, 2, 3, 4, 5):
            if i + w_len <= len(ctc_words):
                group = ctc_words[i:i+w_len]
                comb_norm = "".join(g['norm'] for g in group)
                comb_text = " ".join(g['text'] for g in group)
                spans.append({
                    'text': comb_text,
                    'norm': comb_norm,
                    'start_sec': group[0]['start_sec'],
                    'end_sec': group[-1]['end_sec'],
                    'start_idx': i,
                    'end_idx': i + w_len
                })

    bp_path = os.path.join(BASE_DIR, minfo["config_file"])
    try:
        with open(bp_path, "r", encoding="utf-8") as bpf:
            bp_json = json.load(bpf)
        canonical_words_dev = [w["devanagari"] for w in bp_json.get("words", [])]
        canonical_words_iast = [w["iast"] for w in bp_json.get("words", [])]
    except Exception:
        canonical_words_dev = minfo["default_text"].split()
        canonical_words_iast = ["" for _ in canonical_words_dev]

    canonical_words_meta = bp_json.get("words", [])
    if not canonical_words_meta:
        canonical_words_meta = [{"index": k, "devanagari": cw, "start_sec": 0.0, "end_sec": 1.0} for k, cw in enumerate(canonical_words_dev)]

    # Global Dynamic Programming alignment for exact word boundaries
    refined_slices_trimmed = refine_canonical_word_slices(
        canonical_words_meta,
        ctc_words,
        len(audio_16k) / sr,
        y_audio=audio_16k,
        sr=sr
    )

    matched_ctc_by_canon = {}
    for c_idx, rw in enumerate(refined_slices_trimmed):
        if rw.get('s_tok') is not None and rw.get('sim', 0.0) >= 0.35:
            matched_ctc_by_canon[c_idx] = {
                'span': {
                    'text': rw['matched_text'],
                    'start_sec': rw['user_start_sec'],
                    'end_sec': rw['user_end_sec'],
                    'start_idx': rw['s_tok'],
                    'end_idx': rw.get('e_tok', rw['s_tok']) + 1
                },
                'score': round(rw['sim'] * 100.0, 1)
            }

    active_crop_offset_sec = 0.0
    active_dur = len(audio) / sr
    ref_total_dur = len(ref_audio) / ref_sr
    if matched_ctc_by_canon:
        min_canon_idx = min(matched_ctc_by_canon.keys())
        max_canon_idx = max(matched_ctc_by_canon.keys())
        first_span = matched_ctc_by_canon[min_canon_idx]['span']
        last_span = matched_ctc_by_canon[max_canon_idx]['span']

        # Safeguard against false cropping: only crop if audio is significantly longer than reference (> 1.35x)
        # AND word 0 was already matched (start) or the final word was already matched (end).
        allow_crop = (active_dur > max(12.0, ref_total_dur * 1.35))
        should_crop_start = allow_crop and (min_canon_idx == 0) and (first_span['start_sec'] > 1.5) and (first_span['start_idx'] > 0)
        should_crop_end = allow_crop and (max_canon_idx == len(canonical_words_dev) - 1) and ((active_dur - last_span['end_sec']) > 1.5) and (last_span['end_idx'] < len(ctc_words))
        if should_crop_start or should_crop_end:
            crop_start = max(0.0, first_span['start_sec'] - 0.20) if should_crop_start else 0.0
            crop_end = min(active_dur, last_span['end_sec'] + 0.25) if should_crop_end else active_dur
            if (crop_end - crop_start) >= 2.0:
                print(f"Cropping extra speech: active window [{crop_start:.2f}s, {crop_end:.2f}s] of {active_dur:.2f}s")
                audio = audio[int(crop_start * sr):int(crop_end * sr)]
                active_crop_offset_sec = crop_start
                try:
                    cropped_inputs = MMS_FEATURE_EXTRACTOR(audio, sampling_rate=16000, return_tensors="pt")
                    if device == "cuda":
                        cropped_inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in cropped_inputs.items()}
                    else:
                        cropped_inputs = cropped_inputs.to(device)
                    with torch.inference_mode():
                        cropped_logits = MMS_MODEL(**cropped_inputs).logits.cpu()
                    cropped_pids = torch.argmax(cropped_logits, dim=-1)
                    user_text = MMS_TOKENIZER.decode(cropped_pids[0].tolist(), skip_special_tokens=True).strip().lower()
                except Exception:
                    pass

    # ── Pitch ──
    pitch, _, _ = librosa.pyin(
        audio,
        sr=sr,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C6')
    )
    pitch = np.nan_to_num(pitch)

    # ── Tempo ──

    tempo_arr, _ = librosa.beat.beat_track(y=audio, sr=sr)

    tempo = float(tempo_arr[0]) if isinstance(tempo_arr, np.ndarray) else float(tempo_arr)

    # ── MFCC ──

    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)

    # ── 1. Pitch similarity ──

    pitch_voiced     = pitch[pitch > 0]

    ref_pitch_voiced = ref_pitch[ref_pitch > 0]

    if len(pitch_voiced) == 0 or len(ref_pitch_voiced) == 0:

        pitch_similarity = 0.0

    else:

        pitch_log     = np.log2(pitch_voiced)

        ref_pitch_log = np.log2(ref_pitch_voiced)

        pitch_norm     = (pitch_log - np.mean(pitch_log))         / (np.std(pitch_log)         + 1e-9)

        ref_pitch_norm = (ref_pitch_log - np.mean(ref_pitch_log)) / (np.std(ref_pitch_log)     + 1e-9)

        pitch_resampled     = resample(pitch_norm,     100)

        ref_pitch_resampled = resample(ref_pitch_norm, 100)

        D, wp = dtw(pitch_resampled.reshape(1, -1), ref_pitch_resampled.reshape(1, -1), metric='euclidean')

        dtw_distance     = D[-1, -1] / len(wp)

        pitch_similarity = 100 * np.exp(-dtw_distance / 5)

    # ── 1-a Zone analysis ──

    ref_zones,  ref_norm  = extract_pitch_zones(ref_pitch)

    user_zones, user_norm = extract_pitch_zones(pitch)

    zone_sim, zone_feedback = compare_pitch_zones(ref_zones, user_zones)

    # ── 1-b Accent classifier (speaker-relative thresholds & length-normalized comparison) ──

    ref_voiced     = ref_pitch[ref_pitch > 0]

    ref_low_thresh  = np.percentile(ref_voiced, 33) if len(ref_voiced) > 0 else 0

    ref_high_thresh = np.percentile(ref_voiced, 66) if len(ref_voiced) > 0 else 0

    ref_accent_levels  = classify_accent_levels(ref_pitch, ref_low_thresh, ref_high_thresh)

    user_accent_levels = classify_accent_levels(pitch, low_thresh=None, high_thresh=None)

    ref_voiced_acc = ref_accent_levels[ref_accent_levels > 0]
    user_voiced_acc = user_accent_levels[user_accent_levels > 0]
    if len(ref_voiced_acc) > 0 and len(user_voiced_acc) > 0:
        idx_ref = np.linspace(0, len(ref_voiced_acc) - 1, 100).round().astype(int)
        idx_user = np.linspace(0, len(user_voiced_acc) - 1, 100).round().astype(int)
        ref_resampled = ref_voiced_acc[idx_ref]
        user_resampled = user_voiced_acc[idx_user]
        accent_sim = SequenceMatcher(None, ref_resampled.tolist(), user_resampled.tolist()).ratio() * 100.0
    else:
        accent_sim = 0.0



    # ── 1-c Syllable shape ──

    ref_shapes  = analyze_syllable_shapes(ref_pitch)

    user_shapes = analyze_syllable_shapes(pitch)

    shape_sim, shape_feedback = shape_sequence_similarity(ref_shapes, user_shapes)



    # ── Slope ──

    slope_sim = pitch_slope_similarity(ref_pitch, pitch)



    # ── Combined pitch ──

    pitch_combined = (

        0.35 * pitch_similarity +

        0.25 * zone_sim         +

        0.15 * slope_sim        +

        0.15 * accent_sim       +

        0.10 * shape_sim

    )



    # ── 2. Rhythm ──

    user_onset = get_onset_envelope(audio, sr)

    ref_onset  = get_onset_envelope(ref_audio, ref_sr)

    D, wp = dtw(user_onset.reshape(1, -1), ref_onset.reshape(1, -1), metric='euclidean')

    onset_dist       = D[-1, -1] / len(wp)

    tempo_similarity = 100 * np.exp(-onset_dist / 0.3)



    # ── 3. MFCC (speaker-normalized, drop mfcc[0] energy) ──

    mfcc_scaled     = StandardScaler().fit_transform(mfcc[1:, :].T).T

    ref_mfcc_scaled = StandardScaler().fit_transform(ref_mfcc[1:, :].T).T

    delta           = librosa.feature.delta(mfcc_scaled)

    ref_delta       = librosa.feature.delta(ref_mfcc_scaled)

    mfcc_combined     = np.vstack([mfcc_scaled, delta])

    ref_mfcc_combined = np.vstack([ref_mfcc_scaled, ref_delta])

    D, wp = dtw(mfcc_combined, ref_mfcc_combined, metric='euclidean')

    mfcc_distance   = D[-1, -1] / len(wp)

    mfcc_similarity = 100 * np.exp(-mfcc_distance / 14)



    # Local Word & Phonetic Evaluation
    total_raw_offset_sec = round(user_trim_offset_sec + active_crop_offset_sec, 3)
    phonetic_evaluation_data = {}
    tmp_active_path = None
    try:
        import phonetic_evaluator as pe
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_act:
            sf.write(tmp_act.name, audio_16k, sr)
            tmp_active_path = tmp_act.name

        user_word_boundaries = []
        for w in refined_slices_trimmed:
            user_word_boundaries.append({
                'start_sec': w['user_start_sec'],
                'end_sec': w['user_end_sec'],
                'confidence': 0.90 if w['status'] == 'acceptable' else 0.70
            })

        phonetic_res = pe.evaluate_phonetics(
            user_audio_path=tmp_active_path,
            ref_audio_path=os.path.join(BASE_DIR, minfo["audio_file"]),
            annotation_path=os.path.join(BASE_DIR, minfo["config_file"]),
            precomputed_dtw_wp=None,
            user_word_boundaries=user_word_boundaries,
            user_trim_offset_sec_override=user_trim_offset_sec
        )
        phonetic_evaluation_data = phonetic_res.get("phonetic_evaluation", {})
    except Exception as pe_err:
        print(f"Phonetic evaluation notice: {pe_err}")
        phonetic_evaluation_data = {
            "error": str(pe_err),
            "summary": {"total_words": 0, "acceptable": 0, "review": 0, "inconclusive": 0},
            "words": []
        }
    finally:
        if tmp_active_path and os.path.exists(tmp_active_path):
            try:
                os.unlink(tmp_active_path)
            except Exception:
                pass

    pe_words_list = phonetic_evaluation_data.get("words", [])

    # Populate word timestamps from phonetic evaluation
    word_timestamps_data = []
    for pw in pe_words_list:
        if pw.get("user_start_sec") is not None and pw.get("user_end_sec") is not None:
            word_timestamps_data.append({
                "word": pw.get("devanagari", ""),
                "start": pw.get("user_start_sec", 0.0),
                "end": pw.get("user_end_sec", 0.0),
            })

    # ── 4. Text Recognition (MMS-1B) ──
    ref_clean  = normalize_sanskrit_phonetic(clean_text(ref_mantra))
    user_clean = normalize_sanskrit_phonetic(clean_text(user_text))
    ref_words  = ref_clean.split()
    user_words = user_clean.split()
    ref_syllables  = split_syllables(ref_clean)
    user_syllables = split_syllables(user_clean)

    # Space-invariant character similarity (accommodates compound spacing in ASR)
    ref_nospace = ref_clean.replace(" ", "")
    user_nospace = user_clean.replace(" ", "")
    char_sim = max(
        SequenceMatcher(None, ref_clean, user_clean).ratio(),
        SequenceMatcher(None, ref_nospace, user_nospace).ratio()
    )

    # Multi-token n-gram compound word similarity (automatically pairs split compounds without hardcoding)
    if ref_words and user_words:
        user_ngram_words = list(user_words)
        for w_len in (2, 3, 4, 5):
            for k in range(len(user_words) - w_len + 1):
                user_ngram_words.append("".join(user_words[k:k+w_len]))
        word_sim = sum(
            max(
                max(
                    SequenceMatcher(None, rw, uw).ratio(),
                    SequenceMatcher(None, clean_for_match(rw), clean_for_match(uw)).ratio() * 0.95
                ) for uw in user_ngram_words
            ) for rw in ref_words
        ) / len(ref_words)
    else:
        word_sim = 0.0
    syl_sim  = SequenceMatcher(None, ref_syllables, user_syllables).ratio()
    text_similarity = (0.20 * char_sim + 0.30 * word_sim + 0.50 * syl_sim) * 100

    # ── Word Alignment (green / white / red) ──
    bp_path = os.path.join(BASE_DIR, minfo["config_file"])
    try:
        with open(bp_path, "r", encoding="utf-8") as bpf:
            bp_json = json.load(bpf)
        canonical_words_dev = [w["devanagari"] for w in bp_json.get("words", [])]
        canonical_words_iast = [w["iast"] for w in bp_json.get("words", [])]
    except Exception:
        canonical_words_dev = minfo["default_text"].split()
        canonical_words_iast = ["" for _ in canonical_words_dev]

    word_alignment = []
    n_canon = len(canonical_words_dev)
    for i in range(n_canon):
        pe_w = pe_words_list[i] if i < len(pe_words_list) else {}
        acoustic_score = pe_w.get("word_match_score", 0.0)

        canon_norm = normalize_sanskrit_phonetic(canonical_words_dev[i])
        canon_no_space = canon_norm.replace(" ", "")
        lexical_score = 0.0
        heard_token = ""

        # Candidates constrained to word i's localized acoustic window
        rw = refined_slices_trimmed[i] if i < len(refined_slices_trimmed) else {}
        candidates = []
        if rw.get('matched_text') and rw['matched_text'] != '(interpolated)':
            candidates.append(rw['matched_text'])
        if i in matched_ctc_by_canon:
            candidates.append(matched_ctc_by_canon[i]['span']['text'])

        w_s_trim = rw.get('user_start_sec', 0.0)
        w_e_trim = rw.get('user_end_sec', 1.0)
        overlapping_tokens = [
            tw['text'] for tw in ctc_words
            if (tw['start_sec'] < w_e_trim + 0.20 and tw['end_sec'] > w_s_trim - 0.20)
        ]
        if overlapping_tokens:
            for w_len in (1, 2, 3, 4):
                for j in range(len(overlapping_tokens) - w_len + 1):
                    group = overlapping_tokens[j:j+w_len]
                    candidates.append("".join(group))
                    candidates.append(" ".join(group))
            # Also allow constituent subwords from merged compound tokens
            for t_txt in overlapping_tokens:
                if len(t_txt) >= 4:
                    for sub_l in (2, 3, 4, 5):
                        for start_pos in range(len(t_txt) - sub_l + 1):
                            candidates.append(t_txt[start_pos:start_pos+sub_l])

        best_lex = 0.0
        c_skel = clean_for_match(canonical_words_dev[i]).replace(" ", "")
        for cand in candidates:
            cand_norm = normalize_sanskrit_phonetic(cand)
            ls = SequenceMatcher(None, canon_norm, cand_norm).ratio() * 100.0

            cand_skel = clean_for_match(cand).replace(" ", "")
            if c_skel and cand_skel:
                skel_ls = SequenceMatcher(None, c_skel, cand_skel).ratio() * 100.0
                if (c_skel in cand_skel or cand_skel in c_skel) and len(cand_skel) >= 2 and (len(cand_skel) / max(1, len(c_skel))) >= 0.4:
                    skel_ls = max(skel_ls, 80.0)
                ls = max(ls, skel_ls * 0.95)

            if canonical_words_dev[i] == "ॐ":
                om_full_words = {
                    "ॐ", "ओम", "ओम्", "ऊम", "उम", "औम", "अउम", "आउम", "गोम",
                    "om", "oom", "oum", "aum", "ohm",
                    "ऊँ", "ऊं", "ओं", "ओँ", "ओ", "ऊ", "अम", "अों", "हूँ"
                }
                cand_clean = cand.lower().strip()
                if cand_clean in om_full_words:
                    ls = max(ls, 95.0)
                else:
                    om_prefixes = (
                        "ॐ", "ओम", "ओम्", "ऊम", "औम", "अउम", "om", "oom", "oum", "aum",
                        "ऊं", "ओं", "ओँ", "ओ", "ऊ"
                    )
                    if any(cand_clean.startswith(p) for p in om_prefixes) and len(cand_clean) <= 8:
                        ls = max(ls, 95.0)

            # If this canonical word is ॐ, and acoustic resonance is confirmed (>= 25%), ensure it is recognized
            if canonical_words_dev[i] == "ॐ" and acoustic_score >= 25.0:
                ls = max(ls, 85.0)
                if not heard_token:
                    heard_token = "ॐ"

            if ls > best_lex:
                best_lex = ls
                heard_token = cand

        user_clean_nospace = user_clean.replace(" ", "")
        if canon_no_space and canon_no_space in user_clean_nospace and (best_lex >= 35.0 or acoustic_score >= 35.0):
            best_lex = max(best_lex, 95.0)
            if not heard_token:
                heard_token = canonical_words_dev[i]

        lexical_score = best_lex

        # Determine if this word was spoken
        user_total_dur = len(audio_raw) / sr
        ref_total_dur = len(ref_audio) / ref_sr
        matched_ctc_count = len(matched_ctc_by_canon)
        is_partial_chant = (user_total_dur < 3.2) or (matched_ctc_count < max(2, int(n_canon * 0.35)) and len(user_words) < max(3, int(n_canon * 0.40)))

        has_slice = (pe_w.get("user_start_sec") is not None and pe_w.get("user_end_sec") is not None)
        if has_slice:
            if (i not in matched_ctc_by_canon) and (lexical_score < 25.0) and (acoustic_score < 25.0):
                is_spoken = False
            elif is_partial_chant and (i not in matched_ctc_by_canon) and (lexical_score < 30.0):
                is_spoken = False
            else:
                is_spoken = True
        else:
            # Word recognized via CTC anchor or high lexical score (e.g. single-word recitation)
            if (i in matched_ctc_by_canon) or (lexical_score >= 40.0):
                is_spoken = True
                if i in matched_ctc_by_canon:
                    c_span = matched_ctc_by_canon[i]['span']
                    s_val = round(c_span['start_sec'] + user_trim_offset_sec, 3)
                    e_val = round(c_span['end_sec'] + user_trim_offset_sec, 3)
                else:
                    s_val = round(user_trim_offset_sec, 3)
                    e_val = round(user_trim_offset_sec + (len(audio_trimmed) / sr), 3)
                if e_val <= s_val:
                    e_val = round(s_val + 0.8, 3)

                pe_w["user_start_sec"] = s_val
                pe_w["user_end_sec"] = e_val
                pe_w["trimmed_user_start_sec"] = s_val
                pe_w["trimmed_user_end_sec"] = e_val
                pe_w["duration_sec"] = round(e_val - s_val, 3)

                # Recompute acoustic score for single word if it was 0
                if acoustic_score < 15.0:
                    try:
                        ac_match = pe.compute_local_word_match(
                            audio_raw, sr, ref_audio, ref_sr,
                            s_val, e_val,
                            pe_w.get("ref_start_sec", 0.0), pe_w.get("ref_end_sec", 1.0)
                        )
                        acoustic_score = max(acoustic_score, ac_match)
                        pe_w["word_match_score"] = round(acoustic_score, 1)
                    except Exception:
                        pass
            else:
                is_spoken = False

        if not is_spoken:
            status = "red"
            combined = 0.0
            lexical_score = 0.0
            acoustic_score = 0.0
            u_slice_start = None
            u_slice_end = None
            final_heard_token = "(not spoken)"
            if i < len(pe_words_list):
                pe_words_list[i]["status"] = "inconclusive"
                pe_words_list[i]["user_start_sec"] = None
                pe_words_list[i]["user_end_sec"] = None
                pe_words_list[i]["word_match_score"] = 0.0
        else:
            if lexical_score >= 35.0:
                combined = 0.55 * lexical_score + 0.45 * acoustic_score
            elif lexical_score >= 25.0:
                combined = 0.50 * lexical_score + 0.50 * min(acoustic_score, 50.0)
            elif acoustic_score >= 25.0:
                combined = 0.35 * lexical_score + 0.65 * acoustic_score
            else:
                if len(user_words) > 0:
                    combined = lexical_score * 0.5
                else:
                    combined = acoustic_score * 0.60 if acoustic_score >= 60.0 else 0.0

            if combined >= 65.0:
                status = "green"
            elif combined >= 40.0:
                status = "white"
            else:
                status = "red"

            if text_similarity < 30.0 and lexical_score < 70.0 and acoustic_score < 40.0:
                status = "red"
                combined = 0.0

            u_slice_start = pe_w.get("user_start_sec", 0.0)
            u_slice_end   = pe_w.get("user_end_sec", 0.0)
            final_heard_token = heard_token if (lexical_score >= 25.0 or acoustic_score >= 30.0) else ""

            if i < len(pe_words_list):
                if status == "green":
                    pe_words_list[i]["status"] = "acceptable"
                elif status == "white" and pe_words_list[i].get("status") == "inconclusive":
                    pe_words_list[i]["status"] = "review"
                elif status == "red":
                    pe_words_list[i]["status"] = "inconclusive"

        word_alignment.append({
            "index": i,
            "expected_devanagari": canonical_words_dev[i],
            "expected_iast": canonical_words_iast[i],
            "heard_token": final_heard_token,
            "lexical_score": round(lexical_score, 1),
            "acoustic_score": round(acoustic_score, 1),
            "combined_score": round(combined, 1),
            "status": status,
            "user_start_sec": u_slice_start,
            "user_end_sec":   u_slice_end,
            "ref_start_sec":  pe_w.get("ref_start_sec", 0.0),
            "ref_end_sec":    pe_w.get("ref_end_sec", 0.0),
        })

    # Synchronize phonetic evaluation summary counts
    if "summary" in phonetic_evaluation_data and pe_words_list:
        acc_cnt = sum(1 for pw in pe_words_list if pw.get("status") == "acceptable")
        rev_cnt = sum(1 for pw in pe_words_list if pw.get("status") == "review")
        inc_cnt = sum(1 for pw in pe_words_list if pw.get("status") == "inconclusive")
        phonetic_evaluation_data["summary"]["acceptable"] = acc_cnt
        phonetic_evaluation_data["summary"]["review"] = rev_cnt
        phonetic_evaluation_data["summary"]["inconclusive"] = inc_cnt

    # ── Stage-1 Mantra Verification Gate ──
    green_count = sum(1 for wa in word_alignment if wa["status"] == "green")
    white_count = sum(1 for wa in word_alignment if wa["status"] == "white")
    matched_count = green_count + white_count

    user_duration_sec = len(audio) / sr
    ref_duration_sec = len(ref_audio) / ref_sr
    duration_ratio = round(user_duration_sec / max(ref_duration_sec, 0.1), 2)
    duration_valid = (0.28 <= duration_ratio <= 3.5) or (user_duration_sec >= 4.0 and matched_count >= 4)



    is_valid_mantra = (
        len(user_words) >= 3 and
        matched_count >= 3 and
        green_count >= 1 and
        text_similarity >= 30.0 and
        duration_valid
    )

    m_name = minfo["name"]
    if not is_valid_mantra:
        if len(user_words) == 0:
            gate_message = f"No recognizable Sanskrit chanting detected. Please chant the full {m_name} clearly."
        elif len(user_words) < 3:
            gate_message = (
                f"Recitation is too brief ({len(user_words)} word(s) heard: '{user_text}'). "
                f"The full {m_name} requires all {n_canon} words."
            )
        elif text_similarity < 30.0:
            gate_message = (
                f"Different chant detected. Text similarity with {m_name} is only {round(text_similarity, 1)}% "
                f"({matched_count}/{n_canon} words verified). Heard: '{user_clean}'."
            )
        elif green_count < 1 or matched_count < 3:
            gate_message = (
                f"Recitation does not match {m_name}. "
                f"Only {matched_count}/{n_canon} words matched ({green_count} strong, need ≥ 3 matched). "
                f"Text similarity: {round(text_similarity, 1)}%."
            )

        elif not duration_valid:

            gate_message = (

                f"Chant tempo anomaly: duration ({round(user_duration_sec, 1)}s) is outside expected range "

                f"({duration_ratio}x reference duration)."

            )

        else:

            gate_message = (

                f"Recitation verification failed ({matched_count}/{n_canon} words matched, "

                f"text similarity: {round(text_similarity, 1)}%)."

            )

    else:

        gate_message = (

            f"✓ Mantra verified: {green_count}/{n_canon} words strong, "

            f"{white_count}/{n_canon} partial. Duration ratio: {duration_ratio}x."

        )



    # ── 5. Overall (Dominant 80% weight to legacy Vedic dimensions, 20% to micro-phonetic evaluation) ──
    legacy_overall = (
        0.40 * text_similarity  +
        0.25 * mfcc_similarity  +
        0.20 * pitch_combined   +
        0.15 * tempo_similarity
    )

    pe_summary = phonetic_evaluation_data.get("summary", {})
    phonetic_score = float(pe_summary.get("average_word_score", legacy_overall))

    overall = 0.80 * legacy_overall + 0.20 * phonetic_score

    if not is_valid_mantra:
        overall = min(overall * 0.15, 10.0)
        if text_similarity < 15.0:
            overall = min(overall, 5.0)



    # ── Word svara maps (using exact ref timestamps from JSON) ──

    import json as _json

    _ref_json_path = os.path.join(BASE_DIR, minfo["config_file"])

    try:

        with open(_ref_json_path, "r", encoding="utf-8") as _rjf:

            _ref_annot = _json.load(_rjf)

        ref_word_timestamps = [

            {

                "word": w["devanagari"],

                "start": max(0.0, w["start_sec"] - ref_trim_offset_sec),

                "end": max(0.0, w["end_sec"] - ref_trim_offset_sec),

            }

            for w in _ref_annot.get("words", [])

        ]

    except Exception:

        ref_word_timestamps = []



    ref_svara_map       = build_word_svara_map(ref_pitch, ref_word_timestamps, ref_sr) if ref_word_timestamps else build_ref_word_svara_map(ref_pitch, ref_words, ref_audio, ref_sr)

    user_svara_map      = build_word_svara_map(pitch, word_timestamps_data, sr)

    word_svara_feedback = compare_word_svara_maps(ref_svara_map, user_svara_map)



    # ── Feedback ──

    feedback_result = generate_full_feedback(

        text_similarity, pitch_combined, tempo_similarity, mfcc_similarity,

        pitch_similarity, zone_sim, accent_sim, shape_sim, slope_sim,

        zone_feedback, shape_feedback,

        ref_syllables, user_syllables, ref_words, user_words,

        overall,

        word_svara_feedback=word_svara_feedback,

        char_sim_raw=char_sim, word_sim_raw=word_sim, syl_sim_raw=syl_sim,

        duration_ratio=duration_ratio

    )



    # ── Add extra fields the API needs ──

    feedback_result["mantra_id"]         = mantra_id

    feedback_result["mantra_name"]       = minfo["name"]

    feedback_result["user_transcript"]   = user_text

    feedback_result["phonetic_evaluation"] = phonetic_evaluation_data

    feedback_result["svara_word_detail"] = word_svara_feedback

    feedback_result["is_valid_mantra"]   = is_valid_mantra

    feedback_result["matched_words_count"] = matched_count

    feedback_result["gate_message"]      = gate_message

    feedback_result["word_alignment"]    = word_alignment

    feedback_result["duration_ratio"]    = duration_ratio

    feedback_result["scores"] = {

        "text_similarity" : round(text_similarity,  2),

        "pitch_combined"  : round(pitch_combined,   2),

        "tempo_similarity": round(tempo_similarity, 2),

        "mfcc_similarity" : round(mfcc_similarity,  2),

        "overall"         : round(overall,          2),

        "pitch_breakdown" : {

            "contour_shape"   : round(pitch_similarity, 2),

            "zone_accuracy"   : round(zone_sim,         2),

            "accent_placement": round(accent_sim,        2),

            "syllable_shape"  : round(shape_sim,         2),

            "slope_steepness" : round(slope_sim,         2),

        }

    }

    feedback_result["priority"] = [

        {"dimension": d, "score": round(s, 2), "impact": imp}

        for d, s, w, imp in rank_priority_issues(

            text_similarity, pitch_combined, tempo_similarity, mfcc_similarity

        )

    ]

    return feedback_result





# =============================================================================

# 9. RUN DIRECTLY (python compare_chant.py) — unchanged behaviour

# =============================================================================

if __name__ == "__main__":

    import traceback

    try:

        result = analyze_chant("mantra.wav")

        print("\n========== RAW SCORES ==========")

        print("Text Similarity  :", result["scores"]["text_similarity"],  "%")

        print("Pitch Similarity :", result["scores"]["pitch_combined"],   "%")

        print("Rhythm Similarity:", result["scores"]["tempo_similarity"], "%")

        print("Voice Similarity :", result["scores"]["mfcc_similarity"],  "%")

        print("Overall Score    :", result["scores"]["overall"],          "%")

        print("================================")

    except Exception:

        traceback.print_exc()