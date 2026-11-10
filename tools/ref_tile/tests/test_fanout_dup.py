"""tools/ref_tile/fanout_dup.py: drivers <= limit by construction, load model = native_census (S81-SVCRS-3 11-10)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
sys.path.insert(0, str(ROOT / 'tools'))
import fanout_dup as FD  # noqa: E402
import native_census as NC  # noqa: E402
import textbook_lint as TL  # noqa: E402

LIB = '''library (t) {
 cell (BUFx2_ASAP7_75t_R) { pin (A) { direction : input; } pin (Y) { direction : output; function : "A"; } }
 cell (INVx1_ASAP7_75t_R) { pin (A) { direction : input; } pin (Y) { direction : output; function : "!A"; } }
 cell (AND2x2_ASAP7_75t_R) { pin (A) { direction : input; } pin (B) { direction : input; }
   pin (Y) { direction : output; function : "(A * B)"; } }
 cell (DFFHQNx1_ASAP7_75t_R) { ff (IQN, IQNN) { clocked_on : "CLK"; next_state : "!D"; }
   pin (CLK) { direction : input; clock : true; } pin (D) { direction : input; }
   pin (QN) { direction : output; function : "IQN"; } }
}
'''


def netlist(body, ports, decls):
    return f"module top({', '.join(ports)});\n" + decls + body + "endmodule\n"


def sinks(src, n, start=0, prefix='s'):
    """n register loads (D pin = counted data load) on net src, each driving its own output port bit"""
    return ''.join(f'  DFFHQNx1_ASAP7_75t_R {prefix}{i} ( .CLK(clk), .D({src}), .QN(o[{i + start}]) );\n'
                   for i in range(n))


def run(tmp_path, text, limit=64):
    lib = tmp_path / 't.lib'
    lib.write_text(LIB)
    src = tmp_path / 'in.v'
    src.write_text(text)
    out, rep = tmp_path / 'out.v', tmp_path / 'rep.json'
    rc = FD.main(['--netlist', str(src), '--top', 'top', '--liberty', str(lib), '--out', str(out),
                  '--report', str(rep), '--limit', str(limit)])
    roles, _ = NC.liberty_roles([str(lib)])
    g, _ = TL.flatten({k: v for k, v in TL.parse_verilog(out.read_text()).items() if k not in roles}, 'top')
    return rc, json.loads(rep.read_text()), NC.census(g, roles), g


def test_ff_fanout_200(tmp_path):
    body = '  DFFHQNx1_ASAP7_75t_R r ( .CLK(clk), .D(d), .QN(q) );\n' + sinks('q', 200)
    rc, rep, after, g = run(tmp_path, netlist(body, ['clk', 'd', 'b', 'o'],
                                             '  input clk, d, b;\n  output [199:0] o;\n  wire q;\n'))
    assert rc == 0 and rep['before']['max_loads'] == 200 and after['max_dynamic_loads'] <= 64
    assert rep['splits'][0]['groups'] == 4 and rep['cells_added'] == 3
    ffs = [c for c in g.cells if c[1] == 'r' or c[1].startswith('r__fdup')]
    assert sorted(c[1] for c in ffs) == ['r', 'r__fdup1', 'r__fdup2', 'r__fdup3']
    clk, d = g.find(g.net_id['clk']), g.find(g.net_id['d'])
    assert all(c[2]['CLK'] == [clk] and c[2]['D'] == [d] for c in ffs)   # same clock + same D: register twins


def test_inv_tree_fanout(tmp_path):
    body = '  DFFHQNx1_ASAP7_75t_R r ( .CLK(clk), .D(d), .QN(q) );\n  INVx1_ASAP7_75t_R i0 ( .A(q), .Y(n0) );\n'
    for j in range(3):
        body += f'  BUFx2_ASAP7_75t_R bf{j} ( .A(n0), .Y(m{j}) );\n' + sinks(f'm{j}', 50, 50 * j, f's{j}_')
    rc, rep, after, g = run(tmp_path, netlist(body, ['clk', 'd', 'b', 'o'],
                                             '  input clk, d, b;\n  output [149:0] o;\n  wire q, n0, m0, m1, m2;\n'))
    assert rc == 0 and rep['before']['max_loads'] == 150 and after['max_dynamic_loads'] <= 64
    # every moved sink keeps the inversion: its A net is driven by a clone of i0 (directly or through a clone of bf*)
    assert any(c[1].startswith('i0__fdup') for c in g.cells)
    assert rep['after']['over_limit'] == 0


def test_comb_cascade_fixpoint(tmp_path):
    # AND 'a' drives 100 loads; its input q already has 64 other loads, so the AND clone pushes q to 65:
    # the second iteration clones the register too.
    body = ('  DFFHQNx1_ASAP7_75t_R r ( .CLK(clk), .D(d), .QN(q) );\n'
            '  AND2x2_ASAP7_75t_R a ( .A(q), .B(b), .Y(w) );\n' + sinks('w', 100) + sinks('q', 63, 100, 'q'))
    rc, rep, after, _ = run(tmp_path, netlist(body, ['clk', 'd', 'b', 'o'],
                                             '  input clk, d, b;\n  output [162:0] o;\n  wire q, w;\n'))
    assert rc == 0 and after['max_dynamic_loads'] <= 64 and rep['iterations'] >= 2
    assert {s['driver'].split('/')[0] for s in rep['splits']} == {'a', 'r'}


def test_input_port_driver_is_residual(tmp_path):
    rc, rep, after, _ = run(tmp_path, netlist(sinks('p', 100), ['clk', 'p', 'b', 'o'],
                                             '  input clk, p, b;\n  output [99:0] o;\n'))
    assert rc == 1 and rep['residual_after'] and rep['residual_after'][0]['driver'] == 'p'
    assert rep['residual'] and 'input port' in rep['residual'][0]['why']


def test_under_limit_unchanged(tmp_path):
    body = '  DFFHQNx1_ASAP7_75t_R r ( .CLK(clk), .D(d), .QN(q) );\n' + sinks('q', 40)
    rc, rep, after, _ = run(tmp_path, netlist(body, ['clk', 'd', 'b', 'o'],
                                             '  input clk, d, b;\n  output [39:0] o;\n  wire q;\n'))
    assert rc == 0 and rep['cells_added'] == 0 and rep['after']['band_33_limit'] == 1
    assert (tmp_path / 'out.v').read_bytes() == (tmp_path / 'in.v').read_bytes()   # pass-through, same sha
    assert rep['input']['sha256'] == rep['output']['sha256']
