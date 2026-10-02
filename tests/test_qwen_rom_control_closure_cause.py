import importlib.util,json,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('cause',P/'tools/qwen_rom_control_closure_cause.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ControlCause(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.a=m.build()
 def test_retained_failed_verdict(self):
  self.assertTrue(self.a['failure_unchanged']);self.assertLess(self.a['cause']['SS_full_slack_ps'],0);self.assertLess(self.a['cause']['FF_full_slack_ps'],0)
 def test_reset_not_data_hold(self):
  self.assertIn('removal',self.a['cause']['FF_worst']);self.assertAlmostEqual(self.a['cause']['reset_min_arrival_plus_distribution_minus_capture_skew_required_ps'],50.049297)
 def test_provider_not_arrival_waiver(self):
  self.assertIn('not a substitute',self.a['contextual_constraints']['actual_parent_provider']);self.assertTrue(self.a['contextual_constraints']['actual_reset_owner_and_release_phase_still_needed'])
 def test_counts_conservation(self):
  c=self.a['fixed_candidate'];self.assertEqual(c['total_metadata_FFs_after'],86+c['new_FFs']);self.assertEqual(c['total_added_buffers'],76);self.assertEqual(c['local_mask_FFs'],80);self.assertEqual(c['ROM_macros'],10)
 def test_positive_increment_no_borrow(self):
  c=self.a['cost'];self.assertAlmostEqual(c['new_control_cell_area_um2'],9.27288);self.assertAlmostEqual(c['incremental_die_slot_mm2'],.0356078592);self.assertTrue(c['prior645_control_wire_clock_buffer_allowance_not_subtracted'])
 def test_both_polarities_both_corners(self):
  self.assertEqual(len(self.a['analytical_loaded_arcs']),4)
  for c,a in self.a['analytical_loaded_arcs'].items():
   self.assertEqual(len(a['stages']),5);self.assertTrue(all(r['within_cap'] and r['within_slew'] for r in a['stages']));self.assertGreater(a['cell_path_ps'],0);self.assertFalse(a['characterization'])
 def test_interpolation_and_no_extrapolation(self):
  t='index_1 ("5, 10"); index_2 ("1, 2"); values ("1, 3", "5, 7");'
  self.assertEqual(m.lookup(t,7.5,1.5),4)
  with self.assertRaises(ValueError):m.lookup(t,4,1)
 def test_no_latency_or_qualification_transfer(self):
  self.assertEqual(self.a['fixed_candidate']['new_token_cycles'],0);self.assertTrue(self.a['fixed_candidate']['no_added_cycle_is_conditional_on_actual_SSFF_arrival_and_cause_closure'])
  for k in ('mapped_or_contextual_SSFF_closed','tile_PR','hardware_adoption','new_job'):self.assertFalse(self.a['admission'][k])
 def test_macro_separate_and_no_parameter_fix(self):
  self.assertTrue(self.a['retained_separate_paths']['macro_ideal_margin_is_not_wire_CTS_closure']);self.assertIn('IntegerMEM_EXTRA2 alone',self.a['retained_separate_paths']['if_macro_wire_skew_exceeds_margin'])
 def test_record_replay(self):
  self.assertEqual(self.a,json.loads((m.OUT/'model-r3.json').read_text()))
if __name__=='__main__':unittest.main()
