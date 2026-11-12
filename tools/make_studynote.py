"""Render 'study notes on a desk' carousels (white paper, wooden desk, pastel highlighters).
Usage: python3 make_studynote.py content.json outdir

content.json: {"handle": "tip4ielts", "theme": "...", "pages": [PAGE, ...]}
Page types (key words in *asterisks* get a coloured underline):
  {"type": "sections", "sections": [{"heading": "AFFECT", "bullets": ["..."], "examples": ["..."]}]}   # 2-3 sections
  {"type": "pens", "sections": [{"heading": "ALSO", "bullets": ["..."], "example": "..."}]}            # 2-3 sections
  {"type": "boxes", "title": "CONFUSED WORDS", "items": [{"word": "...", "meaning": "...", "example": "..."}]}  # 2-3 items
  {"type": "list", "title": "INSTEAD OF 'VERY'", "tag": "SAY", "rows": [["very tired", "exhausted"], ...]}       # up to 12 rows
  {"type": "glossary", "left": "INFORMAL", "right": "FORMAL", "rows": [["get", "obtain"], ...]}                  # up to 12 rows
"""
import sys, json, os, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
def F(name, size): return ImageFont.truetype(os.path.join(HERE, "fonts", name), max(10, int(size)))
AM7 = lambda s: F("amatic-sc-latin-700-normal.woff", s)
AM4 = lambda s: F("amatic-sc-latin-400-normal.woff", s)
SC = lambda s: F("patrick-hand-sc-latin-400-normal.woff", s)

W, H = 1080, 1350
PW, PH = 880, 1200
INK = (28, 30, 40)
PASTELS = [(240, 160, 168), (118, 204, 186), (184, 178, 226), (150, 192, 226), (246, 176, 140), (238, 212, 110)]
DEEP = {0: (214, 80, 100), 1: (40, 150, 120), 2: (110, 96, 190), 3: (50, 110, 170), 4: (220, 110, 60), 5: (190, 150, 20)}

# no ligatures (keeps 'fi' / 'fl' as small caps)
_orig_text = ImageDraw.ImageDraw.text
def _text(self, xy, text, *a, **k):
    k.setdefault("features", ["-liga", "-clig"])
    return _orig_text(self, xy, text, *a, **k)
ImageDraw.ImageDraw.text = _text
_orig_len = ImageDraw.ImageDraw.textlength
def _len(self, text, *a, **k):
    k.setdefault("features", ["-liga", "-clig"])
    return _orig_len(self, text, *a, **k)
ImageDraw.ImageDraw.textlength = _len

# ---------------- background ----------------
def wood(rnd):
    img = Image.new("RGB", (W, H), (190, 140, 98))
    d = ImageDraw.Draw(img)
    y = 0
    while y < H:
        h = rnd.randint(2, 9)
        c = rnd.randint(-22, 18)
        d.rectangle((0, y, W, y + h), fill=(190 + c, 140 + c, 98 + c // 2))
        y += h
    for _ in range(60):
        y0 = rnd.randint(0, H); amp = rnd.uniform(2, 8); ph = rnd.uniform(0, 6)
        pts = [(x, y0 + amp * math.sin(x / rnd.uniform(60, 160) + ph)) for x in range(0, W + 20, 20)]
        c = rnd.randint(-40, -10)
        d.line(pts, fill=(190 + c, 140 + c, 98 + c // 2), width=1)
    return img.filter(ImageFilter.GaussianBlur(0.8))

def pen(color, length, rnd, cap_left=True):
    """Horizontal highlighter pen image (RGBA)."""
    th = 74
    im = Image.new("RGBA", (length, th + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = color
    dark = tuple(max(0, int(c * 0.82)) for c in color)
    capw = int(length * 0.36)
    if cap_left:
        d.rounded_rectangle((0, 4, capw, th + 4), 18, fill=dark)
        d.rectangle((capw - 18, 4, capw - 6, th + 4), fill=(30, 30, 30))
        d.rounded_rectangle((capw - 4, 6, length, th + 2), 14, fill=body)
        d.rounded_rectangle((capw + 30, 20, capw + 30 + int(length * 0.3), th - 12), 6, fill=tuple(min(255, c + 30) for c in body))
    else:
        d.rounded_rectangle((0, 6, length - capw + 4, th + 2), 14, fill=body)
        d.rounded_rectangle((length - capw, 4, length, th + 4), 18, fill=dark)
        d.rectangle((length - capw + 6, 4, length - capw + 18, th + 4), fill=(30, 30, 30))
        d.rounded_rectangle((40, 20, 40 + int(length * 0.3), th - 12), 6, fill=tuple(min(255, c + 30) for c in body))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((4, 12, length - 2, th + 10), 18, fill=(0, 0, 0, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(5))
    sh.alpha_composite(im)
    return sh

# ---------------- helpers ----------------
def plain(t): return t.replace("*", "")

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(plain(t), font=f) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    lines.append(cur)
    out, open_ = [], False
    for ln in lines:
        s = ("*" if open_ else "") + ln
        if s.count("*") % 2: s += "*"; open_ = True
        else: open_ = False
        out.append(s)
    return out

def rich(d, x, y, text, f, fill, ucol):
    for i, part in enumerate(text.split("*")):
        if not part: continue
        w = d.textlength(part, font=f)
        d.text((x, y), part, font=f, fill=fill)
        if i % 2 == 1:
            uy = y + f.getbbox("Hg")[3] - f.size * 0.08 + 4
            d.line([(x, uy), (x + w, uy + 1)], fill=ucol, width=max(3, f.size // 11))
        x += w
    return x

def highlight(d, box, color, rnd, alpha_img=None):
    x0, y0, x1, y1 = box
    pts = [(x0 + rnd.uniform(-4, 4), y0 + rnd.uniform(-3, 3)), (x1 + rnd.uniform(-4, 6), y0 + rnd.uniform(-3, 3)),
           (x1 + rnd.uniform(-2, 6), y1 + rnd.uniform(-3, 3)), (x0 + rnd.uniform(-6, 2), y1 + rnd.uniform(-3, 3))]
    d.polygon(pts, fill=color)

def zigzag_blob(d, box, color):
    x0, y0, x1, y1 = box
    pts = []
    n = int((x1 - x0) / 18)
    for i in range(n + 1):
        pts.append((x0 + i * (x1 - x0) / n, y0 + (0 if i % 2 else 10)))
    for i in range(n, -1, -1):
        pts.append((x0 + i * (x1 - x0) / n, y1 - (0 if i % 2 else 10)))
    d.polygon(pts, fill=color)

def dashed_rect(d, box, color, width=6, dash=26, gap=16):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        L = math.hypot(bx - ax, by - ay); n = 0.0
        while n < L:
            e = min(n + dash, L)
            d.line([(ax + (bx - ax) * n / L, ay + (by - ay) * n / L), (ax + (bx - ax) * e / L, ay + (by - ay) * e / L)], fill=color, width=width)
            n += dash + gap

def mix(c, k=0.55):  # lighter version of a colour
    return tuple(int(255 - (255 - v) * k) for v in c)

# ---------------- layouts (draw on paper; return final y) ----------------
M = 60  # paper inner margin

def heading_rays(d, cx, y, text, f, ci, rnd):
    tw = d.textlength(text, font=f)
    th = f.size
    a, b = PASTELS[ci % 6], PASTELS[(ci + 1) % 6]
    for side in (-1, 1):
        ex = cx + side * (tw / 2 + 26)
        for k, (dx, dy, col) in enumerate(((10, -32, a), (16, 0, b), (10, 32, a))):
            x0 = ex + side * 4
            d.line([(x0, y + th * 0.55 + dy * 0.9), (x0 + side * (24 + dx), y + th * 0.55 + dy * 1.25)], fill=col, width=12)
        lx = ex + side * 70
        d.line([(lx, y + th * 0.6), ((PW - M + 30) if side > 0 else (M - 30), y + th * 0.6)], fill=INK, width=3)
    d.text((cx - tw / 2, y), text, font=f, fill=INK)
    return y + th * 1.1

def bullets_block(d, x, y, items, f, s, ucol, maxw, prefix="- "):
    for it in items:
        rows = wrap(d, it, f, maxw - 40 * s)
        for i, r in enumerate(rows):
            if i == 0: d.text((x, y), prefix.strip(), font=f, fill=INK)
            rich(d, x + 34 * s, y, r, f, INK, ucol)
            y += f.size * 1.32
    return y

def tag(d, x, y, text, f, color, rnd):
    tw = d.textlength(text, font=f)
    blob = [(x - 14, y + 4), (x + tw + 18, y - 4), (x + tw + 26, y + f.size * 0.6), (x + tw + 10, y + f.size + 10), (x - 18, y + f.size + 4), (x - 8, y + f.size * 0.5)]
    d.polygon(blob, fill=color)
    d.text((x, y + 2), text, font=f, fill=INK)
    return x + tw + 40

def L_sections(d, p, s, rnd):
    y = 70 * s
    secs = p["sections"][:3]
    for i, sec in enumerate(secs):
        y = heading_rays(d, PW / 2, y, sec["heading"], AM7(118 * s), i * 2, rnd) + 18 * s
        y = bullets_block(d, M + 30, y, sec.get("bullets", []), SC(36 * s), s, PASTELS[(i * 2) % 6], PW - 2 * M - 40)
        if sec.get("examples"):
            y += 14 * s
            tf = SC(30 * s)
            ex_x = tag(d, M, y, "EXAMPLES:", tf, (226, 186, 70), rnd)
            for ex in sec["examples"]:
                rows = wrap(d, ex, SC(34 * s), PW - M - ex_x - 20)
                for r_i, r in enumerate(rows):
                    if r_i == 0: d.text((ex_x, y), "-", font=SC(34 * s), fill=INK)
                    rich(d, ex_x + 28 * s, y, r, SC(34 * s), INK, DEEP[(i * 2) % 6])
                    y += 34 * s * 1.3
        y += 36 * s
    return y

def L_pens(img, d, p, s, rnd, pens_out):
    y = 60 * s
    secs = p["sections"][:3]
    cols = rnd.sample(range(6), len(secs))
    for i, sec in enumerate(secs):
        c = PASTELS[cols[i]]
        f = AM4(130 * s)
        tw = d.textlength(sec["heading"], font=f)
        cy = y + f.size * 0.55
        d.line([(110, cy), (PW / 2 - tw / 2 - 16, cy)], fill=mix(c, 0.8), width=14)
        d.line([(PW / 2 + tw / 2 + 16, cy), (PW - 110, cy)], fill=mix(c, 0.8), width=14)
        d.text((PW / 2 - tw / 2, y), sec["heading"], font=f, fill=INK)
        pens_out.append((cy, c))
        y += f.size * 1.05
        y = bullets_block(d, M + 50, y, sec.get("bullets", []), SC(32 * s), s, DEEP[cols[i]], PW - 2 * M - 70)
        if sec.get("example"):
            y += 18 * s
            ef = SC(36 * s)
            for r in wrap(d, sec["example"], ef, PW - 2 * M - 120):
                rich(d, M + 110, y, r, ef, DEEP[cols[i]], DEEP[cols[i]])
                y += ef.size * 1.3
        y += 40 * s
    return y

def L_boxes(d, p, s, rnd):
    y = 50 * s
    if p.get("title"):
        f = AM7(92 * s)
        tw = d.textlength(p["title"], font=f)
        d.line([(M - 30, y + f.size * 0.85), (PW - M + 30, y + f.size * 0.85)], fill=INK, width=3)
        d.rectangle((PW / 2 - tw / 2 - 10, y, PW / 2 + tw / 2 + 10, y + f.size), fill=(250, 251, 252))
        d.text((PW / 2 - tw / 2, y), p["title"], font=f, fill=INK)
        y += f.size * 1.2
    cols = rnd.sample(range(6), 3)
    for i, it in enumerate(p["items"][:3]):
        c = DEEP[cols[i]]
        f = SC(104 * s)
        word = it["word"].upper()
        while d.textlength(word, font=f) > PW - 2 * M - 80 and f.size > 50:
            f = SC(f.size - 4)
        tw = d.textlength(word, font=f)
        x = M + (20 if i % 2 == 0 else 60) * s
        dashed_rect(d, (x - 24, y - 6, x + tw + 30, y + f.size + 22), mix(c, 0.7), width=int(7 * s) + 1)
        d.text((x, y), word, font=f, fill=mix(c, 0.75), stroke_width=int(5 * s) + 1, stroke_fill=c)
        y += f.size + 46 * s
        mf = SC(36 * s)
        for r in wrap(d, it["meaning"], mf, PW - 2 * M - 100):
            d.text((x + 10, y), "•", font=mf, fill=INK)
            rich(d, x + 40, y, r, mf, INK, c)
            y += mf.size * 1.3
        y += 16 * s
        ef = SC(32 * s)
        for r in wrap(d, it["example"], ef, PW - 2 * M - 40):
            w = d.textlength(plain(r), font=ef)
            highlight(d, (M - 10, y - 2, M + w + 16, y + ef.size + 6), mix(PASTELS[cols[i]], 0.65), rnd)
            rich(d, M, y, r, ef, INK, c)
            y += ef.size * 1.45
        y += 40 * s
    return y

def L_list(d, p, s, rnd):
    y = 60 * s
    f = AM7(110 * s)
    title = p["title"].upper()
    while d.textlength(title, font=f) > PW - 2 * M and f.size > 50:
        f = AM7(f.size - 4)
    x = (PW - d.textlength(title, font=f)) / 2
    for i, ch in enumerate(title):
        col = PASTELS[(i * 2) % 6] if ch.strip() else INK
        d.text((x, y), ch, font=f, fill=INK if ch in "?!'" else mix(col, 0.95), stroke_width=3, stroke_fill=INK)
        x += d.textlength(ch, font=f)
    y += f.size * 1.08
    if p.get("tag"):
        tf = SC(48 * s)
        tw = d.textlength(p["tag"], font=tf)
        dashed_rect(d, (M + 10, y, M + tw + 60, y + tf.size + 34), mix(PASTELS[0], 0.9), width=5, dash=14, gap=8)
        d.text((M + 34, y + 12), p["tag"], font=tf, fill=INK)
        y += tf.size + 50
    rows = p["rows"][:13]
    avail = PH - 90 - y
    step = min(82 * s, avail / max(1, len(rows)))
    lf = SC(min(48, step * 0.66))
    rf = SC(min(46, step * 0.64))
    vx = M + 260
    d.line([(vx, y - 30), (vx, y + step * len(rows))], fill=INK, width=3)
    for i, (a, b) in enumerate(rows):
        yy = y + i * step
        d.ellipse((M + 8, yy + lf.size * 0.55, M + 18, yy + lf.size * 0.55 + 10), fill=mix(PASTELS[0], 0.9))
        aa = a
        while d.textlength(plain(aa), font=lf) > vx - M - 60 and lf.size > 20:
            lf = SC(lf.size - 2)
        rich(d, M + 40, yy, a, lf, (70, 60, 120), DEEP[2])
        d.line([(vx - 8, yy + lf.size * 0.6), (vx + 8, yy + lf.size * 0.6)], fill=INK, width=3)
        rich(d, vx + 50, yy + (lf.size - rf.size) * 0.6, b, rf, INK, DEEP[1])
    return y + step * len(rows)

def L_glossary(d, p, s, rnd):
    y = 70 * s
    hf = AM7(100 * s)
    mid = PW / 2
    for txt, cx in ((p["left"], mid / 2 + 20), (p["right"], mid + mid / 2 - 10)):
        tw = d.textlength(txt, font=hf)
        zigzag_blob(d, (cx - tw / 2 - 30, y + 10, cx + tw / 2 + 30, y + hf.size + 10), mix(PASTELS[4], 0.7))
        d.text((cx - tw / 2, y), txt, font=hf, fill=INK)
    y += hf.size + 50
    rows = p["rows"][:12]
    avail = PH - 80 - y
    step = min(84 * s, avail / max(1, len(rows)))
    d.line([(mid, y - 10), (mid, y + step * len(rows))], fill=INK, width=3)
    kf = SC(min(50, step * 0.6)); vf = SC(min(32, step * 0.42))
    half = len(rows) if p.get("pairs", True) else (len(rows) + 1) // 2
    for i, (a, b) in enumerate(rows):
        yy = y + i * step
        # left column: informal; right column: formal
        lw = d.textlength(plain(a), font=kf)
        f1 = kf
        while lw > mid - M - 40 and f1.size > 20:
            f1 = SC(f1.size - 2); lw = d.textlength(plain(a), font=f1)
        rich(d, M, yy, a, f1, (190, 60, 70), DEEP[0])
        d.text((mid - 34, yy + 4), "=", font=kf, fill=INK)
        f2 = kf
        while d.textlength(plain(b), font=f2) > PW - mid - M - 10 and f2.size > 20:
            f2 = SC(f2.size - 2)
        rich(d, mid + 30, yy, b, f2, (40, 120, 110), DEEP[1])
    return y + step * len(rows)

# ---------------- page ----------------
def render(p, idx, total, handle, out, seed):
    rnd = random.Random(seed)
    bg = wood(rnd).convert("RGBA")
    t = p.get("type", "sections")
    s = 1.3
    for _ in range(18):
        paper = Image.new("RGB", (PW, PH), (250, 251, 252))
        d = ImageDraw.Draw(paper)
        r2 = random.Random(seed)
        pens_out = []
        if t == "sections": end = L_sections(d, p, s, r2)
        elif t == "pens": end = L_pens(paper, d, p, s, r2, pens_out)
        elif t == "boxes": end = L_boxes(d, p, s, r2)
        elif t == "list": end = L_list(d, p, s, r2)
        elif t == "glossary": end = L_glossary(d, p, s, r2)
        else: raise SystemExit(f"unknown page type {t}")
        if end <= PH - 70: break
        s *= 0.93
    # watermark + counter on the paper
    wf = F("patrick-hand-latin-400-normal.woff", 34)
    d.text((PW - 60 - d.textlength("@" + handle, font=wf), PH - 56), "@" + handle, font=wf, fill=(150, 160, 175))
    if total > 1:
        d.text((60, PH - 56), f"{idx}/{total}", font=wf, fill=(150, 160, 175))

    ang = rnd.uniform(-1.3, 1.3)
    paper_rgba = paper.convert("RGBA").rotate(ang, expand=True, resample=Image.BICUBIC)
    px = (W - paper_rgba.width) // 2
    py = 96
    shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    m = paper_rgba.split()[3]
    shadow.paste((0, 0, 0, 110), (px + 8, py + 12), m)
    bg.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    bg.alpha_composite(paper_rgba, (px, py))

    # pens
    if t == "pens":
        for cy, c in pens_out:
            yy = int(py + cy - 40)
            lp = pen(c, 230, rnd, cap_left=True); bg.alpha_composite(lp, (-60, yy))
            rp = pen(c, 230, rnd, cap_left=False); bg.alpha_composite(rp, (W - 170, yy))
    else:
        cols = rnd.sample(PASTELS, 4)
        choice = rnd.choice(["top", "sides", "corner"])
        if choice in ("top", "corner"):
            bg.alpha_composite(pen(cols[0], 330, rnd, True), (60, 4))
            bg.alpha_composite(pen(cols[1], 330, rnd, False), (W - 400, 2))
        if choice in ("sides", "corner"):
            v1 = pen(cols[2], 300, rnd, True).rotate(90, expand=True)
            bg.alpha_composite(v1, (-34, 260))
            v2 = pen(cols[3], 300, rnd, False).rotate(-90, expand=True)
            bg.alpha_composite(v2, (W - 52, 640))
    bg.convert("RGB").save(out, quality=92)

if __name__ == "__main__":
    data = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    pages = data["pages"]
    for i, p in enumerate(pages, 1):
        render(p, i, len(pages), data.get("handle", "tip4ielts"), os.path.join(outdir, f"slide{i}.jpg"), seed=i * 31 + len(json.dumps(p)))
