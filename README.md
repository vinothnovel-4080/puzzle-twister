# Puzzle Twister: source code

Everything runs on GitHub. Nothing needs to be installed on your computer.

| File | What it does |
|---|---|
| `puzzles.json` | All 10 puzzles: question, clues, hint, answer, A/B/C choices, explanation, bonus, captions and hashtags. Edit this to make a new batch. |
| `verify.py` | Checks by brute force that every answer is right and each logic puzzle has exactly one solution. |
| `render.py` | Draws the 1080x1350 Instagram carousel slides (puzzle, hint, answer) into `out/day_XX/`. |
| `reels.py` | Shared helpers for reels: English voiceover (Kokoro TTS), generated background music, sound effects. |
| `reels2.py` | Builds the 15-second vertical reels: yesterday's answer, then today's puzzle, a 3-2-1 countdown with the A/B/C options and "Answer tomorrow". |
| `post_reel.py` | Posts the day's reel with its cover, then posts the cover as a Story. |
| `reply_comments.py` | Replies to new comments on the latest reels, without giving the answer away. |
| `.github/workflows/reply-comments.yml` | **Reply to comments**: runs `reply_comments.py` (switched off for now; run by hand). |
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

## Daily posting: the Scheduler
GitHub's built-in cron drops runs, so posting is done by one always-on **Scheduler** workflow
(`scheduler.py`). It stays awake for ~5h40m, checks every 5 minutes what is due, then starts its
next run; an hourly trigger restarts it if a run is ever lost.

| What | Window (IST) | Runs |
|---|---|---|
| Planned reel | 7:47 am – 12:00 pm | `post_reel.py` (reel, cover, Story) |
| Trend slot 1 | 12:47 – 5:00 pm | `post_trend.py --slot 1` |
| Trend slot 2 | 5:47 – 8:30 pm | `post_trend.py --slot 2` |
| Trend slot 3 | 8:47 – 11:59 pm | `post_trend.py --slot 3` |
| Token check | 5:47 – 7:30 am | once a day |
| Planner | 12:30 – 5:00 am | `gen_trends.py`, commit, start **Build reels** |

A post is retried every 5 minutes until it succeeds (or is found already on Instagram). If something
is still missing when its window closes, the run fails and GitHub emails you. To post by hand, use
Actions → *Post reel to Instagram* or *Post trend puzzle* → *Run workflow*.
Captions use at most 5 hashtags (Instagram's current limit) and put the search keywords in the first line.

## Interaction
- Every puzzle has A/B/C options, in the caption and on the reel's countdown and end screens.
- Right after posting, the script posts the cover as a Story
  (set the repository variable `POST_STORY` to `false` to stop the Story).
- **Switched off for now:** an automatic first comment ("Your answer? Comment A, B or C 👇") and
  **Reply to comments**, which answers new comments with a friendly reply that never gives the answer away.
  Both need the comments permission on the token. To turn them on: set the repository variable
  `POST_FIRST_COMMENT` to `true`, and add the schedule shown at the top of `reply-comments.yml`.
- Quiz stickers can't be added through the API: to use one, share the reel to your Story in the app.

## Trend series (3 extra posts a day)
`trends.json` holds the trend puzzles, posted alongside the planned reel. It keeps itself topped up (see below):

| Slot | Time (IST) | Styles | Answers |
|---|---|---|---|
| 1 | 12:47 pm | Odd-one emoji grid every other day (6x6 → 7x7 → 8x8, ~9 s loop) · emoji word, count, spot the difference | Typed in the comments, no options |
| 2 | 5:47 pm | Quick maths | A/B/C, shown when the countdown reaches 3 |
| 3 | 8:47 pm | Riddle · logic | A/B/C, shown when the countdown reaches 3 |

- `trend.py` renders each reel (title, 10 s countdown with timer bar, end card), cover and caption into `trend/` on Pages.
- `post_trend.py` + **Post trend puzzle** workflow post them, retrying every 10 minutes for about 80 minutes after each slot.
- Day 1 is `start_date` in `trends.json` (or the repository variable `TREND_START_DATE`).
- Each caption reveals the previous day's answer for the same slot.
- Builds only render yesterday's, today's and upcoming posts (set `TREND_BUILD_ALL=1` to render everything).

### Keeping the series going
**Plan trend puzzles** runs every Sunday night (or by hand) and runs `gen_trends.py`, which adds days so about
10 are always planned, commits `trends.json` and starts **Build reels**:
- quick maths traps are generated; the right answer is calculated and wrong options come from common mistakes
- odd-one grids are generated with a random position
- emoji words and riddles come from hand-checked banks in `gen_trends.py`, never repeating;
  every third day slot 3 is a generated number sequence instead
- every new post is checked (answers, options, caption) before it is saved; a failed check stops the run

### Token health check
**Token health check** runs daily at 5:47 am IST and fails (GitHub emails you) if the Instagram token stops
working, two hours before the first post.

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
