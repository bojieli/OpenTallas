import pytest
from core_infra_network import merged_rc


def test_colinear_overlap_is_one_wire_and_shared_load():
    r=merged_rc([[0,0],[10,0],[20,0]],[2.,3.],[[[0,0],[10,0]],[[0,0],[20,0]]],(.1,.2),(.1,.2))
    assert r['wire_um']==20 and r['overlap_removed_um']==10
    assert r['wire_cap_ff']==pytest.approx(4.)
    assert r['target_elmore_ps']==pytest.approx([8.,12.])
    assert r['network_cycles']==0


def test_loop_parallel_resistance_is_solved_without_tree_pruning():
    r=merged_rc([[0,0],[10,10]],[1.],[[[0,0],[10,0],[10,10]],[[0,0],[0,10],[10,10]]],(.1,.2),(.1,.2))
    assert r['network_cycles']==1
    assert r['pin_elmore_coeff_kohm'][0][0]==pytest.approx(1.)
    assert r['wire_elmore_ps'][0]==pytest.approx(4.)
    assert r['target_elmore_ps']==pytest.approx([5.])
