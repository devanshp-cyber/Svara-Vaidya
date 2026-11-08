import compare_chant as cc
import librosa
import torch

cc._load_references()

# Test femalevoicewithoutbgm.wav
print("--- TESTING FEMALE VOICE ---")
res = cc.analyze_chant("test_audio/femalevoicewithoutbgm.wav")
for wa in res['word_alignment']:
    s = wa['user_start_sec']
    e = wa['user_end_sec']
    dur = f"{(e-s):.2f}s" if (s is not None and e is not None) else "N/A"
    print(f"W{wa['index']+1} {wa['expected_devanagari']:12}: [{s} - {e}] (dur={dur}) | heard='{wa['heard_token']}'")

# Test mantra.wav
print("\n--- TESTING MANTRA.WAV ---")
res_m = cc.analyze_chant("mantra.wav")
for wa in res_m['word_alignment']:
    s = wa['user_start_sec']
    e = wa['user_end_sec']
    dur = f"{(e-s):.2f}s" if (s is not None and e is not None) else "N/A"
    print(f"W{wa['index']+1} {wa['expected_devanagari']:12}: [{s} - {e}] (dur={dur}) | heard='{wa['heard_token']}'")
