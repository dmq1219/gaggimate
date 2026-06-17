#!/usr/bin/env python3
"""Render a looping 'turn the steam knob' animation as a GIF + LVGL C array.

Style matches the mockup: a black knob with a light ring + a white indicator
line, and a dashed circular arrow sweeping counter-clockwise with an arrowhead,
telling the user to rotate the physical steam knob. Composited on the dark
screen background (0x131313) so it blends seamlessly, like the coffee-bean GIF.
"""
import math
from PIL import Image, ImageDraw

SS = 4                     # supersample factor for smooth edges
SIZE = 130                 # final frame size (px)
N = 24                     # frames (full 360 deg loop -> seamless)
BG = (0x13, 0x13, 0x13)
RING = (0xDF, 0xDF, 0xDF)  # light knob ring + indicator
KNOB_FILL = (0x05, 0x05, 0x05)
ARROW = (0xC8, 0xC8, 0xC8)

S = SIZE * SS
cx = cy = S / 2
knob_r = 34 * SS           # knob radius
ring_w = 6 * SS
ind_w = 6 * SS             # indicator line width
arc_r = 52 * SS            # dashed arrow radius
arc_w = 5 * SS
dash_deg = 9               # dash arc length (deg)
gap_deg = 7                # gap between dashes (deg)
sweep = 280                # total dashed sweep (deg)


def pt(cx, cy, r, deg):
    a = math.radians(deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def render(frame):
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    # PIL angles increase clockwise (y is down); CCW rotation -> decreasing angle.
    head = (-90 - frame * (360.0 / N)) % 360  # arrowhead leads, starts at top

    # Dashed arc trailing the arrowhead (it sweeps CW back from the head); start a
    # bit behind the head so the arrowhead stands alone at the leading edge.
    deg = 16
    while deg < sweep:
        a0 = head + deg
        a1 = head + min(deg + dash_deg, sweep)
        d.arc([cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r], a0, a1, fill=ARROW, width=arc_w)
        deg += dash_deg + gap_deg

    # Arrowhead at the leading (CCW) end: tip points along the CCW tangent
    # (angle head-90), base spreads radially so it reads as a clean triangle.
    arc_pt = pt(cx, cy, arc_r, head)
    tip_dir = math.radians(head - 90)
    rad_dir = math.radians(head)
    h = 17 * SS
    w = 11 * SS
    tipP = (arc_pt[0] + h * math.cos(tip_dir), arc_pt[1] + h * math.sin(tip_dir))
    baseL = (arc_pt[0] + w * math.cos(rad_dir), arc_pt[1] + w * math.sin(rad_dir))
    baseR = (arc_pt[0] - w * math.cos(rad_dir), arc_pt[1] - w * math.sin(rad_dir))
    d.polygon([tipP, baseL, baseR], fill=ARROW)

    # Knob body: filled circle + light ring.
    d.ellipse([cx - knob_r, cy - knob_r, cx + knob_r, cy + knob_r], fill=KNOB_FILL, outline=RING, width=ring_w)
    # Indicator line from center outwards, rotating CCW (points opposite-ish the head).
    ind = (-90 - frame * (360.0 / N)) % 360
    end = pt(cx, cy, knob_r - 3 * SS, ind)
    d.line([(cx, cy), end], fill=RING, width=ind_w)
    d.ellipse([cx - ind_w / 2, cy - ind_w / 2, cx + ind_w / 2, cy + ind_w / 2], fill=RING)

    return img.resize((SIZE, SIZE), Image.LANCZOS)


frames = [render(i) for i in range(N)]
# Quantize to one shared global palette; full opaque frames + no optimisation so
# LVGL's gifdec sees simple full-canvas frames (matches the coffee-bean GIF).
pal = frames[0].quantize(colors=16, method=Image.MEDIANCUT)
qframes = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
# MEDIANCUT shifts the flat background away from BG, which then renders as a
# visible square against the screen (the screen draws 0x131313 -> RGB565). Force
# the background palette entry back to EXACTLY BG so it matches the screen after
# the panel's RGB565 conversion -> seamless.
bg_idx = qframes[0].getpixel((2, 2))
for q in qframes:
    p = q.getpalette()
    p[bg_idx * 3:bg_idx * 3 + 3] = list(BG)
    q.putpalette(p)
qframes[0].save("/tmp/steam_knob.gif", save_all=True, append_images=qframes[1:],
                duration=55, loop=0, optimize=False, disposal=1)
frames[0].save("/tmp/steam_knob_f0.png")
frames[N // 3].save("/tmp/steam_knob_f1.png")
frames[2 * N // 3].save("/tmp/steam_knob_f2.png")

# Emit the LVGL C array (raw GIF bytes wrapped in lv_img_dsc_t, cf=RAW), same
# format as ui_img_coffee_anim.c.
import os
data = open("/tmp/steam_knob.gif", "rb").read()
out = os.environ.get("KNOB_C_OUT")
if out:
    lines = ["#include \"../ui.h\"", "",
             "// [steam-anim] \"Turn the steam knob\" hint: %dx%d GIF, %d frames, pre-" % (SIZE, SIZE, N),
             "// composited on the dark screen background (0x131313). Played by lv_gif on",
             "// the steam screen so the user knows to rotate the physical steam knob.",
             "const uint8_t ui_img_steam_knob_anim_data[] = {"]
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        lines.append("    " + ",".join("0x%02x" % b for b in chunk) + ",")
    lines += ["};", "",
              "const lv_img_dsc_t ui_img_steam_knob_anim = {",
              "    .header.always_zero = 0,",
              "    .header.w = %d," % SIZE,
              "    .header.h = %d," % SIZE,
              "    .data_size = sizeof(ui_img_steam_knob_anim_data),",
              "    .header.cf = LV_IMG_CF_RAW,",
              "    .data = ui_img_steam_knob_anim_data,",
              "};", ""]
    open(out, "w").write("\n".join(lines))
    print("wrote C:", out, "(%d bytes gif)" % len(data))
print("gif bytes:", len(data), "frames:", N, "size:", SIZE)
