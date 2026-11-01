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
        for rank in range(4):
            word_moves=list(F.word_transfers(rank,spans=spans))
            self.assertEqual(len(word_moves),7*1280)
            for move in word_moves:
                n=move['global_element']
                self.assertEqual((move['sid'],move['leaf'],move['beat']),
                                 (n//320,(n//64)%5,n//64))
                self.assertEqual(4*(move['row']-F.ASSEMBLED-16*move['expert'])+move['word'],n%64)
        # Legacy80/slice map must not pass as the actual aligned source map.
        with self.assertRaisesRegex(ValueError,'row/owner/order'):
            F.verify_moves([m for rank in range(4) for m in F.transfers(rank)],spans=spans)

    def test_missing_or_shifted_source_ownership_rejected(self):
        deal = F.pair_aligned_deal(1280,16,T)
        for faulty in (deal[:-1], [r[:] for r in deal]):
            if len(faulty)==16:faulty[1][0]+=8
            with self.assertRaises(ValueError):F.source_spans(faulty)

    def test_actual_binding_rejects_legacy_source_identity(self):
        spans = F.source_spans(F.pair_aligned_deal(1280,16,T))
        # Global beat1 starts at64: its last rows cross the legacy80 boundary,
        # while the actual aligned first source slice ends at104.
        moves = [m for rank in range(4) for m in F.transfers(rank,spans=spans)
                 if m['sid']==0 and m['leaf']==1]
        arrivals = [dict(expert=m['expert'],row=m['row'],cycle=i,
                         source_rank=m['rank'],source_sid=m['source_sid'],
                         source_leaf=m['source_leaf'],source_row=m['source_row'])
                    for i,m in enumerate(moves)]
        binding = dict(rank=0,source_spans=spans,arrivals=arrivals,leases=[],
                       combine_issue=100,post_issue=203,post_end=300)
        self.assertEqual(F.local_program(0,1,binding)['latest_arrival'],55)
        arrivals[3]['source_sid']=1
        with self.assertRaisesRegex(ValueError,'actual source spans'):
            F.local_program(0,1,binding)

    def test_compiler_cannot_emit_old_fixture_map_as_actual_binding(self):
        from layer_prog import lower_vpx as L
        for op in ('ffn.combine_allreduce','ffn.hc_post'):
            for binding in ({},{'source_spans':None},{'source_spans':[]},
                            {'source_spans':'bad'},{'source_spans':[[0,80]]*16},
                            {'source_spans':[[0,10**12]]+[[i*80,80]for i in range(1,16)]}):
                result=L.lower(None,dict(op=op),dict(final_ffn=binding))
                self.assertEqual(result['status'],'PARTIAL')
                self.assertEqual(result['templates'],[])
                self.assertIn('107/53',result['gap']['missing'])

    def test_local_program_cannot_fall_back_on_explicit_json_null(self):
        binding=dict(rank=0,source_spans=None,arrivals=[],leases=[],combine_issue=0,post_issue=0,post_end=0)
        with self.assertRaisesRegex(ValueError,'actual final FFN source spans'):
            F.local_program(0,0,binding)


if __name__=='__main__':unittest.main()
