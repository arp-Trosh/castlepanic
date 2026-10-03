"""The 3D table: the board, the castle, the Monsters and the defenders, kept in step with the game.

`BoardScene.sync(game)` places everything where the game state says, at once (the start, or a client catching up).
`BoardScene.play(events)` queues the rules' events; `update(dt)` plays them one beat at a time as animations
(Monsters walking in, archers loosing, walls crumbling, the boulder rolling through...), and calls `on_sound(name)`
for the sound to go with each. `busy()` tells whether animations are still playing.
"""
import math
import random

import numpy as np

from unicode3d.lights import Light, PointLight
from unicode3d.scene import Camera, Object3D
from unicode3d.shapes import blob_mesh
from unicode3d.transforms import quat_axis_angle

from . import board
from .actors import Actor, Library, Static
from .banner import Banner
from .fx import Effects
from .rules import ARCS, CASTLE, FOREST, SWORDSMAN, KNIGHT, ARCHER, arc_color

SCALE = {"goblin": 1.7, "orc": 1.55, "troll": 1.4, "goblin_king": 1.6, "orc_warlord": 1.35, "troll_mage": 1.3,
         "healer": 1.5}
DEFENDER_SCALE = 1.5
DEFENDER_FOR = {"archer": "archer", "knight": "knight", "swordsman": "swordsman", "hero": "hero",
                "barbarian": "barbarian"}
BANNER_RGB = {"red": (170, 30, 24), "green": (40, 120, 40), "blue": (40, 70, 170)}
TAR = blob_mesh((0.5, 0.06, 0.5))
SPAWN_AFTER = 0.5  # seconds after "tHe mOnsTeRs aRe CoMing!" that they appear
TOKEN_AFTER = 0.5  # seconds after a drawn Monster token is announced that it takes effect
TOKEN_HOLD = 1.0  # seconds its name stays up
DRAW_UP_HOLD = 0.6  # seconds Draw Up stays lit in the Order of play before Discard
# what each Monster token says as it is drawn, in gilt lettering (the font has no digits)
TOKEN_BANNER = {
    "goblin": ["A Goblin!"], "orc": ["An Orc!"], "troll": ["A Troll!"], "goblin_king": ["The Goblin King!"],
    "orc_warlord": ["The Orc Warlord!"], "troll_mage": ["The Troll Mage!"], "healer": ["The Healer!"],
    "boulder": ["A Giant Boulder!"],
    "move_red": ["Red Monsters", "move one!"], "move_green": ["Green Monsters", "move one!"],
    "move_blue": ["Blue Monsters", "move one!"], "move_cw": ["Monsters move", "clockwise!"],
    "move_ccw": ["Monsters move", "counter-clockwise!"], "plague_archer": ["Plague!", "Archers"],
    "plague_knight": ["Plague!", "Knights"], "plague_swordsman": ["Plague!", "Swordsmen"],
    "discard1": ["All players", "discard a card!"], "draw3": ["Draw three", "more Monsters!"],
    "draw4": ["Draw four", "more Monsters!"],
}
# what a Boss Monster's power does, announced in gilt lettering as it arrives
BOSS_BANNER = {
    "orc_warlord": ["All Monsters of", "the same color", "move one space!"],
    "healer": ["All Monsters", "heal one!"],
    "troll_mage": ["All Monsters on", "the board", "move one space!"],
    "goblin_king": ["Draw three", "more Monsters!"],
}
CROWD_SCALE = {1: 1.0, 2: 0.85}  # Monsters sharing a space shrink a little to fit (three or more: CROWDED)
CROWDED = 0.7
HOME_AFTER = 1.0  # seconds after the action ends that the camera eases back to the whole-board view


class CameraRig:
    """An orbiting camera: yaw around the board, pitch, distance, a target point; eases towards where it's told."""

    def __init__(self):
        self.yaw, self.pitch, self.dist = 0.0, math.radians(50), 20.5
        self.target = np.array([0.0, 0.0, 1.0])
        self.goal = None  # (yaw, pitch, dist, target)
        self.home = (0.0, math.radians(50), 20.5, np.array([0.0, 0.0, 1.2]))
        self.user_moved = 0.0
        self.camera = Camera(fov=42, near=0.3, far=120)
        self.apply()

    def apply(self):
        cp = math.cos(self.pitch)
        eye = self.target + self.dist * np.array([math.sin(self.yaw) * cp, math.sin(self.pitch),
                                                   math.cos(self.yaw) * cp])
        self.camera.position = eye
        self.camera.target = self.target.copy()

    def focus(self, point, dist=11.0, pitch=40):
        """Swing round to look at point (from outside the castle, looking in), unless the player is steering."""
        if self.user_moved > 0:
            return
        p = np.asarray(point, float)
        yaw = math.atan2(p[0], p[2]) if np.hypot(p[0], p[2]) > 0.5 else self.yaw
        # take the short way round
        yaw = self.yaw + ((yaw - self.yaw + math.pi) % (2 * math.pi) - math.pi)
        self.goal = (yaw, math.radians(pitch), dist, p * 0.85)

    def go_home(self):
        if self.user_moved > 0:
            return
        y, p, d, t = self.home
        yaw = self.yaw + ((y - self.yaw + math.pi) % (2 * math.pi) - math.pi)
        self.goal = (yaw, p, d, t)

    def nudge(self, dyaw=0.0, dpitch=0.0, zoom=1.0):
        self.goal = None
        self.user_moved = 6.0
        self.yaw += dyaw
        self.pitch = min(math.radians(85), max(math.radians(12), self.pitch + dpitch))
        self.dist = min(40.0, max(4.0, self.dist * zoom))

    def reset(self):
        self.user_moved = 0.0
        self.go_home()

    def update(self, dt):
        self.user_moved = max(0.0, self.user_moved - dt)
        if self.goal:
            y, p, d, t = self.goal
            k = 1 - math.exp(-dt * 2.5)
            self.yaw += (y - self.yaw) * k
            self.pitch += (p - self.pitch) * k
            self.dist += (d - self.dist) * k
            self.target = self.target + (t - self.target) * k
            if abs(y - self.yaw) + abs(p - self.pitch) + abs(d - self.dist) < 1e-3:
                self.goal = None
        self.apply()


class BoardScene:
    def __init__(self, library=None, seed=1, on_sound=None):
        self.lib = library or Library.shared()
        self.rng = random.Random(seed)
        self.on_sound = on_sound or (lambda name, **kw: None)
        self.fx = Effects(self.rng)
        self.rig = CameraRig()
        self.ground = board.build()
        self.trees = []
        for k in range(36):
            deg = k * 10 + self.rng.uniform(-4, 4)
            r = self.rng.uniform(8.3, 10.3)
            kind = self.rng.choice(["tree_pine", "tree_pine", "tree_dead", "tree_oak", "rocks"])
            if self.lib.has(kind):
                self.trees.append(Static(self.lib, kind, board.polar(deg, r), self.rng.uniform(0, 6.3),
                                         scale=self.rng.uniform(0.9, 1.3)))
        self.towers, self.walls, self.forts = [], [], []
        for arc in range(ARCS):
            p, y = board.tower_position(arc)
            self.towers.append(self._static("tower", p, y))
            p, y, s = board.wall_position(arc)
            self.walls.append(self._static("wall", p, y, (s, 1.0, 1.0)))
            f = self._static("fortify", p + board.polar(board.arc_angle(arc), 0.32), y, (s, 1.0, 1.0))
            if f:
                f.visible = False
            self.forts.append(f)
        self._color_banners()
        self.monsters = {}  # mid -> Actor
        self.mdata = {}  # mid -> monster dict (as last known)
        self.tars = {}  # mid -> Object3D
        self.defenders = []  # temporary attackers on the field
        self.sentries = [None] * ARCS
        self.queue = []
        self.wait = 0.0
        self.pending = 0  # animations still running that the queue waits for
        self.lights = [
            Light(direction=np.array([-0.45, -1.0, -0.35]), ambient=0.5, diffuse=0.95, color=(255, 232, 200),
                  shadows=True),
            Light(direction=np.array([0.6, -0.35, 0.55]), ambient=0.0, diffuse=0.45, color=(130, 150, 255)),
        ]
        self.highlight = set()  # mids to mark as targets
        self.quiet = 0.0  # seconds since the last animation ended (the camera goes home after HOME_AFTER)
        self.homed = True
        self.banners = []  # lettering on screen (banner.Banner)
        self.aspect = 2.0  # the view's width over its height, in pixels (the UI keeps it up to date)
        self.my_seat = None  # whose "Your turn" banner to show
        self.announced = False  # "the Monsters are coming" shown since the last turn began
        self.step = None  # (seat, step) of the turn as far as the animations have got
        self.turn = None  # and that turn's number
        self.selected = None

    def _static(self, name, p, y, scale=1.0):
        if not self.lib.has(name):
            return None
        return Static(self.lib, name, p, y, scale)

    def _color_banners(self):
        """Each tower flies its arc's colour: the banner is the one double-sided part kept out of the bake."""
        for arc, t in enumerate(self.towers):
            if t is None:
                continue
            for p in t.parts:
                if p.double_sided:
                    p.color = BANNER_RGB[arc_color(arc)]

    # -------------------------------------------------------------------------------------------------- drawing

    def objects(self):
        out = list(self.ground)
        for s in self.trees + self.towers + self.walls + self.forts:
            if s:
                out += s.objects()
        for a in self.monsters.values():
            out += a.objects()
        for a in self.defenders:
            out += a.objects()
        for a in self.sentries:
            if a:
                out += a.objects()
        out += list(self.tars.values())
        out += self.fx.objects()
        for b in self.banners:
            out += b.objects()
        return out

    def monster_at_cell(self, renderer, x, y):
        """The Monster id drawn in cell (x, y) of the last frame, if any."""
        hit = renderer.pick(x, y)
        if hit is None:
            return None
        for mid, a in self.monsters.items():
            if hit.object in a.model.objects:
                return mid
        return None

    # -------------------------------------------------------------------------------------------------- state

    def sync(self, game, without=()):
        """Make the scene match the game at once, no animation (bar the Monsters `without`, still to come)."""
        for arc in range(ARCS):
            self._set_static(self.towers[arc], game.towers[arc], "Collapse")
            self._set_static(self.walls[arc], game.walls[arc], "Collapse")
            if self.forts[arc]:
                self.forts[arc].visible = bool(game.fortified[arc])
        live = set(game.monsters) - set(without)
        for mid in list(self.monsters):
            if mid not in live:
                self._remove_monster(mid)
        for mid, m in game.monsters.items():
            if mid not in live:
                continue
            if mid not in self.monsters:
                self._add_monster(m)
            self.mdata[mid] = dict(m)
        self._layout(animate=False)
        for mid, m in game.monsters.items():
            if mid in live:
                self._set_tar(mid, m["tar"])
        self._sentries(game)

    def _set_static(self, s, intact, clip):
        if s is None:
            return
        want = None if intact else clip
        if getattr(s, "_state", None) == want:
            return
        fresh = Static(self.lib, s.name, s.holder.position, s.yaw, s.scale, clip=want)
        s.parts, s.holder, s._state = fresh.parts, fresh.holder, want

    def _sentries(self, game):
        """A defender stands guard on each standing wall."""
        kinds = ["archer", "swordsman", "knight", "archer", "swordsman", "knight"]
        for arc in range(ARCS):
            want = game.walls[arc]
            have = self.sentries[arc]
            if want and have is None and self.lib.has(kinds[arc]):
                p, y, _ = board.wall_position(arc)  # y faces out of the castle, to the oncoming Monsters
                self.sentries[arc] = Actor(self.lib, kinds[arc], p + (0, 1.0, 0), y,
                                           scale=DEFENDER_SCALE * 0.8, rng=self.rng)
            elif not want and have is not None:
                self.sentries[arc] = None

    def _add_monster(self, m, at=None):
        kind = m["kind"]
        name = kind if self.lib.has(kind) else "goblin"
        p, y = board.space_position(m["arc"], m["ring"])
        a = Actor(self.lib, name, at if at is not None else p, y, scale=SCALE.get(kind, 1.5), rng=self.rng)
        self.monsters[m["id"]] = a
        self.mdata[m["id"]] = dict(m)
        return a

    def _remove_monster(self, mid):
        self.monsters.pop(mid, None)
        self.mdata.pop(mid, None)
        self.tars.pop(mid, None)

    def _layout(self, animate=True, only=None, duration=0.9):
        """Put every Monster in its slot (several share a space side by side, smaller the more there are; in a
        Castle space whose Tower has fallen, on the rubble)."""
        spaces = {}
        for mid in sorted(self.mdata):
            m = self.mdata[mid]
            spaces.setdefault((m["arc"], m["ring"]), []).append(mid)
        for (arc, ring), mids in spaces.items():
            rubble = ring == CASTLE and getattr(self.towers[arc], "_state", None) == "Collapse"
            for k, mid in enumerate(mids):
                a = self.monsters.get(mid)
                if a is None or a.dead:
                    continue
                a.holder.scale = SCALE.get(self.mdata[mid]["kind"], 1.5) * CROWD_SCALE.get(len(mids), CROWDED)
                p, y = board.space_position(arc, ring, k, len(mids), rubble)
                if not animate:
                    a.position = p
                    a.set_yaw(y)
                elif only is None or mid in only:
                    if np.linalg.norm(a.position - p) > 0.05:
                        self._wait_for(lambda done, a=a, p=p, y=y: a.move_to(p, duration, then=lambda: (a.face(y), done())))
                    else:
                        a.face(y)

    def _set_tar(self, mid, on):
        if on and mid not in self.tars and mid in self.monsters:
            p = self.monsters[mid].position
            self.tars[mid] = Object3D(TAR, p + (0, 0.02, 0), color=(14, 12, 10), specular=2.5, shininess=90,
                                      scale=1.3)
        elif not on:
            self.tars.pop(mid, None)

    # -------------------------------------------------------------------------------------------------- events

    def play(self, events):
        self.queue.extend(events)

    def busy(self):
        return bool(self.queue) or self.pending > 0 or self.wait > 0

    def _wait_for(self, start):
        """Start an animation that calls done() when it ends; the event queue waits for it."""
        self.pending += 1
        fired = [False]

        def done():
            if not fired[0]:
                fired[0] = True
                self.pending -= 1
        start(done)

    def update(self, dt):
        self.rig.update(dt)
        self.tick_timers(dt)
        for s in self.trees + self.towers + self.walls + self.forts:
            if s:
                s.update(dt)
        for a in list(self.monsters.values()):
            a.update(dt)
        for a in self.sentries:
            if a:
                a.update(dt)
        for a in self.defenders:
            a.update(dt)
        self.defenders = [a for a in self.defenders if a.visible]
        for mid, t in self.tars.items():
            a = self.monsters.get(mid)
            if a:
                t.position = a.position + (0, 0.02, 0)
        self.fx.update(dt)
        for b in self.banners:
            b.update(dt, self.rig.camera, self.aspect)
        for b in [b for b in self.banners if b.done]:
            self.banners.remove(b)
            b.then()
        if self.wait > 0:
            self.wait -= dt
        else:
            while self.queue and self.pending == 0 and self.wait <= 0:
                self._step(self.queue.pop(0))
        # once things have been still a moment, back to the whole board (unless the player is steering)
        if self.busy():
            self.quiet, self.homed = 0.0, False
        else:
            self.quiet += dt
            if self.quiet >= HOME_AFTER and not self.homed:
                self.homed = True
                self.rig.go_home()

    def _monster_point(self, mid, up=0.6):
        a = self.monsters.get(mid)
        return (a.position + (0, up, 0)) if a else np.zeros(3)

    def _step(self, e):
        k = e["e"]
        h = getattr(self, "_ev_" + k, None)
        if h:
            h(e)

    # ---- banners
    def banner(self, lines, style="gilt", then=None, hold=None):
        """Put lettering up; the event queue waits until it has gone, then then() is called."""
        def start(done):
            b = Banner(lines, style, hold)
            b.then = lambda: (then and then(), done())
            self.banners.append(b)
        self._wait_for(start)

    def skip_banners(self):
        for b in self.banners:
            b.skip()

    def _ev_banner(self, e):
        self.banner(e["lines"], e.get("style", "gilt"), hold=e.get("hold"))

    def _ev_sound(self, e):
        self.on_sound(e["name"])
        self.wait = e.get("wait", 0.0)

    def _announce(self, e):
        """Before the first new Monsters of a turn: "tHe mOnsTeRs aRe CoMing!", then (SPAWN_AFTER on) event e."""
        self.announced = True
        self.queue.insert(0, e)
        self.rig.go_home()

        def after():
            self.wait = SPAWN_AFTER
        self.banner(["tHe mOnsTeRs", "aRe CoMing!"], "stone", then=after)

    # ---- turns and cards
    def _ev_step(self, e):
        if self.step == (e["seat"], "draw_up") and not e.get("held"):  # Draw Up moves on by itself: leave it lit
            self.queue.insert(0, dict(e, held=True))  # a moment first
            self.wait = DRAW_UP_HOLD
            return
        self.step = (e["seat"], e["step"])

    def _ev_turn(self, e):
        self.step = (e["seat"], "draw_up")
        self.turn = e["turn"]
        self.on_sound("turn")
        self.rig.go_home()
        self.wait = 0.3
        self.announced = False
        if self.my_seat is not None and e.get("seat") == self.my_seat:
            self.banner(["Your turn.", "Defend the Castle!"], "stone")

    def _ev_wave(self, e):
        """The first Monsters march in together from the forest edge to their places."""
        if not self.announced:
            self._announce(e)
            return
        mids = set()
        for s in e["spawns"]:
            m = {"id": s["mid"], "kind": s["kind"], "arc": s["arc"], "ring": s["ring"], "hp": s["hp"],
                 "max": s["hp"], "tar": False}
            a = self._add_monster(m, at=board.polar(board.arc_angle(s["arc"]), 11.5))
            mids.add(s["mid"])
            if a.has("Roar"):
                self._after(self.rng.uniform(1.2, 2.2), lambda a=a: a.play("Roar"))
        self.on_sound("march")
        self._after(0.6, lambda: self.on_sound("spawn", kind="orc"))
        self._layout(only=mids, duration=2.2)

    def _ev_attack(self, e):
        mid = e["mid"]
        a = self.monsters.get(mid)
        m = self.mdata.get(mid)
        if not a or not m:
            return
        kind = e.get("kind") or "archer"
        self.rig.focus(a.position, dist=10)
        name = DEFENDER_FOR.get(kind, "swordsman")
        if not self.lib.has(name):
            name = "archer" if self.lib.has("archer") else None
        target = a.position
        arc = m["arc"]
        wp, wy, _ = board.wall_position(arc)
        start = wp + board.polar(board.arc_angle(arc), 0.45) + (0, 0.0, 0)
        if name is None:
            self.on_sound("hit")
            self.wait = 0.4
            return
        d = Actor(self.lib, name, start, 0.0, scale=DEFENDER_SCALE, rng=self.rng)
        d.set_yaw(math.atan2(target[0] - start[0], target[2] - start[2]))
        self.defenders.append(d)
        if name == "archer":
            def loose(done):
                self.on_sound("bow")
                d.play("Attack")
                def fly():
                    self.fx.arrow(start + (0, 1.1, 0), target + (0, 0.7, 0), 0.45, 0.8,
                                  then=lambda: (self.on_sound("arrow_hit"), done()))
                self._after(0.55, fly)
                self._after(1.6, lambda: setattr(d, "visible", False))
            self._wait_for(loose)
        else:
            near = target + (start - target) / max(np.linalg.norm(start - target), 1e-6) * 0.9
            def charge(done):
                self.on_sound("charge")
                hop = 0.9 if name == "barbarian" else 0.25
                def strike():
                    self.on_sound("swing")
                    d.play("Attack", then=lambda: d.move_to(start, 0.5, hop=0.3, then=lambda: setattr(d, "visible", False)))
                    self._after(0.45, done)
                d.move_to(near, 0.55, hop=hop, then=strike)
            self._wait_for(charge)

    def _after(self, t, fn):
        self._timers = getattr(self, "_timers", [])
        self._timers.append([t, fn])

    def tick_timers(self, dt):
        ts = getattr(self, "_timers", [])
        due = []
        for t in ts:
            t[0] -= dt
            if t[0] <= 0:
                due.append(t)
        for t in due:
            ts.remove(t)
            t[1]()

    def _ev_damage(self, e):
        mid = e["mid"]
        if mid in self.mdata:
            self.mdata[mid]["hp"] = e["hp"]
        a = self.monsters.get(mid)
        if not a:
            return
        if not e["slain"]:
            self.on_sound("monster_hurt", kind=self.mdata.get(mid, {}).get("kind"))
            self.fx.blood(self._monster_point(mid, 0.8))
            a.play("Hit")
            self.wait = 0.35

    def _ev_slain(self, e):
        mid = e["mid"]
        a = self.monsters.get(mid)
        if not a:
            self._remove_monster(mid)
            return
        self.on_sound("monster_die", kind=e.get("kind"))
        self.fx.blood(self._monster_point(mid, 0.6), 18)
        crushed = e.get("cause") == "boulder"
        self.mdata.pop(mid, None)
        self.tars.pop(mid, None)

        def die(done):
            def gone():
                self._after(0.8, lambda: self._sink(mid))
                done()
            if crushed:
                a.holder.scale = np.array([1.0, 0.25, 1.0]) * SCALE.get(e["kind"], 1.5)
                self.fx.debris(a.position + (0, 0.3, 0), 8, (90, 20, 15), 0.07)
                gone()
            elif not a.play("Die", then=gone):
                gone()
        self._wait_for(die)

    def _sink(self, mid):
        a = self.monsters.get(mid)
        if a:
            a.move_to(a.position - (0, 1.2, 0), 1.2, walk=False, face=False,
                      then=lambda: self.monsters.pop(mid, None))

    def _ev_tar(self, e):
        self.on_sound("tar")
        self._set_tar(e["mid"], True)
        a = self.monsters.get(e["mid"])
        if a:
            self.rig.focus(a.position)
            self.fx.burst(a.position + (0, 0.3, 0), (15, 12, 10), 14, speed=1.5, size=0.06, life=0.6)
        self.wait = 0.6

    def _ev_untar(self, e):
        self._set_tar(e["mid"], False)

    def _ev_driven(self, e):
        mid = e["mid"]
        if mid in self.mdata:
            self.mdata[mid]["ring"] = FOREST
        a = self.monsters.get(mid)
        self.on_sound("drive_back")
        if a:
            p, y = board.space_position(e["arc"], FOREST)
            self._wait_for(lambda done: a.move_to(p, 1.0, hop=2.0, walk=False, face=False,
                                                  then=lambda: (a.play("Hit"), self._layout(), done())))

    def _ev_fortify(self, e):
        f = self.forts[e["arc"]]
        self.on_sound("build")
        if f:
            f.visible = True
            f.play("Build")
            self.rig.focus(f.holder.position, dist=9)
        self.wait = 0.9

    def _ev_build(self, e):
        arc = e["arc"]
        self.on_sound("build")
        w = self.walls[arc]
        if w:
            self._set_static(w, True, "Collapse")
            w.holder.position = w.holder.position - (0, 1.0, 0)
            self.rig.focus(w.holder.position, dist=9)
            pos = w.holder.position.copy()

            def rise(done):
                n = [0.0]

                def step():
                    n[0] += 0.05
                    w.holder.position = pos + (0, min(1.0, n[0] / 0.8), 0)
                    if n[0] < 0.8:
                        self._after(0.05, step)
                    else:
                        done()
                step()
                self.fx.dust(pos + (0, 1.0, 0), 10)
            self._wait_for(rise)
        self._after(1.0, lambda: self._sentries_from_walls())

    def _sentries_from_walls(self):
        class G:
            pass
        g = G()
        g.walls = [getattr(w, "_state", None) is None for w in self.walls]
        self._sentries(g)

    def _ev_missing(self, e):
        """Missing is played: no new Monsters this turn, and everyone breathes out."""
        self.on_sound("missing")
        self.rig.go_home()
        self.banner(["Missing!", "No Monsters this turn", "(whew!)"], "gilt", hold=1.6)

    def _ev_draw2(self, e):
        self.on_sound("card")

    # ---- monsters
    def _ev_monster_phase(self, e):
        self.step = (e["seat"], "move")
        self.on_sound("monsters_move")
        self.rig.go_home()
        self.wait = 0.4

    def _ev_draw_monsters(self, e):
        self.step = (e["seat"], "draw_monsters")
        self.rig.go_home()

    def _ev_token(self, e):
        """A Monster token is drawn: its name in gilt lettering (after "tHe mOnsTeRs aRe CoMing!" for the turn's
        first), then a pause before it takes effect."""
        if not self.announced:
            self._announce(e)
            return
        self.on_sound("token", kind=e["kind"])

        def after():
            self.wait = TOKEN_AFTER
        self.banner(TOKEN_BANNER.get(e["kind"], ["A Monster!"]), "gilt", then=after, hold=TOKEN_HOLD)

    def _ev_boss_power(self, e):
        """A Boss Monster has arrived: what its power does, in gilt lettering, before it takes effect."""
        def after():
            self.wait = TOKEN_AFTER
        self.rig.go_home()
        self.banner(BOSS_BANNER[e["kind"]], "gilt", then=after, hold=TOKEN_HOLD + 0.4)

    def _ev_spawn(self, e):
        if e["mid"] in self.monsters:
            return
        if e["ring"] == FOREST and not self.announced:
            self._announce(e)
            return
        m = {"id": e["mid"], "kind": e["kind"], "arc": e["arc"], "ring": e["ring"], "hp": e["hp"], "max": e["hp"],
             "tar": False}
        deg = board.arc_angle(e["arc"])
        if e["ring"] == FOREST:
            start = board.polar(deg, 11.5)
            a = self._add_monster(m, at=start)
            self.on_sound("spawn", kind=e["kind"])
            self.rig.focus(board.polar(deg, 8.5), dist=12)
            self._wait_for(lambda done: self._layout(only={e["mid"]}, duration=1.1) or done())
            if a.has("Roar"):
                self._after(1.2, lambda: a.play("Roar"))
        else:
            self._add_monster(m)
            self._layout(animate=False)

    def _ev_move_begin(self, e):
        self._moving = []

    def _ev_move(self, e):
        mid = e["mid"]
        if mid in self.mdata:
            self.mdata[mid]["arc"], self.mdata[mid]["ring"] = e["to"]
        getattr(self, "_moving", []).append(mid)

    def _ev_move_end(self, e):
        moving = set(getattr(self, "_moving", []))
        self._moving = []
        if moving:
            self.on_sound("march")
            self._layout(only=moving)

    def _flush_moves(self):
        moving = set(getattr(self, "_moving", []))
        if moving:
            self._moving = []
            self._layout(only=moving)

    def _ev_wall_hit(self, e):
        self._flush_moves()
        arc = e["arc"]
        a = self.monsters.get(e["mid"])
        w, f = self.walls[arc], self.forts[arc]
        self.rig.focus(board.wall_position(arc)[0], dist=9)

        def smash(done):
            def crash():
                self.on_sound("wall_crash")
                p = board.wall_position(arc)[0]
                self.fx.dust(p + (0, 0.5, 0), 20, 1.5)
                self.fx.debris(p + (0, 0.8, 0), 14)
                if e["fortified"]:
                    if f:
                        f.play("Collapse", then=lambda: setattr(f, "visible", False))
                elif w:
                    w.play("Collapse", settle="Collapse")
                    w._state = "Collapse"
                    self.sentries[arc] = None
                done()
            self.on_sound("monster_attack")
            if a:
                a.play("Attack")
            self._after(0.6, crash)
        self._wait_for(smash)
        self.wait = 0.8

    def _ev_tower_hit(self, e):
        self._flush_moves()
        arc = e["arc"]
        a = self.monsters.get(e["mid"])
        t = self.towers[arc]
        self.rig.focus(board.tower_position(arc)[0], dist=9, pitch=30)

        def smash(done):
            def crash():
                self.on_sound("tower_fall")
                p = board.tower_position(arc)[0]
                self.fx.dust(p + (0, 0.5, 0), 30, 2.0)
                self.fx.debris(p + (0, 1.5, 0), 20, size=0.14)
                if t:
                    t.play("Collapse", settle="Collapse")
                    t._state = "Collapse"
                for m in self.monsters.values():
                    if m.has("Roar") and not m.busy() and self.rng.random() < 0.5:
                        m.play("Roar")
                self._after(1.8, lambda: (self._layout(), done()))  # the attackers climb onto the rubble
            self.on_sound("monster_attack")
            if a:
                a.play("Attack")
            self._after(0.6, crash)
        self._wait_for(smash)

    def _ev_heal(self, e):
        mid = e["mid"]
        if mid in self.mdata:
            self.mdata[mid]["hp"] = e["hp"]
        self.on_sound("heal")
        self.fx.sparkle(self._monster_point(mid, 0.5))
        self.wait = 0.15

    def _ev_boulder(self, e):
        """The Giant Boulder rolls in from the forest along its arc, through the castle if nothing stops it."""
        arc = e["arc"]
        deg = board.arc_angle(arc)
        stop = e.get("stop")
        if stop:
            what, sarc = stop
            if what == "tower":
                end_r, end_deg = 1.6, board.arc_angle(sarc)
            else:
                end_r, end_deg = board.R[0] + 0.3, board.arc_angle(sarc)
            end = board.polar(end_deg, end_r) if sarc == arc else board.polar(deg, -end_r)
        else:
            end = board.polar(deg, -11.5)
        start = board.polar(deg, 11.5)
        self.rig.focus(board.polar(deg, 5.0), dist=16, pitch=45)
        rock = Static(self.lib, "boulder", start + (0, 0.75, 0), 0.0, 1.5) if self.lib.has("boulder") else None
        crushed = list(e.get("crushed", []))
        self.on_sound("boulder_roll")
        length = np.linalg.norm(end - start)
        dur = length / 9.0

        def roll(done):
            t = [0.0]
            spin = [0.0]
            axis = np.cross(np.array([0.0, 1.0, 0.0]), (end - start) / max(length, 1e-6))

            def step():
                t[0] += 1 / 30
                u = min(1.0, t[0] / dur)
                p = start + (end - start) * u
                if rock:
                    rock.holder.position = p + (0, 0.75, 0)
                    spin[0] -= 9.0 / 30 / 0.75
                    rock.holder.rotation = quat_axis_angle(axis, -spin[0])
                if int(t[0] * 30) % 3 == 0:
                    self.fx.dust(p + (0, 0.2, 0), 3, 1.2)
                for mid in list(crushed):
                    a = self.monsters.get(mid)
                    if a is not None and np.linalg.norm((a.position - p)[[0, 2]]) < 1.2:
                        crushed.remove(mid)
                        self.on_sound("crush")
                        a.holder.scale = np.array([1.2, 0.2, 1.2]) * SCALE.get(a.name, 1.5)
                        self.fx.debris(a.position + (0, 0.3, 0), 10, (100, 20, 15), 0.08)
                if u < 1.0:
                    self._after(1 / 30, step)
                else:
                    if stop:
                        self.on_sound("wall_crash" if stop[0] != "tower" else "tower_fall")
                        self.fx.dust(p + (0, 0.6, 0), 30, 2.0)
                        self.fx.debris(p + (0, 1.0, 0), 20)
                        what, sarc = stop
                        if what == "tower" and self.towers[sarc]:
                            self.towers[sarc].play("Collapse", settle="Collapse")
                            self.towers[sarc]._state = "Collapse"
                        elif what == "wall" and self.walls[sarc]:
                            self.walls[sarc].play("Collapse", settle="Collapse")
                            self.walls[sarc]._state = "Collapse"
                            self.sentries[sarc] = None
                        elif what == "fortify" and self.forts[sarc]:
                            f = self.forts[sarc]
                            f.play("Collapse", then=lambda: setattr(f, "visible", False))
                    if rock:
                        self._after(0.6, lambda: self.trees.remove(rock) if rock in self.trees else None)
                    self._after(0.8, done)
            if rock:
                self.trees.append(rock)
            step()
        self._wait_for(roll)

    def _ev_game_over(self, e):
        self.rig.go_home()
        if e["result"] == "won":
            self.on_sound("victory")
            for s in self.sentries:
                if s:
                    s.play("Cheer")
        else:
            self.on_sound("defeat")
            for m in self.monsters.values():
                m.play("Roar")
