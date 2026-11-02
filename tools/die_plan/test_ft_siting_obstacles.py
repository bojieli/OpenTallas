import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S
from ft_sites_unblock import placement_boxes


class SitingObstacles(unittest.TestCase):
    def test_reuse_leaf_without_lef_is_not_omitted(self):
        t = {'contents': [{'inst': 'restore', 'module': 'reuse_leaf',
                           'origin_um': [20, 30], 'outline_um': [10, 15]}]}
        self.assertEqual(S.placed_macro_boxes(t), {})
        self.assertEqual(placement_boxes(t)['restore'], (20, 30, 30, 45))

    def test_split_container_does_not_wall_off_its_routing_gap(self):
        t = {'contents': [{'inst': 'bank', 'origin_um': [0, 0],
                           'outline_um': [100, 100]}],
             'hard_cores': [{'inst': 'bank_left', 'origin_um': [0, 0],
                             'outline_um': [10, 100]},
                            {'inst': 'bank_right', 'origin_um': [90, 0],
                             'outline_um': [10, 100]}]}
        boxes = placement_boxes(t)
        self.assertEqual(set(boxes), {'bank_left', 'bank_right'})
        self.assertFalse(any(a < 50 < c and b < 50 < d
                             for a, b, c, d in boxes.values()))

    def test_track_offset_is_not_lost_or_applied_twice(self):
        t = {'hard_cores': [{'inst': 'core', 'origin_um': [1, 2],
                            'outline_um': [10, 20],
                            'track_offset_um': [.216, .108]}]}
        self.assertEqual(placement_boxes(t)['core'],
                         S.placed_macro_boxes(t)['core'])
        self.assertEqual(placement_boxes(t)['core'],
                         (1.216, 2.108, 11.216, 22.108))


if __name__ == '__main__':
    unittest.main()
