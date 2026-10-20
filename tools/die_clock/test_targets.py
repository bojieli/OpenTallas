import json
from pathlib import Path
import tempfile
import unittest
from build import load_targets
from qwen_compute_dieclk_prep import receiver_target


class Targets(unittest.TestCase):
    def test_supplied_targets_refuse_missing_or_invalid_native_r(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'kit.json'
            p.write_text(json.dumps({'masters': {'leaf': {'insertion_per_clock_pin_ps': {'ck': [140, 90, 120], 'zero': [0,0,0]}}}}))
            target = load_targets(p)
            self.assertEqual(target('leaf','ck'), [140,90,120])
            data = json.loads(p.read_text())
            data['masters']['leaf']['physical_insertion_per_clock_pin_ps'] = {'ck[0]': [130,95,122]}
            p.write_text(json.dumps(data))
            self.assertEqual(load_targets(p)('leaf','ck'), [130,95,122])
            self.assertEqual(load_targets(p)('leaf','ck[0]'), [130,95,122])
            self.assertEqual(target('leaf','zero'), [0,0,0])  # explicit R0 retained for labelled diagnostics
            for master, pin in [('leaf','ckvb'), ('absent','ck')]:
                with self.assertRaisesRegex(ValueError, 'missing native insertion R'):
                    target(master,pin)
            p.write_text(json.dumps({'masters': {'bad': {'insertion_in_arcs_ps': [1, None, 3]}}}))
            with self.assertRaisesRegex(ValueError, 'invalid insertion R'):
                load_targets(p)('bad','ck')

class ReceiverTargets(unittest.TestCase):
    def test_explicit_identity_and_missing_native(self):
        with tempfile.TemporaryDirectory() as td:
            rtl = Path(td) / 'glue.sv'
            rtl.write_text('module qfd_clkrx(input wire pll_fwd, output wire pll_r0, output wire pll_r1); assign pll_r0=pll_fwd; assign pll_r1=pll_fwd; endmodule')
            record = receiver_target(rtl)
            self.assertEqual(record['view'], 'MODEL_PASS_THROUGH_R0')
            target_file = Path(td) / 'targets.json'
            target_file.write_text(json.dumps({'masters': {'qfd_clkrx': record}}))
            target = load_targets(target_file)
            self.assertEqual(target('qfd_clkrx', 'pll_fwd[0]'), [0,0,0])
            for master, port in [('qfd_clkrx', 'other'), ('real_receiver', 'pll_fwd')]:
                with self.assertRaisesRegex(ValueError, 'missing native insertion R'):
                    target(master, port)
            for mutation in ['assign pll_r0=~pll_fwd;', 'always @(posedge pll_fwd) pll_r0<=1;', 'assign pll_r0=pll_r1;']:
                rtl.write_text('module qfd_clkrx(input wire pll_fwd, output wire pll_r0);' + mutation + 'endmodule')
                with self.assertRaisesRegex(ValueError, 'exact combinational identity'):
                    receiver_target(rtl)

if __name__ == '__main__':
    unittest.main()
