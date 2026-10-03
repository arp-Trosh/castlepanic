"""Orc Warlord: 1.2x orc in heavy black plate and a horned helm, crimson skull banner on his back, a huge
bone-studded two-handed war axe, trophy skulls on the belt. Body, armour base and clips come from orc.py."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from orc import mats, build, clips, report


def skull(m, name, parent, at, r, turn=(0, 0, 0)):
    p = pivot(name, at=at, turn=turn, parent=parent)
    piece("sphere", name + "Cran", size=(r, r * 1.1, r), at=(0, 0, r * 0.15), mat=m["bone"], parent=p, verts=7)
    block(name + "Jaw", (r * 0.6, r * 0.5, r * 0.35), at=(0, -r * 0.25, -r * 0.35), mat=m["bone"], parent=p)
    for sd in (1, -1):
        piece("sphere", name + "Sock" + str(sd), size=(r * 0.28, r * 0.15, r * 0.25), at=(sd * r * 0.2, -r * 0.48, r * 0.1),
              mat=m["blood"], parent=p, verts=5)
    return p


def war_axe(m, parent, s, name="WarAxe"):
    """Huge two-handed axe: haft along local -Y from the grip, double crescent blades, bone studs."""
    piece("cylinder", name + "Haft", size=(0.045 * s, 0.045 * s, 0.85 * s), at=(0, -0.22 * s, 0), turn=(90, 0, 0),
          mat=m["wood"], parent=parent, verts=6)
    piece("cone", name + "Butt", size=(0.06 * s, 0.06 * s, 0.1 * s), at=(0, 0.22 * s, 0), turn=(-90, 0, 0),
          mat=m["iron"], parent=parent, verts=5)
    for sd, ln in ((-1, 0.27), (1, 0.2)):
        block(name + "Blade" + str(sd), (0.03 * s, 0.19 * s, ln * s), at=(sd * (ln / 2 + 0.01) * s, -0.52 * s, 0),
              mat=m["iron"], parent=parent, taper=(1, 0.55), taper_bottom=(1, 1.6),
              shape_turn=(0, -90 * sd, 0), bevel=0.006 * s)
        block(name + "Edge" + str(sd), (0.03 * s, 0.29 * s * ln / 0.27, 0.022 * s), at=(sd * (ln + 0.015) * s, -0.52 * s, 0),
              mat=m["steel"], parent=parent, bevel=0.004 * s)
    piece("cone", name + "Top", size=(0.06 * s, 0.06 * s, 0.16 * s), at=(0, -0.7 * s, 0), turn=(90, 0, 0),
          mat=m["iron"], parent=parent, verts=5)
    for k, y in enumerate((-0.08, -0.2, -0.32)):
        piece("cone", f"{name}Stud{k}", size=(0.035 * s, 0.035 * s, 0.07 * s), at=(0.03 * s, y * s, 0),
              turn=(0, 90, 0), mat=m["bone"], parent=parent, verts=5)
    skull(m, name + "Skull", parent, (0, -0.4 * s, 0.045 * s), 0.06 * s, turn=(-90, 0, 0))


if __name__ == "__main__":
    reset()
    S = 1.2
    m = mats("orc_warlord", 23)
    j = build("orc_warlord", S, m, warlord=True)
    hd, chest, pel = j["Head"], j["Chest"], j["Pelvis"]
    h = 0.15 * 0.8 * S * 1.4
    # full black horned helm (eyes glow out under the brow)
    piece("sphere", "Helm", size=(h * 1.18, h * 1.22, h * 0.82), at=(0, h * 0.03, h * 0.86), mat=m["iron"],
          parent=hd, verts=8, flat_shade=True)
    piece("cone", "HelmSpike", size=(h * 0.25, h * 0.25, h * 0.45), at=(0, h * 0.05, h * 1.35), mat=m["iron"],
          parent=hd, verts=6)
    block("Nasal", (h * 0.14, h * 0.1, h * 0.45), at=(0, -h * 0.62, h * 0.62), mat=m["iron"], parent=hd,
          taper_bottom=(0.5, 1))
    for sd, side in ((1, "L"), (-1, "R")):
        block("Cheek" + side, (h * 0.18, h * 0.6, h * 0.5), at=(sd * h * 0.5, -h * 0.1, h * 0.42), turn=(0, sd * -8, 0),
              mat=m["iron"], parent=hd, taper_bottom=(0.7, 0.8))
        hp = pivot("Horn" + side, at=(sd * h * 0.52, 0, h * 0.95), turn=(0, sd * 70, 0), parent=hd)
        piece("cylinder", "HornA" + side, size=(h * 0.38, h * 0.38, h * 0.75), shape_at=(0, 0, h * 0.27),
              taper=(0.65, 0.65), mat=m["bone"], parent=hp, verts=6)
        hp2 = pivot("HornTip" + side, at=(0, 0, h * 0.72), turn=(-10, sd * -75, 0), parent=hp)
        piece("cone", "HornB" + side, size=(h * 0.25, h * 0.25, h * 0.8), shape_at=(0, 0, h * 0.4), mat=m["bone"],
              parent=hp2, verts=6)
    # banner pole on the back: crimson flag, skull on top
    bp = pivot("Banner", at=(0.15 * S, 0.2 * S, -0.05 * S), turn=(6, -8, 0), parent=chest)
    piece("cylinder", "Pole", size=(0.03 * S, 0.03 * S, 1.12 * S), shape_at=(0, 0, 0.5 * S), mat=m["wood"],
          parent=bp, verts=6)
    piece("cylinder", "Crossbar", size=(0.022 * S, 0.022 * S, 0.34 * S), at=(0, 0, 0.95 * S), turn=(0, 90, 0),
          mat=m["wood"], parent=bp, verts=6)
    block("Flag", (0.3 * S, 0.015 * S, 0.34 * S), at=(0, 0.01 * S, 0.77 * S), mat=m["cloth"], parent=bp,
          taper_bottom=(0.9, 1), bevel=0.003 * S)
    for k, (x, ln) in enumerate(((-0.1, 0.12), (0.0, 0.07), (0.1, 0.15))):
        block(f"FlagRag{k}", (0.09 * S, 0.014 * S, ln * S), at=(x * S, 0.01 * S, (0.6 - ln / 2) * S),
              turn=(0, k * 6 - 6, 0), mat=m["cloth"], parent=bp, taper_bottom=(0.4, 1), bevel=0.003 * S)
    skull(m, "PoleSkull", bp, (0, 0, 1.1 * S), 0.11 * S)
    # trophy skulls on the belt
    for k, (x, y, z, r) in enumerate(((0.17, -0.06, -0.06, 0.07), (-0.17, -0.05, -0.07, 0.065), (0.12, 0.1, -0.08, 0.06))):
        skull(m, f"Trophy{k}", pel, (x * S, y * S, z * S), r * S, turn=(10, 0, x * 60))
    war_axe(m, j["Weapon"], S)
    war_axe(m, j["Severed"], S, "SevAxe")
    # two-handed grip: left hand reaches over to the haft
    j["ShoulderL"].rotation_euler = (math.radians(-35), math.radians(35), 0)
    j["ElbowL"].rotation_euler = (math.radians(-60), 0, 0)
    report(j)
    clips(j, S, two_hand=True)
    export("orc_warlord", j)
