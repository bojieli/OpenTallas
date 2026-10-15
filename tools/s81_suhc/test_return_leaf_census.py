#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from return_leaf_census import census


class DependencyCensusTest(unittest.TestCase):
    def mapped(self, output):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'fixture.sv').write_text('module fixture(input clk,a,b,c,output y); reg q; '
                                           'always @(posedge clk) q<=q|a; assign y=q&' + output + '; endmodule')
            subprocess.run(['yosys', '-Q', '-T', '-p', 'read_verilog fixture.sv; synth -noabc -top fixture; write_json fixture.json'],
                           cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            return json.loads((root / 'fixture.json').read_text())['modules']['fixture']

    def test_state_feedback_support_and_independent_clock_census(self):
        result = census(self.mapped('b'))
        self.assertEqual(result['dependencies_by_output']['y'], {'a': [0], 'b': [0]})
        self.assertEqual(result['structurally_unused_inputs']['c'], [0])
        self.assertEqual(result['sequential_bits'], 1)
        self.assertEqual(sum(result['clock_net_bits'].values()), 1)

    def test_real_output_rebinding_changes_detected_support(self):
        result = census(self.mapped('c'))
        self.assertEqual(result['dependencies_by_output']['y'], {'a': [0], 'c': [0]})
        self.assertEqual(result['structurally_unused_inputs']['b'], [0])

    def test_unmapped_hierarchy_is_refused(self):
        module = self.mapped('b')
        module['cells']['unsupported'] = dict(type='missing_child')
        with self.assertRaisesRegex(ValueError, 'fully generic mapped'):
            census(module)


if __name__ == '__main__':
    unittest.main()
