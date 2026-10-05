import copy
import unittest
from pathlib import Path
from dsrom_draft_placement_sweep import sweep, serialized, longest

class DraftPlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=sweep(Path(__file__).resolve().parents[1])
        cls.by={v['name']:v for v in cls.data['variants']}
    def test_published_ep5_recomposes(self):
        self.assertAlmostEqual(self.by['DP1-EP5']['draft_blocks_us'],83.992,places=3)
        self.assertAlmostEqual(self.by['DP1-EP5']['added_die_mm2'],43640.428,places=6)
    def test_replica_dies_and_ports(self):
        for e in [1,2,3,5]:
            v=self.by[f'DP1-EP{e}']
            self.assertEqual(v['added_dies'],12*e-8)
            self.assertEqual(v['replica_link_instances'],12*e)
            self.assertTrue(all(0<=i<e for a in v['row_to_replica'] for i in a))
    def test_conservative_time_is_monotone(self):
        times=[self.by[f'DP1-EP{e}']['draft_us'] for e in [1,2,3,5]]
        self.assertEqual(times,sorted(times,reverse=True))
    def test_no_physical_or_endpoint_credit(self):
        self.assertFalse(self.data['physical_admitted'])
        for v in self.data['variants']:
            self.assertIsNone(v['added_endpoint_area_mm2'])
    def test_frequency_and_ties(self):
        for entries in self.data['routing_frequency'].values():
            self.assertEqual(sum(x['count'] for x in entries),15)
            self.assertEqual(entries,sorted(entries,key=lambda x:(-x['count'],x['expert'])))
    def test_hot_no_invented_latency_or_packing(self):
        for k in [1,2,3]:
            v=self.by[f'EP5-hot-top{k}-per-stage']
            self.assertIsNone(v['draft_us']);self.assertIsNone(v['MTP_tok_s'])
            self.assertIsNone(v['packed_added_dies'])
            self.assertEqual(v['added_dies'],52)
    def test_replica_reuse_requires_real_return(self):
        g={f'ffn.{n}.r{r}':{'deps':[]} for r in range(5) for n in ['x_hop','ids_hop','w_hop','ret_hop']}
        s=serialized(g,(0,0,1,1,0))
        self.assertIn('ffn.ret_hop.r1',s['ffn.x_hop.r4']['deps'])
        self.assertIn('ffn.ret_hop.r2',s['ffn.w_hop.r3']['deps'])
        self.assertEqual(g['ffn.x_hop.r4']['deps'],[])
    def test_cycle_refuses(self):
        with self.assertRaisesRegex(ValueError,'cyclic'):
            longest({'a':{'deps':['b']},'b':{'deps':['a']}},{'a':1,'b':1})
    def test_same_historical_composition(self):
        m=self.data['composition_anchor']['MTP'];v=self.by['DP1-EP5']
        self.assertAlmostEqual(v['draft_us'],m['draft_us'],places=3)
        self.assertAlmostEqual(v['MTP_tok_s'],m['tau']*1e6/m['step_us'],places=2)
    def test_capacity_co_location(self):
        v=self.by['DP1-co-location-alone']
        self.assertLessEqual(v['max_rank_words'],v['rank_word_capacity'])
        self.assertEqual(v['added_dies'],0)

if __name__=='__main__': unittest.main()
