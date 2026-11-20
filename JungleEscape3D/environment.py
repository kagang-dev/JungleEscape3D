"""
environment.py - The endless jungle (v2: dense, varied, smooth-shaded).

How the endless world works
---------------------------
* The player runs along +Y.  The world itself never moves.
* The world is made of a few "segments", each SEGMENT_LENGTH long.
* At start-up we build several segment *variants* (jungle, river with wooden
  bridge, ancient ruins).  Every variant is a different random forest made of
  merged meshes, so the sides are never empty or identical.
* A segment far behind the player is moved to the front of the world and given
  a new random variant (instanceTo = no extra memory, almost free).
* The amount of detail depends on the graphics quality (low / medium / high).
"""
import math
import random

from panda3d.core import NodePath, TransparencyAttrib

from settings import QUALITY, SEGMENT_LENGTH
from shapes import MeshBuilder

L = SEGMENT_LENGTH
TAU = math.tau

# ---------------------------------------------------------------- palette
BARKS = [(0.46, 0.33, 0.22), (0.38, 0.27, 0.18), (0.55, 0.42, 0.30), (0.33, 0.25, 0.19)]
LEAVES = [(0.10, 0.45, 0.11), (0.16, 0.57, 0.15), (0.08, 0.36, 0.12), (0.22, 0.60, 0.17),
          (0.19, 0.50, 0.22), (0.12, 0.48, 0.30), (0.20, 0.55, 0.12)]
SUNLIT = [(0.40, 0.70, 0.20), (0.50, 0.75, 0.25), (0.34, 0.66, 0.30)]
GRASS = (0.17, 0.46, 0.14)
GRASS_EDGE = (0.20, 0.48, 0.15)
DIRT = (0.60, 0.43, 0.26)
DIRT_LIGHT = (0.72, 0.55, 0.36)
VINE = (0.12, 0.40, 0.12)
ROCKS = [(0.50, 0.50, 0.47), (0.44, 0.45, 0.43), (0.56, 0.54, 0.48)]
MOSS = (0.27, 0.47, 0.18)
STONE = (0.62, 0.61, 0.54)
STONE_DARK = (0.46, 0.46, 0.42)
WOOD = (0.55, 0.37, 0.19)
FLOWERS = [(0.92, 0.22, 0.28), (0.97, 0.82, 0.22), (0.72, 0.32, 0.82), (1.0, 0.52, 0.22)]
LITTER = [(0.66, 0.43, 0.16), (0.55, 0.36, 0.13), (0.46, 0.50, 0.16), (0.72, 0.56, 0.20), (0.42, 0.30, 0.15)]


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _mixc(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


# ---------------------------------------------------------------- tree parts
def _canopy(mb, rng, q, cx, cy, cz, spread, size, n):
    """A clump of bumpy, smooth leaf blobs with a sunlit highlight on top."""
    for _ in range(n):
        a, d = rng.uniform(0, TAU), rng.uniform(0, 1) * spread
        r = size * rng.uniform(0.6, 1.0)
        mb.sphere((cx + math.cos(a) * d, cy + math.sin(a) * d, cz + rng.uniform(-0.3, 0.6) * size),
                  (r, r * rng.uniform(0.85, 1.1), r * rng.uniform(0.52, 0.72)),
                  rng.choice(LEAVES), hpr=(rng.uniform(0, 360), 0, 0),
                  rings=q["rings"], segs=q["segs"], rough=0.22, grad=0.55)
    mb.sphere((cx, cy, cz + size * 0.5), (size * 0.65, size * 0.65, size * 0.3),
              rng.choice(SUNLIT), rings=q["rings"], segs=q["segs"], rough=0.25, grad=0.8)


def _trunk(mb, rng, q, x, y, height, r0, r1, bend, color, steps=4):
    ang = rng.uniform(0, TAU)
    pts, rad = [(x, y, 0.0)], [r0]
    for i in range(1, steps + 1):
        t = i / steps
        off = bend * height * t * t
        pts.append((x + math.cos(ang) * off + rng.uniform(-0.12, 0.12) * r0,
                    y + math.sin(ang) * off + rng.uniform(-0.12, 0.12) * r0, height * t))
        rad.append(r0 + (r1 - r0) * t)
    for i in range(steps):
        mb.limb(pts[i], pts[i + 1], rad[i], rad[i + 1], color, sides=q["sides"])
        if 0 < i:
            mb.sphere(pts[i], rad[i] * 1.02, color, rings=3, segs=q["sides"], rough=0.08, grad=0.85)
    return pts, rad


def _roots(mb, rng, x, y, r, n, length, color):
    """Exposed roots spreading from the base of the trunk."""
    for i in range(n):
        a = i * TAU / n + rng.uniform(-0.4, 0.4)
        ln = length * rng.uniform(0.6, 1.1)
        ca, sa = math.cos(a), math.sin(a)
        side = rng.uniform(-0.6, 0.6) * ln * 0.25
        p0 = (x + ca * r * 0.4, y + sa * r * 0.4, 0.25 + r * 0.7)
        p1 = (x + ca * (r + ln * 0.45), y + sa * (r + ln * 0.45), r * 0.4 + rng.uniform(0, 0.2))
        p2 = (x + ca * (r + ln) - sa * side, y + sa * (r + ln) + ca * side, 0.0)
        mb.limb(p0, p1, r * 0.42, r * 0.26, color, sides=5)
        mb.limb(p1, p2, r * 0.26, r * 0.08, color, sides=5)


def _vine(mb, rng, x, y, z, length):
    px, py, pz = x, y, z
    for _ in range(3):
        nx, ny, nz = px + rng.uniform(-0.25, 0.25), py + rng.uniform(-0.25, 0.25), pz - length / 3
        mb.limb((px, py, pz), (nx, ny, nz), 0.05, 0.04, VINE, sides=4)
        if rng.random() < 0.7:
            mb.sphere((nx, ny, nz), (0.18, 0.18, 0.1), rng.choice(LEAVES), rings=3, segs=5)
        px, py, pz = nx, ny, nz


def _mushroom(mb, x, y, z, s=1.0, col=(0.82, 0.22, 0.12)):
    mb.limb((x, y, z), (x, y, z + 0.16 * s), 0.04 * s, 0.035 * s, (0.9, 0.86, 0.75), sides=5)
    mb.sphere((x, y, z + 0.18 * s), (0.11 * s, 0.11 * s, 0.06 * s), col, rings=3, segs=6)


# ---------------------------------------------------------------- tree types
def _tree_tall(mb, rng, q, x, y, s, lod):
    h, r0 = rng.uniform(12, 17) * s, rng.uniform(0.38, 0.55) * s
    col = rng.choice(BARKS)
    pts, _ = _trunk(mb, rng, q, x, y, h, r0, r0 * 0.4, rng.uniform(-0.1, 0.1), col, 4 if lod else 3)
    if lod:
        _roots(mb, rng, x, y, r0, 4, r0 * 3.2, col)
        for _ in range(rng.randint(2, 3)):               # side branches with their own leaves
            b = pts[rng.randint(2, 3)]
            a = rng.uniform(0, TAU)
            end = (b[0] + math.cos(a) * 3 * s, b[1] + math.sin(a) * 3 * s, b[2] + rng.uniform(1, 2.2) * s)
            mb.limb(b, end, r0 * 0.3, r0 * 0.15, col, sides=5)
            _canopy(mb, rng, q, end[0], end[1], end[2] + 0.5 * s, 1.5 * s, 2.5 * s, max(2, q["blobs"] // 2))
        top = pts[-1]
        for _ in range(rng.randint(1, 3)):
            _vine(mb, rng, top[0] + rng.uniform(-2, 2) * s, top[1] + rng.uniform(-2, 2) * s, top[2] - 0.5, rng.uniform(3, 6))
    top = pts[-1]
    _canopy(mb, rng, q, top[0], top[1], top[2] + 0.8 * s, 2.4 * s, 3.5 * s,
            q["blobs"] if lod else max(3, q["blobs"] // 2))


def _tree_thick(mb, rng, q, x, y, s, lod):
    h, r0 = rng.uniform(7, 10) * s, rng.uniform(0.8, 1.2) * s
    col = rng.choice(BARKS)
    pts, _ = _trunk(mb, rng, q, x, y, h, r0, r0 * 0.55, rng.uniform(-0.08, 0.08), col, 3)
    _roots(mb, rng, x, y, r0, 6 if lod else 4, r0 * 3.5, col)
    if lod:
        mb.sphere((x + r0 * 0.8, y, 1.6 * s), (0.7 * s, 0.5 * s, 0.9 * s), MOSS, rings=4, segs=6, rough=0.3)
        for _ in range(3):
            b = pts[rng.randint(1, 2)]
            a = rng.uniform(0, TAU)
            end = (b[0] + math.cos(a) * 3.5 * s, b[1] + math.sin(a) * 3.5 * s, b[2] + rng.uniform(1, 2) * s)
            mb.limb(b, end, r0 * 0.35, r0 * 0.15, col, sides=5)
            _canopy(mb, rng, q, end[0], end[1], end[2] + 0.8 * s, 1.8 * s, 3.0 * s, max(2, q["blobs"] // 2))
    top = pts[-1]
    _canopy(mb, rng, q, top[0], top[1], top[2] + 1.0 * s, 3.2 * s, 4.4 * s, q["blobs"] if lod else 3)


def _tree_ancient(mb, rng, q, x, y, s, lod):
    h, r0 = rng.uniform(13, 18) * s, rng.uniform(1.5, 2.0) * s
    col = rng.choice(BARKS)
    pts, _ = _trunk(mb, rng, q, x, y, h, r0, r0 * 0.5, rng.uniform(-0.06, 0.06), col, 5 if lod else 3)
    _roots(mb, rng, x, y, r0, 7 if lod else 4, r0 * 3.0, col)
    if lod:
        for _ in range(3):
            mb.sphere((x + rng.uniform(-r0, r0), y + rng.uniform(-r0, r0), rng.uniform(1.5, 6) * s),
                      (0.9 * s, 0.6 * s, 1.2 * s), MOSS, rings=4, segs=6, rough=0.3)
        for _ in range(3):
            a = rng.uniform(0, TAU)
            _mushroom(mb, x + math.cos(a) * r0 * 1.4, y + math.sin(a) * r0 * 1.4, 0.2, 1.8, rng.choice(FLOWERS))
        for i in range(3):
            b = pts[2 + i % 2]
            a = i * TAU / 3 + rng.uniform(-0.5, 0.5)
            end = (b[0] + math.cos(a) * 4.5 * s, b[1] + math.sin(a) * 4.5 * s, b[2] + rng.uniform(0.5, 2) * s)
            mb.limb(b, end, r0 * 0.3, r0 * 0.12, col, sides=6)
            _canopy(mb, rng, q, end[0], end[1], end[2] + 1.0 * s, 2.2 * s, 3.8 * s, max(2, q["blobs"] // 2))
        top = pts[-1]
        for _ in range(4):
            _vine(mb, rng, top[0] + rng.uniform(-4, 4) * s, top[1] + rng.uniform(-4, 4) * s, top[2], rng.uniform(5, 9))
    top = pts[-1]
    _canopy(mb, rng, q, top[0], top[1], top[2] + 1.5 * s, 4.0 * s, 5.6 * s, q["blobs"] + 1)


def _tree_small(mb, rng, q, x, y, s, lod):
    for _ in range(rng.randint(2, 3)):
        ox, oy = x + rng.uniform(-1, 1), y + rng.uniform(-1, 1)
        h, r0 = rng.uniform(4, 6.5) * s, rng.uniform(0.2, 0.3) * s
        col = rng.choice(BARKS)
        pts, _ = _trunk(mb, rng, q, ox, oy, h, r0, r0 * 0.5, rng.uniform(-0.25, 0.25), col, 3)
        top = pts[-1]
        _canopy(mb, rng, q, top[0], top[1], top[2] + 0.5 * s, 1.0 * s, 2.2 * s, max(2, q["blobs"] // 2))


def _tree_split(mb, rng, q, x, y, s, lod):
    h, r0 = rng.uniform(6, 9) * s, rng.uniform(0.6, 0.9) * s
    col = rng.choice(BARKS)
    pts, rad = _trunk(mb, rng, q, x, y, h * 0.45, r0, r0 * 0.8, 0.0, col, 2)
    fork = pts[-1]
    if lod:
        _roots(mb, rng, x, y, r0, 4, r0 * 3, col)
    for i in range(rng.randint(2, 3)):
        a = i * TAU / 3 + rng.uniform(-0.4, 0.4)
        mid = (fork[0] + math.cos(a) * 1.2 * s, fork[1] + math.sin(a) * 1.2 * s, fork[2] + 2.0 * s)
        end = (fork[0] + math.cos(a) * 2.6 * s, fork[1] + math.sin(a) * 2.6 * s, fork[2] + h * 0.6)
        mb.limb(fork, mid, r0 * 0.75, r0 * 0.55, col, sides=q["sides"])
        mb.limb(mid, end, r0 * 0.55, r0 * 0.25, col, sides=q["sides"])
        _canopy(mb, rng, q, end[0], end[1], end[2] + 0.6 * s, 1.6 * s, 3.0 * s, max(3, q["blobs"] // 2 + 1))


def _tree_palm(mb, rng, q, x, y, s, lod):
    hd = rng.uniform(0, TAU)
    px, py, pz = x, y, 0.0
    seg, r = 1.8 * s, 0.30 * s
    for i in range(5):
        tilt = math.radians(4 + i * 7)
        nx, ny, nz = (px + math.sin(tilt) * math.cos(hd) * seg, py + math.sin(tilt) * math.sin(hd) * seg,
                      pz + math.cos(tilt) * seg)
        mb.limb((px, py, pz), (nx, ny, nz), r * (1.0 - i * 0.08), r * (1.0 - (i + 1) * 0.08),
                (0.50, 0.40, 0.28), sides=q["sides"])
        px, py, pz = nx, ny, nz
    for i in range(9 if lod else 6):
        heading = i * (360 / (9 if lod else 6)) + rng.uniform(-10, 10)
        col = rng.choice(LEAVES)
        if q["cards"]:
            mb.leaf_card((px, py, pz), heading, 2.7 * s, 0.75 * s, 0.9 * s, 2.3 * s, col, segs=3)
        else:
            d = math.radians(heading)
            mb.sphere((px + math.cos(d) * 1.8 * s, py + math.sin(d) * 1.8 * s, pz - 0.2 * s),
                      (1.6 * s, 0.35 * s, 0.1 * s), col, hpr=(heading, -15, 0), rings=3, segs=5)
    for sx in (-0.2, 0.2):
        mb.sphere((px + sx, py, pz - 0.35), 0.2 * s, (0.32, 0.22, 0.10), rings=3, segs=5)


def _tree_stilt(mb, rng, q, x, y, s, lod):
    """Mangrove-like tree standing on arching roots."""
    h = rng.uniform(5, 7) * s
    col = rng.choice(BARKS)
    pts, _ = _trunk(mb, rng, q, x, y, h, 0.5 * s, 0.3 * s, 0.05, col, 3)
    for i in range(6):
        a = i * TAU / 6 + rng.uniform(-0.3, 0.3)
        reach = rng.uniform(2.0, 3.2) * s
        p0 = (x + math.cos(a) * 0.2, y + math.sin(a) * 0.2, 2.4 * s)
        pm = (x + math.cos(a) * reach * 0.6, y + math.sin(a) * reach * 0.6, 2.2 * s)
        p1 = (x + math.cos(a) * reach, y + math.sin(a) * reach, 0.0)
        mb.limb(p0, pm, 0.2 * s, 0.15 * s, col, sides=5)
        mb.limb(pm, p1, 0.15 * s, 0.07 * s, col, sides=5)
    top = pts[-1]
    _canopy(mb, rng, q, top[0], top[1], top[2] + 0.7 * s, 1.8 * s, 3.0 * s, q["blobs"])


# ---------------------------------------------------------------- ground cover
def _bush(mb, rng, q, x, y, s):
    top = 1.0
    for _ in range(rng.randint(2, 3)):
        rad = rng.uniform(0.9, 1.5) * s
        mb.sphere((x + rng.uniform(-0.8, 0.8) * s, y + rng.uniform(-0.8, 0.8) * s, rad * 0.55),
                  (rad, rad, rad * 0.7), rng.choice(LEAVES), rings=4, segs=7, rough=0.2, grad=0.6)
        top = max(top, rad)
    if rng.random() < 0.6:
        col = rng.choice(FLOWERS)
        for _ in range(rng.randint(3, 7)):
            mb.sphere((x + rng.uniform(-1, 1) * s, y + rng.uniform(-1, 1) * s, rng.uniform(0.6, 1.1) * top),
                      0.12, col, rings=2, segs=4)


def _fern(mb, rng, q, x, y, s):
    n = rng.randint(5, 7)
    for i in range(n):
        heading = i * (360 / n) + rng.uniform(-15, 15)
        col = rng.choice(LEAVES)
        if q["cards"]:
            mb.leaf_card((x, y, 0.08), heading, 1.3 * s, 0.5 * s, 0.55 * s, 0.9 * s, col, segs=3)
        else:
            d = math.radians(heading)
            mb.sphere((x + math.cos(d) * 0.8 * s, y + math.sin(d) * 0.8 * s, 0.35 * s),
                      (0.8 * s, 0.17 * s, 0.05 * s), col, hpr=(heading, -20, 0), rings=3, segs=5)


def _banana(mb, rng, q, x, y, s):
    """Big-leaf tropical plant."""
    mb.limb((x, y, 0), (x, y, 1.8 * s), 0.12 * s, 0.08 * s, (0.42, 0.60, 0.25), sides=5)
    for i in range(6):
        heading = i * 60 + rng.uniform(-15, 15)
        col = rng.choice(LEAVES[1:5])
        if q["cards"]:
            mb.leaf_card((x, y, 1.6 * s), heading, 2.4 * s, 1.1 * s, 1.0 * s, 1.9 * s, col, segs=3)
        else:
            d = math.radians(heading)
            mb.sphere((x + math.cos(d) * 1.2 * s, y + math.sin(d) * 1.2 * s, 1.4 * s),
                      (1.3 * s, 0.5 * s, 0.1 * s), col, hpr=(heading, -20, 0), rings=3, segs=5)


def _grass_tuft(mb, rng, x, y, s):
    for _ in range(4):
        h = rng.uniform(0.5, 0.95) * s
        mb.cone((x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.2, 0.2), h / 2), 0.07, h,
                _mixc(GRASS, rng.choice(SUNLIT), rng.uniform(0.2, 0.7)), sides=4,
                hpr=(0, rng.uniform(-12, 12), rng.uniform(-12, 12)), grad=0.7)


def _rock(mb, rng, x, y, s):
    rx, ry, rz = rng.uniform(0.8, 2.0) * s, rng.uniform(0.8, 2.0) * s, rng.uniform(0.6, 1.5) * s
    mb.sphere((x, y, rz * 0.35), (rx, ry, rz), rng.choice(ROCKS), hpr=(rng.uniform(0, 360), 0, 0),
              rings=4, segs=7, rough=0.2, grad=0.6)
    if rng.random() < 0.6:                                # mossy top
        mb.sphere((x, y, rz * 0.8), (rx * 0.75, ry * 0.75, rz * 0.4), MOSS, rings=3, segs=6, rough=0.25)
    for _ in range(rng.randint(0, 2)):
        a = rng.uniform(0, TAU)
        mb.sphere((x + math.cos(a) * rx * 1.1, y + math.sin(a) * ry * 1.1, 0.1),
                  rng.uniform(0.15, 0.35) * s, rng.choice(ROCKS), rings=3, segs=5, rough=0.25)


def _fallen_log(mb, rng, x, y, s):
    length, r = rng.uniform(5, 9) * s, rng.uniform(0.4, 0.7) * s
    hd = math.radians(rng.uniform(-25, 25) + 90)
    dx, dy = math.cos(hd) * length / 2, math.sin(hd) * length / 2
    col = rng.choice(BARKS)
    p0, p1 = (x - dx, y - dy, r * 0.85), (x + dx, y + dy, r * 0.85)
    mb.limb(p0, p1, r, r * 0.85, col, sides=7)
    for _ in range(2):                                    # broken branches
        t = rng.uniform(0.2, 0.8)
        bx, by = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
        mb.limb((bx, by, r * 1.3), (bx + rng.uniform(-1, 1), by + rng.uniform(-1, 1), r * 2.2), r * 0.25, r * 0.1, col, sides=5)
    t = rng.uniform(0.3, 0.7)
    mb.sphere((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, r * 1.7),
              (r * 0.9, r * 1.3, r * 0.3), MOSS, rings=3, segs=6, rough=0.25)
    _mushroom(mb, x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), r * 1.5 + 0.05, 1.2, rng.choice(FLOWERS))


def _leaf_litter(mb, rng, count, xr, y0, y1, z=0.02):
    for _ in range(count):
        x = rng.choice((-1, 1)) * rng.uniform(*xr) if xr[0] >= 6 else rng.uniform(*xr)
        y = rng.uniform(y0, y1)
        a = rng.uniform(0, TAU)
        ln, wd = rng.uniform(0.2, 0.38), rng.uniform(0.09, 0.15)
        ca, sa = math.cos(a), math.sin(a)
        zz = z + rng.uniform(0, 0.012)
        mb.quad((x - ca * ln, y - sa * ln, zz), (x - sa * wd, y + ca * wd, zz),
                (x + ca * ln, y + sa * ln, zz), (x + sa * wd, y - ca * wd, zz), rng.choice(LITTER))


def _hill(mb, rng, side, y):
    mb.sphere((side * rng.uniform(42, 66), y, -2.0),
              (rng.uniform(14, 20), rng.uniform(12, 16), rng.uniform(7, 11)),
              (0.13, 0.38, 0.13), rings=5, segs=9, rough=0.08, grad=0.6)


# ---------------------------------------------------------------- ground & path
def _ground(mb, rng, y0, y1):
    """Grass on both sides of the trail."""
    cy, ln = (y0 + y1) / 2, y1 - y0
    x = 7.5
    while x < 95:
        w = rng.uniform(5, 9)
        shade = rng.uniform(0.85, 1.12)
        col = (GRASS[0] * shade, GRASS[1] * shade, GRASS[2] * shade)
        mb.box(((x + w / 2), cy, -0.55), (w, ln, 1.0), col, grad=0.8)
        mb.box((-(x + w / 2), cy, -0.55), (w, ln, 1.0), col, grad=0.8)
        x += w


def _path(mb, rng, y0, y1, slabs=False):
    """A natural dirt trail: a grid with varied colours that fades into the grass."""
    nx, x0 = 15, -7.5
    ny = max(1, int(math.ceil((y1 - y0) / 2.0)))
    dy = (y1 - y0) / ny
    cols, zs = [], []
    for iy in range(ny + 1):
        crow, zrow = [], []
        for ix in range(nx + 1):
            x = x0 + ix
            w = _clamp((abs(x) - 5.4) / 2.1)
            f = rng.uniform(0.86, 1.10)
            if abs(abs(x) - 1.5) < 0.1:
                f *= 1.08                                 # lane dividers are a little lighter
            base = _mixc(DIRT if not slabs else (0.42, 0.34, 0.24), GRASS_EDGE, w)
            if rng.random() < 0.12:
                base = _mixc(base, DIRT_LIGHT, 0.5)       # lighter worn patches
            crow.append((base[0] * f, base[1] * f, base[2] * f))
            zrow.append(-0.05 * w)
        cols.append(crow)
        zs.append(zrow)
    for iy in range(ny):
        for ix in range(nx):
            ya, yb = y0 + iy * dy, y0 + (iy + 1) * dy
            xa, xb = x0 + ix, x0 + ix + 1
            mb.quad((xa, ya, zs[iy][ix]), (xb, ya, zs[iy][ix + 1]),
                    (xb, yb, zs[iy + 1][ix + 1]), (xa, yb, zs[iy + 1][ix]),
                    [cols[iy][ix], cols[iy][ix + 1], cols[iy + 1][ix + 1], cols[iy + 1][ix]])
    if slabs:                                              # ancient stone slabs on the trail
        for cx in (-4.5, -1.5, 1.5, 4.5):
            t = y0
            while t < y1 - 0.5:
                ln = min(4.0, y1 - t)
                mb.box((cx, t + ln / 2, -0.17 - rng.uniform(0, 0.02)), (2.85, ln - 0.1, 0.3),
                       rng.choice((STONE, STONE_DARK)), grad=0.9)
                t += 4.0


def _path_details(mb, rng, q, y0, y1, slabs=False):
    for _ in range(14):                                    # pebbles
        r = rng.uniform(0.1, 0.26)
        mb.sphere((rng.uniform(-5.7, 5.7), rng.uniform(y0, y1), 0.02), (r, r, r * 0.5),
                  rng.choice(ROCKS), rings=3, segs=5, rough=0.2)
    _leaf_litter(mb, rng, q["litter"], (0.0, 6.0), y0, y1)
    _leaf_litter(mb, rng, q["litter"] // 2, (6.0, 12.0), y0, y1)
    lane = rng.choice((-3.0, 0.0, 3.0))                    # a trail of footprints
    for i in range(10):
        yy = y0 + 1.0 + i * (y1 - y0 - 2) / 10
        side = 0.28 if i % 2 else -0.28
        mb.sphere((lane + side, yy, 0.006), (0.09, 0.17, 0.01), (0.34, 0.23, 0.14), rings=3, segs=6,
                  hpr=(rng.uniform(-8, 8), 0, 0), grad=1.0)
    for sx in (-1.5, 1.5):                                 # dashed lane lines
        yy = y0 + 1.0
        while yy < y1 - 1.5:
            mb.quad((sx - 0.07, yy, 0.014), (sx + 0.07, yy, 0.014), (sx + 0.07, yy + 1.4, 0.014),
                    (sx - 0.07, yy + 1.4, 0.014), (0.78, 0.62, 0.42))
            yy += 3.0
    for _ in range(q["grass"] // 2):                       # grass and ferns along the edges
        side = rng.choice((-1, 1))
        _grass_tuft(mb, rng, side * rng.uniform(6.2, 8.4), rng.uniform(y0, y1), rng.uniform(0.8, 1.3))
    for _ in range(2):
        _fern(mb, rng, q, rng.choice((-1, 1)) * rng.uniform(6.6, 8.0), rng.uniform(y0, y1), rng.uniform(0.6, 0.9))
    if not slabs and rng.random() < 0.55:                  # a tree root crossing the trail
        side = rng.choice((-1, 1))
        yy = rng.uniform(y0 + 2, y1 - 2)
        pts = [(side * 8.5, yy, 0.3), (side * 5.8, yy + rng.uniform(-1, 1), 0.12),
               (side * rng.uniform(1.5, 3.5), yy + rng.uniform(-1.5, 1.5), 0.06)]
        col = rng.choice(BARKS)
        mb.limb(pts[0], pts[1], 0.3, 0.2, col, sides=5)
        mb.limb(pts[1], pts[2], 0.2, 0.08, col, sides=5)


def _decor(mb, rng, q, y_ok, density=1.0):
    """Trees, palms, bushes, ferns, rocks, logs and hills on both sides."""
    def ypos():
        for _ in range(20):
            y = rng.uniform(0, L)
            if y_ok(y):
                return y
        return None

    near_types = [(_tree_tall, 3.0), (_tree_thick, 3.0), (_tree_ancient, 0.6), (_tree_small, 2.0),
                  (_tree_split, 2.0), (_tree_palm, 2.0), (_tree_stilt, 1.0)]
    far_types = [(_tree_tall, 3.0), (_tree_thick, 3.0), (_tree_palm, 2.0)]
    for side in (-1, 1):
        for _ in range(max(1, int(q["trees"] * density))):
            y = ypos()
            if y is None:
                continue
            ax = 9 + (rng.random() ** 1.4) * 33
            types = near_types if ax < 22 else far_types
            fn = rng.choices([t for t, _ in types], [w for _, w in types])[0]
            fn(mb, rng, q, side * ax, y, rng.uniform(0.8, 1.3), ax < 24)
        for _ in range(max(1, int(q["shrubs"] * density))):
            y = ypos()
            if y is not None:
                _bush(mb, rng, q, side * rng.uniform(7.5, 28), y, rng.uniform(0.7, 1.3))
        for _ in range(max(1, int(q["ferns"] * density))):
            y = ypos()
            if y is not None:
                _fern(mb, rng, q, side * rng.uniform(6.8, 20), y, rng.uniform(0.7, 1.3))
        for _ in range(rng.randint(1, 2)):
            y = ypos()
            if y is not None:
                _banana(mb, rng, q, side * rng.uniform(9, 17), y, rng.uniform(0.8, 1.2))
        for _ in range(max(1, int(q["grass"] * density) // 3)):
            y = ypos()
            if y is not None:
                _grass_tuft(mb, rng, side * rng.uniform(8, 26), y, rng.uniform(0.9, 1.5))
        for _ in range(rng.randint(2, 3)):
            y = ypos()
            if y is not None:
                _rock(mb, rng, side * rng.uniform(7.5, 25), y, rng.uniform(0.6, 1.4))
        if rng.random() < 0.65:
            y = ypos()
            if y is not None:
                _fallen_log(mb, rng, side * rng.uniform(9, 15), y, rng.uniform(0.8, 1.2))
        _leaf_litter(mb, rng, q["litter"], (12.0, 30.0), 0, L)
        _hill(mb, rng, side, rng.uniform(5, L - 5))


def _sun_rays(rng, n=3):
    """Faint translucent light shafts falling through the canopy."""
    mb = MeshBuilder(jitter=0, vjit=0)
    for _ in range(n):
        x = rng.choice((-1, 1)) * rng.uniform(4, 16)
        y = rng.uniform(4, L - 4)
        w = rng.uniform(1.0, 2.6)
        top, bot = (1.0, 0.95, 0.65, 0.20), (1.0, 0.95, 0.65, 0.02)
        mb.quad((x, y, 15), (x + w, y, 15), (x + w + 5, y, 0.1), (x + 5, y, 0.1), [top, top, bot, bot])
    np_ = mb.build("rays")
    np_.setLightOff()
    np_.setTwoSided(True)
    np_.setTransparency(TransparencyAttrib.MAlpha)
    np_.setDepthWrite(False)
    return np_


# ---------------------------------------------------------------- variants
def build_jungle(seed, q):
    rng = random.Random(seed)
    mb = MeshBuilder(seed=seed)
    _ground(mb, rng, 0, L)
    _path(mb, rng, 0, L)
    _path_details(mb, rng, q, 0, L)
    _decor(mb, rng, q, lambda y: True)
    root = NodePath("jungle")
    mb.build("main").reparentTo(root)
    _sun_rays(rng, 3).reparentTo(root)
    return root


def _pillar(mb, rng, x, y, h):
    mb.box((x, y, 0.35), (1.7, 1.7, 0.7), STONE_DARK)
    mb.cylinder((x, y, 0.7 + h / 2), 0.6, h, STONE, sides=9)
    if rng.random() < 0.5:
        mb.sphere((x, y, 0.7 + h), (0.8, 0.8, 0.45), STONE_DARK, rings=3, segs=6, rough=0.2)
    else:
        mb.box((x, y, 0.7 + h + 0.2), (1.5, 1.5, 0.4), STONE_DARK)
    mb.sphere((x + 0.4, y, 0.8), (0.8, 0.7, 0.35), MOSS, rings=3, segs=6, rough=0.2)
    _vine(mb, rng, x + 0.5, y, 0.7 + h, min(h, 3.5))


def _temple(mb, x, y):
    for i, (w, hgt) in enumerate(((15, 3), (11.5, 3), (8, 3), (5, 3))):
        mb.box((x, y, 1.5 + i * 3), (w, w, hgt), STONE if i % 2 == 0 else STONE_DARK, grad=0.7)
    mb.box((x, y, 13.2), (2.8, 2.8, 2.4), STONE)
    mb.sphere((x + 3, y + 2, 4.5), (2.5, 2.5, 1.0), MOSS, rings=3, segs=6, rough=0.25)
    mb.sphere((x - 4, y - 3, 7.5), (2.0, 2.0, 0.8), MOSS, rings=3, segs=6, rough=0.25)


def build_ruins(seed, q):
    rng = random.Random(seed)
    mb = MeshBuilder(seed=seed)
    _ground(mb, rng, 0, L)
    _path(mb, rng, 0, L, slabs=True)
    _path_details(mb, rng, q, 0, L, slabs=True)
    _decor(mb, rng, q, lambda y: True, density=0.55)
    for y in (4, 26):
        for side in (-1, 1):
            _pillar(mb, rng, side * 8.5, y, rng.uniform(3, 7))
    for side in (-1, 1):                                   # ancient gateway (high above the camera)
        mb.cylinder((side * 6.9, 15, 4.9), 0.85, 9.8, STONE, sides=9)
        mb.box((side * 6.9, 15, 0.4), (2.0, 2.0, 0.8), STONE_DARK)
        mb.sphere((side * 6.9, 15, 1.0), (1.2, 1.2, 0.6), MOSS, rings=3, segs=6, rough=0.2)
    mb.box((-4.0, 15, 9.9), (8.8, 1.6, 1.1), STONE)
    mb.box((5.9, 15, 9.8), (3.8, 1.6, 1.0), STONE_DARK)
    mb.box((1.2, 15.5, 0.4), (1.6, 1.2, 0.8), STONE_DARK, hpr=(25, 0, 0))
    mb.sphere((-6.5, 15, 8.8), (1.4, 1.4, 0.8), MOSS, rings=3, segs=6, rough=0.25)
    for k in range(3):
        _vine(mb, rng, -6.0 + k * 1.5, 15, 9.3, rng.uniform(2.5, 4.5))
    sx = rng.choice((-1, 1)) * 13                          # statue head
    mb.box((sx, 9, 1.0), (3.4, 3.4, 2.0), STONE_DARK)
    mb.sphere((sx, 9, 3.6), (1.9, 1.9, 2.1), STONE, rings=6, segs=9, rough=0.05)
    mb.sphere((sx - 0.7, 9 - 1.7, 4.0), 0.3, (0.1, 0.1, 0.1), rings=3, segs=5)
    mb.sphere((sx + 0.7, 9 - 1.7, 4.0), 0.3, (0.1, 0.1, 0.1), rings=3, segs=5)
    mb.box((sx, 9 - 1.85, 3.1), (0.6, 0.3, 0.7), STONE_DARK)
    mb.sphere((sx + 0.5, 9, 5.5), (1.2, 1.0, 0.5), MOSS, rings=3, segs=6, rough=0.3)
    _temple(mb, -rng.choice((-1, 1)) * 30, 14)
    for _ in range(5):
        _rock(mb, rng, rng.choice((-1, 1)) * rng.uniform(7, 12), rng.uniform(2, L - 2), 0.8)
    root = NodePath("ruins")
    mb.build("main").reparentTo(root)
    _sun_rays(rng, 2).reparentTo(root)
    return root


def build_river(seed, q):
    rng = random.Random(seed)
    mb = MeshBuilder(seed=seed)
    ry0, ry1 = 8.0, 22.0
    _ground(mb, rng, 0, ry0)
    _ground(mb, rng, ry1, L)
    _path(mb, rng, 0, ry0)
    _path(mb, rng, ry1, L)
    _path_details(mb, rng, q, 0, ry0)
    _path_details(mb, rng, q, ry1, L)
    _decor(mb, rng, q, lambda y: y < 5.5 or y > 24.5, density=0.8)
    mb.box((0, (ry0 + ry1) / 2, -1.4), (190, ry1 - ry0, 1.0), (0.16, 0.22, 0.19))   # river bed
    y = ry0
    while y < ry1 - 0.2:                                   # bridge planks
        mb.box((0, y + 0.45, -0.1), (11.2, 0.86, 0.2), WOOD, hpr=(0, rng.uniform(-0.6, 0.6), 0), grad=0.9)
        y += 0.95
    for side in (-1, 1):
        mb.box((side * 2.8, (ry0 + ry1) / 2, -0.5), (0.5, ry1 - ry0, 0.4), (0.30, 0.22, 0.12))
        mb.limb((side * 5.6, ry0, 1.25), (side * 5.6, ry1, 1.1), 0.07, 0.07, (0.62, 0.52, 0.34), sides=5)
        yy = ry0 + 0.3
        while yy <= ry1:
            mb.limb((side * 5.6, yy, -0.1), (side * 5.6, yy, 1.45), 0.15, 0.12, (0.34, 0.24, 0.13), sides=6)
            yy += 2.8
    for _ in range(12):                                    # reeds on the banks
        edge = rng.choice((ry0 - 0.6, ry1 + 0.6))
        bx = rng.choice((-1, 1)) * rng.uniform(7, 30)
        for k in range(3):
            mb.cone((bx + k * 0.15, edge, 0.8), 0.07, 1.6, (0.30, 0.55, 0.20), sides=4)
    for _ in range(4):
        _rock(mb, rng, rng.choice((-1, 1)) * rng.uniform(9, 30), rng.uniform(ry0 + 1, ry1 - 1), 0.9)
    for _ in range(8):                                     # lily pads
        mb.cylinder((rng.choice((-1, 1)) * rng.uniform(7, 30), rng.uniform(ry0 + 1, ry1 - 1), -0.56),
                    rng.uniform(0.3, 0.55), 0.02, (0.2, 0.5, 0.2), sides=8, smooth=False)
    root = NodePath("river")
    mb.build("main").reparentTo(root)
    wb = MeshBuilder(jitter=0, vjit=0)
    wb.quad((-95, ry0, -0.6), (95, ry0, -0.6), (95, ry1, -0.6), (-95, ry1, -0.6), (0.10, 0.46, 0.58, 0.80))
    for _ in range(14):
        wb.box((rng.uniform(-40, 40), rng.uniform(ry0 + 1, ry1 - 1), -0.58),
               (rng.uniform(2, 6), 0.12, 0.02), (0.78, 0.92, 0.96, 0.5))
    w = wb.build("water")
    w.setTransparency(TransparencyAttrib.MAlpha)
    w.reparentTo(root)
    _sun_rays(rng, 2).reparentTo(root)
    return root


BUILDERS = {"jungle": build_jungle, "river": build_river, "ruins": build_ruins}


# ---------------------------------------------------------------- manager
class Environment:
    def __init__(self, parent, quality="medium"):
        self.root = parent.attachNewNode("environment")
        self.rng = random.Random()
        self.segments = []
        self.variants = {}
        self.next_y = 0.0
        self.since_special = 0
        self.set_quality(quality)

    def set_quality(self, quality):
        """(Re)build the world pieces for a graphics quality level."""
        self.quality = quality
        self.q = QUALITY[quality]
        for seg in self.segments:
            seg["node"].removeNode()
        self.segments = []
        nj, nr, nu = self.q["variants"]
        self.variants = {
            "jungle": [build_jungle(11 + 11 * i, self.q) for i in range(nj)],
            "river": [build_river(55 + 11 * i, self.q) for i in range(nr)],
            "ruins": [build_ruins(77 + 11 * i, self.q) for i in range(nu)],
        }
        for i in range(self.q["segments"]):
            node = self.root.attachNewNode("segment%d" % i)
            self.segments.append({"node": node, "y": 0.0, "kind": "jungle"})
        self.reset()

    def reset(self):
        self.next_y = -L
        self.since_special = 0
        for i, seg in enumerate(self.segments):
            self._place(seg, self.next_y, "jungle" if i < 4 else self._pick_kind())
            self.next_y += L

    def _pick_kind(self):
        self.since_special += 1
        if self.since_special >= 3 and self.rng.random() < 0.4:
            self.since_special = 0
            return self.rng.choice(("river", "ruins", "ruins"))
        return "jungle"

    def _place(self, seg, y, kind):
        seg["node"].getChildren().detach()
        self.rng.choice(self.variants[kind]).instanceTo(seg["node"])
        seg["node"].setY(y)
        seg["y"], seg["kind"] = y, kind

    def update(self, player_y):
        for seg in self.segments:
            if seg["y"] + L < player_y - 25:
                self._place(seg, self.next_y, self._pick_kind())
                self.next_y += L

    def kind_at(self, y):
        for seg in self.segments:
            if seg["y"] <= y < seg["y"] + L:
                return seg["kind"]
        return "jungle"
