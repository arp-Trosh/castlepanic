import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

NAME = "wall"
reset()
rng = new_rng(23)
t = save_textures(NAME, {
    "stone": tex_stone(rng, (0.37, 0.40, 0.48), moss=0.5, soot=0.55),
    "stone2": tex_stone(rng, (0.33, 0.36, 0.42), moss=0.3, soot=0.7),
    "rubble": tex_stone(rng, (0.33, 0.34, 0.37), moss=0.5, blocks=False, soot=0.5),
})
M = {k: material(k.capitalize(), image=t[k], roughness=0.9) for k in t}
J = {}
def jp(name, at=(0, 0, 0), turn=(0, 0, 0), parent=None):
    J[name] = pivot(name, at, turn, parent)
    return J[name]

root = jp("Root")
L, T = 2.2, 0.35
# three wall sections, each its own pivot at ground level
secs = []
xs = [(-1.1, -0.38), (-0.38, 0.4), (0.4, 1.1)]
for k, (a, b) in enumerate(xs):
    cx = (a + b) / 2
    p = jp(f"Section{k}", at=(cx, 0, 0), parent=root)
    w = b - a + 0.004
    block(f"Plinth{k}", (w, T + 0.08, 0.16), at=(0, 0, 0.08), mat=M["stone2"], parent=p, bevel=0.015, tile=0.6)
    block(f"Body{k}", (w, T, 0.62), at=(0, 0, 0.47), mat=M["stone"], parent=p, bevel=0.01, tile=0.6,
          taper=(1, 0.94), jitter=0.004)
    block(f"Course{k}", (w, T + 0.06, 0.06), at=(0, 0, 0.8), mat=M["stone2"], parent=p, bevel=0.012)
    secs.append((p, cx))
# buttresses on the inner (+Y) side
for k, x in enumerate((-0.75, 0.0, 0.78)):
    sec = min(range(3), key=lambda i: abs(secs[i][1] - x))
    p, cx = secs[sec]
    block(f"Buttress{k}", (0.2, 0.22, 0.66), at=(x - cx, T / 2 + 0.09, 0.33), taper=(0.85, 0.35), mat=M["stone2"],
          parent=p, bevel=0.02)
# a few loose facing stones (outer -Y face)
chunks = []
for k in range(6):
    x, z = float(rng.uniform(-1.0, 1.0)), float(rng.uniform(0.25, 0.7))
    p = jp(f"Chunk{k}", at=(x, -T / 2 + 0.005, z), turn=(0, 0, rng.uniform(-4, 4)), parent=root)
    block(f"ChunkStone{k}", (0.16, 0.05, 0.09), mat=M["stone2"], parent=p, jitter=0.005, flat_shade=True)
    chunks.append((p, z))
# merlons
merlons = []
n = 6
for i in range(n):
    x = -L / 2 + 0.16 + i * (L - 0.32) / (n - 1)
    h = 0.17 - (0.06 if i == 4 else 0) - 0.015 * (i % 2)
    p = jp(f"Merlon{i}", at=(x, 0, 0.83), turn=(0, 0, rng.uniform(-3, 3)), parent=root)
    block(f"MerlonStone{i}", (0.24, T * 0.9, h), at=(0, 0, h / 2), mat=M["stone"], parent=p, jitter=0.004,
          taper=(0.92, 0.95), flat_shade=True)
    merlons.append((p, x))
# rubble (hidden until the collapse)
rubble = []
for k in range(12):
    x = float(rng.uniform(-1.05, 1.05))
    y = float(rng.normal(0, 0.25))
    s = float(rng.uniform(0.22, 0.4))
    p = jp(f"Rubble{k}", at=(x, y, 0.12 if abs(y) < 0.15 else 0), turn=(0, 0, rng.uniform(0, 360)), parent=root)
    p.scale = (0.001,) * 3
    piece("ico", f"RubbleStone{k}", size=(s * 1.4, s, s * 0.6), at=(0, 0, s * 0.15), mat=M["rubble"], parent=p,
          jitter=0.035, flat_shade=True)
    rubble.append((p, abs(x)))

def u(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)

def tumble(q, t, t0, dur, out_xy, drop, spin):
    v = u(t, t0, t0 + dur)
    e = 1 - (1 - v) ** 2
    q["loc"] = [out_xy[0] * e, out_xy[1] * e, -drop * v * v]
    q["rot"] = [spin[0] * v, spin[1] * v, spin[2] * v]

spins = [float(x) for x in rng.uniform(-260, 260, 12)]
def collapse(t):
    p = rest_pose(J)
    for i, (m, x) in enumerate(merlons):
        t0 = 0.05 + 0.09 * ((i * 4) % n)
        sy = -1 if i % 3 else 1
        tumble(p[m.name], t, t0, 0.6, (0.15 * x, sy * (0.45 + 0.1 * (i % 2))), 0.8, (sy * spins[i], 0, spins[i + 6] * 0.3))
    for k, (c, z) in enumerate(chunks):
        tumble(p[c.name], t, 0.45 + 0.07 * k, 0.55, (0.1 * (k % 3 - 1), -0.5 - 0.1 * (k % 2)), z - 0.03, (-280, 0, 60))
    # the middle crumbles first, then the ends slump inward
    for k, (s, cx) in enumerate(secs):
        t0 = 0.55 if k == 1 else 0.85 + 0.1 * k
        v = u(t, t0, t0 + 0.75)
        tilt = 0 if k == 1 else (-1 if k == 0 else 1) * -14
        p[s.name]["scale"] = [1 + 0.08 * v, 1 + 0.25 * v, 1 - (0.85 if k == 1 else 0.7) * v]
        p[s.name]["rot"] = [8 * v * (1 if k != 2 else -1), tilt * v, 0]
        if k == 1:
            g = 1 - 0.999 * u(t, 1.25, 1.45)
            p[s.name]["scale"] = [a * g for a in p[s.name]["scale"]]
    for r, d in rubble:
        g = 1000 * u(t, 0.6 + 0.5 * d, 1.1 + 0.6 * d)
        p[r.name]["scale"] = [max(g, 1)] * 3
    return p

record(J, "Collapse", collapse, 1.8)
export(NAME, J)
