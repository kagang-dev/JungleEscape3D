"""
obstacles.py - Obstacle 3D models and the spawner that places them.

The *classes* (Log, Rock, Gap ...) are in gameobjects.py.  This file builds
their models (two variants of each, so they do not all look the same) and
decides where they appear.  The farther you run, the more often they appear
(see difficulty.py).

Obstacle families
    jump  : log, barrier, gap (broken bridge)
    slide : branch (low hanging limb)
    dodge : rock, ruin (never fill all 3 lanes, so there is always a way)
"""
import math
import random

from panda3d.core import NodePath, TransparencyAttrib

from difficulty import row_gap_seconds
from gameobjects import OBSTACLE_CLASSES
from settings import DESPAWN_BEHIND, LANES, SPAWN_AHEAD
from shapes import MeshBuilder

BARK = [(0.42, 0.29, 0.17), (0.36, 0.25, 0.15), (0.48, 0.34, 0.20)]
WOOD = (0.58, 0.40, 0.21)
WOOD_DARK = (0.36, 0.24, 0.13)
CUT = (0.80, 0.62, 0.38)
LEAF = [(0.10, 0.46, 0.13), (0.17, 0.58, 0.17), (0.09, 0.38, 0.14), (0.26, 0.62, 0.18)]
MOSS = (0.28, 0.48, 0.18)
STONE = (0.62, 0.61, 0.54)
STONE_DARK = (0.46, 0.46, 0.42)
ROCK = [(0.50, 0.50, 0.47), (0.44, 0.45, 0.43), (0.56, 0.54, 0.48)]
VINE = (0.14, 0.42, 0.14)


def _mushroom(mb, x, y, z, s=1.0):
    mb.limb((x, y, z), (x, y, z + 0.14 * s), 0.035 * s, 0.03 * s, (0.9, 0.86, 0.75), sides=5)
    mb.sphere((x, y, z + 0.16 * s), (0.1 * s, 0.1 * s, 0.06 * s), (0.82, 0.22, 0.12), rings=3, segs=6)


# ---------------------------------------------------------------- models
def _model_log(mb, rng):
    c = rng.choice(BARK)
    mb.limb((-1.35, 0, 0.45), (1.35, 0, 0.45), 0.47, 0.42, c, sides=9)
    for sx in (-1, 1):                                   # cut ends with growth rings
        mb.limb((sx * 1.34, 0, 0.45), (sx * 1.42, 0, 0.45), 0.40, 0.40, CUT, sides=9, grad=1.0)
        mb.limb((sx * 1.40, 0, 0.45), (sx * 1.46, 0, 0.45), 0.22, 0.22, (0.66, 0.48, 0.28), sides=9, grad=1.0)
    for _ in range(3):                                   # bumps / knots
        mb.sphere((rng.uniform(-1.0, 1.0), rng.uniform(-0.2, 0.2), rng.uniform(0.4, 0.8)),
                  0.17, c, rings=3, segs=6, rough=0.2)
    for _ in range(2):                                   # broken branch stubs
        x = rng.uniform(-0.9, 0.9)
        mb.limb((x, 0.1, 0.78), (x + rng.uniform(-.2, .2), 0.35, 1.05), 0.11, 0.07, c, sides=5)
    for _ in range(3):                                   # moss on top
        mb.sphere((rng.uniform(-1.1, 1.1), 0, 0.84), (rng.uniform(.25, .5), 0.28, 0.1),
                  MOSS, rings=3, segs=6, rough=0.25)
    for sx in (rng.choice((-1, 1)),):                    # roots at one end
        for k in range(3):
            a = (k - 1) * 0.6
            mb.limb((sx * 1.3, 0, 0.5), (sx * 1.85, 0.5 * a * 2, 0.05), 0.15, 0.05, c, sides=5)
    _mushroom(mb, rng.uniform(-1, 1), 0.38, 0.5, 1.0)


def _model_barrier(mb, rng):
    for sx in (-1.2, 1.2):
        mb.limb((sx, 0, 0), (sx, 0, 1.3), 0.11, 0.09, WOOD_DARK, sides=6)
        mb.cone((sx, 0, 1.45), 0.1, 0.3, WOOD_DARK, sides=6)
    mb.box((0, 0, 0.45), (2.7, 0.13, 0.22), WOOD)
    mb.box((0, 0, 0.95), (2.7, 0.13, 0.22), (0.78, 0.26, 0.16))
    mb.limb((-1.15, 0.1, 0.05), (1.1, 0.1, 1.25), 0.07, 0.07, WOOD, sides=5)      # cross beams
    mb.limb((1.15, 0.1, 0.05), (-1.1, 0.1, 1.25), 0.07, 0.07, WOOD, sides=5)
    for sx in (-0.6, 0.0, 0.6):                                                    # sharp stakes
        mb.cone((sx + rng.uniform(-.1, .1), -0.15, 1.2), 0.07, 0.38, WOOD_DARK, sides=5)
    for sx in (-1.2, 1.2):                                                         # rope bindings
        mb.cylinder((sx, 0, 0.7), 0.15, 0.08, (0.72, 0.62, 0.42), sides=7)
    mb.sphere((rng.uniform(-1, 1), 0.1, 0.12), (0.4, 0.2, 0.1), MOSS, rings=3, segs=6, rough=0.2)


def _model_rock(mb, rng):
    c = rng.choice(ROCK)
    mb.sphere((0, 0, 1.1), (1.25, 1.15, 1.5), c, hpr=(rng.uniform(0, 90), 0, 0), rings=6, segs=9, rough=0.17, grad=0.6)
    mb.sphere((0.45, 0.1, 2.05), (0.9, 0.85, 1.05), rng.choice(ROCK), hpr=(rng.uniform(0, 90), 0, 0),
              rings=5, segs=8, rough=0.15, grad=0.7)
    mb.sphere((-0.5, 0.0, 1.9), (0.6, 0.55, 0.7), rng.choice(ROCK), rings=4, segs=7, rough=0.2, grad=0.7)
    mb.sphere((-0.2, 0.0, 2.55), (0.75, 0.65, 0.3), MOSS, rings=4, segs=7, rough=0.25, grad=0.8)
    mb.sphere((0.9, -0.5, 0.9), (0.45, 0.4, 0.28), MOSS, rings=3, segs=6, rough=0.25)
    for _ in range(3):                                   # small rocks around the base
        mb.sphere((rng.uniform(-1.4, 1.4), rng.uniform(-1.0, 1.0), 0.15), rng.uniform(0.2, 0.4),
                  rng.choice(ROCK), rings=3, segs=6, rough=0.25)
    mb.limb((0.6, -0.9, 2.2), (0.8, -1.0, 0.9), 0.04, 0.035, VINE, sides=4)


def _model_ruin(mb, rng):
    mb.box((0, 0, 0.55), (2.5, 2.0, 1.1), STONE_DARK, hpr=(rng.uniform(-4, 4), 0, 0))
    mb.box((0.15, 0, 1.7), (2.0, 1.7, 1.2), STONE, hpr=(rng.uniform(4, 12), 0, 0))
    mb.cylinder((-0.45, 0, 2.8), 0.56, 1.0, STONE, sides=8)
    mb.box((0.7, 0.1, 2.5), (0.7, 0.7, 0.6), STONE_DARK, hpr=(20, 0, 15))
    for gx in (-0.6, 0.0, 0.6):                          # carved glyphs
        mb.box((gx + 0.15, -0.86, 1.7), (0.22, 0.05, 0.4), (0.25, 0.25, 0.22))
    mb.box((0, -1.01, 0.55), (1.0, 0.04, 0.5), (0.28, 0.28, 0.24))
    mb.sphere((0.9, -0.9, 0.45), (0.8, 0.5, 0.45), MOSS, rings=3, segs=6, rough=0.2)
    mb.sphere((-0.8, -0.8, 1.3), (0.5, 0.4, 0.5), MOSS, rings=3, segs=6, rough=0.2)
    mb.limb((0.4, -0.9, 2.2), (0.5, -1.0, 0.7), 0.04, 0.035, VINE, sides=4)
    mb.limb((-1.0, -0.8, 1.2), (-1.1, -0.9, 0.3), 0.04, 0.035, VINE, sides=4)


def _model_branch(mb, rng):
    c = rng.choice(BARK)
    for sx in (-1.4, 1.4):                               # two trunks hold the limb
        mb.limb((sx, 0, 0), (sx, 0, 3.2), 0.46, 0.36, c, sides=7)
        mb.limb((sx, 0, 3.2), (sx * 0.9, 0, 7.0), 0.36, 0.26, c, sides=7)
        for k in range(2):
            a = (-1 if sx < 0 else 1) * (0.3 + k * 0.6)
            mb.limb((sx, 0, 0.3), (sx + a, 0.6 - k * 1.2, 0.0), 0.2, 0.06, c, sides=5)
    mb.limb((-1.4, 0, 1.95), (1.4, 0, 1.95), 0.30, 0.26, c, sides=7)
    for sx in (-1.0, 0.1, 1.0):                          # hanging leaves
        mb.sphere((sx, 0, 2.35), (0.65, 0.65, 0.4), rng.choice(LEAF), rings=4, segs=7, rough=0.22, grad=0.6)
    for sx in (-0.7, 0.5):                               # vines (bottom stays above z=1.5)
        mb.limb((sx, 0.1, 1.9), (sx + 0.05, 0.1, 1.55), 0.045, 0.04, VINE, sides=4)
    mb.sphere((0, 0, 7.2), (2.4, 2.1, 1.0), rng.choice(LEAF), rings=4, segs=8, rough=0.2)


def _model_gap(mb, rng):
    mb.box((0, 0, 0.04), (2.9, 5.0, 0.08), (0.03, 0.02, 0.02))                  # dark hole
    for sy, tilt in ((-2.5, 12), (2.5, -12)):                                    # broken plank edges
        mb.box((0, sy, 0.08), (2.9, 0.55, 0.14), WOOD, hpr=(0, tilt, 0))
    for _ in range(3):
        mb.box((rng.uniform(-0.9, 0.9), rng.choice((-1, 1)) * rng.uniform(1.4, 2.2), 0.12),
               (0.5, rng.uniform(1.0, 1.6), 0.08), rng.choice((WOOD, WOOD_DARK)),
               hpr=(rng.uniform(-15, 15), rng.uniform(-8, 8), 0))
    for sx in (-1.45, 1.45):
        for sy in (-2.5, 2.5):
            mb.limb((sx, sy, 0), (sx, sy, 0.95), 0.13, 0.1, WOOD_DARK, sides=5)  # post stumps
    mb.limb((-1.45, -2.5, 0.8), (-1.2, -1.0, 0.1), 0.03, 0.03, (0.7, 0.6, 0.4), sides=4)   # dangling rope
    mb.limb((1.45, 2.5, 0.8), (1.2, 1.0, 0.1), 0.03, 0.03, (0.7, 0.6, 0.4), sides=4)


MODELS = {"log": _model_log, "barrier": _model_barrier, "rock": _model_rock,
          "ruin": _model_ruin, "branch": _model_branch, "gap": _model_gap}
SHADOWS = {"log": (1.5, 0.8), "barrier": (1.4, 0.6), "rock": (1.7, 1.5),
           "ruin": (1.6, 1.4), "branch": (1.6, 0.8)}


def _build_model(kind, seed):
    rng = random.Random(seed)
    mb = MeshBuilder(seed=seed)
    MODELS[kind](mb, rng)
    root = NodePath(kind)
    mb.build("main").reparentTo(root)
    if kind in SHADOWS:                                  # soft blob shadow on the ground
        sx, sy = SHADOWS[kind]
        sb = MeshBuilder(jitter=0, vjit=0)
        sb.cylinder((0, 0, 0.03), 1.0, 0.01, (0, 0, 0, 0.30), sides=14, smooth=False)
        sh = sb.build("shadow")
        sh.setScale(sx, sy, 1)
        sh.setTransparency(TransparencyAttrib.MAlpha)
        sh.setDepthWrite(False)
        sh.setLightOff()
        sh.reparentTo(root)
    return root


# ---------------------------------------------------------------- manager
class ObstacleManager:
    def __init__(self, parent, environment, coins):
        self.root = parent.attachNewNode("obstacles")
        self.env = environment
        self.coins = coins
        self.models = {k: [_build_model(k, s) for s in (1, 2, 3)] for k in MODELS}
        self.rng = random.Random()
        self.items = []
        self.next_y = 70.0

    def reset(self):
        for o in self.items:
            o.remove()
        self.items = []
        self.next_y = 70.0

    # ------------------------------------------------------------ spawning
    def update(self, dt, player, speed, level):
        while self.next_y < player.y + SPAWN_AHEAD:
            y = self.next_y
            kind = self._spawn_row(y, level, None)
            lo, hi = row_gap_seconds(level)
            self.next_y = y + self.rng.uniform(lo, hi) * speed + 5.0
            # later in the game: a second row follows quickly (jump, then slide...)
            combo = 0.45 * max(0.0, level - 0.3) / 0.7
            if self.rng.random() < combo:
                y2 = y + self.rng.uniform(0.80, 0.95) * speed + 4.0
                self._spawn_row(y2, level, OBSTACLE_CLASSES[kind].NEEDS)
                self.next_y = max(self.next_y, y2 + self.rng.uniform(lo, hi) * speed)
        for o in self.items:
            if o.is_behind(player.y - DESPAWN_BEHIND):
                o.remove()
        self.items = [o for o in self.items if not o.removed]

    def _pick_kind(self, y, level, avoid):
        def ramp(start, width):
            return max(0.0, min(1.0, (level - start) / width))
        weights = {"log": 3.0, "barrier": 2.2, "branch": 2.0, "rock": 1.5,
                   "ruin": 1.4 * ramp(0.10, 0.2), "gap": 1.2 * ramp(0.06, 0.15)}
        if self.env.kind_at(y) == "river":
            weights["gap"] *= 3.0
        if avoid:                                        # make a different kind of challenge
            for k in weights:
                if OBSTACLE_CLASSES[k].NEEDS == avoid:
                    weights[k] *= 0.15
        kinds = list(weights)
        return self.rng.choices(kinds, [weights[k] for k in kinds])[0]

    def _spawn_row(self, y, level, avoid):
        kind = self._pick_kind(y, level, avoid)
        cls = OBSTACLE_CLASSES[kind]
        p3 = 0.08 + 0.32 * level
        p2 = 0.30 + 0.20 * level
        r = self.rng.random()
        count = 3 if r < p3 else (2 if r < p3 + p2 else 1)
        if cls.NEEDS == "dodge":
            count = min(count, 2)                        # always leave a free lane
        lanes = self.rng.sample(range(3), count)
        for lane in lanes:
            node = self.rng.choice(self.models[kind]).copyTo(self.root)
            node.setPos(LANES[lane], y, 0)
            node.setH(self.rng.uniform(-6, 6) if kind in ("log", "rock", "ruin") else 0)
            self.items.append(cls(node, LANES[lane], y))
        if cls.NEEDS == "jump" and self.rng.random() < 0.6:
            span = 6.5 if kind == "gap" else 4.5
            self.coins.spawn_arc(LANES[self.rng.choice(lanes)], y, span)
        return kind

    def row_near(self, y0, y1):
        """True if any obstacle lies between y0 and y1 (used by the coin spawner)."""
        for o in self.items:
            if y0 <= o.y <= y1:
                return True
        return False
