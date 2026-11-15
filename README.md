# insta-posts

Images for the automated daily Instagram carousel on @learnenglishsentences (scheduled through Metricool).

- `posts/YYYY-MM-DD/` – the 5 slides (`slide1.jpg` … `slide5.jpg`) and `content.json` for that day's post
- `tools/make_carousel.py` – renders slides in the house style: `python3 tools/make_carousel.py posts/DATE/content.json posts/DATE`
- `used_sentences.json` – log of every theme and sentence already posted, so nothing repeats

`content.json` format:

```json
{"theme": "Feelings & emotions",
 "slides": [{"hindi": "Mujhe tum par garv hai", "english": "I'm proud of you."}]}
```

## Question slide (from 15 Nov 2026)
Every new carousel ends with a 6th "Your turn!" question slide (see `question_slide` in `channels.json`).
- `make_carousel.py`: add `"question": {"hindi": "...", "prompt": "How do you say this in English?"}`
- `make_notebook.py` / `make_studynote.py`: append a page `{"type": "question", "title": "...", "question": "...", "options": [...], "cta": "..."}`

Reels are switched off (see `reels` in `channels.json`).
