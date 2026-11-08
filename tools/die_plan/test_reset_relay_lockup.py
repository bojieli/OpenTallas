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
    for bad in ({'relay_lockup': {'form': 'latch', 'types': ['ta']}},
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


# ---- S81-STATION-1 11-07: reset.relay_lockup.taps (consumer-tap relays negedge too)
def tree_taps():
    t = tree(True)
    t['relay_lockup_taps'] = True
    return t


def test_taps_form_leaf_taps_negedge_outs_and_entry_plain():
    t = tree_taps()
    nck = R.consumer_count(t)
    leaf = [r for r in t['relays'] if r['q'].startswith('rst_n_t') and r.get('tap') not in range(nck, nck + len(t['outs']))]
    assert leaf
    assert all(R.relay_cell(t, r) == 'ot_dp_rrelay_nl' for r in t['relays'] if r in leaf or not r['q'].startswith('rst_n_t'))
    rtl = '\n'.join(R.rtl_lines(t))
    assert 'ot_dp_rrelay u_rst_in ' in rtl
    assert re.search(r'ot_dp_rrelay \w+ \(\.clk\(clk\), \.d\(\w+\), \.q\(rst_o_0\)\)', rtl)      # out relay plain
    for r in leaf:
        assert f"ot_dp_rrelay_nl {r['name']} (" in rtl and f".q({r['q']}))" in rtl
    # without taps the same tree keeps plain leaf relays (old CLK form #7 unchanged)
    assert all(R.relay_cell(tree(True), r) == 'ot_dp_rrelay' for r in leaf)


def test_taps_tcl_qnet_identity_skips_state_flop():
    base, taps = tree(True), tree_taps()
    for x in (base, taps):
        x.setdefault('reach_um', 405.0)
        for r in x['relays']:
            r.setdefault('kind', 'tap'); r.setdefault('xy', [0.0, 0.0])
        x.setdefault('root', [0.0, 0.0])
    a, b = R.tcl_text(base), R.tcl_text(taps)
    assert '[./]state*' not in a
    assert b.count('if {[llength $qnets] == 1 && ![string match {*[./]state*} $nm]} {') == 1
    assert a.replace('if {[llength $qnets] == 1} {', 'X') == b.replace(
        'if {[llength $qnets] == 1 && ![string match {*[./]state*} $nm]} {', 'X')


def test_taps_plan_option(monkeypatch):
    monkeypatch.setattr(R, 'start_broadcast', lambda P: False)
    on = {'relay_lockup': {'form': 'negedge', 'types': ['ta', 'tb'], 'taps': ['ta']}}
    assert R.relay_lockup_taps(plan(on), 'ta') is True and R.relay_lockup_taps(plan(on), 'tb') is False
    assert R.relay_lockup(plan(on), 'tb') is True                    # tb keeps the internal-hop-only form
    assert R.relay_lockup_taps(plan({'relay_lockup': {'form': 'negedge', 'types': ['ta']}}), 'ta') is False
    assert R.relay_lockup_taps(plan({}), 'ta') is False
    for bad in (True, ['tb'], 'ta'):
        with pytest.raises(R.ResetError):
            R.relay_lockup(plan({'relay_lockup': {'form': 'negedge', 'types': ['ta'], 'taps': bad}}), 'ta')


def test_taps_schema_is_a_type_list():
    import schema
    lk = schema.SCHEMA['properties']['reset']['properties']['relay_lockup']
    assert lk['properties']['taps']['type'] == 'array'


SIM_TAP = '''`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  reg d = 0; wire a, b; reg ea = 1; reg qa, qb; integer i, ra, rb;
  ot_dp_rrelay    p (.clk(clk), .d(d), .q(a));
  ot_dp_rrelay_nl n (.clk(clk), .d(d), .q(b));
  // the consumer: ot_dp_st epoch flop (async active-low reset)
  always @(posedge clk or negedge a) if (!a) qa <= 0; else qa <= ea;
  always @(posedge clk or negedge b) if (!b) qb <= 0; else qb <= ea;
  initial begin
    ra = -1; rb = -1;
    #1; @(negedge clk); d = 1;
    for (i = 0; i < 8; i = i + 1) begin
      @(posedge clk); #1;
      if (qa === 1'b1 && ra < 0) ra = i;
      if (qb === 1'b1 && rb < 0) rb = i;
    end
    if (ra >= 0 && ra == rb) $display("SAME_RELEASE %0d", ra); else $display("DIFF %0d %0d", ra, rb);
    $finish;
  end
endmodule
'''


@pytest.mark.skipif(not shutil.which('iverilog'), reason='iverilog not installed')
def test_sim_tap_relay_negedge_same_consumer_release(tmp_path):
    """an async-reset consumer behind the negedge tap relay leaves reset on the SAME rising edge as behind a plain one;
    MUTANT control: a relay with no state flop (q on the falling edge directly from d) releases one edge early."""
    cells = '`timescale 1ns/1ps\n' + re.search(r'\(\* keep_hierarchy, keep \*\)\nmodule ot_dp_rrelay \(.*?endmodule\n',
                                              gen_rtl.CELLS, re.S).group(0)
    def run(lock, name):
        src = tmp_path / f'{name}.v'
        src.write_text(cells + lock + SIM_TAP)
        subprocess.run(['iverilog', '-o', str(tmp_path / f'{name}.out'), str(src)], check=True)
        return subprocess.run(['vvp', str(tmp_path / f'{name}.out')], capture_output=True, text=True, check=True).stdout
    out = run(gen_rtl.LOCKUP_CELLS, 'ok')
    assert 'SAME_RELEASE' in out, out
    mutant = ('module ot_dp_rrelay_nl (input wire clk, input wire d, output reg q);\n'
              '    always @(negedge clk) q <= d;\nendmodule\n')
    assert 'DIFF' in run(mutant, 'mut')
