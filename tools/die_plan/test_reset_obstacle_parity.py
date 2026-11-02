import reset_tree as RT
import pytest


def test_actual_core_track_offset_is_applied_once():
    t=dict(hard_cores=[dict(inst='core',origin_um=[100.,100.],outline_um=[10.,10.],
                            track_offset_um=[.216,.108])])
    boxes=RT.blockages(t)
    assert boxes[0]==pytest.approx((95.896,95.788,114.536,114.428))
    # This point was outside the old unshifted halo but inside the real one.
    assert not RT._free((114.4,105.),boxes,(0.,0.,200.,200.))


def test_reuse_leaf_without_lef_is_not_an_empty_street():
    t=dict(contents=[dict(inst='reuse',origin_um=[20.,20.],outline_um=[10.,10.])])
    assert not RT._free((25.,25.),RT.blockages(t),(0.,0.,100.,100.))


def test_concrete_core_wins_over_duplicate_content_body():
    t=dict(hard_cores=[dict(inst='core',origin_um=[100.,100.],outline_um=[10.,10.],
                            track_offset_um=[.216,.108])],
           contents=[dict(inst='core',origin_um=[100.,100.],outline_um=[10.,10.],lef='old.lef')])
    assert len(RT.blockages(t))==1
    assert RT.blockages(t)[0][0]==pytest.approx(95.896)


def test_split_container_gap_stays_open_with_same_clearance():
    t=dict(contents=[dict(inst='bank',origin_um=[20.,20.],outline_um=[60.,20.])],
           hard_cores=[dict(inst='bank_a',origin_um=[20.,20.],outline_um=[20.,20.]),
                       dict(inst='bank_b',origin_um=[60.,20.],outline_um=[20.,20.])])
    assert len(RT.blockages(t))==2
    assert RT._free((50.,30.),RT.blockages(t),(0.,0.,100.,100.))
    assert not RT._free((40.+RT.CLEAR_UM-.01,30.),RT.blockages(t),(0.,0.,100.,100.))


def test_power_domain_keepout_policy_unchanged():
    t=dict(contents=[dict(inst='reuse',origin_um=[20.,20.],outline_um=[10.,10.])],
           clock=dict(keepouts_um=[[60.,60.,80.,80.]]))
    assert RT.blockages(t)[-1]==(51.36,51.36,88.64,88.64)
