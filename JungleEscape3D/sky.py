"""
sky.py - A gradient sky dome with soft clouds and a glowing sun.

The dome follows the camera (but never rotates with it), so it always looks
infinitely far away.
"""
import math
import random

from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter, NodePath,
                          TransparencyAttrib)

from settings import FOG_COLOR
from shapes import MeshBuilder

RADIUS = 480.0
ZENITH = (0.22, 0.48, 0.86)
MID = (0.46, 0.72, 0.93)


def _mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _sky_color(t):
    """t = 0 at the horizon, 1 at the top."""
    if t < 0.35:
        return _mix(FOG_COLOR, MID, t / 0.35)
    return _mix(MID, ZENITH, min(1.0, (t - 0.35) / 0.65))


def _style(np_, sort):
    np_.setLightOff()
    np_.setFogOff()
    np_.setDepthWrite(False)
    np_.setDepthTest(False)
    np_.setBin("background", sort)


def build_sky(camera):
    root = camera.attachNewNode("sky")
    root.setCompass()                                    # follow position, ignore rotation

    # ---- dome
    rings, segs = 9, 24
    vdata = GeomVertexData("dome", GeomVertexFormat.getV3c4(), Geom.UHStatic)
    vw = GeomVertexWriter(vdata, "vertex")
    cw = GeomVertexWriter(vdata, "color")
    for r in range(rings + 1):
        elev = -0.12 + (math.pi / 2 + 0.12) * r / rings
        z, rr = math.sin(elev) * RADIUS, math.cos(elev) * RADIUS
        col = _sky_color(max(0.0, math.sin(elev)) ** 0.7)
        for s in range(segs):
            th = 2 * math.pi * s / segs
            vw.addData3(rr * math.cos(th), rr * math.sin(th), z)
            cw.addData4(col[0], col[1], col[2], 1.0)
    prim = GeomTriangles(Geom.UHStatic)
    for r in range(rings):
        for s in range(segs):
            a, b = r * segs + s, r * segs + (s + 1) % segs
            c, d = (r + 1) * segs + (s + 1) % segs, (r + 1) * segs + s
            prim.addVertices(a, b, c)
            prim.addVertices(a, c, d)
    prim.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node = GeomNode("dome")
    node.addGeom(geom)
    dome = root.attachNewNode(node)
    dome.setTwoSided(True)
    _style(dome, 0)

    # ---- clouds (flat translucent blobs)
    rng = random.Random(4)
    mb = MeshBuilder(jitter=0, vjit=0.02, seed=4)
    for _ in range(7):
        az = rng.uniform(0, 2 * math.pi)
        el = math.radians(rng.uniform(18, 48))
        cx, cy, cz = (math.cos(az) * math.cos(el) * RADIUS * 0.92,
                      math.sin(az) * math.cos(el) * RADIUS * 0.92,
                      math.sin(el) * RADIUS * 0.92)
        for _ in range(4):
            mb.sphere((cx + rng.uniform(-45, 45) * -math.sin(az), cy + rng.uniform(-45, 45) * math.cos(az),
                       cz + rng.uniform(-6, 6)),
                      (rng.uniform(28, 50), rng.uniform(20, 30), rng.uniform(8, 13)),
                      (1.0, 1.0, 1.0, 0.55), hpr=(math.degrees(az), 0, 0),
                      rings=4, segs=8, rough=0.12, grad=0.85)
    clouds = mb.build("clouds")
    clouds.reparentTo(root)
    clouds.setTransparency(TransparencyAttrib.MAlpha)
    _style(clouds, 5)

    # ---- sun: three stacked glowing discs facing the camera
    d = (0.30, 1.0, 0.45)
    ln = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
    d = (d[0] / ln, d[1] / ln, d[2] / ln)
    sb = MeshBuilder(jitter=0, vjit=0)
    for radius, alpha in ((70, 0.10), (44, 0.20), (22, 0.95)):
        p0 = tuple(v * (RADIUS * 0.97) for v in d)
        p1 = tuple(v * (RADIUS * 0.98) for v in d)
        sb.limb(p0, p1, radius, radius, (1.0, 0.96, 0.72, alpha), sides=30, smooth=False, grad=1.0)
    sun = sb.build("sun")
    sun.reparentTo(root)
    sun.setTransparency(TransparencyAttrib.MAlpha)
    _style(sun, 10)
    return root
