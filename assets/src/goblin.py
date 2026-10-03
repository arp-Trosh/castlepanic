"""Goblin: wiry, hunched, big-headed, swept-back ears, hooked nose, underbite fangs, yellow eyes, rusted cleaver.
make(king=True) builds the Goblin King (goblin_king.py)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

SKIN = (0.45, 0.50, 0.20)
RAG = (0.32, 0.14, 0.08)
BONE = (0.74, 0.69, 0.56)
PURPLE = (0.28, 0.10, 0.34)


def cone_to(name, length, r, at, turn, mat, parent, verts=6, flat_y=1.0):
    """A cone whose base is at `at` and tip points along the turned +Z."""
    return piece("cone", name, size=(2 * r, 2 * r * flat_y, length), shape_at=(0, 0, length / 2), at=at, turn=turn,
                 mat=mat, parent=parent, verts=verts, flat_shade=True)


def make(king=False):
    name = "goblin_king" if king else "goblin"
    reset()
    rng = new_rng(11 if king else 5)
    tx = {"skin": tex_skin(rng, SKIN, warts=0.7, grime=0.6), "rag": tex_cloth(rng, RAG, wear=0.8),
          "bone": tex_bone(rng, BONE), "iron": tex_metal(rng, (0.30, 0.28, 0.27), rust=0.45),
          "wood": tex_wood(rng, (0.30, 0.20, 0.11)), "leather": tex_leather(rng, (0.24, 0.15, 0.09))}
    if king:
        tx["purple"] = tex_cloth(rng, PURPLE, wear=0.6)
        tx["gold"] = tex_gold(rng, (0.62, 0.46, 0.16))
    t = save_textures(name, tx)
    M = {k: material(k.capitalize(), image=v, roughness=0.85) for k, v in t.items()}
    M["iron"].node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.5
    if king:
        M["gold"].node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.8
        M["gold"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.4
    eye = material("Eye", (1.0, 0.85, 0.15), emission=(1.0, 0.8, 0.1), strength=4.0)
    bloodm = material("Blood", (0.22, 0.01, 0.01), roughness=0.3)

    girth = 1.05 if king else 0.8
    j = humanoid({"skin": M["skin"], "body": M["skin"], "legs": M["skin"], "feet": M["skin"]},
                 height=1.0, hunch=0.0, girth=girth, arm=1.15, leg=0.9, head=1.55)
    s = 1.0
    h = 0.15 * 1.55
    w = 0.13 * girth
    # the hunch (set on the joints directly: spine and chest pitch forward, neck lifts the head back up)
    j["Spine"].rotation_euler.x = math.radians(22)
    j["Chest"].rotation_euler.x = math.radians(18)
    j["Neck"].rotation_euler.x = math.radians(-30)
    j["Neck"].location.y -= 0.02
    j["Head"].rotation_euler.x = math.radians(-6)

    hd, jaw = j["Head"], j["Jaw"]
    # ears: long, flat, swept back and out
    for sd, side in ((1, "L"), (-1, "R")):
        cone_to("Ear" + side, h * 1.15, h * 0.2, (sd * h * 0.42, h * 0.05, h * 0.62), (-38, sd * 68, 0), M["skin"],
                hd, verts=5, flat_y=0.4)
        piece("cube", "Eye" + side, size=(h * 0.17, h * 0.06, h * 0.07), at=(sd * h * 0.19, -h * 0.5, h * 0.66),
              turn=(0, sd * 18, 0), mat=eye, parent=hd)
    block("Brow", (h * 0.75, h * 0.18, h * 0.1), at=(0, -h * 0.47, h * 0.76), turn=(-15, 0, 0), mat=M["skin"],
          parent=hd)
    nose = cone_to("Nose", h * 0.5, h * 0.12, (0, -h * 0.5, h * 0.62), (115, 0, 0), M["skin"], hd, verts=5)
    cone_to("NoseHook", h * 0.2, h * 0.07, (0, -h * 0.88, h * 0.47), (175, 0, 0), M["skin"], hd, verts=5)
    # jutting jaw with underbite fangs (one broken)
    block("Chin", (h * 0.6, h * 0.35, h * 0.2), at=(0, -h * 0.45, -h * 0.05), mat=M["skin"], parent=jaw)
    cone_to("FangL", h * 0.28, h * 0.06, (h * 0.2, -h * 0.58, h * 0.03), (-8, 10, 0), M["bone"], jaw, verts=4)
    cone_to("FangR", h * 0.16, h * 0.06, (-h * 0.2, -h * 0.58, h * 0.03), (-8, -10, 0), M["bone"], jaw, verts=4)

    pel, chest = j["Pelvis"], j["Chest"]
    # rag loincloth: front and back flaps with ragged hems, rope belt
    block("Belt", (w * 2.4, w * 1.7, 0.035), at=(0, 0, 0.045), mat=M["leather"], parent=pel)
    for k, y in (("Front", -1), ("Back", 1)):
        block("Rag" + k, (w * 1.5, 0.02, 0.2), at=(0, y * w * 0.8, -0.07), turn=(y * -8, 0, 0), mat=M["rag"],
              parent=pel, taper_bottom=(0.8, 1))
        for i, (x, l) in enumerate(((-0.4, 0.06), (0.05, 0.09), (0.4, 0.05))):
            block(f"Rag{k}{i}", (w * 0.45, 0.018, l), at=(x * w * 1.3, y * w * 0.8 + y * 0.02, -0.17 - l / 2),
                  turn=(y * -8, 0, x * 20), mat=M["rag"], parent=pel)
    # bone necklace
    piece("torus", "Cord", size=(w * 2.1, w * 1.6, 1.0), at=(0, -0.01, 0.17), turn=(12, 0, 0), mat=M["leather"],
          parent=chest, verts=10)
    for i, a in enumerate((-50, -25, 0, 25, 50)):
        x, y = w * 1.0 * math.sin(math.radians(a)), -w * 0.85 * math.cos(math.radians(a))
        cone_to(f"Tooth{i}", 0.05 if a == 0 else 0.035, 0.012, (x, y, 0.16), (180 - 15, 0, a * 0.3), M["bone"],
                chest, verts=4)

    # weapon
    j["Weapon"] = pivot("Weapon", at=(0, 0, -0.04), turn=(100, 0, 0), parent=j["WristR"])
    wp = pivot("Grip", turn=(0, 0, 35), parent=j["Weapon"])  # twist the blade face toward the viewer
    if not king:
        piece("cylinder", "Haft", size=(0.025, 0.025, 0.2), at=(0, 0, 0.02), mat=M["wood"], parent=wp, verts=6)
        blade = block("Blade", (0.012, 0.13, 0.26), at=(0, -0.05, 0.25), turn=(-6, 0, 0), mat=M["iron"], parent=wp,
                      taper=(1, 1.35), bevel=0.004)
        for i, z in enumerate((-0.06, 0.03, 0.1)):   # jagged notched edge teeth
            cone_to(f"Jag{i}", 0.03, 0.012, (0, -0.115, z), (90, 0, 0), M["iron"], blade, verts=4)
        piece("cylinder", "Pommel", size=(0.035, 0.035, 0.02), at=(0, 0, -0.08), mat=M["iron"], parent=wp, verts=6)
    else:
        piece("cylinder", "Rod", size=(0.032, 0.032, 0.42), at=(0, 0, 0.08), mat=M["gold"], parent=wp, verts=6)
        piece("ico", "SkullS", size=(0.09, 0.1, 0.09), at=(0, 0, 0.33), mat=M["bone"], parent=wp, jitter=0.004)
        block("SkullJaw", (0.06, 0.05, 0.035), at=(0, -0.025, 0.285), mat=M["bone"], parent=wp)
        for sd in (1, -1):
            piece("cube", f"Socket{sd}", size=(0.022, 0.01, 0.018), at=(sd * 0.02, -0.048, 0.34), mat=eye,
                  parent=wp)
            cone_to(f"Prong{sd}", 0.07, 0.012, (sd * 0.03, 0, 0.27), (0, sd * 40, 0), M["gold"], wp, verts=4)
        piece("cylinder", "Collar", size=(0.05, 0.05, 0.03), at=(0, 0, 0.27), mat=M["gold"], parent=wp, verts=6)

    if king:
        # pot belly
        piece("sphere", "Gut", size=(w * 2.3, w * 2.1, 0.24), at=(0, -0.04, 0.07), mat=M["skin"], parent=j["Spine"],
              verts=8)
        # tarnished spiked crown, tilted
        crown = pivot("Crown", at=(0, 0, h * 0.98), turn=(-6, 8, 0), parent=hd)
        piece("cylinder", "CrownBand", size=(h * 0.95, h * 1.0, h * 0.18), mat=M["gold"], parent=crown, verts=8,
              taper=(1.08, 1.08), flat_shade=True)
        for i in range(7):
            a = math.radians(i * 360 / 7 + 10)
            ln = h * (0.36 if i % 2 == 0 else 0.25)
            cone_to(f"Spike{i}", ln, h * 0.08, (h * 0.46 * math.sin(a), -h * 0.48 * math.cos(a), h * 0.06),
                    (0, 0, 0), M["gold"], crown, verts=4)
        # ragged royal cloak hanging from the shoulders down the back
        cl = pivot("Cloak", at=(0, w * 0.95, 0.19), turn=(-8, 0, 0), parent=chest)
        block("Mantle", (w * 3.2, w * 1.9, 0.06), at=(0, -w * 0.5, 0.0), mat=M["purple"], parent=cl)
        block("CloakBody", (w * 3.0, 0.025, 0.5), at=(0, 0.01, -0.25), mat=M["purple"], parent=cl,
              taper_bottom=(1.25, 1))
        for i, (x, l) in enumerate(((-1.4, 0.08), (-0.7, 0.14), (0.0, 0.06), (0.6, 0.12), (1.3, 0.09))):
            block(f"CloakRag{i}", (w * 0.6, 0.022, l), at=(x * w, 0.01, -0.5 - l / 2), turn=(0, 0, x * 8),
                  mat=M["purple"], parent=cl)
        piece("sphere", "Clasp", size=(0.04, 0.03, 0.04), at=(w * 0.9, -w * 1.3, 0.0), mat=M["gold"], parent=cl,
              verts=6)

    # blood pool for Die (hidden)
    bl = j["Blood"] = pivot("Blood", at=(0, 0.3, 0.004))
    for i, (x, y, r) in enumerate(((0, 0, 0.22), (0.12, 0.1, 0.12), (-0.1, -0.08, 0.1), (0.05, 0.2, 0.08))):
        piece("cylinder", f"Pool{i}", size=(r * 2, r * 1.6, 0.004), at=(x, y, 0), mat=bloodm, parent=bl, verts=10)
    bl.scale = (0.001, 0.001, 0.001)

    # fit to height, stand on the ground
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in bpy.context.scene.objects if o.type == "MESH"
          and not o.name.startswith("Pool") for c in o.bound_box]
    target = 0.84 if king else 0.70
    k = target / (max(zs) - min(zs))
    j["Root"].scale = (k, k, k)
    j["Root"].location.z = -min(zs) * k
    bl.scale = (0.001 * k,) * 3
    clips(j, king)
    export(name, j)


# ------------------------------------------------------------------ poses
def base(j, king=False, t=0.0):
    p = rest_pose(j)
    b = 1.5 * wave(t, 2.0) if t else 0.0
    p["Pelvis"]["loc"][2] = -0.015
    for sd, side in ((1, "L"), (-1, "R")):
        p["Hip" + side]["rot"][0] = -18
        p["Hip" + side]["rot"][1] = out(sd, 6)
        p["Knee" + side]["rot"][0] = 30
        p["Ankle" + side]["rot"][0] = -12
    p["ShoulderL"]["rot"] = [-30, out(1, 14 if king else 10), 0]
    p["ElbowL"]["rot"][0] = -25
    if king:  # swagger: sceptre arm out, chest puffed up, chin raised
        p["ShoulderR"]["rot"] = [-40, out(-1, 22), 0]
        p["ElbowR"]["rot"][0] = -50
        p["Chest"]["rot"][0] = -6
        p["Neck"]["rot"][0] = -6
        p["Spine"]["rot"][2] = 6
    else:
        p["ShoulderR"]["rot"] = [-35, out(-1, 12), 0]
        p["ElbowR"]["rot"][0] = -55
    p["Jaw"]["rot"][0] = 4
    return p


def clips(j, king):
    def idle(t):
        p = base(j, king)
        br = wave(t, 3.0)
        p["Chest"]["rot"][0] += 3 * br
        p["Spine"]["rot"][1] = 2 * wave(t, 3.0, 0.25)
        p["Neck"]["rot"][2] = 6 * wave(t, 3.0, 0.1)
        p["ShoulderR"]["rot"][0] += 4 * br
        p["Jaw"]["rot"][0] += 3 * (0.5 + 0.5 * wave(t, 1.5))
        return p

    def fidget1(t):  # scratch the head with the free hand
        p = base(j, king)
        u = keyed(t, [(0, 0), (0.6, 1), (2.4, 1), (3.0, 0)])
        p["ShoulderL"]["rot"][0] = lerp(-30, -155, u)
        p["ShoulderL"]["rot"][1] = lerp(out(1, 10), out(1, 35), u)
        p["ElbowL"]["rot"][0] = lerp(-25, -95, u) + 15 * u * wave(t, 0.3)
        p["Neck"]["rot"][1] = -12 * u
        p["Jaw"]["rot"][0] += 10 * u
        return p

    def fidget2(t):  # look around
        p = base(j, king)
        a = keyed(t, [(0, 0), (0.6, 1), (1.3, 1), (1.9, -1), (2.6, -1), (3.0, 0)])
        p["Spine"]["rot"][2] += 15 * a
        p["Neck"]["rot"][2] = 30 * a
        p["Neck"]["rot"][0] += -8 * abs(a)
        return p

    def fidget3(t):  # heft the weapon, spin it, test the edge
        p = base(j, king)
        u = keyed(t, [(0, 0), (0.5, 1), (2.5, 1), (3.0, 0)])
        p["ElbowR"]["rot"][0] += -40 * u
        p["ShoulderR"]["rot"][1] += out(-1, -10) * u
        p["Weapon"]["rot"][2] = keyed(t, [(0, 0), (0.6, 0), (1.5, 360), (3.0, 360)])
        p["Neck"]["rot"][2] = -20 * u
        p["Neck"]["rot"][0] = 10 * u
        p["ShoulderL"]["rot"][0] = lerp(-30, -70, keyed(t, [(0, 0), (1.6, 0), (2.0, 1), (2.4, 0), (3, 0)]))
        return p

    def walk(t):
        p = base(j, king)
        for sd, side in ((1, "L"), (-1, "R")):
            ph = wave(t, 1.0, 0 if sd > 0 else 0.5)
            p["Hip" + side]["rot"][0] = -18 - 28 * ph
            p["Knee" + side]["rot"][0] = 30 + 30 * max(0.0, wave(t, 1.0, 0.25 if sd > 0 else 0.75))
            p["Ankle" + side]["rot"][0] = -12 + 10 * ph
        p["ShoulderL"]["rot"][0] = -30 + 25 * wave(t, 1.0)
        p["ShoulderR"]["rot"][0] += -8 * wave(t, 1.0, 0.5)
        p["Pelvis"]["loc"][2] = -0.015 - 0.012 * abs(wave(t, 1.0))
        p["Pelvis"]["rot"][2] = 6 * wave(t, 1.0)
        p["Spine"]["rot"][2] = -5 * wave(t, 1.0)
        p["Chest"]["rot"][0] += 4
        p["Spine"]["rot"][1] = 3 * wave(t, 1.0)
        return p

    def attack(t):
        p = base(j, king)
        sh = keyed(t, [(0, -35), (0.4, -165), (0.62, -40), (0.85, -40), (1.2, -35)])
        el = keyed(t, [(0, -55), (0.4, -80), (0.62, -15), (0.85, -15), (1.2, -55)])
        ch = keyed(t, [(0, 0), (0.4, -14), (0.62, 22), (0.85, 22), (1.2, 0)])
        p["ShoulderR"]["rot"][0] = sh
        p["ElbowR"]["rot"][0] = el
        p["Chest"]["rot"][0] += ch
        p["Spine"]["rot"][0] = ch * 0.6
        p["Spine"]["rot"][2] = keyed(t, [(0, 0), (0.4, 15), (0.62, -10), (1.2, 0)])
        p["Jaw"]["rot"][0] += keyed(t, [(0, 0), (0.4, 20), (0.7, 10), (1.2, 0)])
        p["HipL"]["rot"][0] += keyed(t, [(0, 0), (0.45, -15), (0.85, -15), (1.2, 0)])
        return p

    def hit(t):
        p = base(j, king)
        u = keyed(t, [(0, 0), (0.12, 1), (0.3, 0.8), (0.7, 0)])
        p["Chest"]["rot"][0] += -25 * u
        p["Spine"]["rot"][0] = -10 * u
        p["Neck"]["rot"][0] = -20 * u
        p["Root"]["loc"][1] = 0.05 * u
        p["HipR"]["rot"][0] += 20 * u
        p["ShoulderL"]["rot"][0] += 30 * u
        p["ShoulderR"]["rot"][0] += 15 * u
        p["Jaw"]["rot"][0] += 18 * u
        return p

    def die(t):
        p = base(j, king)
        k = keyed(t, [(0, 0), (0.5, 1), (1.8, 1)])           # knees buckle
        f = keyed(t, [(0, 0), (0.4, 0), (1.1, 1), (1.8, 1)])  # topple back
        for side in "LR":
            p["Hip" + side]["rot"][0] += -50 * k
            p["Knee" + side]["rot"][0] += 70 * k
        p["Pelvis"]["loc"][2] += -0.12 * k
        p["Root"]["rot"][0] = -80 * f
        p["Root"]["loc"][2] = 0.07 * f
        p["Chest"]["rot"][0] += -20 * f
        p["Neck"]["rot"][0] = -20 * f
        p["ShoulderL"]["rot"][0] = lerp(-30, -120, f)
        p["ShoulderR"]["rot"][0] = lerp(-35, -90, f)
        p["ShoulderR"]["rot"][1] = out(-1, 50 * f)
        p["Jaw"]["rot"][0] += 25 * k
        g = keyed(t, [(0, 0), (1.0, 0), (1.8, 1)])
        p["Blood"]["scale"] = [1 + 999 * g] * 3
        return p

    def roar(t):
        p = base(j, king)
        u = keyed(t, [(0, 0), (0.35, 1), (1.15, 1), (1.5, 0)])
        sh = 3 * wave(t, 0.15) * u
        p["ShoulderL"]["rot"] = [lerp(-30, -165, u), out(1, lerp(10, 30, u)), 0]
        p["ShoulderR"]["rot"] = [lerp(-35, -160, u), out(-1, lerp(12, 30, u)), 0]
        p["ElbowL"]["rot"][0] = lerp(-25, -20, u)
        p["ElbowR"]["rot"][0] = lerp(-55, -20, u)
        p["Chest"]["rot"][0] += -18 * u + sh
        p["Neck"]["rot"][0] = -30 * u
        p["Jaw"]["rot"][0] += 30 * u
        return p

    for nm, fn, sec in (("Idle", idle, 3.0), ("Fidget1", fidget1, 3.0), ("Fidget2", fidget2, 3.0),
                        ("Fidget3", fidget3, 3.0), ("Walk", walk, 1.0), ("Attack", attack, 1.2),
                        ("Hit", hit, 0.7), ("Die", die, 1.8), ("Roar", roar, 1.5)):
        record(j, nm, fn, sec)


if __name__ == "__main__":
    make(king=False)
