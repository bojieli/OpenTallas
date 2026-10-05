import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('shard_model',Path(__file__).resolve().parents[1]/'tools/dsrom_PAR2_shard_physical_binding.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ShardPhysicalBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model,cls.macros,cls.obs,cls.templates,cls.field,cls.escapes=m.build(0)
 def test_one_successor_no_serial_hops(self):
  self.assertEqual(self.model['candidate'],'DS4096-TP4-S58-PAR2-NP2048')
  self.assertEqual(self.model['serial_stage_owners'],58)
  self.assertEqual(self.model['added_serial_hops'],0)
  self.assertEqual(self.model['added_collective_tree_levels'],0)
 def test_exact_compiled_capacity_not_active_only(self):
  self.assertEqual(len(self.field),2048)
  self.assertEqual(sum(x['template']=='ROM' for x in self.macros),8192)
  self.assertEqual(sum(x['template']=='CFG' for x in self.macros),14336)
  self.assertEqual(sum(x['template']=='SRAM' for x in self.macros),36)
  self.assertEqual(self.model['ownership']['actual_census']['padding_q_pairs'],337)
  self.assertEqual({x['source_pair'] for x in self.field},set(range(2048)))
 def test_ordered_regions_not_split(self):
  for region in range(64):
   pairs=[x['source_pair'] for x in self.field if x['local_return_region']==region]
   self.assertEqual(pairs,list(range(region*32,(region+1)*32)))
 def test_second_shard_bijection_and_distinct_padding(self):
  model,macros,obs,templates,field,escapes=m.build(1)
  self.assertEqual({x['source_pair'] for x in field},set(range(2048,4096)))
  self.assertEqual(model['ownership']['actual_census']['padding_q_pairs'],384)
  self.assertEqual(model['ownership']['local_BF362'],self.model['ownership']['local_BF362'])
  self.assertEqual(model['area'],self.model['area'])
 def test_unique_macro_instances_and_exact_OBS(self):
  self.assertEqual(len({x['name'] for x in self.macros}),22564)
  self.assertTrue(all(x['bbox_DBU'][0]>=0 and x['bbox_DBU'][2]<=33000000 and x['bbox_DBU'][3]<=26000000 for x in self.macros))
  self.assertGreater(len(self.obs),80000)
  self.assertTrue(all(r['layer'] in {'M1','M2','M3','M4'} for r in self.obs))
 def test_clearance_cost_never_free(self):
  a=self.model['area']
  self.assertGreater(a['total_added_debit_mm2'],32)
  self.assertAlmostEqual(a['revised_conservative_screen_mm2']+a['remaining_for_positive_endpoints_exclusions_mm2'],858)
  self.assertLess(a['remaining_for_positive_endpoints_exclusions_mm2'],a['original_extra_budget_mm2'])
  self.assertTrue(a['inherited418_and_residual47_retained'])
 def test_local_pin_escape_only(self):
  r=self.model['collector_pin_escape_hypothesis']
  self.assertEqual(len(self.escapes),29556)
  for k in ['lost_pin_intersections','escaped_outside4320halo','collector_band_intersections','V4_axis_spacing34DBU_violating_pairs']:self.assertEqual(r[k],0)
  self.assertFalse(r['full_DRC_or_global_route'])
  self.assertFalse(r['PG_pin_access_and_CTS_coverage'])
 def test_no_free_PG_vias_clock_or_service_capacity(self):
  self.assertIsNone(self.model['collector']['admissible_capacity'])
  self.assertFalse(self.model['PG_via_clock']['actual_via_origins_bound'])
  self.assertFalse(self.model['PG_via_clock']['parent_SS_FF_qualified'])
  self.assertFalse(self.model['physical_GO'])
  self.assertEqual(self.model['macros']['memory_clk_pin_shapes'],22564)
 def test_SS_macro_cq_priced_before_routing(self):
  t=self.model['PG_via_clock']['source_macro_timing']['ROM']
  self.assertGreater(t['SS_clk_to_q_ps'],740)
  self.assertLess(t['one_stream_cycle_after60ps_uncertainty_minus_macro_cq_ps'],30)
 def test_boundary_width_not_perfect_service(self):
  r=self.model['remote_endpoint'];self.assertEqual(r['raw_root_boundary_bits_per_cycle'],4416)
  self.assertTrue(r['finite_credit_skid_visibility_lease_adapters_unpriced'])
  self.assertTrue(r['no_port_width_equals_service_guarantee'])
if __name__=='__main__':unittest.main()
