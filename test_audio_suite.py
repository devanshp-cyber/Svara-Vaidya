import os
import json
import traceback
from compare_chant import analyze_chant

def run_suite():
    print("=" * 70)
    print("RUNNING COMPREHENSIVE AUDIO SUITE ACROSS ALL TEST RECORDINGS")
    print("=" * 70)

    test_files = [
        ("mantra.wav", "Golden Reference (Male, 16kHz, Clean)", True),
        ("test_audio/correct_with_startingandendingextrawords.mp3", "MP3 with Extra Intro & Outro Speech", True),
        ("test_audio/femalevoicewithoutbgm.wav", "Slow Female Chant (23s, Vilambita Laya)", True),
        ("test_audio/femalevoicewithbgm.wav", "Female Chant with Background Music (28s)", True),
        ("test_audio/femalevoicewithbgm2.wav", "Female Chant with BGM Variant (23s)", True),
        ("test_audio/femalevoicelatestart.wav", "Female Chant with Late Start (28s)", True),
        ("test_audio/user_chant1.wav", "Partial/Other Chant (Om Gan Ganapataye, 3.6s)", False),
        ("test_audio/user_chant2.wav", "Other Chant (Om Ganeshaya Namaha, 5.4s)", False),
        ("test_audio/user_chant3.wav", "Other Chant (Om Namah Shivaya, 3.0s)", False),
        ("test_audio/another_mantra.wav", "Different Full Mantra (Maha Mrityunjaya, 16s)", False),
    ]

    results = []

    for path, desc, expected_valid in test_files:
        if not os.path.exists(path):
            print(f"Skipping {path} (file not found)")
            continue

        print(f"\n--- Testing: {os.path.basename(path)} ---")
        print(f"Description: {desc}")
        try:
            res = analyze_chant(path)
            is_valid = res.get("is_valid_mantra")
            score = res.get("overall_score")
            matched = res.get("matched_words_count")
            gate_msg = res.get("gate_message", "")
            transcript = res.get("heard_transcript", "")
            dur_ratio = res.get("duration_ratio")
            word_align = res.get("word_alignment", [])

            print(f"  Valid Mantra: {is_valid} (Expected: {expected_valid})")
            print(f"  Overall Score: {score}% | Matched Words: {matched}/8 | Duration Ratio: {dur_ratio}x")
            print(f"  Gate Message: {gate_msg}")

            # Print words breakdown
            for wa in word_align:
                idx = wa.get("index") + 1
                word = wa.get("expected_devanagari")
                status = wa.get("status")
                heard = wa.get("heard_token")
                u_s = wa.get("user_start_sec")
                u_e = wa.get("user_end_sec")
                comb = wa.get("combined_score")
                span_str = f"[{u_s:.2f}s - {u_e:.2f}s]" if (u_s is not None and u_e is not None) else "[not spoken]"
                print(f"    W{idx} {word:10s} : {status:5s} ({comb:4.1f}%) | slice: {span_str:17s} | heard: '{heard}'")

            # Assertions
            if expected_valid:
                assert is_valid is True, f"Expected {path} to pass validation gate, but got False. Gate msg: {gate_msg}"
                assert matched >= 4, f"Expected {path} to match at least 4 words, got {matched}"
                print(f"  -> SUCCESS: Recitation correctly validated!")
            else:
                assert is_valid is False, f"Expected {path} to be rejected by validation gate, but got True."
                print(f"  -> SUCCESS: Non-shloka or partial recitation correctly rejected/guarded!")

            results.append((path, desc, True, None))
        except Exception as e:
            traceback.print_exc()
            results.append((path, desc, False, str(e)))

    print("\n" + "=" * 70)
    print("SUITE SUMMARY:")
    all_passed = True
    for path, desc, success, err in results:
        status_sym = "PASS" if success else "FAIL"
        if not success:
            all_passed = False
        print(f"  [{status_sym}] {os.path.basename(path):40s} : {desc} {f'({err})' if err else ''}")
    print("=" * 70)
    if all_passed:
        print("ALL TESTS IN SUITE PASSED!")
    else:
        print("SOME TESTS FAILED.")

if __name__ == "__main__":
    run_suite()
