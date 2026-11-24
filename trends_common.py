"""Shared helpers for the trend series (stdlib only, so the posting job needs no installs)."""
import datetime, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

LABEL = {
    "emoji_word": "Emoji puzzle",
    "odd_grid": "Find the odd one",
    "math": "Quick maths",
    "riddle": "Riddle",
    "stroop": "Brain test",
    "first_word": "First word",
    "spot_diff": "Spot the difference",
    "count_emoji": "Count challenge",
    "memory": "Memory test",
}
HASHTAGS = {
    "emoji_word": ["#puzzletwister", "#emojipuzzle", "#guesstheword", "#emojiquiz", "#brainteaser"],
    "odd_grid": ["#puzzletwister", "#findtheoddone", "#spotthedifference", "#visualpuzzle", "#brainteaser"],
    "math": ["#puzzletwister", "#mathpuzzle", "#quickmaths", "#mathchallenge", "#brainteaser"],
    "riddle": ["#puzzletwister", "#riddle", "#riddles", "#logicpuzzle", "#brainteaser"],
    "stroop": ["#puzzletwister", "#strooptest", "#braintest", "#mindgames", "#brainteaser"],
    "first_word": ["#puzzletwister", "#personalitytest", "#firstwordyousee", "#wordsearch", "#mindgames"],
    "spot_diff": ["#puzzletwister", "#spotthedifference", "#findthedifference", "#visualpuzzle", "#brainteaser"],
    "count_emoji": ["#puzzletwister", "#countchallenge", "#emojichallenge", "#visualpuzzle", "#brainteaser"],
    "memory": ["#puzzletwister", "#memorytest", "#memorychallenge", "#braintest", "#brainteaser"],
}
FOLLOW = "🔔 Follow @puzzledaily_123 for new puzzles every day."


def load():
    with open(os.path.join(HERE, "trends.json"), encoding="utf-8") as f:
        return json.load(f)


def start_date(data):
    return datetime.date.fromisoformat(os.environ.get("TREND_START_DATE") or data["start_date"])


def today_day(data):
    return (datetime.datetime.now(IST).date() - start_date(data)).days + 1


def find(data, day, slot):
    for p in data["posts"]:
        if p["day"] == day and p["slot"] == slot:
            return p
    return None


def has_options(p):
    return bool(p.get("choices"))


def answer_text(p):
    k = p["kind"]
    if k == "emoji_word":
        return p["answer"]
    if k == "odd_grid":
        return f"row {p['odd_row']}, column {p['odd_col']}"
    if k == "stroop":
        return "it's the Stroop effect: your brain reads the word before it names the colour"
    if k == "first_word":
        return " · ".join(f"{w} = {m}" for w, m in p["meanings"]) + " (just for fun 😄)"
    if k == "spot_diff":
        return f"{p['diffs']} differences"
    if k == "count_emoji":
        return f"{p['count']} {p['target']}"
    i = "ABC".index(p["answer_letter"])
    return f"{p['answer_letter']}) {p['choices'][i]}"


def short_answer(p):
    """A version short enough for the reel's title screen."""
    k = p["kind"]
    if k == "stroop":
        return "the Stroop effect"
    if k == "first_word":
        return "meanings in the caption"
    if k == "count_emoji":
        return f"{p['count']}"
    return answer_text(p)


def file_stem(p):
    return f"trend_d{p['day']:02d}_s{p['slot']}"


def caption(data, p):
    """Final caption text, hashtags included. The first line is unique (it carries #id),
    which the duplicate check relies on."""
    k, n = p["kind"], p["id"]
    opts = ""
    if has_options(p):
        opts = "\n".join(f"👉 {l}) {c}" for l, c in zip("ABC", p["choices"])) + "\n\n"
    if k == "emoji_word":
        head = f"Emoji puzzle #{n} 🧩 Guess the word from these emojis!\n\n{p['caption_emojis']} = ?\n\n"
        ask = "💬 Type the word in the comments. Answer tomorrow!\n📤 Send this to the friend who always guesses first.\n"
    elif k == "odd_grid":
        head = f"Find the odd one #{n} 👀 Can you spot it in 10 seconds?\n\nOne {p['name']} in this grid is different.\n\n"
        ask = "💬 Comment the row and column (like 2, 5). Answer tomorrow!\n📤 Send this to a friend with sharp eyes.\n"
    elif k == "math":
        head = f"Quick maths #{n} 🧮 Most people get this wrong at first!\n\n{p['expr'].replace('-', '−')}\n\n{opts}"
        ask = "💬 Comment A, B or C. Answer tomorrow!\n📤 Send this to the friend who says they're good at maths.\n"
    elif k == "stroop":
        head = (f"Brain test #{n} 🧠 Say the COLOUR, not the word!\n\n"
                "Read the colours out loud as fast as you can. Your brain wants to read the word, "
                "so it's harder than it looks.\n\n")
        ask = "💬 How many seconds did it take you? Comment your time ⏱️\n📤 Send this to a friend and race them!\n"
    elif k == "first_word":
        head = (f"Personality test #{n} 🔤 What's the first word you see?\n\n"
                "The first word you spot is said to show what you want most right now (just for fun 😄)\n\n")
        ask = "💬 Comment the first word you saw! Meanings tomorrow.\n📤 Send this to a friend and see if they spot the same one.\n"
    elif k == "spot_diff":
        head = f"Spot the difference #{n} 🔍 How many differences can you find?\n\nCompare grid A and grid B. Some emojis have changed!\n\n"
        ask = "💬 Comment how many you found. Answer tomorrow!\n📤 Send this to a friend with sharp eyes.\n"
    elif k == "count_emoji":
        head = f"Count challenge #{n} 👀 How many {p['target_emoji']} can you count in 10 seconds?\n\nCareful, some look very similar!\n\n"
        ask = "💬 Comment your number. Answer tomorrow!\n📤 Send this to a friend and compare counts.\n"
    elif k == "memory":
        head = (f"Memory test #{n} 🧠 Look for 5 seconds, then answer!\n\n"
                f"The grid disappears. {p['question']}\n\n{opts}")
        ask = "💬 Comment A, B or C. Answer tomorrow!\n📤 Send this to a friend and test their memory.\n"
    else:
        head = f"Riddle #{n} 🤔 Think before you answer!\n\n{p['question']}\n\n{opts}"
        ask = "💬 Comment A, B or C. Answer tomorrow!\n📤 Send this to someone who loves riddles.\n"
    ask = p.get("ask", ask)  # per-post override, e.g. when the reveal isn't the next day
    prev = find(data, p["day"] - 1, p["slot"])
    reveal = ""
    if prev:
        label = "Yesterday's meanings" if prev["kind"] == "first_word" else (
            "Why yesterday's test was hard" if prev["kind"] == "stroop" else "Yesterday's answer")
        reveal = f"✅ {label}: {answer_text(prev)}\n\n"
    return head + reveal + ask + FOLLOW + "\n\n" + " ".join(HASHTAGS[k])
