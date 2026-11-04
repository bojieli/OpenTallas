#!/usr/bin/env python3
"""An empty black box with outputs must stop a vehicle build; vehicle_closure takes the behavioural sibling (SS25-TOK 11-03)."""
import importlib.util, pathlib, subprocess, sys
H = pathlib.Path(__file__).resolve().parent
CHECK = H.parent / 'check_vehicle_blackbox.py'
spec = importlib.util.spec_from_file_location('vehicle_closure', H / 'vehicle_closure.py')
VC = importlib.util.module_from_spec(spec); spec.loader.exec_module(VC)
BB = '(* blackbox *) module rom(input clk, output [7:0] q);\nendmodule\n'
REAL = 'module rom(input clk, output reg [7:0] q);\nalways @(posedge clk) q <= 8\'h5a;\nendmodule\n'
TOP = 'module top; wire [7:0] q; reg clk; rom u(.clk(clk), .q(q)); endmodule\n'


def run(tmp, rom, *extra):
    (tmp / 'top.sv').write_text(TOP); (tmp / 'rom.v').write_text(rom)
    (tmp / 'l.f').write_text('%s\n%s\n' % (tmp / 'top.sv', tmp / 'rom.v'))
    return subprocess.run([sys.executable, '-I', str(CHECK), str(tmp / 'l.f'), '--top', 'top', *extra], capture_output=True, text=True)


def test_reachable_empty_box_fails(tmp_path):
    r = run(tmp_path, BB)
    assert r.returncode == 2 and 'rom' in r.stdout + r.stderr


def test_one_line_empty_box_fails(tmp_path):
    r = run(tmp_path, 'module rom(input clk, output [7:0] q); endmodule\n')
    assert r.returncode == 2 and 'rom' in r.stdout + r.stderr


def test_real_model_passes(tmp_path):
    assert run(tmp_path, REAL).returncode == 0


def test_allow_regex_exempts(tmp_path):
    assert run(tmp_path, BB, '--allow', '^rom$').returncode == 0


def test_unreachable_box_passes(tmp_path):
    (tmp_path / 'x.v').write_text('(* blackbox *) module spare(output y);\nendmodule\n')
    (tmp_path / 'top.sv').write_text('module top; endmodule\n')
    (tmp_path / 'l.f').write_text('%s\n%s\n' % (tmp_path / 'top.sv', tmp_path / 'x.v'))
    assert subprocess.run([sys.executable, '-I', str(CHECK), str(tmp_path / 'l.f'), '--top', 'top'], capture_output=True).returncode == 0


def test_closure_takes_sibling_model(tmp_path):
    (tmp_path / 'r_bb.v').write_text(BB); (tmp_path / 'r.v').write_text(REAL); (tmp_path / 's_bb.v').write_text(BB)
    a, b, c = str(tmp_path / 'r_bb.v'), str(tmp_path / 's_bb.v'), str(tmp_path / 'o.sv')
    got, swapped = VC.sim_model_for_bb([a, b, c])
    assert got == [str(tmp_path / 'r.v'), b, c] and swapped == {a: str(tmp_path / 'r.v')}
