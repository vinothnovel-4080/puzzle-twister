"""Post one trend-series reel (trends.json) to Instagram. Stdlib only.

Usage:
  python post_trend.py --slot 2               # today's post for slot 2
  python post_trend.py --day 3 --slot 1       # a specific post
  python post_trend.py --slot 2 --dry-run     # proof only (checks token, posts nothing)
  python post_trend.py --which-day            # prints today's series day (0 = outside the series)
Env: INSTAGRAM_ACCESS_TOKEN, IG_USER_ID, MEDIA_BASE_URL, TREND_START_DATE (optional).
"""
import os, sys, time
import trends_common as T
from post_reel import graph, reachable


def arg(name, default=None):
    a = sys.argv[1:]
    return a[a.index(name) + 1] if name in a else default


def main():
    data = T.load()
    last = max(p["day"] for p in data["posts"])
    day = int(arg("--day") or T.today_day(data))
    if "--which-day" in sys.argv:
        print(day if 1 <= day <= last else 0)
        return
    slot = int(arg("--slot") or os.environ.get("SLOT") or 0)
    p = T.find(data, day, slot)
    if not p:
        print(f"No trend post for day {day}, slot {slot} (series runs {T.start_date(data)} for {last} days).")
        return
    base = os.environ.get("MEDIA_BASE_URL", "<MEDIA_BASE_URL>").rstrip("/")
    stem = T.file_stem(p)
    url, cover = f"{base}/trend/{stem}.mp4", f"{base}/trend/{stem}_cover.jpg"
    caption = T.caption(data, p)
    print(f"Trend #{p['id']} · day {day} · slot {slot} · {T.LABEL[p['kind']]}\nVideo: {url}\nCover: {cover}\nCaption:\n{caption}\n")

    ig = os.environ["IG_USER_ID"].strip()
    if "--dry-run" in sys.argv:
        acct = graph("GET", ig, fields="username")
        print(f"Token OK. Will post as @{acct.get('username')}")
        return
    if not reachable(url):
        raise SystemExit(f"Video URL not reachable: {url}. Run the 'Build reels' workflow first.")
    first_line = caption.split("\n")[0].strip()
    if "--force" not in sys.argv:
        for m in graph("GET", f"{ig}/media", fields="caption,permalink", limit=25).get("data", []):
            if (m.get("caption") or "").strip().startswith(first_line):
                print(f"Already posted: {m.get('permalink')}")
                return
    extra = {"cover_url": cover} if reachable(cover) else {}
    c = graph("POST", f"{ig}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true", **extra)
    for _ in range(60):
        s = graph("GET", c["id"], fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise SystemExit(f"Instagram could not process the video: {s}")
        time.sleep(10)
    else:
        raise SystemExit("Timed out waiting for Instagram to process the video.")
    r = graph("POST", f"{ig}/media_publish", creation_id=c["id"])
    print(f"Published! Media id {r['id']}  {graph('GET', r['id'], fields='permalink').get('permalink')}")


if __name__ == "__main__":
    main()
