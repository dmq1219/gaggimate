#!/usr/bin/env python3
"""Build the animated brew button GIF from 'brew button animation.pdf'.

The mockup is drawn black-on-white (portafilter pouring espresso into two cyan
cups). On the dark display the portafilter must be light, so: grayscale pixels
are luminance-inverted (white paper -> dark screen bg, black portafilter ->
white), while the coloured pixels (brown coffee, cyan cups) are kept. Frames are
cropped to a shared bbox (no jitter) and downscaled for smooth anti-aliasing.
"""
import os, math
import fitz  # PyMuPDF
from PIL import Image

PDF = "/Users/tuomai/Desktop/gaggiamate 自动关机/brew button animation.pdf"
BG = (0x13, 0x13, 0x13)
LIGHT = (0xFA, 0xFA, 0xFA)
TARGET_H = int(os.environ.get("TARGET_H", "128"))  # final height in px (2x the original 64)
SAT_THRESH = 30          # >this = coloured (brown/cyan), else grayscale

doc = fitz.open(PDF)
hires = []
for page in doc:
    pm = page.get_pixmap(matrix=fitz.Matrix(4, 4))  # 4x render
    img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    hires.append(img)

# Shared content bbox: non-white across ALL frames (so the portafilter is fixed).
def nonwhite_bbox(im):
    g = im.convert("L").point(lambda v: 0 if v > 245 else 255)
    return g.getbbox()

boxes = [nonwhite_bbox(im) for im in hires]
L = min(b[0] for b in boxes); T = min(b[1] for b in boxes)
R = max(b[2] for b in boxes); B = max(b[3] for b in boxes)
m = 12
L, T = max(0, L - m), max(0, T - m)
R, B = min(hires[0].width, R + m), min(hires[0].height, B + m)
print("bbox", (L, T, R, B), "->", R - L, "x", B - T)


def recolor(im):
    px = im.load()
    out = Image.new("RGB", im.size)
    op = out.load()
    W, H = im.size
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            mx, mn = max(r, g, b), min(r, g, b)
            if mx - mn <= SAT_THRESH:           # grayscale: bg / portafilter
                lum = (r + g + b) / 3.0
                t = (255 - lum) / 255.0          # white->0, black->1
                nl = round(BG[0] + t * (LIGHT[0] - BG[0]))
                op[x, y] = (nl, nl, nl)
            else:                                # coloured: coffee / cup -> keep
                op[x, y] = (r, g, b)
    return out


frames = []
for im in hires:
    crop = im.crop((L, T, R, B))
    rc = recolor(crop)
    w = round(TARGET_H * (R - L) / (B - T))
    frames.append(rc.resize((w, TARGET_H), Image.LANCZOS))

W, H = frames[0].size
print("final frame", W, "x", H)

# Force flat background to exactly BG after quantisation (avoid a visible square,
# same fix as the steam-knob GIF).
pal = frames[0].quantize(colors=32, method=Image.MEDIANCUT)
qframes = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
bg_idx = qframes[0].getpixel((1, 1))
for q in qframes:
    p = q.getpalette(); p[bg_idx * 3:bg_idx * 3 + 3] = list(BG); q.putpalette(p)
qframes[0].save("/tmp/brew_pour.gif", save_all=True, append_images=qframes[1:],
                duration=380, loop=0, optimize=False, disposal=1)
for i, f in enumerate(frames):
    f.save(f"/tmp/brew_f{i}.png")

# Contact sheet on a dark bg to preview how it reads on the screen.
cs = Image.new("RGB", (W * 3 + 40, H + 20), BG)
for i, f in enumerate(frames):
    cs.paste(f, (10 + i * (W + 10), 10))
cs.save("/tmp/brew_contact.png")
print("gif bytes:", os.path.getsize("/tmp/brew_pour.gif"))

out = os.environ.get("BREW_C_OUT")
if out:
    data = open("/tmp/brew_pour.gif", "rb").read()
    lines = ['#include "../ui.h"', "",
             "// [brew-anim] Animated brew button: %dx%d GIF, 3 frames, espresso" % (W, H),
             "// pouring into two cups. Pre-composited on the dark screen background",
             "// (0x131313). Played by lv_gif; replaces the play-triangle start button.",
             "const uint8_t ui_img_brew_pour_anim_data[] = {"]
    for i in range(0, len(data), 16):
        lines.append("    " + ",".join("0x%02x" % c for c in data[i:i + 16]) + ",")
    lines += ["};", "",
              "const lv_img_dsc_t ui_img_brew_pour_anim = {",
              "    .header.always_zero = 0,",
              "    .header.w = %d," % W,
              "    .header.h = %d," % H,
              "    .data_size = sizeof(ui_img_brew_pour_anim_data),",
              "    .header.cf = LV_IMG_CF_RAW,",
              "    .data = ui_img_brew_pour_anim_data,",
              "};", ""]
    open(out, "w").write("\n".join(lines))
    print("wrote C:", out)
