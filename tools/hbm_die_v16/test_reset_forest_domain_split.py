import unittest
from unittest.mock import patch

import reset_forest_layer as forest


class DomainSplitTest(unittest.TestCase):
    def test_existing_global_split_keeps_all_domains_identical(self):
        with patch.dict(forest.ZONE_SPLIT, {'NW': [7400, 12600]}, clear=True):
            for domain in ('hbm', 'serial', 'stream'):
                self.assertEqual([forest.split_zone('NW', x, domain) for x in (0, 7399, 7400, 12599, 12600)],
                                 ['NWa', 'NWa', 'NWb', 'NWb', 'NWc'])

    def test_serial_override_preserves_qualified_hbm_partition(self):
        splits = {'NW': [7400, 12600], 'serial/NW': [3700, 7400, 12600]}
        with patch.dict(forest.ZONE_SPLIT, splits, clear=True):
            self.assertEqual(forest.split_zone('NW', 5000, 'hbm'), 'NWa')
            self.assertEqual(forest.split_zone('NW', 5000, 'serial'), 'NWb')
            self.assertEqual(forest.split_zone('NW', 8000, 'hbm'), 'NWb')
            self.assertEqual(forest.split_zone('NW', 8000, 'serial'), 'NWc')
            self.assertEqual(forest.split_zone('NE', 5000, 'serial'), 'NE')


if __name__ == '__main__':
    unittest.main()
