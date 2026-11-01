#!/usr/bin/env python3
"""HBM-CORES-KITS-36/opstore: opt-in output read stages (emit_shell stages={bus: k}) delay exactly that bus by k cycles,
leave every other bus at the plain shell latency, and default (no stages) emits the byte-identical shell."""
import importlib.util, subprocess, tempfile
from pathlib import Path
spec = importlib.util.spec_from_file_location('fs', Path(__file__).with_name('face_shell.py'))
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
widths = {'clk': 1, 'x': 8, 'y': 8, 'z': 8}
dirs = {'clk': 'input', 'x': 'input', 'y': 'output', 'z': 'output'}
keep = dict(widths)
base = fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk')
assert fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk', stages={}) == base
assert 'u_bmid' not in base
for k in (1, 2):
    sh = fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk', stages={'y': k})
    assert sh.count('u_bmid') == k and 'u_bout_y' in sh and 'u_bout_z' in sh
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / 'core.sv').write_text('module core(input clk, input [7:0] x, output [7:0] y, output [7:0] z);\n'
                                   ' assign y = x + 8\'d3; assign z = ~x;\nendmodule\n')
        (p / 'cell.sv').write_text(fs.CELL_SV); (p / 'shell.sv').write_text(sh)
        (p / 'tb.sv').write_text(f'''module tb;
 reg clk = 0; always #5 clk = ~clk;
 reg [7:0] x = 0; wire [7:0] y, z; integer c, bad = 0;
 reg [7:0] h [0:15];
 shell dut(.clk(clk), .x(x), .y(y), .z(z));
 initial begin
  for (c = 0; c < 40; c = c + 1) begin
   @(negedge clk);
   if (c >= 6 && y !== h[(c - 2 - {k}) % 16] + 8'd3) bad = bad + 1;
   if (c >= 6 && z !== ~h[(c - 2) % 16]) bad = bad + 1;
   x = c * 7 + 1; h[c % 16] = x;
  end
  if (bad) $display("FAIL %0d", bad); else $display("PASS");
  $finish;
 end
endmodule
''')
        subprocess.run(['iverilog', '-g2012', '-o', str(p / 'a'), *(str(p / f) for f in ('tb.sv', 'shell.sv', 'cell.sv', 'core.sv'))], check=True)
        out = subprocess.run(['vvp', str(p / 'a')], capture_output=True, text=True).stdout
        assert 'PASS' in out, (k, out)
print('test_face_shell_stage PASS')
