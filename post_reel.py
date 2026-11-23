"""Publish today's Puzzle Twister reel to Instagram via the Graph API.

Env vars:
  INSTAGRAM_ACCESS_TOKEN   long-lived token with instagram_basic + instagram_content_publish
  IG_USER_ID               Instagram Business Account ID
  MEDIA_BASE_URL           public base URL where reels/ is hosted, e.g. https://<user>.github.io/puzzle-twister
  GRAPH_BASE               default https://graph.facebook.com/v24.0
                           (use https://graph.instagram.com/v24.0 for Instagram-Login tokens)
Usage:
  python3 post_reel.py              # picks the day from START_DATE (IST)
  python3 post_reel.py --day 3      # force a day (11 = Day 10 answer reel)
  python3 post_reel.py --dry-run    # print what would be posted
"""
import json, os, sys, time, datetime, urllib.parse, urllib.request

# Day 1, posted 8:00 am IST. Override with the START_DATE env var (YYYY-MM-DD),
# which the GitHub workflow reads from the repository variable of the same name.
START_DATE = datetime.date.fromisoformat(os.environ.get("START_DATE") or "2026-11-22")
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
HERE = os.path.dirname(os.path.abspath(__file__))


def graph(method, path, **params):
    base = os.environ.get("GRAPH_BASE", "https://graph.facebook.com/v24.0")
    # Tolerate stray spaces, line breaks or quotes from pasting the secret.
    params["access_token"] = os.environ["INSTAGRAM_ACCESS_TOKEN"].strip().strip("'\"").strip()
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(f"{base}/{path}?{data.decode()}")
    else:
        req = urllib.request.Request(f"{base}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Graph API error {e.code}: {e.read().decode()[:500]}")


def post_for_day(day):
    d = json.load(open(os.path.join(HERE, "puzzles.json"), encoding="utf-8"))
    if day == 11:
        caption = d["finale_caption"] + " ".join(d["finale_hashtags"])
        video = "puzzle_twister_day10_answer_reel.mp4"
    else:
        p = d["puzzles"][day - 1]
        caption = p["reel_caption"] + " ".join(p["reel_hashtags"])
        video = f"puzzle_twister_day{day:02d}_reel.mp4"
    return caption, f"{os.environ.get('MEDIA_BASE_URL', '<MEDIA_BASE_URL>').rstrip('/')}/reels/{video}"


def main():
    args = sys.argv[1:]
    if "--day" in args:
        day = int(args[args.index("--day") + 1])
    else:
        day = (datetime.datetime.now(IST).date() - START_DATE).days + 1
    if not 1 <= day <= 11:
        print(f"No post scheduled (day {day}). Series runs {START_DATE} for 11 days.")
        return
    caption, url = post_for_day(day)
    print(f"Day {day}\nVideo: {url}\nCaption:\n{caption}\n")
    if "--dry-run" in args:
        # Read-only check that the token and account ID work (posts nothing).
        if os.environ.get("INSTAGRAM_ACCESS_TOKEN") and os.environ.get("IG_USER_ID"):
            t = os.environ["INSTAGRAM_ACCESS_TOKEN"].strip().strip("'\"").strip()
            # Safe hint only: Instagram-Login tokens start with "IG", Facebook ones with "EAA".
            print(f"Token starts with '{t[:3]}', {len(t)} characters. API: {os.environ.get('GRAPH_BASE', 'graph.facebook.com (default)')}")
            try:
                acct = graph("GET", os.environ["IG_USER_ID"].strip(), fields="username")
                print(f"Token OK. Will post as @{acct.get('username')}")
            except SystemExit as e:
                print(f"IG_USER_ID check failed: {e}")
                # Instagram-Login tokens: the account the token belongs to.
                if "graph.instagram.com" in os.environ.get("GRAPH_BASE", ""):
                    try:
                        me = graph("GET", "me", fields="user_id,username")
                        print(f"  Token belongs to @{me.get('username')}  IG_USER_ID = {me.get('user_id')}")
                    except SystemExit as e2:
                        print(f"  Could not read the token's account: {e2}")
                    raise SystemExit("Set the IG_USER_ID secret to the Instagram account ID shown above.")
                # Facebook-Login tokens: list the Instagram business accounts linked to your Pages.
                try:
                    pages = graph("GET", "me/accounts", fields="name,instagram_business_account{id,username}")
                    found = [p for p in pages.get("data", []) if p.get("instagram_business_account")]
                    for p in found:
                        ig = p["instagram_business_account"]
                        print(f"  Page '{p.get('name')}' -> Instagram @{ig.get('username')}  IG_USER_ID = {ig['id']}")
                    if not found:
                        print("  No Instagram business account is linked to a Facebook Page this token can see.")
                except SystemExit as e2:
                    print(f"  Could not list linked accounts: {e2}")
                raise SystemExit("Set the IG_USER_ID secret to the Instagram account ID shown above.")
        else:
            print("Token or IG_USER_ID not set; skipped the account check.")
        return
    # Instagram must be able to download the video, so check the link first.
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            print(f"Video reachable ({r.status}, {r.headers.get('Content-Length')} bytes)")
    except Exception as e:
        raise SystemExit(f"Video URL not reachable: {url} ({e}). Run the 'Build reels' workflow first.")
    ig = os.environ["IG_USER_ID"].strip()
    c = graph("POST", f"{ig}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true")
    cid = c["id"]
    for _ in range(60):  # up to ~10 min for Instagram to process the video
        s = graph("GET", cid, fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise SystemExit(f"Instagram could not process the video: {s}")
        time.sleep(10)
    else:
        raise SystemExit("Timed out waiting for Instagram to process the video.")
    r = graph("POST", f"{ig}/media_publish", creation_id=cid)
    link = graph("GET", r["id"], fields="permalink").get("permalink")
    print(f"Published! Media id {r['id']}  {link}")


if __name__ == "__main__":
    main()
