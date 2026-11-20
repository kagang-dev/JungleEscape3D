"""
coins.py - Coin model, coin patterns and the pick-up effects.

The Coin *class* lives in gameobjects.py.  This file builds the shiny gold
model, creates coin patterns (lines, zig-zags, diagonals, snakes) that get
harder with the difficulty level, and shows the sparkle effect when you
collect a coin.
"""
import math
import random

from panda3d.core import Material, NodePath, TransparencyAttrib

from gameobjects import Coin
from settings import DESPAWN_BEHIND, LANES, SPAWN_AHEAD
from shapes import MeshBuilder

GOLD = (1.0, 0.78, 0.10)
GOLD_DARK = (0.80, 0.55, 0.05)
GOLD_LIGHT = (1.0, 0.93, 0.50)


def _build_disc():
    """Gold coin with a raised rim, an embossed centre and a star."""
    mb = MeshBuilder(jitter=0, vjit=0.02)
    mb.limb((0, -0.045, 0), (0, 0.045, 0), 0.42, 0.42, GOLD, sides=20, grad=1.0)
    mb.limb((0, -0.06, 0), (0, 0.06, 0), 0.46, 0.46, GOLD_DARK, sides=20, grad=1.0)   # rim
    mb.limb((0, -0.05, 0), (0, 0.05, 0), 0.37, 0.37, GOLD, sides=20, grad=1.0)        # inside rim
    mb.limb((0, -0.075, 0), (0, 0.075, 0), 0.26, 0.26, GOLD_LIGHT, sides=16, grad=1.0)  # emboss
    mb.box((0, 0, 0), (0.30, 0.17, 0.08), GOLD, hpr=(0, 0, 0))                         # star
    mb.box((0, 0, 0), (0.30, 0.17, 0.08), GOLD, hpr=(0, 0, 45))
    mb.box((0, 0, 0), (0.30, 0.17, 0.08), GOLD, hpr=(0, 0, 90))
    mb.box((0, 0, 0), (0.30, 0.17, 0.08), GOLD, hpr=(0, 0, 135))
    disc = mb.build("disc")
    m = Material()                                       # glossy metal + warm glow
    m.setSpecular((1.0, 0.95, 0.7, 1))
    m.setShininess(45)
    m.setEmission((0.30, 0.20, 0.02, 1))
    disc.setMaterial(m)
    return disc


def _build_halo():
    mb = MeshBuilder(jitter=0, vjit=0)
    for r, a in ((0.95, 0.10), (0.7, 0.14), (0.5, 0.18)):
        mb.limb((0, 0.0, 0), (0, 0.02, 0), r, r, (1.0, 0.85, 0.3, a), sides=18, smooth=False, grad=1.0)
    halo = mb.build("halo")
    halo.setLightOff()
    halo.setTransparency(TransparencyAttrib.MAlpha)
    halo.setDepthWrite(False)
    return halo


class CoinManager:
    def __init__(self, parent):
        self.root = parent.attachNewNode("coins")
        self.rng = random.Random()
        self.obstacles = None            # set by main.py after creation
        self.coins = []
        self.effects = []
        self.next_y = 40.0
        self.speed = 15.0
        self.disc = _build_disc()
        self.halo = _build_halo()

        mb = MeshBuilder(jitter=0, vjit=0)
        mb.sphere((0, 0, 0), 0.16, GOLD_LIGHT, rings=2, segs=4, smooth=False)
        self.spark = mb.build("spark")
        self.spark.setLightOff()
        mb = MeshBuilder(jitter=0, vjit=0)
        mb.limb((0, -0.01, 0), (0, 0.01, 0), 0.5, 0.5, (1.0, 0.9, 0.4, 0.55), sides=18, smooth=False, grad=1.0)
        self.ring = mb.build("ring")
        self.ring.setLightOff()
        self.ring.setTransparency(TransparencyAttrib.MAlpha)
        self.ring.setDepthWrite(False)

    def reset(self):
        for c in self.coins:
            c.remove()
        for e in self.effects:
            e["node"].removeNode()
        self.coins, self.effects = [], []
        self.next_y = 40.0

    # ------------------------------------------------------------ creation
    def add_coin(self, x, y, z=1.0):
        holder = self.root.attachNewNode("coin")
        holder.setPos(x, y, z)
        disc = self.disc.copyTo(holder)
        halo = self.halo.copyTo(holder)
        halo.setBillboardPointEye()
        self.coins.append(Coin(holder, disc, x, y, z))

    def spawn_arc(self, x, y, span):
        """Coins that follow a jump arc above an obstacle."""
        n = 7
        for i in range(n):
            t = (i / (n - 1)) * 2 - 1
            self.add_coin(x, y + t * span, 1.0 + 1.5 * (1 - t * t))

    # ------------------------------------------------------------ patterns
    def _pattern(self, level, speed):
        """Return (list of (lane, distance), total length) for a random pattern."""
        r = self.rng
        sp = 2.4 + (speed - 15.0) * 0.03                 # coins spread out when faster
        weights = {"line": 3.0 - 1.5 * level, "zigzag": 1.0 + 2.0 * level,
                   "diag": 0.5 + 2.0 * level, "rows": 1.5,
                   "snake": 2.0 * max(0.0, min(1.0, (level - 0.35) / 0.3))}
        kind = r.choices(list(weights), list(weights.values()))[0]
        pts = []
        if kind == "line":
            lane = r.randrange(3)
            pts = [(lane, i * sp) for i in range(r.randint(5, 9))]
        elif kind == "zigzag":
            lane = r.randrange(3)
            for i in range(8):
                pts.append((lane, i * sp * 1.3))
                lane = max(0, min(2, lane + r.choice((-1, 1))))
        elif kind == "diag":
            lanes = [0, 1, 2, 1, 0, 1, 2] if r.random() < 0.5 else [2, 1, 0, 1, 2, 1, 0]
            pts = [(ln, i * sp * 1.5) for i, ln in enumerate(lanes[:r.randint(5, 7)])]
        elif kind == "rows":
            for i in range(3):
                for lane in r.sample(range(3), r.randint(1, 3)):
                    pts.append((lane, i * sp * 1.6))
        else:                                            # snake: long and twisty
            lane, d = r.randrange(3), 0.0
            for i in range(14):
                pts.append((lane, d))
                d += sp * 1.1
                if i % 3 == 2:
                    lane = max(0, min(2, lane + r.choice((-1, 1))))
        return pts, max(d for _, d in pts)

    # ------------------------------------------------------------ update
    def update(self, dt, player, speed, level):
        obs = self.obstacles
        self.speed = speed
        while self.next_y < player.y + SPAWN_AHEAD:
            pts, length = self._pattern(level, speed)
            if self.next_y + length > obs.next_y - 6:
                break                                    # wait until obstacles are decided
            if obs.row_near(self.next_y - 9, self.next_y + length + 9):
                self.next_y += 5.0
                continue
            for lane, d in pts:
                self.add_coin(LANES[lane], self.next_y + d)
            self.next_y += length + self.rng.uniform(10, 28)

        behind = player.y - DESPAWN_BEHIND
        for c in self.coins:
            if c.is_behind(behind):
                c.remove()
        self.coins = [c for c in self.coins if not c.removed]
        self._update_effects(dt)

    # ------------------------------------------------------------ effects
    def collected(self, coin):
        """Remove a collected coin and play the sparkle effect."""
        x, y, z = coin.x, coin.y, coin.z
        coin.remove()
        r = self.rng
        for _ in range(8):
            node = self.spark.copyTo(self.root)
            node.setPos(x, y, z)
            self.effects.append({"node": node, "life": 0.5, "max": 0.5, "ring": False,
                                 "v": [r.uniform(-3, 3), r.uniform(-1, 5) + self.speed * 0.2, r.uniform(2, 6)]})
        ring = self.ring.copyTo(self.root)
        ring.setPos(x, y, z)
        self.effects.append({"node": ring, "life": 0.3, "max": 0.3, "ring": True,
                             "v": [0, self.speed * 0.5, 0]})

    def _update_effects(self, dt):
        keep = []
        for e in self.effects:
            e["life"] -= dt
            node = e["node"]
            if e["life"] <= 0:
                node.removeNode()
                continue
            k = e["life"] / e["max"]
            if e["ring"]:
                node.setScale(1.0 + (1.0 - k) * 2.2)
                node.setColorScale(1, 1, 1, k)
                node.setY(node.getY() + e["v"][1] * dt)
            else:
                e["v"][2] -= 14.0 * dt
                node.setPos(node.getX() + e["v"][0] * dt, node.getY() + e["v"][1] * dt,
                            node.getZ() + e["v"][2] * dt)
                node.setScale(max(0.05, k))
            keep.append(e)
        self.effects = keep
