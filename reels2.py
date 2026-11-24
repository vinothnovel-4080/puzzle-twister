"""Puzzle Twister reels, 'reveal yesterday + today's puzzle' format.
Day N reel: [yesterday's answer] -> [today's puzzle] -> [3-2-1 countdown] -> [answer tomorrow card]
Day 1 starts with a welcome instead of a reveal. An extra 'day10_answer' reel closes the series.
Usage: python3 reels2.py [frames|all] [day ...]   (day 11 = Day 10 answer-only reel)
"""
import json, os, sys, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw
import reels as B           # reuse voice, music, sfx helpers
R = B.R

OUT, TMP = B.OUT, B.TMP
RW, RH, FPS, TOTAL, SR = B.RW, B.RH, B.FPS, B.TOTAL, B.SR
XF = 0.3  # crossfade from reveal to puzzle

PUZZLE_VO = {
    1: "Welcome to Puzzle Twister! Day one. What number comes next? Two, six, twelve, twenty, thirty...",
    2: "Now, day two! Each shape stands for a number. What is the last line?",
    3: "Day three! Unscramble these letters to find an animal.",
    4: "Day four! How many triangles can you count?",
    5: "Day five! Use the three clues to seat four friends on the bench.",
    6: "Day six! Which number is the odd one out?",
    7: "Day seven! Rhea is fifteen, three times her brother's age. How old is he?",
    8: "Day eight! Every row and column adds up to fifteen. Find A, B, C and D.",
    9: "Day nine! A, C, F, J, O. Which letter comes next?",
    10: "Day ten! Five friends ran a race. Use the clues to find the finishing order.",
}
ANSWER_VO = {
    1: "Yesterday's answer: forty-two! The gaps grow by two.",
    2: "Yesterday's answer: sixteen! Circle ten, triangle four, square two.",
    3: "Yesterday's answer: elephant! And the bonus word: planet.",
    4: "Yesterday's answer: twelve triangles!",
    5: "Yesterday's answer: Ben, Ana, Cara, Dev!",
    6: "Yesterday's answer: forty-eight. It's not a square number!",
    7: "Yesterday's answer: five years old!",
    8: "Yesterday's answer: seven, nine, one and three!",
    9: "Yesterday's answer: U! The jumps grow by one.",
    10: "Yesterday's answer: Kiran, Omar, Noor, Maya, Leo!",
}
END_VO = "Comment A, B or C. Reveal tomorrow!"
FINALE_VO = "Did you get them all? New twisters coming soon. Follow Puzzle Twister!"


def plan(day):
    """Returns segment durations and voice clips. day 11 = finale (Day 10 answer only)."""
    speed = B.SPEED
    while True:
        if day == 11:
            v_prev = B.tts(ANSWER_VO[10].replace("Yesterday's", "Day ten"), speed)
            v_end = B.tts(FINALE_VO, speed)
            P1 = 0.3 + len(v_prev) / SR + 0.8
            P4 = len(v_end) / SR + 0.9
            return dict(v_prev=v_prev, v_end=v_end, P1=P1, P4=P4, total=P1 + P4 - XF, speed=speed)
        v_prev = B.tts(ANSWER_VO[day - 1], speed) if day > 1 else None
        v_a = B.tts(PUZZLE_VO[day], speed)
        v_end = B.tts(END_VO, speed)
        P1 = (0.3 + len(v_prev) / SR + 0.5) if v_prev is not None else 0.0
        P2 = len(v_a) / SR + 0.6
        P3 = 3.0
        P4min = len(v_end) / SR + 0.5
        used = P1 - (XF if P1 else 0) + P2 + P3
        P4 = TOTAL - used
        if P4 >= P4min or speed > 1.4:
            # give spare time back to the puzzle scene (more time to look), keep end card >= P4min
            spare = P4 - P4min
            P2 += spare * 0.6
            P4 = TOTAL - (P1 - (XF if P1 else 0) + P2 + P3)
            return dict(v_prev=v_prev, v_a=v_a, v_end=v_end, P1=P1, P2=P2, P3=P3, P4=P4,
                        total=TOTAL, speed=speed)
        speed += 0.05


# ---------------- frames ----------------
def canvas(slide, top_fn, bottom_text):
    img = Image.new("RGB", (RW, RH), R.INK)
    d = ImageDraw.Draw(img)
    img.paste(slide, (0, 300))
    d.rectangle([RW - 270, 300 + 1170, RW - 50, 300 + 1245], fill=R.BG)  # hide carousel pill
    top_fn(d)
    R.ctext(d, RW / 2, 1785, bottom_text, R.font(R.BOLD, 40), R.WHITE)
    return img


def draw_choices(img, p, acc):
    """A/B/C answer panel over the lower part of the puzzle (covers the bonus box)."""
    if not p.get("choices"):
        return img
    d = ImageDraw.Draw(img)
    x0, x1, y0, y1 = 70, RW - 70, 1170, 1690
    d.rounded_rectangle([x0, y0, x1, y1], radius=36, fill=R.INK, outline=acc, width=6)
    R.ctext(d, RW / 2, y0 + 62, "COMMENT A, B OR C", R.font(R.BOLD, 46), acc)
    maxw = x1 - 60 - (x0 + 160)
    for i, (letter, text) in enumerate(zip("ABC", p["choices"])):
        cy = y0 + 170 + i * 120
        d.ellipse([x0 + 50, cy - 42, x0 + 134, cy + 42], fill=acc)
        R.ctext(d, x0 + 92, cy + 2, letter, R.font(R.BOLD, 48), R.WHITE)
        size = 50
        while size > 28 and d.textlength(text, font=R.font(R.BOLD, size)) > maxw:
            size -= 2
        d.text((x0 + 160, cy), text, font=R.font(R.BOLD, size), fill=R.WHITE, anchor="lm")
    return img


def frames(day, data):
    brand, P = data["brand"], data["puzzles"]
    imgs = {}
    # reveal of previous day
    prev = 10 if day == 11 else day - 1
    if prev >= 1:
        pp = P[prev - 1]
        acc = R.ACCENTS[(prev - 1) % len(R.ACCENTS)]
        def top_r(d, acc=acc, prev=prev):
            R.ctext(d, RW / 2, 105, "DAY %d" % prev if day == 11 else "YESTERDAY'S", R.font(R.BOLD, 56), R.WHITE)
            R.ctext(d, RW / 2, 195, "ANSWER", R.font(R.BOLD, 96), acc)
        imgs["reveal"] = canvas(R.slide_answer(brand, pp, acc), top_r, "DID YOU GET IT RIGHT?")
    if day == 11:
        acc = R.ACCENTS[0]
        end = Image.new("RGB", (RW, RH), R.INK)
        d = ImageDraw.Draw(end)
        R.ctext(d, RW / 2, 760, "PUZZLE", R.font(R.BOLD, 150), R.WHITE)
        R.ctext(d, RW / 2, 930, "TWISTER", R.font(R.BOLD, 150), acc)
        R.ctext(d, RW / 2, 1120, "New twisters coming soon", R.font(R.REG, 52), R.WHITE)
        R.ctext(d, RW / 2, 1785, "FOLLOW @PUZZLEDAILY_123", R.font(R.BOLD, 40), R.WHITE)
        imgs["end"] = end
    else:
        p = P[day - 1]
        acc = R.ACCENTS[(day - 1) % len(R.ACCENTS)]
        puzzle = R.slide_puzzle(brand, p, acc)
        def top_q(d):
            R.ctext(d, RW / 2, 120, "TODAY'S TWISTER", R.font(R.BOLD, 56), R.WHITE)
            R.ctext(d, RW / 2, 200, "CAN YOU SOLVE IT?", R.font(R.BOLD, 76), acc)
        imgs["puzzle"] = canvas(puzzle, top_q, "PUZZLE TWISTER  ·  DAY %02d" % day)
        for n in (3, 2, 1):
            def top_c(d, n=n):
                d.text((90, 120), "THINK", font=R.font(R.BOLD, 70), fill=R.WHITE)
                d.text((90, 190), "FAST!", font=R.font(R.BOLD, 70), fill=acc)
                d.ellipse([RW - 330, 50, RW - 90, 290], fill=acc, outline=R.WHITE, width=8)
                R.ctext(d, RW - 210, 172, str(n), R.font(R.BOLD, 150), R.WHITE)
            imgs[f"c{n}"] = draw_choices(canvas(puzzle, top_c, "PUZZLE TWISTER  ·  DAY %02d" % day), p, acc)
        def top_e(d):
            R.ctext(d, RW / 2, 105, "ANSWER", R.font(R.BOLD, 70), R.WHITE)
            R.ctext(d, RW / 2, 200, "TOMORROW!", R.font(R.BOLD, 96), acc)
        imgs["end"] = draw_choices(canvas(puzzle, top_e, "COMMENT  ·  FOLLOW @PUZZLEDAILY_123"), p, acc)
    paths = {}
    for k, im in imgs.items():
        paths[k] = f"{TMP}/v2_day{day:02d}_{k}.png"
        im.save(paths[k])
    return paths


# ---------------- audio ----------------
def mix(day, pl):
    total = pl["total"]
    n = int(total * SR)
    m = B.music(day if day <= 10 else 1)
    if len(m) < n:
        m = np.pad(m, (0, n - len(m)))
    m = m[:n] / np.max(np.abs(m)) * 0.30
    vo = np.zeros(n, np.float32)
    sfx = np.zeros(n, np.float32)
    bell = 0.25 * (B.note(880, 1.2, "bell") + B.note(1320, 1.2, "bell"))
    P1 = pl["P1"]
    t_puz = P1 - XF if P1 else 0.0
    if pl.get("v_prev") is not None:
        B.add(sfx, bell, 0.0)
        B.add(vo, pl["v_prev"] / np.max(np.abs(pl["v_prev"])), 0.3)
    if day == 11:
        B.add(vo, pl["v_end"] / np.max(np.abs(pl["v_end"])), t_puz + 0.25)
    else:
        B.add(vo, pl["v_a"] / np.max(np.abs(pl["v_a"])), t_puz + 0.25)
        t_c = t_puz + pl["P2"]
        for s in range(3):
            B.add(sfx, 0.35 * B.tick(), t_c + s)
        t_e = t_c + pl["P3"]
        B.add(sfx, 0.18 * B.note(660, 0.6, "bell"), t_e)
        B.add(vo, pl["v_end"] / np.max(np.abs(pl["v_end"])), t_e + 0.2)
    env = np.convolve(np.abs(vo), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    duck = 1 - 0.7 * np.clip(env / 0.02, 0, 1)
    out = m * duck + vo * 0.85 + sfx
    f = int(0.6 * SR); out[-f:] *= np.linspace(1, 0, f)
    out = out / max(1.0, np.max(np.abs(out)) / 0.95)
    path = f"{TMP}/v2_day{day:02d}_mix.wav"
    sf.write(path, out, SR)
    return path


# ---------------- video ----------------
def encode(day, paths, audio, pl):
    total = pl["total"]
    if day == 11:
        segs = [("reveal", pl["P1"]), ("end", pl["P4"])]
    else:
        segs = ([("reveal", pl["P1"])] if pl["P1"] else []) + [
            ("puzzle", pl["P2"]), ("c3", 1.0), ("c2", 1.0), ("c1", 1.0), ("end", pl["P4"])]
    acc = R.ACCENTS[(min(day, 10) - 1) % len(R.ACCENTS)]
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for k, _ in segs:
        cmd += ["-framerate", str(FPS), "-i", paths[k]]
    ai = len(segs)
    cmd += ["-i", audio, "-f", "lavfi", "-i", "color=c=0x%02x%02x%02x:s=%dx14:r=%d" % (*acc, RW, FPS)]
    fc = []
    for i, (_, dur) in enumerate(segs):
        fc.append(f"[{i}]format=yuv420p,loop=-1:1,trim=duration={dur:.3f},setpts=PTS-STARTPTS,fps=30,settb=1/30[v{i}]")
    has_reveal = segs[0][0] == "reveal"
    rest = list(range(1, len(segs))) if has_reveal else list(range(len(segs)))
    if len(rest) > 1:
        fc.append("".join(f"[v{i}]" for i in rest) + f"concat=n={len(rest)}:v=1:a=0,fps=30,settb=1/30[rest]")
    else:
        fc.append(f"[v{rest[0]}]null[rest]")
    if has_reveal:
        fc.append(f"[v0][rest]xfade=transition=fade:duration={XF}:offset={pl['P1'] - XF:.3f}[vid]")
    else:
        fc.append("[rest]null[vid]")
    fc.append(f"[vid][{ai + 1}]overlay=x='-w+w*t/{total:.3f}':y=0:shortest=1,format=yuv420p[outv]")
    name = f"puzzle_twister_day{day:02d}_reel.mp4" if day <= 10 else "puzzle_twister_day10_answer_reel.mp4"
    tmp = f"{OUT}/.{name}.tmp.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", f"{ai}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}", "-movflags", "+faststart", tmp]
    subprocess.run(cmd, check=True)
    final = f"{OUT}/{name}"
    os.replace(tmp, final)
    return final


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    days = [int(x) for x in sys.argv[2:]] or list(range(1, 12))
    data = json.load(open(B.PUZZLES, encoding="utf-8"))
    for day in days:
        pl = plan(day)
        paths = frames(day, data)
        print(f"day {day}: " + " ".join(f"{k}={pl[k]:.2f}" for k in ("P1", "P2", "P3", "P4", "total", "speed") if k in pl))
        if mode == "all":
            print(" ->", encode(day, paths, mix(day, pl), pl))


if __name__ == "__main__":
    main()
