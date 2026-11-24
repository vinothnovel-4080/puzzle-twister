"""Render Instagram carousel slides (1080x1350) for every puzzle in puzzles.json.
Output: out/day_XX/01_puzzle.png, 02_hint.png, 03_answer.png
"""
import json, os, math
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(os.environ.get("FONT_DIR", "/usr/share/fonts/truetype/google-fonts"), "")
BOLD = F + "Poppins-Bold.ttf"
SEMI = F + "Poppins-Medium.ttf"
REG = F + "Poppins-Regular.ttf" if os.path.exists(F + "Poppins-Regular.ttf") else BOLD

BG = (255, 248, 238)
INK = (29, 36, 64)
MUTED = (110, 116, 140)
WHITE = (255, 255, 255)
ACCENTS = [(255, 107, 87), (0, 166, 153), (255, 176, 32), (124, 92, 255), (52, 152, 219)]
SHAPE_COL = {"circle": (255, 107, 87), "triangle": (0, 166, 153), "square": (124, 92, 255)}


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(d, text, fnt, x, y, maxw, fill=INK, center=False, gap=1.25):
    lh = int(fnt.size * gap)
    for line in wrap(d, text, fnt, maxw):
        lx = x + (maxw - d.textlength(line, font=fnt)) / 2 if center else x
        d.text((lx, y), line, font=fnt, fill=fill)
        y += lh
    return y


def ctext(d, cx, cy, text, fnt, fill):
    d.text((cx, cy), text, font=fnt, fill=fill, anchor="mm")


def base(brand, p, accent, label):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # decorative dots
    for i, (x, y, r) in enumerate([(990, 70, 120)]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(min(255, c + 60) for c in accent))
    # header
    d.rounded_rectangle([60, 60, 60 + 230, 120], radius=30, fill=INK)
    ctext(d, 175, 90, f"DAY {p['day']:02d}", font(BOLD, 30), WHITE)
    d.text((315, 70), p["type"].upper(), font=font(BOLD, 32), fill=accent)
    d.rounded_rectangle([W - 60 - 200, 1180, W - 60, 1236], radius=28, fill=accent)
    if label == "SWIPE":
        ctext(d, W - 195, 1208, label, font(BOLD, 26), WHITE)
        ax = W - 105
        d.line([(ax - 22, 1208), (ax + 8, 1208)], fill=WHITE, width=5)
        d.polygon([(ax + 18, 1208), (ax + 4, 1197), (ax + 4, 1219)], fill=WHITE)
    else:
        ctext(d, W - 160, 1208, label, font(BOLD, 26), WHITE)
    if brand.get("handle"):
        d.text((60, 1185), brand["name"], font=font(BOLD, 30), fill=INK)
        d.text((60, 1225), brand["handle"], font=font(REG, 24), fill=MUTED)
    else:
        d.text((60, 1190), brand["name"], font=font(BOLD, 34), fill=INK)
    return img, d


def tile(d, x, y, s, text, accent, filled=False):
    d.rounded_rectangle([x + 6, y + 8, x + s + 6, y + s + 8], radius=24, fill=(225, 214, 200))
    d.rounded_rectangle([x, y, x + s, y + s], radius=24, fill=accent if filled else WHITE,
                        outline=INK, width=5)
    ctext(d, x + s / 2, y + s / 2 + 2, text, font(BOLD, int(s * (0.42 if len(text) < 3 else 0.34))),
          WHITE if filled else INK)


def draw_shape(d, kind, cx, cy, r):
    c = SHAPE_COL[kind]
    if kind == "circle":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c, outline=INK, width=4)
    elif kind == "square":
        d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=10, fill=c, outline=INK, width=4)
    else:
        d.polygon([(cx, cy - r), (cx + r * 1.1, cy + r * 0.85), (cx - r * 1.1, cy + r * 0.85)],
                  fill=c, outline=INK, width=4)


def visual(d, p, accent, top, bottom, solved=False):
    v, data = p["visual"], p["visual_data"]
    mid = (top + bottom) / 2
    if v in ("number_tiles", "letter_tiles"):
        n = len(data)
        rows = [data] if n <= 6 else [data[:4], data[4:]]
        per = len(rows[0])
        s = min(150 if n <= 6 else 170, int((W - 120 - (per - 1) * 20) / per))
        total_h = len(rows) * s + (len(rows) - 1) * 30
        y = mid - total_h / 2
        for row in rows:
            rw = len(row) * s + (len(row) - 1) * 20
            x = (W - rw) / 2
            for t in row:
                tile(d, x, y, s, t, accent, filled=(t == "?" or t == p.get("_hl")))
                x += s + 20
            y += s + 30
    elif v == "shape_equations":
        rowh = min(150, (bottom - top) / len(data))
        y = mid - rowh * len(data) / 2 + rowh / 2
        f = font(BOLD, 60)
        for shapes, res in data:
            x = 110
            prev = None
            for sh in shapes:
                if sh == "-":
                    ctext(d, x - 25, y, "–", f, INK)
                    prev = sh
                    continue
                if prev not in (None, "-"):
                    ctext(d, x - 25, y, "+", f, INK)
                draw_shape(d, sh, x + 60, y, 46)
                x += 190
                prev = sh
            ctext(d, 760, y, "=", f, INK)
            if res == "?":
                d.rounded_rectangle([830, y - 52, 970, y + 52], radius=20, fill=accent)
                ctext(d, 900, y + 2, "?", f, WHITE)
            else:
                ctext(d, 900, y + 2, res, f, INK)
            y += rowh
    elif v == "triangle_figure":
        h = bottom - top - 40
        apex = (W / 2, top + 20)
        bl, br = (W / 2 - h * 0.62, bottom - 20), (W / 2 + h * 0.62, bottom - 20)
        d.polygon([apex, bl, br], fill=WHITE, outline=INK, width=8)
        for k in range(1, data["apex_lines"] + 1):
            fx = bl[0] + (br[0] - bl[0]) * k / (data["apex_lines"] + 1)
            d.line([apex, (fx, bl[1])], fill=INK, width=8)
        for k in range(1, data["cross_lines"] + 1):
            t = k / (data["cross_lines"] + 1)
            y = apex[1] + (bl[1] - apex[1]) * t
            x0 = apex[0] + (bl[0] - apex[0]) * t
            x1 = apex[0] + (br[0] - apex[0]) * t
            d.line([(x0, y), (x1, y)], fill=accent, width=8)
    elif v == "bench":
        names = p["answer"].split(", ") if solved else ["?"] * data["seats"]
        n = data["seats"]
        s = 170
        gap = 40
        x0 = (W - (n * s + (n - 1) * gap)) / 2
        y = top + 10
        d.rounded_rectangle([x0 - 30, y + s - 10, x0 + n * s + (n - 1) * gap + 30, y + s + 30],
                            radius=14, fill=(196, 140, 92), outline=INK, width=4)
        for i in range(n):
            x = x0 + i * (s + gap)
            tile(d, x, y, s, names[i] if solved else "?", accent, filled=not solved)
            ctext(d, x + s / 2, y + s + 70, f"Seat {i + 1}", font(SEMI, 28), MUTED)
        clue_y = y + s + 130
        if not solved:
            d.text((80, clue_y), "Friends: " + ", ".join(data["people"]), font=font(SEMI, 32), fill=INK)
            clue_y += 60
            for i, c in enumerate(p["clues"]):
                d.ellipse([80, clue_y + 4, 124, clue_y + 48], fill=accent)
                ctext(d, 102, clue_y + 27, str(i + 1), font(BOLD, 26), WHITE)
                clue_y = text_block(d, c, font(REG, 32), 145, clue_y, W - 225) + 14
    elif v == "podium":
        names = p["answer"].split(", ") if solved else ["?"] * data["places"]
        n = data["places"]
        s = 150
        gap = 25
        x0 = (W - (n * s + (n - 1) * gap)) / 2
        y = top + 10
        labels = ["1st", "2nd", "3rd", "4th", "5th"]
        for i in range(n):
            x = x0 + i * (s + gap)
            d.rounded_rectangle([x + 6, y + 8, x + s + 6, y + s + 8], radius=24, fill=(225, 214, 200))
            d.rounded_rectangle([x, y, x + s, y + s], radius=24, fill=WHITE if solved else accent,
                                outline=INK, width=5)
            ctext(d, x + s / 2, y + s / 2, names[i], font(BOLD, 34 if solved else 64),
                  INK if solved else WHITE)
            ctext(d, x + s / 2, y + s + 45, labels[i], font(SEMI, 28), MUTED)
        clue_y = y + s + 105
        if not solved:
            d.text((80, clue_y), "Runners: " + ", ".join(data["people"]), font=font(SEMI, 32), fill=INK)
            clue_y += 60
            for i, c in enumerate(p["clues"]):
                d.ellipse([80, clue_y + 4, 124, clue_y + 48], fill=accent)
                ctext(d, 102, clue_y + 27, str(i + 1), font(BOLD, 26), WHITE)
                clue_y = text_block(d, c, font(REG, 32), 145, clue_y, W - 225) + 14
    elif v == "two_people":
        for cx, name, scale, col in [(W / 2 - 170, data["left"], 1.0, accent), (W / 2 + 170, data["right"], 0.7, ACCENTS[1])]:
            hr = 70 * scale
            body_h = 200 * scale
            base_y = bottom - 60
            d.rounded_rectangle([cx - 90 * scale, base_y - body_h, cx + 90 * scale, base_y], radius=int(60 * scale), fill=col, outline=INK, width=5)
            d.ellipse([cx - hr, base_y - body_h - 2 * hr - 10, cx + hr, base_y - body_h - 10], fill=(255, 214, 170), outline=INK, width=5)
            ctext(d, cx, base_y + 35, name, font(BOLD, 34), INK)
            head_top = base_y - body_h - 2 * hr - 10
            age = "15" if name == data["left"] else ("?" if not solved else p["answer"])
            d.rounded_rectangle([cx - 60, head_top - 110, cx + 60, head_top - 20], radius=24, fill=WHITE, outline=col, width=5)
            ctext(d, cx, head_top - 63, age, font(BOLD, 54), col)
    elif v == "grid3":
        grid = p["solution_grid"] if solved else data
        s = min(190, (bottom - top - 20) / 3)
        x0, y0 = (W - 3 * s) / 2, mid - 1.5 * s
        for r in range(3):
            for c in range(3):
                t = grid[r][c]
                hidden = data[r][c].isalpha()
                x, y = x0 + c * s, y0 + r * s
                d.rectangle([x, y, x + s, y + s], fill=(accent if (hidden and not solved) else WHITE), outline=INK, width=6)
                ctext(d, x + s / 2, y + s / 2 + 2, t, font(BOLD, 80),
                      WHITE if (hidden and not solved) else (accent if hidden else INK))


def slide_puzzle(brand, p, accent):
    img, d = base(brand, p, accent, "SWIPE")
    y = text_block(d, p["question"], font(BOLD, 54 if len(p["question"]) < 60 else 46), 60, 170, W - 120)
    has_clues = "clues" in p
    vis_top = y + 30
    vis_bot = 960
    visual(d, p, accent, vis_top, vis_bot)
    if True:
        # bonus box
        by = 990
        d.rounded_rectangle([60, by, W - 60, 1155], radius=26, fill=INK)
        d.text((95, by + 22), "BONUS  ·  EXPERTS", font=font(BOLD, 26), fill=accent)
        text_block(d, p["bonus_question"], font(SEMI, 30), 95, by + 60, W - 190, fill=WHITE, gap=1.2)
    return img


def slide_hint(brand, p, accent):
    img, d = base(brand, p, accent, "STUCK?")
    ctext(d, W / 2, 330, "HINT", font(BOLD, 150), accent)
    d.rounded_rectangle([90, 470, W - 90, 900], radius=36, fill=WHITE, outline=INK, width=5)
    fh = font(SEMI, 50)
    n = len(wrap(d, p["hint"], fh, W - 280))
    text_block(d, p["hint"], fh, 140, 685 - n * int(50 * 1.25) / 2, W - 280, center=True)
    text_block(d, "Comment your answer below. Full answer tomorrow!", font(SEMI, 34), 90, 960, W - 180, fill=MUTED, center=True)
    return img


def slide_answer(brand, p, accent):
    img, d = base(brand, p, accent, "ANSWER")
    d.text((60, 160), "THE ANSWER", font=font(BOLD, 34), fill=MUTED)
    fa = font(BOLD, 96 if len(p["answer"]) <= 10 else 54)
    y = text_block(d, p["answer"], fa, 60, 205, W - 120, fill=accent, gap=1.1)
    if p["visual"] in ("number_tiles", "letter_tiles"):
        vd = p["visual_data"]
        q = dict(p)
        if "?" in vd:
            q["visual_data"] = [p["answer"] if t == "?" else t for t in vd]
        elif p["visual"] == "letter_tiles":
            q["visual_data"] = list(p["answer"])
        q["_hl"] = p["answer"]
        h = 200 if len(q["visual_data"]) <= 6 else 400
        visual(d, q, accent, y + 10, y + 10 + h)
        y = y + h + 40
    elif p["visual"] in ("bench", "podium", "grid3", "two_people"):
        top = y + 20
        bot = top + (300 if p["visual"] in ("bench", "podium") else 380)
        visual(d, p, accent, top, bot, solved=True)
        y = bot + (60 if p["visual"] in ("bench", "podium") else 30)
    else:
        y += 30
    y = text_block(d, p["explanation"], font(REG, 34), 60, y, W - 120, gap=1.35)
    by = max(y + 30, 930)
    by = min(by, 1000)
    d.rounded_rectangle([60, by, W - 60, 1150], radius=26, fill=INK)
    d.text((95, by + 22), "BONUS ANSWER", font=font(BOLD, 26), fill=accent)
    text_block(d, p["bonus_answer"], font(SEMI, 32), 95, by + 62, W - 190, fill=WHITE, gap=1.2)
    return img


def slide_cover(brand, p, accent, answer=False):
    """1080x1920 reel cover: day number, puzzle type and that day's puzzle (or answer).
    Everything important sits between y=240 and y=1680, the part the profile grid shows."""
    CW, CH = 1080, 1920
    img = Image.new("RGB", (CW, CH), INK)
    d = ImageDraw.Draw(img)
    # soft accent circles so each day's cover has its own colour at a glance
    soft = tuple(int(c * 0.45 + i * 0.55) for c, i in zip(accent, INK))
    d.ellipse([CW - 380, -160, CW + 220, 440], fill=soft)
    d.ellipse([-260, CH - 420, 340, CH + 180], fill=soft)
    ctext(d, CW / 2, 300, brand["name"], font(BOLD, 44), WHITE)
    label = f"DAY {p['day']:02d} ANSWER" if answer else f"DAY {p['day']:02d}"
    ctext(d, CW / 2, 415, label, font(BOLD, 104 if answer else 150), accent)
    ctext(d, CW / 2, 535, p["type"].upper(), font(BOLD, 50), WHITE)
    slide = slide_answer(brand, p, accent) if answer else slide_puzzle(brand, p, accent)
    sd = ImageDraw.Draw(slide)
    sd.rectangle([W - 270, 1170, W - 50, 1245], fill=BG)  # hide the carousel "SWIPE" pill
    scale = 0.70
    w, h = int(W * scale), int(H * scale)
    lanczos = getattr(Image, "Resampling", Image).LANCZOS
    small = slide.resize((w, h), lanczos)
    x, y = (CW - w) // 2, 600
    d.rounded_rectangle([x - 10, y - 10, x + w + 10, y + h + 10], radius=28, fill=accent)
    img.paste(small, (x, y))
    ctext(d, CW / 2, y + h + 75, "DID YOU GET IT RIGHT?" if answer else "CAN YOU SOLVE IT?", font(BOLD, 64), WHITE)
    return img


def main():
    data = json.load(open(os.path.join(HERE, "puzzles.json"), encoding="utf-8"))
    brand = data["brand"]
    covers = os.path.join(HERE, "out", "covers")
    os.makedirs(covers, exist_ok=True)
    for p in data["puzzles"]:
        accent = ACCENTS[(p["day"] - 1) % len(ACCENTS)]
        slide_cover(brand, p, accent).save(os.path.join(covers, f"cover_day{p['day']:02d}.jpg"), "JPEG", quality=90)
    last = data["puzzles"][-1]
    slide_cover(brand, last, ACCENTS[(last["day"] - 1) % len(ACCENTS)], answer=True).save(
        os.path.join(covers, "cover_day10_answer.jpg"), "JPEG", quality=90)
    for p in data["puzzles"]:
        accent = ACCENTS[(p["day"] - 1) % len(ACCENTS)]
        out = os.path.join(HERE, "out", f"day_{p['day']:02d}")
        os.makedirs(out, exist_ok=True)
        slide_puzzle(brand, p, accent).save(os.path.join(out, "01_puzzle.png"))
        slide_hint(brand, p, accent).save(os.path.join(out, "02_hint.png"))
        slide_answer(brand, p, accent).save(os.path.join(out, "03_answer.png"))
        with open(os.path.join(out, "caption.txt"), "w") as f:
            f.write(p["caption"] + "\n\n" + " ".join(p["hashtags"]) + "\n")
    print("done")


if __name__ == "__main__":
    main()
