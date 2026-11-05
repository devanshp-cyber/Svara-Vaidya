"""
generate_ref_annotations.py
Analyzes mantra.wav using librosa (energy/onset segmentation) to automatically
detect start and end timestamps for the 8 words of the Mahā Mṛtyuñjaya Mantra,
plus estimate internal sub-spans for target phonetic contrasts.
Outputs: ref_maha_mrityunjay.json
"""
import os
import sys
import json
import numpy as np
import librosa
import soundfile as sf

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_PATH = os.path.join(BASE_DIR, "mantra.wav")
OUTPUT_PATH = os.path.join(BASE_DIR, "ref_maha_mrityunjay.json")

WORDS_METADATA = [
    {
        "index": 0,
        "devanagari": "त्र्यम्बकं",
        "iast": "tryambakam",
        "approx_weight": 1.0,
        "phonetic_contrasts": [
            {
                "contrast_type": "conjunct_cluster",
                "label": "tryambakam_tr_cluster",
                "target_phones": ["t", "r", "y"],
                "sub_span_ratio": [0.0, 0.35],
                "expected_features": {
                    "description": "Clear tri-consonant onset cluster /tr/ or /try/",
                    "min_duration_ms": 60
                }
            },
            {
                "contrast_type": "nasal_anusvara",
                "label": "tryambakam_anusvara",
                "target_phones": ["m", "kam"],
                "sub_span_ratio": [0.65, 1.0],
                "expected_features": {
                    "description": "Labial nasalization / anusvara closure",
                    "min_duration_ms": 70
                }
            }
        ]
    },
    {
        "index": 1,
        "devanagari": "यजामहे",
        "iast": "yajāmahe",
        "approx_weight": 1.0,
        "phonetic_contrasts": [
            {
                "contrast_type": "vowel_duration_ratio",
                "label": "yajamahe_short_vs_long_vowel",
                "target_phones": ["ya", "jā"],
                "short_vowel_sub_span_ratio": [0.0, 0.28],
                "long_vowel_sub_span_ratio": [0.28, 0.65],
                "expected_features": {
                    "min_ratio": 1.3,
                    "max_ratio": 3.5,
                    "description": "Ratio of long vowel (jā) to short vowel (ya)"
                }
            }
        ]
    },
    {
        "index": 2,
        "devanagari": "सुगन्धिं",
        "iast": "sugandhim",
        "approx_weight": 1.0,
        "phonetic_contrasts": [
            {
                "contrast_type": "consonant_aspiration",
                "label": "sugandhim_dh_aspiration",
                "target_phones": ["dh"],
                "sub_span_ratio": [0.45, 0.85],
                "expected_features": {
                    "description": "Voiced dental aspirated stop /dh/ with breath release",
                    "min_high_freq_ratio": 0.15
                }
            }
        ]
    },
    {
        "index": 3,
        "devanagari": "पुष्टिवर्धनम्",
        "iast": "puṣṭivardhanam",
        "approx_weight": 1.3,
        "phonetic_contrasts": [
            {
                "contrast_type": "retroflex_cluster",
                "label": "pustivardhanam_retroflex_st",
                "target_phones": ["ṣ", "ṭ"],
                "sub_span_ratio": [0.15, 0.45],
                "expected_features": {
                    "description": "Voiceless retroflex sibilant + stop cluster /ṣṭ/",
                    "lower_spectral_centroid_shift": True
                }
            }
        ]
    },
    {
        "index": 4,
        "devanagari": "उर्वारुकमिव",
        "iast": "urvārukamiva",
        "approx_weight": 1.3,
        "phonetic_contrasts": [
            {
                "contrast_type": "vowel_duration_ratio",
                "label": "urvarukamiva_short_vs_long_vowel",
                "target_phones": ["u", "vā"],
                "short_vowel_sub_span_ratio": [0.0, 0.22],
                "long_vowel_sub_span_ratio": [0.22, 0.55],
                "expected_features": {
                    "min_ratio": 1.3,
                    "max_ratio": 3.5,
                    "description": "Ratio of long vowel (vā) to short vowel (u)"
                }
            }
        ]
    },
    {
        "index": 5,
        "devanagari": "बन्धनान्",
        "iast": "bandhanān",
        "approx_weight": 1.0,
        "phonetic_contrasts": [
            {
                "contrast_type": "consonant_aspiration",
                "label": "bandhanan_dh_aspiration",
                "target_phones": ["dh"],
                "sub_span_ratio": [0.25, 0.65],
                "expected_features": {
                    "description": "Aspirated dental stop /dh/ in medial position",
                    "min_high_freq_ratio": 0.15
                }
            },
            {
                "contrast_type": "vowel_duration_ratio",
                "label": "bandhanan_final_long_vowel",
                "target_phones": ["ba", "nān"],
                "short_vowel_sub_span_ratio": [0.0, 0.30],
                "long_vowel_sub_span_ratio": [0.55, 1.0],
                "expected_features": {
                    "min_ratio": 1.3,
                    "max_ratio": 4.0,
                    "description": "Terminal long vowel and nasal coda /nān/"
                }
            }
        ]
    },
    {
        "index": 6,
        "devanagari": "मृत्योर्मुक्षीय",
        "iast": "mṛtyormukṣīya",
        "approx_weight": 1.3,
        "phonetic_contrasts": [
            {
                "contrast_type": "conjunct_cluster",
                "label": "mrtyormuksiya_ks_cluster",
                "target_phones": ["k", "ṣ", "ī"],
                "sub_span_ratio": [0.50, 0.85],
                "expected_features": {
                    "description": "Velar stop + retroflex sibilant conjunct /kṣ/ followed by long /ī/",
                    "min_duration_ms": 80
                }
            }
        ]
    },
    {
        "index": 7,
        "devanagari": "मामृतात्",
        "iast": "māmṛtāt",
        "approx_weight": 1.0,
        "phonetic_contrasts": [
            {
                "contrast_type": "vowel_duration_ratio",
                "label": "mamrtat_long_vs_vocalic_r",
                "target_phones": ["mā", "mṛ"],
                "short_vowel_sub_span_ratio": [0.38, 0.70],
                "long_vowel_sub_span_ratio": [0.0, 0.38],
                "expected_features": {
                    "min_ratio": 1.1,
                    "max_ratio": 3.0,
                    "description": "Initial long vowel /mā/ contrasted with vocalic /ṛ/ in /mṛ/"
                }
            }
        ]
    }
]


def generate_annotations():
    print(f"Reading audio from {AUDIO_PATH}...")
    audio, sr = librosa.load(AUDIO_PATH, sr=None)
    total_duration = float(len(audio) / sr)
    print(f"Total audio duration: {total_duration:.3f}s at {sr} Hz")

    # 1. Energy envelope and onsets
    hop_length = 256
    frame_length = 1024
    rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)

    # 2. Find speech start and end boundaries (trim quiet silence at edges)
    # Use top_db=30 to locate active speech boundaries
    non_silent_intervals = librosa.effects.split(audio, top_db=28, frame_length=frame_length, hop_length=hop_length)
    if len(non_silent_intervals) > 0:
        speech_start_sec = max(0.0, float(non_silent_intervals[0][0] / sr) - 0.05)
        speech_end_sec = min(total_duration, float(non_silent_intervals[-1][1] / sr) + 0.05)
    else:
        speech_start_sec = 0.1
        speech_end_sec = total_duration - 0.1

    print(f"Active speech window: [{speech_start_sec:.2f}s, {speech_end_sec:.2f}s] (Duration: {speech_end_sec - speech_start_sec:.2f}s)")
    active_duration = speech_end_sec - speech_start_sec

    # 3. Detect major acoustic valleys (pauses between words or pādas)
    # Onset strength
    onset_env = librosa.onset.onset_strength(y=audio, sr=sr, hop_length=hop_length)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop_length, units='time')

    # Proportionate allocation with weights
    weights = [w["approx_weight"] for w in WORDS_METADATA]
    total_weight = sum(weights)
    unit_durations = [(w / total_weight) * active_duration for w in weights]

    # Calculate initial boundaries
    boundaries = [speech_start_sec]
    current_time = speech_start_sec
    for dur in unit_durations:
        current_time += dur
        boundaries.append(min(current_time, speech_end_sec))
    boundaries[-1] = speech_end_sec

    # Snap internal boundaries to nearby local energy minima if within 0.3s
    snapped_boundaries = [boundaries[0]]
    for i in range(1, len(boundaries) - 1):
        target_t = boundaries[i]
        # Look in window [target_t - 0.25, target_t + 0.25]
        mask = (times >= target_t - 0.25) & (times <= target_t + 0.25)
        if np.any(mask):
            window_rms = rms[mask]
            window_times = times[mask]
            min_idx = np.argmin(window_rms)
            best_t = float(window_times[min_idx])
            snapped_boundaries.append(round(best_t, 3))
        else:
            snapped_boundaries.append(round(target_t, 3))
    snapped_boundaries.append(round(speech_end_sec, 3))

    # Construct word entries
    annotated_words = []
    for i, meta in enumerate(WORDS_METADATA):
        start_t = float(snapped_boundaries[i])
        end_t = float(snapped_boundaries[i + 1])
        dur = end_t - start_t

        word_contrasts = []
        for c in meta["phonetic_contrasts"]:
            c_entry = {
                "contrast_type": c["contrast_type"],
                "label": c["label"],
                "target_phones": c["target_phones"],
                "expected_features": c["expected_features"]
            }
            if "sub_span_ratio" in c:
                r0, r1 = c["sub_span_ratio"]
                c_entry["sub_start_sec"] = round(start_t + r0 * dur, 3)
                c_entry["sub_end_sec"] = round(start_t + r1 * dur, 3)
            elif "short_vowel_sub_span_ratio" in c and "long_vowel_sub_span_ratio" in c:
                s0, s1 = c["short_vowel_sub_span_ratio"]
                l0, l1 = c["long_vowel_sub_span_ratio"]
                c_entry["short_vowel_sub_span"] = [round(start_t + s0 * dur, 3), round(start_t + s1 * dur, 3)]
                c_entry["long_vowel_sub_span"] = [round(start_t + l0 * dur, 3), round(start_t + l1 * dur, 3)]

            word_contrasts.append(c_entry)

        word_obj = {
            "index": meta["index"],
            "devanagari": meta["devanagari"],
            "iast": meta["iast"],
            "start_sec": round(start_t, 3),
            "end_sec": round(end_t, 3),
            "duration_sec": round(dur, 3),
            "phonetic_contrasts": word_contrasts
        }
        annotated_words.append(word_obj)

    annotation_data = {
        "mantra_id": "maha_mrityunjay",
        "mantra_text_devanagari": "त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात्",
        "mantra_text_iast": "tryambakam yajāmahe sugandhim puṣṭivardhanam urvārukamiva bandhanān mṛtyormukṣīya māmṛtāt",
        "reference_audio": "mantra.wav",
        "sample_rate": int(sr),
        "total_duration_sec": round(total_duration, 3),
        "num_words": len(annotated_words),
        "words": annotated_words,
        "generation_method": "librosa_rms_onset_snapping",
        "notes": "Reference boundaries detected from mantra.wav for the 8 words of Mahā Mṛtyuñjaya Mantra"
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(annotation_data, f, indent=4, ensure_ascii=False)

    print(f"Successfully generated reference annotations at {OUTPUT_PATH}")
    for w in annotated_words:
        print(f"  Word {w['index']+1}: {w['iast']} -> [{w['start_sec']:.2f}s - {w['end_sec']:.2f}s] ({w['duration_sec']:.2f}s)")

if __name__ == "__main__":
    generate_annotations()
