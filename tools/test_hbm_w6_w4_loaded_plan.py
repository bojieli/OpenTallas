import copy,unittest
from pathlib import Path
from unittest.mock import patch
import hbm_w6_w4_loaded_plan as M
class PlanTests(unittest.TestCase):
 def setUp(self):
  p=M.plan();self.e=dict(route=p['selected_route'],clock={k:p['clock'][k] for k in ['period_ns','SS_setup_uncertainty_ns','FF_hold_uncertainty_ns']},SM_ids=list(range(32)),RF_macros=4096,scratch_macros=64,slot_fit_mm2=1)
  for k in ['positive_composed_model','clean_exact_source','slot_and_macro_census','loaded_pin_bounds','positive_track_capacities','clock_reset_CDC_bound','SSFF_PDK_coherent','fresh_capacity_GO']:self.e[k]=True
 def test_fullsource_geometry(self):
  p=M.plan();self.assertEqual(p['geometry']['macros'][M.RF]['count'],4096);self.assertFalse(p['launch_admitted']);self.assertIsNone(p['geometry']['W4_W6_logic_slot_fit'])
 def test_nominal_enrollment_never_launches(self):self.assertFalse(M.check_admission(self.e)['launch_authorized'])
 def test_each_missing_positive_bound(self):
  for k in ['positive_composed_model','clean_exact_source','slot_and_macro_census','loaded_pin_bounds','positive_track_capacities','clock_reset_CDC_bound','SSFF_PDK_coherent','fresh_capacity_GO']:
   with self.subTest(k=k):
    e=copy.deepcopy(self.e);e[k]=False
    with self.assertRaises(ValueError):M.check_admission(e)
 def test_relaxed_uncertainty_refused(self):
  e=copy.deepcopy(self.e);e['clock']['SS_setup_uncertainty_ns']=.025
  with self.assertRaises(ValueError):M.check_admission(e)
 def test_TT_substitution_refused(self):
  e=copy.deepcopy(self.e);e['clock']['corner']='TT'
  with self.assertRaises(ValueError):M.check_admission(e)
 def test_reduced_geometry(self):
  for k,v in [('SM_ids',list(range(16))),('RF_macros',2048),('scratch_macros',32)]:
   e=copy.deepcopy(self.e);e[k]=v
   with self.assertRaises(ValueError):M.check_admission(e)
 def test_nonpositive_slot(self):
  for v in [None,0,-1,float('nan'),float('inf'),True]:
   e=copy.deepcopy(self.e);e['slot_fit_mm2']=v
   with self.assertRaises(ValueError):M.check_admission(e)
 def test_physical_source_drift(self):
  read=Path.read_bytes
  def changed(p):
   b=read(p);return b+b'\n' if p.name.endswith('.lef') else b
  with patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):M.plan()
 def test_actual_corner_macro_models_labeled(self):
  p=M.plan();r=p['geometry']['macros'][M.RF];self.assertAlmostEqual(r['source_model_SS_clktoq_ps'],455.3205489475797);self.assertFalse(r['loaded_or_extracted_measurement']);self.assertGreater(r['SS_intrinsic_read_budget_before_dest_setup_wire_skew_ps'],0)
 def test_direct_and_ready_path_both_covered(self):
  ids={x['id'] for x in M.plan()['critical_arcs']};self.assertIn('W4_HOST_ACK_TO_W6_STATE',ids);self.assertIn('W6_READY_TO_W4_ACK_CLEAR',ids)
 def test_no_physical_process(self):
  with patch('subprocess.Popen',side_effect=AssertionError('launch')),patch.object(Path,'write_bytes',side_effect=AssertionError('mutation')):M.plan()
if __name__=='__main__':unittest.main()
