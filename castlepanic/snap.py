"""Pictures of what the terminal shows, for previews, screenshots and tests (not used while playing): a FrameBuffer
or a Screen drawn cell by cell as a terminal draws it (Screen.picture)."""
from unicode3d.glyphs import GLYPH_SETS
from unicode3d.terminal import Screen


def screen_of(fb, glyphs="sextant"):
    pw, ph = GLYPH_SETS[glyphs].cell_pixels
    scr = Screen(None, glyphs=glyphs, color="truecolor", size=(fb.height // ph, fb.width // pw))
    scr.draw_frame(fb)
    return scr


def terminal_picture(fb_or_screen, glyphs="sextant"):
    """(rows*16, cols*8, 3) uint8: the cells as a terminal shows them."""
    scr = fb_or_screen if isinstance(fb_or_screen, Screen) else screen_of(fb_or_screen, glyphs)
    return scr.picture()
