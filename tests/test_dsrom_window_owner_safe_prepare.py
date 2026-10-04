import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/rtl/dsrom_window_owner_tag_gate_20261003'
s=importlib.util.spec_from_file_location('prep',ROOT/'tools/prepare_dsrom_window_owner_safe.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class OwnerSafePrepareTests(unittest.TestCase):
    def test_candidate_replay_byte_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'fresh';p.generate(out)
            self.assertEqual({x.name:x.read_bytes() for x in out.iterdir()},{x.name:x.read_bytes() for x in (BASE/'owner_safe').iterdir()})
    def test_defaultoff_full_chain(self):
        d=BASE/'owner_safe'
        pf=(d/'ot_chip_v41x_window_kv_prefetch_owner_safe.sv').read_text()
        self.assertIn('parameter bit REFILL_OWNER_SAFE = 0',pf)
        self.assertIn('(TAGW > 7 ? TAGW-7 : 1) : (TAGW > 5 ? TAGW-5 : 1)',pf)
        self.assertIn('REFILL_OWNER_SAFE && REFILL_CREDITS > 1 && TAGW < 8',pf)
        self.assertIn('.REFILL_OWNER_SAFE(REFILL_OWNER_SAFE)',(d/'ot_chip_v41x_window_attn_source_owner_safe.sv').read_text())
        self.assertIn('.REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE)',(d/'ot_chip_v41x_die_owner_safe.sv').read_text())
        wrap=(d/'ot_v41_rt_die_l20_owner_safe.sv').read_text();self.assertIn('WINDOW_REFILL_OWNER_SAFE = 0',wrap);self.assertIn('.WINDOW_REFILL_CREDITS(WINDOW_REFILL_CREDITS)',wrap)
    def test_no_row_order_publication_changes(self):
        d=(BASE/'owner_safe/ot_chip_v41x_window_kv_prefetch_owner_safe.sv').read_text();old=(BASE/'inputs/ot_chip_v41x_window_kv_prefetch.sv').read_text()
        self.assertEqual(d[d.index('    reg [EPOCH_W-1:0]'):d.index('`ifndef SYNTHESIS')],old[old.index('    reg [EPOCH_W-1:0]'):old.index('`ifndef SYNTHESIS')])
        self.assertEqual(d[d.index('    always @(*) begin\n        m_v'):],old[old.index('    always @(*) begin\n        m_v'):])
    def test_original_actual_failure_pins(self):
        r=json.loads((BASE/'original_r1_evidence/record.json').read_text())
        self.assertEqual(r['status'],'CONFIRMED_ORIGINAL_DUT_OWNER_REJECTION')
        for name,h in r['artifact_sha256'].items():self.assertEqual(hashlib.sha256((BASE/'original_r1_evidence'/name).read_bytes()).hexdigest(),h)
    def test_fullcredit_stress_and_exact_counts(self):
        b=(BASE/'tb_window_owner_tag_r2.sv').read_text();self.assertIn('cycle+9+',b);self.assertIn('reads!=17*epoch',b);self.assertIn('peak!=8',b)
        self.assertNotIn('force ',b);self.assertIn('1536',b)
if __name__=='__main__':unittest.main(verbosity=2)
