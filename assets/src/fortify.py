import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

NAME = "fortify"
reset()
rng = new_rng(31)
wood = tex_wood(rng, (0.30, 0.21, 0.13))
wood = mix(wood, [0.18, 0.24, 0.1], smoothstep(0.65, 0.9, noise(rng, 1.6)) * 0.4)  # moss
char = mix(tex_wood(rng, (0.14, 0.10, 0.07)), [0.03, 0.03, 0.03], smoothstep(0.4, 0.8, noise(rng, 1.2)) * 0.7)
t = save_textures(NAME, {"wood": wood, "char": char, "iron": tex_metal(rng, (0.24, 0.23, 0.24), rust=0.6),
                         "rope": tex_cloth(rng, (0.42, 0.34, 0.22), wear=0.6)})
M = {"wood": material("Wood", image=t["wood"], roughness=0.9), "char": material("Char", image=t["char"], roughness=1),
     "iron": material("Iron", image=t["iron"], roughness=0.5, metallic=0.6),
     "rope": material("Rope", image=t["rope"], roughness=1)}
J = {}
def jp(name, at=(0, 0, 0), turn=(0, 0, 0), parent=None):
    J[name] = pivot(name, at, turn, parent)
    return J[name]

root = jp("Root")
stakes = []
n = 13
for i in range(n):
    x = -1.04 + i * 2.08 / (n - 1) + float(rng.uniform(-0.03, 0.03))
    h = float(rng.uniform(0.62, 0.8))
    r = float(rng.uniform(0.045, 0.06))
    lean = (float(rng.uniform(7, 13)), float(rng.uniform(-5, 5)), float(rng.uniform(0, 60)))
    p = jp(f"Stake{i}", at=(x, float(rng.uniform(-0.02, 0.02)), 0), turn=lean, parent=root)
    tip = 0.14 + float(rng.uniform(-0.02, 0.03))
    piece("cylinder", f"Shaft{i}", size=(2 * r, 2 * r, h - tip), at=(0, 0, (h - tip) / 2), verts=6, mat=M["wood"],
          parent=p, jitter=0.004, flat_shade=True, tile=0.4)
    tp = jp(f"Tip{i}", at=(0, 0, h - tip), parent=p)
    piece("cone", f"Point{i}", size=(2 * r, 2 * r, tip), at=(0, 0, tip / 2), verts=6, mat=M["char"], parent=tp,
          shape_at=(float(rng.uniform(-0.01, 0.01)), 0, 0), flat_shade=True)
    if i % 3 == 1:
        piece("cylinder", f"Band{i}", size=(2 * r + 0.018, 2 * r + 0.018, 0.04), at=(0, 0, 0.18 + 0.1 * (i % 2)),
              verts=6, mat=M["iron"], parent=p, flat_shade=True)
    stakes.append((p, tp, x, h))
# two lashed cross-rails in front (-Y) the stakes, with rope lashings and iron bands
rails = []
for k, (z, y) in enumerate(((0.2, -0.085), (0.46, -0.13))):
    p = jp(f"Rail{k}", at=(0, y, z), turn=(0, 1.5 * (1 - 2 * k), 0), parent=root)
    piece("cylinder", f"RailPole{k}", size=(0.05, 0.05, 2.15), shape_turn=(0, 90, 0), verts=6, mat=M["wood"],
          parent=p, jitter=0.003, flat_shade=True)
    for i, (_, _, x, _) in enumerate(stakes):
        if i % 2 == k:
            piece("cylinder", f"Lash{k}_{i}", size=(0.07, 0.07, 0.05), at=(x, 0.02, 0), shape_turn=(0, 90, 30),
                  verts=6, mat=M["rope"] if i % 4 else M["iron"], parent=p, flat_shade=True)
    rails.append(p)

def u(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)

def build(t):
    p = rest_pose(J)
    for i, (s, tp, x, h) in enumerate(stakes):
        order = (i * 5) % n
        v = u(t, 0.03 * order, 0.03 * order + 0.32)
        e = 1 - (1 - v) ** 3
        p[s.name]["loc"] = [0, 0, -h * (1 - e)]
        sc = max(0.001, e)
        p[s.name]["scale"] = [1, 1, sc]
        p[s.name]["rot"] = [3 * math.sin(v * math.pi) * (1 - v), 0, 0]
    for k, r in enumerate(rails):
        v = u(t, 0.5 + 0.1 * k, 0.75 + 0.05 * k)
        p[r.name]["scale"] = [max(0.001, v), max(0.001, min(1, 3 * v)), max(0.001, min(1, 3 * v))]
    return p

spins = [float(x) for x in rng.uniform(-1, 1, n)]
def collapse(t):
    p = rest_pose(J)
    for i, (s, tp, x, h) in enumerate(stakes):
        t0 = 0.05 * ((i * 7) % n)
        v = u(t, t0, t0 + 0.5)
        fall = v * v
        p[s.name]["rot"] = [(70 + 10 * spins[i]) * fall, 25 * spins[i] * fall, 0]  # topple outward (-Y)
        p[s.name]["loc"] = [0, -0.05 * fall, 0.04 * fall]
        # the sharpened tip splinters off
        w = u(t, t0 + 0.35, t0 + 0.8)
        p[tp.name]["loc"] = [0.15 * spins[i] * w, -0.1 * w, 0.15 * math.sin(w * math.pi) + 0.06 * w]
        p[tp.name]["rot"] = [-120 * w, 200 * spins[i] * w, 0]
    for k, r in enumerate(rails):
        v = u(t, 0.25 + 0.15 * k, 0.85 + 0.15 * k)
        p[r.name]["loc"] = [0, -0.12 * v, -(0.2 if k == 0 else 0.42) * v * v + 0.03 * v]
        p[r.name]["rot"] = [0, (6 - 12 * k) * v, 0]
    return p

record(J, "Build", build, 0.8)
record(J, "Collapse", collapse, 1.6)
export(NAME, J)
