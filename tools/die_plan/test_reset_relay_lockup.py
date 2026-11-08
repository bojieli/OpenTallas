"""CLK FORM #7 (DIE-S81-51/PLAN 11-03): opt-in negative-edge lockup relay ot_dp_rrelay_nl on internal reset hops.

Invariants: default off = byte-identical cells/trees; only internal relays (q = rst_rl_*) change; leaf taps, out
relays and the entry pin register stay ot_dp_rrelay; one relay is still exactly one clock cycle (simulated)."""
import re
import shutil
import subprocess
import types

import pytest

import bind
import gen_rtl
import kit_rsync as K
import reset_tree as R


def tree(lockup):
    t = R.build([('a', 100, 0), ('b', 200, 0), ('out', 300, 0)], (0, 0), depth=4)
    t.update(taps=['a', 'b', 'out'], n_clock_taps=2, outs=[[300, 0]], entry='relayed', sync_stages=2)
    if lockup:
        t['relay_lockup'] = 'negedge'
    return t


def test_default_plain_and_cells_byte_identical():
    t = tree(False)
    assert all(R.relay_cell(t, r) == 'ot_dp_rrelay' for r in t['relays'])
    assert 'ot_dp_rrelay_nl' not in gen_rtl.CELLS
    assert 'ot_dp_rrelay_nl' not in K.cells_text() and 'ot_dp_rrelay_nl' not in bind.wavefront_cells_text()
    assert 'ot_dp_rrelay_nl' not in '\n'.join(R.rtl_lines(t))


def test_lockup_only_internal_hops():
    t = tree(True)
    internal = [r for r in t['relays'] if not r['q'].startswith('rst_n_t')]
    leaf = [r for r in t['relays'] if r['q'].startswith('rst_n_t')]
    assert internal and leaf
    assert all(R.relay_cell(t, r) == 'ot_dp_rrelay_nl' for r in internal)
    assert all(R.relay_cell(t, r) == 'ot_dp_rrelay' for r in leaf)
    assert all(R.relay_cell(t, r, gated=True) == 'ot_dp_rgate' for r in internal)
    rtl = '\n'.join(R.rtl_lines(t))
    assert 'ot_dp_rrelay u_rst_in ' in rtl                       # entry pin register stays plain
    assert re.search(r'ot_dp_rrelay \w+ \(\.clk\(clk\), \.d\(\w+\), \.q\(rst_o_0\)\)', rtl)   # out relay plain
    for r in internal:
        assert f"ot_dp_rrelay_nl {r['name']} (" in rtl
    assert not re.search(r'ot_dp_rrelay_nl \w+ \([^;]*\.q\(rst_(?:n_t|o_)\d+\)', rtl)


def test_kit_and_bind_cells_carry_the_cell_when_opted_in():
    text = K.cells_text(lockup=True)
    assert 'module ot_dp_rrelay_nl' in text and 'negedge clk' in text
    assert K.TREE.match('    ot_dp_rrelay_nl u_rrl_12 (.clk(clk), .d(a), .q(c));  // x')
    assert 'module ot_dp_rrelay_nl' in bind.wavefront_cells_text(lockup=True)
    assert 'ot_dp_rrelay_nl' in K.KIT_RESET_CELLS
    body = re.search(r'module ot_dp_rrelay_nl\b(.*?)endmodule', gen_rtl.LOCKUP_CELLS, re.S).group(1)
    assert body.count('posedge clk') == 1 and body.count('negedge clk') == 1 and 'q <= state' in body
    assert gen_rtl.LOCKUP_CELLS.startswith('(* keep_hierarchy, keep *)')


def plan(reset, tns=('ta', 'tb')):
    return types.SimpleNamespace(reset=reset, types={t: {} for t in tns})


def test_plan_option_validation(monkeypatch):
    monkeypatch.setattr(R, 'start_broadcast', lambda P: bool(P.reset.get('start')))
    assert R.relay_lockup(plan({}), 'ta') is False
    ok = {'relay_lockup': {'form': 'negedge', 'types': ['ta']}}
    assert R.relay_lockup(plan(ok), 'ta') is True and R.relay_lockup(plan(ok), 'tb') is False
    for bad in ({'relay_lockup': {'form': 'pulse', 'types': ['ta']}},
                {'relay_lockup': {'form': 'negedge', 'types': 'ta'}},
                {'relay_lockup': {'form': 'negedge', 'types': ['nope']}},
                dict(ok, relay_driver=True), dict(ok, start=True)):
        with pytest.raises(R.ResetError):
            R.relay_lockup(plan(bad), 'ta')


SIM = '''`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  reg d = 0; wire [3:0] a, b;
  ot_dp_rrelay    p0 (.clk(clk), .d(d),    .q(a[0]));
  ot_dp_rrelay    p1 (.clk(clk), .d(a[0]), .q(a[1]));
  ot_dp_rrelay    p2 (.clk(clk), .d(a[1]), .q(a[2]));
  ot_dp_rrelay    p3 (.clk(clk), .d(a[2]), .q(a[3]));
  ot_dp_rrelay_nl n0 (.clk(clk), .d(d),    .q(b[0]));
  ot_dp_rrelay_nl n1 (.clk(clk), .d(b[0]), .q(b[1]));
  ot_dp_rrelay_nl n2 (.clk(clk), .d(b[1]), .q(b[2]));
  ot_dp_rrelay    n3 (.clk(clk), .d(b[2]), .q(b[3]));
  integer i;
  initial begin
    #1; @(negedge clk); d = 1;
    for (i = 0; i < 12; i = i + 1) begin
      @(posedge clk); #1;
      if (a[3] !== b[3] && i > 1) begin $display("MISMATCH %0d %b %b", i, a, b); $finish; end
    end
    if (a[3] !== 1'b1 || b[3] !== 1'b1) $display("NORELEASE");
    else $display("SAME_CYCLE");
    $finish;
  end
endmodule
'''


@pytest.mark.skipif(not shutil.which('iverilog'), reason='iverilog not installed')
def test_sim_one_cycle_per_relay(tmp_path):
    """the leaf (plain posedge) behind three lockup relays releases on the SAME rising edge as a plain chain."""
    src = tmp_path / 'tb.v'
    src.write_text('`timescale 1ns/1ps\n' + re.search(r'\(\* keep_hierarchy, keep \*\)\nmodule ot_dp_rrelay \(.*?endmodule\n',
                   gen_rtl.CELLS, re.S).group(0) + gen_rtl.LOCKUP_CELLS + SIM)
    subprocess.run(['iverilog', '-o', str(tmp_path / 'a.out'), str(src)], check=True)
    out = subprocess.run(['vvp', str(tmp_path / 'a.out')], capture_output=True, text=True, check=True).stdout
    assert 'SAME_CYCLE' in out and 'MISMATCH' not in out, out
