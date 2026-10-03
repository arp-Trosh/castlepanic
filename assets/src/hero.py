"""Hero: legendary champion in gleaming gold-trimmed steel, open winged helm with a white plume, crimson jointed
cape, a two-handed greatsword."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from knight import slab, dims, set_rot, grip, plate, cape, defender_clips

H = 0.82


def build_hero():
    reset()
    rng = new_rng(23)
    t = save_textures("hero", {
        "steel": tex_metal(rng, (0.72, 0.73, 0.76), rust=0.93, grime=0.4),
        "dark": tex_metal(rng, (0.38, 0.38, 0.41), rust=0.85, grime=0.6),
        "gold": tex_gold(rng, (0.80, 0.62, 0.22)),
        "crimson": tex_cloth(rng, (0.55, 0.06, 0.06), wear=0.6),
        "white": tex_cloth(rng, (0.88, 0.86, 0.80), wear=0.3),
        "skin": tex_skin(rng, (0.60, 0.43, 0.34), warts=0.05, grime=0.35),
        "leather": tex_leather(rng, (0.25, 0.14, 0.07)),
    })
    steel = material("Steel", image=t["steel"], roughness=0.35, metallic=0.4)
    dark = material("Mail", image=t["dark"], roughness=0.5, metallic=0.7)
    gold = material("Gold", image=t["gold"], roughness=0.4, metallic=0.5)
    crimson = material("Crimson", image=t["crimson"], roughness=1.0)
    white = material("Plume", image=t["white"], roughness=1.0)
    skin = material("Skin", image=t["skin"], roughness=0.8)
    leather = material("Leather", image=t["leather"], roughness=0.8)
    d = dims(H, 1.15, 1.1)
    s, w, h = d["s"], d["w"], d["h"]
    j = humanoid({"skin": dark, "body": steel, "legs": dark, "feet": steel}, height=H, girth=1.15, head=1.1)
    for nm in ("Skull", "JawPart", "NeckPart"):
        bpy.data.objects[nm].data.materials[0] = skin

    # stance: wide feet, greatsword upright before the chest in both hands
    set_rot(j["HipL"], (0, -6, 0)); set_rot(j["HipR"], (0, 6, 0))
    set_rot(j["ShoulderR"], (-38, 0, 45)); set_rot(j["ElbowR"], (-58, 0, 0))
    set_rot(j["ShoulderL"], (-38, 0, -45)); set_rot(j["ElbowL"], (-58, 0, 0))

    plate(j, None, d, steel, dark, trim=gold, big_left=False)
    ch, sp, pv = j["Chest"], j["Spine"], j["Pelvis"]
    block("Breast", (w * 2.7, w * 1.85, 0.19 * s), at=(0, -0.006, 0.1 * s), mat=steel, parent=ch,
          taper=(1.12, 1.0), taper_bottom=(0.86, 0.95), flat_shade=True)
    slab("BreastRidge", (0.02 * s, 0.02, 0.15 * s), at=(0, -w * 0.97, 0.09 * s), mat=gold, parent=ch)
    slab("BreastTrim", (w * 2.5, 0.02, 0.025 * s), at=(0, -w * 0.95, 0.18 * s), mat=gold, parent=ch)
    block("Plackart", (w * 2.1, w * 1.75, 0.16 * s), at=(0, -0.004, 0.08 * s), mat=steel, parent=sp,
          taper=(1.1, 1.05), flat_shade=True)
    slab("Belt", (w * 2.2, w * 1.8, 0.035 * s), at=(0, 0, 0.0), mat=gold, parent=sp)
    for k, x in enumerate((-1, 0, 1)):
        slab(f"Fauld{k}", (w * 0.8, 0.025, 0.13 * s), at=(x * w * 0.62, -w * 0.82, -0.07 * s),
              turn=(-8, x * -6, 0), mat=steel, parent=pv, taper_bottom=(1.15, 1))

    # open-faced winged helm with a white plume
    hd = j["Head"]
    piece("sphere", "HelmCap", size=(h * 1.2, h * 1.3, h * 1.0), at=(0, 0.04 * h, h * 0.9), mat=steel, parent=hd,
          verts=10, flat_shade=True)
    piece("cylinder", "HelmBand", size=(h * 1.24, h * 1.34, h * 0.14), at=(0, 0.04 * h, h * 0.66), mat=gold,
          parent=hd, verts=10)
    for sd, side in ((1, "L"), (-1, "R")):
        slab("Cheek" + side, (0.1 * h, 0.7 * h, 0.6 * h), at=(sd * 0.58 * h, -0.05 * h, h * 0.42), mat=steel,
              parent=hd, taper_bottom=(0.8, 0.6), turn=(0, sd * -6, 0))
        wing = pivot("Wing" + side, at=(sd * 0.6 * h, 0.12 * h, h * 0.92), parent=hd)
        for k in range(2):
            L = (0.19 - 0.05 * k) * s
            slab(f"Feather{side}{k}", (0.016 * s, 0.05 * s, L), shape_at=(0, 0, L / 2),
                  turn=(-25 - 30 * k, sd * (35 - 8 * k), 0), mat=steel if k else gold, parent=wing,
                  taper=(0.4, 0.35))
    slab("Nasal", (0.07 * h, 0.06 * h, 0.5 * h), at=(0, -0.66 * h, 0.55 * h), mat=gold, parent=hd,
          taper_bottom=(0.6, 1))
    plume = pivot("PlumeBase", at=(0, 0.1 * h, 1.36 * h), parent=hd)
    piece("cylinder", "PlumeHolder", size=(0.05 * s, 0.05 * s, 0.04 * s), mat=gold, parent=plume, verts=6)
    block("Plume1", (0.045 * s, 0.11 * s, 0.16 * s), shape_at=(0, 0, 0.08 * s), turn=(-25, 0, 0), mat=white,
          parent=plume, taper=(0.7, 0.8), bevel=0.006)
    block("Plume2", (0.04 * s, 0.09 * s, 0.24 * s), at=(0, 0.06 * s, 0.13 * s), shape_at=(0, 0, -0.12 * s),
          turn=(65, 0, 0), mat=white, parent=plume, taper_bottom=(0.35, 0.5), jitter=0.004, bevel=0.005)

    # long crimson cape in three jointed panels
    cj = cape(j, crimson, d, length=0.62, width=w * 3.1)
    for c in cj:
        j[c.name] = c
    block("CapeClasp", (w * 3.0, 0.05, 0.04 * s), at=(0, w * 0.82, 0.18 * s), mat=gold, parent=ch)

    # greatsword, upright in both hands
    wpn = grip("Weapon", j["WristR"], (-6, -24, 0), offset=(0.0, 0, -0.03 * s))
    piece("cylinder", "Grip", size=(0.03, 0.03, 0.17), at=(0, 0, -0.04), mat=leather, parent=wpn, verts=6)
    piece("sphere", "Pommel", size=(0.05, 0.05, 0.05), at=(0, 0, -0.14), mat=gold, parent=wpn, verts=6,
          flat_shade=True)
    slab("Guard", (0.26, 0.03, 0.03), at=(0, 0, 0.055), mat=gold, parent=wpn)
    block("Blade", (0.075, 0.016, 0.6), at=(0, 0, 0.42), mat=steel, parent=wpn, taper=(0.3, 0.7), bevel=0.004)
    slab("Fuller", (0.016, 0.018, 0.4), at=(0, 0, 0.34), mat=dark, parent=wpn, bevel=0.0)

    defender_clips(j, two_handed=True, cape_joints=cj)
    export("hero", j)


if __name__ == "__main__":
    build_hero()
