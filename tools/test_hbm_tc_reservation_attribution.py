#!/usr/bin/env python3
import collections
import copy
import math
import unittest
import hbm_tc_reservation_attribution as A

class Attribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.record=A.build()
    def test_same_source_BD_recovery_matches_record(self):
        r=self.record['recovered_same_source_BD']
        self.assertEqual(r['outline_um'],[104,104])
        self.assertEqual(r['sha256'],'4b06d8be86d02dd447712f9a07dc8f8ab241c1e7ce09ffa9b7b1abe571b39f70')
        self.assertEqual(r['sha256'],r['record_LEF_sha256'])
        self.assertEqual(r['record_git'],A.SOURCE)
        self.assertFalse(r['qualified_timing_transfer'])
    def test_complete_inventory_halo_witness_inside_original_slots(self):
        for name,m in self.record['models'].items():
            rows=m['compact_unchanged_column_placement'];slot=m['existing_slot_um'];h=m['mandatory_halo_each_side_um']
            self.assertEqual(A.conflicts(rows,h),[])
            self.assertTrue(m['compact_fits_existing_slot'])
            names=[r['name'] for r in rows];self.assertEqual(len(names),len(set(names)))
            counts=collections.Counter(r['kind'] for r in rows)
            self.assertEqual(counts['failed_source_TC'],64 if name=='qwen' else 32)
            if name=='qwen':
                self.assertEqual(counts['SRAM_big'],20);self.assertEqual(counts['SRAM_scale'],1)
            else:
                self.assertEqual(counts['same_source_BD'],32);self.assertEqual(counts['SRAM_small'],99);self.assertEqual(counts['SRAM_big'],5)
            for r in rows:
                self.assertGreaterEqual(r['x']-h,-1e-8);self.assertGreaterEqual(r['y']-h,-1e-8)
                self.assertLessEqual(r['x']+r['w']+h,slot[0]+1e-8);self.assertLessEqual(r['y']+r['h']+h,slot[1]+1e-8)
                self.assertAlmostEqual(r['x']/A.SX,round(r['x']/A.SX),places=6)
                self.assertAlmostEqual(r['y']/A.SY,round(r['y']/A.SY),places=6)
    def test_wrong_BD_envelope_changes_necessary_area_bound(self):
        m=self.record['models']['deepseek_v41'];h=m['mandatory_halo_each_side_um']
        self.assertLess(m['contained_disjoint_halo_area_lower_bound_um2'],m['slot_area_um2'])
        # Actual164TC + legacy150BD, not predecessor's180TC, still fails
        # this explicitly contained/disjoint halo-area condition by20442um2.
        mixed=m['contained_disjoint_halo_area_lower_bound_um2']+32*((150+2*h)**2-(104+2*h)**2)
        self.assertAlmostEqual(mixed-m['slot_area_um2'],20442.01544,places=5)
        self.assertTrue(m['geometric_witness_is_not_global_minimum'])
    def test_prior_boxes_and_channel_demands_reproduced_exactly(self):
        for name,m in self.record['models'].items():
            q=name=='qwen'
            self.assertEqual(m['predecessor_upper_policy_reproduced']['box_um'],[5316.192,4769.28] if q else [3895.776,7292.16])
            ledger=m['prior_channel_demand_ledger']
            self.assertEqual(sum(ledger['vertical_spoke'].values()),7843 if q else 5299)
            self.assertEqual(sum(ledger['horizontal_row'].values()),5936 if q else 5456)
            self.assertEqual(sum(x['area_cap_um2'] for x in m['added_cell_cap_breakdown']),m['predecessor_upper_policy_reproduced']['added_cell_area_um2'])
    def test_policy_removal_deltas_telescope_but_are_not_additive_ablations(self):
        for m in self.record['models'].values():
            seq=m['ordered_policy_removal'];full=m['predecessor_upper_policy_reproduced']['box_um'];last=m['compact_box_um']
            for axis in [0,1]:self.assertAlmostEqual(sum(x['delta_from_previous_um'][axis] for x in seq),full[axis]-last[axis],places=5)
            self.assertTrue(m['ordered_deltas_are_path_dependent'])
            ab={x['term']:x for x in m['one_term_ablations']}
            self.assertGreater(ab['all_dedicated_signal_corridors']['delta_box_from_full_um'][1],2000)
            self.assertFalse(ab['all_added_cell_annex']['result']['fits_existing_slot'])
    def test_macro_whitespace_does_not_force_annex_or_admit_repair(self):
        for m in self.record['models'].values():
            a=m['failed_source_cell_area_accounting']
            self.assertLess(a['proposed_predecode_FF_stock_LEF_upper_area_um2'],a['unused_core_area_arithmetic_um2'])
            self.assertTrue(a['internal_spare_area_is_not_legal_placement_or_timing'])
            self.assertFalse(m['geometric_witness_admits_failed_hardware']);self.assertFalse(m['geometric_witness_admits_routing']);self.assertFalse(m['die_resize_adopted'])
        self.assertEqual(self.record['failed_unchanged']['engineering_verdict'],'FAIL')
        self.assertTrue(self.record['no_admission']);self.assertTrue(self.record['no_die_adoption'])
    def test_shelf_rejects_a_nonfitting_macro_instead_of_inventing_fit(self):
        with self.assertRaises(ValueError):A.shelf([('x','test',180,180)],164,4,4,8)
        rows=[dict(name='a',x=4,y=4,w=164,h=164),dict(name='b',x=171,y=4,w=164,h=164)]
        self.assertEqual(len(A.conflicts(rows,4)),1)

if __name__=='__main__':unittest.main()
