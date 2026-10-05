import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).resolve().parents[1]/'tools/h4_hbm_w5_w10_composed_model.py'
s=importlib.util.spec_from_file_location('bridge_r4',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
ZERO=dict.fromkeys(('provider','assembler','RF_ACK','visible','consumer','child_reverse','parent_reverse','forward_CDC','reverse_CDC'),0)

class FullwidthCallerTests(unittest.TestCase):
 def caller(self,kind='KV_read',gen=0):
  a=m.NativeCaller(17);n=16 if kind=='KV_read' else 2;c=a.accept('Qwen',kind,33554432,list(range(n)),gen,12,dict(reference32=37,owner46=(5<<36 if kind=='KV_read' else 0)|(0x123<<4)|gen,native_owner64=2**40,native_generation64=gen,format='raw_U32_frame' if kind=='KV_read' else 'shared64_bytes',legacy=dict(die=1,producer=2**48,transport=0xabcdef01,caller=17,client=2 if kind=='KV_read' else 8,irs_slot=1,irs_serial=0)));return a,c
 def fill(self,a,c):
  for ch in reversed(c):a.returned(ch['index'],ch['owner46'],ch['index'],0,bytes([ch['index']])*32,ch['meta92'],ch['legacy_identity192'])
 def finish(self,a,c):
  for e in ('common_RF_ACK55','metadata_visible','actual_consumer','matched_reverse_CDC'):a.advance(e,a.capture_identity())
  a.retire(ZERO)
 def test_exact_fullwidth_layout_and_real_KV_client(self):
  a,c=self.caller(gen=15)
  for ch in c:
   own=ch['owner46'];self.assertEqual(own>>39,ch['physical_PC']);self.assertEqual(own>>36&7,5);self.assertEqual(own>>4&0xffffffff,ch['originaltag32']);self.assertEqual(own&15,15)
 def test_translation_source_prefix_mismatch_fixed_without_rewrite(self):
  self.assertEqual(m.physical(128)['physical_PC'],32)
  self.assertNotEqual(m.physical(128)['physical_PC'],128//32&127)
  self.assertEqual(m.physical(512)['local_sector'],4)
 def test_unordered_returns_assemble_in_original_byte_order(self):
  a,c=self.caller();self.fill(a,c);self.assertEqual(a.assembled(),b''.join(bytes([i])*32 for i in range(16)))
 def test_stale_generation_and_original_tag_refuse(self):
  a,c=self.caller();ch=c[0]
  with self.assertRaises(ValueError):a.returned(0,ch['owner46'],0,1,bytes(32),ch['meta92'],ch['legacy_identity192'])
  with self.assertRaises(ValueError):a.returned(0,ch['owner46']^(1<<4),0,0,bytes(32),ch['meta92'],ch['legacy_identity192'])
 def test_duplicate_return_and_physical_tag_alias_refuse(self):
  a,c=self.caller();a.returned(0,c[0]['owner46'],0,0,bytes(32),c[0]['meta92'],c[0]['legacy_identity192'])
  with self.assertRaises(ValueError):a.returned(0,c[0]['owner46'],0,0,bytes(32),c[0]['meta92'],c[0]['legacy_identity192'])
  # Children0 and1 are on the same stack; physical tag cannot be reused.
  with self.assertRaises(ValueError):a.returned(1,c[1]['owner46'],0,0,bytes(32),c[1]['meta92'],c[1]['legacy_identity192'])
 def test_unmatched_ACK_and_local_write_not_retirement(self):
  a,c=self.caller();self.fill(a,c)
  with self.assertRaises(ValueError):a.advance('common_RF_ACK55',a.capture_identity()^1)
  a.advance('common_RF_ACK55',a.capture_identity())
  with self.assertRaises(ValueError):a.retire(ZERO)
 def test_live_reverse_copy_blocks_generation_reuse(self):
  a,c=self.caller();self.fill(a,c)
  for e in ('common_RF_ACK55','metadata_visible','actual_consumer','matched_reverse_CDC'):a.advance(e,a.capture_identity())
  z=dict(ZERO,reverse_CDC=1)
  with self.assertRaises(ValueError):a.retire(z)
  with self.assertRaises(ValueError):a.accept('Qwen','KV_read',33554432,list(range(16)),1,12,{})
 def test_repeated_token_wrap_has_no_run_cap(self):
  a=m.NativeCaller(17)
  for token in range(129):
   c=a.accept('DeepSeek','KV_read',33554432,list(range(16)),token%16,12,dict(reference32=token,owner46=(5<<36)|(0x123<<4)|token%16,native_owner64=2**40,native_generation64=token,format='raw_U32_frame',legacy=dict(die=1,producer=2**48,transport=0xabcdef01,caller=17,client=2,irs_slot=1,irs_serial=token)));self.fill(a,c);self.finish(a,c)
  self.assertIsNone(a.live)
 def test_shared64_C0_uses_two_ack_banks(self):
  a,c=self.caller('C0');self.fill(a,c);self.assertEqual(len(a.assembled()),64)
  with self.assertRaises(ValueError):a.advance('common_RF_ACK55',a.capture_identity())
  a.advance('both_shared_bank_ACK',a.capture_identity())
 def test_explicit_actual_port_and_tag_bounds(self):
  with self.assertRaises(ValueError):m.NativeCaller(32)
  a=m.NativeCaller(0)
  with self.assertRaises(ValueError):a.accept('Qwen','KV_read',32,[0]*16,0,12,{})
 def test_model_preserves_unknown_hardware_and_nonzero_sensitivity(self):
  import json
  d=json.loads(m.outputs()['model.json']);self.assertFalse(d['engine_build_allowed']);self.assertFalse(d['hardware_admitted']);self.assertIsNone(d['whole_token_ns'])
  self.assertTrue(d['selected_path']['PC_service_W2_wrapper_on_critical_path']);self.assertTrue(d['selected_path']['current_installed_route_bypasses_W2'])
  self.assertEqual(d['selected_path']['NC'],6);self.assertFalse(d['selected_path']['directory_client_added'])
  for p in d['floorplan'].values():self.assertEqual(p['count'],32);self.assertFalse(p['obstacle_conflicts']);self.assertFalse(p['selected_context_conflicts']);self.assertTrue(p['selected_corridor_single_bus_screens_pass']);self.assertGreater(p['area_margin_mm2'],0)
  for e in d['sensitivity']:self.assertGreater(e['contended_tile_upper_ns_assumed'],0)
  self.assertGreater(d['sensitivity'][2]['contended_tile_upper_ns_assumed'],d['sensitivity'][1]['contended_tile_upper_ns_assumed'])
 def test_backend_zero_or_unbounded_wait_is_not_admitted(self):
  with self.assertRaises(ValueError):m.episode(16,57,0)
  with self.assertRaises(ValueError):m.episode(16,57,549.149,36,0)
 def test_bound_parent_is_not_first_or_last_child(self):
  a,c=self.caller();self.assertNotEqual(a.live['parent']['owner46'],c[0]['owner46']);self.fill(a,c)
  with self.assertRaises(ValueError):a.advance('common_RF_ACK55',c[-1]['owner46'])
  self.assertEqual(a.live['parent']['native_owner64'],2**40)
  a.advance('common_RF_ACK55',a.capture_identity())
 def test_backend_generation_is_independent_and_full_echo_required(self):
  a,c=self.caller(gen=15);ch=c[0]
  a.returned(0,ch['owner46'],(3<<12)|17,3,bytes(32),ch['meta92'],ch['legacy_identity192'])
  self.assertEqual(ch['owner46']&15,15)
  with self.assertRaises(ValueError):a.returned(1,c[1]['owner46'],18,3,bytes(32),c[1]['meta92'],c[1]['legacy_identity192'])
 def test_metadata_wrong_parent_or_SM_refuses(self):
  a,c=self.caller();ch=c[0]
  for flip in (1,1<<41):
   with self.assertRaises(ValueError):a.returned(0,ch['owner46'],0,0,bytes(32),ch['meta92']^flip,ch['legacy_identity192'])
 def test_partial_or_unconverted_frame_never_writes_RF(self):
  a,c=self.caller();a.returned(0,c[0]['owner46'],0,0,bytes(32),c[0]['meta92'],c[0]['legacy_identity192'])
  with self.assertRaises(ValueError):a.assembled()
  a=m.NativeCaller(0)
  with self.assertRaises(ValueError):a.accept('Qwen','KV_read',32,list(range(16)),0,0,dict(reference32=1,owner46=5<<36,native_owner64=2**40,native_generation64=0,format='FP8_raw'))
 def test_W2_sector_and_once_only_frozen_cost(self):
  import json
  a,c=self.caller()
  for ch in c:self.assertEqual(ch['R14_LEN6'],1);self.assertEqual(ch['R14_BEAT5'],0)
  d=json.loads(m.outputs()['model.json']);r=d['resource_ledger'];self.assertIsNone(r['W2_net_increment_mm2']);self.assertIsNone(r['W2_matched_old_debit_mm2'])
  self.assertAlmostEqual(r['W2_gross_bound_mm2_unreconciled'],6.62582757888);self.assertTrue(d['selected_path']['p_wr_done_ready_required_even_readonly_wrapper'])
 def test_exact_address_inverse_and_hash_mismatch_refusal(self):
  for byte in (0,32,128,511,512,33554432,80999999999):self.assertEqual(m.inverse_address(m.physical(byte)),byte)
  d=m.physical(512);d['physical_PC']^=1
  with self.assertRaises(ValueError):m.inverse_address(d)
 def test_RF_slot_is_in_held55_identity(self):
  a,c=self.caller();self.fill(a,c);self.assertEqual(a.capture_identity()&511,12)
  with self.assertRaises(ValueError):a.advance('common_RF_ACK55',a.capture_identity()^1)
 def test_legacy192_is_not_overwritten_or_provider_class_truncated(self):
  a,c=self.caller('C0');ch=c[0];self.assertEqual(ch['legacy_identity192']['client'],8);self.assertEqual(ch['client'],0)
  self.assertEqual(ch['legacy_identity192']['transport'],0xabcdef01)
  mutated=dict(ch['legacy_identity192'],die=0)
  with self.assertRaises(ValueError):a.returned(0,ch['owner46'],0,0,bytes(32),ch['meta92'],mutated)
 def test_CORE_preset_sensitivity_is_positive(self):
  import json
  d=json.loads(m.outputs()['model.json']);v=d['CORE_clock_sensitivity'];self.assertGreater(v[-1]['contended_tile_upper_ns_assumed'],v[0]['contended_tile_upper_ns_assumed'])
 def test_cold_archive_pins_and_canonical_source(self):
  import json
  d=m.inputs();self.assertEqual(len(d),25);self.assertEqual(json.loads(d['canonical.json'])['canonical_owner']['bits'],46)

if __name__=='__main__':unittest.main()
