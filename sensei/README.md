# Sensei Series: anime-style teacher reels (sub-project of Puzzle Twister)

Short vertical reels where an **original** anime-style teacher explains one school concept in
30-45 seconds, with clean exam-style graphics, ending with "Save this for your test".
Separate from the daily puzzle posts: nothing here is scheduled or posted until we decide.

## The format we're borrowing (and what we're not)
Reference: an Instagram account where an anime character teaches "What is Matter?" with simple
graphics (mass shown with boxes on scales, space shown with a grid, 5 exam-ready definitions,
and a teaser for the next class). Students in the comments ask for more subjects.

| Keep (the format) | Don't copy |
|---|---|
| Anime-style teacher presenting graphics | Existing characters (Gojo or any anime/brand character), their names, looks or catchphrases |
| One concept per reel, explained with visual analogies | Show names, logos, music or art from any anime |
| Exam-ready definitions on screen + "save for your test" | |
| A teaser for the next lesson (builds a series and followers) | |

Our characters are designed from scratch, so the account owns them and can grow a following around them.

## Characters (proposal, pick one or the duo)
| | Look | Personality | Voice |
|---|---|---|---|
| **Kai Sensei** | Young man, spiky dark-teal hair, orange hoodie under an open white lab coat, headphones round his neck | High-energy, jokes, hypes the student up | Kokoro male US voice (am_puck / am_michael) |
| **Mira Sensei** | Young woman, purple bob, round glasses, cream cardigan, holds a pointer | Calm, witty, the clear explainer | Saved voice **Emma** (US) or **Priya** (Indian) |
| **Kai & Mira duo** | Both | Kai gets it wrong, Mira explains, quick banter | Two voices |

The duo should engage best: banter keeps people watching and gives viewers someone to side with.

## How each reel is made (free, runs on GitHub like the puzzle posts)
1. **Character sheet (once):** 8-10 images of each character in the same style, one per pose or
   expression (explaining, pointing, surprised, thumbs-up, thinking, laughing), each with two mouth
   shapes (open and closed), on a plain background. Made once with an AI image tool using
   the prompts in `characters/prompts.md`; saved in `characters/`.
2. **Script:** one concept, a hook, 2-3 visual analogies, the exam definition, a teaser for the next lesson.
3. **Voice:** a saved voice (`voices.py`) reads the script.
4. **Animation:** our renderer switches poses on cue, flaps the mouth with the voice, adds
   bounce, zooms, speed lines and flashes (anime-style energy), and draws the lesson graphics
   (diagrams, scales, grids, definition cards), reusing the Brain Bites graphics engine.
5. **Output:** vertical reel + cover + caption, previewed before anything is posted.

## Episode ideas (Class 8-10 science and maths, exam-friendly)
1. What is Matter? (mass + space, 3 states)
2. Speed vs velocity
3. Photosynthesis in 30 seconds
4. Why is the sky blue?
5. Atoms, molecules, compounds
6. Pythagoras theorem with pizza
7. Mass vs weight
8. Acids and bases

## Folders
- `characters/`: character sheets (images) and their prompts
- `episodes/`: one script file per episode
- `out/`: renders (not committed)

## Status
- [x] Sub-project created
- [ ] Choose the character(s)
- [ ] Generate the character sheet
- [ ] Episode 1 script, then a preview render
