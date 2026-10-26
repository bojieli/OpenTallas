import copy
import unittest
from layer_programme import FIELDS,assemble_rows,compile_image,ScheduleError

class LayerRoots(unittest.TestCase):
 def setUp(self):
  self.rows=[dict(stage=s,roots=dict(zip(FIELDS,[3,4,5,6,10,8,7,14,20+s])))for s in range(1,37)]
 def test_all36_actual_boot_format(self):
  z=assemble_rows(self.rows,0x123456789abcdef0,3)
  self.assertEqual(len(z['words']),327);self.assertEqual(z['words'][-3:],[0x123456789abcdef0,3,0x514b564c59523336])
  self.assertEqual(z['token_core_cycles'],1386);self.assertEqual(len(z['events']),324)
  self.assertFalse(z['full_native_qualified'])
 def test_partial_image_refused(self):
  with self.assertRaisesRegex(ScheduleError,'all36'):assemble_rows(self.rows[:-1],0,0)
 def test_unpriced_root_refused(self):
  self.rows[7]['roots']['kgo']=None
  with self.assertRaisesRegex(ScheduleError,'explicit cycle32'):assemble_rows(self.rows,0,0)
 def test_guard_latency_refused(self):
  self.rows[0]['roots']['attention_run']=9
  with self.assertRaisesRegex(ScheduleError,'guard/load'):assemble_rows(self.rows,0,0)
 def test_quiet_cannot_precede_dispatch(self):
  self.rows[0]['roots']['expected_quiet']=9
  with self.assertRaisesRegex(ScheduleError,'precedes last'):assemble_rows(self.rows,0,0)
 def test_token_overflow_refused(self):
  for row in self.rows:row['roots']['stage_end']=0x80000000
  with self.assertRaisesRegex(ScheduleError,'overflows'):assemble_rows(self.rows,0,0)
 def test_missing_actual_clock_profile(self):
  with self.assertRaisesRegex(ScheduleError,'period/phase'):
   compile_image(b'',b'',{},dict(schema='opentallas.qwen_kv_static.layer_roots.v1',stages=self.rows),0,0)
 def test_measured_marker_alone_cannot_qualify_paths(self):
  import hashlib
  from pathlib import Path
  from unittest.mock import patch
  from layer_programme import ROOT,RTL
  for row in self.rows:
   row.update(period_fs=833334,phase_fs=0,physical_profile_status='MEASURED',
    source_sha256={RTL:hashlib.sha256((ROOT/RTL).read_bytes()).hexdigest(),
     'tools/qwen_static_kv/layer_programme.py':hashlib.sha256((ROOT/'tools/qwen_static_kv/layer_programme.py').read_bytes()).hexdigest()})
  with patch('layer_programme.source_contract'):
   with self.assertRaisesRegex(ScheduleError,'receipt missing'):
    compile_image(b'',b'',{},dict(schema='opentallas.qwen_kv_static.layer_roots.v1',stages=self.rows),0,0)
   component=compile_image(b'',b'',{},dict(schema='opentallas.qwen_kv_static.layer_roots.v1',stages=self.rows),0,0,component_test=True)
   self.assertFalse(component['installable']);self.assertFalse(component['full_native_qualified'])
 def test_unsupported_profile_schema(self):
  with self.assertRaisesRegex(ScheduleError,'unsupported'):compile_image(b'',b'',{},dict(schema='old',stages=self.rows),0,0)
if __name__=='__main__':unittest.main()
