"""Animated pieces: a library that loads each model once and makes cheap copies of it (meshes shared, each copy with
its own nodes and clip clocks), Actor, which plays a model's clips: a looping base (Idle, Walk), one-shots on top
(Attack, Hit, Die, Roar...), random fidgets while idle, short crossfades between clips, and moves across the board,
and Static, a piece drawn as a baked mesh until it animates."""
import math
import os
import random
import threading

import numpy as np

from unicode3d.detail import detail_levels
from unicode3d.models import load_model
from unicode3d.scene import Node
from unicode3d.transforms import quat_axis_angle

MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "models")
UP = np.array([0.0, 1.0, 0.0])
# Parts drawn without levels of detail (Object3D.simplify=False): thin plates laid on other parts, which a level of
# detail made on its own sinks behind them (most lost over half their pixels at standard detail), so they flicker
# as zoom changes the level. By model; each part by a name of its own, or the two names it alone has both of. Every
# part named Shield... too (the shields' blue faces). Costs about 1-2% of a mid-game frame (measured 2026-10-05).
EXACT = {
    "archer": ["Belt", "HoodBrow", "Stave0"],
    "barbarian": ["FootL", "BootCuffL", "BootCuffR", "Loin4", "Loin5", "Brow", "HairA0m", "HairA1m", "HairA2m"],
    "goblin": ["Belt", "FootL", "FootR", "Brow"],
    "goblin_king": ["Belt", "FootL", "FootR", "Brow"],
    "healer": ["Belt", "Rag0", "Rag1", "Rag2", "Rag4", "Rag5", "Rag7"],
    "hero": ["GreaveL", "GreaveR", "JawPart"],
    "knight": ["GreaveL", "GreaveR", "Belt"],
    "knight_mounted": [("BodyMesh", "Gold"), ("Gold", "LanceButt"), ("Leather", "SpineMesh")],
    "orc": ["RagTail", "BracerL"],
    "orc_warlord": ["RagTail", "Crossbar"],
    "swordsman": ["Belt"],
    "tower": ["SlitB", "ChunkStone0", "ChunkStone1", "ChunkStone2", "ChunkStone3", "ChunkStone4", "ChunkStone5",
              "ChunkStone6", "Course", "Slit4", "Eave"],
    "troll_mage": ["JawPart", "Staff"],
}


def _exact_parts(name, model):
    """The parts of model `name` to draw without levels of detail (see EXACT)."""
    for part, parts in model.names.items():
        if part.startswith("Shield"):
            yield from parts
    for entry in EXACT.get(name, ()):
        names = (entry,) if isinstance(entry, str) else entry
        held = [{id(o): o for o in model.names.get(n, ())} for n in names]
        yield from (o for i, o in held[0].items() if all(i in h for h in held[1:]))


class Library:
    _shared = None

    def __init__(self, folder=MODELS):
        self.folder = folder
        self.models = {}
        self._locks = {}  # name: a lock held while that model loads (the preloader and the game may want it at once)
        self._locks_lock = threading.Lock()

    @classmethod
    def shared(cls):
        """The library every board uses, loaded once a run (a new game doesn't load the models again), with the
        models no board starts with loading in the background (see preload)."""
        if cls._shared is None:
            cls._shared = cls()
            threading.Thread(target=cls._shared.preload, name="preload models", daemon=True).start()
        return cls._shared

    def has(self, name):
        return name in self.models or os.path.exists(os.path.join(self.folder, name + ".glb"))

    def _load(self, name):
        if name in self.models:
            return self.models[name]
        with self._locks_lock:
            lock = self._locks.setdefault(name, threading.Lock())
        with lock:
            if name not in self.models:
                model = load_model(os.path.join(self.folder, name + ".glb"))
                for o in _exact_parts(name, model):
                    o.simplify = False
                for o in model.objects:  # (a texture's mipmaps and the levels of detail, made now rather than
                    if o.mesh is not None:  # when it is first drawn)
                        for m in range(len(o.mesh.textures)):
                            o.mesh.mipmaps(m)
                        detail_levels(o.mesh)
                self.models[name] = model
            return self.models[name]

    def preload(self):
        """Load every model in the folder, so that a monster's first appearance doesn't pause the game while its
        model loads (50-150 ms each, about a second for all)."""
        for f in sorted(os.listdir(self.folder)):
            if f.endswith(".glb"):
                self._load(f[:-4])

    def instance(self, name):
        """A fresh copy of a model: its own nodes, parts and clip clocks, sharing meshes (Model.copy)."""
        return self._load(name).copy()


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
        c = self.clips[clip]
        c.speed = speed
        c.loop = "loop" if clip in ("Idle", "Walk", "Bubble") else "once"
        if c.loop == "loop" and clip != "Bubble":
            self.base = clip
        c.start(fade=self.BLEND if blend and self.current else 0.0)
        self.current = clip
        self.on_done = then
        return True

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

    def move_to(self, target, duration=1.0, hop=0.0, walk=True, face=True, then=None, ease=True):
        """Slide to target over duration (walking in place if it has Walk), optionally in a hop of that height.
        ease: start and stop gently (False: a constant speed, as a charge arrives)."""
        start = np.array(self.position, float)
        target = np.array(target, float)
        if face:
            d = target - start
            if abs(d[0]) + abs(d[2]) > 1e-3:
                self.turn_to = math.atan2(d[0], d[2])
        if walk and "Walk" in self.clips and not self.dead:
            self.play("Walk")
        self.motion = [start, target, max(duration, 1e-3), 0.0, hop, then, ease]

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
        start, end, dur, t, hop, then, ease = self.motion
        t = min(dur, t + dt)
        self.motion[3] = t
        u = t / dur
        e = u * u * (3 - 2 * u) if ease else u
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
            Static._baked[key] = m.bake()
        baked = Static._baked[key].copy()
        baked.root.parent = self.holder
        self.parts = baked.objects
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
