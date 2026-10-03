"""Drive the App off-screen with scripted keys and save screenshots: python tools/ui_test.py"""
import sys, os, time
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unicode3d.terminal import Screen
from unicode3d.keys import Key
from castlepanic.ui import App
from castlepanic.snap import terminal_picture, CELL

def shot(screen, path):
    img = Image.fromarray(terminal_picture(screen))
    d = ImageDraw.Draw(img)
    rows, cols = screen.chars.shape
    from castlepanic.snap import _unpack, TERMINAL_FG
    from unicode3d.glyphs import GLYPH_SETS
    blocks = set(GLYPH_SETS["sextant"].chars)
    fg = _unpack(screen.fg, TERMINAL_FG)
    for y in range(rows):
        for x in range(cols):
            c = screen.chars[y, x]
            if c != " " and c not in blocks:
                d.rectangle([x * 8, y * 16, x * 8 + 7, y * 16 + 15], fill=(12, 12, 16) if not screen.attrs[y, x] & 4 else tuple(int(v) for v in fg[y, x]))
                d.text((x * 8, y * 16 + 2), c, fill=tuple(int(v) for v in fg[y, x]) if not screen.attrs[y, x] & 4 else (12, 12, 16))
    img.save(path)

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
    run(1, [Key.ENTER]); run(90, [])
    shot(screen, "assets/previews/ui_game0.png")
    g = app.session.game
    # try to play the first playable hit card on its first target
    for i, cid in enumerate(g.hands[0]):
        if g.playable(0, cid) and g.cards[cid]["kind"] in ("archer", "knight", "swordsman", "hero"):
            run(1, [ord(str(i + 1))]); run(3, [])
            shot(screen, "assets/previews/ui_target.png")
            run(1, [ord("a")]); run(60, [])
            shot(screen, "assets/previews/ui_attack.png")
            break
    run(1, [ord("e")])
    t = time.time()
    for k in range(400):
        run(1, [])
        if k == 60: shot(screen, "assets/previews/ui_monsters.png")
    print("400 frames", round(time.time() - t, 1), "s; turn", app.session.game.turn, "log tail:")
    for line in app.session.log[-8:]: print("  ", line[0])
main()
