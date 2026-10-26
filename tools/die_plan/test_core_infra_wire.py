import pytest
from core_infra_wire import rooted_rc


def test_shared_edge_sees_both_downstream_sinks():
    r=rooted_rc([[0,0],[10,0],[20,0]],[2.,3.],(.1,.2),(.1,.2))
    # First edge sees 5fF sinks +2fF downstream wire +1fF own half-C.
    assert r['target_elmore_ps']==pytest.approx([8.,12.])
    assert r['total_load_ff']==pytest.approx(9.)


def test_horizontal_macro_obstruction_changes_channel_and_rc():
    args=([[0,5],[20,5]],[1.],(.1,.2),(.1,.2))
    over_macro=rooted_rc(*args)
    around_macro=rooted_rc(*args,obstacles=[[5,0,15,10]],clearance=1.)
    assert over_macro['wire_um']==20 and around_macro['wire_um']==32
    assert around_macro['target_elmore_ps'][0]>over_macro['target_elmore_ps'][0]


def test_corner_cap_and_layer_rc_are_explicit():
    a=rooted_rc([[0,0],[10,0]],[1.],(.1,.2),(.2,.3))
    b=rooted_rc([[0,0],[10,0]],[2.],(.1,.2),(.2,.3))
    assert b['target_elmore_ps'][0]-a['target_elmore_ps'][0]==pytest.approx(1.)
    with pytest.raises(ValueError):rooted_rc([[0,0],[10,0]],[],(.1,.2),(.1,.2))
