"""Shared Blender helpers for Castle Panic's models: procedural textures, materials, bevelled parts, a jointed
humanoid, pose recording into named clips, and glTF export. Every model script imports this:

    import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from kit import *

and is run headless:  blender -b --python assets/src/goblin.py   (writes assets/models/goblin.glb)

Conventions (read assets/STYLE.md too):
- Blender units are the game's world units. Z is up, the model stands on Z=0 at the origin and FACES -Y
  (the exporter turns that into glTF +Z, which the game treats as "forward").
- Everything moves by nodes (pivots); no armatures, skinning or shape keys (unicode3d won't play them).
- Each clip keys EVERY joint on every frame (record() does this), so switching clips never leaves a part stuck.
- Loops close: a looping clip's last frame equals its first. One-shot clips (Attack, Hit) start and end at the
  idle pose (frame 0 of Idle) so the game can blend back; Die ends in its final pose.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(os.path.dirname(ROOT), "castlepanic", "data", "models")
TEXDIR = os.path.join(ROOT, "build", "textures")
FPS = 24
N = 256  # texture size: terminals show few pixels, keep the .glb small

__all__ = ["bpy", "math", "np", "Vector", "Matrix", "Euler", "FPS", "N", "MODELS", "noise", "blur", "smoothstep",
           "mix", "disc", "scratches", "blood_mask", "paint_blood", "tex_skin", "tex_cloth", "tex_leather",
           "tex_metal", "tex_stone", "tex_wood", "tex_fur", "tex_bone", "tex_gold", "save_textures", "material",
           "flat", "piece", "block", "limb", "pivot", "place", "reset", "humanoid", "rest_pose", "record",
           "export", "smooth", "keyed", "wave", "out", "lerp", "new_rng"]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS


def new_rng(seed):
    return np.random.default_rng(seed)


# ================================================================================================ textures
# All tileable, (N, N, 3) floats 0..1 in sRGB. Paint like a miniature: a mid tone, dark recesses (grime), light
# edges (chips, scratches), and one or two accents. Keep contrast strong: terminal pixels average fine detail away.

def noise(rng, beta, stretch=(1.0, 1.0)):
    """Tileable fractal noise in 0..1; beta ~0.6 is fine grain, ~2.2 broad mottling."""
    ky, kx = np.meshgrid(np.fft.fftfreq(N), np.fft.fftfreq(N), indexing="ij")
    f = np.sqrt((kx / stretch[1]) ** 2 + (ky / stretch[0]) ** 2)
    f[0, 0] = 1.0
    spec = (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) / f ** beta
    spec[0, 0] = 0.0
    a = np.real(np.fft.ifft2(spec))
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    return np.clip((a - lo) / (hi - lo), 0, 1)


def blur(a, sigma):
    ky, kx = np.meshgrid(np.fft.fftfreq(N), np.fft.fftfreq(N), indexing="ij")
    g = np.exp(-2 * (math.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(img, color, amount):
    amount = np.asarray(amount)[..., None] if np.ndim(amount) else amount
    return img * (1 - amount) + np.asarray(color) * amount


def disc(mask, cx, cy, r, value=1.0, sy=1.0):
    """Paint a soft disc into mask, wrapping round the edges."""
    ext = int(r * max(1, sy)) + 2
    ys = np.arange(int(cy) - ext, int(cy) + ext + 1)
    xs = np.arange(int(cx) - ext, int(cx) + ext + 1)
    dy, dx = np.meshgrid((ys - cy) / sy, xs - cx, indexing="ij")
    d = np.sqrt(dx * dx + dy * dy)
    a = np.clip(r - d + 0.5, 0, 1) * value
    sub = np.ix_(ys % N, xs % N)
    mask[sub] = np.maximum(mask[sub], a)


def scratches(rng, count, length, angle=None, spread=math.pi):
    m = np.zeros((N, N))
    for _ in range(count):
        x, y = rng.uniform(0, N, 2)
        a = rng.uniform(0, 2 * math.pi) if angle is None else angle + rng.normal(0, spread)
        n = int(rng.uniform(*length))
        for i in range(n):
            x, y = x + math.cos(a), y + math.sin(a)
            m[int(y) % N, int(x) % N] = max(m[int(y) % N, int(x) % N], 1 - i / (n * 1.4))
    return m


def blood_mask(rng, count, size=(3, 11), drips=True):
    m = np.zeros((N, N))
    for _ in range(count):
        cx, cy = rng.uniform(0, N, 2)
        r0 = rng.uniform(*size)
        for _ in range(6):
            disc(m, cx + rng.normal(0, r0 * 0.45), cy + rng.normal(0, r0 * 0.45), r0 * rng.uniform(0.3, 0.75))
        a = rng.uniform(0, 2 * math.pi)
        for _ in range(int(r0 * 2)):
            d = r0 * rng.uniform(1.0, 4.0)
            b = a + rng.normal(0, 0.35)
            disc(m, cx + d * math.cos(b), cy + d * math.sin(b), rng.uniform(0.5, 1.6))
        if drips:
            for _ in range(rng.integers(1, 3)):
                x, y, w = cx + rng.normal(0, r0 * 0.5), cy - r0 * 0.3, rng.uniform(0.8, 1.6)
                for k in range(int(rng.uniform(8, 50))):
                    disc(m, x, y - k, w * (1 - k / 80))
    return np.clip(m, 0, 1)


def paint_blood(rng, img, mask, fresh=0.5):
    depth = blur(mask, 1.0) * (0.7 + 0.3 * noise(rng, 1.0))
    col = mix(np.array([0.12, 0.01, 0.01]) + 0 * img, [0.32 + 0.1 * fresh, 0.02, 0.015], smoothstep(0.3, 1, depth))
    return mix(img, col, np.clip(mask * 1.2, 0, 1))


def _base(rng, color, mottle=0.4, beta=2.0):
    img = np.ones((N, N, 3)) * np.asarray(color, float)
    img *= (1 - mottle / 2 + mottle * noise(rng, beta))[..., None]
    img *= (0.93 + 0.14 * noise(rng, 0.7))[..., None]
    return img


def tex_skin(rng, color, warts=0.5, veins=0.0, grime=0.5):
    """Monster hide: mottled, warty, darker in the folds."""
    img = _base(rng, color, 0.5, 2.0)
    img = mix(img, np.asarray(color) * 0.45, smoothstep(0.55, 0.9, noise(rng, 1.6)) * grime)
    w = np.zeros((N, N))
    for _ in range(int(220 * warts)):
        disc(w, *rng.uniform(0, N, 2), rng.uniform(0.8, 2.6), rng.uniform(0.5, 1.0))
    img = mix(img, np.minimum(np.asarray(color) * 1.35 + 0.05, 1), w * 0.55)
    img = mix(img, np.asarray(color) * 0.3, (blur(w, 1.2) - w).clip(0, 1) * 2.0)
    if veins:
        img = mix(img, [0.25, 0.08, 0.1], scratches(rng, int(60 * veins), (10, 50)) * 0.5)
    return img


def tex_cloth(rng, color, wear=0.5):
    """Coarse woven cloth: a weave, stains, frayed holes darker."""
    img = _base(rng, color, 0.35, 1.8)
    yy, xx = np.mgrid[0:N, 0:N]
    weave = 0.5 + 0.5 * np.sin(xx * 1.6) * np.sin(yy * 1.6)
    img *= (0.85 + 0.25 * weave)[..., None]
    img = mix(img, [0.08, 0.06, 0.04], smoothstep(0.6, 0.9, noise(rng, 1.5)) * 0.7 * wear)
    return img


def tex_leather(rng, color):
    img = _base(rng, color, 0.45, 1.9)
    img = mix(img, np.asarray(color) * 1.6, scratches(rng, 80, (5, 25)) * 0.4)
    img = mix(img, [0.05, 0.03, 0.02], smoothstep(0.62, 0.9, noise(rng, 1.4)) * 0.6)
    return img


def tex_metal(rng, color, rust=0.75, grime=0.6):
    """Worn iron or steel: oil and soot, rust blooms (rust < 1 means more), bright scratches."""
    img = _base(rng, color, 0.35, 2.0)
    img = mix(img, [0.04, 0.035, 0.03], smoothstep(0.5, 0.85, noise(rng, 1.5)) * grime)
    r = noise(rng, 1.7)
    img = mix(img, [0.4, 0.17, 0.06], smoothstep(rust, rust + 0.1, r) * (0.6 + 0.4 * noise(rng, 0.6)))
    img = mix(img, np.minimum(np.asarray(color) * 1.8 + 0.15, 1), scratches(rng, 140, (4, 30)) * 0.8)
    return img


def tex_stone(rng, color, moss=0.3, blocks=True, soot=0.4):
    """Castle masonry: courses of blocks with dark mortar, pitting, moss low down, soot streaks."""
    img = _base(rng, color, 0.45, 1.8)
    if blocks:
        yy, xx = np.mgrid[0:N, 0:N]
        rows = 8
        h = N // rows
        off = (yy // h) % 2 * (N // 8)
        mortar = ((yy % h) < 3) | (((xx + off) % (N // 4)) < 3)
        img = mix(img, np.asarray(color) * 0.3, blur(mortar.astype(float), 0.6).clip(0, 1) * 0.85)
        per_block = noise(rng, 0.3)
        img *= (0.8 + 0.35 * per_block[(yy // h) * h, ((xx + off) // (N // 4) * (N // 4)) % N])[..., None]
    pits = np.zeros((N, N))
    for _ in range(250):
        disc(pits, *rng.uniform(0, N, 2), rng.uniform(0.5, 1.8))
    img = mix(img, np.asarray(color) * 0.35, pits * 0.7)
    img = mix(img, [0.18, 0.24, 0.1], smoothstep(0.6, 0.85, noise(rng, 1.6)) * moss)
    img = mix(img, [0.04, 0.04, 0.045], smoothstep(0.55, 0.9, noise(rng, 1.4, stretch=(1, 6))) * soot)
    return img


def tex_wood(rng, color):
    """Rough planks: grain running along v, knots, weathering."""
    img = _base(rng, color, 0.3, 1.5)
    grain = noise(rng, 1.2, stretch=(12, 1))
    img *= (0.7 + 0.5 * grain)[..., None]
    k = np.zeros((N, N))
    for _ in range(6):
        disc(k, *rng.uniform(0, N, 2), rng.uniform(2, 5), sy=1.8)
    img = mix(img, np.asarray(color) * 0.35, k * 0.8)
    img = mix(img, [0.35, 0.33, 0.3], smoothstep(0.65, 0.9, noise(rng, 1.4)) * 0.35)
    return img


def tex_fur(rng, color):
    img = _base(rng, color, 0.4, 1.6)
    strands = noise(rng, 0.5, stretch=(8, 1))
    img *= (0.55 + 0.7 * strands)[..., None]
    return img


def tex_bone(rng, color=(0.74, 0.69, 0.56)):
    img = _base(rng, color, 0.35, 1.8)
    img = mix(img, [0.22, 0.17, 0.1], smoothstep(0.62, 0.9, noise(rng, 1.3)) * 0.8)
    img = mix(img, [0.1, 0.08, 0.05], scratches(rng, 40, (8, 40)) * 0.7)
    return img


def tex_gold(rng, color=(0.75, 0.55, 0.18)):
    img = _base(rng, color, 0.4, 1.9)
    img = mix(img, [0.2, 0.14, 0.05], smoothstep(0.55, 0.85, noise(rng, 1.5)) * 0.7)
    img = mix(img, [1.0, 0.9, 0.6], scratches(rng, 80, (4, 20)) * 0.6)
    return img


def save_textures(model, textures):
    """{name: (N, N, 3) array} -> {name: bpy image}, written as PNGs (embedded into the .glb on export)."""
    folder = os.path.join(TEXDIR, model)
    os.makedirs(folder, exist_ok=True)
    out = {}
    for name, img in textures.items():
        path = os.path.join(folder, name + ".png")
        im = bpy.data.images.new(f"{model}_{name}", N, N)
        rgba = np.concatenate([np.clip(img, 0, 1), np.ones((N, N, 1))], axis=2).astype(np.float32)
        im.pixels.foreach_set(rgba.ravel())
        im.filepath_raw = path
        im.file_format = "PNG"
        im.save()
        out[name] = im
    return out


# ================================================================================================ materials

def material(name, color=(1, 1, 1), image=None, roughness=0.6, metallic=0.0, emission=None, strength=1.0):
    """A glTF material: base colour or a texture (then color is ignored), roughness, metal, glow."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    mat.use_backface_culling = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if image is not None:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def flat(name, color, **kw):
    return material(name, color, **kw)


# ================================================================================================ parts

ADD = {
    "cube": lambda: bpy.ops.mesh.primitive_cube_add(size=1),
    "cylinder": lambda v=10: bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=0.5, depth=1),
    "cone": lambda v=10: bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=0.5, depth=1),
    "sphere": lambda v=10: bpy.ops.mesh.primitive_uv_sphere_add(segments=v, ring_count=max(4, v // 2 + 1),
                                                                 radius=0.5),
    "ico": lambda v=1: bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=v, radius=0.5),
    "torus": lambda v=16: bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.08,
                                                           major_segments=v, minor_segments=6),
}

_RNG = np.random.default_rng(7)


def _boxmap(mesh, tile):
    uv = mesh.uv_layers.active or mesh.uv_layers.new(name="UVMap")
    off = _RNG.uniform(0, 1, 2)
    for poly in mesh.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = ((1, 2), (0, 2), (0, 1))[ax]
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv = (co[a] / tile + off[0], co[b] / tile + off[1])


def place(obj, at=(0, 0, 0), turn=(0, 0, 0), parent=None):
    obj.parent = parent
    obj.location = at
    obj.rotation_euler = [math.radians(d) for d in turn]


def pivot(name, at=(0, 0, 0), turn=(0, 0, 0), parent=None):
    """An empty node: a joint that turns or moves what hangs from it."""
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    place(obj, at, turn, parent)
    return obj


def piece(kind, name, size=(1, 1, 1), at=(0, 0, 0), turn=(0, 0, 0), mat=None, parent=None, shape_turn=(0, 0, 0),
          shape_at=(0, 0, 0), bevel=0.0, taper=(1, 1), taper_bottom=(1, 1), squash_bottom=1.0, sharp=35, tile=0.5,
          verts=None, jitter=0.0, flat_shade=False):
    """A mesh part. kind: cube, cylinder, cone, sphere, ico, torus. `size` (x, y, z) and the taper (top, z > 0, and
    bottom, z < 0, scaled in x, y) are baked into the mesh before shape_turn/shape_at; `at`/`turn` (degrees) place
    the node under its parent. verts: segment count for round kinds (keep it low: 6-10, it's low-poly). jitter
    displaces vertices randomly (a fraction of the size) for rough rock, gnarled wood, lumpy hide. flat_shade gives
    faceted low-poly faces."""
    if verts is not None and kind != "cube":
        ADD[kind](verts)
    else:
        ADD[kind]()
    obj = bpy.context.active_object
    obj.name = obj.data.name = name
    me = obj.data
    for v in me.vertices:
        if v.co.z > 1e-6:
            v.co.x *= taper[0]
            v.co.y *= taper[1]
        elif v.co.z < -1e-6:
            v.co.x *= taper_bottom[0]
            v.co.y *= taper_bottom[1]
            v.co.z *= squash_bottom
    if jitter:
        for v in me.vertices:
            v.co += Vector(_RNG.normal(0, jitter, 3))
    turn_m = Matrix.Identity(4)
    for axis, deg in zip("XYZ", shape_turn):
        turn_m = Matrix.Rotation(math.radians(deg), 4, axis) @ turn_m
    me.transform(Matrix.Translation(shape_at) @ turn_m @ Matrix.Diagonal((*size, 1)))
    bm = bmesh.new()
    bm.from_mesh(me)
    if bevel:
        edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(sharp)]
        if edges:
            bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect="EDGES", profile=0.5,
                            clamp_overlap=True)
    for f in bm.faces:
        f.smooth = not flat_shade
    for e in bm.edges:
        if not e.is_manifold or e.calc_face_angle(0) > math.radians(sharp):
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    _boxmap(me, tile)
    if mat:
        me.materials.append(mat)
    place(obj, at, turn, parent)
    return obj


def block(name, size, **kw):
    """A bevelled box."""
    kw.setdefault("bevel", min(size) * 0.15)
    return piece("cube", name, size=size, **kw)


def limb(name, length, r_top, r_bottom, mat, parent, at=(0, 0, 0), verts=8, **kw):
    """A tapered segment hanging DOWN (-Z) from its node: an upper arm, a shin, a finger."""
    return piece("cylinder", name, size=(2 * r_top, 2 * r_top, length), at=at, mat=mat, parent=parent,
                 shape_at=(0, 0, -length / 2), taper_bottom=(r_bottom / r_top, r_bottom / r_top), verts=verts, **kw)


# ================================================================================================ a humanoid

def humanoid(m, height=1.0, hunch=0.0, girth=1.0, arm=1.0, leg=1.0, head=1.0, prefix=""):
    """A jointed body of low-poly parts, standing on Z=0, facing -Y, about `height` tall. m: materials dict with
    "skin", "body" (torso cover), "legs", "feet" (any may repeat). Proportions: girth widens, arm/leg lengthen,
    head scales the head, hunch (0..1) bends the spine forward (goblins 0.4, trolls 0.6).

    Returns {joint: node}: Root, Pelvis, Spine, Chest, Neck, Head, Jaw, ShoulderL/R, ElbowL/R, WristL/R (hands:
    hold things at the wrist node, -Z is down the hand), HipL/R, KneeL/R, AnkleL/R. L is +X (the model's left)."""
    s = height / 1.0
    j = {}
    leg_len = 0.46 * s * leg
    thigh, shin = leg_len * 0.52, leg_len * 0.48
    hip_z = leg_len + 0.04 * s
    j["Root"] = root = pivot(prefix + "Root")
    j["Pelvis"] = pelvis = pivot(prefix + "Pelvis", at=(0, 0, hip_z), parent=root)
    w = 0.13 * s * girth
    block(prefix + "Hips", (w * 2.2, w * 1.5, 0.12 * s), at=(0, 0, 0.0), mat=m["legs"], parent=pelvis)
    j["Spine"] = spine = pivot(prefix + "Spine", at=(0, 0, 0.05 * s), turn=(-25 * hunch, 0, 0), parent=pelvis)
    block(prefix + "Belly", (w * 2.0, w * 1.6, 0.16 * s), at=(0, 0, 0.08 * s), mat=m["body"], parent=spine,
          taper=(1.1, 1.05))
    j["Chest"] = chest = pivot(prefix + "Chest", at=(0, 0, 0.16 * s), turn=(-20 * hunch, 0, 0), parent=spine)
    block(prefix + "Torso", (w * 2.6, w * 1.7, 0.2 * s), at=(0, 0, 0.1 * s), mat=m["body"], parent=chest,
          taper=(1.15, 1.0), taper_bottom=(0.85, 0.9))
    j["Neck"] = neck = pivot(prefix + "Neck", at=(0, -0.02 * s * hunch, 0.21 * s), turn=(35 * hunch, 0, 0),
                             parent=chest)
    piece("cylinder", prefix + "NeckPart", size=(0.08 * s * girth, 0.08 * s * girth, 0.07 * s), at=(0, 0, 0.02 * s),
          mat=m["skin"], parent=neck, verts=6)
    j["Head"] = hd = pivot(prefix + "Head", at=(0, 0, 0.05 * s), parent=neck)
    h = 0.15 * s * head
    piece("sphere", prefix + "Skull", size=(h, h * 1.1, h * 1.1), at=(0, 0, h * 0.55), mat=m["skin"], parent=hd,
          verts=8)
    j["Jaw"] = jaw = pivot(prefix + "Jaw", at=(0, -h * 0.15, h * 0.25), parent=hd)
    block(prefix + "JawPart", (h * 0.8, h * 0.6, h * 0.3), at=(0, -h * 0.2, -h * 0.08), mat=m["skin"], parent=jaw)
    upper, fore = 0.17 * s * arm, 0.16 * s * arm
    for sd, side in ((1, "L"), (-1, "R")):
        sh = j["Shoulder" + side] = pivot(prefix + "Shoulder" + side, at=(sd * w * 1.45, 0, 0.17 * s), parent=chest)
        piece("sphere", prefix + "Delt" + side, size=(0.1 * s * girth,) * 3, mat=m["body"], parent=sh, verts=6)
        limb(prefix + "Upper" + side, upper, 0.045 * s * girth, 0.037 * s * girth, m["skin"], sh)
        el = j["Elbow" + side] = pivot(prefix + "Elbow" + side, at=(0, 0, -upper), parent=sh)
        limb(prefix + "Fore" + side, fore, 0.038 * s * girth, 0.03 * s * girth, m["skin"], el)
        wr = j["Wrist" + side] = pivot(prefix + "Wrist" + side, at=(0, 0, -fore), parent=el)
        block(prefix + "Hand" + side, (0.05 * s * girth, 0.07 * s * girth, 0.07 * s), at=(0, 0, -0.035 * s),
              mat=m["skin"], parent=wr)
        hp = j["Hip" + side] = pivot(prefix + "Hip" + side, at=(sd * w * 0.6, 0, -0.03 * s), parent=pelvis)
        limb(prefix + "Thigh" + side, thigh, 0.06 * s * girth, 0.045 * s * girth, m["legs"], hp)
        kn = j["Knee" + side] = pivot(prefix + "Knee" + side, at=(0, 0, -thigh), parent=hp)
        limb(prefix + "Shin" + side, shin, 0.045 * s * girth, 0.035 * s * girth, m["legs"], kn)
        an = j["Ankle" + side] = pivot(prefix + "Ankle" + side, at=(0, 0, -shin), parent=kn)
        block(prefix + "Foot" + side, (0.08 * s * girth, 0.14 * s, 0.05 * s), at=(0, -0.035 * s, -0.015 * s),
              mat=m["feet"], parent=an)
    return j


# ================================================================================================ poses & clips

def rest_pose(joints):
    return {n: {"rot": [0.0, 0.0, 0.0], "loc": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]} for n in joints}


def out(side, deg):
    """Y rotation raising a hanging limb sideways: side 1 = left (+X), -1 = right."""
    return -side * deg


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def wave(t, period, phase=0.0):
    """sin wave, one cycle every `period` seconds: use with period = clip length / k so loops close."""
    return math.sin(2 * math.pi * (t / period + phase))


def keyed(t, keys):
    """Piecewise-smooth interpolation through [(time, value), ...] (values numbers or lists)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            if isinstance(v0, (list, tuple)):
                return [a + (b - a) * u for a, b in zip(v0, v1)]
            return v0 + (v1 - v0) * u
    return keys[-1][1]


_REST = {}


def _apply(joints, pose):
    for n, obj in joints.items():
        q = pose.get(n)
        if q is None:
            continue
        if n not in _REST:
            _REST[n] = (Vector(obj.location), Vector(obj.rotation_euler), Vector(obj.scale))
        loc0, rot0, scl0 = _REST[n]
        obj.location = loc0 + Vector(q["loc"])
        obj.rotation_euler = [r0 + math.radians(d) for r0, d in zip(rot0, q["rot"])]
        obj.scale = [a * b for a, b in zip(scl0, q["scale"])]


def record(joints, name, fn, seconds):
    """One clip: fn(t) -> pose ({joint: {"rot": [x, y, z] degrees ADDED to the build pose, "loc": offset, "scale":
    factors}}, start from rest_pose(joints)), keyed on every frame for every joint."""
    for n, obj in joints.items():
        if n not in _REST:
            _REST[n] = (Vector(obj.location), Vector(obj.rotation_euler), Vector(obj.scale))
    frames = max(1, round(seconds * FPS))
    action = bpy.data.actions.new(name)
    for obj in joints.values():
        obj.animation_data_create().action = action
    for f in range(frames + 1):
        _apply(joints, fn(seconds * f / frames))
        for obj in joints.values():
            for path in ("rotation_euler", "location", "scale"):
                obj.keyframe_insert(path, frame=f)
    for obj in joints.values():
        anim = obj.animation_data
        slot = anim.action_slot
        track = anim.nla_tracks.new()
        track.name = name
        track.strips.new(name, 0, action).action_slot = slot
        anim.action = None
    print(f"  clip {name}: {seconds:.2f} s, {frames} frames")


def export(name, joints=None, rest=None):
    """Write assets/models/<name>.glb with every recorded clip. rest: a pose to leave the model in (what shows
    with no clip playing; default the build pose)."""
    if joints and rest:
        _apply(joints, rest)
    elif joints:
        for n, obj in joints.items():
            if n in _REST:
                obj.location, obj.rotation_euler, obj.scale = _REST[n][0], _REST[n][1], _REST[n][2]
    os.makedirs(MODELS, exist_ok=True)
    path = os.path.join(MODELS, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_animations=True,
                              export_animation_mode="ACTIONS", export_anim_slide_to_zero=True,
                              export_optimize_animation_size=False, export_apply=True)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.context.scene.objects
               if o.type == "MESH")
    print(f"wrote {path} ({tris} triangles)")
