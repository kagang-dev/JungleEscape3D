"""
camera.py - Third-person chase camera (plus a slow orbit for the main menu).
"""
import math
import random

from panda3d.core import Vec3


class ChaseCamera:
    def __init__(self, base, player):
        self.base = base
        self.cam = base.camera
        self.lens = base.camLens
        self.player = player
        self.mode = "menu"              # "menu" or "follow"
        self.pos = Vec3(0, -8, 4)
        self.look = Vec3(0, 0, 1)
        self.t = 0.0
        self.shake = 0.0
        self.speed = 16.0
        self.rng = random.Random()

    def set_mode(self, mode):
        self.mode = mode

    def kick(self, amount):
        """A short, gentle camera shake (used on crash)."""
        self.shake = amount

    def set_speed(self, speed):
        self.speed = speed

    # ------------------------------------------------------------ targets
    def _targets(self):
        p = self.player
        if self.mode == "menu":
            a = 1.4 + math.sin(self.t * 0.25) * 0.8
            pos = Vec3(p.x + math.sin(a) * 5.5, p.y - math.cos(a) * 5.5, 2.1)
            focus = Vec3(p.x, p.y, 1.2)
            fwd = focus - pos
            fwd.normalize()
            right = fwd.cross(Vec3(0, 0, 1))
            right.normalize()
            # look a bit to the left of the hero so he appears on the right of the screen
            return pos, focus - right * 2.0
        back = 9.0 + (self.speed - 15.0) * 0.06
        run = p.state == "running" and p.on_ground
        # subtle running bob + a small dip when landing (kept tiny: no motion sickness)
        bob = math.sin(p.run_phase * 2.0) * 0.035 if run else 0.0
        sway = math.sin(p.run_phase) * 0.04 if run else 0.0
        pos = Vec3(p.x * 0.55 + sway, p.y - back, 5.0 + p.z * 0.25 + bob - p.land_kick * 0.3)
        look = Vec3(p.x * 0.6, p.y + 14.0, 1.4 + p.z * 0.15)
        return pos, look

    @staticmethod
    def _axis(cur, target, k, lock):
        diff = target - cur
        return target if abs(diff) < lock else cur + diff * k

    def snap(self):
        self.pos, self.look = self._targets()
        self._apply()

    def update(self, dt):
        self.t += dt
        pos, look = self._targets()
        k_pos = 1.0 - math.exp(-6.0 * dt)
        k_look = 1.0 - math.exp(-8.0 * dt)
        if self.mode == "follow":
            k_y = 1.0 - math.exp(-10.0 * dt)
            # Y follows the player exactly (no lag) unless we are far away
            # (for example right after leaving the menu), then it glides.
            self.pos.y = self._axis(self.pos.y, pos.y, k_y, 0.6)
            self.look.y = self._axis(self.look.y, look.y, k_y, 1.2)
            self.pos.x = self.pos.x + (pos.x - self.pos.x) * k_pos
            self.pos.z = self.pos.z + (pos.z - self.pos.z) * k_pos
            self.look.x = self.look.x + (look.x - self.look.x) * k_look
            self.look.z = self.look.z + (look.z - self.look.z) * k_look
        else:
            self.pos = self.pos + (pos - self.pos) * k_pos
            self.look = self.look + (look - self.look) * k_look
        # field of view widens slightly with speed
        fov = 62.0 + (self.speed - 15.0) / 29.0 * 12.0 if self.mode == "follow" else 55.0
        cur = self.lens.getFov()[0]
        self.lens.setFov(cur + (fov - cur) * (1.0 - math.exp(-3.0 * dt)))
        self._apply()
        self.shake = max(0.0, self.shake - dt * 1.2)

    def _apply(self):
        off = Vec3(0, 0, 0)
        if self.shake > 0:
            off = Vec3(self.rng.uniform(-1, 1), 0, self.rng.uniform(-1, 1)) * self.shake * 0.5
        self.cam.setPos(self.pos + off)
        self.cam.lookAt(self.look + off)
