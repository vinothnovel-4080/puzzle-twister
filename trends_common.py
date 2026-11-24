"""Shared helpers for the trend series (stdlib only, so the posting job needs no installs)."""
import datetime, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

LABEL = {
    "emoji_word": "Emoji puzzle",
    "odd_grid": "Find the odd one",
    "math": "Quick maths",
    "matchstick": "Matchstick puzzle",
    "riddle": "Riddle",
}
HASHTAGS = {
    "emoji_word": ["#puzzletwister", "#emojipuzzle", "#guesstheword", "#emojiquiz", "#brainteaser"],
    "odd_grid": ["#puzzletwister", "#findtheoddone", "#spotthedifference", "#visualpuzzle", "#brainteaser"],
    "math": ["#puzzletwister", "#mathpuzzle", "#quickmaths", "#mathchallenge", "#brainteaser"],
    "matchstick": ["#puzzletwister", "#matchstickpuzzle", "#mathpuzzle", "#logicpuzzle", "#brainteaser"],
    "riddle": ["#puzzletwister", "#riddle", "#riddles", "#logicpuzzle", "#brainteaser"],
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
    if p["kind"] == "emoji_word":
        return p["answer"]
    if p["kind"] == "odd_grid":
        return f"row {p['odd_row']}, column {p['odd_col']}"
    i = "ABC".index(p["answer_letter"])
    return f"{p['answer_letter']}) {p['choices'][i]}"


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
    elif k == "matchstick":
        head = (f"Matchstick puzzle #{n} 🔥 Move just ONE matchstick to fix it!\n\n"
                f"{p['expr'].replace('+', ' + ').replace('-', ' − ').replace('=', ' = ')} ❌\n\n{opts}")
        ask = "💬 Comment A, B or C. Found another answer? Tell us!\n📤 Send this to a friend who loves a challenge.\n"
    else:
        head = f"Riddle #{n} 🤔 Think before you answer!\n\n{p['question']}\n\n{opts}"
        ask = "💬 Comment A, B or C. Answer tomorrow!\n📤 Send this to someone who loves riddles.\n"
    prev = find(data, p["day"] - 1, p["slot"])
    reveal = f"✅ Yesterday's answer: {answer_text(prev)}\n\n" if prev else ""
    return head + reveal + ask + FOLLOW + "\n\n" + " ".join(HASHTAGS[k])
