"""The board: geometry of rings and arcs in the world, and the painted mat and table they sit on.

World: Y up, the board lies in the XZ plane centred on the origin. Angles are measured clockwise from north (-Z,
the far side as the players sit at +Z), so arc i (printed i+1) spans ARC_START + 60i .. +60 degrees; arc 0 is
up-left, as on the real board.
"""
import math
import os
import threading

import numpy as np

from unicode3d.detail import detail_levels
from unicode3d.mesh import Mesh
from unicode3d.scene import Object3D

from .rules import ARCS, CASTLE, FOREST, KNIGHT, SWORDSMAN, ARCHER

# ring edges (radius): Castle 0..R[0], Swordsman R[0]..R[1], Knight .., Archer .., Forest R[3]..R[4]
R = [2.5, 4.2, 5.9, 7.6, 10.0]
BOARD = 10.6        # the mat's radius, with its border
ARC_START = -60.0   # degrees: where arc 0 begins (clockwise from north)
ARC_RGB = {"red": (0.62, 0.12, 0.09), "green": (0.20, 0.45, 0.16), "blue": (0.16, 0.30, 0.62)}
LINE_RGB = {"red": (0.95, 0.25, 0.18), "green": (0.35, 0.85, 0.28), "blue": (0.32, 0.55, 1.0)}
TEX = 1024


def arc_angle(arc, frac=0.5):
    """Degrees (clockwise from north) at a fraction across arc."""
    return ARC_START + 60.0 * (arc + frac)


def polar(deg, r, y=0.0):
    a = math.radians(deg)
    return np.array([r * math.sin(a), y, -r * math.cos(a)])


def facing_yaw(deg):
    """Yaw (radians, about +Y) that turns a model facing +Z to face the centre from angle deg."""
    # a model faces +Z; at angle deg, the centre lies along -position = (-sin, 0, cos)
    return math.radians(-deg)


def ring_mid(ring):
    if ring == CASTLE:
        return 1.85
    lo, hi = R[ring - 1], R[ring]
    return (lo + hi) / 2 if ring != FOREST else lo + 1.0


def slot_offsets(n):
    """Where n Monsters in one space stand: (fraction across the arc, radial offset) each."""
    if n <= 0:
        return []
    if n == 1:
        return [(0.5, 0.0)]
    rows = 1 if n <= 3 else 2
    per = math.ceil(n / rows)
    out = []
    for k in range(n):
        row, col = divmod(k, per)
        count = min(per, n - row * per)
        frac = 0.5 + (col - (count - 1) / 2) * (0.62 / max(per - 1, 1)) * (1 if per > 1 else 0)
        dr = 0.0 if rows == 1 else (-0.38 if row == 0 else 0.38)
        out.append((frac, dr))
    return out


RUBBLE_MID = 1.55  # where Monsters stand in a Castle space once its Tower has fallen: on the rubble


def space_position(arc, ring, k=0, n=1, rubble=False):
    """Where the k-th of n Monsters in (arc, ring) stands, in the world, and the yaw facing the castle. rubble: a
    Castle space whose Tower has fallen, so its footprint is free to stand on (more room than beside a Tower)."""
    frac, dr = slot_offsets(n)[k]
    if ring == CASTLE:
        frac = 0.5 + (frac - 0.5) * (0.9 if rubble else 0.7)
    deg = arc_angle(arc, frac)
    pos = polar(deg, (RUBBLE_MID if ring == CASTLE and rubble else ring_mid(ring)) + dr)
    return pos, facing_yaw(deg)


def tower_position(arc):
    deg = arc_angle(arc)
    return polar(deg, 1.45), facing_yaw(deg) + math.pi


def wall_position(arc):
    """The wall stands on the chord of the castle ring across the arc (the castle is a hexagon)."""
    deg = arc_angle(arc)
    apothem = R[0] * math.cos(math.radians(30))
    return polar(deg, apothem - 0.05), facing_yaw(deg) + math.pi, R[0] / 2.2


# ------------------------------------------------------------------------------------------------ painting

def _noise(rng, n, beta):
    ky, kx = np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n), indexing="ij")
    f = np.sqrt(kx ** 2 + ky ** 2)
    f[0, 0] = 1.0
    spec = (rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / f ** beta
    spec[0, 0] = 0
    a = np.real(np.fft.ifft2(spec))
    lo, hi = np.percentile(a, 1), np.percentile(a, 99)
    return np.clip((a - lo) / (hi - lo), 0, 1)


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _mix(img, col, amt):
    return img * (1 - amt[..., None]) + np.asarray(col) * amt[..., None]


def paint_mat(seed=5):
    """The mat's texture (TEX, TEX, 3), sRGB 0..1: grim terrain tinted by each arc's colour, bold ring and arc
    lines in the arc colours, flagstones in the Castle ring, a dark forest floor, a parchment border."""
    n = TEX
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:n, 0:n]
    # texture (u, v) -> world (x, z): u along +x, v along -z (v up the image = far side)
    x = (u + 0.5) / n * 2 * BOARD - BOARD
    z = -((v + 0.5) / n * 2 * BOARD - BOARD)
    z = -z  # row 0 is the top of the image (far side, -z)
    r = np.hypot(x, z)
    deg = (np.degrees(np.arctan2(x, -z)) - ARC_START) % 360
    arc = (deg // 60).astype(int) % ARCS
    within = deg % 60
    big, mid, fine = _noise(rng, n, 2.3), _noise(rng, n, 1.6), _noise(rng, n, 0.8)
    # base earth: dark, muddy
    img = np.ones((n, n, 3)) * np.array([0.23, 0.19, 0.14])
    img *= (0.65 + 0.55 * big)[..., None] * (0.9 + 0.2 * fine)[..., None]
    # tint by arc colour: red = scorched blood-earth, green = moss and bracken, blue = cold marsh
    tint = np.zeros((n, n, 3))
    for k in range(ARCS):
        c = ["red", "red", "green", "green", "blue", "blue"][k]
        tint[arc == k] = ARC_RGB[c]
    field = (r > R[0]) & (r < R[3])
    patches = _smooth(0.42, 0.7, mid)
    img = np.where(field[..., None], _mix(img, tint * 0.75, 0.38 + 0.4 * patches), img)
    # marsh pools in blue arcs, blood-red cracks in red arcs, grass tufts in green
    pools = _smooth(0.66, 0.72, big) * (arc >= 4) * field
    img = _mix(img, [0.08, 0.13, 0.2], pools * 0.85)
    img = _mix(img, [0.22, 0.32, 0.42], pools * _smooth(0.75, 0.95, fine) * 0.5)
    cracks = _smooth(0.47, 0.5, mid) * _smooth(0.53, 0.5, mid) * (arc < 2) * field
    img = _mix(img, [0.3, 0.04, 0.03], cracks * 0.9)
    tufts = _smooth(0.7, 0.85, fine) * ((arc == 2) | (arc == 3)) * field
    img = _mix(img, [0.25, 0.38, 0.12], tufts * 0.5)
    # forest floor: very dark loam and needles
    forest = r >= R[3]
    img = np.where(forest[..., None], _mix(img * 0.6, [0.07, 0.09, 0.05], 0.5 + 0.3 * mid), img)
    # castle courtyard: flagstones
    court = r < R[0]
    fl = ((np.floor(x * 1.6) + np.floor(z * 1.6)) % 2)
    stone = np.array([0.33, 0.32, 0.31]) * (0.75 + 0.3 * fine[..., None]) * (0.88 + 0.12 * fl[..., None])
    gaps = (np.abs((x * 1.6) % 1 - 0.5) > 0.45) | (np.abs((z * 1.6) % 1 - 0.5) > 0.45)
    stone = np.where(gaps[..., None], stone * 0.35, stone)
    img = np.where(court[..., None], stone, img)
    # ring lines and arc dividers, in the arc's colour, slightly glowing
    line = np.zeros((n, n))
    px = 2 * BOARD / n
    for edge in R:
        line = np.maximum(line, _smooth(2.6 * px, 0.6 * px, np.abs(r - edge)))
    seam = np.minimum(within, 60 - within)
    arc_dist = np.radians(seam) * r
    line = np.maximum(line, _smooth(2.6 * px, 0.6 * px, arc_dist) * (r > R[0] - 0.01) * (r < R[4] + 0.01))
    lcol = np.zeros((n, n, 3))
    for k in range(ARCS):
        lcol[arc == k] = LINE_RGB[["red", "red", "green", "green", "blue", "blue"][k]]
    img = img * (1 - line[..., None]) + lcol * line[..., None]
    # border: a dark tooled-leather rim beyond the forest
    rim = r > R[4]
    img = np.where(rim[..., None], np.array([0.12, 0.08, 0.05]) * (0.8 + 0.3 * fine[..., None]), img)
    rim_line = _smooth(2.5 * px, 0.5 * px, np.abs(r - (R[4] + 0.35)))
    img = _mix(img, [0.55, 0.42, 0.2], rim_line * 0.9)
    return np.clip(img, 0, 1)


def paint_table(seed=9, n=512):
    """Dark oiled planks for the table under the board."""
    rng = np.random.default_rng(seed)
    grain = _noise(rng, n, 1.2)
    ky, kx = np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n), indexing="ij")
    f = np.sqrt((kx * 12) ** 2 + ky ** 2)
    f[0, 0] = 1
    spec = (rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / f ** 1.4
    spec[0, 0] = 0
    streak = np.real(np.fft.ifft2(spec))
    streak = (streak - streak.min()) / np.ptp(streak)
    img = np.ones((n, n, 3)) * np.array([0.2, 0.12, 0.07])
    img *= (0.6 + 0.6 * streak)[..., None] * (0.85 + 0.3 * grain)[..., None]
    u = np.arange(n)
    seams = (u % (n // 4)) < 3
    img[:, seams] *= 0.3
    return np.clip(img, 0, 1)


def _cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", base)
    d = os.path.join(base, "castlepanic")
    os.makedirs(d, exist_ok=True)
    return d


def cached_texture(name, fn, version=3):
    path = os.path.join(_cache_dir(), f"{name}-v{version}.npy")
    try:
        return np.load(path)
    except Exception:
        img = fn().astype(np.float32)
        try:
            np.save(path, img)
        except OSError:
            pass
        return img


# ------------------------------------------------------------------------------------------------ meshes

def disc_mesh(radius, segments=96, rings=6, y=0.0, texture=None):
    """A flat disc in XZ facing up, its texture mapped straight down from above over [-radius, radius]."""
    verts = [(0.0, y, 0.0)]
    for k in range(1, rings + 1):
        rr = radius * k / rings
        for s in range(segments):
            a = 2 * math.pi * s / segments
            verts.append((rr * math.sin(a), y, -rr * math.cos(a)))
    faces = []
    for s in range(segments):
        faces.append((0, 1 + (s + 1) % segments, 1 + s))
    for k in range(1, rings):
        a0, b0 = 1 + (k - 1) * segments, 1 + k * segments
        for s in range(segments):
            s1 = (s + 1) % segments
            faces.append((a0 + s, a0 + s1, b0 + s1))
            faces.append((a0 + s, b0 + s1, b0 + s))
    verts = np.array(verts)
    faces = np.array(faces)
    mesh = Mesh(verts, faces)
    if texture is not None:
        uv = np.stack([(verts[:, 0] + radius) / (2 * radius), (verts[:, 2] + radius) / (2 * radius)], axis=1)
        uv[:, 1] = 1 - uv[:, 1]  # the engine samples v=1 at image row 0: put row 0 (north) at the far side
        mesh.uvs = uv[faces]
        mesh.materials = np.zeros(len(faces), np.int64)
        mesh.textures = [texture]
    return mesh


def quad_mesh(half_x, half_z, y, texture, tiles=1.0):
    v = np.array([(-half_x, y, -half_z), (half_x, y, -half_z), (half_x, y, half_z), (-half_x, y, half_z)])
    f = np.array([(0, 2, 1), (0, 3, 2)])
    uv = np.array([(0, 0), (tiles, 0), (tiles, tiles), (0, tiles)], float)
    m = Mesh(v, f)
    m.uvs = uv[f]
    m.materials = np.zeros(2, np.int64)
    m.textures = [texture]
    return m


_meshes = []  # the mat's and the table's meshes, made once a run (see _board_meshes)
_meshes_lock = threading.Lock()


def _board_meshes():
    """The mat's and the table's meshes, made the first time and shared by every board after: the renderer keeps a
    texture's mipmaps and a mesh's levels of detail by the arrays themselves, so a board built afresh each game
    (cached_texture loads a new array every call) made them again in its first frame (~80 ms)."""
    with _meshes_lock:
        if not _meshes:
            _meshes.extend([disc_mesh(BOARD, texture=cached_texture("mat", paint_mat)),
                            quad_mesh(40, 40, -0.06, cached_texture("table", paint_table), tiles=6.0)])
        return list(_meshes)


def prepare():
    """Make the board's mipmaps and levels of detail now (the preload thread calls this first, while the kernels
    load), rather than in the first frame that draws it."""
    for mesh in _board_meshes():
        for m in range(len(mesh.textures)):
            mesh.mipmaps(m)
        detail_levels(mesh)


def build():
    """The mat and the table: a list of Object3Ds (their meshes shared by every board: see _board_meshes)."""
    mat_mesh, table_mesh = _board_meshes()
    mat = Object3D(mat_mesh, color=(255, 255, 255), specular=0.15, shininess=8)
    table = Object3D(table_mesh, color=(255, 255, 255), specular=0.3, shininess=20)
    return [mat, table]
