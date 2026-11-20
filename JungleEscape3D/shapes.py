"""
shapes.py - Procedural modelling toolkit (v2).

Panda3D ships without 3D models, so every object in the game is built from
simple shapes.  Many shapes are merged into ONE mesh with vertex colours, which
keeps the game fast on low-end PCs.

New in v2
    * smooth shading (round trunks, canopies, rocks)
    * `rough`   : bumpy, irregular spheres (natural looking foliage and rocks)
    * `grad`    : darker bottoms (cheap fake ambient occlusion = more depth)
    * `limb`    : tapered cylinder between two points (trunks, branches, roots)
    * `leaf_card` : bent leaf strips (palm fronds, ferns)
"""
import math
import random

from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter, NodePath,
                          Point3, TransformState, Vec3, Vec4)

_cache = {}


# ---------------------------------------------------------------- templates
# A template is (vertices, triangles, heights).
#   triangles : (a, b, c, smooth)  - smooth=False means flat shaded (box faces, caps)
#   heights   : 0..1 value per vertex (bottom..top) used for the colour gradient
def _cube_template():
    if "cube" in _cache:
        return _cache["cube"]
    verts = [Point3(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tris = []
    for a, b, c, d in faces:
        tris.append((a, b, c, False))
        tris.append((a, c, d, False))
    hts = [v.z + 0.5 for v in verts]
    _cache["cube"] = (verts, tris, hts)
    return _cache["cube"]


def _cylinder_template(sides, top, along_y):
    key = ("cyl", sides, round(top, 2), along_y)
    if key in _cache:
        return _cache[key]

    def pt(rx, h, ry):
        return Point3(rx, h, ry) if along_y else Point3(rx, ry, h)

    verts = [pt(0, -.5, 0), pt(0, .5, 0)]
    hts = [0.0, 1.0]
    for i in range(sides):
        a = 2 * math.pi * i / sides
        verts.append(pt(math.cos(a), -.5, math.sin(a)))
        hts.append(0.0)
    for i in range(sides):
        a = 2 * math.pi * i / sides
        verts.append(pt(top * math.cos(a), .5, top * math.sin(a)))
        hts.append(1.0)
    tris = []
    for i in range(sides):
        j = (i + 1) % sides
        tris.append((0, 2 + j, 2 + i, False))                       # bottom cap (flat)
        tris.append((1, 2 + sides + i, 2 + sides + j, False))       # top cap (flat)
        tris.append((2 + i, 2 + j, 2 + sides + j, True))            # side (smooth)
        tris.append((2 + i, 2 + sides + j, 2 + sides + i, True))
    _cache[key] = (verts, tris, hts)
    return _cache[key]


def _sphere_template(rings, segs):
    key = ("sph", rings, segs)
    if key in _cache:
        return _cache[key]
    verts = [Point3(0, 0, 1), Point3(0, 0, -1)]
    for r in range(1, rings):
        phi = math.pi * r / rings
        z, rr = math.cos(phi), math.sin(phi)
        for s in range(segs):
            th = 2 * math.pi * s / segs
            verts.append(Point3(rr * math.cos(th), rr * math.sin(th), z))

    def idx(r, s):
        return 2 + (r - 1) * segs + (s % segs)

    tris = []
    for s in range(segs):
        tris.append((0, idx(1, s), idx(1, s + 1), True))
        tris.append((1, idx(rings - 1, s + 1), idx(rings - 1, s), True))
    for r in range(1, rings - 1):
        for s in range(segs):
            a, b = idx(r, s), idx(r, s + 1)
            c, d = idx(r + 1, s + 1), idx(r + 1, s)
            tris.append((a, b, c, True))
            tris.append((a, c, d, True))
    hts = [(v.z + 1) / 2 for v in verts]
    _cache[key] = (verts, tris, hts)
    return _cache[key]


# ---------------------------------------------------------------- builder
class MeshBuilder:
    """Collects coloured triangles from many shapes into a single mesh."""

    def __init__(self, jitter=0.06, seed=None, vjit=0.04):
        self.tris = []
        self.jitter = jitter      # random brightness change per shape
        self.vjit = vjit          # random brightness change per vertex
        self.rng = random.Random(seed)

    # -- helpers
    def _color(self, color):
        a = color[3] if len(color) > 3 else 1.0
        j = 1.0 + self.rng.uniform(-self.jitter, self.jitter)
        return Vec4(min(1.0, color[0] * j), min(1.0, color[1] * j),
                    min(1.0, color[2] * j), a)

    @staticmethod
    def _matrix(pos, hpr, scale):
        return TransformState.makePosHprScale(
            Vec3(*pos), Vec3(*hpr), Vec3(*scale)).getMat()

    def _add_mesh(self, template, mat, color, smooth=True, grad=1.0, rough=0.0):
        verts, tris, hts = template
        rng = self.rng
        base = self._color(color)
        if rough:
            verts = [v * (1.0 + rng.uniform(-rough, rough)) for v in verts]
        pts = [mat.xformPoint(v) for v in verts]
        center = mat.xformPoint(Point3(0, 0, 0))
        vj = self.vjit
        cols = []
        for t in hts:
            f = (grad + (1.0 - grad) * t) * (1.0 + rng.uniform(-vj, vj))
            cols.append(Vec4(min(1.0, base.x * f), min(1.0, base.y * f),
                             min(1.0, base.z * f), base.w))
        vn = [Vec3(0, 0, 0) for _ in pts]
        keep = []
        for ia, ib, ic, sm in tris:
            a, b, c = pts[ia], pts[ib], pts[ic]
            n = (b - a).cross(c - a)
            if n.lengthSquared() < 1e-12:
                continue                              # degenerate (cone tip)
            mx = (a.x + b.x + c.x) / 3.0 - center.x
            my = (a.y + b.y + c.y) / 3.0 - center.y
            mz = (a.z + b.z + c.z) / 3.0 - center.z
            if n.x * mx + n.y * my + n.z * mz < 0:   # make the face point outwards
                ib, ic = ic, ib
                n = -n
            sm = sm and smooth
            keep.append((ia, ib, ic, n, sm))
            if sm:
                vn[ia] = vn[ia] + n
                vn[ib] = vn[ib] + n
                vn[ic] = vn[ic] + n
        for v in vn:
            if v.lengthSquared() > 0:
                v.normalize()
        for ia, ib, ic, n, sm in keep:
            if sm:
                na, nb, nc = vn[ia], vn[ib], vn[ic]
            else:
                na = Vec3(n)
                na.normalize()
                nb = nc = na
            self.tris.append((pts[ia], pts[ib], pts[ic], na, nb, nc,
                              cols[ia], cols[ib], cols[ic]))

    # -- shapes
    def box(self, pos, size, color, hpr=(0, 0, 0), grad=1.0):
        self._add_mesh(_cube_template(), self._matrix(pos, hpr, size), color,
                       smooth=False, grad=grad)

    def cylinder(self, pos, radius, height, color, hpr=(0, 0, 0), top=1.0,
                 sides=8, grad=1.0, smooth=True):
        self._add_mesh(_cylinder_template(sides, top, False),
                       self._matrix(pos, hpr, (radius, radius, height)),
                       color, smooth=smooth, grad=grad)

    def cone(self, pos, radius, height, color, hpr=(0, 0, 0), sides=8, grad=1.0):
        self.cylinder(pos, radius, height, color, hpr, top=0.0, sides=sides, grad=grad)

    def sphere(self, pos, radii, color, hpr=(0, 0, 0), rings=5, segs=7,
               rough=0.0, grad=0.8, smooth=True):
        if isinstance(radii, (int, float)):
            radii = (radii, radii, radii)
        self._add_mesh(_sphere_template(rings, segs), self._matrix(pos, hpr, radii),
                       color, smooth=smooth, grad=grad, rough=rough)

    def limb(self, p0, p1, r0, r1, color, sides=6, grad=0.85, smooth=True):
        """Tapered cylinder from p0 (radius r0) to p1 (radius r1)."""
        dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-6 or r0 <= 0:
            return
        heading = math.degrees(math.atan2(-dx, dy)) if (abs(dx) + abs(dy)) > 1e-9 else 0.0
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, dz / length))))
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
        self._add_mesh(_cylinder_template(sides, r1 / r0, True),
                       self._matrix(mid, (heading, pitch, 0), (r0, length, r0)),
                       color, smooth=smooth, grad=grad)

    def quad(self, p0, p1, p2, p3, colors, hint=(0, 0, 1), normal=None):
        """A flat quad. colors = one colour or a list of 4 (per-corner)."""
        if isinstance(colors, list):
            cols = [Vec4(*c) if len(c) > 3 else Vec4(c[0], c[1], c[2], 1) for c in colors]
        else:
            cols = [self._color(colors)] * 4
        pts = [Point3(*p) for p in (p0, p1, p2, p3)]
        h = Vec3(*hint)
        for i, j, k in ((0, 1, 2), (0, 2, 3)):
            a, b, c = pts[i], pts[j], pts[k]
            n = (b - a).cross(c - a)
            if n.lengthSquared() < 1e-12:
                continue
            n.normalize()
            if n.dot(h) < 0:
                j, k = k, j
                n = -n
            nn = Vec3(*normal) if normal is not None else n
            self.tris.append((pts[i], pts[j], pts[k], nn, nn, nn, cols[i], cols[j], cols[k]))

    def leaf_card(self, base, heading, length, width, rise, droop, color, segs=3):
        """A bent, flat leaf strip (palm frond / fern leaf). It is lit from above."""
        h = math.radians(heading)
        dx, dy = math.cos(h), math.sin(h)
        sx, sy = -dy * width / 2, dx * width / 2
        pts = []
        for i in range(segs + 1):
            t = i / segs
            pts.append((base[0] + dx * length * t, base[1] + dy * length * t,
                        base[2] + rise * t - droop * t * t))
        for i in range(segs):
            t0, t1 = i / segs, (i + 1) / segs
            w0, w1 = 1.0 - 0.75 * t0, 1.0 - 0.75 * t1        # leaf narrows to the tip
            f0, f1 = 0.72 + 0.28 * t0, 0.72 + 0.28 * t1       # darker at the base
            a, b = pts[i], pts[i + 1]
            c0 = (color[0] * f0, color[1] * f0, color[2] * f0)
            c1 = (color[0] * f1, color[1] * f1, color[2] * f1)
            self.quad((a[0] - sx * w0, a[1] - sy * w0, a[2]), (a[0] + sx * w0, a[1] + sy * w0, a[2]),
                      (b[0] + sx * w1, b[1] + sy * w1, b[2]), (b[0] - sx * w1, b[1] - sy * w1, b[2]),
                      [c0, c0, c1, c1], normal=(0, 0, 1))

    # -- output
    def build(self, name="mesh"):
        vdata = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
        vdata.setNumRows(len(self.tris) * 3)
        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        cw = GeomVertexWriter(vdata, "color")
        prim = GeomTriangles(Geom.UHStatic)
        i = 0
        for a, b, c, na, nb, nc, ca, cb, cc in self.tris:
            for p, n, col in ((a, na, ca), (b, nb, cb), (c, nc, cc)):
                vw.addData3(p.x, p.y, p.z)
                nw.addData3(n.x, n.y, n.z)
                cw.addData4(col.x, col.y, col.z, col.w)
            prim.addVertices(i, i + 1, i + 2)
            i += 3
        prim.closePrimitive()
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode(name)
        node.addGeom(geom)
        return NodePath(node)


def dir_from_hpr(hpr, axis):
    """Direction of a local axis after rotating by (heading, pitch, roll)."""
    mat = TransformState.makeHpr(Vec3(*hpr)).getMat()
    return mat.xformVec(Vec3(*axis))
