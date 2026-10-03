"""3D lettering that comes up in front of the camera to announce things: the siege beginning, the Monsters coming,
your turn. One Object3D per letter, so the letters arrive and leave one after another.

Two styles:
  "gilt"  gold storybook lettering (fonts.GILT), the first letter of each line red, as in an old manuscript; the
          letters rise into place in a wave, then float up and fade.
  "stone" castle blocks (fonts.BLOCK): every pixel a stone of its own shade; the letters drop in from above and
          land with a bounce, as if built into a wall, then tumble away.

Banner(lines, style).update(dt, camera, aspect) places it for this frame; done once it has left.
"""
import math
import random

import numpy as np

from unicode3d.scene import Object3D
from unicode3d.shapes import bitmap_mesh, block_mesh, merge_meshes
from unicode3d.transforms import quat_axis_angle, quat_from_matrix, quat_mul

from .fonts import BLOCK, GILT

DISTANCE = 6.0  # how far in front of the camera the lettering stands
WIDTH = 0.86  # at most this fraction of the view's width...
HEIGHT = 0.42  # ...and of its height
LINE_GAP = 2  # blank font rows between lines

GOLD, BRONZE, CRIMSON = (255, 196, 64), (150, 92, 24), (200, 30, 26)
STONES = [(150, 146, 138), (128, 124, 118), (170, 164, 150), (112, 110, 106), (140, 132, 116)]
MORTAR = (40, 36, 32)

STYLE = {  # font, depth, seconds between letters, seconds to arrive, hold, seconds to leave
    "gilt": dict(font=GILT, depth=1.4, stagger=0.022, arrive=0.5, hold=1.3, leave=0.5),
    "stone": dict(font=BLOCK, depth=1.2, stagger=0.04, arrive=0.5, hold=1.2, leave=0.55),
}

_meshes = {}  # (style, character, first of line): Mesh


def _gilt_mesh(glyph, first):
    cells = np.array([[c == "#" for c in row] for row in glyph])
    m = bitmap_mesh(cells, STYLE["gilt"]["depth"])
    v = np.asarray(m.vertices)[np.asarray(m.faces)]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    front = n[:, 2] > 0.5 * np.linalg.norm(n, axis=1)
    face = CRIMSON if first else GOLD
    m.face_colors = np.array([face if f else BRONZE for f in front], float) / 255
    return m


def _stone_mesh(glyph, rng):
    """A stone per pixel, set a little proud of dark mortar filling the letter's shape."""
    h, w = len(glyph), len(glyph[0])
    cells = np.array([[c == "#" for c in row] for row in glyph])
    if not cells.any():
        return None
    blocks, colors = [bitmap_mesh(cells, STYLE["stone"]["depth"] * 0.7)], [MORTAR]
    for r, row in enumerate(glyph):
        for c, ch in enumerate(row):
            if ch == "#":
                centre = (c + 0.5 - w / 2, h / 2 - r - 0.5, rng.uniform(-0.12, 0.12))
                blocks.append(block_mesh(centre, (0.8, 0.8, STYLE["stone"]["depth"] * rng.uniform(0.85, 1.0))))
                colors.append(rng.choice(STONES))
    return merge_meshes(blocks, colors)


def letter_mesh(style, ch, first=False):
    key = (style, ch, first)
    if key not in _meshes:
        glyph = STYLE[style]["font"][ch]
        if style == "gilt":
            _meshes[key] = _gilt_mesh(glyph, first) if any("#" in r for r in glyph) else None
        else:
            _meshes[key] = _stone_mesh(glyph, random.Random(ord(ch)))
    return _meshes[key]


def _ease_out_back(t, s=1.6):
    t -= 1
    return 1 + t * t * ((s + 1) * t + s)


def _bounce(t):
    """0 -> 1 with a landing bounce, as a block dropped onto a wall."""
    if t < 0.7:
        return (t / 0.7) ** 2
    u = (t - 0.7) / 0.3
    return 1 - 0.12 * math.sin(math.pi * u)


class Banner:
    def __init__(self, lines, style="gilt", hold=None):
        self.style = style
        p = STYLE[style]
        self.hold = p["hold"] if hold is None else hold
        font = p["font"]
        rows = len(next(iter(font.values())))
        self.letters = []  # (Object3D, x, y of its centre in font units, order)
        widths = []
        for line in lines:
            widths.append(sum(len(font[c][0]) for c in line if c in font) + max(0, len(line) - 1))
        self.width = max(widths)
        self.height = len(lines) * rows + (len(lines) - 1) * LINE_GAP
        order = 0
        for i, line in enumerate(lines):
            x = -widths[i] / 2
            y = self.height / 2 - i * (rows + LINE_GAP) - rows / 2
            for k, ch in enumerate(c for c in line if c in font):
                w = len(font[ch][0])
                mesh = letter_mesh(style, ch, first=(k == 0))
                if mesh is not None:
                    obj = Object3D(mesh, color=(255, 255, 255), cast_shadows=False, specular=2.0 if style == "gilt"
                                   else 0.2, shininess=40, emissive=0.3)
                    self.letters.append((obj, x + w / 2, y, order))
                    order += 1
                x += w + 1
        self.count = max(order, 1)
        self.t = 0.0
        self.leaving = None  # when it began to leave
        self.rng = random.Random(len(self.letters))
        self.spin = [self.rng.uniform(-1, 1) for _ in self.letters]

    @property
    def arrived(self):
        p = STYLE[self.style]
        return p["stagger"] * self.count + p["arrive"]

    @property
    def done(self):
        return self.leaving is not None and self.t - self.leaving > STYLE[self.style]["leave"] + 0.05

    def skip(self):
        """Hurry it away (the player pressed a key)."""
        if self.leaving is None:
            self.leaving = self.t

    def objects(self):
        return [o for o, *_ in self.letters if o.visible]

    def update(self, dt, camera, aspect):
        p = STYLE[self.style]
        self.t += dt
        if self.leaving is None and self.t >= self.arrived + self.hold:
            self.leaving = self.t
        eye = np.asarray(camera.position, float)
        fwd = np.asarray(camera.target, float) - eye
        fwd /= np.linalg.norm(fwd)
        right = np.cross(fwd, (0.0, 1.0, 0.0))
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        rot = quat_from_matrix(np.column_stack([right, up, -fwd]))
        tall = 2 * DISTANCE * math.tan(math.radians(camera.fov) / 2)
        unit = min(WIDTH * tall * aspect / self.width, HEIGHT * tall / self.height)
        centre = eye + fwd * DISTANCE + up * tall * 0.12
        for i, (obj, x, y, order) in enumerate(self.letters):
            local = self.t - order * p["stagger"]
            lift, size, fade, turn = 0.0, 1.0, 1.0, 0.0
            if local <= 0:
                obj.visible = False
                continue
            obj.visible = True
            if local < p["arrive"]:
                k = local / p["arrive"]
                if self.style == "gilt":
                    size = max(0.0, _ease_out_back(k))
                    lift = -(1 - k) * 4
                else:
                    lift = (1 - _bounce(k)) * 14
                fade = min(1.0, k * 2.5)
            if self.leaving is not None:
                u = min(1.0, (self.t - self.leaving - (order / self.count) * 0.2) / p["leave"])
                if u > 0:
                    lift += (u * u * 10) if self.style == "gilt" else -(u * u * 22)
                    turn = self.spin[i] * u * 1.8 if self.style == "stone" else 0.0
                    fade = min(fade, 1 - u)
            wobble = 0.0 if self.style == "stone" else math.sin(self.t * 2.2 + x * 0.25) * 0.35
            obj.position = centre + right * (x * unit) + up * ((y + lift + wobble) * unit)
            obj.rotation = quat_mul(rot, quat_axis_angle((0.0, 0.0, 1.0), turn)) if turn else rot
            obj.scale = unit * max(size, 0.001)
            obj.opacity = max(0.0, min(1.0, fade))
            obj.visible = obj.opacity > 0.02
