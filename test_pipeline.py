import soundfile as sf
import numpy as np
import tempfile
import os
import json
from compare_chant import analyze_chant

def run_all_tests():
    sr = 16000
    print("==================================================")
    print("RUNNING 4-POINT VALIDATION SUITE FOR AUDIO PIPELINE")
    print("==================================================")

    # -------------------------------------------------------------
    # TEST 1: Pure Silence (2s)
    # -------------------------------------------------------------
    silence = np.zeros(int(sr * 2.0))
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        silence_path = f.name
    sf.write(silence_path, silence, sr)

    try:
        res_silence = analyze_chant(silence_path)
        print("\n[TEST 1: Pure Silence]")
        print("  is_valid_mantra    :", res_silence.get("is_valid_mantra"))
        print("  overall_score      :", res_silence.get("overall_score"))
        print("  matched_words_count:", res_silence.get("matched_words_count"))
        print("  gate_message       :", res_silence.get("gate_message"))
        pe_words = res_silence.get("phonetic_evaluation", {}).get("words", [])
        print("  word statuses      :", [w.get("status") for w in pe_words])
        assert res_silence.get("is_valid_mantra") is False, "Silence should fail is_valid_mantra"
        assert res_silence.get("overall_score") == 0.0, "Silence should score 0.0"
        assert res_silence.get("matched_words_count") == 0, "Silence matched count should be 0"
        print("  -> TEST 1 PASSED: Silence immediately rejected with 0.0% score and 0 matched words.")
    finally:
        if os.path.exists(silence_path):
            os.remove(silence_path)

    # -------------------------------------------------------------
    # TEST 2: Ambient Background Noise (2.5s)
    # -------------------------------------------------------------
    noise = np.random.normal(0, 0.003, int(sr * 2.5)).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        noise_path = f.name
    sf.write(noise_path, noise, sr)

    try:
        res_noise = analyze_chant(noise_path)
        print("\n[TEST 2: Ambient Noise]")
        print("  is_valid_mantra    :", res_noise.get("is_valid_mantra"))
        print("  overall_score      :", res_noise.get("overall_score"))
        print("  matched_words_count:", res_noise.get("matched_words_count"))
        print("  gate_message       :", res_noise.get("gate_message"))
        pe_words = res_noise.get("phonetic_evaluation", {}).get("words", [])
        print("  word statuses      :", [w.get("status") for w in pe_words])
        assert res_noise.get("is_valid_mantra") is False, "Noise should fail is_valid_mantra"
        assert res_noise.get("overall_score") <= 10.0, "Noise overall score must be <= 10.0"
        print("  -> TEST 2 PASSED: Ambient noise rejected with overall_score <= 10.0%.")
    finally:
        if os.path.exists(noise_path):
            os.remove(noise_path)

    # -------------------------------------------------------------
    # TEST 3: Short 'Om' Chant (1.5s 136Hz tone)
    # -------------------------------------------------------------
    t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
    om_audio = 0.3 * np.sin(2 * np.pi * 136.1 * t)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        om_path = f.name
    sf.write(om_path, om_audio, sr)

    try:
        res_om = analyze_chant(om_path)
        print("\n[TEST 3: Short 'Om' Tone / Syllable]")
        print("  is_valid_mantra    :", res_om.get("is_valid_mantra"))
        print("  overall_score      :", res_om.get("overall_score"))
        print("  matched_words_count:", res_om.get("matched_words_count"))
        print("  gate_message       :", res_om.get("gate_message"))
        pe_words = res_om.get("phonetic_evaluation", {}).get("words", [])
        print("  word statuses      :", [w.get("status") for w in pe_words])
        align_statuses = [w.get("status") for w in res_om.get("word_alignment", [])]
        print("  alignment statuses :", align_statuses)
        assert res_om.get("is_valid_mantra") is False, "Om alone should fail is_valid_mantra"
        assert res_om.get("overall_score") <= 10.0, "Om alone score must be <= 10.0"
        assert all(s in ["red", "grey"] for s in align_statuses), "Alignment cards must be red or grey for unchanted words"
        print("  -> TEST 3 PASSED: Single syllable rejected; unchanted words marked red.")
    finally:
        if os.path.exists(om_path):
            os.remove(om_path)

    # -------------------------------------------------------------
    # TEST 4: Full Reference Ganesha Shloka (mantra.wav)
    # -------------------------------------------------------------
    ref_path = "mantra.wav"
    with open("ganesha_shloka.json", "r", encoding="utf-8") as f:
        expected_annot = json.load(f)

    res_ref = analyze_chant(ref_path)
    print("\n[TEST 4: Reference Chanting (mantra.wav)]")
    print("  is_valid_mantra    :", res_ref.get("is_valid_mantra"))
    print("  overall_score      :", res_ref.get("overall_score"))
    print("  matched_words_count:", res_ref.get("matched_words_count"))
    print("  gate_message       :", res_ref.get("gate_message"))
    pe_words = res_ref.get("phonetic_evaluation", {}).get("words", [])
    align_words = res_ref.get("word_alignment", [])
    
    print("\n  Word Timestamps & Playback Slices Verification:")
    for i, (pw, aw) in enumerate(zip(pe_words, align_words)):
        exp_start = expected_annot["words"][i]["start_sec"]
        exp_end = expected_annot["words"][i]["end_sec"]
        print(f"    Word {i+1} ({pw['devanagari']}):")
        print(f"      Expected Ref : [{exp_start:.3f}s, {exp_end:.3f}s]")
        print(f"      Phonetic Ref : [{pw.get('ref_start_sec'):.3f}s, {pw.get('ref_end_sec'):.3f}s]")
        print(f"      Align Ref    : [{aw.get('ref_start_sec'):.3f}s, {aw.get('ref_end_sec'):.3f}s]")
        print(f"      Phonetic User: [{pw.get('user_start_sec'):.3f}s, {pw.get('user_end_sec'):.3f}s]")
        print(f"      Align User   : [{aw.get('user_start_sec'):.3f}s, {aw.get('user_end_sec'):.3f}s]")
        print(f"      Status       : Phonetic={pw.get('status')} | Align={aw.get('status')} | Score={aw.get('combined_score')}")

        # Assert reference timestamps match ganesha_shloka.json
        assert abs(pw.get('ref_start_sec') - exp_start) < 1e-3, f"Word {i} ref_start_sec mismatch"
        assert abs(pw.get('ref_end_sec') - exp_end) < 1e-3, f"Word {i} ref_end_sec mismatch"
        assert abs(aw.get('ref_start_sec') - exp_start) < 1e-3, f"Word {i} align ref_start_sec mismatch"
        assert abs(aw.get('ref_end_sec') - exp_end) < 1e-3, f"Word {i} align ref_end_sec mismatch"

    assert res_ref.get("is_valid_mantra") is True, "Reference audio must pass is_valid_mantra"
    assert res_ref.get("overall_score") >= 75.0, "Reference audio score must be >= 75.0"
    assert res_ref.get("matched_words_count") >= 6, "Reference audio must match >= 6 words"
    print("\n  -> TEST 4 PASSED: Reference audio passed with full accuracy and exact timestamp alignment!")

    # -------------------------------------------------------------
    # TEST 5: Unrelated Mantra / Different Speech (user_chant2.wav)
    # -------------------------------------------------------------
    diff_path = "user_chant2.wav"
    if os.path.exists(diff_path):
        res_diff = analyze_chant(diff_path)
        print("\n[TEST 5: Unrelated Chant Rejection (user_chant2.wav)]")
        print("  is_valid_mantra    :", res_diff.get("is_valid_mantra"))
        print("  overall_score      :", res_diff.get("overall_score"))
        print("  matched_words_count:", res_diff.get("matched_words_count"))
        print("  gate_message       :", res_diff.get("gate_message"))
        diff_statuses = [w.get("status") for w in res_diff.get("word_alignment", [])]
        print("  alignment statuses :", diff_statuses)
        assert res_diff.get("is_valid_mantra") is False, "Unrelated chant must fail is_valid_mantra"
        assert res_diff.get("overall_score") <= 10.0, "Unrelated chant overall score must be <= 10.0"
        assert res_diff.get("matched_words_count") == 0, "Unrelated chant must have 0 matched words"
        assert all(s == "red" for s in diff_statuses), "All words must be red for unrelated chant"
        print("  -> TEST 5 PASSED: Unrelated chant cleanly rejected with 0/8 matched words and all red cards.")

    print("\n==================================================")
    print("ALL 5 TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
