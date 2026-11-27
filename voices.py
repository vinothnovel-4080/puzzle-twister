"""Saved presenter voices for Puzzle Twister videos (Kokoro TTS, free, runs locally or on GitHub).

    emma   American accent  (Kokoro voice af_heart, the voice of the daily puzzle reels)
    priya  Indian accent    (60% hf_alpha + 40% af_heart, Indian sound with clear English)

A preset is a fixed recipe, so every video gets exactly the same voice.
Not used by the daily posting pipeline; for presenter / explainer videos.

    import voices
    audio, sr = voices.speak("priya", "Hello and welcome!")      # numpy float32, 24000 Hz
    voices.save("emma", "Hello!", "hello.wav")

Env: KOKORO_DIR (folder with kokoro-v1.0.onnx and voices-v1.0.bin; default ./models)
Usage: python voices.py [name ...]   -> writes a sample for each voice to out/voices/
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.environ.get("KOKORO_DIR", os.path.join(HERE, "models"))

# name: (display name, accent, {kokoro voice: weight}, speed)
PRESETS = {
    "emma": ("Emma", "US", {"af_heart": 1.0}, 1.0),
    "priya": ("Priya", "Indian", {"hf_alpha": 0.6, "af_heart": 0.4}, 1.0),
}

_k = None


def _kokoro():
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    return _k


def style(name):
    """The voice's style vector (a weighted blend of Kokoro voices)."""
    _, _, mix, _ = PRESETS[name]
    k = _kokoro()
    return sum(w * k.get_voice_style(v) for v, w in mix.items())


def speak(name, text, speed=None):
    """Return (audio, sample_rate) for text spoken by a saved voice."""
    speed = speed or PRESETS[name][3]
    return _kokoro().create(text, voice=style(name), speed=speed, lang="en-us")


def save(name, text, path, speed=None):
    import soundfile as sf
    audio, sr = speak(name, text, speed)
    sf.write(path, audio, sr)
    return path


if __name__ == "__main__":
    out = os.path.join(HERE, "out", "voices")
    os.makedirs(out, exist_ok=True)
    for name in sys.argv[1:] or PRESETS:
        label, accent, _, _ = PRESETS[name]
        p = save(name, f"Hi, I'm {label}. Welcome to Puzzle Twister Brain Bites!", os.path.join(out, f"{name}.wav"))
        print(f"{label} ({accent}): {p}")
