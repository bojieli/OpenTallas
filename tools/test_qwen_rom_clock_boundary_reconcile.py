import copy
import unittest

import qwen_rom_fulldie_b3r2 as B
import qwen_rom_clock_boundary_reconcile as R


class Reconcile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v, cls.m = B.selected(True, True, True)
        cls.baseline = copy.deepcopy(cls.m['clock_regions'])
        cls.graph = R.digest(cls.m['buses'])
        cls.r = R.project(cls.v, cls.m, True)

    def test_default_off(self):
        with self.assertRaisesRegex(ValueError,'default off'):
            R.project(self.v,self.m)

    def test_only_actual_overlength_regions_split(self):
        names={c['original'] for c in self.r['changes']}
        expected={r['name'] for r in self.baseline if max(R.nm(r['rect'][2])-R.nm(r['rect'][0]),
                        R.nm(r['rect'][3])-R.nm(r['rect'][1])) > R.LIMIT_NM}
        self.assertEqual(names,expected)
        self.assertEqual(len(names),34)
        self.assertEqual(self.r['corrected_count'],154)
        self.assertEqual(self.r['cuts_um'],[9111.96,22125.96])
        self.assertEqual(self.r['max_extent_mm'],5.16672)

    def test_exact_union_no_trim_or_missing_tile(self):
        for orig in self.baseline:
            parts=sorted([r for r in self.r['regions'] if r['parent_region']==orig['name']],key=lambda r:r['rect'][1])
            self.assertEqual(parts[0]['rect'][:2],orig['rect'][:2])
            self.assertEqual(parts[-1]['rect'][2:],orig['rect'][2:])
            for lo,hi in zip(parts,parts[1:]):
                self.assertEqual(lo['rect'][3],hi['rect'][1])
        tiles=[n for n in self.r['source_ownership'] if n.startswith('t_')]
        self.assertEqual(len(tiles),1536)
        self.assertTrue(all(self.r['source_ownership'][n] for n in tiles))

    def test_original_source_graph_and_regions_preserved(self):
        self.assertEqual(self.m['clock_regions'],self.baseline)
        self.assertEqual(R.digest(self.m['buses']),self.graph)
        self.assertEqual(self.r['preserved_bus_graph_sha256'],self.graph)
        self.assertEqual(self.r['die']['mm2'],795.977)

    def test_missing_channel_mutant_rejected(self):
        with self.assertRaisesRegex(ValueError,'unique existing channel'):
            R.split_regions(self.baseline,[],True)

    def test_two_cut_mutant_rejected(self):
        bad=copy.deepcopy(self.baseline)
        r=next(r for r in bad if r['name']=='creg_t0_1')
        with self.assertRaisesRegex(ValueError,'unique existing channel'):
            R.split_regions([r],[6000,9000],True)

    def test_nanorounding_cannot_hide_overlength(self):
        r=dict(name='bad',kind='tile_block',rect=[0,0,100,5250.001])
        with self.assertRaisesRegex(ValueError,'unique existing channel'):
            R.split_regions([r],[],True)

    def test_crossings_priced_once_and_no_parallel_sum_latency(self):
        crosses=self.r['newly_separated_buses']
        self.assertEqual(len(crosses),len({e['bus'] for e in crosses}))
        self.assertEqual(self.r['new_crossing_capacity']['tree_block']['count'],144)
        self.assertEqual(self.r['new_crossing_capacity']['corridor']['count'],128)
        self.assertEqual(self.r['fifo_envelope']['total_state_bits'],sum(4*e['bits']+32 for e in crosses))
        self.assertEqual(self.r['latency']['tree_serial_new_crossings'],3)
        self.assertEqual(self.r['latency']['corridor_serial_new_crossings'],1)
        self.assertEqual(self.r['latency']['nominal_extra_cycles_per_ME_op'],8)

    def test_unknowns_and_physical_fail_closed(self):
        a=self.r['admission']
        self.assertFalse(a['physical_launch_allowed'])
        self.assertTrue(a['macros_spanning_new_cut'])
        self.assertTrue(a['unassigned_source_bus_count'])
        self.assertEqual({i['kind'] for i in a['macros_spanning_new_cut']},{'link_station'})

    def test_tree_cycle_mutant_rejected(self):
        m=dict(self.m,buses=list(self.m['buses']))
        bid,cl,w,eps=next(e for e in m['buses'] if e[1]=='tree_block')
        host=eps[1][0]
        idx=next(i for i,e in enumerate(m['buses']) if e[0]==bid)
        m['buses'][idx]=(bid,cl,w,[(host,'n_y'),eps[1]])
        with self.assertRaisesRegex(ValueError,'dependency cycle'):
            R.project(self.v,m,True)


if __name__=='__main__':
    unittest.main()
