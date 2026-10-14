"""Clock levels and ETM normalization must preserve the physical delivery rule."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hbm_die_relay_sta as S


def sink(instance, domain='clk_stream', level='common', tree=None):
    return dict(instance=instance, master='tile', port='ck', domain=domain,
                level=level, entry_ps={'tt': 150}, etm_tree_ps=tree or {})


def evaluate(sinks):
    # Evaluate generated Tcl, including loops/pair conditions, instead of only
    # checking that a particular text fragment appears in the generator.
    stubs = r'''
proc set_cmd_units args {}
proc get_pins args { return [list [lindex $args end]] }
proc get_full_name p { return $p }
proc get_clocks c { return $c }
proc all_clocks {} { return $::clocks }
proc create_clock args { lappend ::clocks [lindex $args 1] }
proc set_clock_latency args { puts "LATENCY $args" }
proc set_propagated_clock args {}
proc set_clock_uncertainty args { puts "UNCERTAINTY $args" }
proc set_false_path args { puts "FALSEPATH $args" }
set clocks {}
'''
    return subprocess.run(['tclsh'], input=stubs + S.constraints(sinks, 'tt'),
                          text=True, capture_output=True, check=True).stdout


def test_early_launch_and_capture_get_210ps_without_falsepath():
    out = evaluate({'a/ck': sink('a'), 'b/ck': sink('b', level='early_tap'),
                    'c/ck': sink('c', domain='clk_serial')})
    for a, b in [('clk_stream', 'clk_stream__early_tap'),
                 ('clk_stream__early_tap', 'clk_stream'),
                 ('clk_stream__early_tap', 'clk_stream__early_tap')]:
        assert f'UNCERTAINTY -setup -from {a} -to {b} 0.210' in out
        assert f'FALSEPATH -from {a} -to {b}' not in out
    assert 'UNCERTAINTY -setup 0.150' in out
    assert 'FALSEPATH -from clk_stream__early_tap -to clk_serial' in out
    assert 'FALSEPATH -from clk_serial -to clk_stream__early_tap' in out


def test_source_latency_preserves_physical_entry_with_etm_tree_metadata():
    sinks = {'a/ck': sink('a'), 'b/ck': sink('b', tree={
        'tt': {'ck[0]': {'min': 40, 'max': 60}}})}
    out = evaluate(sinks)
    assert 'LATENCY -source -early -clock clk_stream 0.150000 {a/ck[0]}' in out
    assert 'LATENCY -source -late -clock clk_stream 0.150000 {a/ck[0]}' in out
    assert 'LATENCY -source -early -clock clk_stream 0.150000 {b/ck[0]}' in out
    assert 'LATENCY -source -late -clock clk_stream 0.150000 {b/ck[0]}' in out
    assert sinks['b/ck']['entry_ps']['tt'] == 150
    assert 'etm_corrected_pins=0' in out


def test_clock_tree_groups_are_scoped_to_the_pin(tmp_path):
    (tmp_path / 'tile_tt.lib').write_text('''library (tile) {
    cell (tile) {
      pin ("ck[0]") {
        timing () { timing_type : min_clock_tree_path;
          cell_rise (scalar) { values ("100"); } }
        timing () { timing_type : max_clock_tree_path;
          cell_rise (scalar) { values ("120"); } }
      }
      pin ("ck1") {
        timing () { timing_type : min_clock_tree_path;
          cell_rise (scalar) { values ("300"); } }
        timing () { timing_type : max_clock_tree_path;
          cell_rise (scalar) { values ("340"); } }
      }
    }
    }''')
    assert S.view_clock_trees(tmp_path, 'tile') == {
        'tt': {'ck[0]': {'min': 100, 'max': 120},
               'ck1': {'min': 300, 'max': 340}}}
    # Extrema across the two clocks cannot prove population skew.
    assert S.view_spread(tmp_path, 'tile') == {}
    measured = {'tile': {'parasitics': 'routed (6_final.spef)', 'boundary_n': 80,
                         'ss': {'min': 100, 'max': 130},
                         'tt': {'min': 80, 'max': 102}}}
    assert S.view_spread(tmp_path, 'tile', measured) == {'ss': 30, 'tt': 22}
    measured['tile']['parasitics'] = 'placement-estimated'
    assert S.view_spread(tmp_path, 'tile', measured) == {}


def test_uniform_skew_mode_does_not_split_domains(monkeypatch):
    monkeypatch.setattr(S, 'SKEW_ALL', True)
    out = evaluate({'a/ck': sink('a'), 'b/ck': sink('b', level='early_tap')})
    assert 'UNCERTAINTY -setup 0.210' in out
    assert '__early_tap' not in out


def test_tt_fallback_normalizes_against_bound_ss_model(tmp_path):
    (tmp_path / 'tile_ss.lib').write_text('''pin (ck) {
      timing () { timing_type : min_clock_tree_path;
        cell_rise (scalar) { values ("40"); } }
      timing () { timing_type : max_clock_tree_path;
        cell_rise (scalar) { values ("60"); } }
    }''')
    trees = S.view_clock_trees(tmp_path, 'tile')
    assert trees['tt'] == trees['ss'] == {'ck': {'min': 40, 'max': 60}}


def test_unmeasured_insertion_conservative_pairs_stay_synchronous():
    out = evaluate({'a/ck': sink('a'), 'u/ck': sink('u', level='unmeasured'),
                    'e/ck': sink('e', level='early_tap'),
                    'v/ck': sink('v', domain='clk_serial', level='unmeasured')})
    for a, b in [('clk_stream', 'clk_stream__unmeasured'),
                 ('clk_stream__unmeasured', 'clk_stream'),
                 ('clk_stream__unmeasured', 'clk_stream__unmeasured'),
                 ('clk_stream__early_tap', 'clk_stream__unmeasured'),
                 ('clk_stream__unmeasured', 'clk_stream__early_tap')]:
        assert f'UNCERTAINTY -setup -from {a} -to {b} 0.210' in out
        assert f'FALSEPATH -from {a} -to {b}' not in out
    assert 'FALSEPATH -from clk_stream__unmeasured -to clk_serial__unmeasured' in out


def test_unmeasured_delivery_record_exposes_missing_R(tmp_path):
    sinks = {'u/ck': sink('u')}
    record = S.delivery_record(tmp_path, sinks)
    tile = record['tiles']['tile']
    assert tile['level'] == 'unmeasured'
    assert tile['missing_R_evidence'] is True
    assert tile['hop_skew_ps'] == 150
    assert record['summary']['unmeasured'] == ['tile']
    assert sinks['u/ck']['level'] == 'unmeasured'


def test_estimated_R_cannot_claim_common_budget(tmp_path):
    s = sink('u')
    s.update(internal_ps={'tt': 150}, insertion_source='view Liberty min ck->out - offset')
    tile = S.delivery_record(tmp_path, {'u/ck': s})['tiles']['tile']
    assert tile['R_ps']['tt'] == 150  # retain the estimate visibly
    assert tile['level'] == 'unmeasured' and tile['missing_R_evidence']
    assert tile['hop_skew_ps'] == 150
    s['insertion_source'] = 'view Liberty clock_tree_path (min+max)/2'
    tile = S.delivery_record(tmp_path, {'u/ck': s})['tiles']['tile']
    assert tile['level'] == 'common' and not tile['missing_R_evidence']
    s['insertion_source'] = 'placeholder recipe (analytic, hfd_ph_<corner>.lib)'
    tile = S.delivery_record(tmp_path, {'u/ck': s})['tiles']['tile']
    assert tile['level'] == 'common' and tile['analytic_pathfinding_R']
