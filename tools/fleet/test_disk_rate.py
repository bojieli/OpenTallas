import unittest
import disk_rate as D


class Rate(unittest.TestCase):
    def test_projection(self):
        now = 10000.0
        pts = [(now - 3600, 400e9), (now, 350e9)]                       # 50 GB/h falling, 350 GB free -> (350-50)/50 = 6 h
        h, r = D.project(pts, now)
        self.assertAlmostEqual(h, 6.0, places=1); self.assertAlmostEqual(r, 50.0, places=1)

    def test_not_falling_or_too_little_data(self):
        now = 10000.0
        self.assertIsNone(D.project([(now - 3600, 300e9), (now, 400e9)], now))
        self.assertIsNone(D.project([(now - 100, 400e9), (now, 350e9)], now))
        self.assertIsNone(D.project([(now, 400e9)], now))
