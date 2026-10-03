"""Little moving things that aren't models: arrows in flight, dust and debris, blood, sparkles. Each particle is an
Object3D on a shared small mesh, flying under gravity, spinning, and shrinking away at the end of its life."""
import math
import random

import numpy as np

from unicode3d.mesh import make_box
from unicode3d.scene import Object3D
from unicode3d.shapes import blob_mesh
from unicode3d.transforms import quat_axis_angle, quat_between

CUBE = make_box(1.0)
BALL = blob_mesh((0.5, 0.5, 0.5), rings=4, segments=6)
GRAVITY = 9.0


def _rot(axis, angle):
    return quat_axis_angle(np.asarray(axis, float), angle)


class Particle:
    __slots__ = ("obj", "vel", "spin", "axis", "life", "age", "size", "ground", "drag", "grow", "angle")

    def __init__(self, obj, vel, life, size, spin=0.0, ground=0.0, drag=0.0, grow=0.0):
        self.obj, self.vel, self.life, self.size = obj, np.asarray(vel, float), life, size
        self.spin, self.axis, self.age, self.ground = spin, np.random.normal(size=3), 0.0, ground
        self.drag, self.grow, self.angle = drag, grow, 0.0


class Effects:
    def __init__(self, rng=None):
        self.parts = []
        self.arrows = []
        self.rng = rng or random.Random()

    def objects(self):
        return [p.obj for p in self.parts] + [a[0] for a in self.arrows]

    # ---------------------------------------------------------------------------------------------- emitters

    def burst(self, at, color, count=12, speed=2.0, size=0.08, life=0.8, up=1.5, mesh=None, ground=0.0,
              spin=8.0, drag=0.0, grow=0.0, emissive=0.0):
        r = self.rng
        for _ in range(count):
            d = np.array([r.gauss(0, 1), abs(r.gauss(0, 1)) * up, r.gauss(0, 1)])
            v = d / max(np.linalg.norm(d), 1e-6) * speed * r.uniform(0.4, 1.0)
            s = size * r.uniform(0.6, 1.4)
            o = Object3D(mesh or CUBE, np.asarray(at, float) + r.uniform(-0.05, 0.05), color=color, scale=s,
                         specular=0.1, emissive=emissive, cast_shadows=False)
            self.parts.append(Particle(o, v, life * r.uniform(0.7, 1.3), s, spin * r.uniform(0.5, 1.5), ground,
                                       drag, grow))

    def dust(self, at, count=14, spread=1.0, color=(120, 105, 85)):
        """Grey-brown puffs that billow and settle: footfalls, a boulder rolling, a wall crashing."""
        self.burst(at, color, count, speed=1.2 * spread, size=0.16 * spread, life=1.1, up=0.8, mesh=BALL,
                   spin=1.0, drag=2.5, grow=0.6)

    def debris(self, at, count=10, color=(95, 95, 100), size=0.1):
        """Stone chips flung up and bouncing."""
        self.burst(at, color, count, speed=3.5, size=size, life=1.4, up=2.2, ground=0.0)

    def blood(self, at, count=10):
        self.burst(at, (110, 8, 6), count, speed=2.2, size=0.05, life=0.7, up=1.2, mesh=BALL, ground=0.0)

    def sparkle(self, at, color=(120, 255, 140), count=10):
        self.burst(at, color, count, speed=0.8, size=0.05, life=1.0, up=3.0, mesh=BALL, spin=0, drag=1.0,
                   emissive=1.0)

    def arrow(self, start, end, duration=0.45, arc=0.6, then=None, color=(150, 120, 80)):
        """An arrow (a thin stick with a pale fletching) along a shallow arc; then() when it lands."""
        o = Object3D(CUBE, np.asarray(start, float), color=color, scale=(0.03, 0.03, 0.45), specular=0.2,
                     cast_shadows=False)
        self.arrows.append([o, np.asarray(start, float), np.asarray(end, float), duration, 0.0, arc, then])

    # ---------------------------------------------------------------------------------------------- update

    def update(self, dt):
        keep = []
        for p in self.parts:
            p.age += dt
            if p.age >= p.life:
                continue
            p.vel[1] -= GRAVITY * dt * (0.15 if p.drag else 1.0)
            if p.drag:
                p.vel *= max(0.0, 1 - p.drag * dt)
            pos = p.obj.position + p.vel * dt
            if pos[1] < p.ground and p.vel[1] < 0:
                pos[1] = p.ground
                p.vel[1] *= -0.3
                p.vel[0] *= 0.6
                p.vel[2] *= 0.6
                p.spin *= 0.5
            p.obj.position = pos
            p.angle += p.spin * dt
            p.obj.rotation = _rot(p.axis, p.angle)
            u = p.age / p.life
            s = p.size * (1 + p.grow * u) * (1.0 if u < 0.6 else max(0.001, (1 - u) / 0.4))
            p.obj.scale = s
            keep.append(p)
        self.parts = keep
        live = []
        for a in self.arrows:
            o, s, e, dur, t, h, then = a
            t += dt
            a[4] = t
            u = min(1.0, t / dur)
            p = s + (e - s) * u
            p[1] += h * 4 * u * (1 - u)
            # point along the direction of flight
            du = min(1.0, u + 0.02)
            q = s + (e - s) * du
            q[1] += h * 4 * du * (1 - du)
            d = q - p if u < 1 else e - s
            if np.linalg.norm(d) > 1e-6:
                o.rotation = quat_between(np.array([0.0, 0.0, 1.0]), d / np.linalg.norm(d))
            o.position = p
            if u >= 1.0:
                if then:
                    then()
                continue
            live.append(a)
        self.arrows = live
