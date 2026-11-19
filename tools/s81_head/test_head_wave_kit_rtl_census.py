#!/usr/bin/env python3
"""census_path: a wave_prepare.json census recorded under another tree resolves to the same tree-relative file
(KIT_NOT_SELF_CONTAINED on hd_host_n / hd_host_w 11-18: the receipt named the deleted-on-host _nf15f_d2 tree)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_wave_kit_rtl as K  # noqa: E402

REL = Path('physical/die_plan/s81_head/prep/NF6/assets/sink_bins_4.json')
PREP = Path('physical/die_plan/s81_head/prep/NF15f/prep')


class CensusPath(unittest.TestCase):
    def test_existing_path_kept(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'a.json'; f.write_text('{}')
            self.assertEqual(K.census_path(str(f), Path(d)), f)

    def test_rerooted_into_prepared_tree(self):
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d) / 'snap_r5'
            (tree / REL).parent.mkdir(parents=True); (tree / REL).write_text('{}')
            (tree / PREP).mkdir(parents=True)
            gone = Path(d) / 'src_head_pin_x_nf15f_d2' / REL
            self.assertEqual(K.census_path(str(gone), tree / PREP), tree / REL)

    def test_missing_everywhere_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                K.census_path(str(Path(d) / 'gone' / REL), Path(d) / 'other' / PREP)


if __name__ == '__main__':
    unittest.main()
