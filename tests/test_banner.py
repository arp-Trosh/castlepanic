import unittest

from castlepanic.banner import Banner


class Banners(unittest.TestCase):
    def test_hidden_until_placed(self):
        # a banner made after this frame's update() would otherwise draw its letters at the origin for a frame
        for style in ("gilt", "stone"):
            self.assertEqual(Banner(["Missing!"], style).objects(), [])


if __name__ == "__main__":
    unittest.main()
