#!/usr/bin/env python3
"""One Perfect Strawberry — draws a single ripe strawberry with pure code
and writes it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

No external assets, no network, standard library only. The image is painted
pixel by pixel: warm cream background, soft shadow, a glossy red strawberry
body with seed dimples, water droplets, green leaves and a stem.
"""
import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
CX = 512.0

# ---------------------------------------------------------------- pixel buf
buf = bytearray(W * H * 3)


def set_px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend_px(x, y, r, g, b, a):
    """Blend color (r,g,b) over existing pixel with alpha a in [0,1]."""
    if a <= 0.0 or not (0 <= x < W and 0 <= y < H):
        return
    if a >= 1.0:
        set_px(x, y, int(r), int(g), int(b))
        return
    i = (y * W + x) * 3
    buf[i] = int(buf[i] + (r - buf[i]) * a)
    buf[i + 1] = int(buf[i + 1] + (g - buf[i + 1]) * a)
    buf[i + 2] = int(buf[i + 2] + (b - buf[i + 2]) * a)


def fill_ellipse(cx, cy, rx, ry, r, g, b, a=1.0):
    x0 = max(0, int(cx - rx))
    x1 = min(W - 1, int(cx + rx) + 1)
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        dx = math.sqrt(max(0.0, 1.0 - dy * dy))
        xa = int(cx - rx * dx)
        xb = int(cx + rx * dx)
        for x in range(max(x0, xa), min(x1, xb) + 1):
            blend_px(x, y, r, g, b, a)


def soft_ellipse(cx, cy, rx, ry, r, g, b, amax):
    """Ellipse whose alpha fades to 0 at the rim (soft edge)."""
    x0 = max(0, int(cx - rx))
    x1 = min(W - 1, int(cx + rx) + 1)
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        for x in range(x0, x1 + 1):
            dx = (x - cx) / rx
            d = dx * dx + dy * dy
            if d >= 1.0:
                continue
            a = amax * (1.0 - d) ** 1.5
            blend_px(x, y, r, g, b, a)


def fill_rotated_ellipse(cx, cy, rx, ry, ang_deg, r, g, b, a=1.0):
    ang = math.radians(ang_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    ext = int(max(rx, ry)) + 1
    for y in range(max(0, int(cy - ext)), min(H - 1, int(cy + ext)) + 1):
        for x in range(max(0, int(cx - ext)), min(W - 1, int(cx + ext)) + 1):
            dx, dy = x - cx, y - cy
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                blend_px(x, y, r, g, b, a)


# ------------------------------------------------------------- background
for y in range(H):
    t = y / (H - 1)
    r = 255 - 12 * t
    g = 247 - 24 * t
    b = 232 - 34 * t
    i = y * W * 3
    for x in range(W):
        buf[i] = int(r)
        buf[i + 1] = int(g)
        buf[i + 2] = int(b)
        i += 3

# soft warm glow behind the fruit
soft_ellipse(CX, 560, 430, 400, 255, 252, 244, 0.55)

# ------------------------------------------------------------- soft shadow
soft_ellipse(CX, 908, 330, 52, 120, 70, 45, 0.38)
soft_ellipse(CX, 905, 260, 38, 90, 50, 32, 0.30)

# ------------------------------------------------------------- strawberry body
TOP = 330.0
BOT = 890.0
WMAX = 295.0


def half_width(t):
    """t in [0,1]: 0 at top, 1 at tip. Narrow crown, full shoulders at
    t~0.22, then a steady taper to a point."""
    if t < 0.22:
        f = 0.80 + 0.20 * (t / 0.22) ** 0.8
    else:
        u = (t - 0.22) / 0.78
        f = (1.0 - u ** 2.0) ** 0.55
    return WMAX * f


def body_y(x):
    """Top edge of the body at column x (slight dip in the middle)."""
    u = (x - CX) / WMAX
    if abs(u) >= 1.0:
        return None
    return TOP + 26.0 * u * u + 14.0 * (1.0 - u * u) * 0.0


for y in range(int(TOP), int(BOT) + 1):
    t = (y - TOP) / (BOT - TOP)
    w = half_width(t)
    if w <= 0:
        continue
    xa = int(CX - w)
    xb = int(CX + w)
    for x in range(max(0, xa), min(W - 1, xb) + 1):
        u = (x - CX) / w  # -1 .. 1 across the body
        # vertical shading: brighter near the top, deeper near the tip
        vt = 1.0 - 0.22 * t
        # horizontal shading: light from upper-left, dark at the rim
        rim = abs(u)
        shade = 1.0 - 0.38 * rim * rim - 0.10 * max(0.0, u) ** 2
        # warm orange-red at the top, deep red at the bottom
        r = (238.0 + 14.0 * (1.0 - t) - 38.0 * t) * shade * vt
        g = (58.0 + 26.0 * (1.0 - t) - 22.0 * t) * shade * vt
        b = (52.0 + 14.0 * (1.0 - t) - 18.0 * t) * shade * vt
        # faint vertical ribbing
        rib = 1.0 + 0.03 * math.sin(u * 28.0 + t * 9.0)
        set_px(x, y, max(0, min(255, int(r * rib))),
               max(0, min(255, int(g * rib))),
               max(0, min(255, int(b * rib))))

# round the top shoulders: erase above the top edge curve. The edge dips
# down in the middle (a notch where the leaves attach) and rises at the
# shoulders, so the crown reads as a strawberry top, not a flat bowl rim.
for y in range(int(TOP), int(TOP) + 60):
    for x in range(int(CX - WMAX), int(CX + WMAX) + 1):
        u = (x - CX) / WMAX
        edge = TOP + 48.0 * (1.0 - u * u)
        if y < edge:
            tt = y / (H - 1)
            set_px(x, y, int(255 - 12 * tt), int(247 - 24 * tt),
                   int(232 - 34 * tt))

# ------------------------------------------------------------- seeds
rnd = random.Random(7)
seed_rows = [0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.76, 0.85, 0.92]
for ri, t in enumerate(seed_rows):
    w = half_width(t)
    y = TOP + t * (BOT - TOP)
    # seeds across the row, inset from the rim, alternating offset
    span = w * 0.86
    n = max(2, int(span / 48))
    off = 26 if ri % 2 else 0
    for k in range(n):
        fx = -span + (2 * span) * (k + 0.5) / n + off * (1 if k % 2 else -1) * 0.3
        sx = CX + fx
        sy = y + rnd.uniform(-4, 4)
        # dimple: darker red hollow behind the seed
        fill_ellipse(sx, sy + 2, 9, 12, 120, 12, 18, 0.55)
        # pale seed
        fill_ellipse(sx, sy, 6.5, 9.5, 252, 238, 196, 1.0)
        fill_ellipse(sx - 1, sy - 2, 3.5, 5, 255, 248, 225, 1.0)

# ------------------------------------------------------------- specular highlight
soft_ellipse(432, 430, 150, 205, 255, 235, 225, 0.20)
soft_ellipse(468, 392, 78, 105, 255, 245, 238, 0.28)
soft_ellipse(500, 360, 34, 46, 255, 255, 252, 0.35)

# ------------------------------------------------------------- water droplets
drops = [(600, 470, 11), (392, 560, 9), (640, 620, 13), (430, 690, 8),
         (560, 740, 10), (350, 470, 7), (690, 520, 8), (480, 800, 7)]
for (dx, dy, dr) in drops:
    soft_ellipse(dx, dy, dr, dr, 235, 245, 250, 0.45)
    fill_ellipse(dx - dr * 0.3, dy - dr * 0.35, dr * 0.28, dr * 0.28,
                 255, 255, 255, 0.9)

# ------------------------------------------------------------- leaves + stem
# Nine leaves fanning out from the crown notch, bases tucked into the dip
# so they read as attached, not pasted on top.
LEAF_CY = 362.0
leaf_specs = [  # (angle_deg from vertical, length, width)
    (-85, 205, 46), (-62, 200, 48), (-40, 190, 50), (-18, 170, 48),
    (0, 150, 46),
    (18, 170, 48), (40, 190, 50), (62, 200, 48), (85, 205, 46),
]
for li, (ang, length, width) in enumerate(leaf_specs):
    rad = math.radians(ang)
    mid_x = CX + math.sin(rad) * length * 0.5
    mid_y = LEAF_CY - math.cos(rad) * length * 0.5
    dark = (66, 146, 66) if li % 2 == 0 else (58, 138, 60)
    lite = (96, 178, 88) if li % 2 == 0 else (88, 170, 82)
    # leaf as a rotated ellipse, base at the crown, tip outwards
    # (rotation +ang so the long axis follows the midrib direction)
    fill_rotated_ellipse(mid_x, mid_y, width * 0.5, length * 0.52,
                         ang, dark[0], dark[1], dark[2], 1.0)
    fill_rotated_ellipse(mid_x, mid_y, width * 0.34, length * 0.46,
                         ang, lite[0], lite[1], lite[2], 1.0)
    # midrib
    steps = 24
    for s in range(steps + 1):
        f = s / steps
        px = CX + math.sin(rad) * length * f
        py = LEAF_CY - math.cos(rad) * length * f
        blend_px(int(px), int(py), 46, 110, 50, 0.8)
        blend_px(int(px) + 1, int(py), 46, 110, 50, 0.6)

# stem
fill_rotated_ellipse(CX + 6, 300, 9, 42, -12, 96, 128, 66, 1.0)
fill_rotated_ellipse(CX + 6, 300, 5, 40, -12, 130, 168, 92, 1.0)

# small leaf highlight
soft_ellipse(452, 300, 60, 26, 190, 230, 160, 0.35)

# ------------------------------------------------------------- fine grain
rnd2 = random.Random(1234)
for _ in range(26000):
    x = rnd2.randrange(W)
    y = rnd2.randrange(H)
    i = (y * W + x) * 3
    d = rnd2.randint(-5, 5)
    buf[i] = max(0, min(255, buf[i] + d))
    buf[i + 1] = max(0, min(255, buf[i + 1] + d))
    buf[i + 2] = max(0, min(255, buf[i + 2] + d))

# ------------------------------------------------------------- PNG encode
out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "entry.png")


def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
raw = bytearray()
for y in range(H):
    raw.append(0)
    raw += buf[y * W * 3:(y + 1) * W * 3]
png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", ihdr)
png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
png += chunk(b"IEND", b"")
with open(out_path, "wb") as f:
    f.write(png)
print(f"wrote {out_path} {len(png)} bytes")
