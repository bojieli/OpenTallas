import json
from pathlib import Path
import unittest
from tools.gpu_sys.qwen_rf_ack_drain_continuation_model import model
from tools.gpu_sys.canonical_qwen_rf_ack_drain_r2 import port_bindings
ROOT=Path(__file__).resolve().parents[1]
R='rtl/model/qwen_rf_ack_drain_20261003/r2/ot_gpu_qwen_rf_ack_drain_r2.sv'

class Continuation(unittest.TestCase):
 def test_cold_model_exact(self):
  self.assertEqual(model(),json.loads((ROOT/'results/uarch/qwen_rf_ack_drain_continuation_20261003/model.json').read_text()))
 def test_paid_observed_old_SIMD_context(self):
  m=model();self.assertEqual(m['storage']['leaf_raw_bits'],624)
  self.assertEqual(m['storage']['leaf_protected_FF'],720)
  self.assertEqual(m['storage']['full64leaf_twojoin_protected_FF'],46512)
  self.assertGreater(m['area']['extra_cell_mm2_per_leaf_ASSUMED'],0)
 def test_no_old_context_from_continuation_claim(self):
  s=(ROOT/R).read_text();self.assertIn('if(simd_context_accept&&!simd_live)',s)
  self.assertIn('simd_live&&raw[621]&&!raw[622]',s)
  self.assertIn('rf_write_owner55==simd_owner',s)
  self.assertIn('wr_identity==simd_id&&wr_key==simd_saved_key',s)
 def test_existing_W6_one_write_not_a_bypass(self):
  s=(ROOT/R).read_text();self.assertIn('w6_live&&!raw[387]&&!raw[623]',s)
  self.assertIn('rf_write_owner55==raw[299:245]',s)
  self.assertIn('if(rf_write_accept&&write_W6_owner)n[623]=1;',s)
 def test_SIMD_receipt_stays_in_matching_drain(self):
  s=(ROOT/R).read_text();self.assertIn('w6_match||simd_match',s)
  self.assertIn('w6_live||simd_live||draining',s)
  self.assertIn('if(!simd_live||!raw[622]||simd_retire_owner55!=simd_owner',s)
 def test_exact_source_adapter_not_current_control(self):
  b=port_bindings()['continuation'];self.assertIn('retained accepted',b['simd_context_owner55'])
  self.assertIn('NOT rf_read_a/rf_read_b',b['rd_context_owner55'])
  self.assertIn('ACTUAL matching held RF ACK',b['simd_context_retire'])

if __name__=='__main__':unittest.main()
