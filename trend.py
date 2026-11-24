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
          "riddle": R.ACCENTS[4], "stroop": R.ACCENTS[4], "first_word": R.ACCENTS[3],
          "spot_diff": R.ACCENTS[0], "count_emoji": R.ACCENTS[2], "memory": R.ACCENTS[1]}
TOP = {"emoji_word": ("EMOJI PUZZLE", "GUESS THE WORD"), "odd_grid": ("FIND THE ODD ONE", "IN 10 SECONDS"),
       "math": ("QUICK MATHS", "CAN YOU SOLVE IT?"), "riddle": ("RIDDLE", "THINK FIRST!"),
       "stroop": ("BRAIN TEST", "SAY THE COLOUR!"), "first_word": ("WHAT'S THE FIRST", "WORD YOU SEE?"),
       "spot_diff": ("SPOT THE DIFFERENCE", "HOW MANY?"), "count_emoji": ("COUNT CHALLENGE", "HOW MANY?"),
       "memory": ("MEMORY TEST", "LOOK CLOSELY!")}
VO_END_OPTIONS = "Comment A, B, or C, and send this to a friend. Answer tomorrow!"
INK = {"RED": (220, 50, 50), "BLUE": (40, 100, 220), "GREEN": (30, 150, 70),
       "YELLOW": (225, 170, 0), "PURPLE": (130, 60, 200), "ORANGE": (240, 120, 20)}


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
    if k == "stroop":
        return ("Brain test! Say the colour of each word out loud, not the word itself. Go!",
                "How long did it take you? Comment your time, and challenge a friend!")
    if k == "first_word":
        return ("What's the first word you see? Look closely!",
                "Comment the first word you saw, and send this to a friend!")
    if k == "spot_diff":
        return ("Spot the difference! How many changes can you find between the two grids?",
                "Comment how many you found, and send this to a friend. Answer tomorrow!")
    if k == "count_emoji":
        return (f"Count challenge! How many {p['target']} can you count? Careful, some look alike!",
                "Comment your number, and send this to a friend. Answer tomorrow!")
    if k == "memory":
        return ("Memory test! Look at the grid for five seconds and remember it.", VO_END_OPTIONS)
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


def draw_stroop(img, p, acc):
    d = ImageDraw.Draw(img)
    f = R.font(R.BOLD, 64)
    for i, (word, ink) in enumerate(p["words"]):
        r, c = divmod(i, 3)
        R.ctext(d, 230 + c * 310, 530 + r * 130, word, f, INK[ink])
    R.ctext(d, RW / 2, 1085, "Say each COLOUR out loud.", R.font(R.SEMI, 42), R.MUTED)


def draw_first_word(img, p, acc):
    d = ImageDraw.Draw(img)
    f = R.font(R.BOLD, 54)
    cw, ch, x0, y0 = 98, 72, RW / 2 - 98 * 4, 505
    for r, row in enumerate(p["grid"]):
        for c, letter in enumerate(row):
            R.ctext(d, x0 + c * cw, y0 + r * ch, letter, f, R.INK)


def emoji_block(img, items, cols, cx, cy, cell, size):
    rows = math.ceil(len(items) / cols)
    x0, y0 = cx - cell * cols / 2, cy - cell * rows / 2
    for i, e in enumerate(items):
        r, c = divmod(i, cols)
        paste_emoji(img, e, x0 + cell * (c + 0.5), y0 + cell * (r + 0.5), size)


def draw_spot_diff(img, p, acc):
    d = ImageDraw.Draw(img)
    for label, items, cx in (("A", p["left"], RW / 2 - 225), ("B", p["right"], RW / 2 + 225)):
        d.rounded_rectangle([cx - 205, 515, cx + 205, 925], radius=24, fill=R.WHITE, outline=(225, 214, 200), width=4)
        R.ctext(d, cx, 485, label, R.font(R.BOLD, 40), acc)
        emoji_block(img, items, 4, cx, 720, 98, 78)
    R.ctext(d, RW / 2, 1010, "How many differences?", R.font(R.SEMI, 46), R.MUTED)


def draw_count(img, p, acc):
    emoji_block(img, p["cells"], 7, RW / 2, 790, 118, 92)


def draw_memory(img, p, acc):
    d = ImageDraw.Draw(img)
    cell, cx, cy = 175, RW / 2, 735   # grid spans y 472..998, clear of the label pill
    if p.get("_phase") == "ask":
        x0, y0 = cx - cell * 1.5, cy - cell * 1.5
        for i in range(9):
            r, c = divmod(i, 3)
            x, y = x0 + c * cell + 10, y0 + r * cell + 10
            d.rounded_rectangle([x, y, x + cell - 20, y + cell - 20], radius=24, fill=acc)
            R.ctext(d, x + (cell - 20) / 2, y + (cell - 20) / 2, "?", R.font(R.BOLD, 84), R.WHITE)
        R.ctext(d, RW / 2, 1075, p["question"], R.font(R.BOLD, 44), R.INK)
    else:
        emoji_block(img, p["grid"], 3, cx, cy, cell, 138)
        R.ctext(d, RW / 2, 1075, "Remember where everything is!", R.font(R.SEMI, 44), R.MUTED)


DRAW = {"emoji_word": draw_emoji_word, "odd_grid": draw_grid, "math": draw_math, "riddle": draw_riddle,
        "stroop": draw_stroop, "first_word": draw_first_word, "spot_diff": draw_spot_diff,
        "count_emoji": draw_count, "memory": draw_memory}


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
    k, icon = p["kind"], "👇"
    if k == "emoji_word":
        l1, l2 = "TYPE THE WORD", "IN THE COMMENTS"
    elif k == "odd_grid":
        l1, l2 = "COMMENT ROW + COLUMN", "like  2, 5"
    elif k == "stroop":
        l1, l2, icon = "SAY THE COLOUR, NOT THE WORD", "Comment your time", "⏱"
    elif k == "first_word":
        l1, l2 = "COMMENT THE FIRST WORD", "you spotted"
    elif k == "spot_diff":
        l1, l2, icon = "HOW MANY DIFFERENCES?", "Comment the number", "🔍"
    elif k == "count_emoji":
        l1, l2, icon = "HOW MANY CAN YOU COUNT?", "Comment the number", p["target_emoji"]
    else:  # memory, first phase
        l1, l2, icon = "MEMORISE THE GRID", "It disappears at 0!", "🧠"
    size = 62
    while d.textlength(l1, font=R.font(R.BOLD, size)) > RW - 140:
        size -= 2
    R.ctext(d, RW / 2, 1290, l1, R.font(R.BOLD, size), acc)
    R.ctext(d, RW / 2, 1385, l2, R.font(R.BOLD, 52), R.WHITE)
    paste_emoji(img, icon, RW / 2, 1550, 140)


def panel_teaser(img, p, acc):
    d = ImageDraw.Draw(img)
    panel_box(d, acc)
    paste_emoji(img, "⏳", RW / 2, 1330, 120)
    R.ctext(d, RW / 2, 1480, "OPTIONS APPEAR AT 3", R.font(R.BOLD, 58), acc)
    R.ctext(d, RW / 2, 1570, "Solve it first!", R.font(R.SEMI, 46), R.WHITE)


def panel_choices(img, p, acc):
    if p["kind"] != "memory":
        V.draw_choices(img, p, acc)
        return
    # memory options are emojis, which the text font can't draw
    d = ImageDraw.Draw(img)
    panel_box(d, acc)
    R.ctext(d, RW / 2, 1258, "COMMENT A, B OR C", R.font(R.BOLD, 46), acc)
    for i, (letter, e) in enumerate(zip("ABC", p["choices"])):
        cx = RW / 2 + (i - 1) * 300
        d.ellipse([cx - 42, 1330, cx + 42, 1414], fill=acc)
        R.ctext(d, cx, 1374, letter, R.font(R.BOLD, 48), R.WHITE)
        paste_emoji(img, e, cx, 1545, 150)


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


def spoken_answer(p):
    """Yesterday's answer as the voice should say it (None when there isn't a short one)."""
    k = p["kind"]
    if k == "emoji_word":
        return p["answer"].capitalize()
    if k == "odd_grid":
        return f"row {p['odd_row']}, column {p['odd_col']}"
    if k == "spot_diff":
        return f"{p['diffs']} differences"
    if k == "count_emoji":
        return f"{p['count']} {p['target']}"
    if k == "memory":
        return p["answer_letter"]
    if p.get("choices"):
        text = p["choices"]["ABC".index(p["answer_letter"])].replace("₹", "") + (" rupees" if "₹" in str(p["choices"]) else "")
        return f"{p['answer_letter']}, {text}"
    return None


def top_title(p, acc, prev):
    l1 = TOP[p["kind"]][0]
    def f(d):
        R.ctext(d, RW / 2, 80, "WELCOME TO PUZZLE TWISTER", R.font(R.BOLD, 46), R.WHITE)
        size = 80
        while d.textlength(l1, font=R.font(R.BOLD, size)) > RW - 100:
            size -= 4
        R.ctext(d, RW / 2, 178, l1, R.font(R.BOLD, size), acc)
        if prev:
            text = f"Yesterday's answer: {T.short_answer(prev)}"
            size = 32
            while size > 22 and d.textlength(text, font=R.font(R.SEMI, size)) > RW - 80:
                size -= 2
            if d.textlength(text, font=R.font(R.SEMI, size)) > RW - 80:
                text = "Yesterday's answer is in the caption"
            R.ctext(d, RW / 2, 262, text, R.font(R.SEMI, size), R.WHITE)
    return f


def top_count(n, acc):
    def f(d):
        d.text((90, 105), "THINK", font=R.font(R.BOLD, 70), fill=R.WHITE)
        d.text((90, 175), "FAST!", font=R.font(R.BOLD, 70), fill=acc)
        d.ellipse([RW - 300, 40, RW - 90, 250], fill=acc, outline=R.WHITE, width=8)
        R.ctext(d, RW - 195, 150, str(n), R.font(R.BOLD, 130), R.WHITE)
    return f


END_TOP = {"stroop": ("HOW FAST", "WERE YOU?"), "first_word": ("MEANINGS", "TOMORROW!")}


def top_end(acc, kind=None):
    l1, l2 = END_TOP.get(kind, ("ANSWER", "TOMORROW!"))
    def f(d):
        R.ctext(d, RW / 2, 105, l1, R.font(R.BOLD, 70), R.WHITE)
        R.ctext(d, RW / 2, 200, l2, R.font(R.BOLD, 96), acc)
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
    if p["kind"] == "memory":
        ask = "MEMORISE IT · THEN ANSWER"
    else:
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
    B.add(vo, pl["v_hook"] / np.max(np.abs(pl["v_hook"])), pl.get("hook_at", 0.25))
    for i in range(pl["N"]):
        left = pl["N"] - i
        B.add(sfx, (0.45 if left <= 3 else 0.2) * B.tick(), pl["A"] + i)
    t_end = pl["A"] + pl["N"]
    if pl["options_at"] is not None:
        B.add(sfx, 0.25 * B.note(990, 0.5, "bell"), pl["options_at"])
    B.add(sfx, 0.22 * (B.note(880, 1.0, "bell") + B.note(1320, 1.0, "bell")), t_end)
    B.add(vo, pl["v_end"] / np.max(np.abs(pl["v_end"])), t_end + 0.25)
    for clip, t in pl.get("extra", []):  # e.g. the memory test's question
        B.add(vo, clip / np.max(np.abs(clip)), t)
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
    prev = T.find(data, p["day"] - 1, p["slot"])
    said = spoken_answer(prev) if prev else None
    intro = "Welcome to Puzzle Twister!" + (f" Yesterday's answer was {said}." if said else "")
    v_intro, v_hook, v_end = B.tts(intro, B.SPEED), B.tts(hook, B.SPEED), B.tts(end, B.SPEED)
    A = max(1.5, len(v_intro) / SR + 0.5)               # welcome screen lasts as long as the intro
    N = max(10, math.ceil(len(v_hook) / SR + 0.6))       # long riddles get a longer countdown
    C = max(3.5, len(v_end) / SR + 0.7)
    opts = T.has_options(p)
    memory = p["kind"] == "memory"
    pl = dict(v_hook=v_hook, v_end=v_end, A=A, N=N, C=C, total=A + N + C, hook_at=A + 0.1,
              options_at=(A + N - 3) if opts else None, extra=[(v_intro, 0.25)])
    show, ask = dict(p, _phase="show"), dict(p, _phase="ask")
    if memory:
        # 5 s to memorise, then the grid is hidden and the question + emoji options appear
        N = pl["N"] = 10
        pl["total"] = A + N + C
        pl["options_at"] = A + 5
        pl["extra"].append((B.tts(p["question"] + " A, B, or C?", B.SPEED), A + 5.2))
    bottom = f"PUZZLE TWISTER  ·  #{p['id']}"
    segs = []
    title_panel = panel_comment if memory else (panel_teaser if opts else panel_comment)
    title = frame(show, acc, top_title(p, acc, prev), bottom, title_panel)
    fp = os.path.join(tmp, "title.png"); title.save(fp); segs.append((fp, A))
    for n in range(N, 0, -1):
        if memory:
            q, panel = (show, panel_comment) if n > 5 else (ask, panel_choices)
        else:
            q, panel = p, ((panel_choices if n <= 3 else panel_teaser) if opts else panel_comment)
        fp = os.path.join(tmp, f"count_{n:02d}.png")
        frame(q, acc, top_count(n, acc), bottom, panel, timer=(n, N)).save(fp)
        segs.append((fp, 1.0))
    end_panel = panel_choices if opts else panel_comment
    fp = os.path.join(tmp, "end.png")
    frame(ask if memory else p, acc, top_end(acc, p["kind"]), "SEND THIS TO A FRIEND", end_panel).save(fp)
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
        f.write(T.caption(data, p) + "\n\n--- voice ---\n"
                + f"0.3s  {intro}\n{A + 0.1:.1f}s  {hook}\n{A + N + 0.3:.1f}s  {end}\n")
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
