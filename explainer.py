"""Brain Bites: short explainer reels with a presenter (an illustrated woman, drawn in code).

SAMPLE ONLY: not part of the daily posting pipeline (nothing schedules or posts this).
Layout: the presenter stands at the bottom of the frame like a TV explainer host, with
lip sync, blinking and hand gestures; the facts, charts and steps animate above her.

Usage: python explainer.py [--stills]   -> out/explainer/brain_bites_01.mp4 (+ cover, caption)
       --stills only renders preview frames (fast), no voice or video
Env:   FONT_DIR, KOKORO_DIR, EXPLAINER_OUT, FFMPEG (path to ffmpeg, default "ffmpeg")
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

W, H, FPS = 1080, 1920, 30
OUT = os.environ.get("EXPLAINER_OUT", os.path.join(HERE, "out", "explainer"))
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FD = os.path.join(os.environ.get("FONT_DIR", "/usr/share/fonts/truetype/google-fonts"), "")
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS

NAVY, NAVY2 = (18, 24, 52), (40, 36, 92)
INK, WHITE, YELLOW = (20, 22, 40), (255, 255, 255), (255, 206, 60)
CORAL, TEAL, GREY, PURPLE = (255, 107, 87), (0, 176, 160), (150, 156, 180), (124, 92, 255)

# presenter palette
SKIN, SKIN_D = (224, 170, 132), (190, 134, 100)
HAIR, HAIR_H = (38, 24, 20), (82, 56, 46)
TOP, TOP_D = (0, 150, 140), (0, 116, 108)
LIP, MOUTH_IN, IRIS = (184, 72, 82), (110, 32, 42), (66, 40, 26)
GOLD = (236, 190, 80)


def font(weight, size):
    for name in (f"Poppins-{weight}.ttf", "Poppins-Bold.ttf"):
        if os.path.exists(FD + name):
            return ImageFont.truetype(FD + name, size)
    return ImageFont.load_default()


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_back(x):  # overshoots a little, then settles
    x = min(max(x, 0.0), 1.0)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------------------------------------------------------------- the presenter
SS = 2             # supersampling for smooth edges
PW, PH = 820, 984  # sprite size in the video (100 x 120 units)
_cache = {}


def presenter(pose="rest", brows="soft", mouth=0.0, eyes="open", look=(0, 0)):
    key = (pose, brows, round(mouth * 5), eyes, look)
    if key in _cache:
        return _cache[key]
    n = PW * SS
    im = Image.new("RGBA", (n, PH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = n / 100

    def U(*v):
        return [x * u for x in v]

    def limb(p, q, w, col):
        d.line([tuple(U(*p)), tuple(U(*q))], fill=col, width=int(w * u))
        r = w / 2
        for x, y in (p, q):
            d.ellipse(U(x - r, y - r, x + r, y + r), fill=col)

    # long hair behind the shoulders
    d.ellipse(U(25, 11, 75, 66), fill=HAIR)
    d.rounded_rectangle(U(26, 36, 74, 86), radius=int(12 * u), fill=HAIR)

    # body: blouse with soft shoulders and a V neck
    d.rounded_rectangle(U(12, 71, 88, 150), radius=int(20 * u), fill=TOP)
    d.rounded_rectangle(U(12, 90, 88, 150), radius=int(18 * u), fill=TOP_D)
    d.rounded_rectangle(U(14, 73, 86, 146), radius=int(19 * u), fill=TOP)
    d.rectangle(U(44, 54, 56, 74), fill=SKIN)
    d.ellipse(U(43, 56, 57, 64), fill=SKIN_D)
    d.polygon([tuple(U(41.5, 71)), tuple(U(58.5, 71)), tuple(U(50, 84))], fill=SKIN)
    d.line([tuple(U(41.5, 71)), tuple(U(50, 84)), tuple(U(58.5, 71))], fill=TOP_D, width=int(1.4 * u))
    d.arc(U(44, 73, 56, 83), 20, 160, fill=GOLD, width=int(0.7 * u))  # thin necklace

    # face
    d.ellipse(U(30.5, 35, 36, 46), fill=SKIN)           # ears
    d.ellipse(U(64, 35, 69.5, 46), fill=SKIN)
    d.ellipse(U(33, 15, 67, 62), fill=SKIN_D)           # head outline
    d.ellipse(U(33.5, 15.5, 66.5, 61.4), fill=SKIN)

    # blush (soft layer)
    bl = Image.new("L", im.size, 0)
    bd = ImageDraw.Draw(bl)
    for cx in (40, 60):
        bd.ellipse(U(cx - 3.4, 47.6, cx + 3.4, 51.2), fill=70)
    im.paste((236, 120, 120), (0, 0), bl.filter(ImageFilter.GaussianBlur(1.2 * u)))

    # hair on top: side part with a swept fringe and side locks
    d.chord(U(32, 12, 68, 46), 180, 360, fill=HAIR)
    # swept fringe with a curved edge (side part on her right)
    edge = [(33.2, 40), (34.6, 34), (37.4, 30.2), (41.5, 27.6), (46.5, 26.4), (52, 26.6), (57.5, 27.6),
            (62.5, 29.6), (65.6, 32.6), (66.8, 37)]
    d.polygon([tuple(U(*p)) for p in edge + [(68, 30), (68, 20), (32, 20), (32, 36)]], fill=HAIR)
    for side in (-1, 1):  # soft locks framing the face, following its curve
        cx = 50 + side * 17.6
        d.polygon([tuple(U(*p)) for p in ((cx - 1.6 * side, 32), (cx + 2.2 * side, 33), (cx + 2.6 * side, 50),
                                          (cx + 1.6 * side, 62), (cx - 0.2 * side, 50))], fill=HAIR)
    d.arc(U(38, 15.5, 62, 34), 205, 290, fill=HAIR_H, width=int(1.1 * u))  # shine
    for cx in (33, 67):                                                     # earrings
        d.ellipse(U(cx - 1.3, 47.5, cx + 1.3, 50.1), fill=GOLD)

    # eyes
    lx, ly = look
    for ex in (43, 57):
        if eyes == "closed":
            d.arc(U(ex - 3.8, 37.5, ex + 3.8, 42.5), 20, 160, fill=INK, width=int(1.0 * u))
            continue
        d.ellipse(U(ex - 3.5, 38, ex + 3.5, 42.8), fill=WHITE)
        ix, iy = ex + lx * 1.1, 40.4 + ly * 0.7
        d.ellipse(U(ix - 2.1, iy - 2.1, ix + 2.1, iy + 2.1), fill=IRIS)
        d.ellipse(U(ix - 1.0, iy - 1.0, ix + 1.0, iy + 1.0), fill=INK)
        d.ellipse(U(ix - 1.2, iy - 1.5, ix - 0.2, iy - 0.5), fill=WHITE)
        d.arc(U(ex - 3.9, 37.6, ex + 3.9, 44.2), 190, 350, fill=INK, width=int(1.1 * u))  # upper lash line
        side = 1 if ex > 50 else -1
        d.line([tuple(U(ex + 3.6 * side, 39.4)), tuple(U(ex + 4.9 * side, 38.2))], fill=INK, width=int(0.8 * u))

    # brows
    dy = {"soft": 0, "up": -1.6, "flat": 0.4}[brows]
    for ex in (43, 57):
        d.arc(U(ex - 4.6, 33.6 + dy, ex + 4.6, 37.8 + dy), 200, 340, fill=HAIR, width=int(1.1 * u))

    # nose
    d.line([tuple(U(50.3, 44)), tuple(U(49.3, 48.4))], fill=SKIN_D, width=int(0.6 * u))
    d.arc(U(47.8, 46.8, 52.2, 49.6), 10, 170, fill=SKIN_D, width=int(0.6 * u))

    # mouth: 0 = closed smile, 1 = wide open
    if mouth < 0.12:
        d.chord(U(46.2, 51.6, 53.8, 55.2), 0, 180, fill=LIP)                 # lower lip
        d.chord(U(46.2, 51.4, 53.8, 54.0), 180, 360, fill=(170, 62, 72))     # upper lip
        d.arc(U(45.8, 50.6, 54.2, 54.4), 20, 160, fill=MOUTH_IN, width=int(0.5 * u))
    else:
        h = 1.2 + 3.4 * mouth
        top = 53.4 - h / 2
        d.ellipse(U(46.2, top, 53.8, top + h), fill=MOUTH_IN, outline=LIP, width=int(0.7 * u))
        d.chord(U(47, top + 0.3, 53, top + 0.3 + min(2.2, h * 0.7)), 180, 360, fill=WHITE)  # teeth

    # arms (in front): shoulder -> elbow (sleeve) -> hand (skin)
    L, R = (21, 81), (79, 81)
    rest_l, rest_r = ((15, 114), (19, 130)), ((85, 114), (81, 130))
    arms = {
        "rest": (rest_l, rest_r, None),
        "point": (rest_l, ((91, 102), (93, 74)), "point"),
        "present": (((9, 106), (16, 88)), ((91, 106), (84, 88)), "palms"),
        "thumbs": (rest_l, ((90, 104), (86, 82)), "thumb"),
        "explain": (rest_l, ((90, 108), (80, 90)), "palm"),
        "wave": (rest_l, ((93, 94), (95, 68)), "palm"),
    }[pose]
    for (sx, sy), (elbow, hand), side in ((L, arms[0], "l"), (R, arms[1], "r")):
        limb((sx, sy), elbow, 10.5, TOP)
        limb(elbow, hand, 6.4, SKIN)
        hx, hy = hand
        style = arms[2] if (side == "r" or arms[2] == "palms") else None
        if style == "point":
            d.rounded_rectangle(U(hx - 1.2, hy - 8.5, hx + 1.2, hy - 1), radius=int(1.2 * u), fill=SKIN,
                                outline=SKIN_D, width=int(0.4 * u))
        if style == "thumb":
            d.rounded_rectangle(U(hx - 1.4, hy - 8.2, hx + 1.4, hy - 1), radius=int(1.4 * u), fill=SKIN,
                                outline=SKIN_D, width=int(0.4 * u))
        r = 4.3 if style in ("palm", "palms") else 3.8
        d.ellipse(U(hx - r, hy - r, hx + r, hy + r), fill=SKIN, outline=SKIN_D, width=int(0.5 * u))
        if style in ("palm", "palms"):
            for k in (-2.4, -0.8, 0.8, 2.4):
                d.rounded_rectangle(U(hx + k - 0.75, hy - r - 3.2, hx + k + 0.75, hy - r + 1), radius=int(0.75 * u),
                                    fill=SKIN, outline=SKIN_D, width=int(0.3 * u))

    sp = im.resize((PW, PH), LANCZOS)
    _cache[key] = sp
    return sp


# ---------------------------------------------------------------- drawing helpers
def text_c(d, cx, cy, s, f, fill, stroke=0, sfill=INK):
    d.text((cx, cy), s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sfill)


def wrap(d, s, f, maxw):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


_bg = {}


def background(accent):
    """Clean studio backdrop: gradient, soft glows, and a light floor behind the presenter."""
    if accent in _bg:
        return _bg[accent].copy()
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    for i in range(0, H, 6):
        k = i / H
        d.rectangle([0, i, W, i + 6], fill=tuple(int(a + (b - a) * k) for a, b in zip(NAVY, NAVY2)))
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-260, 120, 520, 900], fill=60)
    gd.ellipse([620, 520, 1400, 1300], fill=45)
    gd.ellipse([140, 1180, 940, 1980], fill=80)
    img.paste(accent, (0, 0), glow.filter(ImageFilter.GaussianBlur(120)))
    _bg[accent] = img
    return img.copy()


def paste_at(img, sp, cx, top):
    img.paste(sp, (int(cx - sp.width / 2), int(top)), sp)


def caption_words(img, words, t0, t1, t, y, size=78, hot=(), maxw=960):
    """Kinetic caption: words pop in one by one between t0 and t1; 'hot' words are yellow."""
    d = ImageDraw.Draw(img)
    f = font("ExtraBold", size)
    lines = wrap(d, " ".join(words), f, maxw)
    n, idx, lh = len(words), 0, int(size * 1.22)
    y0 = y - (len(lines) - 1) * lh / 2
    for li, line in enumerate(lines):
        x = W / 2 - d.textlength(line, font=f) / 2
        for w in line.split():
            appear = t0 + (t1 - t0) * idx / max(1, n)
            k = (t - appear) / 0.18
            ww = d.textlength(w, font=f)
            if k > 0:
                s = 0.6 + 0.4 * ease_back(k)
                fill = YELLOW if w.strip(".,!?:").upper() in hot else WHITE
                fs = font("ExtraBold", max(8, int(size * s)))
                d.text((x + ww / 2, y0 + li * lh), w, font=fs, fill=fill, anchor="mm",
                       stroke_width=max(2, int(size * 0.09)), stroke_fill=INK)
            x += d.textlength(w + " ", font=f)
            idx += 1


def bar_chart(img, t, labels, values, colors, title, base_y=880, maxh=500):
    d = ImageDraw.Draw(img)
    text_c(d, W / 2, 270, title, font("Black", 76), YELLOW, 6)

    for i, (lab, v, col) in enumerate(zip(labels, values, colors)):
        cx = W / 2 + (i - 0.5) * 420
        k = ease_out(t / 0.7)
        h = maxh * v / 100 * k
        d.rounded_rectangle([cx - 140, base_y - h, cx + 140, base_y], radius=22, fill=col, outline=INK, width=6)
        text_c(d, cx, base_y - h - 55, f"{round(v * k)}%", font("Black", 96), WHITE, 7)
        text_c(d, cx, base_y + 52, lab, font("ExtraBold", 54), WHITE, 5)


def step_cards(img, t, steps):
    d = ImageDraw.Draw(img)
    for i, s in enumerate(steps):
        k = ease_back((t - i * 0.9) / 0.35)
        if k <= 0:
            continue
        top = 340 + i * 205
        x0 = 70 + (1 - k) * 600
        d.rounded_rectangle([x0, top, x0 + 940, top + 175], radius=34, fill=WHITE, outline=INK, width=7)
        d.ellipse([x0 + 28, top + 35, x0 + 133, top + 140], fill=TEAL, outline=INK, width=6)
        text_c(d, x0 + 80, top + 88, str(i + 1), font("ExtraBold", 62), WHITE)
        f = font("Bold", 48)
        lines = wrap(d, s, f, 750)
        for j, ln in enumerate(lines):
            d.text((x0 + 165, top + 88 + (j - (len(lines) - 1) / 2) * 58), ln, font=f, fill=INK, anchor="lm")


def icon_book(d, cx, cy, s=1.0, col=CORAL):
    w, h = 150 * s, 110 * s
    d.rounded_rectangle([cx - w, cy - h, cx - 6, cy + h], radius=int(16 * s), fill=col, outline=INK, width=6)
    d.rounded_rectangle([cx + 6, cy - h, cx + w, cy + h], radius=int(16 * s), fill=col, outline=INK, width=6)
    for k in range(3):
        yy = cy - 50 * s + k * 40 * s
        d.line([(cx - w + 30 * s, yy), (cx - 36 * s, yy)], fill=WHITE, width=int(9 * s))
        d.line([(cx + 36 * s, yy), (cx + w - 30 * s, yy)], fill=WHITE, width=int(9 * s))
    # a circular "again" arrow
    d.arc([cx + w - 40 * s, cy - h - 50 * s, cx + w + 50 * s, cy - h + 40 * s], 200, 520, fill=YELLOW, width=int(12 * s))


def icon_test(d, cx, cy, s=1.0, col=TEAL):
    w, h = 125 * s, 150 * s
    d.rounded_rectangle([cx - w, cy - h, cx + w, cy + h], radius=int(20 * s), fill=WHITE, outline=INK, width=6)
    for k in range(3):
        yy = cy - 80 * s + k * 75 * s
        d.rounded_rectangle([cx - 90 * s, yy - 20 * s, cx - 50 * s, yy + 20 * s], radius=8, outline=INK, width=5)
        d.line([(cx - 85 * s, yy), (cx - 72 * s, yy + 14 * s), (cx - 48 * s, yy - 22 * s)], fill=col, width=int(10 * s))
        d.line([(cx - 25 * s, yy), (cx + 90 * s, yy)], fill=GREY, width=int(10 * s))


# ---------------------------------------------------------------- the episode
# Retrieval practice (the "testing effect"). Source: Roediger & Karpicke (2006),
# "Test-Enhanced Learning", Psychological Science 17(3). Experiment 1: after 5 minutes,
# reading again scored higher (81% vs 75%); after one week, self-testing won (56% vs 42%).
EPISODE = {
    "slug": "brain_bites_01",
    "scenes": [
        dict(kind="hook", say="Reading your notes again and again? You might be wasting your time.", lead=0.6,
             words="READING YOUR NOTES AGAIN AND AGAIN?", hot=("AGAIN",), pose="present"),
        dict(kind="talk", say="Going over the same page feels like studying. But your brain is only recognising it, not remembering it.",
             words="It feels like studying. But it's recognising, not remembering.",
             hot=("RECOGNISING", "REMEMBERING"), pose="explain"),
        dict(kind="versus", say="In a famous study, students either read a text again, or tested themselves on it.",
             pose="point"),
        dict(kind="chart", say="Five minutes later, reading again won. But one week later, self-testing won. Fifty-six percent, versus forty-two.",
             split=0.42, pose="point"),
        dict(kind="steps", say="So try this. Read once. Close the book. Write down everything you remember. Then check what you missed.",
             steps=["Read it once", "Close it. Write down all you remember", "Check what you missed"], pose="present"),
        dict(kind="end", say="Save this for your next exam, and follow for more Brain Bites!",
             words="SAVE THIS for your next exam!", hot=("SAVE", "THIS"), pose="thumbs"),
    ],
    "caption": (
        "Reading your notes again and again? 📚 Brain Bites #1\n\n"
        "Going over the same page feels like studying, but your brain is mostly recognising it, not remembering it.\n\n"
        "In a classic study, students either read a text again or tested themselves on it. "
        "After 5 minutes, reading again looked better. After ONE WEEK, self-testing won: 56% vs 42%.\n\n"
        "Try it today:\n1️⃣ Read once\n2️⃣ Close the book and write down everything you remember\n3️⃣ Check what you missed\n\n"
        "🔖 Save this for your next exam\n📤 Send it to a friend who's studying\n🔔 Follow for more Brain Bites\n\n"
        "Source: Roediger & Karpicke (2006), Psychological Science.\n\n"
        "#studytips #brainbites #learning #studymotivation #puzzletwister"
    ),
}


def scene_at(scenes, t):
    return next((s for s in scenes if s["t0"] <= t < s["t1"]), scenes[-1])


def render_frame(scenes, t, mouth):
    sc = scene_at(scenes, t)
    lt = t - sc["t0"]
    kind = sc["kind"]
    talking = sc["vs"] <= t <= sc["ve"]
    m = mouth if talking else 0.0
    eyes = "closed" if (t % 3.3) < 0.13 else "open"
    sway = math.sin(t * math.tau * 0.35) * 6
    pose, brows, look = sc.get("pose", "rest"), "soft", (0, 0)
    flash = 0.0
    accent = {"hook": CORAL, "talk": TEAL, "versus": PURPLE, "chart": TEAL, "steps": PURPLE, "end": CORAL}[kind]
    img = background(accent)
    d = ImageDraw.Draw(img)

    if kind == "hook":
        flash = max(0, 1 - lt / 0.3) * 0.6
        caption_words(img, sc["words"].split(), 0.1, sc["ve"] - sc["t0"] - 1.6, lt, 470, size=104, hot=sc["hot"])
        if lt > sc["ve"] - sc["t0"] - 1.4:
            k = ease_back((lt - (sc["ve"] - sc["t0"] - 1.4)) / 0.35)
            bw = 820 * k
            d.rounded_rectangle([W / 2 - bw / 2, 760, W / 2 + bw / 2, 880], radius=60, fill=CORAL, outline=INK, width=6)
            if k > 0.8:
                text_c(d, W / 2, 820, "YOU MIGHT BE WASTING TIME", font("ExtraBold", 50), WHITE)
        brows = "up"
    elif kind == "talk":
        caption_words(img, sc["words"].split(), sc["vs"] - sc["t0"], sc["ve"] - sc["t0"] - 0.4, lt, 520,
                      size=86, hot=sc["hot"])
        look = (-1, 0)
    elif kind == "versus":
        k1, k2 = ease_back((lt - 0.2) / 0.4), ease_back((lt - 1.8) / 0.4)
        if k1 > 0:
            icon_book(d, 280, 520, max(0.25, 0.95 * k1))
            text_c(d, 280, 730, "READ AGAIN", font("ExtraBold", 58), WHITE, 6)
        if lt > 1.3:
            text_c(d, W / 2, 520, "VS", font("Black", 96), YELLOW, 7)
        if k2 > 0:
            icon_test(d, 800, 520, max(0.25, 0.95 * k2))
            text_c(d, 800, 730, "TEST YOURSELF", font("ExtraBold", 56), WHITE, 6)
        look = (1, -1)
    elif kind == "chart":
        split = sc["split"] * (sc["t1"] - sc["t0"])
        if lt < split:
            bar_chart(img, lt, ["Read again", "Self-test"], [81, 75], [GREY, TEAL], "5 MINUTES LATER")
        else:
            k = lt - split
            flash = max(0, 1 - k / 0.2) * 0.5
            bar_chart(img, k, ["Read again", "Self-test"], [42, 56], [GREY, TEAL], "ONE WEEK LATER")
            brows = "up"
        look = (1, -1)
    elif kind == "steps":
        text_c(d, W / 2, 245, "TRY THIS TODAY", font("Black", 88), YELLOW, 7)
        step_cards(img, (lt - (sc["vs"] - sc["t0"]) - 0.9) * 1.45, sc["steps"])
        if lt > 6:
            pose = "thumbs"
    else:
        caption_words(img, sc["words"].split(), 0.1, 0.8, lt, 330, size=100, hot=sc["hot"])
        k = ease_back((lt - 1.0) / 0.4)
        if k > 0:
            bw = 760 * k
            d.rounded_rectangle([W / 2 - bw / 2, 610, W / 2 + bw / 2, 740], radius=65, fill=CORAL, outline=INK, width=7)
            if k > 0.8:
                text_c(d, W / 2, 675, "FOLLOW FOR MORE", font("ExtraBold", 62), WHITE)
        text_c(d, W / 2, 830, "@puzzledaily_123", font("Bold", 48), WHITE, 4)

    paste_at(img, presenter(pose, brows, m, eyes, look), W / 2 + sway, H - PH + 30)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([60, 70, 480, 150], radius=40, fill=INK)
    text_c(d, 270, 110, "BRAIN BITES #1", font("ExtraBold", 44), YELLOW)
    if flash > 0:
        img = Image.blend(img, Image.new("RGB", (W, H), WHITE), min(1, flash))
    return img


def make_cover():
    img = background(CORAL)
    d = ImageDraw.Draw(img)
    text_c(d, W / 2, 330, "READING NOTES", font("Black", 112), WHITE, 8)
    text_c(d, W / 2, 470, "AGAIN & AGAIN?", font("Black", 112), YELLOW, 8)
    d.rounded_rectangle([W / 2 - 400, 600, W / 2 + 400, 720], radius=60, fill=CORAL, outline=INK, width=6)
    text_c(d, W / 2, 660, "DO THIS INSTEAD", font("ExtraBold", 58), WHITE)
    paste_at(img, presenter("present", "up", 0.0, "open"), W / 2, H - PH + 30)
    d.rounded_rectangle([60, 70, 480, 150], radius=40, fill=INK)
    text_c(d, 270, 110, "BRAIN BITES #1", font("ExtraBold", 44), YELLOW)
    return img


# ---------------------------------------------------------------- audio + video
def plan(ep, B):
    t, clips, scenes = 0.0, [], []
    for sc in ep["scenes"]:
        lead = sc.get("lead", 0.15)
        v = B.tts(sc["say"], 1.05)
        start = t + lead
        dur = lead + len(v) / B.SR + 0.35 + (1.2 if sc["kind"] == "end" else 0)
        scenes.append(dict(sc, t0=t, t1=t + dur, vs=start, ve=start + len(v) / B.SR))
        clips.append((v, start))
        t += dur
    return scenes, clips, t


def soundtrack(B, scenes, clips, total, path):
    import soundfile as sf
    SR = B.SR
    n = int(total * SR)
    vo = np.zeros(n, np.float32)
    for v, at in clips:
        B.add(vo, v / np.max(np.abs(v)), at)
    # light, warm background: soft plucks over a slow bass, ducked under the voice
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
    sfx = np.zeros(n, np.float32)
    t = np.arange(int(0.3 * SR)) / SR
    swish = (np.convolve(np.random.default_rng(3).standard_normal(len(t)), np.ones(14) / 14, mode="same")
             * np.sin(np.pi * t / 0.3) ** 2 * 0.25).astype(np.float32)
    for sc in scenes[1:]:
        B.add(sfx, swish, max(0, sc["t0"] - 0.12))
    env = np.convolve(np.abs(vo), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    out = m * (0.9 - 0.6 * np.clip(env / 0.02, 0, 1)) + vo * 0.95 + sfx
    f = int(0.5 * SR)
    out[-f:] *= np.linspace(1, 0, f)
    out = out / max(1.0, np.max(np.abs(out)) / 0.95)
    sf.write(path, out, SR)
    hop = SR // FPS
    frames = int(total * FPS)
    rms = np.array([np.sqrt(np.mean(vo[i * hop:(i + 1) * hop] ** 2)) if i * hop < n else 0 for i in range(frames)])
    return np.clip(rms / (np.percentile(rms[rms > 0], 90) if np.any(rms > 0) else 1), 0, 1)


def stills():
    """Fast preview: a few frames with made-up timings, no voice."""
    os.makedirs(OUT, exist_ok=True)
    scenes, t = [], 0.0
    for sc, dur in zip(EPISODE["scenes"], (4.5, 6.5, 5.5, 8.5, 9.0, 4.5)):
        scenes.append(dict(sc, t0=t, t1=t + dur, vs=t + 0.3, ve=t + dur - 0.4))
        t += dur
    shots = [(3.6, 0.6), (9.5, 0.3), (14.9, 0.5), (21.0, 0.4), (30.0, 0.0), (37.8, 0.5)]
    for i, (tt, m) in enumerate(shots):
        render_frame(scenes, tt, m).save(os.path.join(OUT, f"still_{i + 1}.jpg"), quality=88)
    make_cover().save(os.path.join(OUT, "cover.jpg"), quality=90)
    print("stills in", OUT)


def main():
    if "--stills" in sys.argv:
        return stills()
    import reels as B
    os.makedirs(OUT, exist_ok=True)
    ep = EPISODE
    scenes, clips, total = plan(ep, B)
    audio = os.path.join(OUT, ep["slug"] + ".wav")
    mouth = soundtrack(B, scenes, clips, total, audio)
    out = os.path.join(OUT, ep["slug"] + ".mp4")
    cmd = [FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = int(total * FPS)
    for i in range(frames):
        p.stdin.write(render_frame(scenes, i / FPS, float(mouth[min(i, len(mouth) - 1)])).tobytes())
    p.stdin.close()
    p.wait()
    make_cover().save(os.path.join(OUT, ep["slug"] + "_cover.jpg"), quality=92)
    with open(os.path.join(OUT, ep["slug"] + ".txt"), "w", encoding="utf-8") as f:
        f.write(ep["caption"] + "\n\n--- voice ---\n" + "\n".join(f"{s['vs']:.1f}s  {s['say']}" for s in scenes) + "\n")
    os.remove(audio)
    print(f"{out}: {total:.1f}s, {frames} frames")


if __name__ == "__main__":
    main()
