import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G


class StationEnvelope(unittest.TestCase):
    def setUp(self):
        self.old = G.STN70_SPLIT
        self.addCleanup(setattr, G, 'STN70_SPLIT', self.old)

    def model(self, lanes, horiz, old=False):
        G.STN70_SPLIT = not old
        w, h = G.stn_dims([70] * lanes, horiz)
        hv = 'h' if horiz else 'v'
        x, y = 103.68, 103.68
        tile = G.Inst('station', f'dsfd_stn{hv}_70x{lanes}', x, y, w, h, kind='stn')
        # Occupied neighboring street starts just beyond the RESERVED envelope.
        if horiz:
            guard = G.Inst('guard', 'hard', x-10, y+h+.864, w+20, 100, kind='hard')
        else:
            guard = G.Inst('guard', 'hard', x+w+.864, y-10, 100, h+20, kind='hard')
        buses = [(f'lane{k}', 'lane', 70, [('station', f'do{k}'), ('sink', f'i{k}')]) for k in range(lanes)]
        return dict(insts=[tile, guard], buses=buses), tile

    def test_exact_preplacement_envelopes_need_no_late_search(self):
        for lanes in (2, 3, 4):
            for horiz in (True, False):
                with self.subTest(lanes=lanes, horiz=horiz):
                    m, parent = self.model(lanes, horiz)
                    G.STN70_SPLIT = True
                    with patch.object(G.Placer, 'near', side_effect=AssertionError('late growth search')):
                        G._split_multi_lane_stations(m)
                    children = [i for i in m['insts'] if i.name.startswith('station_k')]
                    self.assertEqual(len(children), lanes)
                    for child in children:
                        self.assertGreaterEqual(child.x, parent.x)
                        self.assertGreaterEqual(child.y, parent.y)
                        self.assertLessEqual(child.x + child.w + G.SHAVE, parent.x + parent.w + 1e-9)
                        self.assertLessEqual(child.y + child.h + G.SHAVE, parent.y + parent.h + 1e-9)
                    self.assertEqual([b[3][0] for b in m['buses']], [(f'station_k{k}', 'do0') for k in range(lanes)])

    def test_original_compact_reservation_reproduces_late_growth(self):
        m, _ = self.model(4, True, old=True)
        G.STN70_SPLIT = True
        with patch.object(G.Placer, 'near', side_effect=AssertionError('late growth search')):
            with self.assertRaisesRegex(AssertionError, 'late growth search'):
                G._split_multi_lane_stations(m)

    def test_flag_off_and_single_root_unchanged(self):
        G.STN70_SPLIT = False
        old_single = G.stn_dims([70], True)
        old_group = G.stn_dims([70] * 4, True)
        G.STN70_SPLIT = True
        self.assertEqual(G.stn_dims([70], True), old_single)
        self.assertGreater(G.stn_dims([70] * 4, True)[1], old_group[1])


if __name__ == '__main__':
    unittest.main()
