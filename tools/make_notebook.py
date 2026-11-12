"""Render a notebook-page style carousel (handwritten look) for phrasal verbs / idioms.
Usage: python3 make_notebook.py content.json outdir

content.json:
{"handle": "phrasalidiomatics", "theme": "...",
 "pages": [{"title": "Give up",
            "meaning": "to stop trying to do something",
            "synonym": "quit, stop",
            "examples": ["Never give up on your dreams.", "He gave up smoking last year."],
            "tip": ["Give up -> quit", "Don't give up -> keep going"]}]}
In "tip" lines, "->" is drawn as a hand-drawn arrow.
"""
import sys, json, os, math, random
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
def font(name, size): return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
K4 = lambda s: font("kalam-latin-400-normal.woff", s)
K7 = lambda s: font("kalam-latin-700-normal.woff", s)

W, H = 1080, 1350
PAPER = (246, 243, 234)
RULE = (178, 192, 214)
RED = (206, 46, 46)
BLUE = (34, 64, 168)
GREEN = (24, 128, 60)
PURPLE = (124, 52, 190)
GREY = (120, 128, 150)
LEFT = 150            # text starts right of the margin
RIGHT = W - 60
LH = 66               # ruled line spacing
TOP = 150             # first ruled line

def wobble_line(d, p1, p2, fill, width, rnd, amp=1.6, steps=24):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        n = rnd.uniform(-amp, amp) if 0 < i < steps else 0
        if abs(p2[0] - p1[0]) > abs(p2[1] - p1[1]): y += n
        else: x += n
        pts.append((x, y))
    d.line(pts, fill=fill, width=width, joint="curve")

def hand_ellipse(d, box, fill, width, rnd):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    pts = []
    start = rnd.uniform(0, math.pi * 2)
    for i in range(80):
        a = start + i / 72 * math.pi * 2          # a little overlap, like a pen loop
        k = 1 + rnd.uniform(-0.025, 0.025)
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    d.line(pts, fill=fill, width=width, joint="curve")

def star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)

def arrow(d, x0, y, x1, fill, rnd, width=4):
    wobble_line(d, (x0, y), (x1, y), fill, width, rnd, amp=1.2, steps=10)
    d.line([(x1 - 16, y - 10), (x1, y), (x1 - 16, y + 10)], fill=fill, width=width, joint="curve")

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    return lines

def on_line(n):  # y for text sitting on ruled line n (0-based)
    return TOP + n * LH - 58

def cloud(img, box, fill, rnd):
    """Scalloped cloud outline: outline of the union of bumps and an inner box."""
    from PIL import ImageFilter, ImageChops
    x0, y0, x1, y1 = box
    m = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(m)
    md.rounded_rectangle((x0, y0, x1, y1), 30, fill=255)
    r = 34
    def bumps(ax, ay, bx, by):
        n = max(2, int(math.hypot(bx - ax, by - ay) // 62))
        for i in range(n + 1):
            t = i / n
            cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
            rr = r + rnd.uniform(-4, 5)
            md.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=255)
    bumps(x0, y0, x1, y0); bumps(x1, y0, x1, y1); bumps(x1, y1, x0, y1); bumps(x0, y1, x0, y0)
    outer = m.filter(ImageFilter.MaxFilter(7))
    edge = ImageChops.subtract(outer, m)
    img.paste(fill, mask=edge)

def page(p, idx, total, handle, out, seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # ruled lines
    y = TOP
    while y < H - 20:
        d.line([(0, y), (W, y)], fill=RULE, width=2); y += LH
    # top double red line and left double margin
    d.line([(0, 70), (W, 70)], fill=(226, 120, 120), width=2)
    d.line([(0, 78), (W, 78)], fill=(226, 120, 120), width=2)
    d.line([(108, 0), (108, H)], fill=(226, 120, 120), width=2)
    d.line([(116, 0), (116, H)], fill=(226, 120, 120), width=2)
    d.rectangle((W - 230, 0, W - 40, 40), outline=(226, 120, 120), width=2)

    # title on line 1, centered with double underline
    tf = K7(78)
    title = p["title"]
    while d.textlength(title, font=tf) > RIGHT - LEFT and tf.size > 44:
        tf = K7(tf.size - 4)
    tw = d.textlength(title, font=tf)
    tx = LEFT + (RIGHT - LEFT - tw) / 2
    d.text((tx, on_line(1) - 14), title, font=tf, fill=RED)
    uy = TOP + LH + 6
    wobble_line(d, (tx - 6, uy), (tx + tw + 10, uy), RED, 4, rnd)
    wobble_line(d, (tx + 10, uy + 9), (tx + tw - 4, uy + 9), RED, 3, rnd)

    ln = 3
    bf = K4(48)
    # circled "Meaning"
    lab = "Meaning"
    lf = K7(46)
    lw = d.textlength(lab, font=lf)
    d.text((LEFT + 14, on_line(ln) + 2), lab, font=lf, fill=RED)
    hand_ellipse(d, (LEFT - 6, TOP + (ln - 1) * LH + 4, LEFT + lw + 34, TOP + ln * LH + 4), RED, 3, rnd)
    ln += 1
    for row in wrap(d, p["meaning"], bf, RIGHT - LEFT - 10):
        d.text((LEFT, on_line(ln)), row, font=bf, fill=BLUE); ln += 1
    # optional green-star line: English synonym (or Hindi meaning if a channel uses it)
    extra = None
    if p.get("synonym"): extra = ("Synonym:", p["synonym"])
    elif p.get("hindi"): extra = ("Hindi:", p["hindi"])
    if extra:
        lab2, val = extra
        star(d, LEFT + 16, TOP + ln * LH - 26, 17, GREEN)
        hrows = wrap(d, lab2 + " " + val, bf, RIGHT - LEFT - 60)
        for i, row in enumerate(hrows):
            d.text((LEFT + 44, on_line(ln)), row, font=bf, fill=GREEN)
            if i == 0:
                hw = d.textlength(lab2, font=bf)
                wobble_line(d, (LEFT + 44, TOP + ln * LH - 6), (LEFT + 44 + hw, TOP + ln * LH - 6), GREEN, 3, rnd)
            ln += 1
    ln += 1
    # circled "Examples"
    lab = "Examples"
    lw = d.textlength(lab, font=lf)
    d.text((LEFT + 14, on_line(ln) + 2), lab, font=lf, fill=RED)
    hand_ellipse(d, (LEFT - 6, TOP + (ln - 1) * LH + 4, LEFT + lw + 34, TOP + ln * LH + 4), RED, 3, rnd)
    ln += 1
    for ex in p["examples"]:
        rows = wrap(d, ex, bf, RIGHT - LEFT - 80)
        arrow(d, LEFT - 30, TOP + ln * LH - 28, LEFT + 40, BLUE, rnd, width=3)
        for row in rows:
            d.text((LEFT + 60, on_line(ln)), row, font=bf, fill=(20, 20, 30)); ln += 1

    # tip cloud at the bottom
    tips = p.get("tip") or []
    if tips:
        ln += 1
        tf2 = K4(46)
        rows = len(tips) + 1
        cy0 = TOP + (ln - 1) * LH + 20
        cy1 = min(cy0 + rows * LH + 70, H - 90)
        cloud(img, (LEFT + 10, cy0 + 20, RIGHT - 50, cy1 - 10), RED, rnd)
        ty = cy0 + 30
        d.text((LEFT + 40, ty), "Tip:", font=K7(48), fill=RED)
        wobble_line(d, (LEFT + 40, ty + 62), (LEFT + 40 + d.textlength("Tip:", font=K7(48)), ty + 62), RED, 3, rnd)
        ty += LH + 4
        for t in tips:
            if "->" in t:
                a, b = [s.strip() for s in t.split("->", 1)]
                d.text((LEFT + 60, ty), a, font=tf2, fill=BLUE)
                ax = LEFT + 70 + d.textlength(a, font=tf2)
                arrow(d, ax, ty + 36, ax + 80, PURPLE, rnd)
                bx = ax + 100
                d.text((bx, ty), b, font=tf2, fill=BLUE)
                wobble_line(d, (bx, ty + 64), (bx + d.textlength(b, font=tf2), ty + 64), GREEN, 3, rnd)
            else:
                d.text((LEFT + 60, ty), t, font=tf2, fill=BLUE)
            ty += LH

    # footer
    hf = font("patrick-hand-latin-400-normal.woff", 40)
    h = "@" + handle
    d.text((RIGHT - d.textlength(h, font=hf), H - 66), h, font=hf, fill=GREY)
    if total > 1:
        d.text((LEFT, H - 66), f"{idx}/{total}", font=hf, fill=GREY)
    img.save(out, quality=92)

if __name__ == "__main__":
    data = json.load(open(sys.argv[1])); out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    pages = data["pages"]
    for i, p in enumerate(pages, 1):
        page(p, i, len(pages), data.get("handle", "phrasalidiomatics"),
             os.path.join(out, f"slide{i}.jpg"), seed=i * 13 + len(p["title"]))
