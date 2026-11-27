"""Post a Brain Bites episode to Instagram (reel with cover, then the cover as a Story).

Files (on GitHub Pages, published by "Build reels"):
  brainbites/<slug>.mp4, brainbites/<slug>_cover.jpg, brainbites/<slug>.txt (caption)
Waits for the video link to go live first (Pages deploys a few minutes after a push),
and skips a post whose caption is already on Instagram.

Usage: python post_brainbites.py <slug> [--dry-run] [--wait-minutes 30]
Env:   INSTAGRAM_ACCESS_TOKEN, IG_USER_ID, MEDIA_BASE_URL
"""
import os, sys, time
import post_reel as P

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    args = sys.argv[1:]
    slug = args[0]
    wait = int(args[args.index("--wait-minutes") + 1]) if "--wait-minutes" in args else 30
    base = os.environ["MEDIA_BASE_URL"].rstrip("/") + "/brainbites"
    url, cover = f"{base}/{slug}.mp4", f"{base}/{slug}_cover.jpg"
    caption = open(os.path.join(HERE, "brainbites", f"{slug}.txt"), encoding="utf-8").read().strip()
    print(f"Episode: {slug}\nVideo: {url}\nCover: {cover}\nCaption:\n{caption}\n")
    if "--dry-run" in args:
        acct = P.graph("GET", os.environ["IG_USER_ID"].strip(), fields="username")
        print(f"Token OK. Will post as @{acct.get('username')}")
        return

    for i in range(wait * 2):  # Pages can take a few minutes to publish a new file
        if P.reachable(url):
            break
        if i == 0:
            print("Waiting for the video to go live on GitHub Pages...")
        time.sleep(30)
    else:
        raise SystemExit(f"Video not reachable after {wait} minutes: {url}")
    print("Video reachable.")

    ig = os.environ["IG_USER_ID"].strip()
    first_line = caption.split("\n")[0].strip()
    for m in P.graph("GET", f"{ig}/media", fields="caption,permalink", limit=20).get("data", []):
        if (m.get("caption") or "").strip().startswith(first_line):
            print(f"Already posted: {m.get('permalink')}")
            return

    extra = {"cover_url": cover} if P.reachable(cover) else {}
    c = P.graph("POST", f"{ig}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true", **extra)
    for _ in range(60):  # up to ~10 min for Instagram to process the video
        s = P.graph("GET", c["id"], fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise SystemExit(f"Instagram could not process the video: {s}")
        time.sleep(10)
    else:
        raise SystemExit("Timed out waiting for Instagram to process the video.")
    r = P.graph("POST", f"{ig}/media_publish", creation_id=c["id"])
    link = P.graph("GET", r["id"], fields="permalink").get("permalink")
    print(f"Published! Media id {r['id']}  {link}")
    P.after_post(ig, r["id"], 99, cover)  # day 99: no first comment, just the Story


if __name__ == "__main__":
    main()
