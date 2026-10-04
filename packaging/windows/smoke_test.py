"""Plays the built CastlePanic.exe in a real Windows console (ConPTY, as Windows Terminal uses).

Starts a solo game, hurries the opening lettering, steps on to Play Cards, leaves, and quits from the menu,
checking the screen at each step: this exercises the Windows console setup, VT input decoding and output that unit
tests cannot. Usage: python smoke_test.py dist/CastlePanic/CastlePanic.exe
"""
import os
import re
import sys
import time

from winpty import PtyProcess

TOKEN = re.compile(r"\x1b\[([0-9;?<>]*)([ -/]*[@-~])|\x1b\][^\x07]*\x07|\x1b[@-Z\\-_]|[\r\n]|[^\x1b\r\n]+")
ROWS, COLS = 34, 110


class VirtualScreen:
    """Just enough of a terminal to follow the game's output: the game only rewrites cells that
    change, so text on screen is often never sent in one piece."""

    def __init__(self):
        self.cells = [[" "] * COLS for _ in range(ROWS)]
        self.y = self.x = 0

    def feed(self, data):
        for m in TOKEN.finditer(data):
            tok = m.group(0)
            if m.group(2):
                self._csi(m.group(1), m.group(2)[-1])
            elif tok == "\r":
                self.x = 0
            elif tok == "\n":
                self.y = min(self.y + 1, ROWS - 1)
            elif not tok.startswith("\x1b"):
                for ch in tok:
                    if self.x < COLS:
                        self.cells[self.y][self.x] = ch
                    self.x += 1

    def _csi(self, params, final):
        nums = [int(p) if p.isdigit() else 0 for p in params.lstrip("?<>").split(";")]
        if final in "Hf":
            y, x = (nums + [1, 1])[:2]
            self.y, self.x = min(max(y, 1), ROWS) - 1, min(max(x, 1), COLS) - 1
        elif final == "J" and not params.startswith("?"):
            self.cells = [[" "] * COLS for _ in range(ROWS)]
        elif final == "K":
            self.cells[self.y][self.x:] = [" "] * (COLS - self.x)
        elif final == "C":
            self.x += max(nums[0], 1)
        elif final == "G":
            self.x = max(nums[0], 1) - 1

    def text(self):
        return "\n".join("".join(row) for row in self.cells)


class Game:
    def __init__(self, exe):
        env = dict(os.environ, CASTLEPANIC_NAME="Smoke", CASTLEPANIC_NO_SOUND="1")  # also checks the launcher passes the name on
        self.proc = PtyProcess.spawn(exe, env=env, dimensions=(ROWS, COLS))
        self.screen = VirtualScreen()

    def wait_for(self, text, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            try:
                chunk = self.proc.read(65536)
            except EOFError:
                break
            self.screen.feed(chunk)
            if text in self.screen.text():
                print(f"  saw {text!r}")
                return
            if not chunk:
                time.sleep(0.05)
        alive = self.proc.isalive()
        status = None if alive else self.proc.exitstatus
        raise AssertionError(f"never saw {text!r} (process alive: {alive}, exit status: {status}); screen:\n"
                             + self.screen.text())

    def drain(self, secs):
        """Keep reading the game's output for secs: the menu's 3D backdrop draws every frame, and a game whose
        output nobody reads blocks on writing it, so never gets to the keys sent."""
        end = time.time() + secs
        while time.time() < end and self.proc.isalive():
            try:
                chunk = self.proc.read(65536)
            except EOFError:
                return
            self.screen.feed(chunk)
            if not chunk:
                time.sleep(0.02)

    def send(self, keys):
        self.proc.write(keys)
        self.drain(0.5)


def main(exe):
    game = Game(os.path.abspath(exe))
    game.wait_for("Single Player", timeout=120)  # (the first start compiles the renderer)
    game.send("\r")                      # Single Player, solo
    game.wait_for("Order of play", timeout=60)
    for _ in range(12):                  # hurry the opening words, the horn and the first wave
        game.send(" ")
    game.wait_for("Smoke (you): Step 2", timeout=60)  # (also checks the launcher passes the name on)
    game.wait_for("Discard & draw a new card", timeout=60)  # (shown once the board is quiet: N works then)
    game.send("n")                       # solo: no trade, straight on to Play Cards
    game.wait_for("Step 4: Play Cards")
    game.send("q")
    game.send("q")                       # leave (confirmed), back to the menu
    game.wait_for("Single Player")
    for _ in range(5):
        game.send("\x1b[B")              # arrow keys down to Quit
    game.send("\r")
    end = time.time() + 15
    while game.proc.isalive() and time.time() < end:
        game.drain(0.2)
    if game.proc.isalive():
        game.proc.terminate(force=True)
        raise AssertionError("the game did not exit after Quit")
    print(f"  exited with status {game.proc.exitstatus}")
    assert game.proc.exitstatus == 0
    print("SMOKE TEST OK")


if __name__ == "__main__":
    main(sys.argv[1])
