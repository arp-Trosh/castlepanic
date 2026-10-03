import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
from kit import *
from kit import _base, noise, smoothstep, mix, disc, N
import numpy as np

ONLY = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def cracks(rng, img, amount=0.8, beta=1.7):
    n = noise(rng, beta)
    line = 1 - np.clip(np.abs(n - 0.5) / 0.012, 0, 1)
    return mix(img, [0.03, 0.03, 0.03], line * amount)


def lichen(rng, img, count=40, color=(0.55, 0.58, 0.42), amt=0.8):
    m = np.zeros((N, N))
    for _ in range(count):
        disc(m, *rng.uniform(0, N, 2), rng.uniform(2, 7))
    m = m.clip(0, 1) * smoothstep(0.3, 0.7, noise(rng, 0.8))
    return mix(img, color, m * amt)


def tex_granite(rng, color=(0.36, 0.35, 0.34), moss=0.6):
    img = tex_stone(rng, color, moss=moss, blocks=False, soot=0.3)
    img *= (0.85 + 0.3 * noise(rng, 0.5))[..., None]  # speckle
    img = cracks(rng, img)
    return lichen(rng, img)


def tex_bark(rng, color=(0.2, 0.17, 0.14)):
    img = _base(rng, color, 0.4, 1.6)
    grain = noise(rng, 1.0, stretch=(14, 1))
    img *= (0.45 + 0.9 * grain)[..., None]
    img = lichen(rng, img, 15, (0.4, 0.44, 0.34), 0.5)
    return img


def tex_leaves(rng, color, rust=None):
    img = _base(rng, color, 0.6, 1.2)
    img *= (0.55 + 0.7 * noise(rng, 0.6))[..., None]
    if rust is not None:
        img = mix(img, rust, smoothstep(0.6, 0.8, noise(rng, 1.8)) * 0.7)
    return img


def seg(name, length, r0, r1, mat, parent, at=(0, 0, 0), turn=(0, 0, 0), jitter=0.06, verts=7):
    """A pivot at the base and a tapered, gnarled cylinder growing UP (+Z) from it."""
    p = pivot(name, at=at, turn=turn, parent=parent)
    piece("cylinder", name + "Wood", size=(2 * r0, 2 * r0, length), shape_at=(0, 0, length / 2), parent=p,
          mat=mat, taper=(r1 / r0, r1 / r0), verts=verts, jitter=jitter, flat_shade=True)
    return p


def sway_clip(j, amp, period=4.0):
    """j: {name: (axis-amplitude scale, phase)}."""
    names = list(j)
    def fn(t):
        p = rest_pose(j)
        for i, n in enumerate(names):
            a = amp * (1 + 0.6 * (i % 3) / 2)
            p[n]["rot"][0] = a * wave(t, period, 0.13 * i)
            p[n]["rot"][1] = 0.7 * a * wave(t, period / 2 if i % 2 else period, 0.3 + 0.21 * i)
        return p
    return fn


def start(name, seed):
    reset()
    kit._REST.clear()
    return new_rng(seed)


# ------------------------------------------------------------------------------------------------ boulder
def boulder():
    rng = start("boulder", 11)
    t = save_textures("boulder", {"stone": tex_granite(rng)})
    m = material("Granite", image=t["stone"], roughness=0.95)
    piece("ico", "Boulder", size=(1.0, 0.92, 0.88), at=(0, 0, 0.44), mat=m, verts=3, jitter=0.04, flat_shade=True,
          tile=0.6)
    export("boulder")


# ------------------------------------------------------------------------------------------------ rocks
def rocks():
    rng = start("rocks", 12)
    t = save_textures("rocks", {"stone": tex_granite(rng, (0.33, 0.33, 0.31), moss=1.0)})
    m = material("MossStone", image=t["stone"], roughness=0.95)
    for i, (x, y, s, h) in enumerate([(-0.1, 0.05, 0.32, 0.22), (0.15, -0.08, 0.22, 0.15), (0.12, 0.17, 0.18, 0.12),
                                      (-0.18, -0.16, 0.14, 0.09), (0.02, -0.22, 0.1, 0.07)]):
        piece("ico", f"Rock{i}", size=(s, s * 0.85, h), at=(x, y, h * 0.4), turn=(0, 0, 37 * i), mat=m, verts=2,
              jitter=0.07, flat_shade=True, tile=0.3)
    export("rocks")


# ------------------------------------------------------------------------------------------------ tar
def tar():
    rng = start("tar", 13)
    pool = material("Tar", (0.012, 0.011, 0.01), roughness=0.08, metallic=0.0)
    crust = material("TarCrust", (0.05, 0.045, 0.04), roughness=0.5)
    piece("cylinder", "Pool", size=(0.6, 0.5, 0.02), at=(0, 0, 0.01), mat=pool, verts=14, jitter=0.06)
    piece("cylinder", "Lobe", size=(0.28, 0.24, 0.016), at=(0.24, 0.12, 0.008), mat=pool, verts=9, jitter=0.08)
    piece("cylinder", "Rim", size=(0.66, 0.56, 0.01), at=(0, 0, 0.005), mat=crust, verts=14, jitter=0.07)
    j = {}
    for i, (x, y, s) in enumerate([(-0.1, 0.05, 0.09), (0.12, -0.06, 0.06), (0.03, 0.15, 0.045)]):
        p = j[f"Bubble{i}"] = pivot(f"Bubble{i}", at=(x, y, 0.018))
        piece("sphere", f"BubblePart{i}", size=(s, s, s * 0.8), mat=pool, parent=p, verts=8)

    def bubble(t):
        p = rest_pose(j)
        for i, n in enumerate(j):
            u = (t / 2.0 + i * 0.37) % 1.0  # swell to 0.8, pop
            k = smooth(u / 0.8) if u < 0.8 else max(0.001, 1 - (u - 0.8) / 0.05) if u < 0.85 else 0.001
            k = max(k, 0.001)
            p[n]["scale"] = [k * (1 + 0.15 * k), k * (1 + 0.15 * k), k]
        return p
    record(j, "Bubble", bubble, 2.0)
    export("tar", j)


# ------------------------------------------------------------------------------------------------ dead tree
def tree_dead():
    rng = start("tree_dead", 14)
    t = save_textures("tree_dead", {"bark": tex_bark(rng, (0.36, 0.32, 0.28))})
    b = material("DeadBark", image=t["bark"], roughness=1.0)
    j = {}
    root = pivot("Root")
    piece("cone", "Roots", size=(0.42, 0.36, 0.25), at=(0, 0, 0.1), mat=b, parent=root, verts=7, jitter=0.08,
          flat_shade=True)
    t1 = seg("Trunk1", 0.6, 0.14, 0.1, b, root, turn=(6, -5, 0))
    t2 = j["Trunk2"] = seg("Trunk2", 0.5, 0.1, 0.07, b, t1, at=(0, 0, 0.58), turn=(-14, 10, 25))
    t3 = j["Trunk3"] = seg("Trunk3", 0.42, 0.07, 0.035, b, t2, at=(0, 0, 0.48), turn=(18, -12, -30))
    # bare clawing limbs: (parent, at z, turn, length, r0, twig turn)
    specs = [(t1, 0.45, (0, 62, 20), 0.48, 0.05, (0, -40, 0)),
             (t1, 0.5, (-58, -20, 0), 0.4, 0.045, (35, 0, 20)),
             (t2, 0.35, (0, -60, -15), 0.5, 0.042, (0, 45, 0)),
             (t2, 0.45, (55, 15, 0), 0.38, 0.035, (-40, 0, 0)),
             (t3, 0.3, (0, 50, 30), 0.3, 0.025, (0, -45, 0)),
             (t3, 0.38, (-40, -30, 0), 0.26, 0.022, (30, 20, 0))]
    for i, (par, z, turn, L, r, tw) in enumerate(specs):
        br = j[f"Branch{i}"] = seg(f"Branch{i}", L, r * 1.5, r * 0.6, b, par, at=(0, 0, z), turn=turn, jitter=0.08)
        tg = j[f"Twig{i}"] = seg(f"Twig{i}", L * 0.6, r * 0.6, 0.006, b, br, at=(0, 0, L * 0.95), turn=tw,
                                 verts=5, jitter=0.05)
        seg(f"Claw{i}", L * 0.35, r * 0.3, 0.003, b, br, at=(0, 0, L * 0.6), turn=(tw[1] * -0.8, tw[0] * 0.8, 40),
            verts=5, jitter=0.04)
    record(j, "Idle", sway_clip(j, 2.2), 4.0)
    export("tree_dead", j)


# ------------------------------------------------------------------------------------------------ pine
def tree_pine():
    rng = start("tree_pine", 15)
    t = save_textures("tree_pine", {"bark": tex_bark(rng, (0.34, 0.26, 0.2)),
                                    "needles": tex_leaves(rng, (0.11, 0.2, 0.17), rust=(0.3, 0.22, 0.1))})
    b = material("PineBark", image=t["bark"], roughness=1.0)
    nd = material("Needles", image=t["needles"], roughness=0.95)
    j = {}
    root = pivot("Root", turn=(5, -3, 0))
    seg("Trunk", 1.9, 0.1, 0.02, b, root, jitter=0.05)
    tiers = [(0.5, 1.0, 0.42), (0.8, 0.8, 0.4), (1.07, 0.64, 0.38), (1.32, 0.5, 0.36), (1.55, 0.36, 0.34),
             (1.78, 0.22, 0.32)]
    prev = root
    for i, (z, w, h) in enumerate(tiers):
        p = j[f"Tier{i}"] = pivot(f"Tier{i}", at=(0, 0, z - (tiers[i - 1][0] if i else 0)), parent=prev)
        piece("cone", f"Needles{i}", size=(w * 1.25, w * 1.15, h), shape_at=(0, 0, h * 0.3), turn=(0, 0, 23 * i),
              mat=nd, parent=p, verts=11, jitter=0.1, taper_bottom=(1, 1), squash_bottom=1.6, flat_shade=True,
              tile=0.3)
        prev = p
    record(j, "Idle", sway_clip(j, 1.0), 4.0)
    export("tree_pine", j)


# ------------------------------------------------------------------------------------------------ oak
def tree_oak():
    rng = start("tree_oak", 16)
    t = save_textures("tree_oak", {"bark": tex_bark(rng, (0.38, 0.31, 0.24)),
                                   "leaves": tex_leaves(rng, (0.22, 0.29, 0.12), rust=(0.48, 0.27, 0.08))})
    b = material("OakBark", image=t["bark"], roughness=1.0)
    lf = material("OakLeaves", image=t["leaves"], roughness=0.95)
    j = {}
    root = pivot("Root")
    piece("cylinder", "Trunk", size=(0.32, 0.3, 0.75), shape_at=(0, 0, 0.375), parent=root, mat=b, verts=8,
          taper=(0.7, 0.7), taper_bottom=(1.5, 1.5), jitter=0.07, flat_shade=True)
    for i, (turn, L) in enumerate([((0, 48, 10), 0.45), ((-45, -25, 0), 0.42), ((40, -40, 0), 0.38)]):
        seg(f"Bough{i}", L, 0.07, 0.035, b, root, at=(0, 0, 0.62), turn=turn, jitter=0.07)
    blobs = [((0.0, 0.0, 1.15), 0.95, 0.6), ((0.45, 0.05, 0.9), 0.6, 0.48), ((-0.42, -0.12, 0.95), 0.62, 0.5),
             ((0.05, 0.4, 0.98), 0.55, 0.45), ((-0.08, -0.25, 1.3), 0.5, 0.4)]
    for i, (at, w, h) in enumerate(blobs):
        p = j[f"Canopy{i}"] = pivot(f"Canopy{i}", at=(at[0] * 0.3, at[1] * 0.3, 0.7), parent=root)
        piece("ico", f"Leaves{i}", size=(w, w * 0.9, h), at=(at[0] * 0.7, at[1] * 0.7, at[2] - 0.7), mat=lf,
              parent=p, verts=2, jitter=0.07, flat_shade=True, tile=0.35)
    record(j, "Idle", sway_clip(j, 1.2), 4.0)
    export("tree_oak", j)


for fn in (boulder, rocks, tar, tree_dead, tree_pine, tree_oak):
    if not ONLY or fn.__name__ in ONLY:
        fn()
