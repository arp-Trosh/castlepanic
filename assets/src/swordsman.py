"""Swordsman defender: stocky man-at-arms in an oxblood gambeson, kettle helm, buckler and arming sword."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archer as A
from archer import aim, orient, reach, setp, cp, add, unwrap, blend, rod
from kit import *


def tex_gambeson(rng, color):
    img = tex_cloth(rng, color, wear=0.6)
    yy, xx = np.mgrid[0:N, 0:N]
    seam = ((xx % 22) < 2).astype(float) + 0.6 * ((yy % 44) < 2)
    img = mix(img, np.asarray(color) * 0.35, np.clip(blur(seam, 0.5), 0, 1) * 0.8)
    puff = 0.5 + 0.5 * np.cos((xx % 22) / 22 * 2 * math.pi)
    return img * (1.08 - 0.18 * puff)[..., None]


reset()
rng = new_rng(57)
t = save_textures("swordsman", {
    "gambeson": tex_gambeson(rng, (0.40, 0.10, 0.08)),
    "leather": tex_leather(rng, (0.30, 0.19, 0.11)),
    "dark": tex_leather(rng, (0.15, 0.10, 0.07)),
    "wool": tex_cloth(rng, (0.22, 0.20, 0.17)),
    "skin": tex_skin(rng, (0.58, 0.41, 0.32), warts=0.06, grime=0.6),
    "beard": tex_fur(rng, (0.20, 0.14, 0.10)),
    "steel": tex_metal(rng, (0.52, 0.53, 0.56), rust=0.78),
    "blade": tex_metal(rng, (0.70, 0.71, 0.74), rust=0.92, grime=0.35),
})
M = {k: material(k.title(), image=v, roughness=0.9) for k, v in t.items()}
M["steel"] = material("Steel", image=t["steel"], roughness=0.45, metallic=0.75)
M["blade"] = material("Blade", image=t["blade"], roughness=0.3, metallic=0.85)
dark = flat("Socket", (0.05, 0.035, 0.03), roughness=1)

s, g = 0.79, 1.18
j = A.body({"skin": M["gambeson"], "body": M["gambeson"], "legs": M["wool"], "feet": M["dark"]}, M["skin"], s, g,
           leg=0.94, head=1.05, arm=1.0)
HAND = A.HAND
w = 0.13 * s * g
h = 0.15 * s * 1.05
ch, hd, pel = j["Chest"], j["Head"], j["Pelvis"]

# face: brow, sunken eyes, broken nose, beard
block("Brow", (0.8 * h, 0.2 * h, 0.14 * h), at=(0, -0.47 * h, 0.7 * h), mat=M["skin"], parent=hd)
block("Eyes", (0.7 * h, 0.08 * h, 0.12 * h), at=(0, -0.5 * h, 0.56 * h), mat=dark, parent=hd)
piece("cone", "Nose", size=(0.2 * h, 0.22 * h, 0.32 * h), at=(0.02 * h, -0.57 * h, 0.44 * h), turn=(-15, 0, 6),
      mat=M["skin"], parent=hd, verts=4)
piece("sphere", "Beard", size=(0.82 * h, 0.5 * h, 0.55 * h), at=(0, -0.22 * h, -0.12 * h), mat=M["beard"],
      parent=j["Jaw"], verts=7, jitter=0.004, taper_bottom=(0.6, 0.7))
# kettle helm, tilted
helm = pivot("Helm", at=(0, 0.01 * h, 0.82 * h), turn=(-5, 4, 0), parent=hd)
piece("sphere", "Dome", size=(1.14 * h, 1.2 * h, 0.95 * h), mat=M["steel"], parent=helm, verts=9, taper_bottom=(1, 1))
piece("cylinder", "Brim", size=(2.0 * h, 2.05 * h, 0.16 * h), at=(0, 0, -0.08 * h), mat=M["steel"], parent=helm,
      verts=10, taper=(0.72, 0.72), bevel=0.003)
block("Comb", (0.07 * h, 1.0 * h, 0.12 * h), at=(0, 0, 0.44 * h), mat=M["steel"], parent=helm, taper=(1, 0.8))
# gambeson skirt, belt, scabbard, gloves
piece("cylinder", "Skirt", size=(w * 2.4, w * 1.8, 0.2 * s), at=(0, 0, -0.07 * s), mat=M["gambeson"], parent=pel,
      taper_bottom=(1.15, 1.12), verts=8)
block("Belt", (w * 2.3, w * 1.7, 0.032 * s), at=(0, 0, 0.055 * s), mat=M["dark"], parent=pel)
block("Buckle", (0.035, 0.01, 0.03), at=(0.02, -w * 0.86, 0.055 * s), mat=M["steel"], parent=pel)
block("Scabbard", (0.03, 0.02, 0.36), at=(w * 1.2, 0.02, -0.12), turn=(-28, 0, 4), mat=M["dark"], parent=pel)
for sd in "LR":
    piece("cylinder", "Cuff" + sd, size=(0.05, 0.05, 0.05), at=(0, 0, -0.11), mat=M["leather"],
          parent=j["Elbow" + sd], verts=6, taper_bottom=(0.85, 0.85))
    piece("sphere", "Pad" + sd, size=(0.11, 0.1, 0.07),
          at=(0, 0, 0.01), mat=M["gambeson"], parent=j["Shoulder" + sd], verts=7)

# arming sword: grip at the origin, blade along +Z, flat in local X
wp = j["Weapon"] = pivot("Weapon", at=(0, 0, -HAND), parent=j["WristR"])
rod("SGrip", (0, 0, -0.045), (0, 0, 0.045), 0.011, 0.011, M["dark"], wp)
piece("sphere", "Pommel", size=(0.03, 0.03, 0.035), at=(0, 0, -0.055), mat=M["steel"], parent=wp, verts=6)
block("Guard", (0.13, 0.022, 0.018), at=(0, 0, 0.05), mat=M["steel"], parent=wp, taper=(1, 1))
block("Blade", (0.04, 0.009, 0.36), at=(0, 0, 0.24), mat=M["blade"], parent=wp, taper=(0.55, 0.7), bevel=0.003)
piece("cone", "Tip", size=(0.022, 0.0063, 0.05), at=(0, 0, 0.445), mat=M["blade"], parent=wp, verts=4)
# round buckler: face along local -Y
sh = j["Shield"] = pivot("Shield", at=(0, 0, -HAND), parent=j["WristL"])
piece("cylinder", "Buckler", size=(0.21, 0.21, 0.025), at=(0, -0.035, 0), turn=(90, 0, 0), mat=M["steel"],
      parent=sh, verts=10, taper=(0.8, 0.8), bevel=0.004)
piece("torus", "Rim", size=(0.21, 0.21, 0.21), at=(0, -0.036, 0), turn=(90, 0, 0), mat=M["steel"], parent=sh, verts=10)
piece("sphere", "Boss", size=(0.07, 0.07, 0.07), at=(0, -0.05, 0), mat=M["steel"], parent=sh, verts=7,
      squash_bottom=0.3)

setp(j, rest_pose(j))


def hold(p, rhand, blade, lhand, face=(0.12, -1, 0.05), up=(0, 0, 1), pole_r=(-1, 0.3, -0.6), pole_l=(1, 0.3, -0.6),
         roll=(1, 0, 0)):
    """Put the sword hand and buckler hand at world points relative to the shoulders, aim blade and buckler."""
    setp(j, p)
    sr = j["ShoulderR"].matrix_world.translation.copy()
    sl = j["ShoulderL"].matrix_world.translation.copy()
    if rhand is not None:
        reach(j, p, "R", sr + Vector(rhand), pole_r)
        bl = Vector(blade)
        orient(j, p, "Weapon", bl, Vector(roll).cross(bl))
    if lhand is not None:
        reach(j, p, "L", sl + Vector(lhand), pole_l)
        orient(j, p, "Shield", Vector(up), Vector(face) * -1)
    return p


def stance(p, k=1.0):
    p["HipL"]["rot"] = [-12 * k, out(1, 5), 0]
    p["KneeL"]["rot"][0] = 14 * k
    p["AnkleL"]["rot"][0] = -2 * k
    p["HipR"]["rot"] = [10 * k, out(-1, 6), 0]
    p["KneeR"]["rot"][0] = 10 * k
    p["AnkleR"]["rot"][0] = -20 * k
    p["Pelvis"]["loc"][2] = -0.012 * k
    return p


R = stance(rest_pose(j))
R["Chest"]["rot"] = [4, 0, -8]
R["Head"]["rot"] = [3, 0, 8]
hold(R, (0.06, -0.15, -0.2), (0.15, -0.55, 0.8), (-0.05, -0.17, -0.14))
setp(j, R)


def idle(t):
    p = cp(R)
    add(p, "Chest", "rot", [1.5 * wave(t, 3.0), 0, 0])
    add(p, "Head", "rot", [0, 0, 6 * wave(t, 3.0, 0.1)])
    add(p, "WristR", "rot", [3 * wave(t, 1.5), 0, 0])
    add(p, "Pelvis", "loc", [0, 0, -0.003 * (1 - math.cos(2 * math.pi * t / 1.5))])
    return p


def fidget1(t):  # shift weight, roll the shoulders, crack the neck
    p = cp(R)
    k = keyed(t, [(0, 0), (0.6, 1), (2.2, 1), (3.0, 0)])
    add(p, "Pelvis", "loc", [-0.015 * k, 0, -0.003 * k])
    add(p, "Pelvis", "rot", [0, 4 * k, 0])
    add(p, "Chest", "rot", [0, -5 * k, 0])
    r = keyed(t, [(0, 0), (0.7, 0), (1.1, 1), (1.5, 0), (1.9, 1), (2.3, 0)])
    for sd in "LR":
        add(p, "Shoulder" + sd, "loc", [0, 0.01 * r, 0.014 * r])
    n = keyed(t, [(0, 0), (1.0, 0), (1.5, 1), (2.0, -1), (2.6, 0)])
    add(p, "Head", "rot", [0, 16 * n, 0])
    return p


# look at the blade
L1 = cp(R)
L1["Head"]["rot"] = [16, 0, -6]
L1["Chest"]["rot"] = [6, 0, -4]
hold(L1, (0.12, -0.2, 0.0), (0.05, -0.15, 1), None, roll=(0.3, -1, 0))
L2 = cp(L1)
hold(L2, (0.12, -0.2, 0.0), (0.05, -0.15, 1), None, roll=(1, 0.2, 0))
add(L2, "Head", "rot", [0, -8, 6])
f2keys = unwrap([(0, R), (0.6, L1), (1.4, L2), (2.2, L1), (3.0, R)])

# attack: wind up over the right shoulder, cut down across, return
W = stance(rest_pose(j), 1.0)
W["Spine"]["rot"] = [0, 0, -12]
W["Chest"]["rot"] = [-6, 0, -22]
W["Head"]["rot"] = [0, 0, 30]
hold(W, (-0.06, 0.05, 0.16), (-0.25, 0.6, 0.6), (0.0, -0.2, -0.08), roll=(0.3, -1, 0.2))
X = stance(rest_pose(j), 1.6)
X["Spine"]["rot"] = [10, 0, 14]
X["Chest"]["rot"] = [12, 0, 20]
X["Head"]["rot"] = [-10, 0, -26]
hold(X, (0.2, -0.24, -0.16), (0.4, -0.85, -0.2), (0.05, -0.08, -0.22), roll=(0.3, 1, 0))
X2 = cp(X)
add(X2, "Chest", "rot", [2, 0, 3])
akeys = unwrap([(0, R), (0.35, W), (0.47, W), (0.62, X), (0.8, X2), (1.2, R)])

# cheer: sword raised high
C = cp(R)
C["Chest"]["rot"] = [-6, 0, 0]
C["Head"]["rot"] = [-14, 0, 6]
hold(C, (-0.06, -0.04, 0.25), (-0.1, -0.15, 1), (0.08, -0.12, -0.05), roll=(1, 0, 0), pole_r=(-1, 0.4, 0))
C2 = cp(C)
add(C2, "ShoulderR", "loc", [0, 0, 0.014])
add(C2, "Chest", "rot", [-3, 0, 0])
ckeys = unwrap([(0, R), (0.35, C), (0.6, C2), (0.85, C), (1.1, C2), (1.5, R)])

record(j, "Idle", idle, 3.0)
record(j, "Fidget1", fidget1, 3.0)
record(j, "Fidget2", lambda t: blend(t, f2keys), 3.0)
record(j, "Attack", lambda t: blend(t, akeys), 1.2)
record(j, "Cheer", lambda t: blend(t, ckeys), 1.5)
export("swordsman", j, rest=R)
