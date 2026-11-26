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


def token():
    # Tolerate stray spaces, line breaks or quotes from pasting the secret.
    return os.environ["INSTAGRAM_ACCESS_TOKEN"].strip().strip("'\"").strip()


def graph_base():
    # Pick the API from the token type: Instagram-Login tokens start with "IG",
    # Facebook-Login tokens with "EAA". GRAPH_BASE is only used for other tokens.
    t = token()
    if t.startswith("IG"):
        return "https://graph.instagram.com/v24.0"
    if t.startswith("EAA"):
        return "https://graph.facebook.com/v24.0"
    return os.environ.get("GRAPH_BASE") or "https://graph.facebook.com/v24.0"


def graph(method, path, **params):
    base = graph_base()
    params["access_token"] = token()
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


def token_days_left():
    """Days until the token (or its data access) expires; None if unknown or it never expires."""
    if not token().startswith("EAA"):
        return None
    try:
        info = graph("GET", "debug_token", input_token=token()).get("data", {})
    except SystemExit:
        return None
    ends = [t for t in (info.get("expires_at"), info.get("data_access_expires_at")) if t]
    return None if not ends else (min(ends) - time.time()) / 86400


def post_for_day(day):
    d = json.load(open(os.path.join(HERE, "puzzles.json"), encoding="utf-8"))
    if day == 11:
        caption = d["finale_caption"] + " ".join(d["finale_hashtags"])
        video = "puzzle_twister_day10_answer_reel.mp4"
        cover = "cover_day10_answer.jpg"
    else:
        p = d["puzzles"][day - 1]
        caption = p["reel_caption"] + " ".join(p["reel_hashtags"])
        video = f"puzzle_twister_day{day:02d}_reel.mp4"
        cover = f"cover_day{day:02d}.jpg"
    base = os.environ.get("MEDIA_BASE_URL", "<MEDIA_BASE_URL>").rstrip("/")
    return caption, f"{base}/reels/{video}", f"{base}/covers/{cover}"


def reachable(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    args = sys.argv[1:]
    if "--day" in args:
        day = int(args[args.index("--day") + 1])
    else:
        day = (datetime.datetime.now(IST).date() - START_DATE).days + 1
    if "--which-day" in args:
        print(day if 1 <= day <= 11 else 0)
        return
    if not 1 <= day <= 11:
        print(f"No post scheduled (day {day}). Series runs {START_DATE} for 11 days.")
        return
    caption, url, cover = post_for_day(day)
    print(f"Day {day}\nVideo: {url}\nCover: {cover}\nCaption:\n{caption}\n")
    if "--dry-run" in args:
        # Read-only check that the token and account ID work (posts nothing).
        if os.environ.get("INSTAGRAM_ACCESS_TOKEN") and os.environ.get("IG_USER_ID"):
            t = token()
            # Safe hint only: Instagram-Login tokens start with "IG", Facebook ones with "EAA".
            print(f"Token starts with '{t[:3]}', {len(t)} characters. API: {graph_base()}")
            try:
                acct = graph("GET", os.environ["IG_USER_ID"].strip(), fields="username")
                print(f"Token OK. Will post as @{acct.get('username')}")
                if t.startswith("EAA"):
                    # Facebook tokens can expire in 1 hour; show expiry and permissions.
                    try:
                        info = graph("GET", "debug_token", input_token=t).get("data", {})
                        exp = info.get("data_access_expires_at") if not info.get("expires_at") else info.get("expires_at")
                        when = "never" if not exp else datetime.datetime.fromtimestamp(exp, IST).strftime("%Y-%m-%d %H:%M IST")
                        print(f"Token type {info.get('type')}, expires: {when}")
                        print(f"Permissions: {', '.join(info.get('scopes', []))}")
                        if "instagram_content_publish" not in info.get("scopes", []):
                            print("WARNING: instagram_content_publish permission is missing; posting will fail.")
                    except SystemExit as e2:
                        print(f"Could not read token expiry: {e2}")
            except SystemExit as e:
                print(f"IG_USER_ID check failed: {e}")
                # Instagram-Login tokens: the account the token belongs to.
                if "graph.instagram.com" in graph_base():
                    try:
                        me = graph("GET", "me", fields="user_id,username")
                        print(f"  Token belongs to @{me.get('username')}  IG_USER_ID = {me.get('user_id')}")
                    except SystemExit as e2:
                        print(f"  Could not read the token's account: {e2}")
                    raise SystemExit("Set the IG_USER_ID secret to the Instagram account ID shown above.")
                # Facebook Page token: the Page's own linked Instagram account.
                try:
                    me = graph("GET", "me", fields="name,instagram_business_account{id,username}")
                    ig = me.get("instagram_business_account")
                    if ig:
                        print(f"  Page '{me.get('name')}' -> Instagram @{ig.get('username')}  IG_USER_ID = {ig['id']}")
                        raise SystemExit("Set the IG_USER_ID secret to the Instagram account ID shown above.")
                except SystemExit as e2:
                    if "Set the IG_USER_ID" in str(e2):
                        raise
                # Facebook user token: list the Instagram business accounts linked to your Pages.
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
    # Never post the same day twice (a late scheduled run plus a manual run, or a backup run).
    if "--force" not in args:
        first_line = caption.split("\n")[0].strip()
        recent = graph("GET", f"{ig}/media", fields="caption,permalink", limit=15).get("data", [])
        for m in recent:
            if (m.get("caption") or "").strip().startswith(first_line):
                print(f"Already posted: {m.get('permalink')}  (use --force to post again)")
                return
    extra = {}
    if reachable(cover):
        extra["cover_url"] = cover  # thumbnail for the feed, Reels tab and profile grid
        print(f"Cover reachable: {cover}")
    else:
        print(f"WARNING: cover not reachable ({cover}); Instagram will use the first frame.")
    c = graph("POST", f"{ig}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true", **extra)
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
    after_post(ig, r["id"], day, cover)


FIRST_COMMENT = "Your answer? Comment A, B or C 👇 No peeking at other comments 😉"


def try_graph(what, method, path, **params):
    """Like graph(), but a failure only prints a warning (the reel is already live)."""
    try:
        return graph(method, path, **params)
    except SystemExit as e:
        print(f"WARNING: {what} failed: {e}")
        return None


def after_post(ig, media_id, day, cover):
    # 1. First comment, so the reel never starts with an empty comment section.
    #    Off unless the repository variable POST_FIRST_COMMENT is "true"; needs the
    #    instagram_manage_comments (or instagram_business_manage_comments) permission.
    if (os.environ.get("POST_FIRST_COMMENT", "false").lower() == "true" and day <= 10
            and try_graph("first comment", "POST", f"{media_id}/comments", message=FIRST_COMMENT)):
        print("First comment posted.")
    # 2. The day's cover as a Story, pointing followers at the new reel.
    if os.environ.get("POST_STORY", "true").lower() == "false" or not reachable(cover):
        return
    s = try_graph("story", "POST", f"{ig}/media", media_type="STORIES", image_url=cover)
    if not s:
        return
    for _ in range(30):
        st = try_graph("story status", "GET", s["id"], fields="status_code") or {}
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            print(f"WARNING: Instagram could not process the story: {st}")
            return
        time.sleep(5)
    if try_graph("story publish", "POST", f"{ig}/media_publish", creation_id=s["id"]):
        print("Story posted.")


if __name__ == "__main__":
    main()
