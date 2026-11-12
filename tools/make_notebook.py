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
    ph, amp = rnd.uniform(0, 6.28), min(6, 0.03 * max(rx, ry))
    for i in range(80):
        a = start + i / 72 * math.pi * 2          # a little overlap, like a pen loop
        k = 1 + rnd.uniform(-2.5, 2.5) / max(rx, ry, 1)
        wob = amp * math.sin(3 * a + ph)
        pts.append((cx + (rx * k + wob) * math.cos(a), cy + (ry * k + wob) * math.sin(a)))
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


INK = (20, 20, 30)

# ---------- rich text: *word* = underlined ----------
def plain(t): return t.replace("*", "")

def wrap_rich(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(plain(t), font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    # carry an open underline across line breaks
    out, open_ = [], False
    for ln in lines:
        s = ("*" if open_ else "") + ln
        if s.count("*") % 2: s += "*"; open_ = True
        else: open_ = False
        out.append(s)
    return out

def draw_rich(d, x, y, text, f, fill, rnd, ucolor=None):
    parts = text.split("*")
    for i, part in enumerate(parts):
        if not part: continue
        w = d.textlength(part, font=f)
        d.text((x, y), part, font=f, fill=fill)
        if i % 2 == 1:
            uy = y + f.size * 1.18
            wobble_line(d, (x, uy), (x + w, uy), ucolor or fill, 3, rnd, amp=1.0, steps=8)
        x += w
    return x

def text_block(d, x, ln, text, f, fill, maxw, rnd, ucolor=None):
    for row in wrap_rich(d, text, f, maxw):
        draw_rich(d, x, on_line(ln) + (48 - f.size), row, f, fill, rnd, ucolor); ln += 1
    return ln

# ---------- doodles ----------
def doodle_star(d, cx, cy, rnd, color=PURPLE):
    pts = []
    for i in range(11):
        a = -math.pi / 2 + i * math.pi / 5 + rnd.uniform(-0.05, 0.05)
        rr = 22 if i % 2 == 0 else 10
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.line(pts, fill=color, width=3, joint="curve")
    for k in range(3):   # motion lines
        ox = -30 - k * 3; oy = 22 + k * 8
        d.line([(cx + ox, cy + oy), (cx + ox - 26, cy + oy + 20)], fill=color, width=2)

def check(d, x, y, color=GREEN):
    d.line([(x, y), (x + 12, y + 14), (x + 38, y - 18)], fill=color, width=5, joint="curve")

def curly_arrow(d, x, y, rnd, color=GREEN):
    pts = [(x + 20 * math.cos(a) - 10, y + 22 * math.sin(a)) for a in [i / 12 * math.pi * 1.2 - math.pi / 2 for i in range(13)]]
    d.line(pts, fill=color, width=3, joint="curve")
    ex, ey = pts[-1]
    d.line([(ex - 2, ey - 14), (ex + 6, ey), (ex + 18, ey - 6)], fill=color, width=3)

def circled_label(d, cx, ln, label, rnd, size=50):
    lf = K7(size)
    lw = d.textlength(label, font=lf)
    x = cx - lw / 2
    d.text((x, on_line(ln) - 2), label, font=lf, fill=RED)
    hand_ellipse(d, (x - 22, TOP + (ln - 1) * LH + 2, x + lw + 22, TOP + ln * LH + 6), RED, 3, rnd)
    return x - 22, x + lw + 22

def note_line(d, x, ln, text, f, maxw, rnd):
    star(d, x + 14, TOP + ln * LH - 26, 15, GREEN)
    for row in wrap_rich(d, text, f, maxw - 40):
        w = d.textlength(plain(row), font=f)
        draw_rich(d, x + 38, on_line(ln) + 4, row, f, GREEN, rnd)
        wobble_line(d, (x + 38, TOP + ln * LH - 4), (x + 38 + w, TOP + ln * LH - 4), GREEN, 3, rnd)
        ln += 1
    return ln

# ---------- page ----------
def page(p, idx, total, handle, out, seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = TOP
    while y < H - 20:
        d.line([(0, y), (W, y)], fill=RULE, width=2); y += LH
    d.line([(0, 70), (W, 70)], fill=(226, 120, 120), width=2)
    d.line([(0, 78), (W, 78)], fill=(226, 120, 120), width=2)
    d.line([(108, 0), (108, H)], fill=(226, 120, 120), width=2)
    d.line([(116, 0), (116, H)], fill=(226, 120, 120), width=2)
    d.rectangle((W - 230, 0, W - 40, 40), outline=(226, 120, 120), width=2)

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
    t = p.get("type", "word")
    if t == "compare":
        ln = compare_body(img, d, p, ln, rnd)
    elif t == "three":
        ln = three_body(d, p, ln, rnd)
    else:
        ln = word_body(d, p, ln, rnd)
    tip_and_footer(img, d, p, ln, idx, total, handle, rnd)
    img.save(out, quality=92)

def word_body(d, p, ln, rnd):
    bf = K4(48)
    circled_label(d, LEFT + 100, ln, "Meaning", rnd, 46)
    ln += 1
    ln = text_block(d, LEFT, ln, p["meaning"], bf, BLUE, RIGHT - LEFT - 10, rnd)
    extra = None
    if p.get("synonym"): extra = ("Synonym:", p["synonym"])
    elif p.get("hindi"): extra = ("Hindi:", p["hindi"])
    if extra:
        lab2, val = extra
        star(d, LEFT + 16, TOP + ln * LH - 26, 17, GREEN)
        for i, row in enumerate(wrap(d, lab2 + " " + val, bf, RIGHT - LEFT - 60)):
            d.text((LEFT + 44, on_line(ln)), row, font=bf, fill=GREEN)
            if i == 0:
                hw = d.textlength(lab2, font=bf)
                wobble_line(d, (LEFT + 44, TOP + ln * LH - 6), (LEFT + 44 + hw, TOP + ln * LH - 6), GREEN, 3, rnd)
            ln += 1
    ln += 1
    circled_label(d, LEFT + 110, ln, "Examples", rnd, 46)
    doodle_star(d, LEFT + 290, TOP + (ln - 1) * LH + 10, rnd)
    ln += 1
    for ex in p["examples"]:
        arrow(d, LEFT - 30, TOP + ln * LH - 28, LEFT + 40, BLUE, rnd, width=3)
        ln = text_block(d, LEFT + 60, ln, ex, bf, INK, RIGHT - LEFT - 80, rnd, RED)
    return ln

def column(d, x, ln, c, colw, rnd, f, arrows=True):
    for ex in c["examples"]:
        if arrows:
            arrow(d, x - 4, TOP + ln * LH - 28, x + 30, BLUE, rnd, width=3)
            ln = text_block(d, x + 40, ln, ex, f, INK, colw - 44, rnd, RED)
        else:
            ln = text_block(d, x, ln, ex, f, INK, colw, rnd, RED)
    return ln

def compare_body(img, d, p, ln, rnd):
    layout = p.get("layout", "divider")
    bf = K4(48)
    if p.get("intro"):
        ln = text_block(d, LEFT, ln, p["intro"], bf, BLUE, RIGHT - LEFT - 10, rnd)
        ln += 1
    mid = (LEFT + RIGHT) // 2
    colw = (RIGHT - LEFT) // 2 - 30
    f = K4(42)
    L, R = p["left"], p["right"]
    lx, rx = LEFT - 20, mid + 20
    start = ln

    if layout == "circles":
        r = 160 if colw > 380 else 150
        ends = []
        for c, x0 in ((L, lx), (R, rx)):
            cx = x0 + colw / 2 + 10
            circled_label(d, cx, start + 1, c["label"], rnd, 46)
            e = column(d, x0 + 50, start + 3, c, colw - 110, rnd, K4(38), arrows=False)
            ends.append(e)
        e = max(ends)
        for c, x0 in ((L, lx), (R, rx)):
            hand_ellipse(d, (x0 - 4, TOP + (start - 1) * LH, x0 + colw + 26, TOP + e * LH + 20), PURPLE, 4, rnd)
            doodle_star(d, x0 + colw - 10, TOP + (start - 1) * LH + 6, rnd)
        ln = e + 1
        ends = []
        for c, x0 in ((L, lx), (R, rx)):
            if c.get("note"):
                curly_arrow(d, x0 + 40, TOP + (ln - 1) * LH + 20, rnd)
                ends.append(note_line(d, x0 + 56, ln, c["note"], f, colw, rnd))
        return max(ends) if ends else ln

    if layout == "steps":
        # left = lower step, right = higher step
        hi, lo = start, start + 2
        sx0, sx1, sx2 = LEFT, mid - 60, mid + 60
        yl, ym, yh = TOP + (lo + 1) * LH - 6, TOP + lo * LH - 6, TOP + (hi + 1) * LH - 6
        lf = K7(50)
        d.text((RIGHT - 40 - d.textlength(R["label"], font=lf), on_line(hi + 1) - 8), R["label"], font=lf, fill=RED)
        d.text((LEFT + 40, on_line(lo + 1) - 8), L["label"], font=lf, fill=RED)
        pts = [(sx0, yl), (sx1 - 70, yl), (sx1 - 70, ym), (sx1 + 90, ym), (sx1 + 90, yh), (RIGHT - 20, yh)]
        for a, b in zip(pts, pts[1:]): wobble_line(d, a, b, PURPLE, 5, rnd, amp=1.2, steps=10)
        doodle_star(d, sx1 + 40, TOP + hi * LH + 10, rnd)
        el = column(d, LEFT, lo + 2, L, colw - 10, rnd, f)
        er = column(d, mid + 30, hi + 2, R, colw - 10, rnd, f)
        el = note_line(d, LEFT - 6, el, L["note"], f, colw, rnd) if L.get("note") else el
        er = note_line(d, mid + 30, max(er, hi + 2 + 3), R["note"], f, colw, rnd) if R.get("note") else er
        return max(el, er)

    if layout == "curve":
        # left column starts high, right column lower, joined by an S-shaped double arrow
        circled_label(d, LEFT + 110, start, L["label"], rnd, 48)
        f = K4(40)
        el = column(d, LEFT - 20, start + 1, L, colw - 50, rnd, f)
        el = note_line(d, LEFT - 20, el, L["note"], f, colw - 40, rnd) if L.get("note") else el
        rs = start + 1
        circled_label(d, RIGHT - 150, rs, R["label"], rnd, 48)
        er = column(d, mid + 70, rs + 1, R, colw - 60, rnd, f)
        er = note_line(d, mid + 60, er, R["note"], f, colw - 20, rnd) if R.get("note") else er
        # S-curve
        cx = mid - 10
        y0, y1 = TOP + (start - 1) * LH + 20, TOP + max(el, er - 1) * LH - 30
        pts = []
        for i in range(41):
            tt = i / 40
            yy = y0 + (y1 - y0) * tt
            xx = cx + 70 * math.sin(tt * math.pi * 1.6 + 0.3)
            pts.append((xx, yy))
        for off in (-14, 14):
            d.line([(x + off, y) for x, y in pts], fill=INK, width=3, joint="curve")
        d.line([(x, y) for x, y in pts[2:-4]], fill=PURPLE, width=4, joint="curve")
        ex, ey = pts[-1]
        d.line([(ex - 10, ey - 26), (ex + 30, ey), (ex - 10, ey + 26)], fill=INK, width=4, joint="curve")
        doodle_star(d, cx + 90, y0 + 20, rnd)
        return max(el, er)

    # default: divider
    ends = []
    for c, x0 in ((L, LEFT), (R, mid + 30)):
        circled_label(d, x0 + colw / 2, start, c["label"], rnd)
        e = column(d, x0 - (20 if x0 == LEFT else 0), start + 2, c, colw - 10, rnd, f, arrows=(x0 == LEFT))
        if c.get("note"):
            e = note_line(d, x0 - 10, e, c["note"], f, colw, rnd)
        ends.append(e)
    end = max(ends)
    pts = []
    for i in range(21):
        tt = i / 20
        pts.append((mid + 8 + 10 * math.sin(tt * math.pi) + rnd.uniform(-1, 1), TOP + (start - 1) * LH + 10 + tt * ((end - start + 1) * LH - 20)))
    d.line(pts, fill=PURPLE, width=4, joint="curve")
    return end

def three_body(d, p, ln, rnd):
    """Three columns on a timeline, big -> small dots (e.g. In / On / At)."""
    bf = K4(48)
    if p.get("intro"):
        ln = text_block(d, LEFT, ln, p["intro"], bf, BLUE, RIGHT - LEFT - 10, rnd)
        ln += 1
    cols = p["columns"][:3]
    cw = (RIGHT - LEFT + 40) / 3
    xs = [LEFT - 30 + i * cw for i in range(3)]
    for i, c in enumerate(cols):
        circled_label(d, xs[i] + cw / 2 - 10, ln, c["label"], rnd, 46)
        if i: doodle_star(d, xs[i] + cw / 2 + 95, TOP + (ln - 2) * LH + 30, rnd)
    ln += 1
    ty = TOP + ln * LH - 10
    wobble_line(d, (30, ty), (W - 40, ty), PURPLE, 5, rnd, amp=1.2)
    d.line([(W - 60, ty - 14), (W - 38, ty), (W - 60, ty + 14)], fill=PURPLE, width=5)
    for i, rr in enumerate((44, 26, 12)):
        cx = xs[i] + cw / 2 - 10
        d.ellipse((cx - rr, ty - rr, cx + rr, ty + rr), fill=(150, 90, 210), outline=PURPLE, width=3)
    for i in range(4):  # little clocks
        cx = 60 + i * (W - 120) / 3
        d.ellipse((cx - 14, ty - 58, cx + 14, ty - 30), outline=PURPLE, width=2)
        d.line([(cx, ty - 44), (cx, ty - 54)], fill=PURPLE, width=2)
        d.line([(cx, ty - 44), (cx + 8, ty - 40)], fill=PURPLE, width=2)
    ln += 2
    f = K4(38)
    ends = []
    for i, c in enumerate(cols):
        r = ln
        for ex in c["examples"]:
            arrow(d, xs[i], TOP + r * LH - 24, xs[i] + 26, INK, rnd, width=2)
            r = text_block(d, xs[i] + 32, r, ex, f, INK, cw - 44, rnd, RED)
        ends.append(r)
    ln = max(ends)
    ends = []
    for i, c in enumerate(cols):
        if c.get("note"):
            ends.append(note_line(d, xs[i] - 6, ln, c["note"], K4(38), cw, rnd))
    return max(ends) if ends else ln

def tip_and_footer(img, d, p, ln, idx, total, handle, rnd):
    tips = p.get("tip") or []
    if tips:
        ln += 1
        style = p.get("tip_style", "box")
        head = p.get("tip_title", "Tip:")
        tf2 = K4(46)
        rows = len(tips) + 1
        cy0 = TOP + (ln - 1) * LH + 20
        step = LH
        if cy0 + rows * step + 70 > H - 90:          # not enough room: drop the blank line
            cy0 -= LH
        if cy0 + rows * step + 70 > H - 90:          # still too tall: tighten the lines
            step = max(48, int((H - 160 - cy0) / rows))
            tf2 = K4(40)
        cy1 = min(cy0 + rows * step + 70, H - 90)
        if style == "cloud":
            cloud(img, (LEFT + 10, cy0 + 20, RIGHT - 50, cy1 - 10), RED, rnd)
        else:
            x0, x1 = LEFT, RIGHT - 120
            def need(t):
                mark = 60 if t.endswith("[check]") or t.endswith("[star]") else 0
                t = t.replace("[check]", "").replace("[star]", "").strip()
                if "->" in t:
                    a, b = [q.strip() for q in t.split("->", 1)]
                    return d.textlength(plain(a), font=tf2) + 112 + d.textlength(plain(b), font=tf2) + mark
                return d.textlength(plain(t), font=tf2) + mark
            longest = max(need(t) for t in tips)
            x1 = min(RIGHT - 10, max(LEFT + 520, LEFT + 110 + longest + 20))
            for a, b in (((x0, cy0 + 10), (x1, cy0 + 10)), ((x1, cy0 + 10), (x1, cy1)), ((x1, cy1), (x0, cy1)), ((x0, cy1), (x0, cy0 + 10))):
                wobble_line(d, a, b, RED, 4, rnd, amp=1.4, steps=16)
        ty = cy0 + 30
        hf = K7(48)
        d.text((LEFT + 40, ty), head, font=hf, fill=RED)
        wobble_line(d, (LEFT + 40, ty + 62), (LEFT + 40 + d.textlength(head, font=hf), ty + 62), RED, 3, rnd)
        ty += step + 4
        if style != "cloud":
            doodle_star(d, LEFT + 66, ty + 40, rnd, color=INK)
        for t in tips:
            mark = None
            if t.endswith("[check]"): mark, t = "check", t[:-7].strip()
            elif t.endswith("[star]"): mark, t = "star", t[:-6].strip()
            x = LEFT + 110
            lf2 = tf2
            def wneed(fnt):
                if "->" in t:
                    a_, b_ = [q.strip() for q in t.split("->", 1)]
                    return d.textlength(plain(a_), font=fnt) + 112 + d.textlength(plain(b_), font=fnt) + 60
                return d.textlength(plain(t), font=fnt) + 60
            while wneed(lf2) > RIGHT - 30 - x and lf2.size > 32:
                lf2 = K4(lf2.size - 2)
            if "->" in t:
                a, b = [s.strip() for s in t.split("->", 1)]
                x = draw_rich(d, x, ty, a, lf2, BLUE, rnd, RED)
                arrow(d, x + 14, ty + 36, x + 94, PURPLE, rnd)
                bx = x + 112
                x = draw_rich(d, bx, ty, b, lf2, BLUE, rnd, GREEN)
                wobble_line(d, (bx, ty + 64), (x, ty + 64), GREEN, 3, rnd)
            else:
                x = draw_rich(d, x, ty, t, lf2, BLUE, rnd, GREEN)
            if mark == "check": check(d, x + 16, ty + 30)
            elif mark == "star": star(d, x + 34, ty + 30, 18, GREEN)
            ty += step

    hf = font("patrick-hand-latin-400-normal.woff", 40)
    h = "@" + handle
    d.text((RIGHT - d.textlength(h, font=hf), H - 66), h, font=hf, fill=GREY)
    if total > 1:
        d.text((LEFT, H - 66), f"{idx}/{total}", font=hf, fill=GREY)

if __name__ == "__main__":
    data = json.load(open(sys.argv[1])); out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    pages = data["pages"]
    for i, p in enumerate(pages, 1):
        page(p, i, len(pages), data.get("handle", "phrasalidiomatic"),
             os.path.join(out, f"slide{i}.jpg"), seed=i * 13 + len(p["title"]))
