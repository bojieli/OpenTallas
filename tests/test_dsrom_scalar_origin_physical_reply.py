import importlib.util,json,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/dsrom_scalar_origin_physical_reply.py'
s=importlib.util.spec_from_file_location('scalar_reply',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ScalarReply(unittest.TestCase):
 def test_source_full_inventory_not_leaf(self):
  x=m.build();self.assertEqual(x['source_cells']['DFFASRHQNx1_ASAP7_75t_R'],112608)
  self.assertAlmostEqual(x['independent_gross50pct_mm2'],1.30217966172)
 def test_origins_inside_existing_cost(self):
  x=m.build()['named_origin_cost_already_inside_source'];self.assertEqual(x['FF_sinks'],144);self.assertFalse(x['separate_clock_or_area_addition'])
 def test_reset7_wire_budget_not_reset8(self):
  x=m.build()['clock'];self.assertAlmostEqual(x['reset7_FF_leaf_wire_cap_budget_fF'],.139637)
  self.assertAlmostEqual(x['six_FF_reset_leaf_wire_cap_budget_fF'],.942546)
  self.assertEqual(x['candidate_extra_BUF_count'],6641)
 def test_selected_wire_tree_not_qualified(self):
  x=m.build();self.assertFalse(x['admission']['scalar_RTL']);self.assertFalse(x['admission']['physical'])
  self.assertIsNone(x['one_home_request']['selected_global_xy'])
 def test_one_home_and_distinct_ports(self):
  x=m.build();self.assertEqual(x['interfaces']['distinct_source_signal_count'],384)
  self.assertEqual(x['one_home_request']['replicas_per_enrolled_core'],1)
  self.assertGreater(x['one_home_request']['local_rectangle_mm2'],1.313)
 def test_tie_allowance_not_silent_credit(self):
  x=m.build()['SETN_tie_allowance'];self.assertFalse(x['source_counted']);self.assertEqual(x['FF_SETN_sinks'],112608)
  self.assertAlmostEqual(x['gross50pct_mm2'],.00985094784)
 def test_pipeline_no_II1_or_VM_raw_transfer(self):
  x=m.build()['timing'];self.assertFalse(x['logical_tick_II1_admitted'])
  self.assertEqual(x['VM_raw_return_edges'],4);self.assertEqual(x['VM_protected_return_functional_candidate_edges'],8)
 def test_cold_model_exact(self):
  self.assertEqual(json.loads((m.BASE/'scalar_physical_reply.json').read_text()),m.build())
if __name__=='__main__':unittest.main()
