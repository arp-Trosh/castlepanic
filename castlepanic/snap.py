"""Pictures of what the terminal shows: a FrameBuffer or a Screen drawn as an image, cell by cell, the way a
terminal draws the block glyphs. For previews, screenshots and tests (not used while playing)."""
import numpy as np

from unicode3d.glyphs import GLYPH_SETS
from unicode3d.terminal import Screen

CELL = (8, 16)  # pixels of one cell in the pictures, wide x high
TERMINAL_FG, TERMINAL_BG = (204, 204, 204), (12, 12, 16)
_masks = {}


def _cell_masks(glyphs):
    if glyphs not in _masks:
        w, h = CELL
        gs = GLYPH_SETS[glyphs]
        pw, ph = gs.cell_pixels
        xs, ys = np.arange(w) * pw // w, np.arange(h) * ph // h
        sub = ys[:, None] * pw + xs[None, :]
        _masks[glyphs] = {c: (bits >> sub & 1).astype(bool) for bits, c in enumerate(gs.chars)}
    return _masks[glyphs]


def _unpack(packed, default):
    out = np.empty(packed.shape + (3,), np.uint8)
    out[...] = default
    truecolor = (packed >= 0) & (packed & (1 << 25) != 0)
    for k, shift in enumerate((16, 8, 0)):
        out[..., k] = np.where(truecolor, (packed >> shift) & 255, out[..., k])
    return out


def screen_of(fb, glyphs="sextant"):
    pw, ph = GLYPH_SETS[glyphs].cell_pixels
    scr = Screen(None, glyphs=glyphs, color="truecolor", size=(fb.height // ph, fb.width // pw))
    scr.draw_frame(fb)
    return scr


def terminal_picture(fb_or_screen, glyphs="sextant"):
    """(rows*16, cols*8, 3) uint8: the cells as a terminal shows them (text drawn as solid fg blocks)."""
    scr = fb_or_screen if isinstance(fb_or_screen, Screen) else screen_of(fb_or_screen, glyphs)
    masks = _cell_masks(glyphs)
    fg, bg = _unpack(scr.fg, TERMINAL_FG), _unpack(scr.bg, TERMINAL_BG)
    rows, cols = scr.chars.shape
    w, h = CELL
    text = np.zeros((h, w), bool)
    text[4:12, 2:6] = True  # a printable character: a little block of foreground
    out = np.empty((rows * h, cols * w, 3), np.uint8)
    blank = np.zeros((h, w), bool)
    for y in range(rows):
        for x in range(cols):
            c = scr.chars[y, x]
            mask = masks.get(c)
            if mask is None:
                mask = blank if c == " " else text
            out[y * h:(y + 1) * h, x * w:(x + 1) * w] = np.where(mask[..., None], fg[y, x], bg[y, x])
    return out
