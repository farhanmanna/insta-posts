"""Render a carousel in the @learnenglishsentences style.
Usage: python3 make_carousel.py posts.json outdir
posts.json: {"slides": [{"hindi": "...", "english": "..."}, ...]}
"""
import sys, json, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "baloo-2-latin-%d-normal.woff")
def font(w, s): return ImageFont.truetype(FD % w, s)

TEAL, CREAM, WHITE = (18, 100, 110), (240, 236, 222), (255, 255, 255)
W = H = 1080
SPLIT = 560

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    return lines

def fit(d, text, weight, start, maxw, maxlines):
    s = start
    while s > 40:
        f = font(weight, s)
        ls = wrap(d, text, f, maxw)
        if len(ls) <= maxlines: return f, ls, s
        s -= 4
    return f, ls, s

def centered(d, lines, f, size, cy, fill):
    lh = int(size * 1.18)
    y = cy - lh * len(lines) // 2
    for ln in lines:
        d.text((W // 2 - d.textlength(ln, font=f) // 2, y), ln, font=f, fill=fill)
        y += lh

def slide(hindi, english, idx, total, out, seed):
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    # torn-paper edge
    rnd = random.Random(seed)
    pts, x = [(0, 0), (W, 0)], W
    while x > 0:
        pts.append((x, SPLIT + rnd.randint(-28, 22)))
        x -= rnd.randint(14, 40)
    pts.append((0, SPLIT + rnd.randint(-28, 22)))
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).polygon([(px, py + 8) for px, py in pts], fill=90)
    img.paste((150, 145, 130), mask=shadow.filter(ImageFilter.GaussianBlur(8)))
    d.polygon(pts, fill=TEAL)

    d.text((24, 14), "website: www.englishsentences.in", font=font(700, 34), fill=WHITE)
    s = "Daily use English Sentences"
    d.text((W // 2 - d.textlength(s, font=font(700, 44)) // 2, 92), s, font=font(700, 44), fill=WHITE)
    f, ls, sz = fit(d, hindi, 800, 88, W - 120, 3)
    centered(d, ls, f, sz, 345, WHITE)
    f, ls, sz = fit(d, english, 800, 84, W - 140, 3)
    centered(d, ls, f, sz, 800, TEAL)
    h = "@learnenglishsentences"
    d.text((W // 2 - d.textlength(h, font=font(700, 50)) // 2, H - 92), h, font=font(700, 50), fill=TEAL)
    if total > 1:
        t = f"{idx}/{total}"
        d.text((W - 30 - d.textlength(t, font=font(700, 34)), H - 70), t, font=font(700, 34), fill=(120, 150, 150))
    img.save(out, quality=92)

if __name__ == "__main__":
    data = json.load(open(sys.argv[1])); out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    n = len(data["slides"])
    for i, s in enumerate(data["slides"], 1):
        slide(s["hindi"], s["english"], i, n, os.path.join(out, f"slide{i}.jpg"), seed=i * 7 + len(s["english"]))
