#!/usr/bin/env python3
"""DIE-HBM-61/CLOCK: opt-in output lockup stage (emit_shell lockup={bus}) = negative-edge flop after the face flop.
(1) default (no lockup) emits the byte-identical shell; (2) cycle behaviour seen by a rising-edge receiver is unchanged
(same value just before every rising edge as the plain shell); (3) the port holds its value through the whole high
phase after a rising edge (the receiver hold window is T/2); (4) with yosys + ASAP7 liberty (ORFS image, OT_ASAP7_SEQ_LIB)
face_guard.py passes the lockup netlist and fails the 'out_latch' mutant (DLL latch drives the port) as unregistered."""
import importlib.util, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fs', HERE / 'face_shell.py')
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
widths = {'clk': 1, 'x': 8, 'y': 8, 'z': 8}
dirs = {'clk': 'input', 'x': 'input', 'y': 'output', 'z': 'output'}
keep = dict(widths)
CORE = ("module core(input clk, input [7:0] x, output [7:0] y, output [7:0] z);\n"
        " reg [7:0] r; always @(posedge clk) r <= x + 8'd3; assign y = r; assign z = ~x;\nendmodule\n")


def shell(name, **kw):
    return fs.emit_shell(name, 'core', {}, widths, dirs, keep, {'clk'}, 'clk', **kw)


def test_default_identical():
    base = shell('shell')
    assert shell('shell', lockup=set()) == base and shell('shell', lockup=None) == base
    assert 'u_bout_y__nl' not in base and fs.NCELL not in base
    lk = shell('shell', lockup={'y'})
    assert 'u_bout_y__nl' in lk and 'u_bout_z__nl' not in lk and lk.count(fs.NCELL) == 1


def test_mutant_guard():
    try:
        shell('shell', lockup={'y'}, mutant={'kind': 'out_bypass', 'bus': 'y', 'bit': 0})
    except ValueError:
        return
    raise AssertionError('out_bypass on a lockup bus must be refused')


def test_sim_cycle_and_hold():
    if not shutil.which('iverilog'):
        print('SKIP sim (no iverilog)'); return
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / 'core.sv').write_text(CORE)
        (p / 'cell.sv').write_text(fs.CELL_SV); (p / 'ncell.sv').write_text(fs.NCELL_SV)
        (p / 'a.sv').write_text(shell('sh_a')); (p / 'b.sv').write_text(shell('sh_b', lockup={'y', 'z'}))
        (p / 'tb.sv').write_text('''module tb;
 reg clk = 0; always #5 clk = ~clk;
 reg [7:0] x = 0; wire [7:0] ya, za, yb, zb; reg [7:0] yh, zh; integer c, bad = 0, holdbad = 0;
 sh_a a(.clk(clk), .x(x), .y(ya), .z(za));
 sh_b b(.clk(clk), .x(x), .y(yb), .z(zb));
 initial begin
  for (c = 0; c < 60; c = c + 1) begin
   @(negedge clk); x = c * 13 + 5; #4;            // 1 ps.. before the rising edge: what the receiver captures
   if (c >= 4 && (ya !== yb || za !== zb)) bad = bad + 1;
   yh = yb; zh = zb;
   @(posedge clk); #4;                             // inside the high phase: lockup output must not have moved
   if (c >= 4 && (yb !== yh || zb !== zh)) holdbad = holdbad + 1;
  end
  if (bad || holdbad) $display("FAIL %0d %0d", bad, holdbad); else $display("PASS");
  $finish;
 end
endmodule
''')
        subprocess.run(['iverilog', '-g2012', '-o', str(p / 'sim'), *(str(p / f) for f in
                        ('tb.sv', 'a.sv', 'b.sv', 'cell.sv', 'ncell.sv', 'core.sv'))], check=True)
        out = subprocess.run(['vvp', str(p / 'sim')], capture_output=True, text=True).stdout
        assert 'PASS' in out, out


def _synth_guard(p, sv, lib, yosys):
    (p / 'top.sv').write_text(sv)
    ys = (f"read_verilog -sv {p/'top.sv'} {p/'cell.sv'} {p/'ncell.sv'} {p/'core.sv'}\n"
          f"synth -top shell -flatten\n dfflibmap -liberty {lib}\n abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX\n opt_clean\n"
          f"write_verilog -noattr -noexpr {p/'net.v'}\n")
    (p / 's.ys').write_text(ys)
    subprocess.run([yosys, '-q', '-s', str(p / 's.ys')], check=True)
    r = subprocess.run([sys.executable, str(HERE.parents[2] / 'tools/die_plan/face_guard.py'), str(p / 'net.v'),
                        '--top', 'shell', '--out', str(p / 'fg.json')], capture_output=True, text=True)
    assert (p / 'fg.json').is_file(), (r.returncode, r.stdout[-800:], r.stderr[-1500:])
    return r.returncode, json.loads((p / 'fg.json').read_text()), (p / 'net.v').read_text()


def test_face_guard():
    lib, yosys = os.environ.get('OT_ASAP7_SEQ_LIB'), shutil.which('yosys')
    if not (lib and yosys and Path(lib).is_file()):
        print('SKIP face_guard (set OT_ASAP7_SEQ_LIB + yosys on PATH, e.g. in the ORFS image)'); return
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / 'core.sv').write_text(CORE); (p / 'cell.sv').write_text(fs.CELL_SV); (p / 'ncell.sv').write_text(fs.NCELL_SV)
        rc, fg, net = _synth_guard(p, shell('shell', lockup={'y', 'z'}), lib, yosys)
        assert 'DFFLQN' in net, 'negedge face stage must map to DFFLQN'
        assert rc == 0, fg
        rc, fg, net = _synth_guard(p, shell('shell', lockup={'y', 'z'}, mutant={'kind': 'out_latch', 'bus': 'y'}), lib, yosys)
        assert rc != 0 and 'unregistered' in json.dumps(fg), fg
    print('face_guard: lockup PASS, latch mutant FAIL unregistered')


if __name__ == '__main__':
    test_default_identical(); test_mutant_guard(); test_sim_cycle_and_hold(); test_face_guard()
    print('test_face_shell_lockup PASS')
