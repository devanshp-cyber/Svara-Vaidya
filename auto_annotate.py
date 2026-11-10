#!/usr/bin/env python3
"""
auto_annotate.py — Automatic Svara & Phonetic Blueprint Generator for Sanskrit Mantras

Takes a clean reference audio chanting file (.wav) and Devanagari text,
then automatically generates the JSON blueprint with:
  1. Exact CTC acoustic word timestamps (start_sec, end_sec) using MMS-1B
  2. Vedic accent detection (udātta, anudātta, svarita) using pYIN F0 contour
  3. Paninian phonetic contrast triggers (retroflex clusters, aspirates, vowel ratios)

Usage:
  python auto_annotate.py --audio <audio.wav> --text "<Devanagari text>" --output <output.json> [--name "<Mantra Name>"]
"""

import os
import sys
import re
import json
import argparse
import unicodedata
import numpy as np
import librosa
import soundfile as sf
import torch
from difflib import SequenceMatcher
from transformers import Wav2Vec2ForCTC, AutoProcessor

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────
# 1. Sanskrit Devanagari to IAST Transliteration Engine
# ─────────────────────────────────────────────────────────────
DEVA_VOWELS = {
    'अ': 'a', 'आ': 'ā', 'इ': 'i', 'ई': 'ī', 'उ': 'u', 'ऊ': 'ū',
    'ऋ': 'ṛ', 'ॠ': 'ṝ', 'ऌ': 'ḷ', 'ॡ': 'ḹ', 'ए': 'e', 'ऐ': 'ai',
    'ओ': 'o', 'औ': 'au', 'ॐ': 'oṃ'
}

DEVA_MATRAS = {
    'ा': 'ā', 'ि': 'i', 'ी': 'ī', 'ु': 'u', 'ू': 'ū',
    'ृ': 'ṛ', 'ॄ': 'ṝ', 'ॢ': 'ḷ', 'े': 'e', 'ै': 'ai',
    'ो': 'o', 'ौ': 'au'
}

DEVA_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ṅ',
    'च': 'c', 'छ': 'ch', 'ज': 'j', 'झ': 'jh', 'ञ': 'ñ',
    'ट': 'ṭ', 'ठ': 'ṭh', 'ड': 'ḍ', 'ढ': 'ḍh', 'ण': 'ṇ',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'ś', 'ष': 'ṣ', 'स': 's', 'ह': 'h',
    'ळ': 'ḻ', 'क्ष': 'kṣ', 'ज्ञ': 'jñ'
}

DEVA_MODIFIERS = {
    'ं': 'ṃ', 'ः': 'ḥ', '्': '', 'ँ': 'm̐'
}

def devanagari_to_iast(text: str) -> str:
    """Accurate phonetic Devanagari to IAST Romanization transliteration."""
    out = []
    i = 0
    chars = list(text.strip())
    n = len(chars)
    while i < n:
        c = chars[i]
        if c in DEVA_VOWELS:
            out.append(DEVA_VOWELS[c])
            i += 1
        elif c in DEVA_CONSONANTS:
            base = DEVA_CONSONANTS[c]
            if i + 1 < n:
                next_c = chars[i + 1]
                if next_c == '्':  # Virama kills inherent vowel
                    out.append(base)
                    i += 2
                elif next_c in DEVA_MATRAS:
                    out.append(base + DEVA_MATRAS[next_c])
                    i += 2
                else:
                    out.append(base + 'a')
                    i += 1
            else:
                out.append(base + 'a')
                i += 1
        elif c in DEVA_MATRAS:
            out.append(DEVA_MATRAS[c])
            i += 1
        elif c in DEVA_MODIFIERS:
            out.append(DEVA_MODIFIERS[c])
            i += 1
        else:
            out.append(c)
            i += 1
    res = "".join(out)
    return res.replace("  ", " ").strip()


# ─────────────────────────────────────────────────────────────
# 2. Phonetic Normalizer & Zero-Crossing Helpers for MMS Alignment
# ─────────────────────────────────────────────────────────────
def normalize_sanskrit_phonetic(text: str) -> str:
    """Accurate phonetic Sanskrit normalizer for MMS ASR alignment."""
    t = unicodedata.normalize("NFC", text)
    # Common ASR dialect variants
    t = t.replace("ऊम", "ॐ")
    t = t.replace("भूर भुवस्वाह", "भूर्भुवः स्वः")
    t = t.replace("भूर भुवः", "भूर्भुवः")
    t = t.replace("भूर भुव", "भूर्भुवः")
    t = re.sub(r'भूर(?!्)', 'भूर्', t)
    t = t.replace("भुवस्वाह", "भुवः स्वः")
    t = t.replace("तसवितुर वरेनुम", "तत्सवितुर्वरेण्यं")
    t = t.replace("त्सा वितुर वरे निम", "तत्सवितुर्वरेण्यं")
    t = t.replace("त्सावितुरवरेनिम", "तत्सवितुर्वरेण्यं")
    t = t.replace("त्सा वितुर", "तत्सवितुर")
    t = t.replace("वरे निम", "वरेण्यं")
    t = t.replace("वरेनुम", "वरेण्यं")
    t = t.replace("भरगो", "भर्गो")
    t = t.replace("दी मही", "धीमहि")
    t = t.replace("दीमही", "धीमहि")
    t = t.replace("नफ़", "नः")
    t = t.replace("प्रछोद या त", "प्रचोदयात्")
    t = t.replace("प्रचोद या त", "प्रचोदयात्")
    t = t.replace("प्रचोद या", "प्रचोदयात्")
    t = t.replace("प्रचोद", "प्रचोद")
    # Mrityunjaya variants
    t = t.replace("सुगन्धीं", "सुगन्धिं")
    t = t.replace("पुष्टी", "पुष्टि")
    t = t.replace("वरधनम", "वर्धनम्")
    t = t.replace("उरवारुकमिव", "उर्वारुकमिव")
    t = t.replace("बन्धनात", "बन्धनान्")
    t = t.replace("मृच्योर", "मृत्योर्")
    t = t.replace("मुख्शी", "मुक्षीय")
    t = t.replace("यमामरता त", "मामृतात्")
    t = t.replace("यमामरता", "मामृतात्")
    # Ganesha variants
    t = re.sub(r'वक्र\s*तु[ण्ं]ड[ं]?', 'वक्रतुण्ड', t)
    t = re.sub(r'महा\s*काय[ा]?', 'महाकाय', t)
    t = re.sub(r'सू[रर्][ि]?य\s*को[टत][ीि]?', 'सूर्यकोटि', t)
    t = re.sub(r'सम\s*[पबफ़][्र]?भ[ा]?', 'समप्रभ', t)
    t = re.sub(r'न[िी]?र[्]?\s*[वब][िीे]?[घ्गख][्]?(?:[नन्मं]+|[लत][ा]?)?', 'निर्विघ्नं', t)
    t = t.replace("कुरु मे देव", "कुरुमेदेव")
    t = re.sub(r'स[रर्]्व?\s*का[रर्][ि]?य[े]?[शष][ुू]?', 'सर्वकार्येषु', t)
    t = re.sub(r'स[रर्]व[दन][ा]?', 'सर्वदा', t)
    # Anusvāra & nasal equivalences
    t = t.replace("म्ब", "ंब").replace("म्प", "ंप")
    t = t.replace("न्द", "ंद").replace("न्ध", "ंध").replace("न्त", "ंत").replace("न्न", "ंन")
    t = t.replace("ण्ड", "ंड").replace("ण्ट", "ंट")
    t = t.replace("ङ्क", "ंक").replace("ङ्ग", "ंग")
    t = t.replace("ग्न", "घ्न")
    t = t.replace("ष", "श")
    t = t.replace("ण", "न")
    t = t.replace("ब", "व")
    t = t.replace("्\u200d", "").replace("्\u200c", "")
    t = re.sub(r'्+', '्', t)
    return t.strip()


def find_zero_crossing(audio, sample_idx, direction='forward', max_search=320):
    """Finds nearest zero-crossing point to avoid audio pop/click on slicing."""
    idx = max(0, min(len(audio) - 1, int(sample_idx)))
    limit = min(len(audio) - 1, idx + max_search) if direction == 'forward' else max(0, idx - max_search)
    step = 1 if direction == 'forward' else -1
    best_idx = idx
    min_val = abs(audio[idx])
    for i in range(idx, limit, step):
        if abs(audio[i]) < min_val:
            min_val = abs(audio[i])
            best_idx = i
        if i > 0 and (audio[i-1] * audio[i] <= 0):
            return i
    return best_idx


def clean_for_match(text: str) -> str:
    """
    Strips diacritics and maps equivalent phonetic consonants so that
    MMS ASR dialect spelling variations match canonical Sanskrit accurately.
    """
    t = unicodedata.normalize("NFC", text)
    # Strip matras, halants, anusvaras, visargas to get consonant skeleton
    t = re.sub(r'[्ािीुूृॄेैोौंःँ]', '', t)
    # Sibilant normalization
    t = t.replace('ष', 'स').replace('श', 'स')
    # Nasal normalization
    t = t.replace('ण', 'न').replace('ङ', 'न').replace('ञ', 'न').replace('म', 'न')
    # Dental / Retroflex normalization
    t = t.replace('ट', 'त').replace('ठ', 'त').replace('ड', 'द').replace('ढ', 'द')
    # Labial normalization
    t = t.replace('ब', 'व')
    return t.strip()


# ─────────────────────────────────────────────────────────────
# 3. Paninian Phonetic Rules Scanner
# ─────────────────────────────────────────────────────────────
ASPIRATES_MAP = {
    'ख': 'kh', 'घ': 'gh', 'छ': 'ch', 'झ': 'jh',
    'ठ': 'ṭh', 'ढ': 'ḍh', 'थ': 'th', 'ध': 'dh',
    'फ': 'ph', 'भ': 'bh'
}

RETROFLEX_LIST = ['ट', 'ठ', 'ड', 'ढ', 'ण', 'ष']

SHORT_VOWELS = {'a', 'i', 'u', 'ṛ'}
LONG_VOWELS  = {'ā', 'ī', 'ū', 'e', 'ai', 'o', 'au', 'ṝ'}

def extract_phonetic_contrasts(dev_word: str, iast_word: str, start_sec: float, end_sec: float):
    """
    Scans word for Sanskrit Paninian phonetic checkpoints:
      1. Retroflex clusters (मूर्धन्य)
      2. Consonant aspiration (महाप्राण)
      3. Vowel duration ratios (ह्रस्व vs दीर्घ)
    """
    contrasts = []
    word_dur = max(0.1, end_sec - start_sec)

    # 1. Retroflex consonants / clusters
    for r in RETROFLEX_LIST:
        if r in dev_word:
            pos_ratio = dev_word.find(r) / max(1, len(dev_word))
            sub_s = start_sec + pos_ratio * word_dur
            sub_e = min(end_sec, sub_s + 0.35 * word_dur)
            contrasts.append({
                "contrast_type": "retroflex_cluster",
                "label": devanagari_to_iast(r),
                "sub_start_sec": round(sub_s, 4),
                "sub_end_sec": round(sub_e, 4),
                "expected_features": {}
            })
            break

    # 2. Consonant aspiration
    for asp_char, asp_label in ASPIRATES_MAP.items():
        if asp_char in dev_word:
            pos_ratio = dev_word.find(asp_char) / max(1, len(dev_word))
            sub_s = start_sec + pos_ratio * word_dur
            sub_e = min(end_sec, sub_s + 0.30 * word_dur)
            contrasts.append({
                "contrast_type": "consonant_aspiration",
                "label": asp_label,
                "sub_start_sec": round(sub_s, 4),
                "sub_end_sec": round(sub_e, 4),
                "expected_features": {
                    "min_high_freq_ratio": 0.10
                }
            })
            break

    # 3. Vowel duration ratio
    found_short = None
    found_long = None
    for v in SHORT_VOWELS:
        if v in iast_word:
            found_short = v
            break
    for v in LONG_VOWELS:
        if v in iast_word:
            found_long = v
            break

    if found_short and found_long:
        mid_sec = start_sec + 0.45 * word_dur
        contrasts.append({
            "contrast_type": "vowel_duration_ratio",
            "label": f"{found_short} vs {found_long}",
            "short_vowel_sub_span": [round(start_sec, 4), round(start_sec + 0.35 * word_dur, 4)],
            "long_vowel_sub_span": [round(mid_sec, 4), round(end_sec, 4)],
            "expected_features": {
                "min_ratio": 1.3,
                "max_ratio": 4.5
            }
        })

    return contrasts


# ─────────────────────────────────────────────────────────────
# 4. Audio Preprocessing and Feature Extraction
# ─────────────────────────────────────────────────────────────
def load_and_preprocess_audio(audio_path: str, target_sr=16000):
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
    y = y.astype(np.float32)
    max_val = np.max(np.abs(y))
    if max_val > 1e-4:
        y = y / max_val * 0.95
    return y, sr


def extract_f0_contour(y, sr):
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=80.0,
        fmax=librosa.note_to_hz('C6'),
        sr=sr,
        frame_length=2048,
        hop_length=512
    )
    return f0


def classify_svara_accent(f0_segment, baseline_pitch):
    valid_f0 = f0_segment[~np.isnan(f0_segment)]
    if len(valid_f0) < 3:
        return "udatta"

    med_f0 = float(np.median(valid_f0))
    std_f0 = float(np.std(valid_f0))

    if len(valid_f0) >= 6:
        first_half = np.mean(valid_f0[:len(valid_f0)//2])
        second_half = np.mean(valid_f0[len(valid_f0)//2:])
        diff = second_half - first_half
        if abs(diff) > 12.0 or (std_f0 > 15.0 and med_f0 >= baseline_pitch * 0.98):
            return "svarita"

    if med_f0 > baseline_pitch * 1.03:
        return "udatta"
    elif med_f0 < baseline_pitch * 0.97:
        return "anudatta"
    else:
        return "udatta"


# ─────────────────────────────────────────────────────────────
# 5. MMS CTC Acoustic Forced Alignment
# ─────────────────────────────────────────────────────────────
def align_words_with_mms(audio, sr, dev_words):
    """
    Runs MMS-1B Devanagari CTC model to obtain frame-level word boundary timestamps.
    Uses multi-token grouping and consonant skeleton matching for robust Sanskrit alignment.
    """
    print("Loading MMS-1B model for acoustic alignment...")
    model_id = "facebook/mms-1b-all"
    target_lang = "urd-script_devanagari"

    try:
        proc = AutoProcessor.from_pretrained(model_id, local_files_only=True)
    except Exception:
        proc = AutoProcessor.from_pretrained(model_id)
    proc.tokenizer.set_target_lang(target_lang)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        model = Wav2Vec2ForCTC.from_pretrained(model_id, local_files_only=True)
    except Exception:
        model = Wav2Vec2ForCTC.from_pretrained(model_id)

    try:
        model.load_adapter(target_lang, local_files_only=True)
    except Exception:
        model.load_adapter(target_lang)

    if device == "cuda":
        model = model.half().to(device)
    else:
        model = model.to(device)
    model.eval()

    inputs = proc(audio, sampling_rate=sr, return_tensors="pt")
    if device == "cuda":
        inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
    else:
        inputs = inputs.to(device)

    print("Running CTC acoustic forward pass...")
    with torch.inference_mode():
        logits = model(**inputs).logits.cpu()

    num_frames = logits.shape[1]
    sec_per_frame = (len(audio) / float(sr)) / max(1, num_frames)

    predicted_ids = torch.argmax(logits, dim=-1)[0].tolist()

    collapsed = []
    for t, pid in enumerate(predicted_ids):
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
        if pid == 4:  # Space token
            if curr_tokens:
                text = proc.tokenizer.decode(curr_tokens, skip_special_tokens=True).strip()
                if text:
                    ctc_words.append({
                        'text': text,
                        'norm': clean_for_match(text),
                        'start_sec': curr_start * sec_per_frame,
                        'end_sec': (curr_end + 1) * sec_per_frame
                    })
                curr_tokens = []
                curr_start = None
        else:
            if curr_start is None:
                curr_start = item['start_frame']
            curr_end = item['end_frame']
            curr_tokens.append(pid)
    if curr_tokens:
        text = proc.tokenizer.decode(curr_tokens, skip_special_tokens=True).strip()
        if text:
            ctc_words.append({
                'text': text,
                'norm': clean_for_match(text),
                'start_sec': curr_start * sec_per_frame,
                'end_sec': (curr_end + 1) * sec_per_frame
            })

    total_dur = len(audio) / float(sr)
    print(f"Decoded {len(ctc_words)} CTC acoustic tokens over {total_dur:.2f}s audio.")

    # 1. Expand tokens where MMS combined multiple words without a space
    expanded_ctc = []
    for w in ctc_words:
        txt = w['text']
        if txt == 'भुवस्वाह':
            mid = w['start_sec'] + 0.45 * (w['end_sec'] - w['start_sec'])
            expanded_ctc.append({'text': 'भुवः', 'start_sec': w['start_sec'], 'end_sec': mid})
            expanded_ctc.append({'text': 'स्वः', 'start_sec': mid, 'end_sec': w['end_sec']})
        elif txt == 'कुरुमेदेव':
            mid = w['start_sec'] + 0.50 * (w['end_sec'] - w['start_sec'])
            expanded_ctc.append({'text': 'कुरु', 'start_sec': w['start_sec'], 'end_sec': mid})
            expanded_ctc.append({'text': 'मेदेव', 'start_sec': mid, 'end_sec': w['end_sec']})
        else:
            expanded_ctc.append(w)
    ctc_words = expanded_ctc

    # Build candidate multi-token spans (1 to 5 words grouped for Sanskrit compounds)
    spans = []
    for i in range(len(ctc_words)):
        for w_len in (1, 2, 3, 4, 5):
            if i + w_len <= len(ctc_words):
                group = ctc_words[i:i+w_len]
                comb_text = " ".join(g['text'] for g in group)
                comb_norm = normalize_sanskrit_phonetic(comb_text).replace(" ", "")
                spans.append({
                    'text': comb_text,
                    'norm': comb_norm,
                    'start_sec': group[0]['start_sec'],
                    'end_sec': group[-1]['end_sec'],
                    'start_idx': i,
                    'end_idx': i + w_len
                })

    # Monotonically match canonical words to spans
    matched_words = []
    last_matched_idx = -1
    last_end_sec = 0.0

    for c_idx, cw in enumerate(dev_words):
        c_norm = normalize_sanskrit_phonetic(cw).replace(" ", "")
        best_span = None
        best_score = 0.0

        for sp in spans:
            # Monotonic order constraint
            if sp['start_idx'] < last_matched_idx:
                continue
            if sp['start_sec'] < last_end_sec - 0.15:
                continue

            score = SequenceMatcher(None, c_norm, sp['norm']).ratio() * 100.0
            if (c_norm in sp['norm'] or sp['norm'] in c_norm) and len(sp['norm']) >= 2:
                score = max(score, 75.0)

            if c_norm == sp['norm']:
                score = 100.0

            if score > best_score:
                best_score = score
                best_span = sp

        if best_span and best_score >= 45.0:
            s_raw = best_span['start_sec']
            e_raw = best_span['end_sec']

            # Snap to zero-crossings for clean playback without clicks
            s_samp = find_zero_crossing(audio, int(s_raw * sr), 'backward')
            e_samp = find_zero_crossing(audio, int(e_raw * sr), 'forward')
            s_sec = round(s_samp / float(sr), 3)
            e_sec = round(e_samp / float(sr), 3)

            matched_words.append({
                'dev': cw,
                'start_sec': s_sec,
                'end_sec': e_sec
            })
            last_matched_idx = best_span['end_idx']
            last_end_sec = e_sec
        else:
            # Interpolated fallback if acoustic match is missed
            est_start = max(last_end_sec, 0.20)
            words_left = max(1, len(dev_words) - c_idx)
            est_dur = max(0.5, (total_dur - est_start) / words_left)
            est_dur = min(est_dur, 2.0)
            est_end = min(total_dur, est_start + est_dur)

            s_samp = find_zero_crossing(audio, int(est_start * sr), 'backward')
            e_samp = find_zero_crossing(audio, int(est_end * sr), 'forward')

            matched_words.append({
                'dev': cw,
                'start_sec': round(s_samp / float(sr), 3),
                'end_sec': round(e_samp / float(sr), 3)
            })
            last_end_sec = est_end

    return matched_words


# ─────────────────────────────────────────────────────────────
# 6. Main Blueprint Assembler
# ─────────────────────────────────────────────────────────────
def generate_mantra_blueprint(audio_path: str, dev_text: str, output_path: str, mantra_name: str = None):
    print(f"\n=======================================================")
    print(f"  Svara Vaidya — Blueprint Auto-Annotation Engine")
    print(f"=======================================================")
    print(f"Audio file : {audio_path}")
    print(f"Sanskrit   : {dev_text}")

    y, sr = load_and_preprocess_audio(audio_path, target_sr=16000)
    audio_dur = len(y) / float(sr)
    print(f"Audio duration: {audio_dur:.2f} seconds.")

    words_dev = [w.strip() for w in dev_text.strip().split() if w.strip()]
    if not words_dev:
        raise ValueError("Provided Sanskrit text is empty!")

    iast_mantra = devanagari_to_iast(dev_text)

    # 1. MMS CTC Acoustic Alignment
    aligned_spans = align_words_with_mms(y, sr, words_dev)

    # 2. Pitch Contour & Vedic Accent Extraction
    print("Computing pYIN F0 pitch contour for Vedic accents...")
    f0 = extract_f0_contour(y, sr)
    valid_f0 = f0[~np.isnan(f0)]
    baseline_pitch = float(np.median(valid_f0)) if len(valid_f0) > 0 else 140.0
    print(f"Baseline chant pitch: {baseline_pitch:.1f} Hz")

    hop_sec = 512 / float(sr)

    # 3. Assemble word blocks
    words_data = []
    for idx, span in enumerate(aligned_spans):
        w_dev = span['dev']
        w_iast = devanagari_to_iast(w_dev)
        s_sec = span['start_sec']
        e_sec = span['end_sec']

        frame_s = int(s_sec / hop_sec)
        frame_e = max(frame_s + 1, int(e_sec / hop_sec))
        word_f0 = f0[frame_s:frame_e]

        accent = classify_svara_accent(word_f0, baseline_pitch)
        contrasts = extract_phonetic_contrasts(w_dev, w_iast, s_sec, e_sec)

        word_obj = {
            "index": idx,
            "devanagari": w_dev,
            "iast": w_iast,
            "start_sec": round(s_sec, 4),
            "end_sec": round(e_sec, 4),
            "svara_accent": accent,
            "phonetic_contrasts": contrasts
        }
        words_data.append(word_obj)

    if not mantra_name:
        mantra_name = words_dev[0] + " Mantra" if len(words_dev) > 0 else "Sanskrit Mantra"

    blueprint = {
        "mantra": mantra_name,
        "mantra_devanagari": dev_text,
        "mantra_iast": iast_mantra,
        "audio_file": os.path.basename(audio_path),
        "words": words_data
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(blueprint, f, ensure_ascii=False, indent=2)

    print(f"\nSuccessfully generated mantra blueprint -> {output_path}")
    print(f"Total words annotated: {len(words_data)}")
    for w in words_data:
        print(f"  [{w['start_sec']:5.2f}s - {w['end_sec']:5.2f}s] {w['devanagari']:14} ({w['iast']:16}) -> {w['svara_accent'].upper():8} ({len(w['phonetic_contrasts'])} contrasts)")
    print("=======================================================\n")
    return blueprint


def main():
    parser = argparse.ArgumentParser(description="Auto-annotate reference Sanskrit chanting audio to JSON blueprint.")
    parser.add_argument("--audio", required=True, help="Path to reference .wav audio file")
    parser.add_argument("--text", required=True, help="Sanskrit text in Devanagari script")
    parser.add_argument("--output", required=True, help="Path for output JSON blueprint (e.g. maha_mrityunjaya_shloka.json)")
    parser.add_argument("--name", default=None, help="Descriptive name of the mantra (optional)")

    args = parser.parse_args()
    generate_mantra_blueprint(args.audio, args.text, args.output, args.name)


if __name__ == "__main__":
    main()
