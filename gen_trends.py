"""Extend trends.json so there are always DAYS_AHEAD days of trend posts ready.

Rotation (from day 11):
Slot 1: odd-one emoji grid every other day (6x6 -> 7x7 -> 8x8), in between:
        emoji word -> count challenge -> spot the difference
Slot 2: quick maths trap (answer computed, wrong options = common mistakes) <-> memory test
Slot 3: riddle -> riddle -> number sequence -> riddle
        (with PSYCH = True: Stroop test -> riddle -> first word you see -> riddle)
(number sequences fill in once the riddle bank runs out)

Every new post is checked before it is written; any failed check stops the run.
Stdlib only.  Usage: python gen_trends.py [--days-ahead 10]
"""
import json, os, random, sys
import trends_common as T

DAYS_AHEAD = 10
PSYCH = False  # Stroop and "first word you see" in slot 3; on hold for now

# ---- hand-checked banks: (emojis, caption form, answer). Single code points only (no ZWJ). ----
EMOJI_WORDS = [
    (["🧈", "🪰"], "🧈 + 🪰", "BUTTERFLY"), (["🔥", "🪵"], "🔥 + 🪵", "FIREWOOD"),
    (["🌙", "💡"], "🌙 + 💡", "MOONLIGHT"), (["🌞", "🌼"], "🌞 + 🌼", "SUNFLOWER"),
    (["🦶", "⚽"], "🦶 + ⚽", "FOOTBALL"), (["☕", "🎂"], "☕ + 🎂", "CUPCAKE"),
    (["🌧", "🧥"], "🌧️ + 🧥", "RAINCOAT"), (["❄", "⚾"], "❄️ + ⚾", "SNOWBALL"),
    (["🏠", "🪰"], "🏠 + 🪰", "HOUSEFLY"), (["🐄", "👦"], "🐄 + 👦", "COWBOY"),
    (["🌊", "🐚"], "🌊 + 🐚", "SEASHELL"), (["🔑", "🕳"], "🔑 + 🕳️", "KEYHOLE"),
    (["🌞", "👓"], "🌞 + 👓", "SUNGLASSES"), (["🍳", "🎂"], "🍳 + 🎂", "PANCAKE"),
    (["🧠", "🌪"], "🧠 + 🌪️", "BRAINSTORM"), (["🥚", "🌱"], "🥚 + 🌱", "EGGPLANT"),
    (["🐶", "🏠"], "🐶 + 🏠", "DOGHOUSE"), (["🔥", "🪰"], "🔥 + 🪰", "FIREFLY"),
    (["💧", "🍉"], "💧 + 🍉", "WATERMELON"), (["💧", "🍂"], "💧 + 🍂", "WATERFALL"),
    (["🦷", "🖌"], "🦷 + 🖌️", "TOOTHBRUSH"), (["🦷", "🧴"], "🦷 + 🧴", "TOOTHPASTE"),
    (["🧺", "⚽"], "🧺 + ⚽", "BASKETBALL"), (["🎵", "📖"], "🎵 + 📖", "NOTEBOOK"),
    (["🐎", "👞"], "🐎 + 👞", "HORSESHOE"), (["🌧", "💧"], "🌧️ + 💧", "RAINDROP"),
    (["🐱", "🐟"], "🐱 + 🐟", "CATFISH"), (["🌙", "🚶"], "🌙 + 🚶", "MOONWALK"),
    (["⭐", "💡"], "⭐ + 💡", "STARLIGHT"), (["🏖", "🏰"], "🏖️ + 🏰", "SANDCASTLE"),
]
# (question, correct, wrong1, wrong2)
RIDDLES = [
    ("What has keys but can't open locks?", "A piano", "A map", "A door"),
    ("What gets wetter the more it dries?", "A towel", "A sponge", "Rain"),
    ("What has hands but can't clap?", "A clock", "A glove", "A statue"),
    ("I'm tall when I'm young and short when I'm old. What am I?", "A candle", "A tree", "A pencil"),
    ("What has a neck but no head?", "A bottle", "A shirt", "A guitar"),
    ("What can you catch but not throw?", "A cold", "A ball", "A fish"),
    ("What goes up but never comes down?", "Your age", "A balloon", "Smoke"),
    ("What has many teeth but can't bite?", "A comb", "A saw", "A zip"),
    ("What has one eye but can't see?", "A needle", "A potato", "A storm"),
    ("The more you take, the more you leave behind. What are they?", "Footsteps", "Photos", "Breaths"),
    ("If you share me, you don't have me any more. What am I?", "A secret", "A sweet", "A joke"),
    ("What is full of holes but still holds water?", "A sponge", "A net", "A bucket"),
    ("What travels around the world but stays in a corner?", "A stamp", "A map", "A spider"),
    ("What has words but never speaks?", "A book", "A radio", "A parrot"),
    ("A rooster lays an egg on a roof. Which way does it roll?", "Roosters don't lay eggs", "Left", "Right"),
    ("How many times can you subtract 5 from 25?", "Once", "5 times", "4 times"),
    ("What comes once in a minute, twice in a moment, but never in a thousand years?", "The letter M", "A second", "The letter E"),
    ("There are 3 apples and you take away 2. How many apples do you have?", "2", "1", "3"),
    ("What has legs but doesn't walk?", "A table", "A snake", "A fish"),
    ("What runs but never walks?", "Water", "A clock", "A car"),
    ("Which building has the most stories?", "A library", "A skyscraper", "A hotel"),
    ("What is always in front of you but can't be seen?", "The future", "Air", "Your nose"),
    ("What can you break without touching it?", "A promise", "Glass", "A record"),
    ("Which is heavier: 1 kg of cotton or 1 kg of iron?", "Both weigh the same", "Iron", "Cotton"),
    ("Some months have 31 days. How many months have at least 30 days?", "11", "7", "12"),
    ("Which word is spelled wrong in every dictionary?", "Wrong", "Dictionary", "Spelled"),
    ("What has a thumb and four fingers but isn't alive?", "A glove", "A hand", "A fork"),
    ("What can fill a room but takes up no space?", "Light", "Air", "Water"),
    ("What has a head and a tail but no body?", "A coin", "A snake", "A comet"),
    ("What gets bigger the more you take away from it?", "A hole", "A cake", "A shadow"),
]
# Odd-one grids are emoji only (the smiley grid is our best post), using pairs that are hard to tell apart.
GRID_PAIRS = [
    ("😀", "😃", True, "face"), ("😁", "😄", True, "face"), ("😐", "😑", True, "face"),
    ("😮", "😯", True, "face"), ("😗", "😙", True, "face"), ("😊", "🙂", True, "face"),
    ("😢", "😥", True, "face"), ("😺", "😸", True, "cat"), ("🕐", "🕑", True, "clock"),
    ("⭐", "🌟", True, "star"), ("🌕", "🌝", True, "moon"), ("😴", "😪", True, "face"),
]
GRID_SIZES = [6, 7, 8]  # grids get harder: 6x6, 7x7, 8x8, then round again


COLOURS = ["RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE"]
# (word, meaning) sets for "first word you see" - shown as "just for fun"
WORD_SETS = [
    [("LOVE", "close relationships matter most right now"), ("MONEY", "you're focused on security and goals"),
     ("PEACE", "you need rest and calm"), ("TRAVEL", "you want adventure")],
    [("HOME", "comfort and family matter most"), ("FAME", "you want your work to be noticed"),
     ("FUN", "you need more play in your life"), ("CALM", "you're craving a quiet moment")],
    [("HOPE", "you're looking forward to something big"), ("POWER", "you want more control over your life"),
     ("FRIEND", "you value the people around you"), ("DREAM", "you're thinking about your goals")],
    [("SMILE", "you want more happy moments"), ("GOAL", "you're driven and focused"),
     ("FREEDOM", "you want more space to be yourself"), ("FAMILY", "the people closest to you come first")],
    [("CHANGE", "you're ready for something new"), ("REST", "you need a proper break"),
     ("WIN", "you love a challenge"), ("TRUST", "honesty matters most to you")],
]
SPOT_POOLS = [["🍎", "🍌", "🍇", "🍓", "🍊", "🍉"], ["🐶", "🐱", "🐰", "🐼", "🦊", "🐸"],
              ["⚽", "🏀", "🎾", "🏐", "🏈", "🎱"], ["🚗", "🚕", "🚌", "🚓", "🚑", "🚒"],
              ["🌸", "🌻", "🌹", "🌷", "🌼", "🌺"]]
# (target, name, look-alikes)
COUNT_SETS = [("🐱", "cats", ["🐯", "🦁"]), ("🍎", "apples", ["🍅", "🍒"]), ("⭐", "stars", ["🌟", "✨"]),
              ("🐶", "dogs", ["🐺", "🦊"]), ("🐟", "fish", ["🐠", "🐡"]), ("🌸", "flowers", ["🌺", "🌼"])]
MEMORY_POOL = ["🍎", "🐶", "⚽", "🚗", "🌙", "🎈", "🍕", "🐸", "⭐", "🎁", "🦋", "🍦", "🚀", "🐢", "🌈", "🎸", "🍩", "🐝"]
MEMORY_Q = [(4, "Which emoji was in the CENTRE?"), (0, "Which emoji was in the TOP-LEFT corner?"),
            (8, "Which emoji was in the BOTTOM-RIGHT corner?"), (2, "Which emoji was in the TOP-RIGHT corner?")]


def make_stroop(rng):
    words = []
    for _ in range(12):
        w = rng.choice(COLOURS)
        ink = rng.choice([c for c in COLOURS if c != w])
        words.append([w, ink])
    return {"kind": "stroop", "words": words}


def make_first_word(rng, used_sets):
    free = [s for s in WORD_SETS if s[0][0] not in used_sets] or WORD_SETS
    ws = rng.choice(free)
    for _ in range(200):
        g = [[None] * 9 for _ in range(9)]
        ok = True
        for word, _m in ws:
            placed = False
            for _ in range(100):
                way = rng.choice("hv")
                r = rng.randint(0, 8 if way == "h" else 9 - len(word))
                c = rng.randint(0, 9 - len(word) if way == "h" else 8)
                cells = [(r, c + k) if way == "h" else (r + k, c) for k in range(len(word))]
                if all(g[a][b] is None for a, b in cells):  # no overlaps at all, keeps words clean
                    for (a, b), ch in zip(cells, word):
                        g[a][b] = ch
                    placed = True
                    break
            if not placed:
                ok = False
                break
        if ok:
            filler = "BCDFGHJKMNPQSVWXZ"  # no vowels: avoids accidental extra words
            grid = ["".join(ch or rng.choice(filler) for ch in row) for row in g]
            return {"kind": "first_word", "grid": grid, "meanings": [list(x) for x in ws]}
    raise SystemExit("could not place first-word grid")


def make_spot_diff(rng):
    pool = rng.choice(SPOT_POOLS)
    left = [rng.choice(pool) for _ in range(16)]
    right = list(left)
    diffs = rng.randint(3, 5)
    for i in rng.sample(range(16), diffs):
        right[i] = rng.choice([e for e in pool if e != left[i]])
    return {"kind": "spot_diff", "left": left, "right": right, "diffs": diffs}


def make_count(rng):
    target, name, alikes = rng.choice(COUNT_SETS)
    count = rng.randint(9, 14)
    cells = [target] * count + [rng.choice(alikes) for _ in range(42 - count)]
    rng.shuffle(cells)
    return {"kind": "count_emoji", "cells": cells, "count": count, "target": name, "target_emoji": target}


def make_memory(rng):
    grid = rng.sample(MEMORY_POOL, 9)
    pos, q = rng.choice(MEMORY_Q)
    right = grid[pos]
    wrong = rng.sample([e for i, e in enumerate(grid) if i != pos], 2)
    opts = [right] + wrong
    rng.shuffle(opts)
    return {"kind": "memory", "grid": grid, "question": q, "choices": opts, "answer_letter": "ABC"[opts.index(right)]}


def ev(expr):
    """Evaluate with normal precedence (× and ÷ before + and -)."""
    return eval(expr.replace("×", "*").replace("÷", "/").replace("= ?", ""))


def left_to_right(expr):
    """The classic mistake: work strictly left to right."""
    toks = expr.replace("= ?", "").split()
    val = float(toks[0])
    for op, n in zip(toks[1::2], toks[2::2]):
        n = float(n)
        val = {"+": val + n, "-": val - n, "×": val * n, "÷": val / n}[op]
    return val


def make_math(rng):
    for _ in range(500):
        t = rng.choice(["a - b × c + d", "a + b × c", "a + b × c - d", "a - b ÷ c", "a ÷ b × c", "a + b ÷ c × d", "a × b - c × d"])
        a, b, c, d = (rng.randint(2, 12) for _ in range(4))
        if "÷" in t:  # make divisions exact
            if "b ÷ c" in t:
                b = c * rng.randint(2, 6)
            if "a ÷ b" in t:
                a = b * rng.randint(2, 6)
        expr = t.replace("a", str(a)).replace("b", str(b)).replace("c", str(c)).replace("d", str(d)) + " = ?"
        right, wrong = ev(expr), left_to_right(expr)
        if right != int(right) or right < 0 or wrong != int(wrong) or wrong == right:
            continue
        right, wrong = int(right), int(wrong)
        third = right + rng.choice([-2, -1, 1, 2, 3])
        if third in (right, wrong) or third < 0:
            continue
        opts = [str(right), str(wrong), str(third)]
        rng.shuffle(opts)
        return {"kind": "math", "expr": expr, "choices": opts, "answer_letter": "ABC"[opts.index(str(right))]}
    raise SystemExit("could not generate a maths puzzle")


def make_sequence(rng):
    kind = rng.choice(["square", "double", "grow", "triangle"])
    s = rng.randint(1, 4)
    if kind == "square":
        seq = [(s + i) ** 2 for i in range(6)]
    elif kind == "double":
        seq = [s * 2 ** i for i in range(6)]
    elif kind == "grow":
        step = rng.randint(1, 3)
        seq = [s]
        for i in range(5):
            seq.append(seq[-1] + step + i)
    else:
        seq = [(s + i) * (s + i + 1) // 2 for i in range(6)]
    nxt, shown = seq[-1], seq[:-1]
    diff = shown[-1] - shown[-2]
    wrongs = list(dict.fromkeys([shown[-1] + diff, nxt + 1, nxt - 2, nxt + 2]))
    wrongs = [w for w in wrongs if w != nxt and w > 0][:2]
    opts = [str(nxt)] + [str(w) for w in wrongs]
    rng.shuffle(opts)
    q = "What comes next? " + ", ".join(map(str, shown)) + ", ..."
    return {"kind": "riddle", "question": q, "choices": opts, "answer_letter": "ABC"[opts.index(str(nxt))]}


def check(p):
    k = p["kind"]
    assert k in T.LABEL, k
    if k == "emoji_word":
        assert p["answer"].isalpha() and len(p["emojis"]) >= 2
    if k == "odd_grid":
        assert 1 <= p["odd_row"] <= p["rows"] and 1 <= p["odd_col"] <= p["cols"] and p["base"] != p["odd"]
    if k in ("math", "riddle"):
        assert len(p["choices"]) == 3 and len(set(p["choices"])) == 3 and p["answer_letter"] in "ABC"
    if k == "math":
        right = ev(p["expr"])
        assert str(int(right)) == p["choices"]["ABC".index(p["answer_letter"])], p
    if k == "stroop":
        assert len(p["words"]) == 12 and all(w != ink for w, ink in p["words"])
    if k == "first_word":
        rows = p["grid"]
        cols = ["".join(r[c] for r in rows) for c in range(9)]
        for w, _m in p["meanings"]:
            assert any(w in line for line in rows + cols), w
    if k == "spot_diff":
        assert sum(a != b for a, b in zip(p["left"], p["right"])) == p["diffs"]
    if k == "count_emoji":
        assert p["cells"].count(p["target_emoji"]) == p["count"] and len(p["cells"]) == 42
    if k == "memory":
        pos = {"CENTRE": 4, "TOP-LEFT": 0, "BOTTOM-RIGHT": 8, "TOP-RIGHT": 2}
        idx = next(v for key, v in pos.items() if key in p["question"])
        assert p["grid"][idx] == p["choices"]["ABC".index(p["answer_letter"])]
        assert len(set(p["choices"])) == 3
    T.caption({"posts": []}, p)  # caption must build


def main():
    ahead = int(sys.argv[sys.argv.index("--days-ahead") + 1]) if "--days-ahead" in sys.argv else DAYS_AHEAD
    path = os.path.join(T.HERE, "trends.json")
    data = T.load()
    posts = data["posts"]
    last_day = max(p["day"] for p in posts)
    target = max(T.today_day(data), 0) + ahead
    used_words = {p.get("answer") for p in posts if p["kind"] == "emoji_word"}
    used_q = {p.get("question") for p in posts if p["kind"] == "riddle"}
    used_expr = {p.get("expr") for p in posts if p["kind"] == "math"}
    used_grid = [(p["base"], p["odd"]) for p in posts if p["kind"] == "odd_grid"]
    grids = [p["rows"] for p in posts if p["kind"] == "odd_grid"]
    n_grid = [GRID_SIZES.index(grids[-1]) + 1 if grids and grids[-1] in GRID_SIZES else 0]  # next size up
    next_id = max(p["id"] for p in posts) + 1
    added = []
    used_sets = {p["meanings"][0][0] for p in posts if p["kind"] == "first_word"}

    def emoji_word(rng):
        free = [w for w in EMOJI_WORDS if w[2] not in used_words] or EMOJI_WORDS
        emojis, cap, ans = rng.choice(free)
        used_words.add(ans)
        return {"kind": "emoji_word", "emojis": emojis, "caption_emojis": cap, "answer": ans}

    def odd_grid(rng):
        # prefer pairs never used; once all are used, avoid the most recent ones
        free_g = [g for g in GRID_PAIRS if (g[0], g[1]) not in used_grid] or \
                 [g for g in GRID_PAIRS if (g[0], g[1]) not in used_grid[-6:]]
        base, odd, is_emoji, name = rng.choice(free_g)
        used_grid.append((base, odd))
        n = GRID_SIZES[n_grid[0] % len(GRID_SIZES)]
        n_grid[0] += 1
        return {"kind": "odd_grid", "base": base, "odd": odd, "emoji": is_emoji, "name": name,
                "rows": n, "cols": n, "odd_row": rng.randint(1, n), "odd_col": rng.randint(1, n)}

    def math_trap(rng):
        for _ in range(20):
            p = make_math(rng)
            if p["expr"] not in used_expr:
                break
        used_expr.add(p["expr"])
        return p

    def riddle(rng):
        free_r = [r for r in RIDDLES if r[0] not in used_q]
        if not free_r:
            return make_sequence(rng)
        q, right, w1, w2 = rng.choice(free_r)
        used_q.add(q)
        opts = [right, w1, w2]
        rng.shuffle(opts)
        return {"kind": "riddle", "question": q, "choices": opts, "answer_letter": "ABC"[opts.index(right)]}

    def first_word(rng):
        p = make_first_word(rng, used_sets)
        used_sets.add(p["meanings"][0][0])
        return p

    # Rotation from day 11 (5 Dec): interactive formats in every slot.
    # Slot 1: an odd-one grid every other day, with the other visual puzzles in between.
    S1 = [emoji_word, odd_grid, make_count, odd_grid, make_spot_diff, odd_grid]
    S2 = [math_trap, make_memory]
    # Psychology formats (Stroop, first word) are on hold: set PSYCH = True to bring them back.
    S3 = [make_stroop, riddle, first_word, riddle] if PSYCH else [riddle, riddle, make_sequence, riddle]
    for day in range(last_day + 1, target + 1):
        rng = random.Random(f"puzzle-twister-{day}")
        i = day - 11
        p1 = S1[i % len(S1)](rng)
        p2 = S2[i % 2](rng)
        p3 = S3[i % 4](rng)
        for slot, p in ((1, p1), (2, p2), (3, p3)):
            p = {"id": next_id, "day": day, "slot": slot, **p}
            if p.get("choices"):  # rotate the right answer through A, B, C so there's no pattern
                ch, right = p["choices"], "ABC".index(p["answer_letter"])
                want = next_id % 3
                ch[right], ch[want] = ch[want], ch[right]
                p["answer_letter"] = "ABC"[want]
            next_id += 1
            check(p)
            added.append(p)
    if not added:
        print(f"Nothing to add: days up to {last_day} are already planned (target {target}).")
        return
    posts.extend(added)
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(data))
    print(f"Added {len(added)} posts for days {added[0]['day']}-{added[-1]['day']}:")
    for p in added:
        print(f"  #{p['id']} day {p['day']} slot {p['slot']} {p['kind']}: {T.answer_text(p)}")


def dump(data):
    """trends.json layout: one post per line."""
    lines = ['{', f'  "start_date": {json.dumps(data["start_date"])},',
             f'  "slots": {json.dumps(data["slots"], ensure_ascii=False)},', '  "posts": [']
    rows = [json.dumps(p, ensure_ascii=False) for p in data["posts"]]
    lines.append(",\n".join("    " + r for r in rows))
    lines += ['  ]', '}', '']
    return "\n".join(lines)


if __name__ == "__main__":
    main()
