"""The active exported view is distinct from immutable raw/provenance evidence."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as C


class ViewSelection(unittest.TestCase):
    def test_raw_first_cannot_select_or_rewrite_provenance(self):
        raw = '/run/record/views/tile/provenance/raw/tile.lef'
        final = '/run/record/views/tile/tile.lef'
        self.assertEqual(C.pick_view_lef([raw, final], 'tile'), final)
        self.assertIsNone(C.pick_view_lef([raw], 'tile'))

    def test_active_bundle_precedes_retained_attempt(self):
        final = '/run/record/views/tile/tile.lef'
        prior = '/run/record/views/tile.attempt1/tile.lef'
        self.assertEqual(C.pick_view_lef([prior, final], 'tile'), final)

    def test_child_and_bloat_are_not_parent_views(self):
        self.assertIsNone(C.pick_view_lef(['/run/record/macros/tile.lef',
                                         '/run/record/tile_bloat.lef'], 'tile'))


if __name__ == '__main__':
    unittest.main()
