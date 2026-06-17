#!/usr/bin/env python3
"""Build the hot-water button GIF from 'water animation.pdf'.

The mockup is drawn on a BLACK background (a cyan glass filling with blue water
+ a pouring stream). Unlike the brew icon it needs no inversion: the only recolor
is mapping the black background to the dark screen bg (0x131313) so it blends; the
bright cyan glass + blue water are kept. Frames share a crop bbox (no jitter) and
are downscaled for smooth anti-aliasing. Sized to match the brew button height.
"""
import os
import fitz  # PyMuPDF
from PIL import Image, ImageChops

PDF = "/Users/tuomai/Desktop/gaggiamate 自动关机/water animation.pdf"
BG = (0x13, 0x13, 0x13)
TARGET_H = int(os.environ.get("TARGET_H", "128"))  # match the brew button height
DARK_MAX = 45  # pixels with all channels below this are background -> screen bg

doc = fitz.open(PDF)
hires = []
for page in doc:
    pm = page.get_pixmap(matrix=fitz.Matrix(4, 4))
    hires.append(Image.frombytes("RGB", (pm.width, pm.height), pm.samples))


def content_bbox(im):
    # The glass is the only SATURATED (coloured) content; this ignores both the
    # white page and the black icon canvas, so the crop tracks the glass.
    r, g, b = im.split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    sat = ImageChops.subtract(mx, mn)
    return sat.point(lambda v: 255 if v > 40 else 0).getbbox()


boxes = [content_bbox(im) for im in hires]
L = min(b[0] for b in boxes); T = min(b[1] for b in boxes)
R = max(b[2] for b in boxes); B = max(b[3] for b in boxes)
m = 12
L, T = max(0, L - m), max(0, T - m)
R, B = min(hires[0].width, R + m), min(hires[0].height, B + m)
print("bbox", (L, T, R, B), "->", R - L, "x", B - T)


def recolor(im):
    px = im.load(); out = Image.new("RGB", im.size); op = out.load()
    W, H = im.size
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            if max(r, g, b) - min(r, g, b) < 28:  # unsaturated (black canvas / white) -> screen bg
                op[x, y] = BG
            else:                                  # cyan glass / blue water -> keep
                op[x, y] = (r, g, b)
    return out


frames = []
for im in hires:
    crop = recolor(im.crop((L, T, R, B)))
    w = round(TARGET_H * (R - L) / (B - T))
    frames.append(crop.resize((w, TARGET_H), Image.LANCZOS))

W, H = frames[0].size
print("final frame", W, "x", H)

pal = frames[0].quantize(colors=32, method=Image.MEDIANCUT)
qframes = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
bg_idx = qframes[0].getpixel((1, 1))  # force flat bg to exactly BG (no visible square)
for q in qframes:
    p = q.getpalette(); p[bg_idx * 3:bg_idx * 3 + 3] = list(BG); q.putpalette(p)
qframes[0].save("/tmp/water_pour.gif", save_all=True, append_images=qframes[1:],
                duration=380, loop=0, optimize=False, disposal=1)

cs = Image.new("RGB", (W * 3 + 40, H + 20), BG)
for i, f in enumerate(frames):
    cs.paste(f, (10 + i * (W + 10), 10))
cs.save("/tmp/water_contact.png")
print("gif bytes:", os.path.getsize("/tmp/water_pour.gif"))

out = os.environ.get("WATER_C_OUT")
if out:
    data = open("/tmp/water_pour.gif", "rb").read()
    lines = ['#include "../ui.h"', "",
             "// [water-anim] Animated hot-water button: %dx%d GIF, 3 frames, a glass" % (W, H),
             "// filling with water + a pouring stream. Pre-composited on the dark screen",
             "// background (0x131313). Played by lv_gif; replaces the water play button.",
             "const uint8_t ui_img_water_pour_anim_data[] = {"]
    for i in range(0, len(data), 16):
        lines.append("    " + ",".join("0x%02x" % c for c in data[i:i + 16]) + ",")
    lines += ["};", "",
              "const lv_img_dsc_t ui_img_water_pour_anim = {",
              "    .header.always_zero = 0,",
              "    .header.w = %d," % W,
              "    .header.h = %d," % H,
              "    .data_size = sizeof(ui_img_water_pour_anim_data),",
              "    .header.cf = LV_IMG_CF_RAW,",
              "    .data = ui_img_water_pour_anim_data,",
              "};", ""]
    open(out, "w").write("\n".join(lines))
    print("wrote C:", out)
