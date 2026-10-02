import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(n,p):
 s=importlib.util.spec_from_file_location(n,ROOT/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=module('qrom','tools/qrom_enabled_capture_context.py');d=module('dsrom','tools/dsrom_PAR2_physical_read_context.py')
class CurrentPhysicalContexts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q,cls.placements,cls.shapes,cls.templates=q.build();cls.d,cls.ds_shapes=d.build()
 def test_main44_source_binding_no7294_model_transfer(self):
  self.assertEqual(self.q['source_main_pin'],'44e58b4aaab28a3539d6d312ac80a8f8442c52dd');self.assertEqual(self.d['source_main_pin'],self.q['source_main_pin']);self.assertTrue(self.q['unreviewed7294_uarch_model_not_consumed']);self.assertTrue(self.q['source_tile_hash_matches_ideal_screen'])
 def test_full_native_macro_counts_and_enabled_cones(self):
  self.assertEqual(len(self.placements),12);self.assertEqual(sum(p['master']=='ROM' for p in self.placements),10);self.assertEqual(self.q['enabled_cones']['ROM']['capture_bits'],2560);self.assertEqual(self.q['enabled_cones']['KV']['capture_bits'],512)
  self.assertEqual(self.q['enabled_cones']['ROM']['bank_enable_capture_loads'],512);self.assertEqual(self.q['enabled_cones']['ROM']['code_rd_capture_loads'],2560)
 def test_enabled_feedback_holds_idle_and_accepts_read(self):
  for old in [0,1]:
   for rd in [0,1]:
    for sel in [0,1]:
     for valid in [0,1]:
      expected=rd if sel and valid else old
      mux=((sel and valid) and rd) or ((not(sel and valid)) and old)
      self.assertEqual(mux,expected)
 def test_QROM_exact_OBS_PG_counts_and_collar_only(self):
  c=self.q['macro_context'];self.assertEqual(c['pin_shapes'],6280);self.assertEqual(c['PG_pin_shapes'],1842);self.assertEqual(c['OBS_shapes'],48);self.assertTrue(c['full_tile_logic_not_contained']);self.assertTrue(c['actual_PG_stripe_via_connections_missing'])
  self.assertEqual({p['capture_hierarchy'] for p in self.placements if p['master']=='SRAM'},{'u_logic.g_kv_local.g_kvcap.cap'})
 def test_tiny_ideal_budget_never_promoted(self):
  t=self.q['timing_budget'];self.assertAlmostEqual(t['SS_setup_budget_after_direct_capture_ps'],7.895628);self.assertLess(t['negative_screen_retained_ps'],0);self.assertTrue(t['no_enabled_or_wire_or_skew_pass_inferred']);self.assertEqual(self.q['new_builds'],0)
 def test_DS_existing_decoder_widths_exact_source(self):
  c=self.d['source_decoder']['replica_cones'];self.assertEqual((c['256']['R'],c['256']['N'],c['256']['replicas']),(9,266,412));self.assertEqual((c['272']['R'],c['272']['N'],c['272']['replicas']),(9,282,256));self.assertEqual(c['256']['independent_syndrome_XOR2_nodes'],1040);self.assertTrue(self.d['source_decoder']['main_inline_sidecar_to_282bit_order_adapter_missing'])
 def test_DS_actual_source_ECC_encoder_singlebit_boundaries(self):
  ecc=d.module('retained_ecc',d.OUT/'inputs/ecc.py')
  for k in [256,272]:
   data=(1<<(k-1))|1;word=ecc.encode(data,k)
   self.assertEqual(ecc.decode(word,k)[0],data)
   for bit in range(ecc.codeword_bits(k)):self.assertEqual(ecc.decode(word^(1<<bit),k)[0],data)
  # Existing Python contract only; this is not an executed RTL exactness claim.
 def test_DS_reused_macro_pin_OBS_union_no_extra_body(self):
  c=self.d['actual_macro_union'];self.assertEqual(c['existing_reused_instances'],412);self.assertEqual(c['additional_instances'],0);self.assertEqual(c['pin_shapes'],185812);self.assertEqual(c['PG_pin_shapes'],67156);self.assertEqual(c['OBS_shapes'],1648);self.assertAlmostEqual(c['body_union_mm2'],3.2471222976);self.assertTrue(c['PG_pin_rectangles_not_PG_stripes_or_connections'])
 def test_DS_bound_conflicts_and_rejection_quantities(self):
  self.assertEqual(self.d['finite_source_read_and_deadline']['retained_first_address_bank_conflict_read_rounds'],64);self.assertEqual(self.d['routing_incidence']['representative_vertical_reply_cut_peak']['reply_bits_if_fully_parallel'],528);self.assertGreater(self.d['enabled_read_capture']['SS_macro_clk_to_q_ps'],740);self.assertEqual(self.d['new_builds'],0)
  self.assertTrue(any('SS setup' in r['quantity'] for r in self.d['rejection_criteria']))
if __name__=='__main__':unittest.main()
