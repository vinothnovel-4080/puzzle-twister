# Puzzle Twister: source code

Everything runs on GitHub. Nothing needs to be installed on your computer.

| File | What it does |
|---|---|
| `puzzles.json` | All 10 puzzles: question, clues, hint, answer, explanation, bonus, captions and hashtags. Edit this to make a new batch. |
| `verify.py` | Checks by brute force that every answer is right and each logic puzzle has exactly one solution. |
| `render.py` | Draws the 1080x1350 Instagram carousel slides (puzzle, hint, answer) into `out/day_XX/`. |
| `reels.py` | Shared helpers for reels: English voiceover (Kokoro TTS), generated background music, sound effects. |
| `reels2.py` | Builds the 15-second vertical reels: yesterday's answer, then today's puzzle, a 3-2-1 countdown and "Answer tomorrow". |
| `post_reel.py` | Posts the day's reel to Instagram through the Graph API (create container, wait, publish). |
| `.github/workflows/build-reels.yml` | **Build reels**: makes all 11 reels and the slides, then publishes them on GitHub Pages. Runs when puzzles or scripts change, or by hand. |
| `.github/workflows/post-reel.yml` | **Post reel to Instagram**: runs every day at 8:00 am IST and posts that day's reel. Can also be run by hand for any day. |

## One-time setup (on github.com)

1. **Turn on Pages:** Settings → Pages → *Build and deployment* → Source: **GitHub Actions**.
2. **Add the Instagram secrets:** Settings → Secrets and variables → Actions → *Secrets* tab → New repository secret:
   - `INSTAGRAM_ACCESS_TOKEN`: long-lived token with `instagram_basic` + `instagram_content_publish`
   - `IG_USER_ID`: numeric Instagram Business Account ID
3. **Set the start date (optional):** same page, *Variables* tab → New repository variable `START_DATE` = the date of Day 1, e.g. `2026-11-24`. Without it, Day 1 is 2026-11-22.
   - Optional variable `GRAPH_BASE` = `https://graph.instagram.com/v24.0` if your token comes from *Instagram Login* rather than Facebook Login.
4. **Build the reels:** Actions → *Build reels* → Run workflow. Takes about 10-15 minutes. The reels then appear at
   `https://vinothnovel-4080.github.io/puzzle-twister/`.
5. **Test the post:** Actions → *Post reel to Instagram* → Run workflow, tick *dry run*. Check the log shows the right day, video link and caption.

## Daily posting
Every day around 8:00 am IST (7:47, with backups at 8:17 and 9:47 in case GitHub starts late) the **Post reel to Instagram** workflow:
1. Records the **proof** (day, video link, caption, hashtags) on the run's summary page and checks the token.
2. Posts that day's reel automatically, unless it is already on Instagram. The log ends with the Instagram link.

If a run fails, GitHub emails you; re-run that day from Actions → *Post reel to Instagram* → *Run workflow*.
Captions use at most 5 hashtags (Instagram's current limit) and put the search keywords in the first line.

## Posting a day by hand
Actions → *Post reel to Instagram* → Run workflow → enter the day (1-11; 11 = Day 10 answer reel).

## Running on your own computer (optional)
```
pip install pillow numpy soundfile kokoro-onnx   # plus ffmpeg
# put kokoro-v1.0.onnx and voices-v1.0.bin in models/, Poppins fonts in a folder and set FONT_DIR
python verify.py
python render.py
python reels2.py all
```
