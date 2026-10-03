"""Troll Mage: a bigger hooded troll with a skull necklace and a glowing crystal staff (shares troll.py's build)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from kit import _apply
import troll

j, M, s = troll.build("troll_mage", 1.35 * 1.2, mage=True)
robe, bone, gold = M["Robe".lower()], M["bone"], M["gold"]
rune = material("Rune", (0.2, 0.9, 0.7), emission=(0.15, 1.0, 0.7), strength=3.0)
crys = material("Crystal", (0.25, 1.0, 0.75), emission=(0.2, 1.0, 0.7), strength=6.0, roughness=0.2)
w = 0.13 * s * 1.55
h = 0.15 * s * 1.15
# hood over the head, point drooping back
hd = j["Head"]
piece("sphere", "Hood", size=(h * 1.4, h * 1.35, h * 1.4), at=(0, h * 0.32, h * 0.62), mat=robe, parent=hd, verts=8,
      jitter=0.01)
piece("cone", "HoodTip", size=(h * 0.9, h * 0.9, h * 0.9), at=(0, h * 0.75, h * 0.95), turn=(110, 0, 8), mat=robe,
      parent=hd, verts=7)
# robe skirt hanging from the pelvis, ragged hem
pv = j["Pelvis"]
L = 0.36 * s
piece("cylinder", "Skirt", size=(w * 2.4, w * 1.9, L), shape_at=(0, 0, -L / 2 + 0.04 * s), taper_bottom=(1.35, 1.4),
      mat=robe, parent=pv, verts=9, jitter=0.006)
rng = new_rng(5)
for k in range(7):
    a = 2 * math.pi * k / 7 + 0.3
    piece("cube", f"Hem{k}", size=(w * 0.5, 0.02 * s, rng.uniform(0.05, 0.11) * s),
          at=(math.sin(a) * w * 1.55, -math.cos(a) * w * 1.25, -L + 0.02 * s), turn=(0, 0, -math.degrees(a)),
          mat=robe, parent=pv)
# runes glowing on the robe front and back
for k, (x, z) in enumerate(((-0.05, -0.12), (0.06, -0.2), (-0.02, -0.3))):
    piece("cube", f"Rune{k}", size=(0.035 * s, 0.01 * s, 0.07 * s), at=(x * s, -w * 1.3 - 0.02 * s * (k == 2), z * s),
          turn=(0, 25 * (k - 1), 0), mat=rune, parent=pv)
# necklace of skulls on the chest
ch = j["Chest"]
piece("torus", "Cord", size=(w * 2.0, w * 1.75, 0.4), at=(0, -0.01 * s, 0.17 * s), turn=(-20, 0, 0), mat=M["rope"],
      parent=ch)
for k in range(5):
    x = (k - 2) / 2
    z = 0.13 * s - 0.04 * s * (1 - x * x)
    sk = piece("sphere", f"Skull{k}", size=(0.06 * s, 0.055 * s, 0.065 * s),
               at=(x * w * 0.75, -w * 0.98 - 0.01 * s * (1 - x * x), z), mat=bone, parent=ch, verts=6)
    piece("cube", f"SkullEye{k}", size=(0.04 * s, 0.01 * s, 0.012 * s), at=(0, -0.027 * s, 0.005 * s), mat=M["moss"],
          parent=sk)
# gnarled staff with a glowing crystal, held aloft
wpn = j["Weapon"]
SL = 0.82 * s
piece("cylinder", "Staff", size=(0.04 * s, 0.04 * s, SL), shape_at=(0, 0, SL / 2 - 0.3 * s), taper=(0.8, 0.8),
      mat=M["wood"], parent=wpn, verts=6, jitter=0.006, flat_shade=True)
top = SL - 0.3 * s
for k in range(3):
    piece("cone", f"Claw{k}", size=(0.035 * s, 0.035 * s, 0.16 * s), at=(0, 0, top), turn=(25, 0, 120 * k),
          shape_at=(0, 0, 0.08 * s), mat=bone, parent=wpn, verts=5)
piece("torus", "Band", size=(0.08 * s, 0.08 * s, 0.5), at=(0, 0, top - 0.03 * s), mat=gold, parent=wpn)
cr = piece("ico", "Crystal", size=(0.09 * s, 0.09 * s, 0.2 * s), at=(0, 0, top + 0.1 * s), mat=crys, parent=wpn,
           flat_shade=True)
for k in range(3):
    piece("cube", f"StaffRune{k}", size=(0.045 * s, 0.045 * s, 0.015 * s), at=(0, 0, top - 0.12 * s - 0.08 * s * k),
          turn=(0, 0, 30 * k), mat=rune, parent=wpn)

rest = troll.clips(j, s, mage=True)
_apply(j, rest); troll.report_height()
export("troll_mage", j, rest)
