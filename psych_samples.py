"""Three SAMPLE psychology-style reels (not scheduled, not posted):
  door   - personality test: pick a door 1, 2 or 3
  stroop - brain test: say the colour, not the word
  words  - personality test: the first word you see in a letter grid

Output (PSYCH_OUT, default out/samples/psych): <name>.mp4, <name>_cover.jpg,
<name>_frame.png and <name>.txt (caption, voice script, next-day "meaning").
Reuses the trend-series look, voice, music and encoder from trend.py.
"""
import os, random
from PIL import Image, ImageDraw
import reels as B
import trend as TR
R = B.R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("PSYCH_OUT", os.path.join(HERE, "out", "samples", "psych"))
RW, RH, SR = B.RW, B.RH, B.SR
FOLLOW = "🔔 Follow @puzzledaily_123 for new puzzles every day."

COL = {"RED": (220, 50, 50), "BLUE": (40, 100, 220), "GREEN": (30, 150, 70),
       "YELLOW": (225, 170, 0), "PURPLE": (130, 60, 200), "ORANGE": (240, 120, 20)}

SAMPLES = {
    "door": dict(
        acc=R.ACCENTS[0], label="PERSONALITY TEST", top=("PERSONALITY TEST", "PICK A DOOR"), N=8,
        hook="Personality test! Pick a door: one, two, or three. Don't overthink it!",
        end="Comment your door, and send this to a friend. We'll tell you what it means tomorrow!",
        end_top=("MEANING", "TOMORROW!"), panel=("COMMENT 1, 2 OR 3", "Go with your gut"),
        caption=("Personality test 🚪 Pick a door: 1, 2 or 3!\n\n"
                 "Don't overthink it. Go with your first choice.\n\n"
                 "💬 Comment your door. We'll share what it says about you tomorrow (just for fun 😄)\n"
                 "📤 Send this to a friend and compare picks!\n" + FOLLOW + "\n\n"
                 "#puzzletwister #personalitytest #psychologytest #mindgames #brainteaser"),
        meaning=("1 (red): bold and full of energy; you like to take the lead.\n"
                 "2 (green): calm and caring; people feel at ease around you.\n"
                 "3 (blue): thoughtful and curious; you like to understand how things work.\n"
                 "(Just for fun, not a real test.)")),
    "stroop": dict(
        acc=R.ACCENTS[4], label="BRAIN TEST", top=("BRAIN TEST", "SAY THE COLOUR!"), N=10,
        hook="Brain test! Say the colour of each word out loud, not the word itself. Go!",
        end="How long did it take you? Comment your time, and challenge a friend!",
        end_top=("HOW FAST", "WERE YOU?"), panel=("SAY THE COLOUR, NOT THE WORD", "Comment your time"),
        caption=("Brain test 🧠 Say the COLOUR, not the word!\n\n"
                 "Read the colours out loud as fast as you can. Your brain wants to read the word, "
                 "so it's harder than it looks.\n\n"
                 "💬 How many seconds did it take you? Comment your time ⏱️\n"
                 "📤 Send this to a friend and race them!\n" + FOLLOW + "\n\n"
                 "#puzzletwister #strooptest #braintest #mindgames #brainteaser"),
        meaning=("This is the Stroop effect: reading is so automatic that the word gets in the way "
                 "of naming the colour. Most people take 10 to 20 seconds for 12 words.")),
    "words": dict(
        acc=R.ACCENTS[3], label="PERSONALITY TEST", top=("WHAT'S THE FIRST", "WORD YOU SEE?"), N=8,
        hook="What's the first word you see? Look closely!",
        end="Comment the first word you saw, and send this to a friend!",
        end_top=("COMMENT", "YOUR WORD!"), panel=("COMMENT THE FIRST WORD", "you spotted"),
        caption=("Personality test 🔤 What's the first word you see?\n\n"
                 "Look at the grid for 5 seconds. The first word you spot is said to show what you "
                 "want most right now (just for fun 😄)\n\n"
                 "💬 Comment the first word you saw!\n"
                 "📤 Send this to a friend and see if they spot the same one.\n" + FOLLOW + "\n\n"
                 "#puzzletwister #personalitytest #firstwordyousee #wordsearch #mindgames"),
        meaning=("LOVE: close relationships matter most to you right now.\n"
                 "MONEY: you're focused on security and your goals.\n"
                 "PEACE: you need rest and calm.\n"
                 "TRAVEL: you want adventure and something new.\n"
                 "(Just for fun, not a real test.)")),
}


# ---------------- puzzle drawings (inside the card, y 330..1150) ----------------
def draw_door(img, s):
    d = ImageDraw.Draw(img)
    colors = [(214, 64, 52), (38, 150, 90), (46, 104, 210)]
    w, h, top = 230, 400, 560
    for i, col in enumerate(colors):
        cx = 220 + i * 320
        x0, x1 = cx - w / 2, cx + w / 2
        d.rounded_rectangle([x0 - 14, top - 14, x1 + 14, top + h], radius=18, fill=(120, 84, 52))  # frame
        d.rounded_rectangle([x0, top, x1, top + h], radius=12, fill=col)
        for py in (top + 30, top + h / 2 + 15):  # panels
            d.rounded_rectangle([x0 + 28, py, x1 - 28, py + h / 2 - 60], radius=8,
                                outline=tuple(max(0, c - 45) for c in col), width=6)
        d.ellipse([x1 - 50, top + h / 2 - 14, x1 - 22, top + h / 2 + 14], fill=(240, 200, 80))  # knob
        d.ellipse([cx - 42, top - 120, cx + 42, top - 36], fill=R.INK)
        R.ctext(d, cx, top - 76, str(i + 1), R.font(R.BOLD, 52), R.WHITE)
    R.ctext(d, RW / 2, top + h + 70, "Trust your gut. Which one?", R.font(R.SEMI, 44), R.MUTED)


STROOP = [("RED", "BLUE"), ("GREEN", "RED"), ("YELLOW", "PURPLE"),
          ("BLUE", "ORANGE"), ("PURPLE", "GREEN"), ("ORANGE", "RED"),
          ("RED", "YELLOW"), ("BLUE", "GREEN"), ("GREEN", "PURPLE"),
          ("YELLOW", "BLUE"), ("ORANGE", "GREEN"), ("PURPLE", "ORANGE")]


def draw_stroop(img, s):
    d = ImageDraw.Draw(img)
    f = R.font(R.BOLD, 64)
    for i, (word, ink) in enumerate(STROOP):
        assert word != ink
        r, c = divmod(i, 3)
        R.ctext(d, 230 + c * 310, 520 + r * 130, word, f, COL[ink])
    R.ctext(d, RW / 2, 1075, "Say each COLOUR out loud.", R.font(R.SEMI, 42), R.MUTED)


WORDS = [("LOVE", 1, 0, "h"), ("MONEY", 4, 3, "h"), ("PEACE", 4, 1, "v"), ("TRAVEL", 0, 8, "v")]


def word_grid():
    g = [[None] * 9 for _ in range(9)]
    for word, r, c, way in WORDS:
        for k, ch in enumerate(word):
            rr, cc = (r, c + k) if way == "h" else (r + k, c)
            assert g[rr][cc] in (None, ch), (word, rr, cc)
            g[rr][cc] = ch
    rng = random.Random("first-word")
    filler = "BCDFGHJKLMNPQRSTVWXZAEIOU"
    return [[ch or rng.choice(filler) for ch in row] for row in g]


def draw_words(img, s):
    d = ImageDraw.Draw(img)
    f = R.font(R.BOLD, 54)
    g = word_grid()
    cw, ch, x0, y0 = 98, 72, RW / 2 - 98 * 4, 500
    for r, row in enumerate(g):
        for c, letter in enumerate(row):
            R.ctext(d, x0 + c * cw, y0 + r * ch, letter, f, R.INK)


DRAW = {"door": draw_door, "stroop": draw_stroop, "words": draw_words}


# ---------------- frames ----------------
def card(img, name, s):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([50, 330, RW - 50, 1150], radius=40, fill=R.BG)
    lw = d.textlength(s["label"], font=R.font(R.BOLD, 30)) + 60
    d.rounded_rectangle([100, 360, 100 + lw, 420], radius=30, fill=R.INK)
    R.ctext(d, 100 + lw / 2, 390, s["label"], R.font(R.BOLD, 30), R.WHITE)
    DRAW[name](img, s)


def panel(img, name, s):
    d = ImageDraw.Draw(img)
    acc = s["acc"]
    d.rounded_rectangle([36, 1196, RW - 36, 1700], radius=36, fill=R.INK, outline=acc, width=6)
    l1, l2 = s["panel"]
    size = 62
    while d.textlength(l1, font=R.font(R.BOLD, size)) > RW - 140:
        size -= 2
    R.ctext(d, RW / 2, 1290, l1, R.font(R.BOLD, size), acc)
    R.ctext(d, RW / 2, 1385, l2, R.font(R.BOLD, 50), R.WHITE)
    TR.paste_emoji(img, "⏱" if name == "stroop" else "👇", RW / 2, 1550, 130)


def frame(name, s, top_fn, bottom, timer=None):
    img = Image.new("RGB", (RW, RH), R.INK)
    card(img, name, s)
    panel(img, name, s)
    d = ImageDraw.Draw(img)
    top_fn(d)
    if timer:
        left, total = timer
        d.rounded_rectangle([50, 298, RW - 50, 318], radius=10, fill=(60, 66, 96))
        d.rounded_rectangle([50, 298, 50 + (RW - 100) * left / total, 318], radius=10, fill=s["acc"])
    R.ctext(d, RW / 2, 1790, bottom, R.font(R.BOLD, 38), R.WHITE)
    return img


def top_two(l1, l2, acc):
    def f(d):
        R.ctext(d, RW / 2, 100, l1, R.font(R.BOLD, 60), R.WHITE)
        size = 92
        while d.textlength(l2, font=R.font(R.BOLD, size)) > RW - 100:
            size -= 4
        R.ctext(d, RW / 2, 200, l2, R.font(R.BOLD, size), acc)
    return f


def cover(name, s, title):
    CW, CH = 1080, 1920
    img = Image.new("RGB", (CW, CH), R.INK)
    d = ImageDraw.Draw(img)
    acc = s["acc"]
    soft = tuple(int(c * 0.45 + i * 0.55) for c, i in zip(acc, R.INK))
    d.ellipse([CW - 380, -160, CW + 220, 440], fill=soft)
    d.ellipse([-260, CH - 420, 340, CH + 180], fill=soft)
    R.ctext(d, CW / 2, 300, "PUZZLE TWISTER", R.font(R.BOLD, 44), R.WHITE)
    l1, l2 = s["top"]
    R.ctext(d, CW / 2, 410, l1, R.font(R.BOLD, 70), R.WHITE)
    size = 110
    while d.textlength(l2, font=R.font(R.BOLD, size)) > 980:
        size -= 6
    R.ctext(d, CW / 2, 530, l2, R.font(R.BOLD, size), acc)
    crop = title.crop((50, 330, RW - 50, 1150))
    k = 0.86
    crop = crop.resize((int(crop.width * k), int(crop.height * k)), TR.LANCZOS)
    x, y = (CW - crop.width) // 2, 640
    d.rounded_rectangle([x - 10, y - 10, x + crop.width + 10, y + crop.height + 10], radius=40, fill=acc)
    img.paste(crop, (x, y))
    R.ctext(d, CW / 2, y + crop.height + 85, "COMMENT YOUR ANSWER", R.font(R.BOLD, 50), R.WHITE)
    return img


def build(name, s):
    tmp = os.path.join(B.TMP, "psych_" + name)
    os.makedirs(tmp, exist_ok=True)
    v_hook, v_end = B.tts(s["hook"], B.SPEED), B.tts(s["end"], B.SPEED)
    A, N = 1.5, s["N"]
    C = max(3.5, len(v_end) / SR + 0.7)
    pl = dict(v_hook=v_hook, v_end=v_end, A=A, N=N, C=C, total=A + N + C, options_at=None)
    bottom = "PUZZLE TWISTER  ·  SAMPLE"
    title = frame(name, s, top_two(*s["top"], s["acc"]), bottom)
    segs = [(os.path.join(tmp, "title.png"), A)]
    title.save(segs[0][0])
    for n in range(N, 0, -1):
        fp = os.path.join(tmp, f"count_{n:02d}.png")
        frame(name, s, TR.top_count(n, s["acc"]), bottom, timer=(n, N)).save(fp)
        segs.append((fp, 1.0))
    fp = os.path.join(tmp, "end.png")
    frame(name, s, top_two(*s["end_top"], s["acc"]), "SEND THIS TO A FRIEND").save(fp)
    segs.append((fp, C))
    audio = os.path.join(tmp, "mix.wav")
    TR.mix(pl, audio, {"door": 41, "stroop": 42, "words": 43}[name])
    TR.encode(segs, audio, os.path.join(OUT, name + ".mp4"), s["acc"], pl["total"])
    cover(name, s, title).save(os.path.join(OUT, name + "_cover.jpg"), "JPEG", quality=90)
    Image.open(os.path.join(tmp, f"count_{N - 2:02d}.png")).save(os.path.join(OUT, name + "_frame.png"))
    with open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8") as f:
        f.write(s["caption"] + "\n\n--- voice ---\n"
                f"0.3s  {s['hook']}\n{A + N + 0.3:.1f}s  {s['end']}\n\n--- next-day reveal ---\n{s['meaning']}\n")
    print(f"{name}: countdown {N}s, total {pl['total']:.1f}s")


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, s in SAMPLES.items():
        build(name, s)


if __name__ == "__main__":
    main()
