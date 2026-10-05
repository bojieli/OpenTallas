import json
from pathlib import Path
import unittest
from tools.gpu_sys.canonical_qwen_native_consumer_drain import native_tuple,unpack_native_tuple,port_linkage
from tools.gpu_sys.qwen_native_consumer_drain_model import model,source_join
ROOT=Path(__file__).resolve().parents[1]

class SourceBinding(unittest.TestCase):
 def test_all144_actual_operators_roundtrip(self):
  for row in source_join()['operators']:
   fields=dict(native_tag=(1<<64)-1,native_generation=0xabcdef0123456789,
               source_PC=row['pc'],SM=31,rank=row['rank'],reader_lease=0x123456,
               key=(row['layer']<<14)|(row['rank']<<13)|8191,stage=row['stage'])
   self.assertEqual(unpack_native_tuple(native_tuple(fields)),fields)
 def test_partial_fragment_never_native_stage(self):
  for pc in (40,0,14,1737):
   with self.assertRaisesRegex(ValueError,'source SCORES/PV'):
    native_tuple(dict(native_tag=1,native_generation=2,source_PC=pc,SM=0,rank=0,reader_lease=3,key=0,stage=0))
 def test_rank_and_stage_mutants_refused(self):
  f=dict(native_tag=1,native_generation=2,source_PC=13,SM=0,rank=0,reader_lease=3,key=0,stage=0)
  for name,value in [('rank',1),('stage',1),('key',1<<13),('source_PC',15)]:
   with self.assertRaises(ValueError):native_tuple(dict(f,**{name:value}))
 def test_exact_private64_fields_not_truncated(self):
  f=dict(native_tag=(1<<63)+17,native_generation=(1<<63)+31,source_PC=15,SM=17,rank=0,reader_lease=(1<<63)+3,key=15,stage=1)
  self.assertEqual(unpack_native_tuple(native_tuple(f)),f)
  for name,width in [('native_tag',64),('native_generation',64),('reader_lease',64),('SM',5)]:
   with self.assertRaises(ValueError):native_tuple(dict(f,**{name:1<<width}))
 def test_prospective_costs_are_positive_and_once_only(self):
  m=model();self.assertEqual(m['protected_FF_bits'],432);self.assertEqual(m['raw_bits'],335)
  self.assertEqual(m['replicas_per_rank'],1);self.assertEqual(m['ranks'],2)
  self.assertGreater(m['cell_mm2_ASSUMED'],0);self.assertEqual(m['new_SRAM_macros'],0)
  self.assertFalse(m['clock']['SSFF']);self.assertIsNone(m['latency']['whole_token'])
 def test_cold_model_replay(self):
  recorded=json.loads((ROOT/'results/uarch/qwen_native_consumer_drain_20261003/model.json').read_text())
  self.assertEqual(recorded,model())
 def test_existing_controller_port_link_exact(self):
  source=(ROOT/'rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv').read_text()
  bridge=(ROOT/'rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv').read_text()
  for name in (*port_linkage()['KV_controller_inputs'],*port_linkage()['KV_controller_outputs']):
   self.assertIn(name,source);self.assertIn(name,bridge)
 def test_current_fault_not_masked_by_permit(self):
  source=(ROOT/'rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv').read_text()
  fault=source.split('wire current_bad=',1)[1].split(';',1)[0]
  for token in ('ready','live','permit'):self.assertNotIn(token,fault)
  self.assertIn('assign drain_done_allcopies=seen;',source)
  self.assertIn('assign cohort_quiesce={8{draining}};',source)
  self.assertNotIn('timer',source.split('module ',1)[1])
 def test_no_controller_or_source_modifications(self):
  self.assertTrue(port_linkage()['actual_enclosing_binding_required'])
  self.assertEqual(port_linkage()['result_bytes'],'none; exact arithmetic and payload remain in original native execution')

class LifecycleComposition(unittest.TestCase):
 def test_real_controller_and_bridge_are_instantiated(self):
  s=(ROOT/'rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_kv_native_lifecycle.sv').read_text()
  self.assertIn('ot_gpu_qwen_kv_lifecycle_controller #(.ENABLE(ENABLE)) lifecycle(',s)
  self.assertIn('ot_gpu_qwen_native_consumer_drain #(.ENABLE(ENABLE)) consumer_drain(',s)
  for p in (*port_linkage()['KV_controller_inputs'],*port_linkage()['KV_controller_outputs']):
   self.assertEqual(s.count('.'+p+'('+p+')'),2,p)
  self.assertIn('.run_enable(run_enable&&!bridge_fault)',s)
  self.assertIn('.endpoint_fault(endpoint_fault||controller_fault)',s)
 def test_permit_masked_drain_valid_not_in_current_fault_cone(self):
  s=(ROOT/'rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv').read_text()
  cone=s.split('wire current_bad=',1)[1].split(';',1)[0]
  self.assertNotIn('drain_valid',cone)
  self.assertIn('if(drain_key[19:14]>=36)next_raw[334]=1;',s)
  self.assertIn('if(drain_valid&&drain_ready)',s)

if __name__=='__main__':unittest.main()
