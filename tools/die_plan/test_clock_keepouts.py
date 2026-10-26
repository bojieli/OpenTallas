"""Physical IO reservations apply to taps, including a one-tap partition."""
import pytest
import schema as S


def test_clock_keepout_moves_single_grid_tap():
    raw = dict(die=dict(name='probe', outline_um=[80, 80], reach_um=405),
               partition_types={'t': dict(module='probe_t', outline_um=[80, 80],
                   clock=dict(tap_um=[20, 40], keepouts_um=[[0, 0, 40, 80]]))},
               partitions=[dict(name='a', type='t', origin_um=[0, 0])], ports=[], lanes=[])
    P = S.Plan(raw)
    _, x, y = S.tap_grid(P, 't')[0]
    assert x >= 40 + S.TAP_CLEAR_UM
    assert S.TAP_CLEAR_UM <= y <= 80 - S.TAP_CLEAR_UM


def test_clock_keepout_without_any_legal_site_fails():
    t = dict(module='blocked', outline_um=[40, 40], clock=dict(keepouts_um=[[0, 0, 40, 40]]))
    with pytest.raises(ValueError, match='no legal clock tap site'):
        S.tap_clear(t, 20, 20)


def test_type_keepout_union_respects_mirrors():
    # The PHY reserve occupies opposite die edges on MY copies, but the same type-frame side.
    raw = dict(die=dict(name='mirror', outline_um=[200, 80], reach_um=405),
               partition_types={'t': dict(module='t', outline_um=[80, 80])},
               partitions=[dict(name='a', type='t', origin_um=[0, 0]),
                           dict(name='b', type='t', origin_um=[120, 0], orient='MY')], ports=[], lanes=[])
    P = S.Plan(raw)
    for n, points in [('a', [(0, 0), (30, 80)]), ('b', [(170, 0), (200, 80)])]:
        corners = [P.to_type(n, (x, y)) for x in (points[0][0], points[1][0])
                   for y in (points[0][1], points[1][1])]
        assert [min(x for x, y in corners), min(y for x, y in corners),
                max(x for x, y in corners), max(y for x, y in corners)] == [0, 0, 30, 80]


def test_bare_hard_macro_has_one_fixed_clock_terminal():
    # A bare hard macro (no hard_cores) larger than one R4 pitch cell keeps ONE clock port 'clk' at its LEF tap_um,
    # exactly as die_clock.plan_taps sees it (no grid clk_t<i> ports the macro does not have).
    raw = dict(die=dict(name='probe', outline_um=[2000, 2000], reach_um=405),
               partition_types={'phy': dict(module='probe_phy', hard=True, outline_um=[900, 1500],
                                            clock=dict(tap_um=[388.8, 388.8])),
                                'soft': dict(module='probe_soft', outline_um=[900, 1500])},
               partitions=[dict(name='a', type='phy', origin_um=[0, 0]),
                           dict(name='b', type='soft', origin_um=[1000, 0])], ports=[], lanes=[])
    P = S.Plan(raw)
    assert S.tap_grid(P, 'phy') == [('clk', 388.8, 388.8)]
    assert len(S.tap_grid(P, 'soft')) > 1
