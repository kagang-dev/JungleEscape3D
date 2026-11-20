"""
player.py - The jungle explorer: detailed procedural model, animation, movement.

Coordinate system used everywhere in the game:
    X = left/right (lanes)     Y = forward (running direction)     Z = up

New in v2: tapered limbs, face, explorer hat with feather, scarf, gloves, boots,
backpack with bedroll, landing animation, lives and a blinking "invincible" state.
"""
import math

from panda3d.core import NodePath, TransparencyAttrib

from settings import (FAST_FALL_VELOCITY, GRAVITY, JUMP_VELOCITY, LANES,
                      LANE_SWITCH_SPEED, PLAYER_HALF_DEPTH, PLAYER_HALF_WIDTH,
                      PLAYER_HEIGHT, PLAYER_SLIDE_HEIGHT, SLIDE_TIME)
from shapes import MeshBuilder

SKIN = (0.88, 0.67, 0.50)
SHIRT = (0.82, 0.72, 0.46)
VEST = (0.30, 0.42, 0.26)
PANTS = (0.40, 0.33, 0.24)
BOOTS = (0.28, 0.18, 0.11)
LEATHER = (0.45, 0.30, 0.16)
HAT = (0.58, 0.40, 0.20)
HAT_BAND = (0.62, 0.14, 0.10)
PACK = (0.26, 0.42, 0.30)
SCARF = (0.78, 0.20, 0.16)
HAIR = (0.25, 0.15, 0.08)

POSE_KEYS = ("rh", "lh", "rk", "lk", "ra", "la", "re", "le", "lean", "pz", "pitch", "tw", "bx")


def _lerp(a, b, t):
    return a + (b - a) * t


class Player:
    def __init__(self, parent):
        self.root = parent.attachNewNode("player")
        self.model = self.root.attachNewNode("model")
        self._build_model()
        self._build_shadow()
        self.cur = {k: 0.0 for k in POSE_KEYS}
        self.cur["pz"] = 0.85
        self.lives = 3
        self.reset()

    # ------------------------------------------------------------ model
    def _part(self, parent, name, fn, jitter=0.0):
        mb = MeshBuilder(jitter=jitter, vjit=0.015)
        fn(mb)
        np_ = mb.build(name)
        np_.reparentTo(parent)
        return np_

    def _build_model(self):
        self.body = self.model.attachNewNode("body")          # pivots around the hips
        self.body.setPos(0, 0, 0.85)

        self.torso = self.body.attachNewNode("torso")

        def torso(mb):
            mb.sphere((0, 0, 0.12), (0.25, 0.17, 0.17), SHIRT, rings=5, segs=8, grad=0.8)      # belly
            mb.sphere((0, 0, 0.40), (0.29, 0.19, 0.27), SHIRT, rings=5, segs=8, grad=0.85)     # chest
            mb.box((0, 0.03, 0.02), (0.50, 0.30, 0.07), LEATHER)                              # belt
            mb.box((0, 0.17, 0.02), (0.10, 0.04, 0.08), (0.85, 0.7, 0.3))                     # buckle
            mb.box((0.27, 0.05, 0.02), (0.14, 0.14, 0.17), LEATHER)                           # pouch
            mb.limb((-0.27, 0.0, 0.62), (0.15, 0.16, 0.08), 0.045, 0.045, LEATHER, sides=5)   # strap
            mb.sphere((0, 0.1, 0.42), (0.26, 0.12, 0.22), VEST, rings=4, segs=8, grad=0.8)    # vest
            mb.sphere((0.36, 0, 0.55), 0.10, VEST, rings=3, segs=6)                           # shoulder pads
            mb.sphere((-0.36, 0, 0.55), 0.10, VEST, rings=3, segs=6)
            mb.limb((0, 0, 0.58), (0, 0, 0.72), 0.07, 0.065, SKIN, sides=6)                   # neck
            mb.cylinder((0, 0, 0.66), 0.115, 0.09, SCARF, sides=8)                            # scarf
            mb.sphere((0.06, 0.12, 0.62), 0.05, SCARF, rings=3, segs=5)
            mb.limb((0.06, -0.08, 0.64), (0.12, -0.38, 0.5), 0.045, 0.03, SCARF, sides=4)     # scarf tail
        self._part(self.torso, "torso", torso)

        def pack(mb):
            mb.box((0, -0.25, 0.34), (0.38, 0.19, 0.44), PACK, grad=0.8)
            mb.box((0, -0.27, 0.50), (0.34, 0.20, 0.18), (0.32, 0.48, 0.34))                  # flap
            mb.limb((-0.2, -0.27, 0.68), (0.2, -0.27, 0.68), 0.09, 0.09, (0.78, 0.68, 0.45), sides=7)  # bedroll
            mb.sphere((0.3, -0.2, 0.30), (0.07, 0.07, 0.11), (0.35, 0.45, 0.55), rings=3, segs=6)      # canteen
            mb.limb((-0.14, -0.14, 0.60), (-0.12, 0.13, 0.55), 0.03, 0.03, LEATHER, sides=4)  # straps
            mb.limb((0.14, -0.14, 0.60), (0.12, 0.13, 0.55), 0.03, 0.03, LEATHER, sides=4)
        self._part(self.torso, "pack", pack)

        # head: face, hair, hat
        self.head = self.torso.attachNewNode("head")
        self.head.setPos(0, 0, 0.84)

        def head(mb):
            mb.sphere((0, 0, 0), (0.165, 0.18, 0.2), SKIN, rings=6, segs=10, grad=0.9)
            mb.sphere((0, -0.04, 0.03), (0.17, 0.17, 0.19), HAIR, rings=5, segs=8, grad=0.9)  # hair at back
            for sx in (-1, 1):
                mb.sphere((sx * 0.065, 0.155, 0.03), 0.04, (0.97, 0.97, 0.95), rings=4, segs=6)   # eye white
                mb.sphere((sx * 0.065, 0.188, 0.03), 0.022, (0.12, 0.08, 0.05), rings=3, segs=5)  # pupil
                mb.box((sx * 0.07, 0.17, 0.085), (0.07, 0.025, 0.02), HAIR, hpr=(0, 0, sx * -12))  # eyebrow
                mb.sphere((sx * 0.17, 0.0, -0.01), 0.04, SKIN, rings=3, segs=5)                 # ears
            mb.sphere((0, 0.185, -0.03), 0.035, (0.82, 0.60, 0.44), rings=3, segs=6)            # nose
            mb.box((0, 0.17, -0.09), (0.07, 0.02, 0.018), (0.55, 0.25, 0.2))                   # mouth
            mb.cylinder((0, 0, 0.13), 0.31, 0.035, HAT, sides=14)                               # brim
            mb.cylinder((0, 0, 0.215), 0.19, 0.16, HAT, top=0.82, sides=12)                     # crown
            mb.cylinder((0, 0, 0.165), 0.196, 0.05, HAT_BAND, sides=12)                         # band
            mb.limb((0.15, 0.0, 0.18), (0.30, -0.10, 0.34), 0.03, 0.01, (0.85, 0.25, 0.2), sides=4)  # feather
        self._part(self.head, "headmesh", head)

        # arms: sleeve, rolled cuff, forearm, leather glove
        self.arm_sh, self.arm_el = {}, {}
        for side, sx in (("r", 0.38), ("l", -0.38)):
            sh = self.torso.attachNewNode("shoulder_" + side)
            sh.setPos(sx, 0, 0.55)

            def upper(mb):
                mb.limb((0, 0, 0), (0, 0, -0.29), 0.075, 0.062, SHIRT, sides=7)
            self._part(sh, "upper_" + side, upper)
            el = sh.attachNewNode("elbow_" + side)
            el.setPos(0, 0, -0.29)

            def fore(mb):
                mb.sphere((0, 0, 0), 0.066, SHIRT, rings=3, segs=6)
                mb.cylinder((0, 0, -0.03), 0.07, 0.05, (0.7, 0.6, 0.38), sides=7)           # cuff
                mb.limb((0, 0, -0.04), (0, 0, -0.25), 0.056, 0.045, SKIN, sides=7)
                mb.sphere((0, 0, -0.29), (0.062, 0.07, 0.07), LEATHER, rings=4, segs=6)    # glove
                mb.cylinder((0, 0, -0.22), 0.052, 0.05, LEATHER, sides=7)
            self._part(el, "fore_" + side, fore)
            self.arm_sh[side], self.arm_el[side] = sh, el

        # legs: thigh, knee pad, shin, gaiter, boot
        self.leg_hip, self.leg_knee, self.leg_ankle = {}, {}, {}
        for side, sx in (("r", 0.13), ("l", -0.13)):
            hip = self.body.attachNewNode("hip_" + side)
            hip.setPos(sx, 0, 0.0)

            def thigh(mb):
                mb.limb((0, 0, 0.0), (0, 0, -0.40), 0.105, 0.080, PANTS, sides=8)
            self._part(hip, "thigh_" + side, thigh)
            knee = hip.attachNewNode("knee_" + side)
            knee.setPos(0, 0, -0.40)

            def shin(mb):
                mb.sphere((0, 0.03, 0), (0.085, 0.09, 0.08), LEATHER, rings=3, segs=6)       # knee pad
                mb.limb((0, 0, 0), (0, 0, -0.38), 0.080, 0.062, PANTS, sides=8)
                mb.cylinder((0, 0, -0.28), 0.072, 0.15, LEATHER, sides=8)                    # gaiter
            self._part(knee, "shin_" + side, shin)
            ankle = knee.attachNewNode("ankle_" + side)
            ankle.setPos(0, 0, -0.38)

            def boot(mb):
                mb.sphere((0, 0.06, -0.03), (0.085, 0.16, 0.075), BOOTS, rings=4, segs=7, grad=0.8)
                mb.box((0, 0.06, -0.09), (0.15, 0.32, 0.04), (0.14, 0.09, 0.06))             # sole
                mb.box((0, 0.10, 0.02), (0.07, 0.10, 0.02), (0.85, 0.8, 0.6))                # laces
            self._part(ankle, "boot_" + side, boot)
            self.leg_hip[side], self.leg_knee[side], self.leg_ankle[side] = hip, knee, ankle

    def _build_shadow(self):
        mb = MeshBuilder(jitter=0, vjit=0)
        mb.cylinder((0, 0, 0), 0.55, 0.02, (0, 0, 0, 0.35), sides=14, smooth=False)
        self.shadow = mb.build("blob_shadow")
        self.shadow.reparentTo(self.root)
        self.shadow.setLightOff()
        self.shadow.setTransparency(TransparencyAttrib.MAlpha)
        self.shadow.setDepthWrite(False)
        self.shadow.setZ(0.04)

    # ------------------------------------------------------------ state
    def reset(self):
        self.lives = 3
        self.lane = 1
        self.x = LANES[1]
        self.y = 0.0
        self.z = 0.0
        self.vz = 0.0
        self.on_ground = True
        self.sliding = False
        self.slide_timer = 0.0
        self.queued_slide = False
        self.state = "idle"          # idle | running | crashed | falling
        self.run_phase = 0.0
        self.time = 0.0
        self.crash_time = 0.0
        self.crash_speed = 0.0
        self.land_timer = 0.0
        self.land_kick = 0.0
        self.invincible = 0.0
        self.model.setHpr(0, 0, 0)
        self.model.setZ(0)
        self.model.show()
        self._apply()

    def start_run(self):
        self.state = "running"

    def recover(self, forward):
        """Lose a life but keep playing: stand up again and blink for a moment."""
        self.state = "running"
        self.y += forward
        self.z, self.vz, self.on_ground = 0.0, 0.0, True
        self.sliding = False
        self.queued_slide = False
        self.invincible = 2.2
        self.model.setHpr(0, 0, 0)
        self.model.setZ(0)
        self.crash_speed = 0.0

    @property
    def height(self):
        return PLAYER_SLIDE_HEIGHT if self.sliding else PLAYER_HEIGHT

    def hitbox(self):
        return (self.x - PLAYER_HALF_WIDTH, self.x + PLAYER_HALF_WIDTH,
                self.y - PLAYER_HALF_DEPTH, self.y + PLAYER_HALF_DEPTH,
                self.z, self.z + self.height)

    # ------------------------------------------------------------ input
    def move_left(self):
        if self.state == "running" and self.lane > 0:
            self.lane -= 1
            return True
        return False

    def move_right(self):
        if self.state == "running" and self.lane < 2:
            self.lane += 1
            return True
        return False

    def jump(self):
        if self.state == "running" and self.on_ground:
            self.vz = JUMP_VELOCITY
            self.on_ground = False
            self.sliding = False
            self.queued_slide = False
            return True
        return False

    def slide(self):
        if self.state != "running":
            return False
        if self.on_ground:
            self.sliding = True
            self.slide_timer = SLIDE_TIME
            return True
        self.vz = min(self.vz, FAST_FALL_VELOCITY)
        self.queued_slide = True
        return False

    # ------------------------------------------------------------ update
    def update(self, dt, speed):
        """Called every frame while the game is running."""
        self.y += speed * dt
        step = LANE_SWITCH_SPEED * dt
        diff = LANES[self.lane] - self.x
        self.x += max(-step, min(step, diff))

        if not self.on_ground:
            self.vz -= GRAVITY * dt
            self.z += self.vz * dt
            if self.z <= 0.0:
                impact = -self.vz
                self.z, self.vz, self.on_ground = 0.0, 0.0, True
                if impact > 8.0:
                    self.land_timer = 0.17                      # squat when landing
                    self.land_kick = min(1.0, impact / 24.0)    # camera dips a little
                if self.queued_slide:
                    self.queued_slide = False
                    self.sliding = True
                    self.slide_timer = SLIDE_TIME
        if self.sliding:
            self.slide_timer -= dt
            if self.slide_timer <= 0:
                self.sliding = False
        self.land_timer = max(0.0, self.land_timer - dt)
        self.land_kick = max(0.0, self.land_kick - dt * 3.5)

        if self.invincible > 0:                                  # blink while protected
            self.invincible = max(0.0, self.invincible - dt)
            if self.invincible > 0 and int(self.invincible * 10) % 2 == 0:
                self.model.hide()
            else:
                self.model.show()

        self.run_phase += dt * speed * 0.55
        self._pose(dt, self._target_pose(speed))
        self._apply()

    def update_idle(self, dt):
        """Standing still (main menu)."""
        self.time += dt
        s = math.sin(self.time * 2.2)
        pose = dict(rh=0, lh=0, rk=0, lk=0, ra=4 + s * 3, la=4 - s * 3, re=14, le=14,
                    lean=0, pz=0.85 + s * 0.012, pitch=0, tw=0, bx=0)
        self._pose(dt, pose)
        self.model.setHpr(math.sin(self.time * 0.6) * 6, 0, 0)
        self._apply()

    # ------------------------------------------------------------ crash
    def crash(self, kind):
        self.sliding = False
        self.crash_time = 0.0
        self.model.show()
        if kind == "gap":
            self.state = "falling"
            self.crash_speed = 8.0
            self.vz = max(self.vz, 0.0) * 0.2
            self.on_ground = False
        else:
            self.state = "crashed"
            self.crash_speed = 5.0

    def update_crashed(self, dt):
        self.crash_time += dt
        self.y += self.crash_speed * dt
        self.crash_speed = max(0.0, self.crash_speed - 14.0 * dt)
        if self.state == "falling":
            self.vz -= GRAVITY * 0.6 * dt
            self.z = max(-8.0, self.z + self.vz * dt)
            pose = dict(rh=30, lh=-20, rk=-40, lk=-10, ra=-160, la=-150, re=20, le=20,
                        lean=-15, pz=0.85, pitch=0, tw=0, bx=0)
        else:
            if not self.on_ground:
                self.vz -= GRAVITY * dt
                self.z = max(0.0, self.z + self.vz * dt)
                if self.z == 0.0:
                    self.on_ground = True
            k = min(1.0, self.crash_time / 0.35)
            self.model.setP(-80 * k)
            self.model.setZ(0.25 * k)
            pose = dict(rh=25, lh=-25, rk=-20, lk=-35, ra=-50, la=-80, re=30, le=30,
                        lean=0, pz=0.85, pitch=0, tw=0, bx=0)
        self._pose(dt, pose, rate=14.0)
        self._apply()

    # ------------------------------------------------------------ animation
    def _target_pose(self, speed):
        if self.sliding:
            return dict(rh=0, lh=0, rk=0, lk=0, ra=25, la=25, re=35, le=35,
                        lean=0, pz=0.42, pitch=72, tw=0, bx=0)
        if not self.on_ground:
            rising = self.vz > 0
            return dict(rh=50 if rising else 30, lh=-20 if rising else 10,
                        rk=-80 if rising else -45, lk=-25 if rising else -35,
                        ra=-150 if rising else -110, la=-150 if rising else -110,
                        re=20, le=20, lean=-6, pz=0.85, pitch=0, tw=0, bx=0)
        if self.land_timer > 0:                                  # landing squat
            return dict(rh=38, lh=38, rk=-60, lk=-60, ra=-20, la=-20, re=40, le=40,
                        lean=-22, pz=0.68, pitch=0, tw=0, bx=0)
        p = self.run_phase
        s, c = math.sin(p), math.cos(p)
        return dict(rh=s * 44, lh=-s * 44,
                    rk=-(12 + 58 * max(0.0, math.cos(p + 0.3))),
                    lk=-(12 + 58 * max(0.0, math.cos(p + 0.3 + math.pi))),
                    ra=-s * 42, la=s * 42, re=65 - 12 * c, le=65 + 12 * c,
                    lean=-7 - (speed - 15.0) * 0.18, pz=0.85 + abs(s) * 0.06 - 0.02,
                    pitch=0, tw=s * 7, bx=s * 0.025)

    def _pose(self, dt, target, rate=18.0):
        t = min(1.0, rate * dt)
        for k in POSE_KEYS:
            self.cur[k] = _lerp(self.cur[k], target[k], t)
        c = self.cur
        for side, hk, kk, ak, ek in (("r", "rh", "rk", "ra", "re"), ("l", "lh", "lk", "la", "le")):
            self.leg_hip[side].setP(c[hk])
            self.leg_knee[side].setP(c[kk])
            self.leg_ankle[side].setP(-(c[hk] + c[kk]) * 0.4)         # feet follow the legs
            self.arm_sh[side].setP(c[ak])
            self.arm_el[side].setP(c[ek])
        self.body.setZ(c["pz"])
        self.body.setX(c["bx"])
        self.body.setP(c["lean"] + c["pitch"])
        self.torso.setH(c["tw"])
        self.head.setH(-c["tw"] * 0.7)
        self.head.setP(-c["pitch"] * 0.6 - c["lean"] * 0.4)

    def _apply(self):
        self.root.setPos(self.x, self.y, self.z)
        if self.state == "running":
            turn = (self.x - LANES[self.lane]) * 10.0
            self.model.setH(max(-18.0, min(18.0, turn)))
        self.shadow.setZ(0.04 - self.z)
        self.shadow.setScale(max(0.3, 1.0 - self.z * 0.18))
        if self.z > -0.2:
            self.shadow.show()
        else:
            self.shadow.hide()
