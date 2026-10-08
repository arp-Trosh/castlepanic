import json
import os
import tempfile
import unittest
import unittest.mock

from castlepanic.session import single_player
from castlepanic.ui import App, _port
from unicode3d.keys import Key
from unicode3d.terminal import Screen


class Ports(unittest.TestCase):
    def test_port(self):
        self.assertEqual(_port(""), 5555)
        self.assertEqual(_port(" 6000 "), 6000)
        for bad in ("0", "70000", "-1", "abc"):
            with self.assertRaises(ValueError):
                _port(bad)


class Settings(unittest.TestCase):
    def test_detail_is_a_setting_kept_for_next_time(self):
        with tempfile.TemporaryDirectory() as config, unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config, "APPDATA": config}):
            screen = Screen(None, size=(30, 100))
            app = App("Test", sound=False, seed=1)
            app.frame(screen, 1 / 30, [])
            self.assertEqual((app.controls.detail.value, app.renderer.simplify), ("standard", 1.0))
            app.mode, app.settings_index = "settings", 0
            app.frame(screen, 1 / 30, [Key.DOWN] * 5 + [Key.RIGHT])  # (Detail is the sixth line)
            app.frame(screen, 1 / 30, [])
            self.assertEqual((app.controls.detail.value, app.renderer.simplify), ("high", 0.0))
            with open(os.path.join(config, "castlepanic", "settings.json")) as f:
                self.assertEqual(json.load(f)["detail"], "high")
            again = App("Test", sound=False, seed=1)
            self.assertEqual(again.renderer.simplify, 0.0)

    def test_quality_starts_on_auto_and_is_kept_for_next_time(self):
        with tempfile.TemporaryDirectory() as config, unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config, "APPDATA": config}):
            screen = Screen(None, size=(30, 100))
            app = App("Test", sound=False, seed=1)
            app.frame(screen, 1 / 30, [])
            self.assertEqual(app.controls.auto_quality.mode, "auto")
            app.mode, app.settings_index = "settings", 0
            app.frame(screen, 1 / 30, [Key.DOWN] * 6 + [Key.LEFT])  # (Quality is the seventh line: auto -> low)
            app.frame(screen, 1 / 30, [])
            self.assertEqual((app.controls.auto_quality.mode, app.renderer.edge_samples), ("low", 0))
            self.assertEqual(app.controls.detail.value, "standard")  # (the user's detail, not the step's)
            with open(os.path.join(config, "castlepanic", "settings.json")) as f:
                self.assertEqual(json.load(f)["quality"], "low")
            again = App("Test", sound=False, seed=1)
            again.frame(screen, 1 / 30, [])
            self.assertEqual(again.controls.auto_quality.mode, "low")

    def test_quality_saved_as_fast_loads_as_low(self):
        # unicode3d called its lowest quality preset "fast" before 0.17; settings saved then still load.
        with tempfile.TemporaryDirectory() as config, unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config, "APPDATA": config}):
            os.makedirs(os.path.join(config, "castlepanic"))
            with open(os.path.join(config, "castlepanic", "settings.json"), "w") as f:
                json.dump({"quality": "fast", "detail": "high"}, f)
            screen = Screen(None, size=(30, 100))
            app = App("Test", sound=False, seed=1)
            app.frame(screen, 1 / 30, [])
            self.assertEqual((app.controls.auto_quality.mode, app.renderer.simplify), ("low", 2.0))

    def test_every_settings_line_fits_the_smallest_screen(self):
        with tempfile.TemporaryDirectory() as config, unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config, "APPDATA": config}):
            screen = Screen(None, size=(20, 70))
            app = App("Test", sound=False, seed=1)
            app.mode = "settings"
            app.frame(screen, 1 / 30, [])
            lines = ["".join(row) for row in screen.chars]
            self.assertTrue(any("Back" in line for line in lines[:-1]))
            self.assertTrue(any("Quality" in line for line in lines[:-1]))


class Chime(unittest.TestCase):
    def test_another_players_trade_with_me_chimes_like_chat(self):
        app = App("Test", sound=False, seed=1)
        app.session = single_player("Test", 3, seed=1)
        app.session.start()
        a, b = list(app.session.game.cards)[:2]
        heard = []
        app.sound.play = lambda name, **kw: heard.append(name)
        for e in ({"e": "offer", "from": 0, "to": 1, "give": a, "take": b},  # (my own doing: no chime)
                  {"e": "offer", "from": 1, "to": 2, "give": a, "take": b},  # (between two others: no chime)
                  {"e": "trade", "from": 1, "to": 2, "give": a, "take": b},
                  {"e": "cancelled", "seat": 1, "from": 1, "to": 2, "give": a, "take": b}):
            app._narrate([e])
        self.assertEqual(heard, [])
        for e in ({"e": "offer", "from": 1, "to": 0, "give": b, "take": a},
                  {"e": "trade", "from": 0, "to": 1, "give": a, "take": b},
                  {"e": "declined", "from": 0, "to": 2, "give": a, "take": b},
                  {"e": "cancelled", "seat": 1, "from": 1, "to": 0, "give": b, "take": a}):
            app._narrate([e])
        self.assertEqual(heard, ["chat"] * 4)

    def test_a_taken_back_offer_says_whom_it_was_to(self):
        g = single_player("Test", 2, seed=1)
        g.start()
        g = g.game
        g.phase, g.current = "trade", 0
        g.offer_trade(0, 1, g.hands[0][0], g.hands[1][0])
        g.take_events()
        g.cancel_trade(0)
        e = g.take_events()[-1]
        self.assertEqual((e["e"], e["seat"], e["from"], e["to"]), ("cancelled", 0, 0, 1))

if __name__ == "__main__":
    unittest.main()
