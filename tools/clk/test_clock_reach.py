import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'die_plan'))
from clock_reach import actual_reach


def tree():
    return dict(nodes={'1': {'x': 100, 'y': 0}},
                sites={'b0': [0, 0], 'r1_0': [250, 0], 'r1_1': [500, 0], 'b1': [600, 0]},
                parent_of={'r1_0': 'b0', 'r1_1': 'r1_0', 'b1': 'r1_1'},
                node_buf={'1': 'b1'}, taps=[dict(port='t_p__clk', node=1, xy=[610, 0])])


def test_actual_sites_override_ideal_topology_coordinates():
    t = tree()
    t['sites']['r1_1'] = [750, 0]  # legalisation moved a physical repeater, ideal node unchanged
    r = actual_reach(t)
    assert r['verdict'] == 'FAIL' and r['over_count'] == 1
    assert r['over'][0] == dict(kind='cell', child='r1_1', parent='r1_0', length_um=500)


def test_tap_stub_uses_actual_driver():
    t = tree()
    t['sites']['pad'] = [0, 100]
    t['parent_of']['pad'] = 'b0'
    t['taps'][0]['driver'] = 'pad'
    r = actual_reach(t)
    assert r['over'][0]['kind'] == 'tap' and r['over'][0]['length_um'] == 710


def test_complete_short_tree_passes_without_mutation():
    t = tree(); before = copy.deepcopy(t)
    r = actual_reach(t)
    assert r['verdict'] == 'PASS' and r['cell_edges'] == 3 and r['tap_edges'] == 1
    assert t == before


def test_missing_or_nonfinite_sites_fail_closed():
    for point in (None, [float('nan'), 0], [True, 0], [0]):
        t = tree(); t['sites']['r1_0'] = point
        r = actual_reach(t)
        assert r['verdict'] == 'FAIL' and len(r['missing_sites']) == 2


def test_explicit_limit_and_exact_boundary():
    t = tree(); t['sites']['r1_0'] = [450, 0]
    assert actual_reach(t, 450)['verdict'] == 'PASS'
    assert actual_reach(t, 405)['over_count'] == 1
    with pytest.raises(ValueError): actual_reach(t, float('inf'))


def test_polarity_restoring_inverter_is_final_stub_driver():
    t = tree()
    t['sites']['q1_t_p__clk'] = [0, 100]
    t['parent_of']['q1_t_p__clk'] = 'b0'
    t['taps'][0]['driver'] = 'b1'  # older metadata can name the pre-parity driver
    r = actual_reach(t)
    assert r['over_count'] == 1 and r['over'][0]['kind'] == 'tap'
    assert r['over'][0]['parent'] == 'q1_t_p__clk'
