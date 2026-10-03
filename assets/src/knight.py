"""Knight: worn steel plate, great helm, blue tabard with a gold cross, kite shield, longsword.
Also holds the shared defender helpers that hero.py imports."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

H = 0.8  # humanoid() height parameter (helm brings the top to ~0.9)


def dims(s=H, girth=1.0, head=1.0):
    return {"s": s, "w": 0.13 * s * girth, "h": 0.15 * s * head}


def set_rot(obj, deg):
    obj.rotation_euler = [math.radians(d) for d in deg]


def grip(name, joint, world_rot, offset=(0, 0, 0)):
    """A pivot at a wrist whose world orientation is world_rot (degrees) in the current pose: children are then
    built in a world-aligned frame (z up, -y forward)."""
    bpy.context.view_layer.update()
    p = pivot(name, parent=joint)
    bpy.context.view_layer.update()
    wm = joint.matrix_world
    loc = wm @ Vector(offset)
    rot = Euler([math.radians(d) for d in world_rot]).to_matrix().to_4x4()
    p.matrix_world = Matrix.Translation(loc) @ rot
    return p


def slab(name, size, **kw):
    """An unbevelled box (12 tris) for thin trim, hems and plates."""
    kw.setdefault("bevel", 0.0)
    return block(name, size, **kw)


def plate(j, m, d, steel, dark, trim=None, big_left=True):
    """Shared armour overlay: pauldrons, couters, knee cops, greaves, gorget."""
    s, w = d["s"], d["w"]
    for sd, side in ((1, "L"), (-1, "R")):
        sh = j["Shoulder" + side]
        k = 1.15 if (sd == 1) == big_left else 1.0
        piece("sphere", "Pauldron" + side, size=(0.14 * s * k, 0.13 * s * k, 0.09 * s * k), at=(sd * 0.01, 0, 0.012),
              turn=(0, sd * 18, 0), mat=steel, parent=sh, verts=8, taper_bottom=(1.1, 1.1), flat_shade=True)
        piece("sphere", "Lame" + side, size=(0.12 * s * k, 0.11 * s * k, 0.06 * s), at=(sd * 0.022, 0, -0.03),
              turn=(0, sd * 28, 0), mat=trim or dark, parent=sh, verts=8, flat_shade=True)
        piece("sphere", "Couter" + side, size=(0.06 * s,) * 3, at=(0, 0.01, 0), mat=steel,
              parent=j["Elbow" + side], verts=6, flat_shade=True)
        limb("Gauntlet" + side, 0.08 * s, 0.042 * s, 0.05 * s, steel, j["Elbow" + side], at=(0, 0, -0.09 * s),
             verts=7, flat_shade=True)
        piece("sphere", "Cop" + side, size=(0.07 * s, 0.06 * s, 0.07 * s), at=(0, -0.025 * s, 0), mat=steel,
              parent=j["Knee" + side], verts=6, flat_shade=True)
        limb("Greave" + side, 0.16 * s, 0.05 * s, 0.042 * s, steel, j["Knee" + side], at=(0, -0.004, -0.02 * s),
             verts=7, flat_shade=True)
        block("Sabaton" + side, (0.09 * s, 0.16 * s, 0.045 * s), at=(0, -0.045 * s, -0.012 * s), mat=steel,
              parent=j["Ankle" + side], taper=(0.85, 0.8))
    piece("cylinder", "Gorget", size=(0.13 * s, 0.12 * s, 0.05 * s), at=(0, 0, 0.19 * s), mat=steel,
          parent=j["Chest"], verts=8, taper=(0.75, 0.75), flat_shade=True)


def cape(j, m, d, length, width, segs=3, tilt=6):
    """A jointed cloth panel chain hanging from the back of the chest; returns its pivots (add them to joints)."""
    s, w = d["s"], d["w"]
    seg = length / segs
    parent = pivot("Cape1", at=(0, w * 0.95, 0.17 * s), turn=(tilt, 0, 0), parent=j["Chest"])
    out_ = [parent]
    rng = new_rng(5)
    for i in range(segs):
        wt = width * (1 + 0.12 * i)
        wb = width * (1 + 0.12 * (i + 1))
        block(f"CapePanel{i}", (wt, 0.018, seg * 1.04), at=(0, 0, -seg / 2), mat=m, parent=parent,
              taper_bottom=(wb / wt, 1), taper=(1, 1), bevel=0.004)
        if i == segs - 1:
            for k in range(4):
                x = (k - 1.5) / 4 * wb
                l = seg * rng.uniform(0.12, 0.35)
                slab(f"CapeHem{k}", (wb / 4.3, 0.016, l), at=(x, 0, -seg - l / 2 + 0.01), mat=m, parent=parent,
                      taper_bottom=(0.5, 1), bevel=0.003)
        else:
            nxt = pivot(f"Cape{i + 2}", at=(0, 0, -seg), turn=(4, 0, 0), parent=parent)
            out_.append(nxt)
            parent = nxt
    return out_


def defender_clips(j, two_handed=False, cape_joints=()):
    """Idle, Fidget1, Fidget2, Attack, Cheer: deltas from the built (armed) rest pose."""
    def capes(p, t, amp, period):
        for i, c in enumerate(cape_joints):
            p[c.name]["rot"][0] += amp * (1 + 0.5 * i) * wave(t, period, -0.12 * i)
            p[c.name]["rot"][1] += amp * 0.4 * wave(t, period * 2, 0.3 + 0.1 * i)

    def idle(t):
        p = rest_pose(j)
        b = wave(t, 3.0)
        p["Chest"]["rot"][0] = 2 * b
        p["Pelvis"]["loc"][2] = -0.003 * (1 + b)
        p["Head"]["rot"][2] = 4 * wave(t, 3.0, 0.2)
        p["ShoulderR"]["rot"][0] = -2 * b
        p["ShoulderL"]["rot"][0] = -2 * b
        capes(p, t, 3, 3.0)
        return p

    def fidget1(t):  # shift weight, roll the shoulders, settle the helm
        p = idle(t)
        u = keyed(t, [(0, 0), (0.6, 1), (2.2, 1), (3.0, 0)])
        r = keyed(t, [(0, 0), (0.8, 0), (1.2, 1), (1.6, -1), (2.0, 0)])
        p["Pelvis"]["loc"][0] = 0.02 * u
        p["Pelvis"]["rot"][1] = 4 * u
        p["Chest"]["rot"][1] = -6 * u
        p["HipL"]["rot"][1] = -4 * u
        p["HipR"]["rot"][1] = -4 * u
        p["KneeR"]["rot"][0] += 10 * u
        p["ShoulderL"]["loc"][2] = 0.012 * r
        p["ShoulderR"]["loc"][2] = -0.012 * r
        p["Neck"]["rot"][1] = 10 * r
        p["Head"]["rot"][0] = -6 * u
        return p

    def fidget2(t):  # bring the blade up and look along it
        p = idle(t)
        u = keyed(t, [(0, 0), (0.7, 1), (2.3, 1), (3.0, 0)])
        tilt = keyed(t, [(0, 0), (0.9, 0), (1.5, 1), (2.1, -1), (2.4, 0)])
        if two_handed:
            for sd in ("L", "R"):
                p["Shoulder" + sd]["rot"][0] -= 30 * u
                p["Elbow" + sd]["rot"][0] -= 25 * u
            p["Chest"]["rot"][2] = 12 * tilt
        else:
            p["ShoulderR"]["rot"][0] -= 25 * u
            p["ShoulderR"]["rot"][2] = 35 * u
            p["ElbowR"]["rot"][0] -= 30 * u
            p["WristR"]["rot"][1] = 25 * tilt
        p["Neck"]["rot"][2] = -12 * u
        p["Head"]["rot"][0] = 8 * u
        p["Head"]["rot"][2] = -10 * u
        return p

    def attack(t):
        p = rest_pose(j)
        wind = keyed(t, [(0, 0), (0.35, 1), (0.55, -1), (0.75, -1), (1.1, 0)])
        step = keyed(t, [(0, 0), (0.35, 0.3), (0.5, 1), (0.8, 1), (1.1, 0)])
        if two_handed:
            for sd in ("L", "R"):
                p["Shoulder" + sd]["rot"][0] = keyed(t, [(0, 0), (0.35, -110), (0.55, 25), (0.75, 25), (1.1, 0)])
                p["Elbow" + sd]["rot"][0] = keyed(t, [(0, 0), (0.35, -15), (0.55, 30), (0.75, 30), (1.1, 0)])
            p["Chest"]["rot"][0] = keyed(t, [(0, 0), (0.35, 10), (0.55, -18), (0.75, -18), (1.1, 0)])
        else:
            p["ShoulderR"]["rot"][0] = keyed(t, [(0, 0), (0.35, -125), (0.55, 20), (0.75, 20), (1.1, 0)])
            p["ShoulderR"]["rot"][2] = keyed(t, [(0, 0), (0.35, -20), (0.55, 25), (0.75, 25), (1.1, 0)])
            p["ElbowR"]["rot"][0] = keyed(t, [(0, 0), (0.35, -20), (0.55, 50), (0.75, 50), (1.1, 0)])
            p["ShoulderL"]["rot"][0] = -12 * step
            p["Chest"]["rot"][2] = 18 * wind
            p["Chest"]["rot"][0] = keyed(t, [(0, 0), (0.35, 6), (0.55, -12), (0.75, -12), (1.1, 0)])
        p["Pelvis"]["loc"][1] = -0.03 * step
        p["Pelvis"]["loc"][2] = -0.02 * step
        p["HipL"]["rot"][0] = -30 * step
        p["KneeL"]["rot"][0] = 30 * step
        p["HipR"]["rot"][0] = 15 * step
        p["KneeR"]["rot"][0] = 15 * step
        for i, c in enumerate(cape_joints):
            p[c.name]["rot"][0] = 18 * step * (1 + 0.4 * i)
        return p

    def cheer(t):
        p = rest_pose(j)
        u = keyed(t, [(0, 0), (0.35, 1), (1.1, 1), (1.5, 0)])
        pump = 0.5 + 0.5 * wave(t, 0.5) if 0.35 < t < 1.1 else 0
        p["ShoulderR"]["rot"][0] = -140 * u
        p["ShoulderR"]["rot"][1] = out(-1, 18) * u
        p["ElbowR"]["rot"][0] = 70 * u - 15 * pump * u
        p["WristR"]["rot"][0] = (40 if two_handed else 75) * u
        if two_handed:
            p["ShoulderL"]["rot"][0] = 25 * u
            p["ShoulderL"]["rot"][1] = out(1, 20) * u
            p["ElbowL"]["rot"][0] = 40 * u
        else:
            p["ShoulderL"]["rot"][1] = out(1, 15) * u
        p["Chest"]["rot"][0] = 8 * u
        p["Head"]["rot"][0] = 15 * u
        p["Pelvis"]["loc"][2] = 0.01 * pump * u
        for i, c in enumerate(cape_joints):
            p[c.name]["rot"][0] = (10 + 6 * pump) * u * (1 + 0.4 * i)
        return p

    record(j, "Idle", idle, 3.0)
    record(j, "Fidget1", fidget1, 3.0)
    record(j, "Fidget2", fidget2, 3.0)
    record(j, "Attack", attack, 1.1)
    record(j, "Cheer", cheer, 1.5)


def build_knight():
    reset()
    rng = new_rng(11)
    t = save_textures("knight", {
        "steel": tex_metal(rng, (0.55, 0.56, 0.60), rust=0.8, grime=0.55),
        "dark": tex_metal(rng, (0.30, 0.31, 0.34), rust=0.7, grime=0.7),
        "blue": tex_cloth(rng, (0.10, 0.16, 0.38), wear=0.7),
        "gold": tex_gold(rng, (0.78, 0.58, 0.2)),
        "leather": tex_leather(rng, (0.28, 0.17, 0.09)),
    })
    steel = material("Steel", image=t["steel"], roughness=0.4, metallic=0.4)
    dark = material("Mail", image=t["dark"], roughness=0.5, metallic=0.7)
    blue = material("Tabard", image=t["blue"], roughness=1.0)
    gold = material("Gold", image=t["gold"], roughness=0.4, metallic=0.5)
    leather = material("Leather", image=t["leather"], roughness=0.8)
    slit = flat("Slit", (0.01, 0.01, 0.012), roughness=1.0)
    d = dims(H, 1.12, 1.15)
    s, w, h = d["s"], d["w"], d["h"]
    j = humanoid({"skin": dark, "body": steel, "legs": dark, "feet": steel}, height=H, girth=1.12, head=1.15)

    # stance: feet apart, sword up, shield forward
    set_rot(j["HipL"], (0, -4, 0)); set_rot(j["HipR"], (0, 4, 0))
    set_rot(j["ShoulderR"], (-22, out(-1, 10), 0)); set_rot(j["ElbowR"], (-70, 0, 0))
    set_rot(j["ShoulderL"], (-30, out(1, 6), -10)); set_rot(j["ElbowL"], (-55, 0, 0))
    set_rot(j["Head"], (0, 4, 0))

    plate(j, None, d, steel, dark)
    # tabard over the torso, skirt panels front and back (a little taller than the Torso, so no faces share a plane)
    block("TabardTop", (w * 2.75, w * 1.85, 0.212 * s), at=(0, 0, 0.1 * s), mat=blue, parent=j["Chest"],
          taper=(1.12, 1.0), taper_bottom=(0.86, 0.92))
    block("TabardMid", (w * 2.15, w * 1.75, 0.17 * s), at=(0, 0, 0.08 * s), mat=blue, parent=j["Spine"],
          taper=(1.1, 1.05))
    block("Belt", (w * 2.25, w * 1.82, 0.035 * s), at=(0, 0, 0.0), mat=leather, parent=j["Spine"])
    slab("Buckle", (0.035 * s, 0.01, 0.03 * s), at=(0.02, -w * 0.92, 0.0), mat=gold, parent=j["Spine"])
    for y, nm in ((-1, "Front"), (1, "Back")):
        block("Skirt" + nm, (w * 1.9, 0.02, 0.2 * s), at=(0, y * w * 0.85, -0.1 * s), turn=(y * 6, 0, 0),
              mat=blue, parent=j["Pelvis"], taper_bottom=(1.15, 1))
        for k in range(4 if y < 0 else 0):
            l = 0.03 * s * (1 + rng.uniform(0, 1.2))
            slab(f"Hem{nm}{k}", (w * 0.42, 0.018, l), at=(w * 0.5 * (k - 1.5), y * (w * 0.85 + 0.012 * s),
                  -0.2 * s - l / 2), turn=(y * 6, 0, 0), mat=blue, parent=j["Pelvis"], taper_bottom=(0.6, 1))
    # gold cross on the chest
    slab("DevicePale", (0.035 * s, 0.012, 0.15 * s), at=(0, -w * 0.94, 0.1 * s), mat=gold, parent=j["Chest"])
    slab("DeviceFess", (0.12 * s, 0.012, 0.035 * s), at=(0, -w * 0.94, 0.13 * s), mat=gold, parent=j["Chest"])

    # great helm: a flat-topped faceted pot with a narrow eye slit
    hd = j["Head"]
    piece("cylinder", "Helm", size=(h * 1.3, h * 1.4, h * 1.25), at=(0, -0.004, h * 0.6), mat=steel, parent=hd,
          verts=8, taper=(0.9, 0.88), taper_bottom=(1.02, 1.04), bevel=0.004, flat_shade=True)
    piece("cylinder", "HelmTop", size=(h * 1.18, h * 1.24, h * 0.2), at=(0, 0, h * 1.3), mat=steel, parent=hd,
          verts=8, taper=(0.6, 0.6), flat_shade=True)
    block("EyeSlit", (h * 1.0, 0.02, h * 0.07), at=(0, -h * 0.68, h * 0.8), mat=slit, parent=hd, bevel=0.0)
    slab("HelmBrow", (h * 1.15, 0.02, h * 0.1), at=(0, -h * 0.67, h * 0.92), mat=steel, parent=hd)
    slab("HelmCross", (h * 0.12, 0.02, h * 0.55), at=(0, -h * 0.69, h * 0.45), mat=gold, parent=hd)

    # longsword
    wpn = grip("Weapon", j["WristR"], (-12, 0, 0), offset=(0, 0, -0.03 * s))
    piece("cylinder", "Grip", size=(0.028, 0.028, 0.1), at=(0, 0, 0.0), mat=leather, parent=wpn, verts=6)
    piece("sphere", "Pommel", size=(0.04, 0.04, 0.04), at=(0, 0, -0.06), mat=gold, parent=wpn, verts=6)
    slab("Guard", (0.17, 0.026, 0.026), at=(0, 0, 0.055), mat=gold, parent=wpn, taper=(1, 1))
    block("Blade", (0.05, 0.012, 0.48), at=(0, 0, 0.3), mat=steel, parent=wpn, taper=(0.35, 0.8), bevel=0.003)
    slab("Fuller", (0.012, 0.014, 0.32), at=(0, 0, 0.24), mat=dark, parent=wpn, bevel=0.0)

    # kite shield on the left forearm, facing forward
    sh = grip("Shield", j["WristL"], (0, 0, 8), offset=(0, 0, 0.02 * s))
    block("ShieldBack", (0.27, 0.03, 0.17), at=(0.02, -0.04, 0.03), mat=steel, parent=sh, taper_bottom=(1, 1),
          taper=(0.92, 1))
    block("ShieldPoint", (0.27, 0.03, 0.26), at=(0.02, -0.04, -0.185), mat=steel, parent=sh,
          taper_bottom=(0.06, 1))
    block("ShieldFace", (0.245, 0.02, 0.155), at=(0.02, -0.05, 0.035), mat=blue, parent=sh, taper=(0.92, 1),
          bevel=0.002)
    block("ShieldFaceP", (0.245, 0.02, 0.235), at=(0.02, -0.05, -0.17), mat=blue, parent=sh,
          taper_bottom=(0.06, 1), bevel=0.002)
    slab("ChargePale", (0.045, 0.02, 0.32), at=(0.02, -0.06, -0.06), mat=gold, parent=sh, taper_bottom=(0.5, 1))
    slab("ChargeFess", (0.22, 0.02, 0.045), at=(0.02, -0.06, 0.02), mat=gold, parent=sh)
    piece("sphere", "Boss", size=(0.06, 0.04, 0.06), at=(0.02, -0.07, 0.02), mat=steel, parent=sh, verts=6)

    defender_clips(j)
    export("knight", j)


if __name__ == "__main__":
    build_knight()
