# Puzzle Twister: source code

| File | What it does |
|---|---|
| `puzzles.json` | All 10 puzzles: question, clues, hint, answer, explanation, bonus, captions and hashtags. Edit this to make a new batch. |
| `verify.py` | Checks by brute force that every answer is right and each logic puzzle has exactly one solution. |
| `render.py` | Draws the 1080x1350 Instagram carousel slides (puzzle, hint, answer) into `out/day_XX/`. |
| `reels.py` | Shared helpers for reels: English voiceover (Kokoro TTS), generated background music, sound effects. |
| `reels2.py` | Builds the 15-second vertical reels: yesterday's answer, then today's puzzle, a 3-2-1 countdown and "Answer tomorrow". |
| `post_reel.py` | Posts the day's reel to Instagram through the Graph API (create container, wait, publish). |

## Setup
```
pip install pillow numpy soundfile kokoro-onnx
# ffmpeg must be installed
# Kokoro voice files (put next to the scripts, or edit the paths in reels.py):
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```
The scripts use paths under `/home/claude/...`; change these at the top of each file to match your folders.

## Run
```
python3 verify.py          # check the puzzles
python3 render.py          # carousel slides
python3 reels2.py all      # all 11 reels (day 11 = Day 10 answer reel)
```

## Post to Instagram
```
export INSTAGRAM_ACCESS_TOKEN=...   # instagram_basic + instagram_content_publish
export IG_USER_ID=...               # numeric Instagram Business Account ID
export MEDIA_BASE_URL=https://vinothnovel-4080.github.io/puzzle-twister
python3 post_reel.py --dry-run      # preview today's post
python3 post_reel.py                # publish today's reel
python3 post_reel.py --day 3        # publish a specific day
```
`START_DATE` in `post_reel.py` sets which date is Day 1.
