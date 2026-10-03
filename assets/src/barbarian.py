import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

reset()
rng = new_rng(31)
SKIN = (0.62, 0.42, 0.30)
FUR = (0.38, 0.33, 0.28)


def tex_woad(rng):
    img = tex_skin(rng, SKIN, warts=0.15, grime=0.35)
    yy, xx = np.mgrid[0:N, 0:N]
    wob = noise(rng, 1.8) * 30
    band = np.sin((xx * 0.7 + yy + wob) * 2 * math.pi / 64)  # 4 diagonal stripes per tile
    m = smoothstep(0.55, 0.75, band) * (0.7 + 0.3 * noise(rng, 0.8))
    m *= smoothstep(0.25, 0.5, noise(rng, 1.2))  # broken, hand-daubed
    img = mix(img, [0.10, 0.20, 0.50], m * 0.9)
    img = mix(img, [0.95, 0.85, 0.7], scratches(rng, 25, (6, 18)) * 0.35)  # old scars
    return img


def tex_hair(rng):
    img = tex_fur(rng, (0.07, 0.06, 0.06))
    return mix(img, [0.2, 0.19, 0.2], noise(rng, 0.5, stretch=(10, 1)) ** 4 * 0.6)


t = save_textures("barbarian", {
    "skin": tex_woad(rng), "fur": tex_fur(rng, FUR), "wolf": tex_fur(rng, (0.56, 0.53, 0.49)),
    "hair": tex_hair(rng), "leather": tex_leather(rng, (0.30, 0.18, 0.10)),
    "iron": tex_metal(rng, (0.62, 0.62, 0.66), rust=0.8, grime=0.4), "wood": tex_wood(rng, (0.30, 0.20, 0.11)),
    "bone": tex_bone(rng)})
skin = material("Skin", image=t["skin"], roughness=0.7)
fur = material("Fur", image=t["fur"], roughness=1)
wolf = material("Wolf", image=t["wolf"], roughness=1)
hair = material("Hair", image=t["hair"], roughness=0.9)
leather = material("Leather", image=t["leather"], roughness=0.8)
iron = material("Iron", image=t["iron"], roughness=0.45, metallic=0.3)
wood = material("Wood", image=t["wood"], roughness=0.9)
bone = material("Bone", image=t["bone"], roughness=0.7)
dark = flat("Dark", (0.03, 0.02, 0.02), roughness=1)

j = humanoid({"skin": skin, "body": skin, "legs": skin, "feet": fur}, height=0.9, girth=1.35, head=1.1, arm=1.15)
S = 0.9

# --- muscle: pecs, biceps, traps
ch = j["Chest"]
for sd in (1, -1):
    piece("sphere", f"Pec{sd}", size=(0.15, 0.07, 0.11), at=(sd * 0.075, -0.1, 0.13), turn=(0, sd * 10, 0),
          mat=skin, parent=ch, verts=8)
    side = "L" if sd > 0 else "R"
    piece("sphere", "Bicep" + side, size=(0.075, 0.08, 0.11), at=(0, -0.01, -0.07), mat=skin,
          parent=j["Shoulder" + side], verts=7)
    piece("sphere", "Fist" + side, size=(0.065, 0.075, 0.07), at=(0, 0, -0.045), mat=skin,
          parent=j["Wrist" + side], verts=6)
    piece("sphere", "Trap" + side, size=(0.12, 0.12, 0.07), at=(sd * 0.09, 0.02, 0.19), mat=skin, parent=ch, verts=6)
piece("sphere", "Abs", size=(0.2, 0.06, 0.14), at=(0, -0.11, 0.07), mat=skin, parent=j["Spine"], verts=8)

# --- belt and fur loincloth
pel = j["Pelvis"]
piece("cylinder", "Belt", size=(0.36, 0.27, 0.06), at=(0, 0, 0.04), mat=leather, parent=pel, verts=10)
piece("cylinder", "Buckle", size=(0.06, 0.06, 0.02), at=(0, -0.14, 0.04), turn=(90, 0, 0), mat=iron, parent=pel,
      verts=6)
for i, (x, y, l, a) in enumerate([(0, -0.12, 0.2, 8), (0.1, -0.08, 0.15, 5), (-0.1, -0.08, 0.16, -4),
                                  (0, 0.12, 0.22, -8), (0.13, 0.04, 0.13, 0), (-0.13, 0.04, 0.14, 0)]):
    block(f"Loin{i}", (0.13, 0.04, l), at=(x, y, 0.02 - l / 2), turn=(a, 0, 0), mat=fur, parent=pel,
          taper_bottom=(0.6, 1), jitter=0.004, bevel=0)

# --- fur boots
for side in "LR":
    kn = j["Knee" + side]
    piece("cylinder", "Boot" + side, size=(0.11, 0.12, 0.13), at=(0, 0, -0.14), mat=fur, parent=kn, verts=7,
          taper=(1.15, 1.15), jitter=0.006)
    piece("cylinder", "BootCuff" + side, size=(0.13, 0.14, 0.03), at=(0, 0, -0.075), mat=fur, parent=kn, verts=7,
          jitter=0.008)
    piece("cylinder", "Wrap" + side, size=(0.085, 0.09, 0.02), at=(0, 0, -0.04), mat=leather, parent=kn, verts=6)
    piece("cylinder", "Bracer" + side, size=(0.065, 0.065, 0.07), at=(0, 0, -0.1), mat=leather,
          parent=j["Elbow" + side], verts=6)

# --- head: brow, eyes, jaw, wild black hair
hd = j["Head"]
h = 0.15 * S
block("Brow", (0.12, 0.04, 0.025), at=(0, -0.065, 0.1), turn=(-15, 0, 0), mat=skin, parent=hd)
for sd in (1, -1):
    block(f"Eye{sd}", (0.025, 0.01, 0.01), at=(sd * 0.028, -0.07, 0.085), mat=dark, parent=hd)
block("Nose", (0.025, 0.03, 0.04), at=(0, -0.078, 0.07), turn=(15, 0, 0), mat=skin, parent=hd)
block("Stubble", (0.11, 0.06, 0.05), at=(0, -0.03, -0.01), mat=hair, parent=j["Jaw"], taper_bottom=(0.7, 0.8))
piece("sphere", "HairCap", size=(0.16, 0.17, 0.12), at=(0, 0.012, 0.115), turn=(-10, 0, 0), mat=hair, parent=hd,
      verts=8, jitter=0.006)
hair_j = {}
for i, (x, y, l, a, b) in enumerate([(0, 0.07, 0.17, 12, 0), (0.06, 0.05, 0.15, 8, 15), (-0.06, 0.05, 0.16, 8, -15),
                                     (0.08, -0.02, 0.17, -8, 25), (-0.08, -0.02, 0.18, -8, -25)]):
    p1 = hair_j[f"HairA{i}"] = pivot(f"HairA{i}", at=(x, y, 0.13), turn=(a, b, 0), parent=hd)
    block(f"HairA{i}m", (0.07, 0.04, l * 0.55), at=(0, 0, -l * 0.27), mat=hair, parent=p1, taper_bottom=(0.8, 0.8),
          jitter=0.004, bevel=0)
    p2 = hair_j[f"HairB{i}"] = pivot(f"HairB{i}", at=(0, 0, -l * 0.55), turn=(8, 0, 0), parent=p1)
    block(f"HairB{i}m", (0.05, 0.03, l * 0.5), at=(0, 0, -l * 0.25), mat=hair, parent=p2, taper_bottom=(0.4, 0.6),
          jitter=0.004, bevel=0)

# --- wolf-pelt mantle: back pelt + collar, the wolf's head on the left shoulder
mant = hair_j["Mantle"] = pivot("Mantle", at=(0, 0.12, 0.2), parent=ch)
block("Pelt", (0.36, 0.05, 0.36), at=(0, 0.02, -0.17), turn=(6, 0, 0), mat=wolf, parent=mant,
      taper_bottom=(0.75, 1), jitter=0.008)
for i, x in enumerate((-0.13, -0.04, 0.05, 0.13)):
    block(f"PeltRag{i}", (0.07, 0.035, 0.08), at=(x, 0.05, -0.37 - 0.02 * (i % 2)), turn=(6, 0, (i - 1.5) * 8),
          mat=wolf, parent=mant, taper_bottom=(0.3, 1), bevel=0)
piece("torus", "Collar", size=(0.38, 0.3, 0.45), at=(0, -0.01, 0.2), mat=wolf, parent=ch, verts=10, jitter=0.006)
wh = pivot("WolfHead", at=(-0.18, -0.01, 0.26), turn=(0, -20, -8), parent=ch)
piece("sphere", "WolfSkull", size=(0.13, 0.15, 0.1), mat=wolf, parent=wh, verts=8, jitter=0.004)
piece("cone", "WolfSnout", size=(0.07, 0.07, 0.13), at=(0.0, -0.11, -0.01), turn=(90, 0, 0), mat=wolf, parent=wh,
      verts=6, taper=(1, 0.7))
block("WolfNose", (0.025, 0.02, 0.02), at=(0, -0.17, 0.0), mat=dark, parent=wh)
for sd in (1, -1):
    piece("cone", f"WolfEar{sd}", size=(0.045, 0.03, 0.07), at=(sd * 0.04, 0.0, 0.07), turn=(-10, sd * 15, 0),
          mat=wolf, parent=wh, verts=4)
    piece("cone", f"WolfFang{sd}", size=(0.012, 0.012, 0.035), at=(sd * 0.02, -0.15, -0.04), turn=(180, 0, 0),
          mat=bone, parent=wh, verts=4)
    block(f"WolfEye{sd}", (0.02, 0.01, 0.008), at=(sd * 0.035, -0.07, 0.03), mat=dark, parent=wh)
block("WolfPaw", (0.05, 0.04, 0.16), at=(-0.24, -0.06, 0.12), turn=(10, 0, -12), mat=wolf, parent=ch,
      taper_bottom=(0.6, 0.8))

# --- arms holding the axe two-handed (build pose)
def turn(name, x=0, y=0, z=0):
    j[name].rotation_euler = [math.radians(x), math.radians(y), math.radians(z)]


turn("HipL", -4, -6, 0); turn("HipR", 6, 6, 0)
bpy.context.view_layer.update()


def eul(x, y, z):
    return Euler((math.radians(x), math.radians(y), math.radians(z))).to_matrix().to_4x4()


def solve(side, target):
    """grid-search shoulder/elbow angles so the hand reaches target (a world point)."""
    sh, el, wr = j["Shoulder" + side], j["Elbow" + side], j["Wrist" + side]
    P = sh.parent.matrix_world @ Matrix.Translation(sh.location)
    Te, Tw = Matrix.Translation(el.location), Matrix.Translation(wr.location)
    best = None
    sgn = 1 if side == "L" else -1
    for sx in range(-100, 21, 8):
        for sy in range(-30, 31, 6):
            A = P @ eul(sx, sy * sgn, 0) @ Te
            for ex in range(-130, 1, 8):
                for ez in range(-40, 41, 10):
                    q = A @ eul(ex, 0, ez) @ Tw @ Vector((0, 0, -0.04))
                    d = (q - target).length
                    if best is None or d < best[0]:
                        best = (d, sx, sy * sgn, ex, ez)
    print("solve", side, best)
    turn("Shoulder" + side, best[1], best[2], 0)
    turn("Elbow" + side, best[3], 0, best[4])


AXIS = Vector((0.95, 0.25, 1.0)).normalized()  # haft: head up beside the left shoulder, right hand low
GRIP = Vector((-0.12, -0.15, 0.5))
solve("R", GRIP)
solve("L", GRIP + AXIS * 0.2)
bpy.context.view_layer.update()
gR = j["WristR"].matrix_world @ Vector((0, 0, -0.04))
gL = j["WristL"].matrix_world @ Vector((0, 0, -0.04))
print("grip err", (gR - GRIP).length, (gL - (GRIP + AXIS * 0.2)).length)
z = AXIS
x = Vector((0, 1, 0)).cross(z).normalized()
y = z.cross(x)
M = Matrix((x, y, z)).transposed().to_4x4()
M.translation = gR
weap = j["Weapon"] = pivot("Weapon", parent=j["WristR"])
weap.matrix_world = M
bpy.context.view_layer.update()

# the axe, haft along +Z: grip at 0, butt below, the double head above
piece("cylinder", "Haft", size=(0.03, 0.03, 0.9), at=(0, 0, 0.15), mat=wood, parent=weap, verts=6)
piece("cylinder", "Grip", size=(0.036, 0.036, 0.3), at=(0, 0, 0.06), mat=leather, parent=weap, verts=6)
piece("cone", "Spike", size=(0.04, 0.04, 0.08), at=(0, 0, 0.64), mat=iron, parent=weap, verts=4)
piece("cone", "Butt", size=(0.04, 0.04, 0.05), at=(0, 0, -0.32), turn=(180, 0, 0), mat=iron, parent=weap, verts=4)
block("Socket", (0.06, 0.05, 0.12), at=(0, 0, 0.53), mat=iron, parent=weap)
for sd in (1, -1):
    piece("cube", f"Bit{sd}", size=(0.13, 0.035, 0.19), at=(sd * 0.025, 0, 0.53), shape_at=(sd * 0.095, 0, 0),
          shape_turn=(0, sd * 90, 0), taper=(2.2, 0.25), taper_bottom=(0.9, 1), mat=iron, parent=weap, bevel=0.004)
for i in range(2):
    piece("cylinder", f"Lash{i}", size=(0.04, 0.04, 0.015), at=(0, 0, 0.42 - i * 0.025), mat=leather, parent=weap,
          verts=6)

J = dict(j); J.update(hair_j)


def base(t):
    p = rest_pose(J)
    br = wave(t, 3.0)
    p["Chest"]["rot"][0] = -2 * br
    p["Chest"]["scale"] = [1 + 0.015 * br, 1 + 0.015 * br, 1]
    p["Pelvis"]["loc"][2] = -0.004 + 0.004 * br
    for k in ("HipL", "HipR"):
        p[k]["rot"][0] += 0
    for i in range(5):
        p[f"HairA{i}"]["rot"][0] = 3 * wave(t, 3.0, 0.1 * i)
        p[f"HairB{i}"]["rot"][0] = 4 * wave(t, 3.0, 0.1 * i + 0.2)
    p["Mantle"]["rot"][0] = 2 * wave(t, 3.0, 0.3)
    return p


def arms(p, sx, ex=0, sy=0):
    for s in ("L", "R"):
        p["Shoulder" + s]["rot"][0] += sx
        p["Elbow" + s]["rot"][0] += ex
        p["Shoulder" + s]["rot"][2] += sy


def idle(t):
    p = base(t)
    arms(p, 3 * wave(t, 3.0, 0.25))
    p["Head"]["rot"][2] = 4 * wave(t, 3.0, 0.1)
    return p


def fidget1(t):  # roll the shoulders, shift weight
    p = base(t)
    u = keyed(t, [(0, 0), (0.6, 1), (2.2, 1), (3.0, 0)])
    roll = math.sin(2 * math.pi * min(t / 2.0, 1)) * u
    p["Chest"]["rot"][1] = 6 * roll
    p["Chest"]["rot"][2] = 8 * roll
    p["Neck"]["rot"][1] = -10 * roll
    p["Pelvis"]["loc"][0] = 0.02 * u * math.sin(math.pi * min(t / 3.0, 1))
    p["Pelvis"]["rot"][1] = 4 * u
    arms(p, -8 * u * abs(roll))
    return p


def fidget2(t):  # look at the blade, run a thumb along it
    p = base(t)
    u = keyed(t, [(0, 0), (0.7, 1), (2.3, 1), (3.0, 0)])
    arms(p, -20 * u, -15 * u)
    p["Chest"]["rot"][2] = 12 * u
    p["Head"]["rot"][2] = -25 * u
    p["Head"]["rot"][0] = -10 * u
    p["ElbowL"]["rot"][2] += 10 * u * wave(t, 0.8)
    return p


def attack(t):  # mighty overhead cleave
    p = base(0)
    k = [(0, 0), (0.35, 1), (0.48, 1.05), (0.62, -0.25), (0.85, -0.25), (1.2, 0)]
    a = keyed(t, k)
    up, down = max(a, 0), max(-a, 0)
    arms(p, -150 * up + 40 * down, -10 * up)
    p["Chest"]["rot"][0] = -14 * up + 28 * down
    p["Spine"]["rot"][0] = -6 * up + 14 * down
    p["Head"]["rot"][0] = -10 * up - 15 * down
    p["Jaw"]["rot"][0] = 12 * keyed(t, [(0, 0), (0.45, 0.3), (0.6, 1), (0.9, 1), (1.2, 0)])
    p["Pelvis"]["loc"][2] = -0.05 * down
    p["Pelvis"]["loc"][1] = -0.03 * down
    p["HipL"]["rot"][0] = -30 * down
    p["KneeL"]["rot"][0] = 35 * down
    p["HipR"]["rot"][0] = 20 * down
    p["KneeR"]["rot"][0] = 25 * down
    p["Weapon"]["rot"][0] = -15 * down
    for i in range(5):
        p[f"HairA{i}"]["rot"][0] = 25 * up - 20 * down
    p["Mantle"]["rot"][0] = 15 * down
    return p


def cheer(t):  # axe raised, roaring
    p = base(0)
    u = keyed(t, [(0, 0), (0.3, 1), (1.15, 1), (1.5, 0)])
    arms(p, -160 * u, 30 * u)
    p["ShoulderL"]["rot"][1] -= 15 * u
    p["ShoulderR"]["rot"][1] += 15 * u
    p["Chest"]["rot"][0] = -12 * u
    p["Head"]["rot"][0] = -25 * u
    p["Jaw"]["rot"][0] = 30 * u
    for i in range(5):
        p[f"HairA{i}"]["rot"][0] = 20 * u
    shake = 3 * u * math.sin(t * 40)
    p["ShoulderR"]["rot"][0] += shake
    p["ShoulderL"]["rot"][0] += shake
    return p


record(J, "Idle", idle, 3.0)
record(J, "Fidget1", fidget1, 3.0)
record(J, "Fidget2", fidget2, 3.0)
record(J, "Attack", attack, 1.2)
record(J, "Cheer", cheer, 1.5)
export("barbarian", J)
