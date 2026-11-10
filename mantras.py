"""
mantras.py — Centralized, lightweight metadata catalog for Svara-Vaidya mantras.
Contains zero heavy ML dependencies (no torch, no transformers, no librosa),
enabling instant API startup and instantaneous (<5ms) reference audio streaming.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MANTRAS = {
    "ganesha": {
        "id": "ganesha",
        "name": "Shri Ganesha Shloka",
        "subtitle": "Vakratuṇḍa Mahākāya",
        "audio_file": "mantra.wav",
        "config_file": "ganesha_shloka.json",
        "features_file": "reference_features.json",
        "default_text": "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा"
    },
    "mrityunjaya": {
        "id": "mrityunjaya",
        "name": "Maha Mrityunjaya Mantra",
        "subtitle": "Tryambakaṃ Yajāmahe",
        "audio_file": "maha_mrityunjaya_mantra.wav",
        "config_file": "maha_mrityunjaya_shloka.json",
        "features_file": "mrityunjaya_reference_features.json",
        "default_text": "त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात्"
    },
    "gayatri": {
        "id": "gayatri",
        "name": "Gayatri Mantra",
        "subtitle": "Savitṛ Gāyatrī",
        "audio_file": "gayatri_mantra.wav",
        "config_file": "gayatri_shloka.json",
        "features_file": "gayatri_reference_features.json",
        "default_text": "ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात्"
    }
}

DEFAULT_MANTRA_ID = "ganesha"


def get_mantra_info(mantra_id: str) -> dict:
    """Safely retrieves mantra metadata dictionary with fallback to default."""
    m_id = (mantra_id or "").strip().lower()
    return MANTRAS.get(m_id, MANTRAS[DEFAULT_MANTRA_ID])
