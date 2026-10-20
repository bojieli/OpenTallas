"""Exercise actual main/form/render pad migration, including its source master guard."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import kv_fwd_lanes as F

class PadMigration(unittest.TestCase):
    def run_case(self, declared):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); case=root/'case_kv'; case.mkdir()
            (case/'die.v').write_text("""module die;
  wire [35:0] x;
  wire [35:0] y;
  source u_source (.ck(n_clk_core_c), .rs(n_rst_c), .b(x[0]));
  qkd_rlys_36 rly_q_0__s0 (.ck(n_clk_core_c), .a({35'b0, x[0]}), .b(y[35:0]));
  sink u_sink (.ck(n_clk_core_ES), .rs(n_rst_ES), .a(y[0]));
endmodule
""")
            (case/'elements.lef').write_text('MACRO sink\n PIN a\n DIRECTION INPUT ;\n END a\nEND sink\nMACRO source\n PIN b\n DIRECTION OUTPUT ;\n END b\nEND source\n')
            (case/'die.v.pads.json').write_text(json.dumps({'instances':{'rly_q_0__s0':{'master':declared,'reason':'exact high pads','ports':{'a':[[1,35]],'b':[[1,35]]}}}}))
            with patch.object(F,'ROOT',root):
                rc=F.main(['--run',tmp,'--netlist-only'])
            self.assertEqual(rc,0)
            pad=json.loads((case/'die.v.pads.json').read_text())['instances']['rly_q_0__s0']
            self.assertEqual(pad['master'],'qkd_landsh0_36')
            self.assertEqual(pad['ports'],{'a':[[1,35]],'b':[[1,35]]})
            self.assertIn('qkd_landsh0_36 rly_q_0__s0', (case/'die.v').read_text())
            self.assertEqual(json.loads((root/'fwd_lanes.json').read_text())['totals']['lanes'],1)

    def test_main_migrates_exact_pads_after_render(self):
        self.run_case('qkd_rlys_36')

    def test_main_refuses_wrong_source_master(self):
        with self.assertRaisesRegex(ValueError,'pad declaration master'):
            self.run_case('qkd_rlys_296')
