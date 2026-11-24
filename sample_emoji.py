"""Build one complete sample emoji puzzle: 15 s reel (voice, music, countdown timer,
A/B/C panel), cover image, caption and voice script.

Runs in the Build reels workflow and publishes to <Pages>/samples/. It does not touch
puzzles.json or the daily posting.

Env: SAMPLE_OUT (output folder), EMOJI_FONT (path to NotoColorEmoji.ttf), plus the
FONT_DIR / KOKORO_DIR / REELS_TMP used by reels.py.
"""
import os, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
import reels as B          # voice, music, sound effects
import reels2 as V         # A/B/C panel
R = B.R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("SAMPLE_OUT", os.path.join(HERE, "out", "samples"))
EMOJI_FONT = os.environ.get("EMOJI_FONT", os.path.join(HERE, "fonts", "NotoColorEmoji.ttf"))
RW, RH, FPS, SR = B.RW, B.RH, B.FPS, B.SR
TOTAL = 15.0
ACC = R.ACCENTS[3]  # purple

PUZZLE = {
    "type": "Emoji Puzzle",
    "emojis": ["\U0001F327", "\U0001F3F9"],          # cloud with rain + bow and arrow
    "caption_emojis": "🌧️ + 🏹 = ?",
    "choices": ["RAINDROP", "RAINBOW", "THUNDER"],
    "answer_letter": "B",
    "answer": "RAINBOW",
    "explanation": "Rain + bow = RAINBOW.",
}
VO_HOOK = "Emoji puzzle! Which word do these two emojis make? A, B, or C?"
VO_END = "Comment A, B, or C, and send this to a friend. Answer tomorrow!"
CAPTION = (
    "Emoji puzzle 🧩 Guess the word from two emojis in 10 seconds!\n\n"
    "🌧️ + 🏹 = ?\n\n"
    "👉 A) RAINDROP\n👉 B) RAINBOW\n👉 C) THUNDER\n\n"
    "💬 Comment A, B or C. We reveal it tomorrow!\n"
    "📤 Send this to the friend who always guesses first.\n"
    "🔔 Follow @puzzledaily_123 for a new brain teaser every day.\n\n"
)
HASHTAGS = ["#puzzletwister", "#emojipuzzle", "#guesstheword", "#emojiquiz", "#brainteaser"]

# ---------------- emoji drawing ----------------
_ef = None
def emoji_img(ch, size):
    """Noto Color Emoji is a bitmap font that only renders at 109 px: draw, crop, scale."""
    global _ef
    if _ef is None:
        _ef = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 20), ch, font=_ef, embedded_color=True)
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    s = size / max(im.size)
    lanczos = getattr(Image, "Resampling", Image).LANCZOS
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), lanczos)


def emoji_row(img, cy, size, ink):
    """[emoji] + [emoji] = [?] centred on cy."""
    d = ImageDraw.Draw(img)
    sym = R.font(R.BOLD, int(size * 0.55))
    parts = [("e", PUZZLE["emojis"][0]), ("s", "+"), ("e", PUZZLE["emojis"][1]), ("s", "="), ("q", "?")]
    gap, symw = int(size * 0.14), int(size * 0.42)
    widths = [size if k != "s" else symw for k, _ in parts]
    x = (RW - (sum(widths) + gap * (len(parts) - 1))) / 2
    for (kind, val), w in zip(parts, widths):
        cx = x + w / 2
        if kind == "e":
            e = emoji_img(val, size)
            img.paste(e, (int(cx - e.width / 2), int(cy - e.height / 2)), e)
        elif kind == "s":
            R.ctext(d, cx, cy, val, sym, ink)
        else:
            d.rounded_rectangle([cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2], radius=int(size * 0.18), fill=ACC)
            R.ctext(d, cx, cy + 4, "?", R.font(R.BOLD, int(size * 0.62)), R.WHITE)
        x += w + gap


# ---------------- frames ----------------
def card(img):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([50, 330, RW - 50, 1150], radius=40, fill=R.BG)
    d.rounded_rectangle([100, 380, 400, 440], radius=30, fill=R.INK)
    R.ctext(d, 250, 410, "EMOJI PUZZLE", R.font(R.BOLD, 30), R.WHITE)
    emoji_row(img, 720, 210, R.INK)
    R.ctext(d, RW / 2, 950, "Two emojis make one word.", R.font(R.SEMI, 44), R.INK)
    R.ctext(d, RW / 2, 1015, "Which one is it?", R.font(R.SEMI, 44), R.MUTED)


def frame(top_fn, bottom_text, timer=None):
    img = Image.new("RGB", (RW, RH), R.INK)
    card(img)
    V.draw_choices(img, PUZZLE, ACC)
    d = ImageDraw.Draw(img)
    top_fn(d)
    if timer is not None:  # (left, total): shrinking bar between the header and the card
        left, total = timer
        d.rounded_rectangle([50, 298, RW - 50, 318], radius=10, fill=(60, 66, 96))
        d.rounded_rectangle([50, 298, 50 + (RW - 100) * left / total, 318], radius=10, fill=ACC)
    R.ctext(d, RW / 2, 1790, bottom_text, R.font(R.BOLD, 38), R.WHITE)
    return img


def top_hook(d):
    R.ctext(d, RW / 2, 110, "EMOJI PUZZLE", R.font(R.BOLD, 56), R.WHITE)
    R.ctext(d, RW / 2, 205, "GUESS THE WORD", R.font(R.BOLD, 92), ACC)


def top_count(n):
    def f(d):
        d.text((90, 105), "THINK", font=R.font(R.BOLD, 70), fill=R.WHITE)
        d.text((90, 175), "FAST!", font=R.font(R.BOLD, 70), fill=ACC)
        d.ellipse([RW - 300, 40, RW - 90, 250], fill=ACC, outline=R.WHITE, width=8)
        R.ctext(d, RW - 195, 150, str(n), R.font(R.BOLD, 130), R.WHITE)
    return f


def top_end(d):
    R.ctext(d, RW / 2, 105, "ANSWER", R.font(R.BOLD, 70), R.WHITE)
    R.ctext(d, RW / 2, 200, "TOMORROW!", R.font(R.BOLD, 96), ACC)


def cover():
    CW, CH = 1080, 1920
    img = Image.new("RGB", (CW, CH), R.INK)
    d = ImageDraw.Draw(img)
    soft = tuple(int(c * 0.45 + i * 0.55) for c, i in zip(ACC, R.INK))
    d.ellipse([CW - 380, -160, CW + 220, 440], fill=soft)
    d.ellipse([-260, CH - 420, 340, CH + 180], fill=soft)
    R.ctext(d, CW / 2, 300, "PUZZLE TWISTER", R.font(R.BOLD, 44), R.WHITE)
    R.ctext(d, CW / 2, 420, "EMOJI PUZZLE", R.font(R.BOLD, 120), ACC)
    R.ctext(d, CW / 2, 545, "GUESS THE WORD", R.font(R.BOLD, 52), R.WHITE)
    d.rounded_rectangle([80, 640, CW - 80, 1330], radius=40, fill=R.BG, outline=ACC, width=10)
    emoji_row(img, 985, 175, R.INK)
    R.ctext(d, CW / 2, 1460, "CAN YOU GET IT IN 10s?", R.font(R.BOLD, 60), R.WHITE)
    return img


# ---------------- audio + video ----------------
def plan():
    """1.5 s title, then a full 10 s countdown (the hook voice plays over its start),
    then the end card for as long as the closing line needs."""
    v_hook, v_end = B.tts(VO_HOOK, B.SPEED), B.tts(VO_END, B.SPEED)
    A, N = 1.5, 10
    C = max(3.5, len(v_end) / SR + 0.7)
    return dict(v_hook=v_hook, v_end=v_end, A=A, N=N, C=C, total=A + N + C)


def mix(pl, path):
    n = int(pl["total"] * SR)
    m = B.music(3)
    m = (np.pad(m, (0, max(0, n - len(m))))[:n]) / np.max(np.abs(m)) * 0.30
    vo = np.zeros(n, np.float32)
    sfx = np.zeros(n, np.float32)
    B.add(vo, pl["v_hook"] / np.max(np.abs(pl["v_hook"])), 0.25)
    for i in range(pl["N"]):
        left = pl["N"] - i
        B.add(sfx, (0.45 if left <= 3 else 0.22) * B.tick(), pl["A"] + i)
    t_end = pl["A"] + pl["N"]
    B.add(sfx, 0.22 * (B.note(880, 1.0, "bell") + B.note(1320, 1.0, "bell")), t_end)
    B.add(vo, pl["v_end"] / np.max(np.abs(pl["v_end"])), t_end + 0.25)
    env = np.convolve(np.abs(vo), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    out = m * (1 - 0.7 * np.clip(env / 0.02, 0, 1)) + vo * 0.85 + sfx
    f = int(0.6 * SR); out[-f:] *= np.linspace(1, 0, f)
    out = out / max(1.0, np.max(np.abs(out)) / 0.95)
    sf.write(path, out, SR)


def encode(segs, audio, path, total):
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p, _ in segs:
        cmd += ["-framerate", str(FPS), "-i", p]
    ai = len(segs)
    cmd += ["-i", audio, "-f", "lavfi", "-i", "color=c=0x%02x%02x%02x:s=%dx14:r=%d" % (*ACC, RW, FPS)]
    fc = [f"[{i}]format=yuv420p,loop=-1:1,trim=duration={d:.3f},setpts=PTS-STARTPTS,fps=30,settb=1/30[v{i}]"
          for i, (_, d) in enumerate(segs)]
    fc.append("".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0,fps=30,settb=1/30[vid]")
    fc.append(f"[vid][{ai + 1}]overlay=x='-w+w*t/{total:.3f}':y=0:shortest=1,format=yuv420p[outv]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", f"{ai}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}", "-movflags", "+faststart", path]
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(B.TMP, "sample")
    os.makedirs(tmp, exist_ok=True)
    pl = plan()
    segs = []
    p = os.path.join(OUT, "frame_hook.png"); frame(top_hook, "COMMENT A, B OR C  ·  @PUZZLEDAILY_123").save(p)
    segs.append((p, pl["A"]))
    for n in range(pl["N"], 0, -1):
        p = os.path.join(tmp, f"count_{n:02d}.png")
        frame(top_count(n), "COMMENT A, B OR C  ·  @PUZZLEDAILY_123", timer=(n, pl["N"])).save(p)
        segs.append((p, 1.0))
    mid = pl["N"] // 2
    Image.open(os.path.join(tmp, f"count_{mid:02d}.png")).save(os.path.join(OUT, "frame_countdown.png"))
    p = os.path.join(OUT, "frame_end.png"); frame(top_end, "SEND THIS TO A FRIEND WHO'S FAST").save(p)
    segs.append((p, pl["C"]))
    audio = os.path.join(tmp, "mix.wav")
    mix(pl, audio)
    encode(segs, audio, os.path.join(OUT, "emoji_sample_reel.mp4"), pl["total"])
    cover().save(os.path.join(OUT, "emoji_sample_cover.jpg"), "JPEG", quality=90)
    with open(os.path.join(OUT, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(CAPTION + " ".join(HASHTAGS) + "\n")
    with open(os.path.join(OUT, "voice.txt"), "w", encoding="utf-8") as f:
        f.write(f"0.3s  {VO_HOOK}\n{pl['A'] + pl['N'] + 0.3:.1f}s  {VO_END}\n"
                f"Timing: title {pl['A']:.1f}s, countdown {pl['N']}s, end card {pl['C']:.1f}s, "
                f"total {pl['total']:.1f}s\n")
    print(f"Sample built: title {pl['A']:.1f}s, countdown {pl['N']}s, end {pl['C']:.1f}s -> {OUT}")


if __name__ == "__main__":
    main()
