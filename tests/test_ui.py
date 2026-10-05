import json
import os
import tempfile
import unittest
import unittest.mock

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
        with tempfile.TemporaryDirectory() as config, unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config}):
            screen = Screen(None, size=(30, 100))
            app = App("Test", sound=False, seed=1)
            app.frame(screen, 1 / 30, [])
            self.assertEqual((app.detail.value, app.renderer.simplify), ("standard", 1.0))
            app.mode, app.settings_index = "settings", 0
            app.frame(screen, 1 / 30, [Key.DOWN] * 5 + [Key.RIGHT])  # (Detail is the sixth line)
            app.frame(screen, 1 / 30, [])
            self.assertEqual((app.detail.value, app.renderer.simplify), ("high", 0.0))
            with open(os.path.join(config, "castlepanic", "settings.json")) as f:
                self.assertEqual(json.load(f)["detail"], "high")
            again = App("Test", sound=False, seed=1)
            self.assertEqual(again.renderer.simplify, 0.0)


if __name__ == "__main__":
    unittest.main()
