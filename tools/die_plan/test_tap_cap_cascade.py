"""TAP-GRID-R2 11-21 (FABLE-VISUAL-0030 cause 5): taps far over the cap beside near-empty taps.

KV pc_v3: the one-hop cap pass filled the near neighbours of clk_t4 / clk_t7 to the 1,200 cap, and then every tap in the
200 um reach was full, so clk_t4 kept 10,960 sinks and clk_t7 9,982 while clk_t2 held 46 and clk_t11 19.  S81 col_h9_r1:
t25 / t1 / t2 sat at the 3,000 default cap against a median of 324.  Fixes under test:
  - clock_taps.tcl CT_CASCADE (OT_TAP_CAP_CASCADE=1): ejection chains, over-full tap -> full neighbour -> tap with room;
  - a CAPACITY WARN when the sinks cannot fit taps x cap at all (the die needs bank taps, not a better assignment);
  - gen_phys: clock.tap_grid caps a tap at bank_sinks and turns the cascade on; clock.tap_cap_cascade alone turns it on.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_clock_taps_cap_recheck import run  # noqa: E402  (OpenDB mock + clock_taps.tcl runner)

# 1-D shape: clk at 0 holds 15 sinks (cap 10); clk_t1 at 500 is full; clk_t2 at 1000 has room but is 900 um from the
# excess sinks (reach 600).  One hop cannot help; a chain clk -> clk_t1 -> clk_t2 can.
CHAIN = r'''
addtap clk 0; addtap clk_t1 500; addtap clk_t2 1000
fills a 15 100
fills b 10 500
fills c 2 1000
'''
ENV = 'set ::env(OT_TAP_MAX_SINKS) 10\nset ::env(OT_TAP_REASSIGN_UM) 600\nset ::env(OT_TAP_PITCH_UM) 1200'


def test_one_hop_pass_leaves_the_dense_tap_over_cap(tmp_path):
    out, nets, js = run(tmp_path, CHAIN, ENV)
    assert js['sinks'] == {'clk': 15, 'clk_t1': 10, 'clk_t2': 2}, js
    assert 'WARN clk keeps 15 sinks > cap 10' in out and 'CAP_CASCADE' not in out, out


def test_cascade_moves_the_excess_through_the_full_neighbour(tmp_path):
    out, nets, js = run(tmp_path, CHAIN, ENV + '\nset ::env(OT_TAP_CAP_CASCADE) 1')
    assert js['sinks'] == {'clk': 10, 'clk_t1': 10, 'clk_t2': 7}, js
    assert js['over_cap'] == [] and 'CAP_CASCADE 5 ejection chains' in out, out
    # every moved sink is within reach of its new tap: a* (x 100) only went to clk_t1 (500), b* (x 500) to clk_t2 (1000)
    assert sum(1 for k, v in nets.items() if k.startswith('a') and v == 'n_clk_t1') == 5
    assert not any(v == 'n_clk_t2' for k, v in nets.items() if k.startswith('a'))
    assert sum(1 for k, v in nets.items() if k.startswith('b') and v == 'n_clk_t2') == 5


def test_cascade_never_breaks_reach_or_overfills(tmp_path):
    # clk_t2 only has room for 1 more: the chain moves 1, the rest stays with a loud WARN
    body = CHAIN.replace('fills c 2 1000', 'fills c 9 1000')
    out, nets, js = run(tmp_path, body, ENV + '\nset ::env(OT_TAP_CAP_CASCADE) 1')
    assert js['sinks'] == {'clk': 14, 'clk_t1': 10, 'clk_t2': 10}, js
    assert 'WARN clk keeps 14 sinks > cap 10' in out and 'WARN CAPACITY 34 movable sinks > 3 taps x cap 10' in out, out
    assert 'needs >= 4 taps' in out


def test_no_capacity_warn_when_it_fits(tmp_path):
    out, _, _ = run(tmp_path, CHAIN, ENV + '\nset ::env(OT_TAP_CAP_CASCADE) 1')
    assert 'CAPACITY' not in out


def test_gen_phys_tap_grid_caps_at_bank_sinks_and_turns_cascade_on(monkeypatch):
    import gen_phys as G
    monkeypatch.delenv('OT_TAP_MAX_SINKS', raising=False)
    monkeypatch.delenv('OT_TAP_SPAN_UM', raising=False)
    assert G._tap_cap({'clock': {}}) == 3000                                        # no key: unchanged default
    assert G._tap_cap({'clock': {'tap_grid': {}}}) == 1000                          # tap grid: bank_sinks default
    assert G._tap_cap({'clock': {'tap_grid': {'bank_sinks': 1500}, 'tap_max_sinks': 1200}}) == 1200
    assert G._tap_cap({'clock': {'tap_grid': {'bank_sinks': 800}, 'tap_max_sinks': 1200}}) == 800
    monkeypatch.setenv('OT_TAP_MAX_SINKS', '2000')
    assert G._tap_cap({'clock': {'tap_grid': {}}}) == 2000                          # the gen env still wins
    assert 'export OT_TAP_CAP_CASCADE = 1' in G.tap_grid_exports({'clock': {'tap_grid': {}}})
    assert G.tap_grid_exports({'clock': {}}) == []


def test_schema_accepts_tap_cap_cascade():
    src = (Path(__file__).resolve().parent / 'schema.py').read_text()
    assert '"tap_cap_cascade": {"type": "boolean"}' in src
    gp = (Path(__file__).resolve().parent / 'gen_phys.py').read_text()
    assert 'get("tap_cap_cascade") and not tap_grid_cfg(t)' in gp

# Keep the original mock unchanged for its one-dimensional cap tests. The
# cascade span cases place the selected registers on opposite sides of a tap.
XY = r'''
rename instp instp_x
proc instp {name m args} {
    if {$m eq "getLocation" && [info exists ::Y($name)]} {
        return [list $::X($name) $::Y($name)]
    }
    return [instp_x $name $m {*}$args]
}
proc ffxy {name x y} {
    ff $name $x
    set ::Y($name) $y
}
'''


def test_cascade_rechecks_receiving_tap_span_after_each_ejection(tmp_path):
    body = XY + r'''
addtap clk 0; addtap clk_t1 500; addtap clk_t2 1000
fills a 8 230
fills bmid 4 500
ffxy b_up 510 120
ffxy b_down 510 -120
fills c 2 1000
'''
    env = r'''
set ::env(OT_TAP_MAX_SINKS) 6
set ::env(OT_TAP_REASSIGN_UM) 650
set ::env(OT_TAP_SPAN_UM) 650
set ::env(OT_TAP_CAP_CASCADE) 1
'''
    out, nets, js = run(tmp_path, body, env)
    assert js['sinks'] == {'clk': 6, 'clk_t1': 6, 'clk_t2': 4}
    assert 'CAP_CASCADE 2 ejection chains' in out
    assert sum(nets[n] == 'n_clk_t2' for n in ('b_up', 'b_down')) == 1
    assert sum(v == 'n_clk_t2' for n, v in nets.items() if n.startswith('bmid')) == 1


def test_cascade_rechecks_full_neighbour_span_after_each_incoming_sink(tmp_path):
    body = XY + r'''
addtap clk 0; addtap clk_t1 500; addtap clk_t2 800
fills a 6 0
ffxy a_up 240 90
ffxy a_down 240 -90
fills b 6 500
fills c 2 800
'''
    env = r'''
set ::env(OT_TAP_MAX_SINKS) 6
set ::env(OT_TAP_REASSIGN_UM) 410
set ::env(OT_TAP_SPAN_UM) 370
set ::env(OT_TAP_CAP_CASCADE) 1
'''
    out, nets, js = run(tmp_path, body, env)
    assert js['sinks'] == {'clk': 7, 'clk_t1': 6, 'clk_t2': 3}
    assert 'CAP_CASCADE 1 ejection chains' in out
    assert sum(nets[n] == 'n_clk_t1' for n in ('a_up', 'a_down')) == 1
