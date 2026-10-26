#!/usr/bin/env python3
"""tt_input_binding.connected_bands: a band whose tt is driven bit-completely (direct or through direct_up4 aliases)
is never also tied (r2h2/r2h4 GEN emitted .tt(actual) AND .tt(1538'h0) on sp_band_lanes_0)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_split.tt_input_binding import connected_bands  # noqa: E402

BAND = 'qfd_sp_band_lanes'
JOIN = {BAND: {'tt_uv': ('tt', [1536, 1537]),
               **{f'tt_l{l}': ('tt', [128 * l + j + 512 * k for k in range(3) for j in range(128)]) for l in range(4)}}}


def model(buses, ties=()):
    insts = [NS(name=f'sp_band_lanes_{k}', master=BAND) for k in range(3)] + [NS(name='up', master='leaf')]
    return dict(insts=insts, buses=buses, port_join=JOIN, ties=list(ties))


ALIAS = [(f'tt_ty_l{l}', 'd', 384, [('up', f'o{l}'), ('sp_band_lanes_0', f'tt_l{l}')]) for l in range(4)] + \
        [('tt_ty_uv', 'd', 2, [('up', 'ouv'), ('sp_band_lanes_0', 'tt_uv')])]
BANDS = [f'sp_band_lanes_{k}' for k in range(3)]


class T(unittest.TestCase):
    def test_aliases_complete(self):
        self.assertEqual(connected_bands(model(ALIAS), BANDS), {'sp_band_lanes_0'})

    def test_direct(self):
        b = [('tt0', 'd', 1538, [('up', 'o'), ('sp_band_lanes_0', 'tt')])]
        self.assertEqual(connected_bands(model(b), BANDS), {'sp_band_lanes_0'})

    def test_partial(self):
        with self.assertRaisesRegex(ValueError, 'partial'):
            connected_bands(model(ALIAS[:-1]), BANDS)

    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            connected_bands(model(ALIAS + ALIAS[:1]), BANDS)

    def test_missing_top(self):
        with self.assertRaisesRegex(ValueError, 'missing actual upper-tree producer'):
            connected_bands(model([]), BANDS)

    def test_tie_conflict(self):
        with self.assertRaisesRegex(ValueError, 'literal tie'):
            connected_bands(model(ALIAS, [('sp_band_lanes_0', 'tt', 1538, 0)]), BANDS)


if __name__ == '__main__':
    unittest.main()
