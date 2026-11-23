"""Build 15s vertical reels (1080x1920, 30fps) with English voiceover + generated music.
Usage: python3 reels.py [frames|all] [day ...]
"""
import json, os, sys, subprocess, math
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw

sys.path.insert(0, "/home/claude/puzzles")
import render as R

OUT = "/home/claude/reels/out"
TMP = "/home/claude/reels/tmp"
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
RW, RH, FPS, TOTAL = 1080, 1920, 30, 15.0
SR = 44100
VOICE, SPEED = "af_heart", 1.08

SCRIPT = {
    1: ("Day one twister! What number comes next? Two, six, twelve, twenty, thirty...",
        "It's forty-two! The gaps grow by two each time. Follow for tomorrow's twister!"),
    2: ("Day two! Each shape stands for a number. What is the last line?",
        "Sixteen! Circle is ten, triangle four, square two. Follow for more!"),
    3: ("Day three! Unscramble these letters to find an animal.",
        "Elephant! And the hidden bonus word is planet. Follow for more twisters!"),
    4: ("Day four! How many triangles can you count?",
        "Twelve! Six in the top part, and six in the whole shape. Did you get it?"),
    5: ("Day five! Use the three clues to seat four friends on the bench.",
        "Ben, Ana, Cara, Dev! Ben can't sit next to Dev. Follow for more!"),
    6: ("Day six! Which number is the odd one out?",
        "Forty-eight! All the others are square numbers. Follow for more twisters!"),
    7: ("Day seven! Rhea is fifteen, three times her brother's age. How old is he?",
        "Five! Bonus: in five years, Rhea will be twice his age."),
    8: ("Day eight! Every row and column adds up to fifteen. Find A, B, C and D.",
        "Seven, nine, one and three! Follow for tomorrow's twister!"),
    9: ("Day nine! A, C, F, J, O. Which letter comes next?",
        "U! The jumps grow by one each time. Follow for more twisters!"),
    10: ("Day ten! Five friends ran a race. Use the clues to find the finishing order.",
         "Kiran, Omar, Noor, Maya, Leo! Follow for more twisters!"),
}

# ---------------- voice ----------------
_k = None
def tts(text, speed):
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro("/home/claude/tts_models/kokoro-v1.0.onnx", "/home/claude/tts_models/voices-v1.0.bin")
    a, sr = _k.create(text, voice=VOICE, speed=speed, lang="en-us")
    # resample 24k -> 44.1k
    n = int(len(a) * SR / sr)
    a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    # trim silence
    idx = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, idx[0] - 400): idx[-1] + 2000] if len(idx) else a

def plan(day):
    qa, qc = SCRIPT[day]
    speed = SPEED
    while True:
        va, vc = tts(qa, speed), tts(qc, speed)
        da, dc = len(va) / SR, len(vc) / SR
        A = max(4.0, 0.3 + da + 0.6)
        C = TOTAL - A - 3.0
        if C >= dc + 0.6 or speed > 1.35:
            return dict(va=va, vc=vc, A=A, C=C, speed=speed)
        speed += 0.06

# ---------------- music & sfx ----------------
def note(freq, dur, kind="pluck"):
    t = np.arange(int(dur * SR)) / SR
    if kind == "pluck":
        w = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.1 * np.sin(6 * np.pi * freq * t)
        env = np.exp(-t * 7) * np.minimum(1, t * 400)
    elif kind == "bass":
        w = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(4 * np.pi * freq * t)
        env = np.exp(-t * 3.5) * np.minimum(1, t * 200)
    else:  # bell
        w = np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 6)
        env = np.exp(-t * 3) * np.minimum(1, t * 800)
    return (w * env).astype(np.float32)

def add(buf, x, at):
    i = int(at * SR)
    j = min(len(buf), i + len(x))
    if i < len(buf):
        buf[i:j] += x[: j - i]

def music(day):
    bpm = 108
    beat = 60 / bpm
    root = 261.63 * 2 ** ([0, 2, -3, 5, -1, 3, -2, 4, 1, -4][(day - 1) % 10] / 12)
    prog = [(0, 4, 7), (7, 11, 14), (9, 12, 16), (5, 9, 12)]  # I V vi IV
    buf = np.zeros(int((TOTAL + 1) * SR), np.float32)
    rng = np.random.default_rng(day)
    t, bar = 0.0, 0
    while t < TOTAL:
        ch = prog[bar % 4]
        tones = [root * 2 ** (s / 12) for s in ch] + [root * 2 ** ((ch[0] + 12) / 12)]
        for b in range(4):
            add(buf, 0.5 * note(root * 2 ** ((ch[0] - 24) / 12), beat * 0.95, "bass"), t + b * beat)
            for s in range(4):
                f = tones[[0, 1, 2, 3, 2, 1, 3, 2][(b * 4 + s) % 8]]
                add(buf, 0.22 * note(f, beat, "pluck"), t + b * beat + s * beat / 4)
            # soft hat on offbeat
            hat = rng.standard_normal(int(0.03 * SR)).astype(np.float32) * np.exp(-np.arange(int(0.03 * SR)) / SR * 150)
            hat = np.diff(hat, prepend=0)
            add(buf, 0.05 * hat, t + b * beat + beat / 2)
        t += 4 * beat; bar += 1
    return buf

def tick():
    t = np.arange(int(0.08 * SR)) / SR
    return (np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 60)).astype(np.float32)

def mix(day, p):
    n = int(TOTAL * SR)
    m = music(day)[:n]
    m = m / np.max(np.abs(m)) * 0.30
    vo = np.zeros(n, np.float32)
    add(vo, p["va"], 0.3)
    reveal = p["A"] + 3.0
    add(vo, p["vc"], reveal + 0.15)
    # ducking envelope
    env = np.abs(vo)
    k = int(0.15 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    duck = 1 - 0.7 * np.clip(env / 0.02, 0, 1)
    sfx = np.zeros(n, np.float32)
    for s in range(3):
        add(sfx, 0.35 * tick(), p["A"] + s)
    add(sfx, 0.25 * (note(880, 1.2, "bell") + note(1320, 1.2, "bell")), reveal - 0.3)
    out = m * duck + vo / max(1e-6, np.max(np.abs(vo))) * 0.85 + sfx
    # fade out last 0.6s
    f = int(0.6 * SR); out[-f:] *= np.linspace(1, 0, f)
    out = out / max(1.0, np.max(np.abs(out)) / 0.95)
    path = f"{TMP}/day{day:02d}_mix.wav"
    sf.write(path, out, SR)
    return path

# ---------------- frames ----------------
def band_canvas(slide, accent, top_fn, bottom_text):
    img = Image.new("RGB", (RW, RH), R.INK)
    d = ImageDraw.Draw(img)
    img.paste(slide, (0, 300))
    d.rectangle([RW - 270, 300 + 1170, RW - 50, 300 + 1245], fill=R.BG)  # hide carousel pill
    top_fn(d, accent)
    R.ctext(d, RW / 2, 1785, bottom_text, R.font(R.BOLD, 40), R.WHITE)
    return img

def frames(day, p_data, brand, plan_):
    p = p_data
    accent = R.ACCENTS[(day - 1) % len(R.ACCENTS)]
    puzzle = R.slide_puzzle(brand, p, accent)
    answer = R.slide_answer(brand, p, accent)
    paths = []

    def top_q(d, a):
        R.ctext(d, RW / 2, 120, "CAN YOU", R.font(R.BOLD, 56), R.WHITE)
        R.ctext(d, RW / 2, 200, "SOLVE IT?", R.font(R.BOLD, 84), a)
    img = band_canvas(puzzle, accent, top_q, "PUZZLE TWISTER  ·  DAY %02d" % day)
    paths.append(f"{TMP}/day{day:02d}_0.png"); img.save(paths[-1])

    for i, n in enumerate([3, 2, 1]):
        def top_c(d, a, n=n):
            d.text((90, 120), "THINK", font=R.font(R.BOLD, 70), fill=R.WHITE)
            d.text((90, 190), "FAST!", font=R.font(R.BOLD, 70), fill=a)
            d.ellipse([RW - 330, 50, RW - 90, 290], fill=a, outline=R.WHITE, width=8)
            R.ctext(d, RW - 210, 172, str(n), R.font(R.BOLD, 150), R.WHITE)
        img = band_canvas(puzzle, accent, top_c, "COMMENT YOUR ANSWER")
        paths.append(f"{TMP}/day{day:02d}_{i + 1}.png"); img.save(paths[-1])

    def top_a(d, a):
        R.ctext(d, RW / 2, 165, "ANSWER!", R.font(R.BOLD, 120), a)
    img = band_canvas(answer, accent, top_a, "FOLLOW FOR A NEW TWISTER DAILY")
    paths.append(f"{TMP}/day{day:02d}_4.png"); img.save(paths[-1])
    return paths

def encode(day, imgs, audio, pl):
    A, C = pl["A"], pl["C"]
    durs = [A, 1, 1, 1, C + 0.3]
    accent = R.ACCENTS[(day - 1) % len(R.ACCENTS)]
    hexc = "0x%02x%02x%02x" % accent
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for im in imgs:
        cmd += ["-framerate", str(FPS), "-i", im]
    cmd += ["-i", audio, "-f", "lavfi", "-i", f"color=c={hexc}:s={RW}x14:r={FPS}"]
    fc = []
    for i, dur in enumerate(durs):
        fc.append(f"[{i}]format=yuv420p,loop=-1:1,trim=duration={dur:.3f},setpts=PTS-STARTPTS,fps=30,settb=1/30[v{i}]")
    fc.append("[v0][v1][v2][v3]concat=n=4:v=1:a=0,fps=30,settb=1/30[pre]")
    fc.append(f"[pre][v4]xfade=transition=fade:duration=0.3:offset={A + 3 - 0.3:.3f}[vid]")
    fc.append(f"[vid][6]overlay=x='-w+w*t/{TOTAL}':y=0:shortest=1,format=yuv420p[outv]")
    tmp = f"{OUT}/.day{day:02d}_tmp.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "5:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), "-movflags", "+faststart", tmp]
    subprocess.run(cmd, check=True)
    final = f"{OUT}/puzzle_twister_day{day:02d}_reel.mp4"
    os.replace(tmp, final)
    return final

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    days = [int(x) for x in sys.argv[2:]] or list(range(1, 11))
    data = json.load(open("/home/claude/puzzles/puzzles.json"))
    brand = data["brand"]
    for day in days:
        p = data["puzzles"][day - 1]
        pl = plan(day)
        imgs = frames(day, p, brand, pl)
        print(f"day {day}: A={pl['A']:.2f}s C={pl['C']:.2f}s vo_c={len(pl['vc'])/SR:.2f}s speed={pl['speed']:.2f}")
        if mode == "all":
            audio = mix(day, pl)
            print(" ->", encode(day, imgs, audio, pl))

if __name__ == "__main__":
    main()
