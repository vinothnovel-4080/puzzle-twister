"""Render the trend series (trends.json): one reel + cover + caption per post.

Styles: emoji_word and odd_grid (no options, "comment your answer"), and math
and riddle (A/B/C options appear when the countdown reaches 3).

Reel: 1.5 s title -> 10 s countdown with timer bar (hook voice over it) -> end card.
Env: TREND_OUT (output folder), EMOJI_FONT, plus FONT_DIR / KOKORO_DIR / REELS_TMP.
"""
import math, os, subprocess, sys
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
import reels as B
import reels2 as V
import trends_common as T
R = B.R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("TREND_OUT", os.path.join(HERE, "out", "trend"))
EMOJI_FONT = os.environ.get("EMOJI_FONT", os.path.join(HERE, "fonts", "NotoColorEmoji.ttf"))
RW, RH, FPS, SR = B.RW, B.RH, B.FPS, B.SR
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS

ACCENT = {"emoji_word": R.ACCENTS[3], "odd_grid": R.ACCENTS[2], "math": R.ACCENTS[1],
          "riddle": R.ACCENTS[4]}
TOP = {"emoji_word": ("EMOJI PUZZLE", "GUESS THE WORD"), "odd_grid": ("FIND THE ODD ONE", "IN 10 SECONDS"),
       "math": ("QUICK MATHS", "CAN YOU SOLVE IT?"), "riddle": ("RIDDLE", "THINK FIRST!")}
VO_END_OPTIONS = "Comment A, B, or C, and send this to a friend. Answer tomorrow!"


def vo_lines(p):
    k = p["kind"]
    if k == "emoji_word":
        return ("Emoji puzzle! Which word do these emojis make? Type it in the comments!",
                "Comment the word, and send this to a friend. Answer tomorrow!")
    if k == "odd_grid":
        return ("Find the odd one out! You have ten seconds.",
                "Comment the row and column, and send this to a friend. Answer tomorrow!")
    if k == "math":
        return ("Quick maths! What's the answer? Options appear at three.", VO_END_OPTIONS)
    return (p["question"].replace("₹", " rupees ") + " Options appear at three.", VO_END_OPTIONS)


# ---------------- emoji ----------------
_ef, _ecache = None, {}
def emoji_img(ch, size):
    global _ef
    key = (ch, size)
    if key in _ecache:
        return _ecache[key]
    if _ef is None:
        _ef = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 20), ch, font=_ef, embedded_color=True)
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    s = size / max(im.size)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), LANCZOS)
    _ecache[key] = im
    return im


def paste_emoji(img, ch, cx, cy, size):
    e = emoji_img(ch, size)
    img.paste(e, (int(cx - e.width / 2), int(cy - e.height / 2)), e)


# ---------------- puzzle drawings (inside the card, y 330..1150) ----------------
def draw_emoji_word(img, p, acc, cy=720, size=200):
    d = ImageDraw.Draw(img)
    parts = []
    for i, e in enumerate(p["emojis"]):
        if i:
            parts.append(("s", "+"))
        parts.append(("e", e))
    parts += [("s", "="), ("q", "?")]
    gap, symw = int(size * 0.14), int(size * 0.42)
    widths = [symw if k == "s" else size for k, _ in parts]
    total = sum(widths) + gap * (len(parts) - 1)
    if total > 900:  # shrink for 3+ emojis
        size = int(size * 900 / total)
        return draw_emoji_word(img, p, acc, cy, size)
    x = (RW - total) / 2
    for (k, v), w in zip(parts, widths):
        cx = x + w / 2
        if k == "e":
            paste_emoji(img, v, cx, cy, size)
        elif k == "s":
            R.ctext(d, cx, cy, v, R.font(R.BOLD, int(size * 0.55)), R.INK)
        else:
            d.rounded_rectangle([cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2],
                                radius=int(size * 0.18), fill=acc)
            R.ctext(d, cx, cy + 4, "?", R.font(R.BOLD, int(size * 0.62)), R.WHITE)
        x += w + gap
    R.ctext(d, RW / 2, cy + 230, "Which word do they make?", R.font(R.SEMI, 44), R.MUTED)


def draw_grid(img, p, acc):
    d = ImageDraw.Draw(img)
    rows, cols = p["rows"], p["cols"]
    top, bottom = 470, 1120
    cell = min((bottom - top) / (rows + 0.6), 880 / (cols + 0.6))
    gx = (RW - cell * (cols + 0.6)) / 2 + cell * 0.6
    gy = top + cell * 0.6
    lab = R.font(R.BOLD, int(cell * 0.32))
    for c in range(cols):
        R.ctext(d, gx + cell * (c + 0.5), gy - cell * 0.32, str(c + 1), lab, R.MUTED)
    for r in range(rows):
        R.ctext(d, gx - cell * 0.32, gy + cell * (r + 0.5), str(r + 1), lab, R.MUTED)
    glyph = R.font(R.BOLD, int(cell * 0.72))
    for r in range(rows):
        for c in range(cols):
            ch = p["odd"] if (r + 1, c + 1) == (p["odd_row"], p["odd_col"]) else p["base"]
            cx, cy = gx + cell * (c + 0.5), gy + cell * (r + 0.5)
            if p.get("emoji"):
                paste_emoji(img, ch, cx, cy, int(cell * 0.8))
            else:
                R.ctext(d, cx, cy, ch, glyph, R.INK)


def draw_math(img, p, acc):
    d = ImageDraw.Draw(img)
    size = 130
    while size > 60 and d.textlength(p["expr"], font=R.font(R.BOLD, size)) > 880:
        size -= 4
    R.ctext(d, RW / 2, 700, p["expr"], R.font(R.BOLD, size), R.INK)
    R.ctext(d, RW / 2, 930, "Most people get this wrong.", R.font(R.SEMI, 44), R.MUTED)


def draw_riddle(img, p, acc):
    d = ImageDraw.Draw(img)
    f = R.font(R.SEMI, 54)
    lines = R.wrap(d, p["question"], f, 820)
    lh = int(54 * 1.3)
    y = 760 - len(lines) * lh / 2
    for line in lines:
        R.ctext(d, RW / 2, y + lh / 2, line, f, R.INK)
        y += lh


DRAW = {"emoji_word": draw_emoji_word, "odd_grid": draw_grid, "math": draw_math, "riddle": draw_riddle}


def card(img, p, acc):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([50, 330, RW - 50, 1150], radius=40, fill=R.BG)
    label = f"#{p['id']}  {T.LABEL[p['kind']].upper()}"
    lw = d.textlength(label, font=R.font(R.BOLD, 30)) + 60
    d.rounded_rectangle([100, 380, 100 + lw, 440], radius=30, fill=R.INK)
    R.ctext(d, 100 + lw / 2, 410, label, R.font(R.BOLD, 30), R.WHITE)
    DRAW[p["kind"]](img, p, acc)


# ---------------- bottom panels ----------------
def panel_box(d, acc):
    d.rounded_rectangle([36, 1196, RW - 36, 1700], radius=36, fill=R.INK, outline=acc, width=6)


def panel_comment(img, p, acc):
    d = ImageDraw.Draw(img)
    panel_box(d, acc)
    if p["kind"] == "emoji_word":
        l1, l2 = "TYPE THE WORD", "IN THE COMMENTS"
    else:
        l1, l2 = "COMMENT ROW + COLUMN", "like  2, 5"
    R.ctext(d, RW / 2, 1290, l1, R.font(R.BOLD, 62), acc)
    R.ctext(d, RW / 2, 1385, l2, R.font(R.BOLD, 52), R.WHITE)
    paste_emoji(img, "👇", RW / 2, 1550, 140)


def panel_teaser(img, p, acc):
    d = ImageDraw.Draw(img)
    panel_box(d, acc)
    paste_emoji(img, "⏳", RW / 2, 1330, 120)
    R.ctext(d, RW / 2, 1480, "OPTIONS APPEAR AT 3", R.font(R.BOLD, 58), acc)
    R.ctext(d, RW / 2, 1570, "Solve it first!", R.font(R.SEMI, 46), R.WHITE)


def panel_choices(img, p, acc):
    V.draw_choices(img, p, acc)


# ---------------- frames ----------------
def frame(p, acc, top_fn, bottom, panel, timer=None):
    img = Image.new("RGB", (RW, RH), R.INK)
    card(img, p, acc)
    panel(img, p, acc)
    d = ImageDraw.Draw(img)
    top_fn(d)
    if timer is not None:
        left, total = timer
        d.rounded_rectangle([50, 298, RW - 50, 318], radius=10, fill=(60, 66, 96))
        d.rounded_rectangle([50, 298, 50 + (RW - 100) * left / total, 318], radius=10, fill=acc)
    R.ctext(d, RW / 2, 1790, bottom, R.font(R.BOLD, 38), R.WHITE)
    return img


def top_title(p, acc, prev):
    l1, l2 = TOP[p["kind"]]
    def f(d):
        R.ctext(d, RW / 2, 95, l1, R.font(R.BOLD, 56), R.WHITE)
        R.ctext(d, RW / 2, 185, l2, R.font(R.BOLD, 84), acc)
        if prev:
            R.ctext(d, RW / 2, 262, f"Yesterday's answer: {T.answer_text(prev)}", R.font(R.SEMI, 32), R.WHITE)
    return f


def top_count(n, acc):
    def f(d):
        d.text((90, 105), "THINK", font=R.font(R.BOLD, 70), fill=R.WHITE)
        d.text((90, 175), "FAST!", font=R.font(R.BOLD, 70), fill=acc)
        d.ellipse([RW - 300, 40, RW - 90, 250], fill=acc, outline=R.WHITE, width=8)
        R.ctext(d, RW - 195, 150, str(n), R.font(R.BOLD, 130), R.WHITE)
    return f


def top_end(acc):
    def f(d):
        R.ctext(d, RW / 2, 105, "ANSWER", R.font(R.BOLD, 70), R.WHITE)
        R.ctext(d, RW / 2, 200, "TOMORROW!", R.font(R.BOLD, 96), acc)
    return f


def cover(p, acc, title_frame):
    CW, CH = 1080, 1920
    img = Image.new("RGB", (CW, CH), R.INK)
    d = ImageDraw.Draw(img)
    soft = tuple(int(c * 0.45 + i * 0.55) for c, i in zip(acc, R.INK))
    d.ellipse([CW - 380, -160, CW + 220, 440], fill=soft)
    d.ellipse([-260, CH - 420, 340, CH + 180], fill=soft)
    l1, l2 = TOP[p["kind"]]
    R.ctext(d, CW / 2, 300, f"PUZZLE TWISTER  ·  #{p['id']}", R.font(R.BOLD, 44), R.WHITE)
    size = 120
    while d.textlength(l1, font=R.font(R.BOLD, size)) > 960:
        size -= 6
    R.ctext(d, CW / 2, 420, l1, R.font(R.BOLD, size), acc)
    R.ctext(d, CW / 2, 545, l2, R.font(R.BOLD, 52), R.WHITE)
    crop = title_frame.crop((50, 330, RW - 50, 1150))
    s = 0.86
    crop = crop.resize((int(crop.width * s), int(crop.height * s)), LANCZOS)
    x, y = (CW - crop.width) // 2, 640
    d.rounded_rectangle([x - 10, y - 10, x + crop.width + 10, y + crop.height + 10], radius=40, fill=acc)
    img.paste(crop, (x, y))
    ask = "OPTIONS AT 3 · COMMENT A, B, C" if T.has_options(p) else "COMMENT YOUR ANSWER"
    R.ctext(d, CW / 2, y + crop.height + 85, ask, R.font(R.BOLD, 50), R.WHITE)
    return img


# ---------------- audio + video ----------------
def mix(pl, path, seed):
    n = int(pl["total"] * SR)
    m = B.music(seed)
    m = np.pad(m, (0, max(0, n - len(m))))[:n] / np.max(np.abs(m)) * 0.30
    vo = np.zeros(n, np.float32)
    sfx = np.zeros(n, np.float32)
    B.add(vo, pl["v_hook"] / np.max(np.abs(pl["v_hook"])), 0.25)
    for i in range(pl["N"]):
        left = pl["N"] - i
        B.add(sfx, (0.45 if left <= 3 else 0.2) * B.tick(), pl["A"] + i)
    t_end = pl["A"] + pl["N"]
    if pl["options_at"] is not None:
        B.add(sfx, 0.25 * B.note(990, 0.5, "bell"), pl["options_at"])
    B.add(sfx, 0.22 * (B.note(880, 1.0, "bell") + B.note(1320, 1.0, "bell")), t_end)
    B.add(vo, pl["v_end"] / np.max(np.abs(pl["v_end"])), t_end + 0.25)
    env = np.convolve(np.abs(vo), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    out = m * (1 - 0.7 * np.clip(env / 0.02, 0, 1)) + vo * 0.85 + sfx
    f = int(0.6 * SR); out[-f:] *= np.linspace(1, 0, f)
    out = out / max(1.0, np.max(np.abs(out)) / 0.95)
    sf.write(path, out, SR)


def encode(segs, audio, path, acc, total):
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for fp, _ in segs:
        cmd += ["-framerate", str(FPS), "-i", fp]
    ai = len(segs)
    cmd += ["-i", audio, "-f", "lavfi", "-i", "color=c=0x%02x%02x%02x:s=%dx14:r=%d" % (*acc, RW, FPS)]
    fc = [f"[{i}]format=yuv420p,loop=-1:1,trim=duration={d:.3f},setpts=PTS-STARTPTS,fps=30,settb=1/30[v{i}]"
          for i, (_, d) in enumerate(segs)]
    fc.append("".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0,fps=30,settb=1/30[vid]")
    fc.append(f"[vid][{ai + 1}]overlay=x='-w+w*t/{total:.3f}':y=0:shortest=1,format=yuv420p[outv]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", f"{ai}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}", "-movflags", "+faststart", path]
    subprocess.run(cmd, check=True)


def build(data, p):
    acc = ACCENT[p["kind"]]
    stem = T.file_stem(p)
    tmp = os.path.join(B.TMP, stem)
    os.makedirs(tmp, exist_ok=True)
    hook, end = vo_lines(p)
    v_hook, v_end = B.tts(hook, B.SPEED), B.tts(end, B.SPEED)
    A = 1.5
    N = max(10, math.ceil(len(v_hook) / SR + 0.6 - A))   # long riddles get a longer countdown
    C = max(3.5, len(v_end) / SR + 0.7)
    opts = T.has_options(p)
    pl = dict(v_hook=v_hook, v_end=v_end, A=A, N=N, C=C, total=A + N + C,
              options_at=(A + N - 3) if opts else None)
    prev = T.find(data, p["day"] - 1, p["slot"])
    bottom = f"PUZZLE TWISTER  ·  #{p['id']}"
    segs = []
    title_panel = panel_teaser if opts else panel_comment
    title = frame(p, acc, top_title(p, acc, prev), bottom, title_panel)
    fp = os.path.join(tmp, "title.png"); title.save(fp); segs.append((fp, A))
    for n in range(N, 0, -1):
        panel = (panel_choices if n <= 3 else panel_teaser) if opts else panel_comment
        fp = os.path.join(tmp, f"count_{n:02d}.png")
        frame(p, acc, top_count(n, acc), bottom, panel, timer=(n, N)).save(fp)
        segs.append((fp, 1.0))
    end_panel = panel_choices if opts else panel_comment
    fp = os.path.join(tmp, "end.png")
    frame(p, acc, top_end(acc), "SEND THIS TO A FRIEND", end_panel).save(fp)
    segs.append((fp, C))
    audio = os.path.join(tmp, "mix.wav")
    mix(pl, audio, p["id"])
    encode(segs, audio, os.path.join(OUT, stem + ".mp4"), acc, pl["total"])
    cover(p, acc, title).save(os.path.join(OUT, stem + "_cover.jpg"), "JPEG", quality=90)
    # previews: the frame people see most, and (for options) the frame with options shown
    Image.open(os.path.join(tmp, f"count_{N - 2:02d}.png")).save(os.path.join(OUT, stem + "_frame.png"))
    if opts:
        Image.open(os.path.join(tmp, "count_02.png")).save(os.path.join(OUT, stem + "_options.png"))
    with open(os.path.join(OUT, stem + ".txt"), "w", encoding="utf-8") as f:
        f.write(T.caption(data, p) + "\n\n--- voice ---\n" + f"0.3s  {hook}\n{A + N + 0.3:.1f}s  {end}\n")
    print(f"#{p['id']} {stem}: {p['kind']}, countdown {N}s, total {pl['total']:.1f}s")


def main():
    data = T.load()
    os.makedirs(OUT, exist_ok=True)
    only = {int(a) for a in sys.argv[1:]}
    # Posts already published don't need their files any more; build yesterday onwards.
    first = -10**6 if os.environ.get("TREND_BUILD_ALL") else T.today_day(data) - 1
    for p in data["posts"]:
        if (only and p["id"] in only) or (not only and p["day"] >= first):
            build(data, p)


if __name__ == "__main__":
    main()
