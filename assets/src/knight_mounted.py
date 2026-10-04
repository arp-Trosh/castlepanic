"""Mounted Knight: the Castle Panic Knight on a barded dark-bay destrier, couching a polished chrome lance.
Reuses knight.py's helpers and look; the foot knight (knight.py) stays as it is."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from knight import dims, set_rot, grip, slab, plate, cape

H = 0.8
BODY_Z = 0.58


def hleg(J, side, front, parent, at, coat, hoof, dark):
    """A horse leg: Leg (shoulder/hip) -> Knee (knee/hock) -> Fet (fetlock). Returns nothing; fills J."""
    up, cn = 0.24, 0.22
    lg = J["Leg" + side] = pivot("Leg" + side, at=at, parent=parent)
    if front:
        piece("sphere", "Arm" + side, size=(0.11, 0.17, 0.2), at=(0, -0.01, -0.03), mat=coat, parent=lg, verts=5,
              flat_shade=True)
        limb("Forearm" + side, up, 0.05, 0.03, coat, lg, verts=7, flat_shade=True)
    else:
        piece("sphere", "Haunch" + side, size=(0.12, 0.22, 0.24), at=(0, 0.0, -0.04), mat=coat, parent=lg, verts=5,
              flat_shade=True)
        limb("Gaskin" + side, up, 0.055, 0.03, coat, lg, verts=7, flat_shade=True)
    kn = J["Knee" + side] = pivot("Knee" + side, at=(0, 0, -up), parent=lg)
    piece("sphere", "Joint" + side, size=(0.06, 0.07, 0.07), mat=dark, parent=kn, verts=5, flat_shade=True)
    limb("Cannon" + side, cn, 0.027, 0.024, dark, kn, verts=6, flat_shade=True)
    ft = J["Fet" + side] = pivot("Fet" + side, at=(0, 0, -cn), parent=kn)
    piece("sphere", "Fetlock" + side, size=(0.055, 0.065, 0.06), at=(0, 0.008, 0), mat=dark, parent=ft, verts=5,
          flat_shade=True)
    limb("Pastern" + side, 0.1, 0.026, 0.032, dark, ft, verts=6, flat_shade=True)
    piece("cylinder", "Hoof" + side, size=(0.075, 0.085, 0.06), at=(0, -0.008, -0.13), mat=hoof, parent=ft, verts=7,
          taper=(0.75, 0.7), flat_shade=True)


def merge_static(pivots):
    """Join the mesh parts hanging from each pivot into one object (fewer parts for the renderer)."""
    groups = {}
    for o in list(bpy.context.scene.objects):
        if o.type == "MESH" and o.parent in pivots and not o.children:
            groups.setdefault(o.parent.name, []).append(o)
    for name, objs in groups.items():
        if len(objs) < 2:
            continue
        with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs,
                                       selected_objects=objs):
            bpy.ops.object.join()
        objs[0].name = name + "Mesh"


def build():
    reset()
    rng = new_rng(23)
    t = save_textures("knight_mounted", {
        "steel": tex_metal(rng, (0.55, 0.56, 0.60), rust=0.8, grime=0.55),
        "dark": tex_metal(rng, (0.30, 0.31, 0.34), rust=0.7, grime=0.7),
        "blue": tex_cloth(rng, (0.13, 0.20, 0.45), wear=0.7),
        "gold": tex_gold(rng, (0.80, 0.60, 0.20)),
        "leather": tex_leather(rng, (0.26, 0.15, 0.08)),
        "coat": tex_skin(rng, (0.36, 0.20, 0.10), warts=0.0, grime=0.3),
        "legs": tex_skin(rng, (0.17, 0.10, 0.06), warts=0.0, grime=0.4),
        "mane": tex_fur(rng, (0.05, 0.045, 0.045)),
    })
    steel = material("Steel", image=t["steel"], roughness=0.4, metallic=0.4)
    dark = material("Mail", image=t["dark"], roughness=0.5, metallic=0.7)
    blue = material("Tabard", image=t["blue"], roughness=1.0)
    gold = material("Gold", image=t["gold"], roughness=0.4, metallic=0.5)
    leather = material("Leather", image=t["leather"], roughness=0.8)
    chrome = material("Chrome", (0.9, 0.92, 0.96), roughness=0.15, metallic=0.5, emission=(0.55, 0.58, 0.64), strength=0.35)
    coat = material("Coat", image=t["coat"], roughness=0.7)
    legc = material("Legs", image=t["legs"], roughness=0.7)
    mane = material("Mane", image=t["mane"], roughness=0.9)
    hoofm = flat("Hoof", (0.05, 0.045, 0.04), roughness=0.6)
    slit = flat("Slit", (0.01, 0.01, 0.012), roughness=1.0)

    # ------------------------------------------------------------------ horse
    J = {}
    hr = J["HorseRoot"] = pivot("HorseRoot")
    bd = J["Body"] = pivot("Body", at=(0, 0, BODY_Z), parent=hr)
    piece("cylinder", "Barrel", size=(0.29, 0.33, 0.64), shape_turn=(90, 0, 0), mat=coat, parent=bd, verts=6,
          taper=(1.0, 1.05), taper_bottom=(0.95, 0.95), flat_shade=True)
    piece("sphere", "Chest", size=(0.3, 0.3, 0.38), at=(0, -0.27, 0.02), mat=coat, parent=bd, verts=6,
          flat_shade=True)
    piece("sphere", "Rump", size=(0.31, 0.32, 0.33), at=(0, 0.27, 0.03), mat=coat, parent=bd, verts=6,
          flat_shade=True)
    for side, x, y, z, front in (("FL", 0.085, -0.25, 0.04, True), ("FR", -0.085, -0.25, 0.04, True),
                                 ("BL", 0.085, 0.27, 0.026, False), ("BR", -0.085, 0.27, 0.026, False)):
        hleg(J, side, front, bd, (x, y, z), coat, hoofm, legc)
        if not front:
            set_rot(J["Leg" + side], (14, 0, 0)); set_rot(J["Knee" + side], (-28, 0, 0))
            set_rot(J["Fet" + side], (14, 0, 0))

    # caparison: a blue cloth shell over the barrel, skirts with ragged gold-trimmed hems
    piece("cylinder", "Housing", size=(0.35, 0.37, 0.6), at=(0, 0.02, 0.01), shape_turn=(90, 0, 0), mat=blue,
          parent=bd, verts=7, taper=(1.06, 1.06), flat_shade=True)
    for sd, nm in ((1, "L"), (-1, "R")):
        block("Skirt" + nm, (0.016, 0.62, 0.2), at=(sd * 0.178, 0.02, -0.08), turn=(0, sd * -6, 0), mat=blue,
              parent=bd, bevel=0.004)
        slab("Trim" + nm, (0.02, 0.6, 0.022), at=(sd * 0.19, 0.02, -0.17), turn=(0, sd * -6, 0), mat=gold, parent=bd)
        for k in range(4):
            l = 0.03 + rng.uniform(0, 0.05)
            slab(f"Tab{nm}{k}", (0.014, 0.13, l), at=(sd * 0.19, -0.24 + k * 0.15, -0.18 - l / 2),
                 turn=(0, sd * -6, rng.uniform(-4, 4)), mat=blue, parent=bd, taper_bottom=(1, 0.55))
        slab("CrossP" + nm, (0.012, 0.035, 0.15), at=(sd * 0.191, 0.12, -0.04), turn=(0, sd * -6, 0), mat=gold,
             parent=bd)
        slab("CrossF" + nm, (0.012, 0.12, 0.035), at=(sd * 0.191, 0.12, -0.0), turn=(0, sd * -6, 0), mat=gold,
             parent=bd)
    block("Peytral", (0.3, 0.03, 0.17), at=(0, -0.4, -0.04), turn=(12, 0, 0), mat=blue, parent=bd,
          taper_bottom=(1.1, 1))
    slab("PeytralTrim", (0.31, 0.035, 0.02), at=(0, -0.41, -0.12), turn=(12, 0, 0), mat=gold, parent=bd)
    block("Crupper", (0.32, 0.18, 0.12), at=(0, 0.3, 0.13), mat=blue, parent=bd, taper=(0.8, 0.8))
    for k in range(3):
        l = 0.05 + rng.uniform(0, 0.06)
        slab(f"CrupHem{k}", (0.06, 0.014, l), at=(-0.09 + k * 0.09, 0.42, 0.08 - l / 2), turn=(-10, 0, 0),
             mat=blue, parent=bd, taper_bottom=(0.5, 1))

    # saddle
    block("Saddle", (0.2, 0.28, 0.05), at=(0, -0.01, 0.2), mat=leather, parent=bd)
    block("Cantle", (0.2, 0.04, 0.13), at=(0, 0.12, 0.26), turn=(-12, 0, 0), mat=leather, parent=bd,
          taper=(0.8, 1))
    block("Pommel", (0.12, 0.04, 0.08), at=(0, -0.14, 0.24), turn=(10, 0, 0), mat=leather, parent=bd)
    slab("CantleTrim", (0.17, 0.045, 0.02), at=(0, 0.13, 0.32), turn=(-12, 0, 0), mat=gold, parent=bd)

    # neck, head, mane
    nk = J["HorseNeck"] = pivot("HorseNeck", at=(0, -0.29, 0.08), turn=(34, 0, 0), parent=bd)
    piece("cylinder", "NeckPart", size=(0.15, 0.24, 0.5), shape_at=(0, 0.0, 0.23), mat=coat, parent=nk, verts=7,
          taper=(0.72, 0.6), flat_shade=True)
    for k in range(2):  # steel crinet lames on top of the neck
        slab(f"Crinet{k}", (0.12 - k * 0.01, 0.02, 0.09), at=(0, -0.06 + k * 0.003, 0.08 + k * 0.08),
             turn=(-8, 0, 0), mat=steel, parent=nk)
    for k in range(5):
        l = 0.08 + rng.uniform(0, 0.06)
        slab(f"Mane{k}", (0.04, 0.07, l * 1.5), at=(rng.uniform(-0.01, 0.025), 0.085 - k * 0.008, 0.04 + k * 0.08),
             turn=(-70 + rng.uniform(-12, 12), 0, rng.uniform(-10, 10)), mat=mane, parent=nk, taper=(0.6, 0.6))
    hh = J["HorseHead"] = pivot("HorseHead", at=(0, -0.01, 0.46), turn=(12, 0, 0), parent=nk)
    piece("cube", "Skull", size=(0.13, 0.16, 0.34), shape_turn=(90, 0, 0), shape_at=(0, -0.15, 0), taper=(0.68, 0.55), mat=coat,
          parent=hh, bevel=0.012, flat_shade=True)
    piece("sphere", "Jowl", size=(0.13, 0.15, 0.17), at=(0, 0.01, -0.02), mat=coat, parent=hh, verts=6,
          flat_shade=True)
    block("Chanfron", (0.12, 0.28, 0.03), at=(0, -0.13, 0.075), turn=(-5, 0, 0), mat=steel, parent=hh, taper=(1, 1),
          bevel=0.006)
    piece("cone", "Spike", size=(0.035, 0.035, 0.11), at=(0, -0.05, 0.1), turn=(-35, 0, 0), mat=steel, parent=hh,
          verts=5, flat_shade=True)
    slab("ChanfronTrim", (0.13, 0.04, 0.035), at=(0, 0.02, 0.07), mat=gold, parent=hh)
    for sd in (1, -1):
        piece("cone", f"Ear{sd}", size=(0.035, 0.03, 0.09), at=(sd * 0.04, 0.04, 0.09), turn=(-20, sd * 10, 0),
              mat=coat, parent=hh, verts=4, flat_shade=True)
        piece("sphere", f"Nostril{sd}", size=(0.03, 0.03, 0.025), at=(sd * 0.03, -0.33, 0.0), mat=slit,
              parent=hh, verts=5)
        piece("sphere", f"Eye{sd}", size=(0.02, 0.03, 0.02), at=(sd * 0.065, -0.06, 0.03), mat=slit, parent=hh,
              verts=5)
    for k in range(1):
        l = 0.09
        slab(f"Forelock{k}", (0.03, 0.02, l), at=(-0.02 + k * 0.02, -0.02, 0.07), turn=(-60, 0, 10 - 10 * k),
             mat=mane, parent=hh)

    tl = J["Tail"] = pivot("Tail", at=(0, 0.42, 0.1), turn=(34, 0, 0), parent=bd)
    limb("TailDock", 0.14, 0.04, 0.03, mane, tl, verts=6, flat_shade=True)
    for k in range(3):
        l = 0.3 + rng.uniform(0, 0.12)
        piece("cone", f"TailHair{k}", size=(0.06, 0.05, l), at=(-0.015 + k * 0.01, 0.0, -0.1),
              shape_at=(0, 0, -l / 2), shape_turn=(180, 0, 0), turn=(rng.uniform(-6, 6), rng.uniform(-8, 8), 0),
              mat=mane, parent=tl, verts=5, flat_shade=True)

    # ------------------------------------------------------------------ rider
    d = dims(H, 1.12, 1.15)
    s, w, h = d["s"], d["w"], d["h"]
    j = humanoid({"skin": dark, "body": steel, "legs": dark, "feet": steel}, height=H, girth=1.12, head=1.15)
    j["Root"].parent = bd
    j["Root"].location = (0, 0.0, 0.88 - 0.4 - BODY_Z)
    set_rot(j["Spine"], (6, 0, 0))
    for sd, side in ((1, "L"), (-1, "R")):
        set_rot(j["Hip" + side], (-62, out(sd, 34), 0))
        set_rot(j["Knee" + side], (80, 0, 0))
        set_rot(j["Ankle" + side], (-20, 0, 0))
    set_rot(j["ShoulderR"], (-8, out(-1, 14), 0)); set_rot(j["ElbowR"], (-78, 0, 0))
    set_rot(j["ShoulderL"], (-30, out(1, 10), 0)); set_rot(j["ElbowL"], (-60, 0, 0))
    set_rot(j["Head"], (0, 3, 0))
    plate(j, None, d, steel, dark)
    block("TabardTop", (w * 2.75, w * 1.85, 0.212 * s), at=(0, 0, 0.1 * s), mat=blue, parent=j["Chest"],
          taper=(1.12, 1.0), taper_bottom=(0.86, 0.92))
    block("TabardMid", (w * 2.15, w * 1.75, 0.17 * s), at=(0, 0, 0.08 * s), mat=blue, parent=j["Spine"],
          taper=(1.1, 1.05))
    block("Belt", (w * 2.25, w * 1.82, 0.035 * s), at=(0, 0, 0.0), mat=leather, parent=j["Spine"])
    for sd, nm in ((1, "L"), (-1, "R")):  # tabard skirts drape over the thighs
        block("Skirt" + nm + "R", (w * 0.9, w * 1.6, 0.03), at=(sd * w * 0.55, -0.05, -0.03), turn=(0, sd * -30, 0),
              mat=blue, parent=j["Pelvis"])
    slab("DevicePale", (0.035 * s, 0.012, 0.15 * s), at=(0, -w * 0.94, 0.1 * s), mat=gold, parent=j["Chest"])
    slab("DeviceFess", (0.12 * s, 0.012, 0.035 * s), at=(0, -w * 0.94, 0.13 * s), mat=gold, parent=j["Chest"])
    hd = j["Head"]
    piece("cylinder", "Helm", size=(h * 1.3, h * 1.4, h * 1.25), at=(0, -0.004, h * 0.6), mat=steel, parent=hd,
          verts=8, taper=(0.9, 0.88), taper_bottom=(1.02, 1.04), bevel=0.004, flat_shade=True)
    piece("cylinder", "HelmTop", size=(h * 1.18, h * 1.24, h * 0.2), at=(0, 0, h * 1.3), mat=steel, parent=hd,
          verts=8, taper=(0.6, 0.6), flat_shade=True)
    block("EyeSlit", (h * 1.0, 0.02, h * 0.07), at=(0, -h * 0.68, h * 0.8), mat=slit, parent=hd, bevel=0.0)
    slab("HelmBrow", (h * 1.15, 0.02, h * 0.1), at=(0, -h * 0.67, h * 0.92), mat=steel, parent=hd)
    slab("HelmCross", (h * 0.12, 0.02, h * 0.55), at=(0, -h * 0.69, h * 0.45), mat=gold, parent=hd)
    piece("cone", "Crest", size=(0.03, 0.12, 0.09), at=(0, 0.01, h * 1.45), mat=blue, parent=hd, verts=4,
          flat_shade=True)

    # stirrups under the feet
    bpy.context.view_layer.update()
    for side in ("L", "R"):
        a = bd.matrix_world.inverted() @ j["Ankle" + side].matrix_world.translation
        piece("torus", "Stirrup" + side, size=(0.07, 0.07, 0.07), at=(a.x, a.y - 0.03, a.z - 0.03),
              turn=(0, 90, 0), mat=steel, parent=bd, verts=4)
        top = 0.18
        slab("Leather" + side, (0.012, 0.02, top - a.z), at=(a.x * 0.92, a.y - 0.03, (top + a.z) / 2), mat=leather,
             parent=bd)

    # ------------------------------------------------------------------ lance (couched, -Y, a little down and in)
    LR = (9, 0, 7)
    wpn = grip("Weapon", j["WristR"], LR, offset=(0, 0, -0.03 * s))

    def ax(kind, name, y0, y1, r0, r1, mat, verts=8, **kw):  # a round part along -Y from y0 to y1 (y1 < y0)
        L = y0 - y1
        return piece(kind, name, size=(2 * r0, 2 * r0, L), shape_turn=(90, 0, 0), at=(0, (y0 + y1) / 2, 0),
                     taper=(r1 / r0, r1 / r0), mat=mat, parent=wpn, verts=verts, flat_shade=True, **kw)
    ax("cylinder", "LanceButt", 0.3, 0.05, 0.022, 0.03, chrome)
    ax("sphere", "ButtCap", 0.33, 0.27, 0.03, 0.03, gold, verts=6)
    ax("cylinder", "LanceGrip", 0.05, -0.08, 0.026, 0.026, leather, verts=6)
    ax("cone", "Vamplate", -0.02, -0.2, 0.13, 0.03, chrome, verts=8)
    ax("cylinder", "VampRim", -0.015, -0.035, 0.135, 0.135, gold, verts=8)
    ax("cylinder", "Shaft", -0.2, -1.0, 0.04, 0.02, chrome, verts=8)
    for k, y in enumerate((-0.36, -0.6, -0.84)):  # spiral fluting read as offset gold bands
        r = 0.04 - (0.02 * (-0.2 - y) / -0.8) * -1
        r = 0.04 + 0.02 * (y + 0.2) / 0.8
        piece("cylinder", f"Band{k}", size=(2 * r + 0.016, 2 * r + 0.016, 0.03), shape_turn=(90, 0, 0),
              at=(0, y, 0), turn=(0, 0, 0), mat=gold if k % 2 == 0 else steel, parent=wpn, verts=8,
              flat_shade=True)
    ax("cylinder", "TipCollar", -0.99, -1.03, 0.03, 0.03, gold)
    ax("cone", "Tip", -1.02, -1.18, 0.032, 0.002, chrome, verts=6)
    slab("Pennon", (0.008, 0.16, 0.08), at=(0, -0.92, 0.06), mat=blue, parent=wpn, taper=(1, 1))
    slab("PennonTail", (0.008, 0.08, 0.045), at=(0, -0.81, 0.045), mat=blue, parent=wpn, taper_bottom=(1, 0.4))
    slab("PennonCross", (0.01, 0.025, 0.07), at=(0, -0.93, 0.06), mat=gold, parent=wpn)
    bpy.context.view_layer.update()
    fwd_world = Euler([math.radians(a) for a in LR]).to_matrix() @ Vector((0, -1, 0))
    FWD = j["WristR"].matrix_world.to_3x3().normalized().inverted() @ fwd_world
    tip = wpn.matrix_world @ Vector((0, -1.18, 0))
    print("LANCE TIP world", tuple(round(c, 3) for c in tip))

    # kite shield on the left arm, angled out to the left
    sh = grip("Shield", j["WristL"], (0, 0, 35), offset=(0, 0, 0.02 * s))
    block("ShieldBack", (0.27, 0.03, 0.17), at=(0.02, -0.04, 0.03), mat=steel, parent=sh, taper=(0.92, 1))
    block("ShieldPoint", (0.27, 0.03, 0.26), at=(0.02, -0.04, -0.185), mat=steel, parent=sh, taper_bottom=(0.06, 1))
    block("ShieldFace", (0.245, 0.02, 0.155), at=(0.02, -0.05, 0.035), mat=blue, parent=sh, taper=(0.92, 1),
          bevel=0.002)
    block("ShieldFaceP", (0.245, 0.02, 0.235), at=(0.02, -0.05, -0.17), mat=blue, parent=sh,
          taper_bottom=(0.06, 1), bevel=0.002)
    slab("ChargePale", (0.045, 0.02, 0.32), at=(0.02, -0.06, -0.06), mat=gold, parent=sh, taper_bottom=(0.5, 1))
    slab("ChargeFess", (0.22, 0.02, 0.045), at=(0.02, -0.06, 0.02), mat=gold, parent=sh)

    J.update(j)
    for nm in ("Barrel", "Skull.001", "JawPart", "Torso", "Belly"):  # hidden under housing, helm, tabard
        bpy.data.objects.remove(bpy.data.objects[nm])
    merge_static(set(J.values()) | {wpn, sh})
    J["Weapon"] = wpn
    J["Shield"] = sh
    LEGS = ("FL", "FR", "BL", "BR")

    # ------------------------------------------------------------------ clips
    def base(t, period=3.0):
        p = rest_pose(J)
        b = wave(t, period)
        p["Body"]["loc"][2] = 0.004 * b
        p["Body"]["scale"] = [1 + 0.012 * b, 1, 1 + 0.008 * b]
        p["HorseNeck"]["rot"][0] = 2 * wave(t, period, 0.2)
        p["HorseHead"]["rot"][0] = 4 * wave(t, period / 2, 0.1)
        p["Tail"]["rot"][1] = 10 * wave(t, period)
        p["Tail"]["rot"][0] = 3 * wave(t, period / 2)
        p["Chest"]["rot"][0] = 1.5 * b
        p["Head"]["rot"][2] = 5 * wave(t, period, 0.3)
        return p

    def idle(t):
        p = base(t)
        u = max(0.0, wave(t, 3.0, 0.1)) ** 2  # rest a hind hoof
        p["KneeBR"]["rot"][0] -= 14 * u
        p["FetBR"]["rot"][0] += 18 * u
        p["LegBR"]["rot"][0] += 3 * u
        p["Body"]["rot"][1] = -1.5 * u
        return p

    def fidget1(t):  # paw the ground, toss the head; rider settles
        p = base(t)
        paw = keyed(t, [(0, 0), (0.4, 1), (0.7, 0.3), (1.0, 1), (1.3, 0.2), (1.6, 1), (1.9, 0)])
        p["LegFR"]["rot"][0] = -35 * paw
        p["KneeFR"]["rot"][0] = 80 * paw
        p["FetFR"]["rot"][0] = 20 * paw
        toss = keyed(t, [(0, 0), (1.9, 0), (2.2, 1), (2.45, -0.6), (2.7, 0.3), (3.0, 0)])
        p["HorseNeck"]["rot"][0] -= 14 * toss
        p["HorseHead"]["rot"][0] -= 18 * toss
        p["HorseHead"]["rot"][1] = 10 * toss
        sett = keyed(t, [(0, 0), (0.5, 0), (0.9, 1), (1.4, -0.3), (1.8, 0)])
        p["Root"]["loc"][2] = 0.015 * sett
        p["Spine"]["rot"][1] = 4 * sett
        p["Neck"]["rot"][2] = 8 * keyed(t, [(0, 0), (2.0, 0), (2.3, 1), (2.8, 0)])
        return p

    def fidget2(t):  # raise the lance upright, look along it, lower; horse shakes its mane
        p = base(t)
        u = keyed(t, [(0, 0), (0.8, 1), (2.1, 1), (2.9, 0)])
        p["Weapon"]["rot"][0] = -75 * u
        p["ElbowR"]["rot"][0] = -15 * u
        p["ShoulderR"]["rot"][0] = -10 * u
        p["Neck"]["rot"][2] = 14 * u
        p["Head"]["rot"][0] = 14 * u
        sh_ = keyed(t, [(0, 0), (1.2, 0), (1.35, 1), (1.5, -1), (1.65, 1), (1.8, -1), (1.95, 0)])
        p["HorseNeck"]["rot"][1] = 6 * sh_
        p["HorseHead"]["rot"][1] = 14 * sh_
        return p

    def walk(t):  # gallop in place, 0.6 s stride
        T = 0.6
        p = rest_pose(J)
        ph = {"BL": 0.0, "BR": 0.1, "FL": 0.45, "FR": 0.55}
        for lg in LEGS:
            a = 2 * math.pi * (t / T - ph[lg])
            sw, vel = math.sin(a), math.cos(a)
            if lg[0] == "F":
                p["Leg" + lg]["rot"][0] = -32 * sw
                p["Knee" + lg]["rot"][0] = 75 * max(0.0, vel) ** 1.5
                p["Fet" + lg]["rot"][0] = 30 * max(0.0, vel) - 10 * max(0.0, -vel)
            else:
                p["Leg" + lg]["rot"][0] = -30 * sw
                p["Knee" + lg]["rot"][0] = -45 * max(0.0, vel) ** 1.5
                p["Fet" + lg]["rot"][0] = 35 * max(0.0, vel)
        p["Body"]["rot"][0] = 6 * wave(t, T, 0.1)
        p["Body"]["loc"][2] = 0.03 * wave(t, T, 0.35)
        p["HorseNeck"]["rot"][0] = -8 * wave(t, T, 0.15)
        p["HorseHead"]["rot"][0] = 6 * wave(t, T, 0.3)
        p["Tail"]["rot"][0] = 45 + 8 * wave(t, T / 2)
        p["Tail"]["rot"][1] = 6 * wave(t, T)
        r = wave(t, T, 0.6)
        p["Root"]["loc"][2] = 0.02 + 0.02 * r
        p["Spine"]["rot"][0] = 4 - 4 * r
        p["Knee" + "L"]["rot"][0] = -8 * r
        p["Knee" + "R"]["rot"][0] = -8 * r
        p["Body"]["loc"][2] -= 0.0
        p["Weapon"]["rot"][0] = 2 * wave(t, T, 0.4)
        # frame 0 must be rest: ease the gallop in over nothing (loop) -> keep offsets periodic, Tail/Root offsets
        # are constant, so blend them in only via the loop itself
        return p

    def attack(t):
        p = rest_pose(J)
        lunge = keyed(t, [(0, 0), (0.3, 0.4), (0.45, 1), (0.6, 1), (1.1, 0)])
        drive = keyed(t, [(0, 0), (0.25, -0.3), (0.45, 1), (0.6, 1), (1.1, 0)])
        p["Body"]["loc"][1] = -0.1 * lunge
        p["Body"]["loc"][2] = -0.03 * lunge
        p["Body"]["rot"][0] = 6 * lunge
        for lg in ("FL", "FR"):
            p["Leg" + lg]["rot"][0] = -28 * lunge
            p["Knee" + lg]["rot"][0] = 10 * lunge
        for lg in ("BL", "BR"):
            p["Leg" + lg]["rot"][0] = 18 * lunge
            p["Knee" + lg]["rot"][0] = 10 * lunge
        p["HorseNeck"]["rot"][0] = 12 * lunge
        p["HorseHead"]["rot"][0] = -10 * lunge
        p["Tail"]["rot"][0] = 30 * lunge
        p["Spine"]["rot"][0] = 8 * drive
        p["Chest"]["rot"][0] = 3 * drive
        p["Weapon"]["rot"][0] = -14 * lunge
        p["ShoulderR"]["rot"][0] = -10 * drive
        p["Weapon"]["loc"] = [c * 0.07 * drive for c in FWD]
        return p

    def cheer(t):  # rear up, lance to the sky
        p = rest_pose(J)
        u = keyed(t, [(0, 0), (0.45, 1), (1.0, 1), (1.5, 0)])
        th = -38 * u
        r = math.radians(th)
        yh = 0.27
        p["Body"]["rot"][0] = th
        p["Body"]["loc"][1] = yh - yh * math.cos(r)
        p["Body"]["loc"][2] = -yh * math.sin(r) - 0.02 * u
        for lg in ("BL", "BR"):
            p["Leg" + lg]["rot"][0] = -th - 14 * u
            p["Knee" + lg]["rot"][0] = 28 * u * 0.5
            p["Fet" + lg]["rot"][0] = -10 * u
        kick = 0.5 + 0.5 * wave(t, 0.35) if 0.45 < t < 1.0 else 0.5
        for k, lg in enumerate(("FL", "FR")):
            p["Leg" + lg]["rot"][0] = (-30 - 25 * (kick if k else 1 - kick)) * u
            p["Knee" + lg]["rot"][0] = 95 * u
            p["Fet" + lg]["rot"][0] = 30 * u
        p["HorseNeck"]["rot"][0] = 10 * u
        p["HorseHead"]["rot"][0] = -15 * u
        p["Tail"]["rot"][0] = -20 * u
        p["Spine"]["rot"][0] = 30 * u  # rider leans in to stay on
        p["ShoulderR"]["rot"][0] = -95 * u
        p["ElbowR"]["rot"][0] = 50 * u
        p["Weapon"]["rot"][0] = -55 * u
        p["Head"]["rot"][0] = -12 * u
        return p

    record(J, "Idle", idle, 3.0)
    record(J, "Fidget1", fidget1, 3.0)
    record(J, "Fidget2", fidget2, 3.0)
    record(J, "Walk", walk, 0.6)
    record(J, "Attack", attack, 1.1)
    record(J, "Cheer", cheer, 1.5)
    _probe = J  # tip at full Attack extension
    from kit import _apply
    _apply(J, attack(0.5)); bpy.context.view_layer.update()
    _apply(J, attack(0.5)); bpy.context.view_layer.update()
    print("LANCE TIP attack", tuple(round(c, 3) for c in wpn.matrix_world @ Vector((0, -1.18, 0))))
    print("PARTS", sum(1 for o in bpy.context.scene.objects if o.type == "MESH"))
    export("knight_mounted", J)


if __name__ == "__main__":
    build()
