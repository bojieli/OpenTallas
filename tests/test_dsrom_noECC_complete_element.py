import importlib.util
import json
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_noECC_complete_element as t

class CompleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=t.build()

    def test_complete_macros_capture_and_regions_disjoint(self):
        for e in self.m['elements'].values():
            self.assertEqual(len(e['macro_instances']),4)
            box=e['outline_DBU']
            regions=[i['placement_halo_DBU'] for i in e['macro_instances']]+[i['bbox_DBU'] for i in e['capture_regions']]+[e['compute_control_clock_region_DBU']]
            for i,a in enumerate(regions):
                self.assertTrue(0<=a[0]<a[2]<=box[2] and 0<=a[1]<a[3]<=box[3])
                for b in regions[i+1:]:self.assertEqual(t.intersection(a,b),0)
            self.assertEqual(sum(r['register_bits'] for r in e['capture_regions']),1096)
            self.assertAlmostEqual(e['macro_body_union_um2'],31525.4592)

    def test_translated_macro_ports_and_OBS_not_reduced(self):
        for e in self.m['elements'].values():
            p=e['translated_macro_pin_OBS_PG']
            self.assertEqual(sum(r['kind']=='signal_pin' and r['pin'].startswith('rd_out[') for r in p),1096)
            self.assertEqual(sum(r['kind']=='OBS' for r in p),16)
            for i in e['macro_instances']:
                clk=next(r for r in p if r['instance']==i['instance'] and r.get('pin')=='clk')
                self.assertEqual(clk['bbox_DBU'][0],i['bbox_DBU'][0])

    def test_BF_growth_prices_real_reservation_not_new_counts(self):
        bf=self.m['elements']['BF16_column_pair'];q=self.m['elements']['q_pair']
        self.assertEqual(bf['outline_DBU'][3],157680)
        self.assertEqual(q['outline_DBU'][3],144720)
        self.assertAlmostEqual(bf['added_area_over_existing_PAR2_reservation_um2'],12997.4544)
        for e in (bf,q):self.assertGreaterEqual(e['area_reservation']['remaining_after_inherited_and_increment_um2'],0)
        old=json.loads((t.BASE/'initial_BF_reservation_negative.json').read_text())
        self.assertLess(old['elements']['BF16_column_pair']['area_reservation']['remaining_after_inherited_and_increment_um2'],0)

    def test_explicit_PG_shadow_no_percentage_capacity(self):
        for e in self.m['elements'].values():
            m2=next(c for c in e['crossing_capacity'] if c['layer']=='M2')
            self.assertGreater(m2['source_OBS_PG_template_blocked'],0)
            self.assertEqual(m2['remaining_before_vias_clock_spacing'],m2['grid_tracks']-m2['source_OBS_PG_template_blocked'])
            self.assertGreater(e['M2_M4_margin_before_actual_vias_clock_spacing'],0)
            self.assertEqual(e['local_ICG_groups'],8)
            self.assertTrue(e['complete_leaf_clock_load_not_only_capture'])

    def test_source_capture_and_policy_scope(self):
        c=self.m['capture_constraints']
        self.assertEqual((c['capture_postNBA_edge'],c['consume_preedge'],c['added_ECC_cycles']),(2,3,0))
        self.assertTrue(c['forbid_multicycle_to_arithmetic_or_valid_metadata'])
        self.assertFalse(self.m['actual_parent_parameter_join']['configuration_ROM_ECC_required'])
        self.assertTrue(self.m['actual_parent_parameter_join']['descriptor_validity_address_bounds_identity_and_mutable_control_protection_remain'])
        self.assertFalse(self.m['physical_G0']['admitted'])

    def test_literal_full_source_preparation(self):
        manifest=json.loads((t.BASE/'physical_source_manifest.json').read_text())
        self.assertEqual(len(manifest['files']),21)
        self.assertTrue(manifest['unchanged_literal_prefix_helpers'])
        self.assertTrue(manifest['test_runtime_memories_not_used'])
        src=(t.BASE/'inputs/physical_sources/ot_v41_rom_elem_w10.sv').read_text()
        self.assertIn('parameter integer GRADUAL_RNE = 0',src)
        self.assertIn('assign gclk = leaf_clk[0];',src)
        self.assertIn('.clk(leaf_clk[4 + 2*mb])',src)
        self.assertEqual(self.m['elements']['q_pair']['actual_WAKE1_clock_branch_topology']['ss']['distinct_capture_plus4ROM_load_groups_lowerbound'],15)
        self.assertEqual(json.dumps(self.m,indent=2,sort_keys=True)+'\n',(t.BASE/'model.json').read_text())

if __name__=='__main__':unittest.main()
