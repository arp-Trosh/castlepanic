import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

reset()
rng = new_rng(1)
t = save_textures("kittest", {"skin": tex_skin(rng, (0.42, 0.48, 0.22)), "cloth": tex_cloth(rng, (0.35, 0.12, 0.08)),
                              "iron": tex_metal(rng, (0.3, 0.3, 0.32))})
m = {"skin": material("Skin", image=t["skin"], roughness=0.8), "body": material("Cloth", image=t["cloth"], roughness=1),
     "legs": material("Cloth2", image=t["cloth"], roughness=1), "feet": material("Iron", image=t["iron"], roughness=0.5, metallic=0.5)}
j = humanoid(m, height=0.9, hunch=0.4, head=1.3)
def idle(t):
    p = rest_pose(j)
    p["Chest"]["rot"][0] = 3 * wave(t, 2.0)
    p["ShoulderL"]["rot"][1] = out(1, 10); p["ShoulderR"]["rot"][1] = out(-1, 10)
    return p
def walk(t):
    p = rest_pose(j)
    for s, side in ((1, "L"), (-1, "R")):
        p["Hip"+side]["rot"][0] = 30 * s * wave(t, 1.0)
        p["Knee"+side]["rot"][0] = 25 + 25 * wave(t, 1.0, 0.25 * s)
        p["Shoulder"+side]["rot"][0] = -25 * s * wave(t, 1.0)
    return p
record(j, "Idle", idle, 2.0)
record(j, "Walk", walk, 1.0)
export("kittest", j)
