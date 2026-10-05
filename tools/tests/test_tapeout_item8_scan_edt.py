"""Integration contracts only; Boole's component proof is consumed, not replayed."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tapeout_item8_scan_edt as edt
from dft import atpg_model, netlist as nl


class Integration(unittest.TestCase):
    def test_mapped_splice_keeps_macro_names_and_actual_internal_32(self):
        core = '''module ot_v41_rom_elem_q_qp_w10(clk,rst_n,scan_en,test_mode,edt_chain_in,edt_chain_out);
input clk; input rst_n; input scan_en; input test_mode;
input [31:0] edt_chain_in; wire [31:0] edt_chain_in;
output [31:0] edt_chain_out; wire [31:0] edt_chain_out;
ROM u_real_macro (.CLK(clk));
endmodule'''
        inputs = ['clk', 'rst_n', 'scan_en', 'pattern_reset']
        inputs += [f'edt_in[{i}]' for i in range(4)] + [f'chain_out[{i}]' for i in range(32)]
        outputs = [f'edt_out[{i}]' for i in range(4)] + [f'chain_in[{i}]' for i in range(32)]
        name = nl.verilog_name
        text = 'module codec(' + ','.join(name(n) for n in inputs + outputs) + ');\n'
        text += '\n'.join('input ' + name(n) + ';' for n in inputs)
        text += '\n' + '\n'.join('output ' + name(n) + ';' for n in outputs)
        text += '\nBUF body (.A(' + name('edt_in[0]') + '),.Y(' + name('chain_in[0]') + '));\nendmodule'
        codec = nl.parse_netlist(text)[0]
        result = nl.parse_netlist(edt.splice_codec(core, codec))[0]
        self.assertEqual(result.ranges['edt_chain_in'], (31, 0))
        self.assertNotIn('edt_chain_in', result.ports)
        self.assertEqual(result.ranges['scan_in'], (3, 0))
        self.assertIn('scan_pattern_reset', result.ports)
        self.assertEqual([i.name for i in result.instances], ['u_real_macro', 'edt_codec_body'])
        self.assertEqual(result.instances[1].pins, {'A': ['scan_in[0]'], 'Y': ['edt_chain_in[0]']})

    def test_legacy_independent_ppi_model_refused_before_netlist_read(self):
        with self.assertRaisesRegex(ValueError, 'independent-PPI'):
            atpg_model.build_models(Path('/missing'), {'edt': {'chains': 32}}, {}, Path('/missing'))

    def test_care_hook_requires_actual_chain_extent(self):
        with tempfile.TemporaryDirectory() as temp:
            scan, cube = Path(temp) / 'scan.json', Path(temp) / 'cube.json'
            scan.write_text(json.dumps(dict(chains=[{}]*32,
                edt=dict(channels=4, max_chain_length=2, response_window='reset then L-1'))))
            cube.write_text(json.dumps(dict(load=[[None]*32])))
            with self.assertRaisesRegex(ValueError, 'actual full L'):
                edt.encode_actual(scan, cube, Path(temp) / 'out.json')

    def test_care_hook_keeps_unsat_witness_and_never_credits_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            scan, cube, out = [Path(temp) / n for n in ('scan.json', 'cube.json', 'out.json')]
            scan.write_text(json.dumps(dict(chains=[{}]*32,
                edt=dict(channels=4, max_chain_length=1, response_window='reset then L-1'))))
            cube.write_text(json.dumps(dict(load=[[None]*32])))
            with patch.object(edt, 'encode', return_value=dict(encodable=False, unsat_chain=7)):
                self.assertEqual(edt.encode_actual(scan, cube, out), 1)
            record = json.loads(out.read_text())
            self.assertEqual(record['unsat_chain'], 7)
            self.assertEqual(record['coverage'], 'UNVALIDATED')


if __name__ == '__main__':
    unittest.main()
