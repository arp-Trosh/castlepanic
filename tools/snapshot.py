"""Render the board scene off-screen and save what the terminal would show: tools/snapshot.py [out.png] [--top]"""
import sys, os, time
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unicode3d.scene import Camera, Renderer, Object3D
from unicode3d.lights import Light
from unicode3d.shapes import blob_mesh
from castlepanic import board
from castlepanic.snap import terminal_picture

def main(out="assets/previews/board.png", top=False, cols=200, rows=60):
    t = time.time()
    objs = board.build()
    print("build", round(time.time() - t, 2))
    # markers: arc k gets k+1 little balls in the archer ring
    for arc in range(6):
        for k in range(arc + 1):
            p, _ = board.space_position(arc, 3, k, arc + 1)
            objs.append(Object3D(blob_mesh((0.2, 0.2, 0.2)), p + (0, 0.2, 0), color=(255, 240, 200)))
    cam = Camera(position=np.array([0, 26.0, 0.01]) if top else np.array([0, 15.0, 16.0]), target=np.zeros(3), fov=45)
    light = [Light(direction=np.array([-0.4, -1, -0.3]), ambient=0.35, diffuse=0.75, shadows=True)]
    r = Renderer(cols, rows, (2, 3), background=(20, 18, 24))
    fb = r.render(objs, cam, light)
    Image.fromarray(terminal_picture(fb)).save(out)
    print(out)

if __name__ == "__main__":
    main(*(a for a in sys.argv[1:] if not a.startswith("--")), top="--top" in sys.argv)
