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


def test_declared_access_and_turn_vias_have_finite_shared_resistance():
    r=merged_rc([[0,0],[10,0]],[1.],[[[0,0],[10,0]]],(.1,.2),(.1,.2),
      horizontal_layer=2,vertical_layer=3,terminal_layers=[1,1],via_resistance_kohm={'V1':.2,'V2':.3})
    # Driver access sees whole2fF wire +1fF sink; target access sees sink only.
    assert r['target_elmore_ps']==pytest.approx([2.+.2*3+.2*1])
    assert r['via_count']==2
    assert r['pin_elmore_coeff_kohm'][0][0]==pytest.approx(1.4)
