"""Drive the App off-screen with scripted keys and save screenshots: python tools/ui_test.py"""
import sys, os, time
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unicode3d.terminal import Screen
from unicode3d.keys import Key
from castlepanic.ui import App

def shot(screen, path):
    Image.fromarray(screen.picture()).save(path)

def main():
    rows, cols = int(os.environ.get("ROWS", 50)), int(os.environ.get("COLS", 170))
    screen = Screen(None, glyphs="sextant", color="truecolor", size=(rows, cols))
    screen.refresh = lambda: None
    app = App("Tester", sound=False, seed=5)
    script = [(5, []), (1, [Key.ENTER])] + [(60, [])]
    n = 0
    def run(frames, keys):
        nonlocal n
        for i in range(frames):
            ok = app.frame(screen, 1 / 30, keys if i == 0 else [])
            assert ok is not False
    run(5, []); shot(screen, "assets/previews/ui_menu.png")
    run(1, [Key.ENTER]); run(60, [])
    shot(screen, "assets/previews/ui_intro.png")
    while app.scene.busy():  # the opening: words, horn, the first wave
        run(1, [])
    run(30, [])
    shot(screen, "assets/previews/ui_game0.png")
    g = app.session.game
    run(1, [ord("1")])  # (Draw Up moves on to Discard by itself); run(3, [])
    shot(screen, "assets/previews/ui_discard.png")
    run(1, [Key.ESC]); run(1, [ord("n")]); run(3, [])  # (solo: no trade) -> play
    # try to play the first playable hit card on its first target
    for i, cid in enumerate(g.hands[0]):
        if g.playable(0, cid) and g.cards[cid]["kind"] in ("archer", "knight", "swordsman", "hero"):
            run(1, [ord(str(i + 1))]); run(3, [])
            shot(screen, "assets/previews/ui_target.png")
            run(1, [ord("a")]); run(60, [])
            shot(screen, "assets/previews/ui_attack.png")
            break
    while app.scene.busy():
        run(1, [])
    run(1, [ord("n")])  # play -> the Monsters move
    for k in range(60):
        run(1, [])
    shot(screen, "assets/previews/ui_monsters.png")
    while app.scene.busy():
        run(1, [])
    shot(screen, "assets/previews/ui_move_done.png")
    run(1, [ord("n")])  # -> draw 2 Monsters: "tHe mOnsTeRs aRe CoMing!", then each token's name
    t = time.time()
    for k in range(400):
        run(1, [])
        if k in (70, 130): shot(screen, f"assets/previews/ui_draw{k}.png")
    print("400 frames", round(time.time() - t, 1), "s; turn", app.session.game.turn, "log tail:")
    for line in app.session.log[-8:]: print("  ", line[0])
main()
