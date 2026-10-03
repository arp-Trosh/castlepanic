"""Troll: huge, hunched, knuckle-dragging stony brute with a tree-trunk club. build() is shared with troll_mage.py."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

HIDE = (0.36, 0.42, 0.46)
MOSS = (0.22, 0.30, 0.12)
OCHRE = (0.50, 0.36, 0.14)


def lumpy(objs, amount, seed=3):
    """Jitter vertices of finished parts (fraction of each part's size) for lumpy stony hide."""
    rng = new_rng(seed)
    for o in objs:
        me = o.data
        dim = max(o.dimensions) or 1
        offs = {}
        for v in me.vertices:
            k = tuple(round(c, 4) for c in v.co)
            if k not in offs:
                offs[k] = Vector(rng.normal(0, amount * dim, 3))
            v.co += offs[k]


def build(name, height, mage=False):
    reset()
    rng = new_rng(11 if not mage else 12)
    hide = tex_skin(rng, HIDE, warts=0.9, grime=0.7)
    hide = mix(hide, MOSS, smoothstep(0.66, 0.82, noise(rng, 1.8)) * 0.85)
    texs = {"hide": hide, "moss": tex_fur(rng, MOSS), "cloth": tex_cloth(rng, OCHRE, wear=0.8),
            "wood": tex_wood(rng, (0.30, 0.22, 0.14)), "rock": tex_stone(rng, (0.45, 0.45, 0.47), moss=0.4, blocks=False),
            "bone": tex_bone(rng), "rope": tex_leather(rng, (0.42, 0.34, 0.2))}
    if mage:
        texs["robe"] = tex_cloth(rng, (0.14, 0.12, 0.18), wear=0.6)
        texs["gold"] = tex_gold(rng)
    t = save_textures(name, texs)
    M = {k: material(k.title(), image=t[k], roughness=0.9) for k in t}
    eye = material("Eye", (0.7, 0.9, 1.0), emission=(0.6, 0.9, 1.0), strength=4.0)
    body = M["robe"] if mage else M["hide"]
    m = {"skin": M["hide"], "body": body, "legs": M["robe"] if mage else M["hide"], "feet": M["hide"]}
    j = humanoid(m, height=height, hunch=0.6, girth=1.55, arm=1.55, leg=0.7, head=1.15)
    for nm in ("Torso", "Belly"):
        bpy.data.objects.remove(bpy.data.objects[nm])
    s = height
    hide_parts = [o for o in bpy.data.objects if o.type == "MESH" and o.data.materials and
                  o.data.materials[0] == M["hide"]]

    # --- head: heavy brow, long drooping nose, ice eyes, small ears, under-bite tusks
    hd, h = j["Head"], 0.15 * s * 1.15
    hide_parts += [
        piece("cube", "Brow", size=(h * 1.05, h * 0.35, h * 0.28), at=(0, -h * 0.42, h * 0.78), turn=(-12, 0, 4),
              mat=M["hide"], parent=hd, bevel=0.01),
        piece("cone", "Nose", size=(h * 0.32, h * 0.32, h * 0.8), at=(0, -h * 0.62, h * 0.5), turn=(-150, 0, 0),
              shape_at=(0, 0, 0.5 * h * 0.8), mat=M["hide"], parent=hd, verts=6),
    ]
    for sd in (1, -1):
        piece("sphere", "Eye" + ("L" if sd > 0 else "R"), size=(h * 0.16, h * 0.08, h * 0.1),
              at=(sd * h * 0.24, -h * 0.5, h * 0.64), mat=eye, parent=hd, verts=6)
        hide_parts.append(piece("cone", "Ear" + str(sd), size=(h * 0.15, h * 0.4, h * 0.4), at=(sd * h * 0.52, 0, h * 0.6),
                                turn=(10, sd * 70, 0), mat=M["hide"], parent=hd, verts=5))
        piece("cone", "Tusk" + str(sd), size=(h * 0.08, h * 0.08, h * 0.26), at=(sd * h * 0.25, -h * 0.5, h * 0.05),
              turn=(-10, sd * 15, 0), mat=M["bone"], parent=j["Jaw"], verts=5)
    # --- bulk: humped shoulders, gut, big fists, moss patches
    ch = j["Chest"]
    w = 0.13 * s * 1.55
    hide_parts.append(piece("sphere", "Torso", size=(w * 2.9, w * 1.9, 0.3 * s), at=(0, 0, 0.11 * s), taper_bottom=(0.75, 0.85),
                            mat=body, parent=ch, verts=9))
    hide_parts.append(piece("sphere", "Hump", size=(w * 2.4, w * 1.9, 0.2 * s), at=(0, 0.06 * s, 0.2 * s),
                            mat=M["hide"] if not mage else M["robe"], parent=ch, verts=8))
    hide_parts.append(piece("sphere", "Gut", size=(w * 2.0, w * 1.8, 0.22 * s), at=(0, -0.03 * s, 0.07 * s),
                            mat=body, parent=j["Spine"], verts=8))
    piece("ico", "MossBack", size=(w * 1.6, w * 0.7, 0.1 * s), at=(0.02 * s, 0.13 * s, 0.24 * s), turn=(20, 0, 10),
          mat=M["moss"], parent=ch, jitter=0.08, flat_shade=True)
    for sd, side in ((1, "L"), (-1, "R")):
        hide_parts.append(piece("ico", "Fist" + side, size=(0.11 * s, 0.12 * s, 0.11 * s), at=(0, -0.01 * s, -0.06 * s),
                                mat=M["hide"], parent=j["Wrist" + side]))
        hide_parts.append(piece("sphere", "Calf" + side, size=(0.1 * s, 0.1 * s, 0.13 * s), at=(0, 0.01 * s, -0.06 * s),
                                mat=M["hide"], parent=j["Knee" + side], verts=7))
        hide_parts.append(piece("ico", "Toes" + side, size=(0.15 * s, 0.17 * s, 0.07 * s), at=(0, -0.06 * s, -0.01 * s),
                                mat=M["hide"], parent=j["Ankle" + side]))
    piece("ico", "MossShoulder", size=(0.12 * s, 0.12 * s, 0.07 * s), at=(0, 0, 0.04 * s), mat=M["moss"],
          parent=j["ShoulderL"], jitter=0.08, flat_shade=True)
    # --- loincloth: belt + ragged front/back flaps
    pv = j["Pelvis"]
    if not mage:
        piece("torus", "Belt", size=(w * 2.5, w * 1.9, 0.5), at=(0, 0, 0.03 * s), mat=M["rope"], parent=pv)
        for i, (y, rz) in enumerate(((-1, 4), (1, -6))):
            piece("cube", f"Flap{i}", size=(w * 1.3, 0.02 * s, 0.2 * s), at=(0.01 * s * i, y * w * 0.8, -0.06 * s),
                  turn=(y * -8, 0, rz), mat=M["cloth"], parent=pv, taper_bottom=(1.25, 1), jitter=0.004)
            for k in range(3):
                piece("cube", f"Rag{i}{k}", size=(w * 0.3, 0.018 * s, 0.07 * s),
                      at=((k - 1) * w * 0.45, y * w * 0.85, -0.17 * s - 0.02 * s * (k % 2)), turn=(0, 0, 8 * (k - 1)),
                      mat=M["cloth"], parent=pv)
    lumpy(hide_parts, 0.035)

    # --- weapon pivot in the right fist
    wpn = pivot("Weapon", at=(0, -0.01 * s, -0.06 * s), parent=j["WristR"])
    j["Weapon"] = wpn
    if not mage:
        L = 0.64 * s
        piece("cylinder", "Club", size=(0.07 * s, 0.07 * s, L), shape_at=(0, 0, -L / 2 + 0.06 * s),
              taper_bottom=(2.2, 2.2), mat=M["wood"], parent=wpn, verts=7, jitter=0.012, flat_shade=True)
        piece("ico", "Rock", size=(0.2 * s, 0.17 * s, 0.17 * s), at=(0, 0, -L + 0.12 * s), turn=(20, 10, 0),
              mat=M["rock"], parent=wpn, jitter=0.02, flat_shade=True)
        for k in range(2):
            piece("torus", f"Lash{k}", size=(0.22 * s, 0.22 * s, 1.5), at=(0, 0, -L + 0.2 * s + 0.05 * s * k),
                  turn=(15 * k, 0, 0), mat=M["rope"], parent=wpn)
        piece("cylinder", "Bone", size=(0.03 * s, 0.03 * s, 0.25 * s), at=(0.07 * s, 0, -L + 0.22 * s),
              turn=(0, 70, 20), mat=M["bone"], parent=wpn, verts=6)
        piece("cone", "Spike", size=(0.05 * s, 0.05 * s, 0.14 * s), at=(-0.08 * s, -0.04 * s, -L + 0.3 * s),
              turn=(30, -80, 0), mat=M["bone"], parent=wpn, verts=5)

    # --- blood pool and a severed-arm stand-in for Die
    bl = pivot("Blood", at=(0, -0.45 * s, 0.003))
    j["Blood"] = bl
    gore = material("Gore", (0.22, 0.015, 0.01), roughness=0.3)
    for k, (x, y, r) in enumerate(((0, 0, 0.35), (0.18, -0.1, 0.18), (-0.15, 0.12, 0.2))):
        piece("cylinder", f"BloodPool{k}", size=(r * s, r * s * 0.8, 0.004), at=(x * s, y * s, 0.002 * k),
              mat=gore, parent=bl, verts=9)
    return j, M, s


# ================================================================ poses
def base(j, s, mage=False):
    """Rest pose: arms hanging forward, knuckles near the ground, bowed legs."""
    p = rest_pose(j)
    for sd, side in ((1, "L"), (-1, "R")):
        p["Hip" + side]["rot"][1] = out(sd, 9)
        p["Knee" + side]["rot"][1] = out(sd, -14)
        p["Knee" + side]["rot"][0] = 14
        p["Hip" + side]["rot"][0] = -12
        p["Ankle" + side]["rot"][1] = out(sd, 5)
        p["Shoulder" + side]["rot"] = [-38, out(sd, 12), 0]
        p["Elbow" + side]["rot"][0] = -12
    p["Root"]["loc"][2] = 0.032 * s
    p["Spine"]["rot"][0] = 30
    p["Chest"]["rot"][0] = 22
    p["Neck"]["rot"][0] = -30
    p["Head"]["rot"][0] = -12
    p["Weapon"]["rot"] = [-52, 0, 0]
    p["Blood"]["scale"] = [0.001, 0.001, 0.001]
    if mage:  # staff held aloft
        p["ShoulderR"]["rot"] = [-95, out(-1, 18), 0]
        p["ElbowR"]["rot"][0] = -55
        p["Weapon"]["rot"] = [150, 0, 0]
    return p


def clips(j, s, mage=False):
    B = lambda: base(j, s, mage)

    def add(p, joint, i, v, key="rot"):
        p[joint][key][i] += v

    def idle(t):
        p = B()
        b = wave(t, 3.0)
        add(p, "Chest", 0, 3 * b)
        add(p, "Spine", 2, 2 * wave(t, 3.0, 0.25))
        add(p, "ShoulderL", 0, -3 * b); add(p, "ShoulderR", 0, -3 * b)
        add(p, "Head", 0, -2 * b)
        add(p, "Jaw", 0, 4 + 4 * b)
        return p

    def fidget1(t):  # sniff the air, scratch the head
        p = idle(t)
        u = keyed(t, [(0, 0), (0.6, 1), (1.4, 1), (1.8, 0), (3.0, 0)])
        add(p, "Neck", 0, -25 * u); add(p, "Head", 0, -15 * u + 6 * math.sin(t * 25) * u)
        v = keyed(t, [(0, 0), (1.6, 0), (2.1, 1), (2.6, 1), (3.0, 0)])
        add(p, "ShoulderL", 0, -150 * v); add(p, "ElbowL", 0, -70 * v)
        add(p, "ElbowL", 1, 12 * v * math.sin(t * 30))
        return p

    def fidget2(t):  # look left, then right
        p = idle(t)
        y = keyed(t, [(0, 0), (0.7, 1), (1.4, 1), (2.1, -1), (2.8, -1), (3.4, 0)])
        add(p, "Chest", 2, 18 * y); add(p, "Neck", 2, 30 * y); add(p, "Spine", 2, 8 * y)
        return p

    def fidget3(t):  # heft the club, slap it in the other palm
        p = idle(t)
        u = keyed(t, [(0, 0), (0.6, 1), (2.4, 1), (3.0, 0)])
        tap = max(0, math.sin(t * 2 * math.pi / 0.6)) * u
        add(p, "ShoulderR", 0, -70 * u - 15 * tap); add(p, "ElbowR", 0, -55 * u)
        add(p, "ShoulderR", 2, -20 * u)
        add(p, "ShoulderL", 0, -55 * u); add(p, "ElbowL", 0, -45 * u); add(p, "ShoulderL", 2, 25 * u)
        add(p, "Weapon", 0, 40 * u)
        add(p, "Head", 0, 15 * u)
        return p

    def walk(t):
        p = B()
        for sd, side in ((1, "L"), (-1, "R")):
            add(p, "Hip" + side, 0, 24 * sd * wave(t, 1.0))
            add(p, "Knee" + side, 0, 18 + 18 * wave(t, 1.0, 0.25 * sd))
            add(p, "Shoulder" + side, 0, -22 * sd * wave(t, 1.0))
        stomp = abs(wave(t, 1.0))
        add(p, "Root", 2, -0.03 * s * (1 - stomp), "loc")
        add(p, "Pelvis", 1, 6 * wave(t, 1.0))
        add(p, "Chest", 1, -5 * wave(t, 1.0))
        add(p, "Chest", 0, -4 * stomp)
        return p

    def attack(t):  # club overhead, two-handed-ish smash forward
        p = B()
        u = keyed(t, [(0, 0), (0.45, 1), (0.6, 2), (0.75, 2), (1.3, 0)])
        up, down = min(u, 1), max(0, u - 1)
        add(p, "ShoulderR", 0, -190 * up + 120 * down); add(p, "ElbowR", 0, -40 * up + 40 * down)
        add(p, "ShoulderL", 0, -120 * up + 80 * down)
        add(p, "Weapon", 0, 40 * up - 20 * down)
        add(p, "Chest", 0, 15 * up - 30 * down); add(p, "Spine", 0, 8 * up - 15 * down)
        add(p, "Head", 0, -10 * up + 10 * down); add(p, "Jaw", 0, 20 * up)
        add(p, "HipL", 0, -20 * down); add(p, "KneeL", 0, 20 * down)
        return p

    def hit(t):
        p = B()
        u = keyed(t, [(0, 0), (0.12, 1), (0.35, 0.8), (0.7, 0)])
        add(p, "Chest", 0, 22 * u); add(p, "Spine", 0, 10 * u); add(p, "Head", 0, 15 * u)
        add(p, "Root", 1, 0.08 * s * u, "loc")
        add(p, "HipR", 0, 20 * u); add(p, "KneeR", 0, 15 * u)
        add(p, "ShoulderL", 1, out(1, 30 * u)); add(p, "ShoulderR", 1, out(-1, 30 * u))
        add(p, "Jaw", 0, 18 * u)
        return p

    def die(t):  # knees buckle, topple backward, club drops
        p = B()
        k = keyed(t, [(0, 0), (0.5, 1), (1.8, 1)])
        f = keyed(t, [(0, 0), (0.4, 0), (1.2, 1), (1.8, 1)])
        add(p, "HipL", 0, -60 * k); add(p, "HipR", 0, -60 * k)
        add(p, "KneeL", 0, 80 * k); add(p, "KneeR", 0, 80 * k)
        add(p, "Root", 2, -0.15 * s * k * (1 - f) + 0.04 * s * f, "loc")
        add(p, "Root", 0, 70 * f)
        add(p, "Chest", 0, 20 * k - 10 * f); add(p, "Head", 0, 25 * f)
        add(p, "ShoulderL", 1, out(1, 60 * f)); add(p, "ShoulderR", 1, out(-1, 70 * f))
        add(p, "ShoulderR", 0, -30 * f)
        add(p, "Jaw", 0, 25 * k)
        b = 0.001 + keyed(t, [(0, 0), (0.9, 0), (1.8, 1)])
        p["Blood"]["scale"] = [b, b, 1]
        return p

    def roar(t):
        p = B()
        u = keyed(t, [(0, 0), (0.35, 1), (1.1, 1), (1.5, 0)])
        sh = math.sin(t * 40) * u * 2
        add(p, "ShoulderL", 0, -160 * u); add(p, "ShoulderR", 0, -160 * u)
        add(p, "ShoulderL", 1, out(1, 25 * u)); add(p, "ShoulderR", 1, out(-1, 25 * u))
        add(p, "ElbowL", 0, -30 * u); add(p, "ElbowR", 0, -30 * u)
        add(p, "Chest", 0, 25 * u + sh); add(p, "Spine", 0, 10 * u)
        add(p, "Neck", 0, 20 * u); add(p, "Head", 0, 25 * u); add(p, "Jaw", 0, 35 * u)
        return p

    record(j, "Idle", idle, 3.0)
    record(j, "Fidget1", fidget1, 3.0)
    record(j, "Fidget2", fidget2, 3.4)
    record(j, "Fidget3", fidget3, 3.0)
    record(j, "Walk", walk, 1.0)
    record(j, "Attack", attack, 1.3)
    record(j, "Hit", hit, 0.7)
    record(j, "Die", die, 1.8)
    record(j, "Roar", roar, 1.5)
    return B()


def report_height():
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("Blood")
          for c in o.bound_box]
    print(f"HEIGHT min {min(zs):.3f} max {max(zs):.3f}")



if __name__ == "__main__":
    j, M, s = build("troll", 1.35)
    rest = clips(j, s)
    from kit import _apply
    _apply(j, rest); report_height()
    export("troll", j, rest)
