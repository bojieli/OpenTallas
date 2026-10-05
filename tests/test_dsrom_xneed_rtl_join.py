import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('prepare',R/'tools/prepare_dsrom_xneed_rtl_join.py');M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
class PreparedJoin(unittest.TestCase):
    def test_exact_generation(self):
        for p,s in M.generated().items():self.assertEqual((R/p).read_text(),s,p)
    def test_helper_state_matches_model(self):
        # At selected N8 SW3: two36-bit tables, five1-bit and two3-bit facts, one valid.
        self.assertEqual(3*(2*(8*(3+1)+3+1)+5+2*3+1),252)
    def test_local_successor_distribution(self):
        s=M.generated()['rtl/v41rom/xneed_lookahead/ot_v41_rom_elem_qp_xneed_w10.sv']
        self.assertIn('need_local[hc][UW-2:0]',s)
        self.assertIn('hit_k[1 % HC] && !need_local[1 % HC]',s)
        self.assertIn('.accept(hit_k[h])',s)
    def test_mandatory_live_and_delayed_decoder(self):
        s=M.generated()['rtl/v41rom/xneed_lookahead/ot_v41_rom_elem_qp_xneed_w10.sv']
        self.assertNotIn('NSEG + cfg_a_e[SW-1:0] - 1',s)
        self.assertNotIn('NSEG + qa_[SW-1:0] - 1',s)
        self.assertIn("32'(qa_) <= 3*NSEG",s)
    def test_default_off_q_only(self):
        d=M.generated();field=d['rtl/dsrom_sys/ot_v41_field_w17w10_xneed_sys.sv'];pair=d['rtl/v41die/ot_v41_pair_w17w10_xneed.sv']
        self.assertIn('QP_NEED_LOOKAHEAD = 0',field)
        self.assertIn('is_bf(g) ? 0 : QP_NEED_LOOKAHEAD',field)
        self.assertIn('QP_NEED_LOOKAHEAD != 0 && BF16 == 0',pair)
        self.assertIn('end else begin : g_retained',pair)
    def test_stalls_and_reset_isolation(self):
        s=(R/'rtl/v41rom/xneed_lookahead/ot_v41_need_lookahead.sv').read_text()
        self.assertIn('if(go || accept)',s);self.assertIn('if(!rst_n) valid<=0;',s)
        self.assertIn('if(valid) begin',s);self.assertIn('reference_walker',s);self.assertNotIn('function automatic [TB-1:0] priority(',s)
    def test_arithmetic_imports_exact(self):
        for e in json.loads((R/'results/rtl/dsrom_xneed_rtl_join_20261003/unchanged_arithmetic_imports.json').read_text()):
            self.assertEqual(hashlib.sha256((R/e['runtime_path']).read_bytes()).hexdigest(),e['sha256'])
    def test_source_list_usable(self):
        for p in (R/'results/rtl/dsrom_xneed_rtl_join_20261003/added_sources.f').read_text().splitlines():self.assertTrue((R/p).is_file())
    def test_pair_port_names(self):
        s=M.generated()['rtl/v41die/ot_v41_pair_w17w10_xneed.sv']
        for p in ('go','rst_n','xs_v','cfg_a','xs_pos'):self.assertIn('.'+p+'_pin(',s)
    def test_publication_unmodified(self):
        d=json.loads((R/'results/rtl/dsrom_xneed_rtl_join_20261003/parent_hook.json').read_text())
        self.assertTrue(d['no_new_parent_ports']);self.assertFalse(d['RTL_executed']);self.assertFalse(d['physical_admission'])
if __name__=='__main__':unittest.main()
