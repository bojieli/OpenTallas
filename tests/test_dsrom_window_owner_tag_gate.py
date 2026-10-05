import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/rtl/dsrom_window_owner_tag_gate_20261003'
class TagGateTests(unittest.TestCase):
    def test_actual_source_pins(self):
        for pin in json.loads((BASE/'input_pins.json').read_text()):
            with self.subTest(path=pin['path']):self.assertEqual(hashlib.sha256((BASE/pin['archive']).read_bytes()).hexdigest(),pin['sha256'])
    def test_source_owner_fields(self):
        pf=(BASE/'inputs/ot_chip_v41x_window_kv_prefetch.sv').read_text();outer=(BASE/'inputs/ot_chip_v41x_kv_rope_reqmux.sv').read_text();inner=(BASE/'inputs/ot_chip_v41x_kv_reqmux.sv').read_text()
        self.assertIn('TAGW-5',pf);self.assertIn('TAGW\'({refill_epoch, refill_next})',pf);self.assertIn('!(|wt[TAGW-1:TAGW-2])',outer)
        self.assertIn('.TAGW(TAGW-1)',outer);self.assertIn('s_tag[s*TAGW + TAGW-1]',inner)
        self.assertEqual(512<<5,0x4000);self.assertEqual((512<<5)>>14,1)
    def test_budget_wrap_for_full_modeled_context(self):
        for refill in range(1048576):self.assertEqual(((refill%512)<<5|16)>>14,0)
    def test_no_force_or_epoch_cap_in_bench(self):
        b=(BASE/'tb_window_owner_tag.sv').read_text()
        self.assertNotIn('force ',b);self.assertNotIn('dut.refill_epoch=',b)
        self.assertIn('.REFILL_CREDITS(8)',b);self.assertIn('.BANKED_STAGE(1)',b)
        self.assertIn('epoch<=(OWNER_SAFE ? 1536 : 512)',b)
        self.assertIn('wt[15:0]!=16\'h4000',b);self.assertIn('bank_rows[4223:0]!==expected_row(r)',b)
        self.assertIn('ot_chip_v41x_kv_rope_reqmux mux',b)
    def test_refill_drained_publication_fence(self):
        b=(BASE/'inputs/ot_chip_v41x_window_kv_prefetch.sv').read_text()
        self.assertIn("refill_received[15:0] == 16'hffff",b);self.assertIn('!refill_received[reply_sector]',b)
        self.assertIn('if (reply_sector == 16)',b);self.assertIn('state <= IDLE',b)
    def test_no_arbitrary_build_limits_and_no_auto_retry(self):
        r=(ROOT/'tools/run_dsrom_window_owner_tag_gate.py').read_text()
        self.assertNotIn('timeout=',r);self.assertNotIn('RLIMIT_AS',r)
        self.assertIn('resource.RLIM_INFINITY',r);self.assertIn('clean pinned source required',r)
        self.assertIn('fresh output directory required',r)
    def test_model_no_scope_or_price_credit(self):
        m=json.loads((BASE/'model.json').read_text());self.assertEqual(m['incremental']['repair_epoch_FF_delta_per_instance'],-2)
        self.assertEqual(m['geometry']['WINDOW_SLOTS'],128);self.assertEqual(m['successor']['default_off_parameter'],'REFILL_OWNER_SAFE=0')
        self.assertFalse(m['successor']['physical_admission']);self.assertIn('after complete old-row drain',m['lifetime']['full_lifetime'])
if __name__=='__main__':unittest.main(verbosity=2)
