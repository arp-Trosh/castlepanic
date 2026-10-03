import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

# The monsters' Healer boss: a hunched gaunt goblinoid shaman, bone mask with horns, charm-hung staff, amber flask.
reset()
rng = new_rng(31)
SKIN = (0.40, 0.38, 0.42)
t = save_textures("healer", {
    "skin": tex_skin(rng, (0.48, 0.45, 0.52), warts=0.4, veins=0.4, grime=0.3),
    "leather": tex_leather(rng, (0.42, 0.29, 0.17)),
    "rags": tex_cloth(rng, (0.34, 0.24, 0.16), wear=0.6),
    "feather": tex_fur(rng, (0.20, 0.17, 0.19)),
    "bone": tex_bone(rng),
    "wood": tex_wood(rng, (0.30, 0.22, 0.14)),
    "brass": tex_gold(rng, (0.55, 0.42, 0.18)),
})
M = {k: material(k.title(), image=t[k], roughness=0.85) for k in ("skin", "leather", "rags", "feather", "bone", "wood")}
M["brass"] = material("Brass", image=t["brass"], roughness=0.4, metallic=0.7)
GLOW = material("Glow", (1.0, 0.62, 0.15), emission=(1.0, 0.55, 0.1), strength=4.0)
EYE = material("Eye", (1.0, 0.7, 0.2), emission=(1.0, 0.6, 0.1), strength=6.0)
GLASS = material("Glass", (0.35, 0.22, 0.08), roughness=0.2, emission=(0.8, 0.4, 0.05), strength=1.2)
BLOOD = material("Blood", (0.22, 0.02, 0.02), roughness=0.3)

S = 0.98
j = humanoid({"skin": M["skin"], "body": M["leather"], "legs": M["rags"], "feet": M["skin"]},
             height=S, hunch=0.5, girth=0.82, arm=1.18, head=1.25, leg=0.95)
h = 0.15 * S * 1.25

# ---- bone mask with horns, glowing eyes
hd = j["Head"]
piece("sphere", "Mask", size=(h * 1.1, h * 0.5, h * 1.3), at=(0, -h * 0.45, h * 0.55), mat=M["bone"], parent=hd,
      verts=8, taper=(0.9, 1), taper_bottom=(0.6, 0.8), flat_shade=True)
piece("cone", "Snout", size=(h * 0.35, h * 0.35, h * 0.45), at=(0, -h * 0.68, h * 0.35), turn=(80, 0, 0),
      mat=M["bone"], parent=hd, verts=5, flat_shade=True)
for sd in (1, -1):
    piece("sphere", "Eye" + ("L" if sd > 0 else "R"), size=(h * 0.16, h * 0.08, h * 0.11),
          at=(sd * h * 0.2, -h * 0.66, h * 0.66), mat=EYE, parent=hd, verts=6)
    hb = pivot("HornBase" + ("L" if sd > 0 else "R"), at=(sd * h * 0.32, -h * 0.25, h * 1.0),
               turn=(30, sd * 60, 0), parent=hd)
    piece("cone", "Horn" + ("L" if sd > 0 else "R"), size=(h * 0.3, h * 0.3, h * 0.9), at=(0, 0, h * 0.42),
          mat=M["bone"], parent=hb, verts=6)
    piece("cone", "HornTip" + ("L" if sd > 0 else "R"), size=(h * 0.16, h * 0.16, h * 0.55), at=(0, h * 0.18, h * 1.0),
          turn=(40, 0, 0), mat=M["bone"], parent=hb, verts=6)
    piece("cone", "Ear" + ("L" if sd > 0 else "R"), size=(h * 0.2, h * 0.08, h * 0.5), at=(sd * h * 0.55, 0, h * 0.6),
          turn=(0, sd * 70, 0), mat=M["skin"], parent=hd, verts=4)
# feather tuft at the crown
for i, a in enumerate((-30, -10, 12, 28)):
    piece("cone", f"Plume{i}", size=(0.03, 0.012, 0.16 + 0.03 * (i % 2)), at=(a * 0.002, h * 0.15, h * 1.0),
          turn=(-30 + i * 6, a, 0), shape_at=(0, 0, 0.08), mat=M["feather"], parent=hd, verts=4)

# ---- feathered mantle on the shoulders, tattered leather skirt
ch = j["Chest"]
w = 0.13 * S * 0.82
piece("cone", "Mantle", size=(w * 4.2, w * 3.2, 0.2), at=(0, 0.01, 0.17 * S), mat=M["feather"], parent=ch,
      verts=9, taper=(0.35, 0.4), jitter=0.006, flat_shade=True)
for i in range(11):
    a = math.radians(-150 + i * 30)
    x, y = math.sin(a) * w * 1.6, -math.cos(a) * w * 1.25
    if y < -w * 1.0:
        continue  # leave the front open
    piece("cone", f"Feather{i}", size=(0.045, 0.02, 0.15 + 0.04 * (i % 3)), at=(x, y + 0.01, 0.13 * S),
          turn=(180 + math.degrees(-math.cos(a)) * 0.2, math.degrees(math.sin(a)) * 0.25, 0), mat=M["feather"],
          parent=ch, verts=4, flat_shade=True)
pv = j["Pelvis"]
for i in range(9):
    a = math.radians(i * 40)
    x, y = math.sin(a) * w * 1.15, -math.cos(a) * w * 0.8
    block(f"Rag{i}", (0.07, 0.02, 0.13 + 0.05 * ((i * 7) % 3)), at=(x, y, -0.06 - 0.02 * ((i * 5) % 3)),
          turn=(math.cos(a) * 10, -math.sin(a) * 10, math.degrees(-a)), mat=M["rags"], parent=pv)
piece("cylinder", "Robe", size=(w * 2.7, w * 2.1, 0.3), at=(0, 0, -0.08), mat=M["leather"], parent=pv,
      verts=8, taper=(0.8, 0.8), taper_bottom=(1.15, 1.2), jitter=0.006, flat_shade=True)
block("Belt", (w * 2.4, w * 1.7, 0.035), at=(0, 0, 0.05), mat=M["leather"], parent=pv)
piece("cylinder", "Pouch", size=(0.06, 0.05, 0.07), at=(w * 1.1, -w * 0.5, 0.0), mat=M["leather"], parent=pv, verts=6)

# ---- crooked staff hung with charms (right hand)
wr = j["WristR"]
wp = j["Weapon"] = pivot("Weapon", at=(0, 0, -0.04), turn=(95, 0, 0), parent=wr)
L = 0.9
sr = pivot("StaffRoot", at=(0, 0, -0.18), parent=wp)
piece("cylinder", "StaffLow", size=(0.035, 0.035, L * 0.55), at=(0, 0, -L * 0.2), turn=(0, 4, 0), mat=M["wood"],
      parent=sr, verts=6, jitter=0.002)
piece("cylinder", "StaffHigh", size=(0.03, 0.03, L * 0.45), at=(0.012, 0, L * 0.25), turn=(0, -8, 3), mat=M["wood"],
      parent=sr, verts=6, jitter=0.002)
piece("cylinder", "StaffHook", size=(0.025, 0.025, 0.16), at=(-0.03, 0, L * 0.5), turn=(0, -60, 0), mat=M["wood"],
      parent=sr, verts=6)
piece("sphere", "StaffSkull", size=(0.08, 0.08, 0.07), at=(0.02, 0, L * 0.48), mat=M["bone"], parent=sr, verts=6)
piece("torus", "StaffRing", size=(0.08, 0.08, 0.3), at=(0.01, 0, L * 0.38), mat=M["brass"], parent=sr, verts=8)
for i, (dx, dz, ln) in enumerate(((-0.06, 0.40, 0.10), (0.05, 0.42, 0.14), (-0.02, 0.36, 0.17))):
    piece("cylinder", f"Cord{i}", size=(0.006, 0.006, ln), at=(dx, 0, L * dz - ln / 2), mat=M["leather"], parent=sr,
          verts=4)
    kind = ("cone", "ico", "cube")[i]
    piece(kind, f"Charm{i}", size=(0.035, 0.035, 0.05), at=(dx, 0, L * dz - ln - 0.02),
          mat=(M["bone"], M["brass"], M["feather"])[i], parent=sr, verts=None if kind == "cube" else (5 if kind == "cone" else 1))

# ---- glowing amber potion flask (left hand)
wl = j["WristL"]
of = j["Offhand"] = pivot("Offhand", at=(0, -0.01, -0.06), turn=(-70, 0, 0), parent=wl)
piece("sphere", "Flask", size=(0.1, 0.1, 0.11), at=(0, 0, 0.0), mat=GLASS, parent=of, verts=8)
piece("cylinder", "FlaskNeck", size=(0.035, 0.035, 0.06), at=(0, 0, 0.07), mat=GLASS, parent=of, verts=6)
piece("cylinder", "Cork", size=(0.04, 0.04, 0.025), at=(0, 0, 0.105), mat=M["brass"], parent=of, verts=6)
gl = j["Glow"] = pivot("Glow", parent=of)
piece("ico", "FlaskGlow", size=(0.085, 0.085, 0.09), at=(0, 0, -0.005), mat=GLOW, parent=gl, verts=1)

# ---- blood pool for Die
bl = j["Blood"] = pivot("Blood", at=(0, 0.25, 0.003))
piece("cylinder", "BloodPool", size=(0.5, 0.36, 0.004), mat=BLOOD, parent=bl, verts=10)


# ======================================================================== clips
def base(t, br=2.0):
    p = rest_pose(j)
    b = wave(t, br)
    p["Spine"]["rot"][0] = -20
    p["Chest"]["rot"][0] = -18 + 2.5 * b
    p["Neck"]["rot"][0] = 34 - 1.5 * b
    p["ShoulderR"]["rot"] = [-10, out(-1, 8), 0]
    p["ElbowR"]["rot"] = [-28, 0, 0]
    p["ShoulderL"]["rot"] = [5, out(1, 15), 0]
    p["ElbowL"]["rot"] = [-60, 0, 0]
    p["KneeL"]["rot"][0] = p["KneeR"]["rot"][0] = 14
    p["HipL"]["rot"][0] = p["HipR"]["rot"][0] = -10
    p["AnkleL"]["rot"][0] = p["AnkleR"]["rot"][0] = -4
    p["Root"]["loc"][2] = -0.02
    p["Blood"]["scale"] = [0.001] * 3
    return p


def idle(t):
    p = base(t)
    p["Pelvis"]["rot"][1] = 2 * wave(t, 4.0)
    p["Glow"]["scale"] = [1 + 0.12 * wave(t, 1.0)] * 3
    return p


def fidget1(t):  # sniff the potion
    p = base(t)
    k = keyed(t, [(0, 0), (0.6, 1), (2.0, 1), (2.6, 0), (3.0, 0)])
    p["ShoulderL"]["rot"][0] += -25 * k
    p["ElbowL"]["rot"][0] += -35 * k
    p["Neck"]["rot"][0] += 18 * k + 4 * k * wave(t, 0.5)
    p["Neck"]["rot"][2] += -12 * k
    p["Glow"]["scale"] = [1 + 0.25 * k * (0.5 + 0.5 * wave(t, 0.4))] * 3
    return p


def fidget2(t):  # look around
    p = base(t)
    yaw = keyed(t, [(0, 0), (0.7, 35), (1.3, 35), (2.1, -35), (2.6, -35), (3.0, 0)])
    p["Neck"]["rot"][2] += yaw * 0.6
    p["Chest"]["rot"][2] += yaw * 0.35
    return p


def fidget3(t):  # heft and shake the staff, rattling the charms
    p = base(t)
    k = keyed(t, [(0, 0), (0.5, 1), (2.2, 1), (2.8, 0), (3.0, 0)])
    p["ShoulderR"]["rot"][0] += -25 * k
    p["Weapon"]["rot"][1] += 10 * k * wave(t, 0.3)
    p["Weapon"]["loc"][2] += 0.02 * k * wave(t, 0.3)
    p["Neck"]["rot"][2] += -15 * k
    return p


def walk(t):
    p = base(t, 1.0)
    for s, side in ((1, "L"), (-1, "R")):
        p["Hip" + side]["rot"][0] += 26 * s * wave(t, 1.0)
        p["Knee" + side]["rot"][0] += 20 + 20 * wave(t, 1.0, 0.25 * s)
    p["Weapon"]["rot"][0] += -12 * wave(t, 1.0)
    p["ShoulderR"]["rot"][0] += -10 * wave(t, 1.0)
    p["ShoulderL"]["rot"][0] += 8 * wave(t, 1.0)
    p["Root"]["loc"][2] += -0.015 * abs(wave(t, 1.0))
    p["Pelvis"]["rot"][1] = 4 * wave(t, 1.0)
    p["Chest"]["rot"][0] += 4
    return p


def attack(t):  # raise the flask high, flare, hurl it forward
    p = base(t)
    up = keyed(t, [(0, 0), (0.45, 1), (0.6, 1), (0.8, 0), (1.3, 0)])
    th = keyed(t, [(0, 0), (0.55, 0), (0.75, 1), (0.95, 1), (1.3, 0)])
    p["ShoulderL"]["rot"][0] += -140 * up - 70 * th
    p["ElbowL"]["rot"][0] += 40 * up + 30 * th
    p["Chest"]["rot"][0] += 10 * up - 25 * th
    p["Chest"]["rot"][2] += -15 * up + 10 * th
    p["Neck"]["rot"][0] += -15 * up + 10 * th
    p["ShoulderR"]["rot"][0] += -10 * th
    flare = keyed(t, [(0, 1), (0.45, 2.2), (0.75, 2.8), (1.0, 1.6), (1.3, 1)])
    p["Glow"]["scale"] = [flare] * 3
    p["HipL"]["rot"][0] += -15 * th
    p["KneeL"]["rot"][0] += 10 * th
    return p


def hit(t):
    p = base(t)
    k = keyed(t, [(0, 0), (0.12, 1), (0.35, 0.8), (0.7, 0)])
    p["Chest"]["rot"][0] += 22 * k
    p["Neck"]["rot"][0] += -20 * k
    p["Root"]["loc"][1] += 0.06 * k
    p["ShoulderL"]["rot"][0] += 25 * k
    p["ShoulderR"]["rot"][1] += out(-1, 20) * k
    p["HipR"]["rot"][0] += 15 * k
    return p


def die(t):
    p = base(t)
    kb = keyed(t, [(0, 0), (0.5, 1), (1.8, 1)])
    fall = keyed(t, [(0, 0), (0.4, 0), (1.1, 1), (1.8, 1)])
    p["KneeL"]["rot"][0] += 60 * kb
    p["KneeR"]["rot"][0] += 60 * kb
    p["HipL"]["rot"][0] += -50 * kb * (1 - fall)
    p["HipR"]["rot"][0] += -50 * kb * (1 - fall)
    p["Root"]["loc"][2] += -0.1 * kb - 0.05 * fall
    p["Root"]["rot"][0] = -84 * fall
    p["Root"]["loc"][1] += 0.08 * fall
    p["Root"]["loc"][2] += 0.12 * fall
    p["ShoulderL"]["rot"][0] = lerp(-20, -150, fall)
    p["ShoulderR"]["rot"][0] = lerp(-28, -120, fall)
    p["ElbowL"]["rot"][0] = lerp(-60, -10, fall)
    p["Weapon"]["rot"][0] += 40 * fall
    p["Glow"]["scale"] = [max(0.001, 1 - fall)] * 3
    b = keyed(t, [(0, 0.001), (1.0, 0.001), (1.8, 1.0)])
    p["Blood"]["scale"] = [b, b, 1]
    return p


def roar(t):
    p = base(t)
    k = keyed(t, [(0, 0), (0.4, 1), (1.1, 1), (1.5, 0)])
    p["ShoulderL"]["rot"][0] += -130 * k
    p["ShoulderR"]["rot"][0] += -110 * k
    p["ElbowL"]["rot"][0] += 50 * k
    p["Chest"]["rot"][0] += 18 * k
    p["Neck"]["rot"][0] += -30 * k + 4 * k * wave(t, 0.25)
    p["Jaw"]["rot"][0] = 25 * k
    p["Glow"]["scale"] = [1 + 1.0 * k] * 3
    return p


record(j, "Idle", idle, 2.0)
record(j, "Fidget1", fidget1, 3.0)
record(j, "Fidget2", fidget2, 3.0)
record(j, "Fidget3", fidget3, 3.0)
record(j, "Walk", walk, 1.0)
record(j, "Attack", attack, 1.3)
record(j, "Hit", hit, 0.7)
record(j, "Die", die, 1.8)
record(j, "Roar", roar, 1.5)
export("healer", j, rest=idle(0))
