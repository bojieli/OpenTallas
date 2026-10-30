"""Internal95ps/leaf48ps must hold; corrected52ps full coverage may proceed."""
from pathlib import Path
import importlib.util,sys,unittest
from types import SimpleNamespace
from unittest.mock import patch
P=Path(__file__).resolve().parents[1]/'results/core_lat_r8_1026/l0r_r8_uf3.py'
s=importlib.util.spec_from_file_location('all_buffer_adapter',P);A=importlib.util.module_from_spec(s);s.loader.exec_module(A)
PLAN=SimpleNamespace(nodes=dict(root={},internal={},leaf={}))

def kernel(internal=95.5255173102168,leaf_output=47.65460975816248,bad=None):
 def predict(plan,libs,corner,edge,detail,**params):
  detail['leaf']=dict(sinks=[100.,101.],slew_in=28.44,slew_out=leaf_output)
  arrivals=dict(root=(0.,0.),internal=(10.,internal),leaf=(20.,28.44))
  if bad=='missing':del arrivals['internal']
  if bad=='nan':arrivals['internal']=(10.,float('nan'))
  return {'leaf':100.5},arrivals
 return predict

class AllBufferSlew(unittest.TestCase):
 def summary(self,**kwargs):
  with patch.object(A.V3,'predict3',side_effect=kernel(**kwargs)) as calls:
   q=A.calibrated_summary(PLAN,{}, {}, {})
  self.assertEqual(calls.call_count,3)
  return q
 def test_actual_internal_negative_control_leaf_metrics_unchanged(self):
  q=self.summary()
  self.assertEqual(q['TT']['leaf_slew_in_max'],28.44)
  self.assertEqual(q['TT']['leaf_out_slew_max'],47.65)
  self.assertGreater(A.all_buffer_slew_max(q),80)
  self.assertEqual(q['TT']['all_buffer_input_coverage'],3)
 def test_repaired_positive_control(self):
  q=self.summary(internal=52.581153028785806)
  self.assertLessEqual(A.all_buffer_slew_max(q),80)
 def test_terminal_output_uses_unrounded_boundary(self):
  q=self.summary(internal=52.,leaf_output=80.004)
  self.assertEqual(q['TT']['leaf_out_slew_max'],80.)
  self.assertGreater(A.all_buffer_slew_max(q),80.)
 def test_missing_or_nonfinite_arrivals_fail_closed(self):
  for bad in ('missing','nan'):
   with self.subTest(bad=bad),patch.object(A.V3,'predict3',side_effect=kernel(bad=bad)),self.assertRaises(ValueError):
    A.calibrated_summary(PLAN,{}, {}, {})
  with self.assertRaises(ValueError):A.all_buffer_slew_max({'TT':{},'FF':{}})
 def test_limit_cannot_expand_calibration(self):
  self.assertEqual(A.calibration_slew_limit(100),80)
  for value in (float('nan'),float('inf'),0,-1):
   with self.subTest(value=value),self.assertRaises(ValueError):A.calibration_slew_limit(value)
if __name__=='__main__':unittest.main()
