import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

NAME = "tower"
reset()
rng = new_rng(11)
STONE = (0.37, 0.40, 0.48)
t = save_textures(NAME, {
    "stone": tex_stone(rng, STONE, moss=0.45, soot=0.55),
    "stone2": tex_stone(rng, (0.33, 0.36, 0.42), moss=0.25, soot=0.7),
    "rubble": tex_stone(rng, (0.33, 0.34, 0.37), moss=0.5, blocks=False, soot=0.5),
    "slate": tex_stone(rng, (0.17, 0.18, 0.22), moss=0.2, soot=0.3),
    "wood": tex_wood(rng, (0.22, 0.15, 0.09)),
    "iron": tex_metal(rng, (0.22, 0.22, 0.24)),
    "cloth": tex_cloth(rng, (0.88, 0.86, 0.80), wear=0.15),
})
M = {k: material(k.capitalize(), image=t[k], roughness=0.9) for k in ("stone", "stone2", "rubble", "slate", "wood")}
M["iron"] = material("Iron", image=t["iron"], roughness=0.5, metallic=0.6)
M["slit"] = flat("Slit", (0.02, 0.02, 0.025), roughness=1)
CLOTH = material("BannerCloth", image=t["cloth"], roughness=1)
CLOTH.use_backface_culling = False

J = {}
def jp(name, at=(0, 0, 0), turn=(0, 0, 0), parent=None):
    J[name] = pivot(name, at, turn, parent)
    return J[name]

OCT = (0, 0, 22.5)  # flat face toward -Y
root = jp("Root")
# ---- base (0 .. 0.85): flared plinth, door
base = jp("Base", parent=root)
piece("cylinder", "Plinth", size=(1.16, 1.16, 0.22), at=(0, 0, 0.11), verts=8, shape_turn=OCT, taper=(0.93, 0.93),
      mat=M["stone2"], parent=base, bevel=0.02, flat_shade=True, tile=0.6)
piece("cylinder", "BaseBody", size=(1.02, 1.02, 0.7), at=(0, 0, 0.55), verts=8, shape_turn=OCT, taper=(0.97, 0.97),
      mat=M["stone"], parent=base, flat_shade=True, tile=0.6)
fy = -0.505
block("DoorFrame", (0.34, 0.06, 0.4), at=(0, fy + 0.0, 0.27), mat=M["stone2"], parent=base)
piece("cylinder", "DoorArchFrame", size=(0.34, 0.34, 0.06), at=(0, fy, 0.47), shape_turn=(90, 0, 0), verts=10,
      mat=M["stone2"], parent=base)
block("Door", (0.24, 0.05, 0.34), at=(0, fy - 0.015, 0.2), mat=M["wood"], parent=base, bevel=0.005)
piece("cylinder", "DoorArch", size=(0.24, 0.24, 0.05), at=(0, fy - 0.015, 0.37), shape_turn=(90, 0, 0), verts=10,
      mat=M["wood"], parent=base)
for z in (0.12, 0.3):
    block(f"DoorBand{z}", (0.25, 0.06, 0.025), at=(0, fy - 0.02, z), mat=M["iron"], parent=base, bevel=0.004)

# ---- middle (0.85 .. 1.75)
mid = jp("Mid", at=(0, 0, 0.85), parent=root)
piece("cylinder", "MidBody", size=(0.98, 0.98, 0.92), at=(0, 0, 0.45), verts=8, shape_turn=OCT, taper=(0.93, 0.93),
      mat=M["stone"], parent=mid, flat_shade=True, tile=0.6)
piece("cylinder", "Course", size=(1.04, 1.04, 0.07), at=(0, 0, 0.0), verts=8, shape_turn=OCT, mat=M["stone2"],
      parent=mid, flat_shade=True, bevel=0.01)

def face(i, r):
    a = math.radians(-90 + 45 * i)
    return math.cos(a) * r, math.sin(a) * r, math.degrees(a) + 90

# arrow slits on alternate faces (dark, slightly proud of the wall so they read)
for i, z in ((0, 0.5), (2, 0.35), (4, 0.55), (6, 0.4), (1, 0.62), (7, 0.6)):
    x, y, rz = face(i, 0.455 - 0.03 * z)
    block(f"Slit{i}", (0.05, 0.03, 0.22), at=(x, y, z), turn=(0, 0, rz), mat=M["slit"], parent=mid, bevel=0.005)
for i, z in ((0, 0.12), (4, -0.55)):  # low slits on the base
    x, y, rz = face(i, 0.49)
    if i == 4:
        block("SlitB", (0.05, 0.03, 0.18), at=(x, y, 0.5), turn=(0, 0, rz), mat=M["slit"], parent=base, bevel=0.005)

# loose facing stones that blow out in the collapse
chunks = []
for k in range(7):
    i = int(rng.integers(0, 8))
    z = float(rng.uniform(0.15, 0.85))
    x, y, rz = face(i + rng.uniform(-0.3, 0.3), 0.445 - 0.03 * z)
    p = jp(f"Chunk{k}", at=(x, y, z + 0.85), turn=(0, 0, rz), parent=root)
    block(f"ChunkStone{k}", (0.2, 0.06, 0.11), mat=M["stone2"], parent=p, jitter=0.006)
    chunks.append((p, i, z + 0.85))

# ---- top (1.75 .. 2.4): corbels, jutting machicolation, parapet, merlons
top = jp("Top", at=(0, 0, 1.75), parent=root)
for i in range(8):
    x, y, rz = face(i + 0.5, 0.45)
    block(f"Corbel{i}", (0.09, 0.16, 0.14), at=(x, y, -0.02), turn=(0, 0, rz), taper_bottom=(0.8, 0.4),
          mat=M["stone2"], parent=top)
piece("cylinder", "Machicolation", size=(1.16, 1.16, 0.14), at=(0, 0, 0.12), verts=8, shape_turn=OCT,
      mat=M["stone2"], parent=top, flat_shade=True, bevel=0.015)
piece("cylinder", "Parapet", size=(1.12, 1.12, 0.22), at=(0, 0, 0.3), verts=8, shape_turn=OCT, taper=(0.98, 0.98),
      mat=M["stone"], parent=top, flat_shade=True, tile=0.6)
merlons = []
for i in range(8):
    x, y, rz = face(i, 0.49)
    p = jp(f"Merlon{i}", at=(x, y, 2.16), turn=(0, 0, rz), parent=root)
    hgt = 0.24 - (0.07 if i == 3 else 0) - 0.02 * (i % 2)
    block(f"MerlonStone{i}", (0.26, 0.12, hgt), at=(0, 0, hgt / 2), mat=M["stone"], parent=p, jitter=0.004,
          taper=(0.92, 1), flat_shade=True)
    merlons.append((p, i))

# ---- roof
roof = jp("Roof", at=(0, 0, 2.15), parent=root)
piece("cone", "Spire", size=(0.98, 0.98, 1.25), at=(0, 0, 0.62), verts=8, shape_turn=OCT, mat=M["slate"],
      parent=roof, flat_shade=True, tile=0.4)
piece("cylinder", "Eave", size=(1.0, 1.0, 0.06), at=(0, 0, 0.02), verts=8, shape_turn=OCT, mat=M["slate"],
      parent=roof, flat_shade=True)
piece("sphere", "Finial", size=(0.06, 0.06, 0.06), at=(0, 0, 1.25), verts=6, mat=M["iron"], parent=roof)
piece("cylinder", "Pole", size=(0.025, 0.025, 0.45), at=(0, 0, 1.45), verts=6, mat=M["wood"], parent=roof)
ban = jp("Banner", at=(0, 0, 1.64), parent=roof)
piece("cube", "BannerFlag", size=(0.34, 0.012, 0.16), at=(0.18, 0, 0), mat=CLOTH, parent=ban, turn=(0, 4, 0))
piece("cube", "BannerTail", size=(0.12, 0.012, 0.07), at=(0.38, 0, 0.04), turn=(0, -8, 0), mat=CLOTH, parent=ban)
piece("cube", "BannerTail2", size=(0.12, 0.012, 0.06), at=(0.38, 0, -0.045), turn=(0, 10, 0), mat=CLOTH, parent=ban)

# ---- rubble (hidden until the collapse)
rubble = []
for k in range(15):
    a = rng.uniform(0, 2 * math.pi)
    d = rng.uniform(0.1, 0.9)
    s = rng.uniform(0.28, 0.5) * (1.3 - 0.5 * d)
    zz = 0.3 if k < 4 else 0
    d = d * 0.35 if k < 4 else d
    p = jp(f"Rubble{k}", at=(math.cos(a) * d, math.sin(a) * d, zz), turn=(0, 0, rng.uniform(0, 360)), parent=root)
    p.scale = (0.001,) * 3
    piece("ico", f"RubbleStone{k}", size=(s * 1.4, s, s * 0.7), at=(0, 0, s * 0.2), mat=M["rubble"], parent=p,
          jitter=0.04, flat_shade=True)
    rubble.append((p, d))

def u(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)

def tumble(q, t, t0, dur, out_xy, drop, spin):
    v = u(t, t0, t0 + dur)
    q["loc"] = [out_xy[0] * (1 - (1 - v) ** 2), out_xy[1] * (1 - (1 - v) ** 2), -drop * v * v]
    q["rot"] = [spin[0] * v, spin[1] * v, spin[2] * v]

def collapse(t):
    p = rest_pose(J)
    # roof pitches over toward +X and falls first, shattering on landing
    v = u(t, 0.0, 0.9)
    p["Roof"]["rot"] = [10 * v, 75 * v * v, 0]
    p["Roof"]["loc"] = [1.1 * v, -0.2 * v, -1.9 * v * v]
    s = 1 - 0.999 * u(t, 0.85, 1.05)
    p["Roof"]["scale"] = [s, s, s]
    # merlons tumble outward one after another
    for m, i in merlons:
        t0 = 0.1 + 0.07 * ((i * 3) % 8)
        x, y, _ = face(i, 0.6 + 0.25 * (i % 3))
        tumble(p[m.name], t, t0, 0.7, (x, y), 2.08, (rng_spin[i], 0, 40 * (i % 3 - 1)))
    # top ring drops and breaks up
    v = u(t, 0.45, 1.15)
    p["Top"]["loc"] = [0.1 * v, 0, -1.1 * v * v]
    p["Top"]["rot"] = [0, -25 * v, 0]
    s = 1 - 0.999 * u(t, 1.0, 1.25)
    p["Top"]["scale"] = [s, s, s]
    # facing stones blow out
    for c, i, z in chunks:
        k = int(c.name[5:])
        x, y, _ = face(i, 0.4 + 0.1 * (k % 3))
        tumble(p[c.name], t, 0.5 + 0.08 * k, 0.6, (x, y), z - 0.05, (300, 0, 90))
    # middle slumps into the ground
    v = u(t, 0.75, 1.6)
    p["Mid"]["scale"] = [1 + 0.1 * v, 1 + 0.1 * v, 1 - 0.85 * v]
    p["Mid"]["rot"] = [6 * v, -8 * v, 0]
    p["Mid"]["loc"] = [0, 0, -0.55 * v]
    s = 1 - 0.999 * u(t, 1.5, 1.7)
    p["Mid"]["scale"] = [x * s for x in p["Mid"]["scale"]]
    # the base cracks down to a stump
    v = u(t, 1.1, 1.8)
    p["Base"]["scale"] = [1, 1, 1 - 0.55 * v]
    p["Base"]["rot"] = [0, 4 * v, 0]
    # rubble heaps up
    for r, d in rubble:
        g = 1000 * u(t, 0.7 + 0.5 * d, 1.3 + 0.6 * d)
        p[r.name]["scale"] = [max(g, 1), max(g, 1), max(g, 1)]
    return p

rng_spin = [float(x) for x in rng.uniform(-250, 250, 8)]
record(J, "Collapse", collapse, 2.0)
export(NAME, J)
