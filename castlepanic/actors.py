"""Animated pieces: a library that loads each model once and makes cheap copies of it (meshes shared, each copy with
its own nodes and clip clocks), and Actor, which plays a model's clips: a looping base (Idle, Walk), one-shots on
top (Attack, Hit, Die, Roar...), random fidgets while idle, short crossfades between clips, and moves across the
board."""
import copy
import math
import os
import random

import numpy as np

from unicode3d.animation import Animation, Clip
from unicode3d.models import load_model
from unicode3d.scene import Node
from unicode3d.transforms import quat_axis_angle, quat_slerp

MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "models")
UP = np.array([0.0, 1.0, 0.0])


class Library:
    def __init__(self, folder=MODELS):
        self.folder = folder
        self.models = {}

    def has(self, name):
        return name in self.models or os.path.exists(os.path.join(self.folder, name + ".glb"))

    def _load(self, name):
        if name not in self.models:
            self.models[name] = load_model(os.path.join(self.folder, name + ".glb"))
        return self.models[name]

    def instance(self, name):
        """A fresh copy of a model: new nodes and parts (sharing meshes), clips rebound to them."""
        src = self._load(name)
        mapping = {}

        def clone(node):
            if node is None:
                return None
            if node in mapping:
                return mapping[node]
            c = copy.copy(node)
            mapping[node] = c
            c.parent = clone(node.parent)
            c.position = np.array(node.position, dtype=float)
            c.rotation = np.array(node.rotation, dtype=float)
            if isinstance(node.scale, np.ndarray):
                c.scale = node.scale.copy()
            return c

        root = clone(src.root)
        objects = [clone(o) for o in src.objects]
        nodes = {k: clone(v) for k, v in src.nodes.items()}
        clips = {}
        for cname, clip in src.animations.items():
            anims = [Animation(clone(a.target), speed=a.speed, **a.tracks) for a in clip.animations]
            clips[cname] = Clip(anims, name=cname, loop=clip.loop, speed=clip.speed)
        m = copy.copy(src)
        m.root, m.objects, m.nodes, m.animations = root, objects, nodes, clips
        return m


def _yaw_quat(yaw):
    return quat_axis_angle(UP, yaw)


class Actor:
    """A model on the board. base: the looping clip it falls back to. Clips that aren't there are skipped, so a
    model missing a clip still works."""

    BLEND = 0.18  # seconds of crossfade between clips

    def __init__(self, library, name, position=(0, 0, 0), yaw=0.0, scale=1.0, rng=None):
        self.name = name
        self.model = library.instance(name)
        self.holder = Node(position=np.array(position, dtype=float), rotation=_yaw_quat(yaw), scale=scale)
        self.model.root.parent = self.holder
        self.yaw = yaw
        self.clips = self.model.animations
        self.rng = rng or random.Random()
        self.base = "Idle" if "Idle" in self.clips else None
        self.current = None
        self.on_done = None
        self._targets = []
        for c in self.clips.values():
            for a in c.animations:
                if a.target not in self._targets:
                    self._targets.append(a.target)
        self._blend = None  # (snapshot, time left)
        self.fidget_in = self.rng.uniform(3, 9)
        self.motion = None  # (start, end, duration, t, arc height, then)
        self.turn_to = None
        self.dead = False
        self.visible = True
        self.extra = []  # other objects riding along (a tar pool, a fortify token...)
        if self.base:
            self.play(self.base, blend=False)
            self.clips[self.base].time = self.rng.uniform(0, self.clips[self.base].duration)

    # ------------------------------------------------------------------------------- objects to draw

    def objects(self):
        if not self.visible:
            return []
        return list(self.model.objects)

    @property
    def position(self):
        return self.holder.position

    @position.setter
    def position(self, p):
        self.holder.position = np.array(p, dtype=float)

    def set_yaw(self, yaw):
        self.yaw = yaw
        self.holder.rotation = _yaw_quat(yaw)

    def top(self):
        """A point just above the model's head, in the world (from its rest height, worked out once: asking the
        model for its bounds every frame walks every part's parents and is slow)."""
        if not hasattr(self, "_height"):
            lo, hi = self.model.bounds()
            self._height = float(hi[1])
        s = self.holder.scale
        s = float(s if np.isscalar(s) else np.asarray(s)[1])
        return self.position + (0.0, self._height * s + 0.12, 0.0)

    # ------------------------------------------------------------------------------- clips

    def has(self, clip):
        return clip in self.clips

    def play(self, clip, then=None, blend=True, speed=1.0):
        """Play a clip: a loop becomes the base; a one-shot plays once, then `then()` is called and the base
        resumes (unless the clip was Die)."""
        if clip not in self.clips:
            if then:
                then()
            return False
        if blend and self.current:
            self._blend = (self._snapshot(), self.BLEND)
        c = self.clips[clip]
        c.time = 0.0
        c.speed = speed
        c.loop = "loop" if clip in ("Idle", "Walk", "Bubble") else "once"
        if c.loop == "loop" and clip != "Bubble":
            self.base = clip
        self.current = clip
        self.on_done = then
        c.apply(0.0)
        return True

    def _snapshot(self):
        return [(t, np.array(t.position, float), np.array(t.rotation, float),
                 np.array(t.scale, float) if not np.isscalar(t.scale) else t.scale) for t in self._targets]

    def busy(self):
        return self.current is not None and self.current != self.base

    def update(self, dt):
        if self.current:
            c = self.clips[self.current]
            c.update(dt)
            if c.loop == "once" and c.done():
                finished, cb = self.current, self.on_done
                self.on_done = None
                if finished == "Die":
                    self.dead = True
                    self.current = None
                elif self.base and self.base != finished:
                    self.play(self.base)
                else:
                    self.current = None
                if cb:
                    cb()
        if self._blend:
            snap, left = self._blend
            left -= dt
            k = max(0.0, left / self.BLEND)
            k = k * k * (3 - 2 * k)
            for t, p, r, s in snap:
                t.position = p * k + np.asarray(t.position) * (1 - k)
                t.rotation = quat_slerp(np.asarray(t.rotation), r, k)
                if not np.isscalar(s):
                    t.scale = s * k + np.asarray(t.scale, float) * (1 - k)
            self._blend = (snap, left) if left > 0 else None
        # fidgets: now and then, while idling
        if not self.dead and self.current == "Idle" and not self.motion:
            self.fidget_in -= dt
            if self.fidget_in <= 0:
                fidgets = [n for n in self.clips if n.startswith("Fidget")]
                if fidgets:
                    self.play(self.rng.choice(fidgets))
                self.fidget_in = self.rng.uniform(5, 14)
        self._update_motion(dt)

    # ------------------------------------------------------------------------------- moving

    def move_to(self, target, duration=1.0, hop=0.0, walk=True, face=True, then=None):
        """Slide to target over duration (walking in place if it has Walk), optionally in a hop of that height."""
        start = np.array(self.position, float)
        target = np.array(target, float)
        if face:
            d = target - start
            if abs(d[0]) + abs(d[2]) > 1e-3:
                self.turn_to = math.atan2(d[0], d[2])
        if walk and "Walk" in self.clips and not self.dead:
            self.play("Walk")
        self.motion = [start, target, max(duration, 1e-3), 0.0, hop, then]

    def _update_motion(self, dt):
        if self.turn_to is not None:
            diff = (self.turn_to - self.yaw + math.pi) % (2 * math.pi) - math.pi
            step = 8.0 * dt
            if abs(diff) <= step:
                self.set_yaw(self.turn_to)
                self.turn_to = None
            else:
                self.set_yaw(self.yaw + math.copysign(step, diff))
        if not self.motion:
            return
        start, end, dur, t, hop, then = self.motion
        t = min(dur, t + dt)
        self.motion[3] = t
        u = t / dur
        e = u * u * (3 - 2 * u)
        p = start + (end - start) * e
        p[1] += hop * 4 * u * (1 - u)
        self.position = p
        if t >= dur:
            self.motion = None
            if self.current == "Walk":
                self.base = "Idle" if "Idle" in self.clips else None
                if self.base:
                    self.play(self.base)
            if then:
                then()

    def face(self, yaw):
        self.turn_to = yaw


def bake(model):
    """The model as it stands now, merged into as few Object3Ds as possible: one mesh holding every ordinary part
    (vertices moved into the model root's space, part colours as face colours, textures kept), plus the parts
    that glow or are see-through, kept apart. For static scenery: one object instead of dozens."""
    from unicode3d.mesh import Mesh
    from unicode3d.scene import Object3D
    from unicode3d.transforms import world_matrix
    saved = model.root.parent
    model.root.parent = None
    root_pos, root_rot, root_scale = model.root.position, model.root.rotation, model.root.scale
    model.root.position, model.root.rotation, model.root.scale = np.zeros(3), np.array([1.0, 0, 0, 0]), 1.0
    verts, faces, uvs, mats, fcols, textures, keep = [], [], [], [], [], [], []
    base = 0
    spec = []
    for o in model.objects:
        lin, pos, vis = world_matrix(o)
        if not vis or o.mesh is None or not len(o.mesh.faces):
            continue
        if o.emissive > 0 or o.opacity < 1 or o.reflectivity > 0 or o.double_sided:
            c = copy.copy(o)
            c.parent = None
            m = copy.copy(o.mesh)
            m.vertices = np.asarray(o.mesh.vertices, float) @ lin.T + pos
            m.normals = None
            c.mesh, c.position, c.rotation, c.scale = m, np.zeros(3), np.array([1.0, 0, 0, 0]), 1.0
            keep.append(c)
            continue
        m = o.mesh
        v = np.asarray(m.vertices, float) @ lin.T + pos
        f = np.asarray(m.faces, np.int64)
        verts.append(v)
        faces.append(f + base)
        base += len(v)
        n = len(f)
        if m.uvs is not None and m.textures:
            uvs.append(np.asarray(m.uvs, float))
            mats.append(np.asarray(m.materials if m.materials is not None else np.zeros(n), np.int64) + len(textures))
            textures.extend(m.textures)
        else:
            uvs.append(np.zeros((n, 3, 2)))
            mats.append(np.full(n, -1, np.int64))
        col = _srgb01(o.color)
        if m.face_colors is not None:
            fc = np.asarray(m.face_colors, float)[:, :3]
            fc = fc / 255.0 if fc.max() > 1.0 else fc
            fcols.append(fc * col)
        elif m.vertex_colors is not None:
            vc = np.asarray(m.vertex_colors, float)[:, :3]
            vc = vc / 255.0 if vc.max() > 1.0 else vc
            fcols.append(vc[f].mean(axis=1) * col)
        else:
            fcols.append(np.broadcast_to(col, (n, 3)))
        spec.append((o.specular, o.shininess or 20.0, n))
    model.root.position, model.root.rotation, model.root.scale = root_pos, root_rot, root_scale
    model.root.parent = saved
    out = []
    if verts:
        mesh = Mesh(np.concatenate(verts), np.concatenate(faces))
        mesh.face_colors = np.concatenate(fcols)
        if textures:
            mat = np.concatenate(mats)
            white = len(textures)
            textures.append(np.ones((2, 2)))
            mat[mat < 0] = white
            mesh.uvs = np.concatenate(uvs)
            mesh.materials = mat
            mesh.textures = textures
        total = sum(n for _, _, n in spec)
        sp = sum(s * n for s, _, n in spec) / total
        sh = sum(h * n for _, h, n in spec) / total
        out.append(Object3D(mesh, color=(255, 255, 255), specular=sp, shininess=sh))
    return out + keep


def _srgb01(c):
    c = np.asarray(c if not isinstance(c, int) else (200, 200, 200), float)
    if c.shape != (3,):
        c = np.asarray(getattr(c, "value", (200, 200, 200)), float)[:3]
    return c / 255.0 if c.max() > 1.0 else c


class Static:
    """A piece that stands still most of the time (a tower, a wall, a tree): drawn as a baked mesh shared by every
    copy, swapped for a live animated Actor only while it plays a clip."""
    _baked = {}

    def __init__(self, library, name, position=(0, 0, 0), yaw=0.0, scale=1.0, clip=None):
        self.library, self.name = library, name
        self.holder = Node(position=np.array(position, float), rotation=_yaw_quat(yaw), scale=scale)
        self.yaw, self.scale = yaw, scale
        key = (name, clip)
        if key not in Static._baked:
            m = library.instance(name)
            if clip and clip in m.animations:  # e.g. the collapsed pose: the end of Collapse
                c = m.animations[clip]
                c.apply(c.duration)
            Static._baked[key] = bake(m)
        self.parts = [copy.copy(o) for o in Static._baked[key]]
        for p in self.parts:
            p.parent = self.holder
        self.actor = None
        self.visible = True

    def objects(self):
        if not self.visible:
            return []
        if self.actor:
            return self.actor.objects()
        return self.parts

    def play(self, clip, then=None, settle=None):
        """Animate a clip on a live copy; afterwards show `settle` (a baked pose: e.g. ("wall", "Collapse") for
        the rubble), or the intact piece."""
        a = Actor(self.library, self.name, self.holder.position, self.yaw, self.scale)
        self.actor = a

        def done():
            if settle is not None:
                s = Static(self.library, self.name, self.holder.position, self.yaw, self.scale, clip=settle)
                self.parts = s.parts
                self.holder = s.holder
            self.actor = None
            if then:
                then()
        if not a.play(clip, then=done):
            self.actor = None

    def update(self, dt):
        if self.actor:
            self.actor.update(dt)
