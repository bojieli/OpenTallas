import importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h4_hbm_c0_pc40_exact_gate_r2 as G
class GateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m=G.compose()
 def test_actual_Ampere_packet(self):
  p=self.m['selected_source_packet'];self.assertEqual(p['source_PC'],40);self.assertEqual(p['RF_source_slot9'],38);self.assertEqual(p['RF_workspace'],[17,18,19])
 def test_actual_next_consumer(self):
  c=self.m['source_next_consumer'];self.assertEqual(c['opcode'],'FMIN');self.assertEqual(c['source_slot'],19);self.assertEqual(c['literal_bits'],0x42b00000)
 def test_missing_production_entering_snapshot_preserved(self):
  self.assertEqual(self.m['workspace']['production_entering_workspace'],'REFUSED_MISSING_ENTERING_LIVE_LEASES');self.assertFalse(self.m['production_entering_workspace_admitted'])
 def test_workspace_reverse_retained(self):self.assertEqual(self.m['workspace']['max_outstanding'],1);self.assertIn('held native retire',self.m['workspace']['release'])
 def test_real_provider_counts(self):
  p=self.m['ports'];self.assertEqual((p['RF_read_commands'],p['RF_write_commands'],p['HBM_commands']),(4,5,0));self.assertEqual(p['mirror_write_bytes'],5120)
 def test_finite_positive_bound_sensitivity(self):
  self.assertTrue(all(x>0 for x in self.m['cost_events'].values()));self.assertGreater(G.compose(16)['latency_ns_conditional'],G.compose(1)['latency_ns_conditional'])
 def test_literal_new_storage_priced(self):
  i=self.m['incremental'];self.assertEqual(i['protected_context_bits'],72);self.assertEqual(i['protected_FMIN_result_bits'],9216);self.assertEqual(i['codec_word_count'],129)
 def test_source_once_only_replacement(self):self.assertIn('replace paid r9',self.m['replaced_subtree']);self.assertEqual(self.m['W2']['HBM_candidate_II'],8)
 def test_scope_no_hardware_timing_promotion(self):self.assertFalse(self.m['physical_qualified']);self.assertFalse(self.m['protected_hardware_qualified']);self.assertIsNone(self.m['whole_token_ns'])
 def test_oracle_boundaries(self):
  r=G.oracle_vectors();self.assertEqual(len(r),128)
  self.assertEqual((r[0]['FMAX'],r[0]['FMIN']),(0xc2ae0000,0xc2ae0000))
  self.assertEqual((r[1]['FMAX'],r[1]['FMIN']),(0x42c80000,0x42b00000))
  self.assertEqual(r[2]['FMAX'],0);self.assertEqual(r[3]['FMAX'],0)
 def test_record_byteexact(self):self.assertEqual(json.loads((G.BASE/'model.json').read_text())['model'],self.m)
 def test_dynamic_source_packet_mutant_refusal(self):
  p=G.B.source_plan(17,31);p['native_command']['source_bittypes']=[64,32]
  with self.assertRaises(ValueError):G.B.emit_source(p,enabled=True)
if __name__=='__main__':unittest.main()
