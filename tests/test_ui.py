import unittest

from castlepanic.ui import _port


class Ports(unittest.TestCase):
    def test_port(self):
        self.assertEqual(_port(""), 5555)
        self.assertEqual(_port(" 6000 "), 6000)
        for bad in ("0", "70000", "-1", "abc"):
            with self.assertRaises(ValueError):
                _port(bad)


if __name__ == "__main__":
    unittest.main()
