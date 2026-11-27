"""Brain Bites reel: a presenter video (e.g. from Synthesia) combined with our own graphics.

SAMPLE / TEST: not part of the daily posting pipeline.
  - Start: presenter full screen with the hook caption (grabs attention).
  - Middle: split screen - our graphics on top (captions, versus, bar chart, steps),
    presenter in the bottom half.
  - End: presenter full screen again with "SAVE THIS" and a FOLLOW button.
Scene timings come from the pauses between her sentences (ffmpeg silencedetect).

Usage: python brainbites.py presenter.mp4 out.mp4
Env:   FONT_DIR, FFMPEG, FFPROBE
"""
import math, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import explainer as X  # graphics helpers (fonts, captions, chart, steps, icons, backgrounds)

W, H, FPS = 1080, 1920, 30
SPLIT = 960  # top half = graphics, bottom half = presenter
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")
SCENES = [s["kind"] for s in X.EPISODE["scenes"]]  # hook, talk, versus, chart, steps, end


def probe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "default=nw=1", path],
                         capture_output=True, text=True).stdout
    vals = dict(l.split("=") for l in out.split() if "=" in l)
    return int(vals["width"]), int(vals["height"]), float(vals["duration"])


def sentence_times(path, n, total):
    """Start/end of n spoken blocks, cut at the n-1 longest pauses."""
    log = subprocess.run([FFMPEG, "-i", path, "-af", "silencedetect=noise=-32dB:d=0.18", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    gaps = [(e - s, (s + e) / 2) for s, e in zip(starts, ends) if 0.5 < s and e < total - 0.5]
    cuts = sorted(m for _, m in sorted(gaps, reverse=True)[: n - 1])
    if len(cuts) < n - 1:  # not enough pauses: fall back to even spacing
        cuts = [total * (i + 1) / n for i in range(n - 1)]
    b = [0.0] + cuts + [total]
    return [(b[i], b[i + 1]) for i in range(n)]


def presenter_frames(path, w, h):
    """Yield the presenter video as 1080x1920 RGB frames (scaled and cropped to fill)."""
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
    p = subprocess.Popen([FFMPEG, "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    size = W * H * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def tag(d):
    d.rounded_rectangle([60, 70, 480, 150], radius=40, fill=X.INK)
    X.text_c(d, 270, 110, "BRAIN BITES #1", X.font("ExtraBold", 44), X.YELLOW)


def top_graphics(kind, lt, sc_len, accent):
    """Our graphics for the top half (drawn on a full frame, then cropped to 0..SPLIT)."""
    img = X.background(accent)
    d = ImageDraw.Draw(img)
    sc = X.EPISODE["scenes"][SCENES.index(kind)]
    if kind == "talk":
        X.caption_words(img, sc["words"].split(), 0.1, sc_len * 0.8, lt, 500, size=86, hot=sc["hot"])
    elif kind == "versus":
        k1, k2 = X.ease_back((lt - 0.2) / 0.4), X.ease_back((lt - 1.6) / 0.4)
        if k1 > 0:
            X.icon_book(d, 280, 470, max(0.25, 0.95 * k1))
            X.text_c(d, 280, 690, "READ AGAIN", X.font("ExtraBold", 58), X.WHITE, 6)
        if lt > 1.2:
            X.text_c(d, W / 2, 470, "VS", X.font("Black", 96), X.YELLOW, 7)
        if k2 > 0:
            X.icon_test(d, 800, 470, max(0.25, 0.95 * k2))
            X.text_c(d, 800, 690, "TEST YOURSELF", X.font("ExtraBold", 56), X.WHITE, 6)
    elif kind == "chart":
        split = 0.42 * sc_len
        if lt < split:
            X.bar_chart(img, lt, ["Read again", "Self-test"], [81, 75], [X.GREY, X.TEAL], "5 MINUTES LATER", base_y=840, maxh=470)
        else:
            X.bar_chart(img, lt - split, ["Read again", "Self-test"], [42, 56], [X.GREY, X.TEAL], "ONE WEEK LATER", base_y=840, maxh=470)
    elif kind == "steps":
        X.text_c(d, W / 2, 245, "TRY THIS TODAY", X.font("Black", 88), X.YELLOW, 7)
        # each card pops in as she says that step (times in seconds into the scene)
        appear = [float(x) for x in os.environ.get("STEP_TIMES", "1.2,2.3,5.6").split(",")]
        k = sum(lt >= a for a in appear)
        X.step_cards(img, ((k - 1) * 0.9 + min(0.89, lt - appear[k - 1])) if k else -1, sc["steps"])
    tag(d)
    return img.crop((0, 0, W, SPLIT))


def shade_top(img, h=760, strength=200):
    """Dark gradient over the top of a full-screen frame, so captions stay readable."""
    g = Image.new("L", (1, h))
    for y in range(h):
        g.putpixel((0, y), int(strength * (1 - y / h) ** 1.4))
    img.paste(X.INK, (0, 0, W, h), g.resize((W, h)))


def compose(frame, t, times, total, face_y):
    i = next((k for k, (a, b) in enumerate(times) if a <= t < b), len(times) - 1)
    kind = SCENES[i]
    a, b = times[i]
    lt, sc_len = t - a, b - a
    accent = {"talk": X.TEAL, "versus": X.PURPLE, "chart": X.TEAL, "steps": X.PURPLE}.get(kind, X.CORAL)

    # how much of the screen the presenter fills: 1 = full screen, 0 = bottom half
    if kind == "hook":
        full = 1.0 - ease((t - (b - 0.35)) / 0.35)          # slide into the split as the hook ends
    elif kind == "end":
        full = ease(lt / 0.35)                               # slide back to full screen
    else:
        full = 0.0
    top_h = int(SPLIT * (1 - full))

    out = Image.new("RGB", (W, H), X.INK)
    # presenter: crop a band around her face into the space below top_h
    band_h = H - top_h
    y0 = int(min(max(face_y - band_h * 0.42, 0), H - band_h)) if band_h < H else 0
    out.paste(frame.crop((0, y0, W, y0 + band_h)), (0, top_h))
    d = ImageDraw.Draw(out)

    if kind in ("hook", "end"):
        shade_top(out)
        if kind == "hook":
            sc = X.EPISODE["scenes"][0]
            X.caption_words(out, sc["words"].split(), 0.05, min(1.6, sc_len * 0.5), lt, 250, size=104, hot=sc["hot"])
            kb = X.ease_back((lt - min(1.9, sc_len * 0.6)) / 0.35)
            if kb > 0:
                bw = 820 * kb
                d.rounded_rectangle([W / 2 - bw / 2, 470, W / 2 + bw / 2, 590], radius=60, fill=X.CORAL, outline=X.INK, width=6)
                if kb > 0.8:
                    X.text_c(d, W / 2, 530, "YOU MIGHT BE WASTING TIME", X.font("ExtraBold", 50), X.WHITE)
            if lt < 0.25:  # quick flash on the very first frames
                out = Image.blend(out, Image.new("RGB", (W, H), X.WHITE), 0.6 * (1 - lt / 0.25))
                d = ImageDraw.Draw(out)
        else:
            sc = X.EPISODE["scenes"][-1]
            X.caption_words(out, sc["words"].split(), 0.3, 1.0, lt, 360, size=100, hot=sc["hot"])
            kb = X.ease_back((lt - 1.2) / 0.4)
            if kb > 0:
                bw = 780 * kb
                pulse = 1 + 0.04 * math.sin(max(0, lt - 1.6) * 6)
                hgt = 130 * pulse
                d.rounded_rectangle([W / 2 - bw / 2, 1560 - hgt / 2, W / 2 + bw / 2, 1560 + hgt / 2], radius=65,
                                    fill=X.CORAL, outline=X.INK, width=7)
                if kb > 0.8:
                    X.text_c(d, W / 2, 1560, "FOLLOW FOR MORE", X.font("ExtraBold", 62), X.WHITE)
                X.text_c(d, W / 2, 1690, "@puzzledaily_123", X.font("Bold", 50), X.WHITE, 5)
        if kind == "end":
            tag(d)
    if top_h > 0:
        out.paste(top_graphics(kind if kind not in ("hook", "end") else "talk", lt, sc_len, accent).crop((0, SPLIT - top_h, W, SPLIT)), (0, 0))
        d = ImageDraw.Draw(out)
        d.rectangle([0, top_h - 4, W, top_h + 4], fill=X.YELLOW)  # divider
    return out


def music(total, sr=44100):
    import reels as B
    n = int(total * sr)
    m = np.zeros(n, np.float32)
    beat = 60 / 96
    chords = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    k = 0
    while k * beat < total:
        ch = chords[(k // 4) % 4]
        B.add(m, 0.10 * B.note(ch[k % 3] * 2, 0.6, "pluck"), k * beat)
        if k % 4 == 0:
            B.add(m, 0.16 * B.note(ch[0] / 2, beat * 3.5, "bass"), k * beat)
        k += 1
    f = int(0.8 * sr)
    m[-f:] *= np.linspace(1, 0, f)
    return m, sr


def main(src, dst, face_y=None):
    w, h, total = probe(src)
    tt = os.environ.get("SCENE_TIMES")  # optional manual cut points, e.g. "4.5,11.2,16.6,26.5,34.25"
    if tt:
        c = [0.0] + [float(x) for x in tt.split(",")] + [total]
        times = [(c[i], c[i + 1]) for i in range(len(SCENES))]
    else:
        times = sentence_times(src, len(SCENES), total)
    print("scenes:", [(k, round(a, 1), round(b, 1)) for k, (a, b) in zip(SCENES, times)])
    face_y = face_y or int(os.environ.get("FACE_Y", H * 0.36))
    import soundfile as sf
    m, sr = music(total)
    bg = os.path.splitext(dst)[0] + "_music.wav"
    sf.write(bg, m, sr)
    enc = subprocess.Popen([FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", src, "-i", bg, "-filter_complex",
                            "[2:a]volume=0.55[m];[1:a][m]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[mm];"
                            "[1:a][mm]amix=inputs=2:duration=first:normalize=0[a]",
                            "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", dst],
                           stdin=subprocess.PIPE)
    for i, fr in enumerate(presenter_frames(src, w, h)):
        t = i / FPS
        img = compose(fr, t, times, total, face_y)
        enc.stdin.write(img.tobytes())
        if i % int(FPS * 2.5) == 0:
            img.save(os.path.splitext(dst)[0] + f"_f{i:04d}.jpg", quality=80)
    enc.stdin.close()
    enc.wait()
    os.remove(bg)
    print("done:", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
