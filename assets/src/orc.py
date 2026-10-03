"""Orc: a broad, hunched brute in mismatched blackened iron, crimson rag sash, notched iron cleaver-axe.
orc_warlord.py imports build() and clips() from here."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

SKIN = (0.28, 0.34, 0.20)
IRON = (0.16, 0.16, 0.17)
CRIMSON = (0.45, 0.06, 0.05)
BONE = (0.74, 0.69, 0.56)


def mats(name, seed):
    rng = new_rng(seed)
    t = save_textures(name, {
        "skin": tex_skin(rng, SKIN, warts=0.6, veins=0.3),
        "iron": tex_metal(rng, IRON, rust=0.7, grime=0.5),
        "cloth": paint_blood(rng, tex_cloth(rng, CRIMSON, wear=0.7), blood_mask(rng, 4) * 0.6),
        "leather": tex_leather(rng, (0.24, 0.16, 0.10)),
        "bone": tex_bone(rng, BONE),
        "wood": tex_wood(rng, (0.30, 0.20, 0.12)),
        "steel": tex_metal(rng, (0.42, 0.42, 0.44), rust=0.8, grime=0.4),
    })
    m = {k: material(name + k.title(), image=v, roughness=0.85 if k in ("skin", "cloth", "leather") else 0.5,
                     metallic=0.6 if k in ("iron", "steel") else 0.0) for k, v in t.items()}
    m["eye"] = material(name + "Eye", (1.0, 0.12, 0.05), emission=(1.0, 0.1, 0.03), strength=6.0)
    m["blood"] = material(name + "Blood", (0.22, 0.01, 0.01), roughness=0.3)
    m["brass"] = material(name + "Brass", (0.55, 0.40, 0.15), roughness=0.4, metallic=0.8)
    return m


def cleaver(m, parent, s, name="Axe"):
    """Notched heavy iron cleaver-axe. Haft runs along local -Y (the grip is at the origin)."""
    piece("cylinder", name + "Haft", size=(0.035 * s, 0.035 * s, 0.62 * s), at=(0, -0.2 * s, 0), turn=(90, 0, 0),
          mat=m["wood"], parent=parent, verts=6)
    piece("sphere", name + "Pommel", size=(0.06 * s,) * 3, at=(0, 0.11 * s, 0), mat=m["iron"], parent=parent, verts=6)
    # broad blade sticking outward (-X for the right hand), tapering to a wide edge, with a notch cut in it
    block(name + "Blade", (0.025 * s, 0.24 * s, 0.22 * s), at=(-0.12 * s, -0.40 * s, 0), mat=m["iron"],
          parent=parent, taper=(1, 0.7), taper_bottom=(1, 1.3), shape_turn=(0, 90, 0), bevel=0.006 * s)
    block(name + "Edge", (0.04 * s, 0.30 * s, 0.018 * s), at=(-0.245 * s, -0.42 * s, 0), mat=m["steel"],
          parent=parent, turn=(0, 0, 4), bevel=0.004 * s)
    block(name + "Notch", (0.06 * s, 0.035 * s, 0.03 * s), at=(-0.25 * s, -0.36 * s, 0), mat=m["blood"],
          parent=parent, bevel=0.0)
    piece("cone", name + "Spike", size=(0.05 * s, 0.05 * s, 0.12 * s), at=(0.05 * s, -0.42 * s, 0),
          turn=(0, 90, 0), mat=m["iron"], parent=parent, verts=5)


def build(name, s, m, warlord=False):
    """Body, head and armour common to both orcs. Returns joints (incl. Weapon, Severed, Blood)."""
    j = humanoid({"skin": m["skin"], "body": m["skin"], "legs": m["leather"], "feet": m["iron"]},
                 height=0.8 * s, hunch=0.25, girth=1.6, arm=1.15, leg=0.85, head=1.4)
    hd, jaw, chest, pel = j["Head"], j["Jaw"], j["Chest"], j["Pelvis"]
    h = 0.15 * 0.8 * s * 1.4
    # thick neck: a trapezius wedge
    piece("cylinder", "Traps", size=(0.22 * s, 0.14 * s, 0.10 * s), at=(0, 0.01 * s, 0.17 * s), mat=m["skin"],
          parent=chest, taper=(0.55, 0.7), verts=8)
    # sloped brow and heavy jaw with big lower tusks
    block("Brow", (h * 1.0, h * 0.35, h * 0.22), at=(0, -h * 0.42, h * 0.75), turn=(-25, 0, 0), mat=m["skin"],
          parent=hd, taper=(0.8, 0.6))
    block("Snout", (h * 0.45, h * 0.3, h * 0.28), at=(0, -h * 0.55, h * 0.5), mat=m["skin"], parent=hd,
          taper=(0.7, 0.8))
    block("JawHeavy", (h * 1.0, h * 0.75, h * 0.38), at=(0, -h * 0.28, -h * 0.05), mat=m["skin"], parent=jaw,
          taper=(1.1, 1.0), taper_bottom=(0.8, 0.8))
    for sd in (1, -1):
        piece("cone", "Tusk" + ("L" if sd > 0 else "R"), size=(h * 0.16, h * 0.16, h * (0.5 if sd > 0 else 0.38)),
              at=(sd * h * 0.34, -h * 0.58, h * 0.25), turn=(-12, sd * 14, 0), mat=m["bone"], parent=jaw, verts=6)
        piece("sphere", "Eye" + ("L" if sd > 0 else "R"), size=(h * 0.2, h * 0.08, h * 0.11),
              at=(sd * h * 0.22, -h * 0.5, h * 0.6), turn=(0, 0, sd * -12), mat=m["eye"], parent=hd, verts=6)
        piece("cone", "Ear" + ("L" if sd > 0 else "R"), size=(h * 0.18, h * 0.08, h * 0.45),
              at=(sd * h * 0.5, 0, h * 0.6), turn=(-20, sd * 75, 0), mat=m["skin"], parent=hd, verts=5)
    # armour: big spiked pauldron on the left shoulder, a mismatched chest plate, sash, ragged loincloth
    shL, shR = j["ShoulderL"], j["ShoulderR"]
    pa = 1.25 if warlord else 1.0
    piece("sphere", "PauldronL", size=(0.2 * s * pa, 0.2 * s * pa, 0.15 * s * pa), at=(0.02 * s, 0, 0.02 * s),
          turn=(0, -20, 0), mat=m["iron"], parent=shL, verts=8, squash_bottom=0.3, flat_shade=True)
    for k, (x, y) in enumerate(((0.03, -0.04), (0.06, 0.03), (0.0, 0.05))):
        piece("cone", f"SpikeL{k}", size=(0.04 * s * pa, 0.04 * s * pa, 0.12 * s * pa),
              at=(x * s * pa, y * s * pa, 0.08 * s * pa), turn=(y * 300, 30, 0), mat=m["steel"], parent=shL, verts=5)
    if warlord:
        piece("sphere", "PauldronR", size=(0.17 * s, 0.17 * s, 0.12 * s), at=(-0.02 * s, 0, 0.02 * s),
              turn=(0, 20, 0), mat=m["iron"], parent=shR, verts=8, squash_bottom=0.3, flat_shade=True)
        block("ChestPlate", (0.33 * s, 0.07 * s, 0.24 * s), at=(0, -0.11 * s, 0.1 * s), turn=(-6, 0, 0),
              mat=m["iron"], parent=chest, taper=(1.1, 1), taper_bottom=(0.8, 1))
        block("BellyPlate", (0.30 * s, 0.07 * s, 0.13 * s), at=(0, -0.11 * s, 0.07 * s), mat=m["iron"],
              parent=j["Spine"], taper=(1.05, 1))
        for sd in (1, -1):
            block("Tasset" + str(sd), (0.13 * s, 0.03 * s, 0.14 * s), at=(sd * 0.09 * s, -0.08 * s, -0.08 * s),
                  turn=(8, 0, sd * 4), mat=m["iron"], parent=pel)
    else:
        block("ChestPlate", (0.2 * s, 0.06 * s, 0.17 * s), at=(0.05 * s, -0.11 * s, 0.12 * s), turn=(-8, 0, -9),
              mat=m["iron"], parent=chest, taper=(1.1, 1))
        block("SidePlate", (0.12 * s, 0.05 * s, 0.10 * s), at=(-0.1 * s, -0.1 * s, 0.03 * s), turn=(-5, 0, 14),
              mat=m["iron"], parent=chest)
        for k, x in enumerate((0.0, 0.1)):
            piece("sphere", f"Rivet{k}", size=(0.025 * s,) * 3, at=(x * s, -0.145 * s, 0.17 * s), mat=m["brass"],
                  parent=chest, verts=5)
    piece("cylinder", "Belt", size=(0.33 * s, 0.25 * s, 0.06 * s), at=(0, 0, 0.03 * s), mat=m["cloth"],
          parent=pel, verts=8)
    for k, (x, ln, tw) in enumerate(((-0.07, 0.2, 6), (0.03, 0.25, -4), (0.1, 0.17, 10))):
        block(f"Rag{k}", (0.08 * s, 0.02 * s, ln * s), at=(x * s, -0.12 * s, -ln * s / 2), turn=(6, 0, tw),
              mat=m["cloth"], parent=pel, taper_bottom=(0.6, 1))
    block("RagTail", (0.06 * s, 0.03 * s, 0.22 * s), at=(-0.12 * s, 0.05 * s, -0.08 * s), turn=(0, 0, -8),
          mat=m["cloth"], parent=pel, taper_bottom=(0.5, 1))
    # crimson sash across the chest (from right hip over the left shoulder)
    block("SashF", (0.07 * s, 0.03 * s, 0.38 * s), at=(0.0, -0.125 * s, 0.09 * s), turn=(-6, 35, 0),
          mat=m["cloth"], parent=chest)
    block("BracerL", (0.07 * s, 0.07 * s, 0.09 * s), at=(0, 0, -0.07 * s), mat=m["iron"], parent=j["ElbowL"])
    block("GreaveR", (0.08 * s, 0.07 * s, 0.13 * s), at=(0, -0.01 * s, -0.08 * s), mat=m["iron"],
          parent=j["KneeR"], taper_bottom=(0.8, 0.8))
    # weapon in the right fist
    j["Weapon"] = pivot("Weapon", at=(0, 0, -0.045 * s), parent=j["WristR"])
    # gore for Die: blood pool and a severed arm on the ground, hidden until then
    j["Blood"] = bl = pivot("Blood", at=(0, 0.1 * s, 0.003), parent=j["Root"])
    for k, (x, y, r) in enumerate(((0, 0.15, 0.32), (-0.25, -0.08, 0.2), (0.15, 0.4, 0.14))):
        piece("cylinder", f"Pool{k}", size=(r * s, r * s * 0.8, 0.004), at=(x * s, y * s, 0.001 * k),
              mat=m["blood"], parent=bl, verts=9, jitter=0.0)
    bl.scale = (1e-3,) * 3
    j["Severed"] = sv = pivot("Severed", at=(-0.42 * s, -0.12 * s, 0.035 * s), turn=(0, 0, 25), parent=j["Root"])
    limb("SevArm", 0.3 * s, 0.05 * s, 0.035 * s, m["skin"], sv, at=(0, 0.33 * s, 0))
    sv.children[0].rotation_euler = (math.radians(-90), 0, 0)
    sv.scale = (1e-3,) * 3
    # ready stance: knees slightly bent, weapon arm forward
    j["ShoulderR"].rotation_euler = (math.radians(-15), math.radians(14), 0)
    j["ElbowR"].rotation_euler = (math.radians(-65), 0, 0)
    j["ShoulderL"].rotation_euler = (math.radians(-10), math.radians(-18), 0)
    j["ElbowL"].rotation_euler = (math.radians(-35), 0, 0)
    j["WristR"].rotation_euler = (math.radians(-15), 0, 0)
    return j


def clips(j, s, two_hand=False):
    hip_z = j["Pelvis"].location.z

    def idle(t):
        p = rest_pose(j)
        b = wave(t, 3.0)
        p["Chest"]["rot"][0] = 3 * b
        p["Spine"]["rot"][1] = 2 * wave(t, 3.0, 0.25)
        p["Pelvis"]["loc"][2] = -0.006 * s * (1 + b)
        p["Head"]["rot"][2] = 5 * wave(t, 3.0, 0.1)
        p["ShoulderL"]["rot"][1] = -3 * b
        p["ShoulderR"]["rot"][0] = 3 * b
        p["Jaw"]["rot"][0] = 4 + 4 * b
        return p

    def fidget1(t):  # sniff the air
        p = idle(t)
        u = keyed(t, [(0, 0), (0.5, 1), (2.4, 1), (3.0, 0)])
        p["Head"]["rot"][0] -= 25 * u
        p["Neck"]["rot"][0] -= 10 * u
        p["Head"]["rot"][2] += 18 * keyed(t, [(0, 0), (0.7, 0), (1.0, 1), (1.4, -1), (1.8, 0.5), (2.2, 0), (3, 0)])
        p["Head"]["rot"][0] += 5 * u * max(0, wave(t, 0.3))
        p["Chest"]["rot"][0] -= 6 * u
        return p

    def fidget2(t):  # look around
        p = idle(t)
        u = keyed(t, [(0, 0), (0.6, 1), (1.4, 1), (2.0, -1), (2.8, -1), (3.4, 0)])
        p["Chest"]["rot"][2] += 25 * u
        p["Head"]["rot"][2] += 30 * u
        p["Spine"]["rot"][2] += 8 * u
        return p

    def fidget3(t):  # heft the axe, look at the edge, test it with a thumb
        p = idle(t)
        u = keyed(t, [(0, 0), (0.6, 1), (2.6, 1), (3.2, 0)])
        p["ShoulderR"]["rot"][0] -= 35 * u
        p["ShoulderR"]["rot"][1] -= 20 * u
        p["ElbowR"]["rot"][0] -= 30 * u
        p["Weapon"]["rot"][1] = 360 * keyed(t, [(0, 0), (0.7, 0), (1.3, 1), (3.2, 1)])
        p["ShoulderL"]["rot"][0] -= 40 * keyed(t, [(0, 0), (1.4, 0), (1.8, 1), (2.4, 1), (2.8, 0), (3.2, 0)])
        p["ShoulderL"]["rot"][1] += 25 * keyed(t, [(0, 0), (1.4, 0), (1.8, 1), (2.4, 1), (2.8, 0), (3.2, 0)])
        p["Head"]["rot"][0] += 18 * u
        p["Head"]["rot"][2] -= 15 * u
        return p

    def walk(t):
        p = rest_pose(j)
        for sd, side in ((1, "L"), (-1, "R")):
            p["Hip" + side]["rot"][0] = -28 * sd * wave(t, 1.0)
            p["Knee" + side]["rot"][0] = 18 + 22 * wave(t, 1.0, 0.25 * sd)
            p["Ankle" + side]["rot"][0] = -10 * sd * wave(t, 1.0)
        p["ShoulderL"]["rot"][0] = 22 * wave(t, 1.0)
        p["ShoulderR"]["rot"][0] = -8 * wave(t, 1.0)
        p["Pelvis"]["loc"][2] = -0.025 * s * abs(wave(t, 1.0, 0.0)) - 0.01 * s
        p["Pelvis"]["rot"][1] = 5 * wave(t, 1.0)
        p["Chest"]["rot"][1] = -6 * wave(t, 1.0)
        p["Chest"]["rot"][0] = 6
        p["Head"]["rot"][1] = 4 * wave(t, 1.0)
        return p

    def attack(t):
        p = rest_pose(j)
        k = [(0, 0), (0.45, 1), (0.62, 2), (0.85, 2), (1.25, 0)]
        u = keyed(t, k)
        up, dn = min(u, 1), max(0, u - 1)
        if u > 1 or t > 0.62:
            up = keyed(t, [(0, 0), (0.45, 1), (0.62, 0), (1.25, 0)])
            dn = keyed(t, [(0.45, 0), (0.62, 1), (0.85, 1), (1.25, 0)])
        p["ShoulderR"]["rot"][0] = -135 * up - 35 * dn
        p["ShoulderR"]["rot"][1] = 10 * up
        p["ElbowR"]["rot"][0] = 35 * up + 45 * dn
        p["WristR"]["rot"][0] = 30 * up - 10 * dn
        p["Chest"]["rot"][0] = -12 * up + 25 * dn
        p["Spine"]["rot"][0] = -6 * up + 10 * dn
        p["Chest"]["rot"][2] = -15 * up + 10 * dn
        p["ShoulderL"]["rot"][0] = 20 * up - 20 * dn
        p["HipR"]["rot"][0] = 15 * up - 10 * dn
        p["HipL"]["rot"][0] = -25 * dn
        p["KneeL"]["rot"][0] = 25 * dn
        p["Pelvis"]["loc"][2] = -0.04 * s * dn
        p["Jaw"]["rot"][0] = 25 * dn
        if two_hand:
            p["ShoulderL"]["rot"][0] = -120 * up - 40 * dn
            p["ShoulderL"]["rot"][1] = 25 * (up + dn)
            p["ElbowL"]["rot"][0] = 20 * up + 20 * dn
        return p

    def hit(t):
        p = rest_pose(j)
        u = keyed(t, [(0, 0), (0.12, 1), (0.35, 0.8), (0.7, 0)])
        p["Chest"]["rot"][0] = -25 * u
        p["Spine"]["rot"][0] = -8 * u
        p["Head"]["rot"][0] = -22 * u
        p["Head"]["rot"][2] = 10 * u
        p["Pelvis"]["loc"][1] = 0.06 * s * u
        p["HipR"]["rot"][0] = 20 * u
        p["KneeR"]["rot"][0] = 15 * u
        p["HipL"]["rot"][0] = -10 * u
        p["ShoulderL"]["rot"][0] = -30 * u
        p["ShoulderL"]["rot"][1] = -25 * u
        p["ShoulderR"]["rot"][1] = 20 * u
        p["Jaw"]["rot"][0] = 20 * u
        return p

    def die(t):
        p = rest_pose(j)
        a = keyed(t, [(0, 0), (0.2, 1), (0.5, 1)])           # the blow
        b = keyed(t, [(0.35, 0), (0.95, 1)])                  # knees buckle
        c = keyed(t, [(0.9, 0), (1.5, 1), (2.0, 1)])          # fall back
        p["Chest"]["rot"][0] = -20 * a + 25 * b - 30 * c
        p["Head"]["rot"][0] = -25 * a + 30 * b - 35 * c
        p["Jaw"]["rot"][0] = 30 * a
        for side in "LR":
            p["Hip" + side]["rot"][0] = -55 * b + 50 * c
            p["Knee" + side]["rot"][0] = 80 * b - 55 * c
            p["Ankle" + side]["rot"][0] = -25 * b + 25 * c
        p["HipL"]["rot"][1] = 10 * c
        p["HipR"]["rot"][1] = -14 * c
        p["Pelvis"]["rot"][0] = -78 * c
        p["Pelvis"]["loc"][2] = -0.2 * s * b - (hip_z - 0.2 * s - 0.08 * s) * c
        p["Pelvis"]["loc"][1] = 0.04 * s * a + 0.1 * s * c
        p["ShoulderL"]["rot"][0] = -40 * a - 70 * c
        p["ShoulderL"]["rot"][1] = -40 * c
        gone = 1.0 if t >= 0.18 else 0.0
        p["ShoulderR"]["scale"] = [1 - gone * 0.999] * 3
        p["Severed"]["scale"] = [1 + gone * 999] * 3
        p["Blood"]["scale"] = [1 + 999 * keyed(t, [(0.18, 0.05), (2.0, 1)])] * 3
        return p

    def roar(t):
        p = rest_pose(j)
        u = keyed(t, [(0, 0), (0.35, 1), (1.15, 1), (1.5, 0)])
        sh = 3 * wave(t, 0.15) * u
        p["ShoulderR"]["rot"][0] = -110 * u
        p["ShoulderR"]["rot"][1] = 35 * u
        p["ElbowR"]["rot"][0] = 40 * u
        p["ShoulderL"]["rot"][0] = -120 * u
        p["ShoulderL"]["rot"][1] = -55 * u
        p["ElbowL"]["rot"][0] = -20 * u
        p["Chest"]["rot"][0] = -18 * u + sh
        p["Head"]["rot"][0] = -30 * u
        p["Neck"]["rot"][0] = -10 * u
        p["Jaw"]["rot"][0] = 35 * u
        return p

    record(j, "Idle", idle, 3.0)
    record(j, "Fidget1", fidget1, 3.0)
    record(j, "Fidget2", fidget2, 3.4)
    record(j, "Fidget3", fidget3, 3.2)
    record(j, "Walk", walk, 1.0)
    record(j, "Attack", attack, 1.25)
    record(j, "Hit", hit, 0.7)
    record(j, "Die", die, 2.0)
    record(j, "Roar", roar, 1.5)


def report(j):
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in bpy.context.scene.objects if o.type == "MESH"
          and o.name not in ("SevArm",) and not o.name.startswith(("Pool", "Sev"))
          for c in o.bound_box]
    print(f"height {max(zs):.3f}  min z {min(zs):.3f}")


if __name__ == "__main__":
    reset()
    S = 1.0
    m = mats("orc", 11)
    j = build("orc", S, m)
    cleaver(m, j["Weapon"], S * 1.2)
    cleaver(m, j["Severed"], S * 1.2, "SevAxe")
    report(j)
    clips(j, S)
    export("orc", j)
