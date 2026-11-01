"""Actual proportional ownership must fit native RD row-pair source boundaries."""
import unittest
from layer_prog import final_ffn as F, xs_topo as T


class SourceSpans(unittest.TestCase):
    def setUp(self):
        self.old = T.PROP, T.TOPO
        T.PROP = True
        T.TOPO = [6,6,3,3,6,6,3,3,3,3,6,6,3,3,6,6]

    def tearDown(self):
        T.PROP, T.TOPO = self.old

    def test_current_unaligned_deal_fails_closed(self):
        raw = T.slice_deal(1280,16)
        self.assertEqual(sorted(set(map(len,raw))),[53,107])
        with self.assertRaisesRegex(ValueError,'eight-word aligned'):
            F.source_spans(raw)

    def test_all_four_ranks_exact_capture_to_owner_map(self):
        deal = F.pair_aligned_deal(1280,16,T)
        self.assertEqual(sorted(set(map(len,deal))),[56,104])
        spans = F.source_spans(deal)
        moves = [m for rank in range(4) for m in F.transfers(rank,spans=spans)]
        self.assertEqual(len(moves),4480)
        F.verify_moves(moves,spans=spans)
        destinations = set()
        for m in moves:
            cfg = F.capture(m['rank'],m['source_sid'],m['expert'],spans=spans)
            source_word = 4*m['source_row'] - cfg['obase']
            for word in range(8):
                local = cfg['rbase'] + 64*m['source_leaf'] + source_word + word
                self.assertLess(local,cfg['rbase']+cfg['rcnt'])
                global_row = 1280*m['rank']+local
                owner = F.owner(global_row)
                self.assertEqual((m['sid'],m['leaf'],4*(m['row']-F.ASSEMBLED-16*m['expert'])+word),
                                 (owner['sid'],owner['leaf'],owner['word']))
                key = m['expert'],global_row
                self.assertNotIn(key,destinations)
                destinations.add(key)
        self.assertEqual(len(destinations),7*5120)
        # Legacy80/slice map must not pass as the actual aligned source map.
        with self.assertRaisesRegex(ValueError,'row/owner/order'):
            F.verify_moves([m for rank in range(4) for m in F.transfers(rank)],spans=spans)

    def test_missing_or_shifted_source_ownership_rejected(self):
        deal = F.pair_aligned_deal(1280,16,T)
        for faulty in (deal[:-1], [r[:] for r in deal]):
            if len(faulty)==16:faulty[1][0]+=8
            with self.assertRaises(ValueError):F.source_spans(faulty)


if __name__=='__main__':unittest.main()
