"""Archer defender: lean hooded longbowman. Also holds the helpers the swordsman imports (world-space aiming of
limbs and held items, pose blending)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy
import kit
from kit import *

HAND = 0.03


# ---------------------------------------------------------------------------------------------- pose helpers
def upd():
    bpy.context.view_layer.update()


def setp(j, p):
    kit._apply(j, p)
    upd()


def cp(p):
    return copy.deepcopy(p)


def hand_pos(j, side):
    return j["Wrist" + side].matrix_world @ Vector((0, 0, -HAND))


def _rot(pose, n, m3):
    e = m3.to_euler("XYZ")
    pose[n]["rot"] = [math.degrees(a - r) for a, r in zip(e, kit._REST[n][1])]


def aim(j, pose, n, wdir, axis=(0, 0, -1)):
    """Turn joint n so its local `axis` points along the world direction wdir."""
    setp(j, pose)
    pm = j[n].parent.matrix_world.to_3x3().normalized()
    local = pm.inverted() @ Vector(wdir).normalized()
    _rot(pose, n, Vector(axis).rotation_difference(local).to_matrix())


def orient(j, pose, n, zdir, yhint, pos=None):
    """Turn (and optionally move) joint n so its local Z points along zdir, local Y toward yhint (world)."""
    setp(j, pose)
    pm = j[n].parent.matrix_world
    z = Vector(zdir).normalized()
    x = Vector(yhint).cross(z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed()
    _rot(pose, n, pm.to_3x3().normalized().inverted() @ m)
    if pos is not None:
        loc = pm.inverted() @ Vector(pos)
        pose[n]["loc"] = list(loc - kit._REST[n][0])


def reach(j, pose, side, target, pole):
    """Two-bone arm: put the hand centre on world `target`, elbow bending toward `pole`."""
    setp(j, pose)
    s = j["Shoulder" + side].matrix_world.translation.copy()
    a = -kit._REST["Elbow" + side][0].z
    b = -kit._REST["Wrist" + side][0].z + HAND
    t = Vector(target)
    d = t - s
    dist = min(max(d.length, 1e-3), a + b - 1e-4)
    u = d.normalized()
    x = (a * a - b * b + dist * dist) / (2 * dist)
    h = math.sqrt(max(a * a - x * x, 0.0))
    p = Vector(pole)
    p = (p - u * p.dot(u)).normalized()
    e = s + u * x + p * h
    aim(j, pose, "Shoulder" + side, e - s)
    aim(j, pose, "Elbow" + side, t - e)


def add(p, n, ch, vals):
    p[n][ch] = [a + b for a, b in zip(p[n][ch], vals)]
    return p


def unwrap(keys):
    for (_, prev), (_, cur) in zip(keys, keys[1:]):
        for n in cur:
            r = cur[n]["rot"]
            for i in range(3):
                while r[i] - prev[n]["rot"][i] > 180:
                    r[i] -= 360
                while r[i] - prev[n]["rot"][i] < -180:
                    r[i] += 360
    return keys


def blend(t, keys):
    out_ = {}
    for n in keys[0][1]:
        out_[n] = {ch: keyed(t, [(tt, p[n][ch]) for tt, p in keys]) for ch in ("rot", "loc", "scale")}
    return out_


def body(m, skin, height, girth, leg=1.0, head=1.0, arm=1.0):
    """kit.humanoid with sleeves (m["skin"]) and real skin on the head and hands."""
    global HAND
    j = humanoid(m, height=height, girth=girth, leg=leg, head=head, arm=arm)
    for nm in ("Skull", "JawPart", "NeckPart", "HandL", "HandR"):
        bpy.data.objects[nm].data.materials[0] = skin
    HAND = 0.035 * height
    return j


def rod(name, p0, p1, r0, r1, mat, parent, verts=6):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    e = Vector((0, 0, 1)).rotation_difference(d).to_euler("XYZ")
    return piece("cylinder", name, size=(2 * r0, 2 * r0, d.length), at=tuple((p0 + p1) / 2),
                 turn=[math.degrees(a) for a in e], taper=(r1 / r0, r1 / r0), mat=mat, parent=parent, verts=verts)


# ---------------------------------------------------------------------------------------------- the archer
def build():
    reset()
    rng = new_rng(31)
    t = save_textures("archer", {
        "cloak": tex_cloth(rng, (0.22, 0.36, 0.19), wear=0.3),
        "leather": tex_leather(rng, (0.44, 0.27, 0.14)),
        "dark": tex_leather(rng, (0.17, 0.11, 0.07)),
        "linen": tex_cloth(rng, (0.60, 0.55, 0.45), wear=0.5),
        "wool": tex_cloth(rng, (0.21, 0.19, 0.16)),
        "skin": tex_skin(rng, (0.56, 0.42, 0.33), warts=0.05, grime=0.5),
        "yew": tex_wood(rng, (0.72, 0.47, 0.22)),
        "steel": tex_metal(rng, (0.58, 0.59, 0.62), rust=0.85),
        "feather": tex_bone(rng, (0.80, 0.77, 0.70)),
    })
    M = {k: material(k.title(), image=v, roughness=0.9) for k, v in t.items()}
    M["steel"] = material("Steel", image=t["steel"], roughness=0.4, metallic=0.7)
    shadow = flat("Shadow", (0.025, 0.022, 0.02), roughness=1)
    string = flat("String", (0.70, 0.66, 0.55), roughness=1)
    s = 0.79
    j = body({"skin": M["linen"], "body": M["leather"], "legs": M["wool"], "feet": M["dark"]}, M["skin"], s, 0.9,
             leg=1.03, arm=1.05)
    w = 0.13 * s * 0.9
    h = 0.15 * s
    ch, hd, pel = j["Chest"], j["Head"], j["Pelvis"]

    # hood, face in shadow, liripipe tail
    piece("sphere", "Hood", size=(1.28 * h, 1.36 * h, 1.32 * h), at=(0, 0.05 * h, 0.6 * h), mat=M["cloak"], parent=hd,
          verts=8, jitter=0.01)
    piece("sphere", "FaceShadow", size=(0.82 * h, 0.2 * h, 0.8 * h), at=(0, -0.6 * h, 0.48 * h), mat=shadow,
          parent=hd, verts=8)
    block("HoodBrow", (1.05 * h, 0.45 * h, 0.16 * h), at=(0, -0.42 * h, 1.02 * h), turn=(-18, 0, 0), mat=M["cloak"],
          parent=hd, taper=(0.8, 1))
    piece("cone", "HoodTail", size=(0.55 * h, 0.5 * h, 0.9 * h), at=(0, 0.6 * h, 0.75 * h), turn=(-125, 0, 0),
          mat=M["cloak"], parent=hd, verts=6)
    # mantle and cloak with a ragged hem
    piece("cylinder", "Mantle", size=(w * 3.8, w * 2.5, 0.1 * s), at=(0, 0.01, 0.145 * s), mat=M["cloak"],
          parent=ch, taper=(0.42, 0.5), verts=8, jitter=0.004)
    cl = block("Cloak", (0.29, 0.025, 0.5), at=(0, 0.1, 0.15 * s - 0.25), turn=(7, 0, 0), mat=M["cloak"], parent=ch,
               taper=(0.75, 1), bevel=0.006)
    for sd in (1, -1):
        block(f"CloakSide{sd}", (0.1, 0.022, 0.44), at=(sd * 0.182, -0.032, 0.02), turn=(0, 0, -sd * 40), mat=M["cloak"],
              parent=cl, taper=(0.5, 1), bevel=0.005)
    for i, (x, ln, tl) in enumerate(((-0.11, 0.07, 6), (-0.04, 0.04, -4), (0.03, 0.08, 3), (0.1, 0.05, -7))):
        block(f"Rag{i}", (0.07, 0.022, ln), at=(x, 0.002, -0.25 - ln / 2 + 0.01), turn=(0, tl, 0), mat=M["cloak"],
              parent=cl, taper=(1, 1), taper_bottom=(0.5, 1), bevel=0.004)
    # quiver
    q = piece("cylinder", "Quiver", size=(0.075, 0.075, 0.3), at=(-0.045, 0.145, 0.03), turn=(14, -24, 0),
              mat=M["dark"], parent=ch, verts=8, taper=(1.1, 1.1))
    for i, (x, y) in enumerate(((-0.015, -0.01), (0.012, 0.0), (0.0, 0.016), (0.018, -0.016))):
        rod(f"QShaft{i}", (x, y, 0.1), (x, y, 0.19), 0.006, 0.006, M["yew"], q, verts=4)
        block(f"QFletch{i}", (0.03, 0.008, 0.06), at=(x, y, 0.17), turn=(0, 0, 40 * i), mat=M["feather"], parent=q)
    # belt, jerkin skirt, bracer
    block("Belt", (w * 2.35, w * 1.7, 0.03 * s), at=(0, 0, 0.055 * s), mat=M["dark"], parent=pel)
    piece("cylinder", "Skirt", size=(w * 2.3, w * 1.65, 0.11 * s), at=(0, 0, -0.02 * s), mat=M["leather"],
          parent=pel, taper_bottom=(1.15, 1.12), verts=8)
    piece("cylinder", "Bracer", size=(0.05, 0.05, 0.065), at=(0, 0, -0.09), mat=M["leather"], parent=j["ElbowL"],
          verts=6)

    # longbow: stave along local Z, belly toward -Y, string at +Y
    bow = j["Offhand"] = pivot("Offhand", at=(0, 0, -HAND), parent=j["WristL"])
    L, br = 0.84, 0.075
    zs = [-L / 2 + L * i / 6 for i in range(7)]
    pts = [(0, br * (2 * z / L) ** 2 - 0.012 * (1 - (2 * z / L) ** 2), z) for z in zs]
    for i in range(6):
        rz = lambda z: 0.021 - 0.01 * abs(2 * z / L)
        rod(f"Stave{i}", pts[i], pts[i + 1], rz(zs[i]), rz(zs[i + 1]), M["yew"], bow)
    piece("cylinder", "Grip", size=(0.04, 0.04, 0.08), at=(0, -0.012, 0), mat=M["dark"], parent=bow, verts=6)
    for sd in (1, -1):
        piece("cone", f"Nock{sd}", size=(0.02, 0.02, 0.035), at=(0, br, sd * (L / 2 + 0.01)), turn=(0 if sd > 0 else 180, 0, 0),
              mat=M["feather"], parent=bow, verts=5)
    su = j["StringU"] = pivot("StringU", at=(0, br, L / 2), parent=bow)
    sl = j["StringL"] = pivot("StringL", at=(0, br, -L / 2), parent=bow)
    rod("StrU", (0, 0, 0), (0, 0, -L / 2), 0.0045, 0.0045, string, su, verts=4)
    rod("StrL", (0, 0, 0), (0, 0, L / 2), 0.0045, 0.0045, string, sl, verts=4)

    # arrow: nock at the origin, head along +Z
    ar = j["Arrow"] = pivot("Arrow", at=(0, 0, -HAND), parent=j["WristR"])
    AL = 0.44
    rod("Shaft", (0, 0, 0), (0, 0, AL), 0.009, 0.009, M["yew"], ar, verts=5)
    piece("cone", "Head", size=(0.04, 0.012, 0.06), at=(0, 0, AL + 0.025), mat=M["steel"], parent=ar, verts=4)
    for k in (0, 90):
        block(f"Fletch{k}", (0.036, 0.005, 0.08), at=(0, 0, 0.06), turn=(0, 0, k), mat=M["feather"], parent=ar,
              taper=(0.5, 1))

    setp(j, rest_pose(j))

    # ---- rest pose
    R = rest_pose(j)
    R["HipL"]["rot"][1] = out(1, 4)
    R["HipR"]["rot"][1] = out(-1, 4)
    R["HipR"]["rot"][0] = 5
    R["KneeR"]["rot"][0] = 6
    R["AnkleR"]["rot"][0] = -11
    R["Chest"]["rot"][2] = -6
    R["Head"]["rot"] = [4, 0, 6]
    R["ShoulderR"]["rot"] = [-8, out(-1, 9), 0]
    R["ElbowR"]["rot"][0] = -30
    R["ShoulderL"]["rot"] = [-12, out(1, 12), 0]
    R["ElbowL"]["rot"][0] = -55
    orient(j, R, "Offhand", (0.1, -0.22, 1), (-1, 0.5, 0))
    setp(j, R)
    d = Vector((0.12, -0.6, -1)).normalized()
    orient(j, R, "Arrow", d, (1, 0, 0), pos=hand_pos(j, "R") - d * 0.13)
    setp(j, R)

    def idle(t):
        p = cp(R)
        add(p, "Chest", "rot", [1.5 * wave(t, 3.0), 0, 0])
        add(p, "Head", "rot", [0, 0, 5 * wave(t, 3.0, 0.15)])
        add(p, "ShoulderL", "rot", [1.5 * wave(t, 3.0), 0, 0])
        add(p, "ShoulderR", "rot", [-1.5 * wave(t, 3.0), 0, 0])
        add(p, "Pelvis", "loc", [0, 0, -0.003 * (1 - math.cos(2 * math.pi * t / 1.5))])
        return p

    def fidget1(t):  # shift weight, roll the shoulders, crack the neck
        p = cp(R)
        k = keyed(t, [(0, 0), (0.6, 1), (2.2, 1), (3.0, 0)])
        add(p, "Pelvis", "loc", [0.018 * k, 0, -0.004 * k])
        add(p, "Pelvis", "rot", [0, -4 * k, 0])
        add(p, "Chest", "rot", [0, 5 * k, 0])
        add(p, "HipL", "rot", [0, 4 * k, 0])
        add(p, "HipR", "rot", [0, 4 * k, 0])
        r = keyed(t, [(0, 0), (0.7, 0), (1.1, 1), (1.5, 0), (1.9, 1), (2.3, 0)])
        for sd in "LR":
            add(p, "Shoulder" + sd, "loc", [0, 0.01 * r, 0.014 * r])
        n = keyed(t, [(0, 0), (1.0, 0), (1.5, 1), (2.0, -1), (2.6, 0)])
        add(p, "Head", "rot", [0, 14 * n, 0])
        return p

    # sight along an arrow
    S = cp(R)
    S["Head"]["rot"] = [8, 0, 4]
    setp(j, S)
    hp = j["Head"].matrix_world @ Vector((-0.02, -0.09, 0.065))
    d = Vector((0.03, -1, 0.04)).normalized()
    reach(j, S, "R", hp + d * 0.15, (-1, 0.3, -1))
    orient(j, S, "Arrow", d, (0, 0, 1), pos=hp)
    S2 = cp(S)
    orient(j, S2, "Arrow", d, (0.7, 0, 0.7), pos=hp)
    add(S2, "Head", "rot", [0, -6, 0])
    f2keys = unwrap([(0, R), (0.7, S), (1.4, S2), (2.1, S), (2.3, S), (3.0, R)])

    # attack: nock, draw to the cheek, loose
    D = cp(R)
    D["Spine"]["rot"] = [0, 0, -14]
    D["Chest"]["rot"] = [-3, 0, -24]
    D["Head"]["rot"] = [0, 0, 36]
    D["HipL"]["rot"] = [-6, out(1, 9), 0]
    D["HipR"]["rot"] = [6, out(-1, 9), 0]
    D["KneeR"]["rot"][0] = 4
    D["AnkleR"]["rot"][0] = -9
    setp(j, D)
    shl = j["ShoulderL"].matrix_world.translation
    head = j["Head"].matrix_world.translation
    grip = Vector((head.x - 0.02, shl.y - 0.27, shl.z + 0.03))
    aim(j, D, "ShoulderL", grip - shl)
    aim(j, D, "ElbowL", grip - shl)
    orient(j, D, "Offhand", (0.08, 0, 1), (0, 1, 0))
    setp(j, D)
    g = j["Offhand"].matrix_world.translation.copy()
    nock_rest = j["Offhand"].matrix_world @ Vector((0, br, 0))
    anchor = Vector((g.x, head.y - 0.05, g.z))
    N_ = cp(D)  # nocked
    reach(j, N_, "R", nock_rest, (-1, 1, 0))
    fdir = (g - nock_rest).normalized()
    orient(j, N_, "Arrow", fdir, (0, 0, 1), pos=nock_rest)
    reach(j, D, "R", anchor, (-1, 1, -0.2))
    fdir = (g - anchor).normalized()
    orient(j, D, "Arrow", fdir, (0, 0, 1), pos=anchor)
    setp(j, D)
    for nm, ax in (("StringU", (0, 0, -1)), ("StringL", (0, 0, 1))):
        a_loc = j["Offhand"].matrix_world.inverted() @ anchor
        v = a_loc - kit._REST[nm][0]
        _rot(D, nm, Vector(ax).rotation_difference(v).to_matrix())
        D[nm]["scale"] = [1, 1, v.length / (L / 2)]
    LO = cp(D)  # loosed
    for nm in ("StringU", "StringL"):
        LO[nm] = cp(R[nm])
    reach(j, LO, "R", anchor + Vector((-0.05, 0.07, 0.02)), (-1, 1, -0.2))
    setp(j, D)
    FLY = cp(D)
    orient(j, FLY, "Arrow", fdir, (0, 0, 1), pos=anchor + fdir * 2.5)
    FLY["Arrow"]["scale"] = [0.001] * 3
    akeys = unwrap([(0, R), (0.22, N_), (0.6, D), (0.72, D), (0.76, LO), (1.2, R)])
    T0 = cp(R)
    T0["Arrow"]["scale"] = [0.001] * 3
    arrowkeys = unwrap([(0, R), (0.22, N_), (0.6, D), (0.72, D), (0.86, FLY), (0.88, T0), (1.1, T0), (1.2, R)])

    def attack(t):
        p = blend(t, akeys)
        p["Arrow"] = blend(t, arrowkeys)["Arrow"]
        return p

    # cheer: bow brandished overhead
    C = cp(R)
    C["Chest"]["rot"] = [-7, 0, 0]
    C["Head"]["rot"] = [-16, 0, 0]
    aim(j, C, "ShoulderL", (0.35, -0.15, 1))
    aim(j, C, "ElbowL", (0.15, -0.1, 1))
    orient(j, C, "Offhand", (1, 0, 0.2), (0, 0.3, -1))
    aim(j, C, "ShoulderR", (-0.45, -0.2, 1))
    aim(j, C, "ElbowR", (-0.05, -0.3, 1))
    C2 = cp(C)
    add(C2, "Chest", "rot", [-4, 0, 0])
    add(C2, "ShoulderL", "loc", [0, 0, 0.012])
    add(C2, "ShoulderR", "loc", [0, 0, 0.012])
    ckeys = unwrap([(0, R), (0.35, C), (0.6, C2), (0.85, C), (1.1, C2), (1.5, R)])

    record(j, "Idle", idle, 3.0)
    record(j, "Fidget1", fidget1, 3.0)
    record(j, "Fidget2", lambda t: blend(t, f2keys), 3.0)
    record(j, "Attack", attack, 1.2)
    record(j, "Cheer", lambda t: blend(t, ckeys), 1.5)
    export("archer", j, rest=R)


if __name__ == "__main__":
    build()
