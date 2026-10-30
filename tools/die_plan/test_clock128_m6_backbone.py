"""QC-001: a planned M6-entry backbone (router.stack_backbone_xy) must be DRAWN, not only planned.

The M7 riser, its VIA78 junction and the trunk branch sit on the backbone column; the lower stack stays on the actual
pin bar; an M6 jog + VIA67 join them, in both the census shapes and the emitted encoder Tcl."""
from test_clock128_r7 import C, R, _router, _tree

SHIFT = {('D', 'Y'): 0.16, ('H1', 'A'): -0.08, ('H1', 'Y'): 0.08, ('V1', 'A'): 0.24}


def _backbone_router():
    router = _router()
    router.stack_backbone_xy = lambda cell, pin, xy: (xy[0] + SHIFT[(cell, pin)], xy[1])
    return router


def test_backbone_moves_riser_and_keeps_actual_bar():
    M, cells, nets = _tree()
    wires = C.fixed_wires(M, cells, nets, 1.62, .27, off=0., router=_backbone_router(), pin_stack=True, l_drops=True)
    for w in wires:
        for s in w['stacks']:
            ax, ay = C.pin_xy(cells, s['cell'], s['pin'], .27)
            bx = round(ax + SHIFT[(s['cell'], s['pin'])], 4)
            assert s['xy'] == [bx, ay] and s['riser_from'][0] == bx
            assert s['m6_entry_xy'] == [ax, ay]
            pts = R.stack_down(s)
            assert ('M7', bx, ay) in pts and ('M6', bx, ay) in pts and ('M6', ax, ay) in pts
            assert pts[-1] == ('M1', ax, ay)
            # census: M7 riser on the backbone column, M6 jog spanning actual -> backbone
            sh = R.stack_shapes(dict(name=w['name'], stacks=[s]))
            assert any(L == 'M7' and x0 < bx < x1 and not (x0 < ax < x1) for _, L, x0, _, x1, _ in sh)
            assert any(L == 'M6' and x0 <= min(ax, bx) - .016 + 1e-8 and x1 >= max(ax, bx) + .016 - 1e-8
                       for _, L, x0, _, x1, _ in sh)
    # the branch / trunk junction of every cell load is on the backbone column
    nh = next(w for w in wires if w['name'] == 'nh')
    hx = round(C.pin_xy(cells, 'H1', 'A', .27)[0] - .08, 4)
    assert ('H1', hx, nh['trunk_tap'][1]) in [tuple(b) for b in nh['branches']]
    lines, rec = R.routed_tcl(wires, cells, {}, 'BUFx24_ASAP7_75t_R', 'NDR')
    assert sum('VIA67' in l_ for l_ in lines) >= 4
    # the M6 jog is an M6 encoder move at the pin row to the actual bar x
    assert f'$e addPoint {R.q(C.pin_xy(cells, "H1", "A", .27)[0])} {R.q(C.pin_xy(cells, "H1", "A", .27)[1])}' in lines


def test_no_backbone_callback_keeps_old_geometry():
    M, cells, nets = _tree()
    a = C.fixed_wires(M, cells, nets, 1.62, .27, off=0., router=_router(), pin_stack=True, l_drops=True)
    r = _router()
    r.stack_backbone_xy = lambda cell, pin, xy: xy
    b = C.fixed_wires(M, cells, nets, 1.62, .27, off=0., router=r, pin_stack=True, l_drops=True)
    assert a == b and not any('m6_entry_xy' in s for w in a for s in w['stacks'])


def test_backbone_off_pin_row_is_a_plan_error():
    M, cells, nets = _tree()
    r = _router()
    r.stack_backbone_xy = lambda cell, pin, xy: (xy[0] + .08, xy[1] + .27)
    try:
        C.fixed_wires(M, cells, nets, 1.62, .27, off=0., router=r, pin_stack=True, l_drops=True)
    except C.PlanError as e:
        assert any(row['kind'] == 'no_pin_stack' and 'pin row' in row['detail'] for row in e.rows)
    else:
        raise AssertionError('backbone off the pin row was accepted')
