"""Contact sheets of a model's clips, drawn by unicode3d as a TERMINAL shows them (sextant cells), so you judge a
model at the size it will really be seen. One row per clip, `--shots` moments across it.

    .venv/bin/python tools/preview.py castlepanic/data/models/goblin.glb [--shots 5] [--yaw 30] [--cells 40] [--pixels]

Writes assets/previews/<name>.png. --cells sets each tile's width in terminal cells (default 36: a monster seen
close up in game; try 14 for how it looks on the whole board). --pixels saves the raw framebuffer instead
(square pixels, more detail than any terminal shows: for checking geometry, not looks).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from castlepanic.snap import terminal_picture  # noqa: E402
from unicode3d.color import linear_to_srgb  # noqa: E402
from unicode3d.lights import Light  # noqa: E402
from unicode3d.models import load_model  # noqa: E402
from unicode3d.scene import Camera, Renderer  # noqa: E402


def sheet(path, shots=5, yaw=25.0, cells=36, pixels=False, clips=None):
    model = load_model(path)
    lo, hi = model.world_bounds()
    height = max(hi[1] - lo[1], 0.2)
    centre = (lo + hi) / 2
    names = [n for n in model.animations if not clips or n in clips] or [None]
    a = np.radians(yaw)
    dist = height * 1.9
    eye = centre + np.array([dist * np.sin(a), height * 0.35, dist * np.cos(a)])
    camera = Camera(position=eye, target=centre, fov=40)
    lights = [Light(direction=np.array([-0.5, -1.0, -0.4]), ambient=0.25, diffuse=0.8, color=(255, 236, 205),
                    shadows=True),
              Light(direction=np.array([0.7, -0.3, 0.6]), ambient=0.0, diffuse=0.35, color=(150, 170, 255))]
    rows_px = []
    if pixels:
        renderer = Renderer(240, 240, (1, 1), cell_aspect=1.0)
    else:
        rows = int(cells * 0.62)
        renderer = Renderer(cells, rows, (2, 3), cell_aspect=0.5, background=(28, 26, 30))
    for name in names:
        clip = model.animations.get(name) if name else None
        tiles = []
        for k in range(shots):
            if clip:
                clip.apply(clip.duration * k / max(1, shots - 1) if clip.loop == "once" else clip.duration * k / shots)
            fb = renderer.render([*model], camera, lights)
            if pixels:
                tiles.append(np.rint(linear_to_srgb(np.clip(fb.rgb, 0, 1)) * 255).astype(np.uint8))
            else:
                tiles.append(terminal_picture(fb))
            tiles.append(np.full((tiles[-1].shape[0], 4, 3), 90, np.uint8))
        rows_px.append(np.concatenate(tiles, axis=1))
        rows_px.append(np.full((4, rows_px[-1].shape[1], 3), 90, np.uint8))
    out = os.path.join(ROOT, "assets", "previews", os.path.splitext(os.path.basename(path))[0] +
                       ("-px" if pixels else "") + ".png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray(np.concatenate(rows_px, axis=0)).save(out)
    info = ", ".join(f"{n} {model.animations[n].duration:.2f}s" for n in names if n)
    tris = sum(len(o.mesh.faces) for o in model)
    print(out, f"[{info}]", f"{len(list(model))} parts, {tris} tris, height {height:.2f}", *model.warnings)
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("models", nargs="+")
    p.add_argument("--shots", type=int, default=5)
    p.add_argument("--yaw", type=float, default=25.0, help="camera angle around the model, degrees")
    p.add_argument("--cells", type=int, default=36, help="tile width in terminal cells")
    p.add_argument("--pixels", action="store_true", help="raw square pixels instead of terminal cells")
    p.add_argument("--clips", nargs="*", help="only these clips")
    args = p.parse_args()
    for m in args.models:
        sheet(m, args.shots, args.yaw, args.cells, args.pixels, args.clips)
