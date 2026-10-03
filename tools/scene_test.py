import sys, os, time, math, random
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unicode3d.scene import Camera, Renderer
from unicode3d.lights import Light
from castlepanic import board
from castlepanic.actors import Library, Actor, Static
from castlepanic.snap import terminal_picture
lib = Library(); rng = random.Random(1)
acts = []
for arc in range(6):
    p, y = board.tower_position(arc); acts.append(Static(lib, "tower", p, y))
    p, y, s = board.wall_position(arc); acts.append(Static(lib, "wall", p, y, scale=(s, 1, 1)))
for k in range(40):
    deg = rng.uniform(0, 360); r = rng.uniform(8.0, 10.2)
    acts.append(Static(lib, rng.choice(["tree_pine", "tree_pine", "tree_dead", "tree_oak"]), board.polar(deg, r), rng.uniform(0, 6.28), scale=rng.uniform(0.8, 1.2)))
for arc, ring, kind in [(0, 3, "troll"), (2, 2, "healer"), (4, 1, "troll"), (5, 3, "healer")]:
    p, y = board.space_position(arc, ring); acts.append(Actor(lib, kind, p, y))
p, y, _ = board.wall_position(1); acts.append(Actor(lib, "barbarian", p + (0, 1.0, 0), y + math.pi))
t = time.time()
for a in acts: a.update(0.5)
print("update", len(acts), round(time.time() - t, 3))
objs = board.build() + [o for a in acts for o in a.objects()]
print("objects", len(objs))
cam = Camera(position=np.array([0, 13.0, 15.0]), target=np.array([0, 0, 1.5]), fov=45)
light = [Light(direction=np.array([-0.5, -1, -0.35]), ambient=0.3, diffuse=0.8, color=(255, 235, 205), shadows=True),
         Light(direction=np.array([0.6, -0.4, 0.5]), ambient=0, diffuse=0.3, color=(140, 160, 255))]
r = Renderer(200, 60, (2, 3), background=(18, 16, 22))
t = time.time(); fb = r.render(objs, cam, light); print("render", round(time.time() - t, 3))
t = time.time(); fb = r.render(objs, cam, light); 
for a in acts: a.update(0.03)
fb = r.render(objs, cam, light); print("render2", round(time.time() - t, 3))
Image.fromarray(terminal_picture(fb)).save("assets/previews/scene.png")
import collections
cnt = {}

for label, light_set in (("shadows", light), ("noshadow", [Light(direction=np.array([-0.5, -1, -0.35]))])):
    ts = []
    for i in range(15):
        for a in acts: a.update(1/30)
        t = time.time(); r.render(objs, cam, light_set); ts.append(time.time() - t)
    tu = time.time()
    for a in acts: a.update(1/30)
    print(label, "render ms", round(1000 * np.median(ts), 1), "update ms", round(1000 * (time.time() - tu), 1))
