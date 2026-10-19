"""Actual OpenSTA connectivity witness; generic Liberty is not physical signoff."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'ref_tile'))
import ck_insertion as C
from test_async_gray_fifo_constraints import YOSYS, STA, fixture_lib


@unittest.skipUnless(pathlib.Path(YOSYS).exists() and pathlib.Path(STA).exists(),
                     'Yosys/OpenSTA fixture tools required; run on fleet')
class ActualBoundary(unittest.TestCase):
    def test_false_paths_keep_data_boundary_but_not_reset_or_other_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'probe.sv').write_text('''
module boundary_probe(input ck, other_ck, din, rst_n, output dout);
  (* keep *) reg capture, launch, interior, arst, other;
  always @(posedge ck) begin capture <= din; launch <= capture; interior <= launch; end
  always @(posedge ck or negedge rst_n) if (!rst_n) arst <= 0; else arst <= interior;
  always @(posedge other_ck) other <= din;
  assign dout = launch;
endmodule
''')
            command = (f'read_verilog -sv {root}/probe.sv; synth -top boundary_probe -noabc; '
                       f'dffunmap; abc -g simple; clean; write_json {root}/probe.json; '
                       f'write_verilog -noattr -noexpr -norename {root}/mapped.v')
            p = subprocess.run([YOSYS, '-Q', '-T', '-p', command], text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            module = json.loads((root / 'probe.json').read_text())['modules']['boundary_probe']
            expected = {name.lstrip('\\') for name, cell in module['cells'].items()
                        if any(cell['connections'].get('Q') == module['netnames'][net]['bits']
                               for net in ('capture', 'launch'))}
            self.assertEqual(len(expected), 2)
            (root / 'probe.lib').write_text(fixture_lib(module))
            script = f'''read_liberty {{{root}/probe.lib}}
read_verilog {{{root}/mapped.v}}
link_design boundary_probe
create_clock -name ck -period 100 [get_ports ck]
create_clock -name other_ck -period 100 [get_ports other_ck]
set_input_delay 1 -clock ck [get_ports {{din rst_n}}]
set_output_delay 1 -clock ck [get_ports dout]
set_false_path -from [get_ports din]
set_false_path -to [get_ports dout]
set regs {{}}
foreach p [all_registers -clock_pins -clock [get_clocks ck]] {{
  set n [get_full_name $p]
  dict set regs [regsub {{/[^/]+$}} $n {{}}] $n
}}
set hidden [find_timing_paths -from [get_ports din] -to [all_registers -data_pins]]
if {{[llength $hidden]}} {{error "false-path witness unexpectedly timed"}}
{C.BOUNDARY_TCL}
dict for {{name present}} $bnd {{puts "BOUNDARY:$name"}}
puts ACTUAL_BOUNDARY_PASS
exit 0
'''
            (root / 'probe.tcl').write_text(script)
            p = subprocess.run([STA, '-exit', str(root / 'probe.tcl')], text=True, capture_output=True)
            log = p.stdout + p.stderr
            self.assertEqual(p.returncode, 0, log)
            self.assertIn('ACTUAL_BOUNDARY_PASS', log)
            actual = {line.removeprefix('BOUNDARY:') for line in log.splitlines()
                      if line.startswith('BOUNDARY:')}
            self.assertEqual(actual, expected, log)


if __name__ == '__main__':
    unittest.main()
