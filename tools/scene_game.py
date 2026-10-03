"""Play a bot game through the 3D scene off-screen, saving snapshots: checks the event animations don't crash."""
import sys, os, time
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unicode3d.scene import Renderer
from castlepanic import bots
from castlepanic.rules import Game, apply
from castlepanic.scene import BoardScene
from castlepanic.snap import terminal_picture
seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
turns = int(sys.argv[2]) if len(sys.argv) > 2 else 6
g = Game(["A", "B", "C"][:int(os.environ.get("N", 2))], seed=seed)
sc = BoardScene(seed=seed)
sc.sync(g); g.take_events()
r = Renderer(200, 60, (2, 3), background=(18, 16, 22))
shots, frames, t0, rt = 0, 0, time.time(), 0
offered = {0: set(), 1: set()}
while g.phase != "over" and g.turn <= turns:
    seats = [s for s in g.pending] or ([g.trade_offer["to"]] if g.trade_offer else [g.current])
    apply(g, seats[0], bots.next_action(g, seats[0], offered[seats[0]]))
    sc.play(g.take_events())
    n = 0
    while sc.busy() and n < 2000:
        sc.update(1 / 30); n += 1; frames += 1
        if frames % 60 == 0:
            t = time.time(); fb = r.render(sc.objects(), sc.rig.camera, sc.lights); rt += time.time() - t
        if frames % 900 == 0:
            Image.fromarray(terminal_picture(r.render(sc.objects(), sc.rig.camera, sc.lights))).save(f"assets/previews/game{shots}.png"); shots += 1
    assert n < 2000, "scene stuck"
print("frames", frames, "shots", shots, "wall", round(time.time() - t0, 1), "render avg ms", round(1000 * rt / max(1, frames // 10), 1),
      "monsters", len(g.monsters), "actors", len(sc.monsters), "objs", len(sc.objects()))
