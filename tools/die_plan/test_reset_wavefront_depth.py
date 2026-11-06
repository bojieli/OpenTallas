"""Bounded checks for optional per-type reset padding."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_tree as RT


class WavefrontDepth(unittest.TestCase):
    def test_default_and_invalid(self):
        self.assertIsNone(RT.wavefront_min_depth({}))
        for bad in (-1, 1.2, True, '7'):
            with self.assertRaises(RT.ResetError):
                RT.wavefront_min_depth({'reset': {'wavefront_min_depth': bad}})

    def test_padding_is_real_and_cannot_shorten(self):
        topo = RT.topology([('tap0', 50, 50), ('tap1', 150, 50)], (10, 10), reach=405)
        original = RT.assign(topo)
        floor = original['depth'] + 2
        padded = RT.assign(topo, RT.wavefront_min_depth({'reset': {'wavefront_min_depth': floor}}))
        self.assertEqual(padded['depth'], floor)
        self.assertGreater(len(padded['relays']), len(original['relays']))
        self.assertEqual(RT.assign(topo, 0)['depth'], original['depth'])
        self.assertLessEqual(padded['max_hop_um'], 405)
        self.assertTrue(all(r['depth'] <= floor for r in padded['relays']))


if __name__ == '__main__':
    unittest.main()
