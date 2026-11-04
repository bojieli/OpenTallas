#!/usr/bin/env python3
"""DIE-HBM-61/CUTS 11-03: opt-in input relay stages (emit_shell in_stages={bus: k}) delay exactly that input bus by k
cycles after its face flop, leave every other bus at the plain shell latency, default (none / {}) emits the
byte-identical shell, and the bench mutant in_short (one bit skips its last stage) is caught."""
import importlib.util, subprocess, tempfile
from pathlib import Path
spec = importlib.util.spec_from_file_location('fs', Path(__file__).with_name('face_shell.py'))
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
widths = {'clk': 1, 'x': 8, 'w': 8, 'y': 8, 'z': 8}
dirs = {'clk': 'input', 'x': 'input', 'w': 'input', 'y': 'output', 'z': 'output'}
keep = dict(widths)
base = fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk')
assert fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk', in_stages=None) == base
assert fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk', in_stages={}) == base
assert 'u_bimid' not in base
CORE = ('module core(input clk, input [7:0] x, input [7:0] w, output [7:0] y, output [7:0] z);\n'
        ' assign y = x + 8\'d3; assign z = ~w;\nendmodule\n')
def run(sh, k, ostage=0):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / 'core.sv').write_text(CORE); (p / 'cell.sv').write_text(fs.CELL_SV); (p / 'shell.sv').write_text(sh)
        (p / 'tb.sv').write_text(f'''module tb;
 reg clk = 0; always #5 clk = ~clk;
 reg [7:0] x = 0, w = 0; wire [7:0] y, z; integer c, bad = 0;
 reg [7:0] hx [0:15]; reg [7:0] hw [0:15];
 shell dut(.clk(clk), .x(x), .w(w), .y(y), .z(z));
 initial begin
  for (c = 0; c < 60; c = c + 1) begin
   @(negedge clk);
   if (c >= 8 && y !== hx[(c - 2 - {k} - {ostage}) % 16] + 8'd3) bad = bad + 1;
   if (c >= 8 && z !== ~hw[(c - 2) % 16]) bad = bad + 1;
   x = c * 7 + 1; w = c * 13 + 5; hx[c % 16] = x; hw[c % 16] = w;
  end
  if (bad) $display("FAIL %0d", bad); else $display("PASS");
  $finish;
 end
endmodule
''')
        subprocess.run(['iverilog', '-g2012', '-o', str(p / 'a'), *(str(p / f) for f in ('tb.sv', 'shell.sv', 'cell.sv', 'core.sv'))], check=True)
        return subprocess.run(['vvp', str(p / 'a')], capture_output=True, text=True).stdout
for k in (1, 2):
    sh = fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk', in_stages={'x': k})
    assert sh.count('u_bimid') == k and 'u_bin_x' in sh and 'u_bin_w' in sh
    assert 'PASS' in run(sh, k), k
    # combined with the output read stage on y: +k in, +1 out
    sh2 = fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk', stages={'y': 1}, in_stages={'x': k})
    assert 'PASS' in run(sh2, k, 1), k
    mut = fs.emit_shell('shell', 'core', {}, widths, dirs, keep, {'clk'}, 'clk', in_stages={'x': k},
                        mutant={'kind': 'in_short', 'bus': 'x', 'bit': 3})
    assert 'FAIL' in run(mut, k), ('mutant in_short survived', k)
print('test_face_shell_in_stage PASS')
