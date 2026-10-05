#!/usr/bin/env python3
"""Small STA API test of the boundary contract; no parent closure evidence.

Uses real SS/FF libraries and four ROM abstracts, a handful of flops and one
ICG. It does not synthesize or route the element, or approximate its latency.
"""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class BoundaryContractTest(unittest.TestCase):
    def run_sta(self, corner, unclocked=False):
        with tempfile.TemporaryDirectory(prefix='v9-field-sdc-api-') as tmp:
            tmp = pathlib.Path(tmp)
            flops = [('sp', 'clk', 'i'), ('field', 'clk', 'i'), ('vm', 'clk', 'i'),
                     ('act', 'gclk' if not unclocked else "1'b0", 'sq'),
                     ('cfg', 'clk', 'sq'), ('go', 'clk', 'sq'),
                     ('ret', 'clk', 'aq'), ('vr', 'clk', 'sq'),
                     ('vw', 'clk', 'sq'), ('cap', 'gclk', 'romq[0]')]
            lines = ['module test_parent(input clk, input i, output o);',
                     'wire gclk, sq, aq, gq; wire [273:0] romq;',
                     "ICGx1_ASAP7_75t_R gate(.CLK(clk), .ENA(gq), .SE(1'b0), .GCLK(gclk));"]
            for name, clock, data in flops:
                q = 'sq' if name == 'sp' else 'aq' if name == 'act' else 'gq' if name == 'go' else 'o' if name == 'ret' else ''
                lines.append(f'DFFHQNx1_ASAP7_75t_R {name}(.CLK({clock}), .D({data}), .QN({q}));')
            for n in range(4):
                out = 'romq' if n == 0 else ''
                lines.append(f"ot_rom_4096x274_m8 rom{n}(.clk(gclk), .ce_in(1'b1), .addr_in(12'b0), .rd_out({out}));")
            lines.append('endmodule')
            netlist = tmp/'test.v'
            netlist.write_text('\n'.join(lines))
            script = tmp/'test.tcl'
            script.write_text(f'''
read_liberty {{{ROOT}/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib}}
read_liberty {{{ROOT}/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_{corner.lower()}.lib}}
read_verilog {{{netlist}}}
link_design test_parent
source {{{ROOT}/physical/dsrom_field_spine/field_boundary_clock.tcl}}
set b [dict create root_port clk root_clock actual_root gated_clock actual_gated \\
    gate_input gate/CLK gate_output gate/GCLK gate_enable gate/ENA gate_enable_launch go/QN source_commit API_TEST_ONLY \\
    macro_cells {{rom0 rom1 rom2 rom3}} \\
    clock_anchors [dict create spine sp/CLK field field/CLK vm vm/CLK] \\
    boundaries [dict create \\
      activation [dict create launch sp/QN capture act/D] \\
      configuration [dict create launch sp/QN capture cfg/D] \\
      go [dict create launch sp/QN capture go/D] \\
      result [dict create launch act/QN capture ret/D] \\
      vm_read [dict create launch sp/QN capture vr/D] \\
      vm_write [dict create launch sp/QN capture vw/D] \\
      macro_read [dict create launch {{rom0/rd_out[0]}} capture cap/D]]]
if {{![catch {{ot_v9_field::constrain [dict create] {corner}}} msg]}} {{error "accepted missing parent"}}
if {{![catch {{ot_v9_field::constrain $b TT}} msg]}} {{error "accepted TT signoff"}}
if {{[catch {{ot_v9_field::constrain $b {corner}; ot_v9_field::report $b {{{tmp}/paths}}}} msg]}} {{
  puts stderr $msg
  exit 1
}}
write_sdc {{{tmp}/result.sdc}}
puts API_CONTRACT_PASS_NOT_PARENT_CLOSURE
exit 0
''')
            result = subprocess.run(['sta', '-no_init', '-exit', str(script)],
                                    text=True, capture_output=True)
            return result, (tmp/'result.sdc').read_text() if (tmp/'result.sdc').exists() else ''

    def test_actual_library_root_and_icg_relation(self):
        for corner in ('SS', 'FF'):
            with self.subTest(corner=corner):
                result, sdc = self.run_sta(corner)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertIn('create_generated_clock', sdc)
                self.assertIn('-master_clock [get_clocks {actual_root}]', sdc)
                self.assertNotIn('set_false_path', sdc)

    def test_unclocked_activation_capture_rejected(self):
        result, _ = self.run_sta('SS', unclocked=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('capture lacks expected actual_gated', result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
