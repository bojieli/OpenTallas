import importlib.util,json,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('join',P/'tools/dsrom_noECC_source_geometry_join.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Join(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r=m.build()
 def test_counts(self):self.assertEqual(self.r['paired_read_count'],33280);self.assertEqual(self.r['MB_read_count'],66560)
 def test_exact_phases(self):self.assertEqual([x['phase_identities'][0][3] for x in self.r['native_phases']],[10,11,12]);self.assertEqual([x['last_native_consumer'] for x in self.r['native_phases']],[199,199,129])
 def test_no_seats_or_ACK(self):self.assertTrue(self.r['source_capacity']['no_new_128_320_512_global_pool']);self.assertTrue(self.r['source_capacity']['no_new_local_ACK_wire']);self.assertEqual(self.r['source_capacity']['existing_perpair_capture_bits'],1096)
 def test_root_boundaries(self):self.assertEqual(m.root(1,0,0),64);self.assertEqual(m.root(1,31,1),64);self.assertEqual(m.root(1,32,0),65);self.assertEqual(m.root(1,2047,1),127)
 def test_invalid_root(self):
  for a in [(2,0,0),(0,2048,0),(0,0,2)]:
   with self.assertRaises(ValueError):m.root(*a)
 def test_translated_pins(self):
  for x in self.r['translated_macro_endpoints'].values():
   self.assertFalse(x['source_hierarchy_elaborated']);self.assertFalse(x['capture_D_endpoint_coordinates_available']);self.assertEqual(x['root_id'],m.root(x['shard'],x['local_pair'],x['MB']));self.assertIn('rd_out[273]',x['pins'])
 def test_nonzero_clock_load(self):
  c=self.r['physical']['capture_and_macro_clock_loads'];self.assertEqual(c['ff']['minimum_46p08fF_load_groups_before_wires_or_other_element_logic'],14);self.assertEqual(c['ss']['minimum_46p08fF_load_groups_before_wires_or_other_element_logic'],12)
 def test_source_done_not_ACK(self):
  x=self.r['cfg_and_completion'];self.assertTrue(x['source_rows_left_counts_r_v_not_external_ACK']);self.assertIn('final destination write',x['dependent_collective_PC_requires'])
 def test_no_missing_cost_zero(self):self.assertIsNone(self.r['root']['root_latency_cycles_unmeasured']);self.assertTrue(self.r['cfg_and_completion']['cfg_or_root_missing_cost_not_zero']);self.assertTrue(all(not x['absolute_origin_bound'] for x in self.r['native_phases']))
 def test_proposal_not_fit(self):
  a=self.r['area'];self.assertEqual(a['noECC_macro_instances_area_credit_mm2'],0);self.assertFalse(a['actual_geometry_fit_proven']);self.assertTrue(a['numeric_common_proxy_branch_not_auto_adopted']);self.assertAlmostEqual(a['source_native_no_extra_global_request_or_mux_reservation_branch_mm2'],727.0393290187258)
 def test_safety_scope(self):self.assertTrue(self.r['semantic_ROM_checks_retained']);self.assertTrue(self.r['SRAM_HBM_link_protection_retained']);self.assertFalse(self.r['build_admitted']);self.assertEqual(self.r['new_jobs'],0)
 def test_record(self):self.assertEqual(self.r,json.loads((m.BASE/'model-r1.json').read_text()))
if __name__=='__main__':unittest.main()
