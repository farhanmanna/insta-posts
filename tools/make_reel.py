"""Turn a rendered carousel (slide1..slide5.jpg) into a 9:16 Instagram Reel.
Usage: python3 make_reel.py POST_FOLDER HANDLE "HOOK TEXT" [OUT.mp4]
  POST_FOLDER  folder with slide1.jpg..slideN.jpg (and content.json, optional)
  HANDLE       instagram handle without @
  HOOK TEXT    short line shown at the top, e.g. "5 Daily Use English Sentences"
Output: POST_FOLDER/reel.mp4 (1080x1920, 30 fps, H.264, silent) and reel_cover.jpg
"""
import sys, os, glob, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
FB = os.path.join(HERE, "fonts", "baloo-2-latin-800-normal.woff")
FM = os.path.join(HERE, "fonts", "baloo-2-latin-700-normal.woff")
W, H = 1080, 1920
SLIDE_SECS, FADE, OUTRO_SECS = 3.4, 0.45, 2.2

def font(p, s): return ImageFont.truetype(p, s)

def fit_lines(d, text, path, size, maxw, maxlines=2):
    while size > 30:
        f = font(path, size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= maxw: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur)
        if len(lines) <= maxlines: return f, lines
        size -= 4
    return f, lines

def background(slide):
    s = slide.convert("RGB")
    bg = s.resize((int(H * s.width / s.height) + 400, H + 400)).filter(ImageFilter.GaussianBlur(40))
    left = (bg.width - W) // 2
    bg = bg.crop((left, 200, left + W, 200 + H))
    dark = Image.new("RGB", (W, H), (10, 18, 28))
    return Image.blend(bg, dark, 0.55)

def accent(slide):
    r, g, b = ImageStat.Stat(slide.convert("RGB").resize((50, 50))).mean
    # push toward a saturated, readable accent
    m = max(r, g, b, 1)
    return tuple(int(min(255, 60 + 195 * c / m)) for c in (r, g, b))

def frame(slide, i, n, handle, hook):
    img = background(slide)
    d = ImageDraw.Draw(img)
    acc = accent(slide)
    # hook at the top
    f, lines = fit_lines(d, hook, FB, 80, W - 200)
    y = 150
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, y), ln, font=f, fill="white", stroke_width=3, stroke_fill=(0, 0, 0))
        y += int(f.size * 1.1)
    # slide card
    sw = 960
    sh = int(slide.height * sw / slide.width)
    if sh > 1200:
        sh = 1200; sw = int(slide.width * sh / slide.height)
    card = slide.convert("RGB").resize((sw, sh), Image.LANCZOS)
    cx, cy = (W - sw) // 2, max(y + 40, (H - sh) // 2 + 40)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((cx + 10, cy + 18, cx + sw + 10, cy + sh + 18), 30, fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(18)))
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw, sh), 30, fill=255)
    img.paste(card, (cx, cy), mask)
    d = ImageDraw.Draw(img)
    # progress dots + footer
    by = cy + sh + 60
    gap = 44
    x0 = W / 2 - (n - 1) * gap / 2
    for k in range(n):
        r = 13 if k == i else 9
        d.ellipse((x0 + k * gap - r, by - r, x0 + k * gap + r, by + r), fill=acc if k == i else (200, 205, 215))
    ff = font(FM, 42)
    t = f"Follow @{handle} for daily English"
    d.text(((W - d.textlength(t, font=ff)) / 2, min(H - 140, by + 50)), t, font=ff, fill=(235, 240, 245))
    return img.convert("RGB")

def outro(slide, handle):
    img = background(slide)
    d = ImageDraw.Draw(img)
    acc = accent(slide)
    f1 = font(FB, 96); f2 = font(FM, 60); f3 = font(FB, 72)
    lines = [("Save this post", f1, "white"), ("and practise daily", f2, (220, 228, 236)), ("", f2, "white"), (f"@{handle}", f3, acc), ("Follow for more", f2, (220, 228, 236))]
    y = 640
    for t, f, c in lines:
        if t:
            d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=c, stroke_width=2, stroke_fill=(0, 0, 0))
        y += int(f.size * 1.35)
    return img

def main():
    folder, handle, hook = sys.argv[1], sys.argv[2], sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(folder, "reel.mp4")
    slides = sorted(glob.glob(os.path.join(folder, "slide*.jpg")), key=lambda p: int(os.path.basename(p)[5:-4]))
    if not slides: raise SystemExit("no slides found")
    tmp = tempfile.mkdtemp()
    frames = []
    for i, p in enumerate(slides):
        fp = os.path.join(tmp, f"f{i}.png")
        frame(Image.open(p), i, len(slides), handle, hook).save(fp)
        frames.append((fp, SLIDE_SECS))
    op = os.path.join(tmp, "outro.png")
    outro(Image.open(slides[0]), handle).save(op)
    frames.append((op, OUTRO_SECS))
    Image.open(frames[0][0]).save(os.path.join(folder, "reel_cover.jpg"), quality=92)

    fps = 30
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for fp, secs in frames:
        args += ["-i", fp]
    chains = []
    for k, (fp, secs) in enumerate(frames):
        nfr = int(secs * fps)
        # gentle push-in on each frame
        chains.append(f"[{k}:v]scale=2160:3840,zoompan=z='min(1+0.0004*on,1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={nfr}:s={W}x{H}:fps={fps},setsar=1,format=yuv420p[v{k}]")
    last = "v0"
    offset = 0.0
    trans = ["slideleft", "fade", "slideleft", "smoothleft", "fade", "slideleft"]
    for k in range(1, len(frames)):
        offset += frames[k - 1][1] - FADE
        chains.append(f"[{last}][v{k}]xfade=transition={trans[(k - 1) % len(trans)]}:duration={FADE}:offset={offset:.2f}[x{k}]")
        last = f"x{k}"
    args += ["-filter_complex", ";".join(chains), "-map", f"[{last}]", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    print(out)

if __name__ == "__main__":
    main()
