import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
import hbm_w6_w4_context_bound as C
class ContextTests(unittest.TestCase):
 def test_complete_provider_source_census(self):
  r=C.bound();self.assertEqual(r['FF_ledger']['complete_provider_FFs'],8328);self.assertEqual(r['FF_ledger']['existing_provider_FFs'],8200);self.assertEqual(r['FF_ledger']['new_W4_provider_FFs'],128);self.assertEqual(r['FF_ledger']['provider_data_capture_FFs'],8192);self.assertEqual(r['FF_ledger']['provider_reset_FFs'],136)
 def test_no_SIMD_or_W6_duplicate(self):
  r=C.bound();self.assertEqual(r['FF_ledger']['fullSM_SIMD_shadow_FFs'],0);self.assertEqual(r['FF_ledger']['W6_existing_FFs'],144);self.assertEqual(r['FF_ledger']['controller_padding_newFF'],0)
 def test_source_provider_reduced_lanes_refused(self):
  raw=C.inputs();s=next(v.decode() for k,v in raw.items() if k.endswith('/inputs/ot_gpu_rf_service.sv'))
  with self.assertRaises(ValueError):C.census(s.replace('4095:0','2047:0'))
 def test_hidden_provider_state_refused(self):
  raw=C.inputs();s=next(v.decode() for k,v in raw.items() if k.endswith('/inputs/ot_gpu_rf_service.sv'))
  with self.assertRaises(ValueError):C.census(s.replace('reg read_pending, prefer_write;','reg read_pending, prefer_write;reg hidden;'))
 def test_macro_count_and_each_index(self):
  r=C.bound();p=r['candidate_home']['RF128_positions'];self.assertEqual(len(p),128);self.assertEqual(len({(x['bank'],x['copy'],x['page']) for x in p}),128);self.assertEqual(r['RF_macros_full32'],4096)
 def test_halos_nonoverlap(self):
  p=C.bound()['candidate_home']['RF128_positions']
  for i,a in enumerate(p):
   for b in p[i+1:]:
    a1,a2=a['halo_bbox_um'],b['halo_bbox_um'];self.assertTrue(a1[2]<=a2[0] or a2[2]<=a1[0] or a1[3]<=a2[1] or a2[3]<=a1[1])
 def test_response_mux_paid(self):
  r=C.bound();self.assertEqual(r['area']['baseline_RF_fourpage_mux2_cells'],24576);self.assertGreater(r['area']['baseline_provider_50pct_footprint_mm2_ASSUMED'],0)
 def test_cut_counts_all_payload_and_owner(self):
  r=C.bound();p=r['provider_ports'];self.assertEqual(sum(p[k]['bits'] for k in ['rsp_a','rsp_b','wr_data']),12288);self.assertEqual(sum(p[k]['bits'] for k in ['wr_owner','ack_owner','ack_slot','ack_identity_fault']),102);self.assertGreater(r['channel']['planning_margin_tracks'],0)
 def test_full_model_byte_replay(self):self.assertEqual(C.bound(),json.loads((C.BASE/'model.json').read_text()))
 def test_new_provider_state_not_doubled_globally(self):
  r=C.bound();self.assertEqual(r['area']['global_provider_baseline_debit_added_again'],0);self.assertEqual(r['area']['global_RF_macro_debit_added_again'],0);self.assertIsNone(r['area']['matched_global_logic_replacement_net_mm2'])
 def test_no_launch_or_installed_claim(self):
  with patch('subprocess.Popen',side_effect=AssertionError('launch')):r=C.bound()
  self.assertFalse(r['physical_admitted']);self.assertFalse(r['candidate_home']['installed_home_fit']);self.assertIsNone(r['channel']['actual_OBS_PG_neighbor_cut_capacity'])
 def test_input_drift_refused(self):
  read=Path.read_bytes
  def changed(p):
   b=read(p);return b+b'\n' if p.name=='make_tracks.tcl' else b
  with patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):C.bound()
if __name__=='__main__':unittest.main()
