"""Reply to new comments on the latest Puzzle Twister reels.

Runs every 30 minutes from GitHub Actions. Replies are friendly, vary, and never
say whether an answer is right (the answer is revealed in the next day's reel).
Needs the instagram_manage_comments permission on INSTAGRAM_ACCESS_TOKEN.

Usage:
  python reply_comments.py            # reply to new comments
  python reply_comments.py --dry-run  # only print what it would reply
"""
import os, random, re, sys
from post_reel import graph

REELS_TO_CHECK = 3          # today's reel plus the two before it
MAX_REPLIES_PER_RUN = 30    # stay well inside Instagram's limits

LETTER_REPLIES = [
    "Locked in: {L}! 🔒 Answer drops tomorrow at 8 am.",
    "{L} it is! 🧠 We reveal the answer tomorrow morning.",
    "Got your {L}! 👀 Tag a friend and see if they agree.",
    "{L}, noted! ✅ Come back tomorrow at 8 am for the reveal.",
    "Bold pick: {L}! 🔥 Answer in tomorrow's reel.",
]
OTHER_REPLIES = [
    "Thanks for playing! 🧠 Pick A, B or C, answer tomorrow at 8 am.",
    "Love it! 🙌 What's your pick, A, B or C?",
    "Thanks! 😊 New puzzle every morning at 8, follow so you don't miss it.",
    "Appreciate you! 💛 Tag a friend who'd solve this one.",
]


def pick_letter(text):
    """Find an answer letter like 'B', 'b)', 'option c', 'Answer: A', 'I think C'.
    A lone lowercase 'a' inside a sentence is the English article, not an answer."""
    t = (text or "").strip()
    for pattern, flags in (
        (r"\W*([abc])\W*", re.I),                                    # the whole comment is the letter
        (r"\b(?:option|answer|ans|choice|pick)\s*(?:is)?\s*[:\-]?\s*([abc])\b", re.I),
        (r"(?<![A-Za-z])([ABCabc])\)", 0),                           # "B)" or "c)"
        (r"(?<![A-Za-z'])([BC])(?![A-Za-z'])", 0),                   # a capital B or C on its own
    ):
        m = re.fullmatch(pattern, t, flags) if pattern.startswith(r"\W*") else re.search(pattern, t, flags)
        if m:
            return m.group(1).upper()
    return None


def main():
    dry = "--dry-run" in sys.argv
    ig = os.environ["IG_USER_ID"].strip()
    me = (graph("GET", ig, fields="username").get("username") or "").lower()
    media = graph("GET", f"{ig}/media", fields="id,caption,permalink", limit=REELS_TO_CHECK).get("data", [])
    replied = 0
    for m in media:
        comments = graph("GET", f"{m['id']}/comments",
                         fields="id,text,username,replies{username}", limit=50).get("data", [])
        for c in comments:
            if replied >= MAX_REPLIES_PER_RUN:
                break
            who = (c.get("username") or "").lower()
            if not who or who == me:
                continue  # skip our own comments (like the first comment)
            reply_users = [(r.get("username") or "").lower() for r in c.get("replies", {}).get("data", [])]
            if me in reply_users:
                continue  # already replied
            letter = pick_letter(c.get("text") or "")
            msg = random.choice(LETTER_REPLIES).format(L=letter) if letter else random.choice(OTHER_REPLIES)
            print(f"{m.get('permalink')}  @{c.get('username')}: {c.get('text')!r}  ->  {msg}")
            if not dry:
                graph("POST", f"{c['id']}/replies", message=msg)
            replied += 1
    print(f"Replied to {replied} comment(s)." if not dry else f"Would reply to {replied} comment(s).")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code in (None, 0):
            raise
        # Most likely the token lacks instagram_manage_comments. Warn instead of failing,
        # so GitHub doesn't email a failure every 30 minutes.
        print(f"::warning::Could not reply to comments: {e}")
        print("Add the instagram_manage_comments permission to the token, then update the secret.")
