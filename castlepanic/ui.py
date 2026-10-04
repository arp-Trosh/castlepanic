"""The terminal front end: menus, the lobby, and the game screen (3D view, hand, players, log, chat).

Everything works by keyboard and most things by mouse too. The game screen:

    status line
    +------------------------------------------+----------------+
    |                                          | players & their|
    |            the 3D board                  | open hands     |
    |                                          |----------------|
    |                                          | log            |
    +------------------------------------------+----------------+
    | your hand: card boxes, what to do next   | order of play,  |
    |                                          | [NEXT STEP]     |
    | (multiplayer) chat                                          |
    | keys help                                         frame rate |

The display settings (glyphs, colours, frame rate, shadows, reflections) are on the menu's Settings screen, kept
between runs (settings.py); F2-F6 still switch them anywhere.
"""
import math
import time

import numpy as np

from unicode3d.keys import Key, MouseEvent
from unicode3d.scene import Renderer
from unicode3d.terminal import Color
from unicode3d.ui import DisplayControls

from . import board, settings
from .narrate import describe
from .net import DEFAULT_PORT, local_ip
from .rules import (ARCHER, ARCS, CARD_HELP, CASTLE, FOREST, HIT_RING, KNIGHT, RING_NAMES, STEP_TITLES, STEPS,
                    SWORDSMAN, IllegalMove, arc_color, card_title)
from .scene import BoardScene
from .session import MAX_NAME, ClientSession, HostSession, single_player
from .sound import Sound

CARD_COLOR = {"red": Color.RED, "green": Color.GREEN, "blue": Color.BLUE, "any": Color.MAGENTA, None: Color.YELLOW}
SHORT = {"archer": "Arc", "knight": "Kni", "swordsman": "Swd", "hero": "Her", "barbarian": "Bar", "brick": "Brk",
         "mortar": "Mor", "nice_shot": "Nic", "tar": "Tar", "fortify": "For", "drive_back": "Drv", "missing": "Mis",
         "draw2": "Dr2", "scavenge": "Scv"}
ORDER_W = 41  # the Order of play window's width (ORDER_NARROW when the terminal is narrow)
ORDER_NARROW = 24
CHAT_H = 8  # the game screen's chat panel, docked in the bottom bar until wanted
CHAT_SLIDE = 0.3  # seconds it takes to slide up out of the bar, or back down into it
CHAT_BG = (14, 14, 20)
LETTERS = "abcdefghijklmnopqrstuvwxyz"
HP_PIP = "●"
RING_LABEL = {ARCHER: "Arc", KNIGHT: "Kni", SWORDSMAN: "Swo"}
RING_LABELS_FAR = 26.0  # camera distance beyond which only one line of ring names shows
# a short tag over each Monster, so it's known at a glance (set SHOW_TAGS False to drop them)
SHOW_TAGS = True
MONSTER_TAG = {"goblin_king": "GK", "orc_warlord": "OW", "troll_mage": "TM", "healer": "HL", "troll": "TR",
               "orc": "OR", "goblin": "GO"}


# the start of a siege: these words, the war horn, then "tHe mOnsTeRs aRe CoMing!" and the first wave
INTRO = [
    {"e": "banner", "lines": ["We're being attacked", "by monsters!"], "style": "gilt"},
    {"e": "banner", "lines": ["Defend the castle!"], "style": "gilt", "hold": 1.2},
    {"e": "banner", "lines": ["Fight! Fight!", "Never surrender!"], "style": "gilt"},
    {"e": "sound", "name": "start", "wait": 1.8},
]
SKIP_KEYS = (Key.ESC, Key.ENTER, ord(" "))  # hurry the lettering away

HELP = [
    "HOW TO PLAY",
    "",
    "Monsters march from the Forest ring through the Archer, Knight and Swordsman rings",
    "to the Castle. Defend the 6 Towers together; survive all 49 Monster tokens to win.",
    "",
    "Your turn, a step at a time (N, Enter or NEXT STEP moves on):",
    "  1 draw up (by itself)  2 discard & draw 1 (click a card twice; solo: 2)  3 trade 1 card",
    "  (6 players: 2, with two players)  4 play cards  5 the Monsters move  6 draw 2 Monsters",
    "All hands are open: it's a co-operative game, so trade for what you need (click your card,",
    "  then a player's card in Defenders, either way round).",
    "",
    "To hit a Monster the card must match its ring AND colour (red 1-2, green 3-4, blue 5-6).",
    "  Archer / Knight / Swordsman: that ring.  Any Colour: that ring, any colour.",
    "  Hero: Archer, Knight or Swordsman ring of its colour.  Nothing hits in the Forest.",
    "  Barbarian: slay any Monster outside the Forest (Castle too).  Nice Shot + hit: slain.",
    "  Tar: hold a Monster this turn.  Drive Him Back!: back to the Forest.",
    "  Brick + Mortar (choose both): rebuild a Wall.  Fortify: a Wall survives one attack.",
    "  Missing: no new Monsters.  Draw 2 / Scavenge: more cards.",
    "",
    "A Monster at a Wall smashes it and takes 1 damage; in the Castle it smashes Towers",
    "and walks clockwise. Goblins 1, Orcs 2, Trolls 3 hit points; bosses have powers.",
    "Slain Monsters are trophies: most points is the Master Slayer.",
    "",
    "Press H or Esc to close.",
]


def card_color(c):
    return CARD_COLOR.get(c["color"], Color.YELLOW) if c["kind"] not in ("brick", "mortar") else Color.WHITE


class TextInput:
    def __init__(self, value="", limit=40):
        self.value, self.limit = value, limit

    def handle(self, k):
        if k == Key.BACKSPACE or k == 8:
            self.value = self.value[:-1]
            return True
        if isinstance(k, int) and 32 <= k < 0x110000 and k not in (127,) and k < 0xE000 and len(self.value) < self.limit:
            ch = chr(k)
            if ch.isprintable():
                self.value += ch
                return True
        return False


class App:
    def __init__(self, name, sound=True, seed=None, fixed=()):
        """fixed: the display settings given on the command line, which win over the saved ones this run."""
        self.name = name[:MAX_NAME]
        self.sound = Sound(sound)
        self.seed = seed
        self.mode = "menu"
        self.menu_index = 0
        self.session = None
        self.scene = BoardScene(seed=seed or 1, on_sound=self.sound.play)
        self.renderer = Renderer(1, 1)
        # Drawn: the frame rate only; the rest are on the Settings screen (and F2-F6).
        self.controls = DisplayControls(renderer=self.renderer, show=("fps",))
        self.saved = settings.load()
        self.controls.apply({k: v for k, v in self.saved.items() if k not in fixed})  # (they wait for the screen)
        self.settings_index = 0
        self.form = {"players": 1, "host_players": 4, "port": TextInput(str(DEFAULT_PORT), 5),
                     "address": TextInput("127.0.0.1", 60), "name": TextInput(self.name, MAX_NAME), "bots": True,
                     "field": 0}
        self.ui = {}  # the game screen's interaction state
        self.chat_input = None
        self.chat_open = False  # the game screen's chat panel is up (else docked in the bottom bar)
        self.chat_slide = 0.0  # 0 docked .. 1 up, easing between
        self.chat_tab = (-1, -1, -1, -1)  # the bottom bar's Chat tab: x0, y0, x1, y1
        self.chat_rect = (-1, -1, -1, -1)  # the panel as drawn now
        self.heard = (None, 0, 0)  # (session, chat messages from others chimed for, and read)
        self.message = ""
        self.message_t = 0.0
        self.quit_armed = 0.0
        self.view = (0, 0, 1, 1)  # top, left, width, height of the 3D view
        self.hand_boxes = []  # (x0, y0, x1, y1, card id)
        self.next_box = (-1, -1, -1, -1)  # the Next Step button: x0, y0, x1, y1
        self.side_boxes = []  # (x0, y0, x1, y1, seat, card id or None for the name) in the Defenders list
        self.click_zones = []  # (x0, y0, x1, y1, callback)
        self._demo()
        self.last_sync = 0.0

    # ---------------------------------------------------------------------------------------------- helpers

    def flash(self, text):
        self.message, self.message_t = text, 4.0

    def _demo(self):
        """The menu's backdrop: a game in progress, Monsters fidgeting, the camera circling."""
        from .rules import Game
        g = Game(["demo"], seed=11)
        for _ in range(3):
            g.end_turn(0) if g.phase != "over" else None
            g.take_events()
        self.scene.sync(g)
        self.scene.rig.user_moved = 0

    def close(self):
        if self.session:
            self.session.close()
        self.sound.close()

    # ---------------------------------------------------------------------------------------------- frame

    def frame(self, screen, dt, keys):
        dt = min(dt, 0.1)
        self.message_t = max(0.0, self.message_t - dt)
        self.quit_armed = max(0.0, self.quit_armed - dt)
        first = self.controls.screen is None
        keys = self.controls.handle(keys, screen)
        if first:  # what the saved settings and the command line came to on this terminal
            self.saved = self.controls.settings()
        elif self.controls.settings() != self.saved:
            self.saved = self.controls.settings()
            settings.save(self.saved)
        rows, cols = screen.size()
        screen.erase()
        if rows < 20 or cols < 70:
            screen.text(0, 0, "Make the terminal at least 70x20 for Castle Panic.", Color.YELLOW)
            screen.refresh()
            return not any(k in (ord("q"), Key.ESC) for k in keys)
        self._chime()
        handler = getattr(self, "frame_" + self.mode)
        result = handler(screen, dt, keys, rows, cols)
        self.controls.draw(screen, rows - 1, cols - self.controls.width - 1)
        screen.refresh()
        return result is not False

    def _draw_view(self, screen, top, left, width, height):
        self.view = (top, left, width, height)
        self.renderer.resize(width, height, screen.cell_pixels)
        fb = self.renderer.render(self.scene.objects(), self.scene.rig.camera, self.scene.lights)
        screen.draw_frame(fb, top=top, left=left)

    def _camera_keys(self, k):
        rig = self.scene.rig
        if k in (Key.LEFT, ord("a")):
            rig.nudge(dyaw=-0.15)
        elif k in (Key.RIGHT, ord("d")):
            rig.nudge(dyaw=0.15)
        elif k in (Key.UP, ord("w")):
            rig.nudge(dpitch=0.08)
        elif k in (Key.DOWN, ord("s")):
            rig.nudge(dpitch=-0.08)
        elif k in (ord("+"), ord("=")):
            rig.nudge(zoom=0.88)
        elif k in (ord("-"), ord("_")):
            rig.nudge(zoom=1.14)
        elif k in (Key.HOME, ord("r")):
            rig.reset()
        else:
            return False
        return True

    def _mouse_view(self, ev):
        top, left, w, h = self.view
        if isinstance(ev, MouseEvent) and left <= ev.x < left + w and top <= ev.y < top + h:
            if ev.button == 64:
                self.scene.rig.nudge(zoom=0.9)
                return True
            if ev.button == 65:
                self.scene.rig.nudge(zoom=1.1)
                return True
        return False

    def _setting_widgets(self):
        """(key, title, widget, shown) for each display setting, in the Settings screen's order."""
        c = self.controls
        return [("glyphs", "Characters", c.glyphs, str), ("color", "Colours", c.color, str),
                ("fps", "Frame rate", c.fps, lambda v: f"{v} fps"),
                ("shadows", "Shadows", c.shadows, lambda v: "on" if v else "off"),
                ("reflections", "Reflections", c.reflections, lambda v: "on" if v else "off")]

    # ---------------------------------------------------------------------------------------------- menu

    MENU = ["Single Player", "Host Game", "Join Game", "Name", "Settings", "Quit"]

    def _backdrop(self, screen, dt, rows, cols, sub="Defend the last towers against the horde"):
        """The menu screens' background: the demo board, the camera circling; the title over it."""
        self.scene.rig.yaw += dt * 0.08
        self.scene.rig.pitch = math.radians(38)
        self.scene.rig.dist = 19
        self.scene.update(dt)
        self._draw_view(screen, 0, 0, cols, rows - 1)
        title = "C A S T L E   P A N I C"
        screen.text(2, (cols - len(title)) // 2, title, Color.YELLOW, bold=True)
        screen.text(3, (cols - len(sub)) // 2, sub, Color.WHITE, dim=True)

    def frame_menu(self, screen, dt, keys, rows, cols):
        self._backdrop(screen, dt, rows, cols)
        f = self.form
        x0 = cols // 2 - 18
        y0 = 6
        items = [
            f"Single Player   < {f['players']} {'(solo)' if f['players'] == 1 else 'players, bots'} >",
            f"Host Game       < {f['host_players']} seats, bots {'on' if f['bots'] else 'off'}, port {f['port'].value} >",
            f"Join Game       [{f['address'].value}]",
            f"Name            [{f['name'].value}]",
            "Settings",
            "Quit",
        ]
        self.click_zones = []
        for i, text in enumerate(items):
            sel = i == self.menu_index
            screen.text(y0 + 2 * i, x0 - 2, ("> " if sel else "  ") + text, Color.YELLOW if sel else Color.WHITE,
                        bold=sel, reverse=False)
            self.click_zones.append((x0 - 2, y0 + 2 * i, x0 + 60, y0 + 2 * i, i))
        help_ = "Up/Down choose  Left/Right change  Enter select  type to edit  Q quit"
        if self.menu_index == 1:
            help_ = "Left/Right seats  B bots  P port  Enter host  (port: type digits after P)"
        screen.text(rows - 1, 1, help_[:cols - self.controls.width - 3], Color.WHITE, dim=True)
        if self.message_t > 0:
            screen.text(y0 + 12, x0 - 2, self.message, Color.RED, bold=True)
        editing = {2: f["address"], 3: f["name"]}.get(self.menu_index)
        if self.menu_index == 1 and f.get("port_edit"):
            editing = f["port"]
        for k in keys:
            if isinstance(k, MouseEvent):
                if k.pressed and k.button == MouseEvent.LEFT:
                    for x0_, y0_, x1, y1, i in self.click_zones:
                        if y0_ == k.y and x0_ <= k.x <= x1:
                            self.menu_index = i
                            return self._menu_select()
                continue
            if k == Key.UP:
                self.menu_index = (self.menu_index - 1) % len(items)
                f["port_edit"] = False
            elif k == Key.DOWN or k == Key.TAB:
                self.menu_index = (self.menu_index + 1) % len(items)
                f["port_edit"] = False
            elif k in (Key.LEFT, Key.RIGHT):
                d = -1 if k == Key.LEFT else 1
                if self.menu_index == 0:
                    f["players"] = min(6, max(1, f["players"] + d))
                elif self.menu_index == 1:
                    f["host_players"] = min(6, max(2, f["host_players"] + d))
            elif k == Key.ENTER:
                return self._menu_select()
            elif k == Key.ESC:
                return False
            elif editing is not None and editing.handle(k):
                pass
            elif self.menu_index == 1 and k in (ord("b"), ord("B")):
                f["bots"] = not f["bots"]
            elif self.menu_index == 1 and k in (ord("p"), ord("P")):
                f["port_edit"] = True
                f["port"].value = ""
            elif k in (ord("q"), ord("Q")) and editing is None:
                return False
        return True

    def _menu_select(self):
        f = self.form
        self.name = f["name"].value.strip() or "Player"
        i = self.menu_index
        try:
            if i == 0:
                self.session = single_player(self.name, f["players"], seed=self.seed)
                self._begin_game(self.session.start())
            elif i == 1:
                port = int(f["port"].value or DEFAULT_PORT)
                self.session = HostSession(self.name, max_players=f["host_players"], bots_on=f["bots"], port=port,
                                           seed=self.seed)
                self.mode = "lobby"
            elif i == 2:
                addr = f["address"].value.strip()
                host, _, port = addr.partition(":")
                self.session = ClientSession(self.name, host or "127.0.0.1", int(port or DEFAULT_PORT))
                self.mode = "lobby"
            elif i == 4:
                self.mode = "settings"
                self.settings_index = 0
            elif i == 5:
                return False
        except (OSError, ValueError) as e:
            self.flash(f"Couldn't: {e}")
            self.session = None
        return True

    # ---------------------------------------------------------------------------------------------- settings

    def frame_settings(self, screen, dt, keys, rows, cols):
        self._backdrop(screen, dt, rows, cols, "Settings")
        widgets = self._setting_widgets()
        x0, y0 = cols // 2 - 18, 6
        self.click_zones = []
        for i, (_, title, w, shown) in enumerate(widgets + [(None, "Back", None, None)]):
            sel = i == self.settings_index
            text = f"{title:<15} < {shown(w.value)} >" if w else title
            screen.text(y0 + 2 * i, x0 - 2, ("> " if sel else "  ") + text, Color.YELLOW if sel else Color.WHITE,
                        bold=sel)
            self.click_zones.append((x0 - 2, y0 + 2 * i, x0 + 40, y0 + 2 * i, i))
        help_ = "Up/Down choose  Left/Right change  Esc back  (kept for next time)"
        screen.text(rows - 1, 1, help_[:cols - self.controls.width - 3], Color.WHITE, dim=True)
        n = len(widgets) + 1
        for k in keys:
            step = 0
            if isinstance(k, MouseEvent):
                if k.pressed and k.button in (MouseEvent.LEFT, MouseEvent.RIGHT):
                    for x0_, y0_, x1, y1, i in self.click_zones:
                        if y0_ == k.y and x0_ <= k.x <= x1:
                            self.settings_index = i
                            step = 1 if k.button == MouseEvent.LEFT else -1
                if not step:
                    continue
            elif k == Key.UP:
                self.settings_index = (self.settings_index - 1) % n
            elif k in (Key.DOWN, Key.TAB):
                self.settings_index = (self.settings_index + 1) % n
            elif k in (Key.LEFT, Key.RIGHT, Key.ENTER, ord(" ")):
                step = -1 if k == Key.LEFT else 1
            elif k in (Key.ESC, ord("q"), ord("Q")):
                self.mode = "menu"
                return True
            if step:
                if self.settings_index == n - 1:
                    self.mode = "menu"
                    return True
                widgets[self.settings_index][2].step(step)
        return True

    # ---------------------------------------------------------------------------------------------- lobby

    def frame_lobby(self, screen, dt, keys, rows, cols):
        s = self.session
        events = s.poll(dt)
        if s.phase == "game":
            self._begin_game(events)
            return True
        if s.error and not s.is_host:
            self.flash(s.error)
            self._leave()
            return True
        self.scene.rig.yaw += dt * 0.06
        self.scene.update(dt)
        chat_h = 8
        self._draw_view(screen, 0, 0, cols, rows - 1 - chat_h)
        screen.text(1, 2, "LOBBY", Color.YELLOW, bold=True)
        if s.is_host:
            screen.text(2, 2, f"Hosting on {local_ip()}:{s.port}  (players join with this address)", Color.WHITE)
            screen.text(3, 2, f"Seats: {s.max_players}   Bots fill empty seats: {'ON' if s.bots_on else 'OFF'}",
                        Color.WHITE)
        else:
            screen.text(2, 2, f"Waiting for the host to start...  Seats: {s.max_players}", Color.WHITE)
        for i in range(max(s.max_players, len(s.seats))):
            seat = s.seats[i] if i < len(s.seats) else None
            if seat:
                tag = {"human": "(host)", "remote": "", "bot": "(bot)"}[seat["kind"]]
                screen.text(5 + i, 4, f"{i + 1}. {seat['name']} {tag}", Color.GREEN)
            else:
                screen.text(5 + i, 4, f"{i + 1}. {'(a bot will fill this)' if s.bots_on else '(open)'}", Color.WHITE,
                            dim=True)
        self._draw_chat(screen, rows - 1 - chat_h, 0, cols, chat_h)
        help_ = "+/- seats  B bots  Enter start  Tab chat  Esc leave" if s.is_host else "Tab chat  Esc leave"
        screen.text(rows - 1, 1, help_, Color.WHITE, dim=True)
        for k in keys:
            if self._chat_key(k):
                continue
            if k == Key.ESC:
                self._leave()
                return True
            if not s.is_host or isinstance(k, MouseEvent):
                continue
            if k in (ord("+"), ord("=")):
                s.set_max_players(s.max_players + 1)
            elif k == ord("-"):
                s.set_max_players(s.max_players - 1)
            elif k in (ord("b"), ord("B")):
                s.set_bots(not s.bots_on)
            elif k == Key.ENTER:
                humans = len(s.seats)
                if not s.bots_on and humans < 1:
                    self.flash("Need players")
                else:
                    self._begin_game(s.start())
        return True

    def _leave(self):
        if self.session:
            self.session.close()
        self.session = None
        self.mode = "menu"
        self.scene = BoardScene(seed=self.seed or 1, on_sound=self.sound.play)
        self._demo()

    # ---------------------------------------------------------------------------------------------- chat

    def _chime(self):
        """A soft chime when another player's chat message arrives (and count it unread while the chat is docked)."""
        s = self.session
        if s is None:
            return
        who, chimed, read = self.heard
        if who is not s:
            chimed = read = 0
        if s.heard > chimed:
            self.sound.play("chat")
        if self.chat_open or self.mode != "game":
            read = s.heard
        self.heard = (s, s.heard, read)

    def _chat_key(self, k):
        """Tab opens the chat line (multiplayer; in the game the panel slides up with it); typing goes into it until
        Enter (sent, the panel stays up) or Esc / Tab (the panel docks again)."""
        if not self.session or not self.session.networked:
            return False
        if self.chat_input is None:
            if k == Key.TAB:
                self.chat_input = TextInput("", 200)
                self.chat_open = True
                return True
            return False
        if isinstance(k, MouseEvent):
            return False
        if k == Key.ENTER:
            if self.chat_input.value.strip():
                self.session.chat(self.chat_input.value)
            self.chat_input = None
        elif k in (Key.ESC, Key.TAB):
            self.chat_input = None
            self.chat_open = False
        else:
            self.chat_input.handle(k)
        return True

    def _toggle_chat(self):
        self.chat_open = not self.chat_open
        if not self.chat_open:
            self.chat_input = None

    def _draw_chat(self, screen, top, left, width, height, bottom=None, bg=None, hint="Tab to chat"):
        """The chat: a title rule, the latest lines, the typing line. Rows from `bottom` down are left alone (the
        panel sliding out from under them); bg fills the panel's background."""
        bottom = top + height if bottom is None else bottom

        def put(y, x, text, color, **kw):
            if y < bottom:
                screen.text(y, x, text, color, bg=bg, **kw)
        if bg is not None:
            for y in range(top, top + height):
                put(y, left, " " * width, Color.WHITE)
        put(top, left, "─" * width, Color.WHITE, dim=True)
        put(top, left + 2, " Chat ", Color.CYAN)
        lines = [t for t, kind in self.session.log if kind in ("chat", "system")][-(height - 2):]
        for i, t in enumerate(lines):
            put(top + 1 + i, left + 1, t[:width - 2], Color.WHITE if ":" in t else Color.CYAN)
        y = top + height - 1
        if self.chat_input is not None:
            put(y, left + 1, ("> " + self.chat_input.value + "_")[-(width - 2):], Color.YELLOW)
        else:
            put(y, left + 1, hint, Color.WHITE, dim=True)

    def _chat_dock(self, screen, dt, view_bottom, width, bar_y, bar_right):
        """The game screen's chat (multiplayer): a Chat tab in the bottom bar (with the unread count), and the panel,
        which slides up over the bottom of the 3D view when opened and back down into the bar when closed."""
        s = self.session
        up = self.chat_open or self.chat_input is not None
        step = dt / CHAT_SLIDE
        self.chat_slide = min(1.0, self.chat_slide + step) if up else max(0.0, self.chat_slide - step)
        k = self.chat_slide
        e = k * k * (3 - 2 * k)  # ease in and out
        shown = round(CHAT_H * e)
        self.chat_rect = (0, view_bottom - shown, width - 1, view_bottom - 1) if shown else (-1, -1, -1, -1)
        if shown:
            self._draw_chat(screen, view_bottom - shown, 0, width, CHAT_H, bottom=view_bottom, bg=CHAT_BG,
                            hint="Tab to chat  (Chat in the bar, or Esc while typing, docks it)")
        unread = s.heard - self.heard[2] if self.heard[0] is s else 0
        arrow = ("▼" if up else "▲") if screen.unicode else ("v" if up else "^")
        label = f" Chat {arrow} " + (f"({unread}) " if unread and not up else "")
        x = bar_right - len(label)
        screen.text(bar_y, x, label, Color.YELLOW if unread and not up else Color.CYAN, reverse=True,
                    bold=bool(unread and not up))
        self.chat_tab = (x, bar_y, x + len(label) - 1, bar_y)
        return x

    # ---------------------------------------------------------------------------------------------- game

    def _new_scene(self):
        self.scene = BoardScene(seed=self.seed or 2, on_sound=self.sound.play)
        self.scene.my_seat = self.session.my_seat
        if self.session.is_host:
            self.session.scene_busy = self.scene.busy

    def _begin_game(self, events):
        s, g = self.session, self.session.game
        self._new_scene()
        self.mode = "game"
        self.ui = {"mode": None}
        self.chat_open, self.chat_slide, self.chat_rect = False, 0.0, (-1, -1, -1, -1)
        self.log = []
        events = [e for e in events if e.get("e") != "_sync"]
        if not (g and g.turn == 1 and g.phase == "discard" and not g.discards_used):  # (not a fresh game: just catch up)
            if g:
                self.scene.sync(g)
            self._feed(events)
            return
        # a fresh siege: an empty board, the opening words, the horn, then the first Monsters march in
        self.scene.sync(g, without=g.monsters)
        self._narrate(events)
        wave = [{"e": "spawn", "mid": mid, "kind": m["kind"], "arc": m["arc"], "ring": m["ring"], "hp": m["hp"]}
                for mid, m in sorted(g.monsters.items())]
        rest = [e for e in events if e.get("e") != "spawn"]
        if not any(e.get("e") == "turn" for e in rest):  # (a client is sent the state, not the opening events)
            rest.append({"e": "turn", "seat": g.current, "turn": g.turn})
        self.scene.play(INTRO + [{"e": "wave", "spawns": wave}] + rest)

    def _narrate(self, events):
        s = self.session
        for e in events:
            text = describe(e, s.game, s.names) if e.get("e") != "_sync" else None
            if text:
                s.say(text, "game")

    def _feed(self, events):
        if any(e.get("e") == "_sync" for e in events):
            self._new_scene()
            self.scene.sync(self.session.game)
        self._narrate(events)
        self.scene.play([e for e in events if e.get("e") != "_sync"])

    def frame_game(self, screen, dt, keys, rows, cols):
        s = self.session
        g = s.game
        events = s.poll(dt)
        if events:
            self._feed(events)
        if s.error and not s.is_host:
            self.flash(s.error)
        self.scene.update(dt)
        # keep the scene honest: once it is quiet, match the state exactly
        self.last_sync += dt
        if g and not self.scene.busy() and self.last_sync > 1.5:
            self.last_sync = 0
            self.scene.sync(s.game)
        g = s.game
        side = 38 if cols >= 140 else 32
        hand_h = 8
        view_h = rows - 1 - hand_h - 1
        view_w = cols - side
        self.scene.aspect = view_w * self.renderer.cell_aspect / max(view_h, 1)
        self._draw_view(screen, 1, 0, view_w, view_h)
        if not self.scene.banners:
            self._labels(screen)
        self._status(screen, cols)
        self._side(screen, 1, view_w, side, view_h)
        order_w = ORDER_W if cols >= 110 else ORDER_NARROW
        self._hand(screen, 1 + view_h, 0, cols - order_w, hand_h)
        self._order(screen, 1 + view_h, cols - order_w, order_w, hand_h)
        bar_right = cols - self.controls.width - 2
        if s.networked:
            bar_right = self._chat_dock(screen, dt, 1 + view_h, view_w, rows - 1, bar_right) - 1
        help_ = "1-9 card  N/Enter next step  X discard  T trade  arrows/+/- camera  R view  H help  M sound  Q quit"
        if s.networked:
            help_ += "  Tab chat"
        screen.text(rows - 1, 1, help_[:max(0, bar_right - 2)], Color.WHITE, dim=True)
        self._popups(screen, rows, cols)
        if self.ui.get("help"):
            self._help(screen, rows, cols)
        for k in keys:
            if self._chat_key(k):
                continue
            if k in (ord("h"), ord("H"), Key.F1) or (self.ui.get("help") and k == Key.ESC):
                self.ui["help"] = not self.ui.get("help")
                continue
            if self.scene.banners and k in SKIP_KEYS:
                self.scene.skip_banners()
                continue
            if isinstance(k, MouseEvent):
                self._mouse(k)
                continue
            self._key(k)
            if self.ui.get("quit"):
                return False
        return True

    # ---- drawing
    def _shown(self):
        """(seat, step, turn) as shown: the animations' while they run (the state is ahead of them: once the new
        Monsters are drawn it is already the next player's turn), else the game's."""
        g = self.session.game
        if self.scene.busy() and self.scene.step and self.scene.turn and g.phase != "over":
            return (*self.scene.step, self.scene.turn)
        return g.current, g.phase, g.turn

    def _status(self, screen, cols):
        g, s = self.session.game, self.session
        seat, phase, turn = self._shown()
        who = s.names[seat]
        mine = seat == s.my_seat
        step = f"Step {STEPS.index(phase) + 1}: " if phase in STEPS else ""
        txt = f" Turn {turn}  {who}{' (you)' if mine else ''}: {step}{STEP_TITLES.get(phase, phase)}"
        screen.text(0, 0, " " * cols, Color.WHITE, reverse=True)
        screen.text(0, 0, txt, Color.YELLOW if mine else Color.WHITE, reverse=True, bold=mine)
        towers = "".join("♖" if t else "." for t in g.towers) if screen.unicode else \
            "".join("T" if t else "." for t in g.towers)
        right = f"Towers {towers}  Walls {sum(g.walls)}/6  Monsters left {len(g.pile)}  Deck {len(g.deck)} "
        screen.text(0, cols - len(right), right, Color.WHITE, reverse=True)

    def _spot(self, point, text, owner=None, hide=True):
        """Where (row, column) a label for a world point would start on screen; None if hidden or off the view."""
        top, left, w, h = self.view
        anchor = self.renderer.anchor(point, owner)
        if anchor is None or (hide and anchor.hidden):
            return None
        x, y = left + anchor.x - len(text) // 2, top + anchor.y
        return None if x < left or x + len(text) > left + w else (y, x)

    @staticmethod
    def _free(used, spot, text, pad=1, rows=0):
        """Whether a label at spot keeps pad columns (and rows rows) clear of those already put (used: row -> spans)."""
        y, x = spot
        return not any(x - pad < b and a < x + len(text) + pad
                       for yy in range(y - rows, y + rows + 1) for a, b in used.get(yy, ()))

    def _put(self, screen, used, spot, text, color, bold=False):
        y, x = spot
        used.setdefault(y, []).append((x, x + len(text)))
        screen.text(y, x, text, color, bold=bold)

    def _labels(self, screen):
        """Health pips over every Monster; target letters while choosing; wall numbers while choosing a wall;
        ring names along the lines where the colours change; arc numbers round the forest edge. Monsters' labels
        come first; the board's give way to them and to each other."""
        top, left, w, h = self.view
        ui = self.ui
        letters = ui.get("letters", {})
        used = {}
        for mid, a in self.scene.monsters.items():
            m = self.scene.mdata.get(mid)
            if not m or a.dead:
                continue
            pips = HP_PIP * m["hp"] + "○" * (m["max"] - m["hp"]) if screen.unicode else "o" * m["hp"]
            tag = f"[{letters[mid]}]" if mid in letters else ""
            if SHOW_TAGS:
                tag += MONSTER_TAG.get(m["kind"], "") + " "
            color = Color.YELLOW if mid in letters else (Color.RED if m["ring"] <= 1 else Color.WHITE)
            if m.get("tar"):
                tag += "~"
            text = tag + pips
            anchor = screen.label(self.renderer, a.top(), text, color, top=top, left=left, owner=a.model, hide=False,
                                  bold=mid in letters)
            if anchor:
                x = left + anchor.x - len(text) // 2
                used.setdefault(top + anchor.y, []).append((x, x + len(text)))
        if ui.get("mode") == "wall":
            for arc in ui.get("arcs", []):
                p, _, _ = board.wall_position(arc)
                screen.label(self.renderer, p + (0, 1.6, 0), f"[{arc + 1}]", Color.YELLOW, top=top, left=left,
                             hide=False, bold=True)
        # arc numbers around the forest edge
        for arc in range(ARCS):
            p = board.polar(board.arc_angle(arc), 9.0, 0.1)
            col = {"red": Color.RED, "green": Color.GREEN, "blue": Color.BLUE}[arc_color(arc)]
            spot = self._spot(p, str(arc + 1), self.scene.ground)
            if spot and self._free(used, spot, str(arc + 1), pad=0):
                self._put(screen, used, spot, str(arc + 1), col, bold=True)
        # ring names on the lines between the colours, nearest the camera first; a line's names show all together
        # (those not hidden behind something) or not at all, so a half-labelled line never misleads; zoomed far out,
        # only the nearest line's, as the rings are too thin on screen for more
        eye = self.scene.rig.camera.position
        lines = sorted((0, 2, 4), key=lambda arc: np.linalg.norm(board.polar(board.arc_angle(arc, 0.0), 5.0) - eye))
        if self.scene.rig.dist > RING_LABELS_FAR:
            lines = lines[:1]
        for arc in lines:
            names = []
            for ring in (ARCHER, KNIGHT, SWORDSMAN):
                p = board.polar(board.arc_angle(arc, 0.0), board.ring_mid(ring), 0.1)
                spot = self._spot(p, RING_LABEL[ring], self.scene.ground)
                if spot:
                    names.append((spot, RING_LABEL[ring]))
            line = {}  # this line's names so far, which mustn't crowd each other either
            fits = True
            for sp, t in names:
                fits = fits and self._free(used, sp, t, rows=1) and self._free(line, sp, t, rows=1)
                line.setdefault(sp[0], []).append((sp[1], sp[1] + len(t)))
            if fits:
                for sp, t in names:
                    self._put(screen, used, sp, t, Color.WHITE)

    def _side(self, screen, top, x, width, height):
        s, g = self.session, self.session.game
        for yy in range(top, top + height):
            screen.text(yy, x, "│" if screen.unicode else "|", Color.WHITE, dim=True)
        x += 2
        width -= 3
        y = top
        screen.text(y, x, "Defenders", Color.CYAN, bold=True)
        y += 1
        self.side_boxes = []
        for i, name in enumerate(s.names):
            cur = i == g.current
            mark = "▶" if cur and screen.unicode else (">" if cur else " ")
            you = "*" if i == s.my_seat else ""
            line = f"{mark}{i + 1} {name[:12]}{you}"
            partner = self.ui.get("partner") == i
            screen.text(y, x, line, Color.YELLOW if cur else Color.WHITE, bold=cur or partner, reverse=partner)
            sc = f"{g.score(i)}pt"
            screen.text(y, x + width - len(sc), sc, Color.WHITE)
            self.side_boxes.append((x, y, x + width - 1, y, i, None))
            y += 1
            xx = x + 2
            for k, c in enumerate(g.hand(i)):
                cid = g.hands[i][k]
                lab = SHORT[c["kind"]]
                if self.ui.get("mode") == "trade_take" and partner:
                    lab = f"{LETTERS[k]}{lab}"
                if xx + len(lab) >= x + width:
                    break
                screen.text(y, xx, lab, card_color(c), reverse=self.ui.get("take") == cid)
                self.side_boxes.append((xx, y, xx + len(lab) - 1, y, i, cid))
                xx += len(lab) + 1
            y += 1
        y += 1
        if y < top + height - 2:
            screen.text(y, x, "Log", Color.CYAN, bold=True)
            y += 1
            room = top + height - y
            lines = []
            for t, kind in s.log:
                if kind == "chat" and s.networked:
                    continue
                while len(t) > width:
                    lines.append(t[:width])
                    t = "  " + t[width:]
                lines.append(t)
            for t in lines[-room:]:
                col = Color.WHITE
                if t.startswith("---"):
                    col = Color.YELLOW
                elif "slain" in t or "VICTORY" in t:
                    col = Color.GREEN
                elif "falls" in t or "smashed" in t or "DEFEAT" in t or "Boulder" in t:
                    col = Color.RED
                elif t.startswith("Monster token"):
                    col = Color.MAGENTA
                screen.text(y, x, t, col)
                y += 1

    def next_live(self):
        """Whether the Next Step button is mine to press now."""
        s, g = self.session, self.session.game
        return (g.current == s.my_seat and g.phase in STEPS and g.phase != "draw_monsters" and not g.pending
                and not g.trade_offer and not self.scene.busy())

    def _order(self, screen, top, x, width, height):
        """The Order of play: the six steps of a turn, the one we're on lit, and the button to go on to the next."""
        g = self.session.game
        _, phase, _ = self._shown()
        bar = "─" if screen.unicode else "-"
        screen.text(top, x, bar * width, Color.WHITE, dim=True)
        screen.text(top, x + 2, " Order of play ", Color.CYAN, bold=True)
        for yy in range(top + 1, top + height):
            screen.text(yy, x, "│" if screen.unicode else "|", Color.WHITE, dim=True)
        x += 2
        width -= 3
        now = STEPS.index(phase) if phase in STEPS else len(STEPS)
        title = STEP_TITLES.get(phase, phase)
        screen.text(top + 1, x, f"Step: {title}"[:width], Color.YELLOW, bold=True)
        mark = "▶" if screen.unicode else ">"
        if width >= 36:  # all six steps, in two columns
            for i, step in enumerate(STEPS):
                col, row = divmod(i, 3)
                label = f"{mark if i == now else ' '}{i + 1} {STEP_TITLES[step]}"
                skipped = step == "trade" and not g.max_trades
                screen.text(top + 2 + row, x + col * 20, label, Color.YELLOW if i == now else Color.WHITE,
                            bold=i == now, reverse=i == now, dim=i < now or skipped)
        else:  # narrow: where we are and what comes next
            screen.text(top + 2, x, f"Step {min(now + 1, 6)} of 6"[:width], Color.WHITE)
            if now < len(STEPS) - 1:
                screen.text(top + 3, x, f"then: {STEP_TITLES[STEPS[now + 1]]}"[:width], Color.WHITE, dim=True)
        live = self.next_live()
        nxt = STEPS[now + 1] if now < len(STEPS) - 1 else None
        if phase == "trade" or (phase == "discard" and not g.max_trades):
            nxt = "play"
        label = "NEXT STEP"
        if nxt and width >= 30:
            label += f": {STEP_TITLES[nxt]}"
        w = min(width, max(24, len(label) + 4))
        tl, tr, bl, br, hz, vt = "╭╮╰╯─│" if screen.unicode else "++++-|"
        col = Color.YELLOW if live else Color.WHITE
        y = top + height - 3
        screen.text(y, x, tl + hz * (w - 2) + tr, col, dim=not live)
        screen.text(y + 1, x, vt, col, dim=not live)
        screen.text(y + 1, x + 1, label.center(w - 2)[:w - 2], col, bold=live, dim=not live, reverse=live)
        screen.text(y + 1, x + w - 1, vt, col, dim=not live)
        screen.text(y + 2, x, bl + hz * (w - 2) + br, col, dim=not live)
        self.next_box = (x, y, x + w - 1, y + 2)

    def _hand(self, screen, top, left, width, height):
        s, g = self.session, self.session.game
        me = s.my_seat
        screen.text(top, left, "─" * width if screen.unicode else "-" * width, Color.WHITE, dim=True)
        hand = g.hand(me)
        n = max(1, len(hand))
        cw = max(9, min(15, (width - 2) // n))
        self.hand_boxes = []
        sel = self.ui.get("card")
        h = "─" if screen.unicode else "-"
        v = "│" if screen.unicode else "|"
        tl, tr, bl, br = ("┌", "┐", "└", "┘") if screen.unicode else ("+", "+", "+", "+")
        for i, c in enumerate(hand):
            x = left + 1 + i * cw
            if x + cw > left + width:
                break
            col = card_color(c)
            chosen = sel == c["id"] or c["id"] in self.ui.get("chosen", ())
            ok = g.playable(me, c["id"]) or (g.current == me and (
                g.phase == "discard" and g.discards_used < g.max_discards or
                g.phase == "trade" and g.trades_used < g.max_trades))
            dim = not ok and not chosen
            title = CARD_TITLE_SHORT(c)
            ring = ""
            if c["kind"] in HIT_RING:
                ring = RING_NAMES[HIT_RING[c["kind"]]] + " ring"
            elif c["kind"] == "hero":
                ring = "Any ring"
            color_name = (c["color"] or "").capitalize() if c["color"] and c["color"] != "any" else (
                "Any colour" if c["color"] == "any" else "")
            iw = cw - 2
            rows_ = [f"{i + 1} {color_name}"[:iw], title[:iw], ring[:iw]]
            screen.text(top + 1, x, tl + h * (cw - 3) + tr, col, bold=chosen, dim=dim)
            for r, t in enumerate(rows_):
                screen.text(top + 2 + r, x, v + t.ljust(cw - 3)[:cw - 3] + v, col, bold=chosen, dim=dim,
                            reverse=chosen)
            screen.text(top + 5, x, bl + h * (cw - 3) + br, col, bold=chosen, dim=dim)
            self.hand_boxes.append((x, top + 1, x + cw - 2, top + 5, c["id"]))
        prompt = self._prompt()
        screen.text(top + 6, left + 1, prompt[:width - 2], Color.YELLOW if g.current == me else Color.WHITE,
                    bold=g.current == me)
        if self.message_t > 0:
            screen.text(top + 7, left + 1, self.message[:width - 2], Color.RED, bold=True)
        elif self.ui.get("card") is not None:
            c = g.cards[self.ui["card"]]
            screen.text(top + 7, left + 1, f"{card_title(c)}: {CARD_HELP[c['kind']]}"[:width - 2], Color.WHITE)

    def _prompt(self):
        s, g, ui = self.session, self.session.game, self.ui
        me = s.my_seat
        mode = ui.get("mode")
        if g.phase == "over":
            return ("VICTORY! " if g.result == "won" else "DEFEAT. ") + (
                "P play again, Q quit" if s.is_host else "Q quit")
        if g.pending.get(me) == "discard1":
            if mode == "forced_discard":
                return f"Discard {card_title(g.cards[ui['card']])}? Click it again (or press its number)"
            return "All players discard 1 card: click it twice, or press its number"
        if g.trade_offer and g.trade_offer["to"] == me:
            o = g.trade_offer
            return (f"{s.names[o['from']]} offers {card_title(g.cards[o['give']])} for your "
                    f"{card_title(g.cards[o['take']])}: Y accept, N decline")
        if mode == "target":
            return "Choose a Monster: its letter or click it (Esc cancels)"
        if mode == "wall":
            return "Choose a Wall: its number (Esc cancels)"
        if mode == "nice":
            return "Nice Shot: now choose the hit card to play it with (Esc cancels)"
        if mode == "scavenge":
            return "Scavenge: choose a card from the discard pile (letter, Esc cancels)"
        if mode == "discard":
            return f"Discard {card_title(g.cards[ui['card']])} and draw a new card? Click it again or X (Esc cancels)"
        if mode == "pair":
            return f"{card_title(g.cards[ui['card']])}: now choose a {ui['need'].capitalize()} to go with it (Esc cancels)"
        if mode == "trade_give":
            if ui.get("take") is not None:
                return (f"Trade for {s.names[ui['partner']]}'s {card_title(g.cards[ui['take']])}: which of your cards "
                        "do you give? (click or number, Esc cancels)")
            return "Trade: which of your cards do you give? (click or number, Esc cancels)"
        if mode == "trade_partner":
            return "Trade with whom? Click their name or the card you want in Defenders, or their number (Esc cancels)"
        if mode == "trade_take":
            return f"Which of {s.names[ui['partner']]}'s cards do you want? (click or letter, Esc cancels)"
        if g.trade_offer:
            return f"Waiting for {s.names[g.trade_offer['to']]} to answer the trade..."
        if g.pending:
            return "Waiting for players to discard..."
        if self.scene.busy() and g.current != me:
            return "..."
        if g.current != me:
            return f"{s.names[g.current]} is defending..."
        if self.scene.busy():
            return "..."
        if g.phase == "discard":
            if g.discards_used >= g.max_discards:
                return "Discarded. Next Step to " + ("trade" if g.max_trades else "play cards")
            return "Discard a card and draw a new one: click it (optional), or Next Step to pass"
        if g.phase == "trade":
            if g.trades_used >= g.max_trades:
                return "Traded. Next Step to play cards"
            return "Trade: click a card of yours to give, or one of theirs in Defenders (optional), or Next Step to pass"
        if g.phase == "play":
            return "Play cards (click or number), then Next Step: the Monsters move"
        if g.phase == "move":
            return "The Monsters have moved. Next Step: draw 2 new Monsters"
        return "..."

    def _help(self, screen, rows, cols):
        w = max(len(t) for t in HELP) + 4
        x, y = max(0, (cols - w) // 2), max(1, (rows - len(HELP) - 2) // 2)
        for i, t in enumerate([""] + HELP + [""]):
            screen.text(y + i, x, ("  " + t).ljust(w), Color.YELLOW if i == 1 else Color.WHITE, reverse=True,
                        bold=i == 1)

    def _popups(self, screen, rows, cols):
        g = self.session.game
        if self.ui.get("mode") == "scavenge":
            pile = g.discard_pile[-26:]
            w, h = 36, min(len(pile), 20) + 2
            x, y = (cols - w) // 2, max(2, (rows - h) // 2)
            screen.text(y, x, " Discard pile ".center(w, "="), Color.YELLOW, reverse=True)
            self.ui["pile"] = list(reversed(pile))[:20]
            for i, cid in enumerate(self.ui["pile"]):
                c = g.cards[cid]
                screen.text(y + 1 + i, x, f" {LETTERS[i]}  {card_title(c)}".ljust(w), card_color(c), reverse=True)
        if g.phase == "over":
            w = 44
            x, y = (cols - w) // 2, 4
            res = "VICTORY - the Castle stands!" if g.result == "won" else "DEFEAT - the Castle has fallen"
            screen.text(y, x, f" {res} ".center(w), Color.GREEN if g.result == "won" else Color.RED, reverse=True,
                        bold=True)
            order = sorted(range(g.players), key=lambda i: (g.score(i), len(g.trophies[i])), reverse=True)
            for k, i in enumerate(order):
                crown = " Master Slayer" if g.result == "won" and k == 0 and g.master_slayer() == i else ""
                screen.text(y + 1 + k, x, f" {self.session.names[i][:16]:16} {g.score(i):3} pts "
                                          f"{len(g.trophies[i]):2} slain{crown}".ljust(w), Color.WHITE, reverse=True)

    # ---- input
    def _mouse(self, ev):
        x0, y0, x1, y1 = self.chat_tab
        if self.session.networked and x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
            if ev.pressed and ev.button == MouseEvent.LEFT and not ev.moved:
                self._toggle_chat()
            return
        x0, y0, x1, y1 = self.chat_rect
        if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
            return  # (the chat panel, over the 3D view)
        if self._mouse_view(ev):
            return
        if not (ev.pressed and ev.button == MouseEvent.LEFT) or ev.moved:
            return
        x0, y0, x1, y1 = self.next_box
        if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
            if self.session.game.current == self.session.my_seat:
                self._next()
            return
        for x0, y0, x1, y1, cid in self.hand_boxes:
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                hand = self.session.game.hands[self.session.my_seat]
                if cid in hand:
                    self._card_key(hand.index(cid))
                return
        for x0, y0, x1, y1, seat, cid in self.side_boxes:
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                self._side_click(seat, cid)
                return
        top, left, w, h = self.view
        if left <= ev.x < left + w and top <= ev.y < top + h:
            mid = self.scene.monster_at_cell(self.renderer, ev.x - left, ev.y - top)
            if mid is not None and self.ui.get("mode") == "target" and mid in self.ui.get("letters", {}):
                self._choose_monster(mid)

    def _side_click(self, seat, cid):
        """A click on a Defender's name or one of their cards: in your Trade step, whom to trade with and for what."""
        s, g, ui = self.session, self.session.game, self.ui
        me = s.my_seat
        if seat == me:
            if cid in g.hands[me]:
                self._card_key(g.hands[me].index(cid))
            return
        if not (g.current == me and g.phase == "trade" and g.trades_used < g.max_trades and not g.trade_offer):
            if g.current == me and g.phase in ("discard", "trade") and not g.trade_offer:
                self.flash("No more trades this turn" if g.phase == "trade" else "Trading is step 3, after discarding")
            return
        if seat in g.traded_with:
            self.flash(f"You've traded with {s.names[seat]} already: the second trade is with someone else")
            return
        if not g.hands[seat]:
            self.flash(f"{s.names[seat]} has no cards")
            return
        give = ui.get("give") if ui.get("mode") in ("trade_partner", "trade_take") else None
        if give is None:  # theirs first: then which of yours
            self.ui = {"mode": "trade_give", "partner": seat, "take": cid}
        elif cid is None:
            self.ui = dict(ui, mode="trade_take", partner=seat)
        else:
            self._send({"a": "offer", "to": seat, "give": give, "take": cid})
            self._reset_ui()

    def _send(self, action):
        try:
            events = self.session.act(action)
            if events:
                self._feed(events)
            return True
        except IllegalMove as e:
            self.flash(str(e))
            return False

    def _reset_ui(self):
        self.ui = {"mode": None}

    def _key(self, k):
        s, g, ui = self.session, self.session.game, self.ui
        me = s.my_seat
        ch = chr(k).lower() if isinstance(k, int) and 32 <= k < 127 else None
        if k == Key.ESC:
            if ui.get("mode"):
                self._reset_ui()
            return
        mode = ui.get("mode")
        # answers others are waiting on
        if g.trade_offer and g.trade_offer["to"] == me and ch in ("y", "n"):
            self._send({"a": "answer", "accept": ch == "y"})
            return
        if g.pending.get(me) == "discard1" and ch and ch.isdigit():
            hand = g.hands[me]
            i = int(ch) - 1
            if 0 <= i < len(hand):
                self._send({"a": "forced_discard", "card": hand[i]})
                self._reset_ui()
            return
        if mode == "target" and ch and ch in LETTERS:
            for mid, letter in ui["letters"].items():
                if letter == ch:
                    self._choose_monster(mid)
                    return
            return
        if mode == "wall" and ch and ch.isdigit():
            arc = int(ch) - 1
            if arc in ui["arcs"]:
                self._send(dict(ui["action"], target=arc))
                self._reset_ui()
            return
        if mode == "scavenge" and ch and ch in LETTERS:
            i = LETTERS.index(ch)
            if i < len(ui.get("pile", [])):
                self._send({"a": "play", "card": ui["card"], "target": ui["pile"][i]})
                self._reset_ui()
            return
        if mode == "trade_partner" and ch and ch.isdigit():
            p = int(ch) - 1
            if 0 <= p < g.players and p != me and g.hands[p]:
                ui["partner"] = p
                ui["mode"] = "trade_take"
            return
        if mode == "trade_take" and ch and ch in LETTERS:
            i = LETTERS.index(ch)
            hand = g.hands[ui["partner"]]
            if i < len(hand):
                self._send({"a": "offer", "to": ui["partner"], "give": ui["give"], "take": hand[i]})
                self._reset_ui()
            return
        if ch == "q":
            if self.quit_armed > 0 or g.phase == "over":
                self._leave()
            else:
                self.quit_armed = 2.0
                self.flash("Press Q again to leave the game")
            return
        if ch == "m":
            self.flash("Sound on" if self.sound.toggle() else "Sound off")
            return
        if ch == "p" and g.phase == "over" and s.is_host:
            self._begin_game(s.restart())
            return
        if ch and ch.isdigit() and ch != "0":
            self._card_key(int(ch) - 1)
            return
        if self._camera_keys(k):
            return
        if g.current != me:
            return
        if ch == "x":
            if g.phase != "discard":
                self.flash("Discarding is step 2, after drawing up")
            elif mode == "discard":
                self._send({"a": "discard", "card": ui["card"]})
                self._reset_ui()
            else:
                self.flash("Click (or number) the card to discard")
        elif ch == "t":
            if g.players < 2:
                self.flash("No one to trade with in a solo game")
            elif g.phase != "trade":
                self.flash("Trading is step 3, after discarding")
            else:
                self.ui = {"mode": "trade_give"}
        elif ch == "n" or k == Key.ENTER and not mode:
            self._next()

    def _next(self):
        """On to the next step of the turn (the NEXT STEP button, N or Enter)."""
        if self.scene.busy():
            self.flash("Wait for the action to finish")
        elif self.next_live():
            self._reset_ui()
            self._send({"a": "next"})

    def _card_key(self, i):
        s, g, ui = self.session, self.session.game, self.ui
        me = s.my_seat
        hand = g.hands[me]
        if not 0 <= i < len(hand):
            return
        cid = hand[i]
        mode = ui.get("mode")
        if g.pending.get(me) == "discard1":  # (a Monster token's "All Players Discard 1 Card": click twice)
            if mode == "forced_discard" and ui["card"] == cid:
                self._send({"a": "forced_discard", "card": cid})
                self._reset_ui()
            else:
                self.ui = {"mode": "forced_discard", "card": cid, "chosen": [cid]}
            return
        if mode == "discard" and ui["card"] == cid:
            self._send({"a": "discard", "card": cid})
            self._reset_ui()
            return
        if mode == "pair":
            kind = g.cards[cid]["kind"]
            if cid == ui["card"]:
                self._reset_ui()
            elif kind == ui["need"]:
                brick, mortar = (ui["card"], cid) if kind == "mortar" else (cid, ui["card"])
                arcs = [a for a in range(ARCS) if not g.walls[a]]
                self.ui = {"mode": "wall", "arcs": arcs, "action": {"a": "play", "card": brick, "extra": mortar},
                           "chosen": [brick, mortar], "card": ui["card"]}
            else:
                self.flash(f"Choose a {ui['need'].capitalize()} to go with it (Esc cancels)")
            return
        if mode in ("trade_give", "trade_partner", "trade_take") or (mode is None and g.current == me and g.phase == "trade" and
                                    g.trades_used < g.max_trades and not g.trade_offer):
            if ui.get("take") is not None:  # (their card was clicked first)
                self._send({"a": "offer", "to": ui["partner"], "give": cid, "take": ui["take"]})
                self._reset_ui()
            elif ui.get("partner") is not None:
                self.ui = {"mode": "trade_take", "partner": ui["partner"], "give": cid, "chosen": [cid]}
            else:
                self.ui = {"mode": "trade_partner", "give": cid, "chosen": [cid]}
            return
        if mode == "nice":
            c = g.cards[cid]
            if c["kind"] not in ("archer", "knight", "swordsman", "hero"):
                self.flash("Choose a hit card (Archer, Knight, Swordsman, Hero)")
                return
            targets = g.targets(cid)
            if not targets:
                self.flash("That card can't hit anything now")
                return
            self._target_mode({"a": "play", "card": ui["card"], "extra": cid}, targets, chosen=[ui["card"], cid])
            return
        if g.current != me:
            self.ui = {"mode": None, "card": cid}
            return
        if self.scene.busy():
            self.flash("Wait for the action to finish")
            return
        c = g.cards[cid]
        kind = c["kind"]
        if g.phase == "discard":
            if g.discards_used >= g.max_discards:
                self.ui = {"mode": None, "card": cid}
                self.flash("No more discards this turn: Next Step to go on")
            else:
                self.ui = {"mode": "discard", "card": cid, "chosen": [cid]}
            return
        if g.phase != "play":
            self.ui = {"mode": None, "card": cid}
            if g.phase in ("draw_up", "trade"):
                self.flash("Cards are played in step 4: Next Step to go on")
            return
        if not g.playable(me, cid):
            self.ui = {"mode": None, "card": cid}
            self.flash(f"{card_title(c)} can't be played now")
            return
        if kind in ("archer", "knight", "swordsman", "hero", "barbarian", "tar", "drive_back"):
            self._target_mode({"a": "play", "card": cid}, g.targets(cid), chosen=[cid])
        elif kind in ("brick", "mortar"):  # choose the other half too, then the Wall
            self.ui = {"mode": "pair", "card": cid, "chosen": [cid], "need": "mortar" if kind == "brick" else "brick"}
        elif kind == "fortify":
            arcs = [a for a in range(ARCS) if g.walls[a] and not g.fortified[a]]
            self.ui = {"mode": "wall", "arcs": arcs, "action": {"a": "play", "card": cid}, "chosen": [cid],
                       "card": cid}
        elif kind == "nice_shot":
            self.ui = {"mode": "nice", "card": cid, "chosen": [cid]}
        elif kind == "scavenge":
            self.ui = {"mode": "scavenge", "card": cid, "chosen": [cid]}
        else:  # missing, draw2
            self._send({"a": "play", "card": cid})
            self._reset_ui()

    def _target_mode(self, action, targets, chosen):
        ms = self.session.game.monsters
        order = sorted(targets, key=lambda m: (ms[m]["ring"], ms[m]["arc"], m))
        letters = {mid: LETTERS[i] for i, mid in enumerate(order[:26])}
        self.ui = {"mode": "target", "action": action, "letters": letters, "chosen": chosen, "card": chosen[0]}
        if len(order) == 1:
            pass  # still ask: a mis-key shouldn't play a card

    def _choose_monster(self, mid):
        self._send(dict(self.ui["action"], target=mid))
        self._reset_ui()


def CARD_TITLE_SHORT(c):
    from .rules import CARD_TITLES
    t = CARD_TITLES[c["kind"]]
    return {"Drive Him Back!": "Drive Back", "Fortify Wall": "Fortify", "Draw 2 Cards": "Draw 2"}.get(t, t)
