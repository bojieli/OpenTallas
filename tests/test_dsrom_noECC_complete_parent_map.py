import importlib.util,json,gzip,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('map',P/'tools/dsrom_noECC_complete_parent_map.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ParentMap(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r,cls.f,cls.mac,cls.cfg,cls.bands,cls.svc=m.build()
 def test_inventory(self):self.assertEqual(len(self.f),2048);self.assertEqual(len(self.mac),8192);self.assertEqual(len(self.cfg),14336);self.assertEqual(self.r['field']['BF_pairs'],362)
 def test_complete_BF_growth_once(self):self.assertAlmostEqual(self.r['area']['BF_complete_frame_growth_charged_once_mm2'],362*12997.4544/1e6)
 def test_q_frame(self):self.assertTrue(all(x['bbox_DBU'][3]-x['bbox_DBU'][1]==144720 for x in self.f if x['source_class']=='q_pair'))
 def test_BF_frame(self):self.assertTrue(all(x['bbox_DBU'][3]-x['bbox_DBU'][1]==157680 for x in self.f if x['source_class']=='BF16_column_pair'))
 def test_macros_inside_complete_frames(self):
  f={r['local_pair']:r['bbox_DBU'] for r in self.f}
  for a in self.mac:
   b=f[a['local_pair']];c=a['bbox_DBU'];self.assertTrue(b[0]<=c[0]<c[2]<=b[2] and b[1]<=c[1]<c[3]<=b[3])
 def test_row_and_cfg_translation(self):self.assertEqual(self.r['field']['cfg_return_band_y_translation_DBU'],492480);self.assertGreater(min(x['bbox_DBU'][1] for x in self.cfg),self.r['field']['field_end_DBU'])
 def test_new_selector_preserves_others(self):
  b=self.r['selector']['single_full_slot_bbox_DBU'];self.assertTrue(all(not m.overlap(b,x['bbox_DBU']) for x in self.svc if x['name']!='X_SEL_TOPK_STORE'));self.assertLess(b[3],26000000)
 def test_full_selector_cost_not_suffix(self):
  x=self.r['selector'];self.assertGreaterEqual(x['reserved_rectangle_mm2'],x['full_proxy_mm2']);self.assertAlmostEqual(x['only_additional_full_proxy_charge_mm2'],x['reserved_rectangle_mm2']-.3693656376);self.assertTrue(x['balanced_filter_full_G0_not_closed'])
 def test_clock_basis(self):self.assertEqual(self.r['clock'],{'ss':15,'ff':17})
 def test_directedbench_scope(self):
  x=self.r['trace_plan'];self.assertFalse(x['launch_admitted']);self.assertIn('NP4096',x['hierarchy']);self.assertTrue(any('root' in z for z in x['required_existing_bench_adaptation']));self.assertTrue(any('postNBA' in z for z in x['events']))
 def test_objective(self):
  x=self.r['single_user_objective'];self.assertAlmostEqual(x['assumed_iteration_budget_us'],x['assumed_tau']/3000*1e6);self.assertIn('sixposition',x['required_iteration']);self.assertTrue(x['phase_trace_not_MTP_rate'])
 def test_no_fit_or_jobs(self):self.assertFalse(self.r['physical_fit']);self.assertFalse(self.r['fulltoken_rate']);self.assertFalse(self.r['all_ROM_ECC_mandatory']);self.assertEqual(self.r['new_jobs'],0)
 def test_union_and_counterfactual(self):
  a=self.r['area'];self.assertAlmostEqual(a['combined_noncontainment_policy_screen_mm2'],a['prior_proposal_screen_mm2']+a['BF_complete_frame_growth_charged_once_mm2']+a['extra_row_whitespace_noncontainment_policy_mm2']+a['complete_selector_extra_charged_once_mm2']);self.assertTrue(a['new_row_void_may_already_be_contained_in_inherited418_no_credit_until_disjoint_union'])
 def test_replay(self):self.assertEqual(self.r,json.loads((m.BASE/'r2/model.json').read_text()))
if __name__=='__main__':unittest.main()
