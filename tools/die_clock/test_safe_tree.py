"""QW-DIECLK3 10-19: safe die clock tree (regtree SAFE) + reach check (clock_reach_check.py).

Geometry = a scaled Qwen compute die column pair: two hard columns 2445 um wide with a 17.28 um abutment gap
(qfd_c_b16_dv at 2462.4 pitch), a 129.6 um channel above them, rst_field-like sinks in the gap and a sink beyond the
far column.  Legacy (dv2f19g2 rA): no free cell in the gap -> the gap sinks' leaf sits across a column, one clock net
> 2 mm.  Safe + grid_center: every clock segment <= SEG_MAX, no clock cell inside a block, every net <= 405 um."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regtree as rt  # noqa: E402
import build  # noqa: E402  grid_center only (no OpenROAD import at module level)
import clock_reach_check as crc  # noqa: E402

W, H = 5300.0, 3400.0
COLS = [(200.0, 100.0, 2645.0, 3100.0), (2662.28, 100.0, 5107.28, 3100.0)]   # 17.28 um gap at x 2645..2662.28
GAP_X = 2653.6


def sinks():
    s = [(f'rst_{i}/clk', 'qfd_rst_rep', GAP_X, 300.0 + 220.0 * i, 'qfd_rst_rep/clk') for i in range(12)]
    s += [('far/ck', 'm', 5200.0, 1500.0, 'm/ck'), ('top/ck', 'm', 1500.0, 3150.0, 'm/ck')]
    return s


def manifest(b, root, rxy):
    """the build.py manifest subset clock_reach_check reads, from a regtree Builder (no OpenROAD)."""
    cells = [[n, c, x, y] for n, c, x, y in b.bufs]
    sk = {s[0]: dict(x=s[2], y=s[3]) for s in sinks()}
    par = dict(b.parent)
    return dict(cells=cells, sinks=sk, parent=par, trees={'t': dict(root=root, root_xy=list(rxy))},
                safe_tree=dict(violations=list(b.violations)) if b.safe else None)


def build_tree(safe, center):
    g = rt.dct.Grid(W, H, COLS)
    if center:
        build.grid_center(g, COLS)
    rt.SAFE = safe
    try:
        b = rt.Builder(g, 'dc_t')
        b.build('pll/ck', (100.0, 3300.0), rt.cluster(sinks()))
    finally:
        rt.SAFE = False
    return g, b


def inside(x, y, r):
    return r[0] < x < r[2] and r[1] < y < r[3]


def test_legacy_reproduces_unbuffered_cross_column_leaf():
    g, b = build_tree(safe=False, center=False)
    r = crc.check(manifest(b, 'pll/ck', (100.0, 3300.0)))
    assert r['verdict'] == 'FAIL' and r['max_um'] > 405.0           # the dv2f19g2 class: unbuffered over a column


def test_safe_tree_meets_reach_and_never_sits_on_a_block():
    g, b = build_tree(safe=True, center=True)
    assert b.violations == []
    for n, cell, x, y in b.bufs:
        assert not any(inside(x, y, r) for r in COLS), (n, x, y)
    r = crc.check(manifest(b, 'pll/ck', (100.0, 3300.0)))
    assert r['verdict'] == 'PASS', r['worst'][:3]
    assert r['max_um'] <= rt.SEG_MAX + 2 * rt.GRID                 # segment <= SEG_MAX (+ cell-centre rounding)


def test_safe_plan_segments_bounded_on_long_free_path():
    g = rt.dct.Grid(3000.0, 200.0, [])
    rt.SAFE = True
    try:
        b = rt.Builder(g, 'dc_p')
        path = [(i, 5) for i in range(0, 290)]
        reps, d = b.plan(path)
    finally:
        rt.SAFE = False
    ks = [0] + [c[0] for c in reps] + [289]
    assert max(k1 - k0 for k0, k1 in zip(ks, ks[1:])) * rt.GRID <= rt.SEG_MAX
    assert b.violations == [] and d > 0


def test_safe_route_goes_around_a_wide_block():
    blk = [(500.0, 0.0, 2945.0, 2900.0)]           # wide block, free channel above y 2900
    g = rt.dct.Grid(3500.0, 3100.0, blk)
    rt.SAFE = True
    try:
        b = rt.Builder(g, 'dc_r')
        p = b.route(g.cell(300.0, 1000.0), g.cell(3200.0, 1000.0))
    finally:
        rt.SAFE = False
    run = best = 0
    for c in p:
        run = 0 if g.free(c) else run + 1
        best = max(best, run)
    assert best * rt.GRID <= rt.SAFE_RUNS[-1]       # never a run over the 2445-um block


def test_reach_check_flags_long_net():
    m = dict(cells=[['dc_x_L1', 'BUFx24_ASAP7_75t_R', 0.0, 0.0]], sinks={'a/ck': dict(x=2472.0, y=10.0)},
             parent={'a/ck': 'dc_x_L1'}, trees={})
    r = crc.check(m)
    assert r['verdict'] == 'FAIL' and r['over_limit'] == 1 and r['over_by_driver_type'] == {'L': 1}
    m['sinks']['a/ck'] = dict(x=150.0, y=10.0)
    assert crc.check(m)['verdict'] == 'PASS'


def test_regional_spec_safe_and_neighbours(tmp_path):
    import json
    import subprocess
    spec = dict(note='', trees=[dict(name='r0', root='clk_rx/pll_r0[0]', period=833.333333, sinks=5),
                                dict(name='r1', root='clk_rx/pll_r1[0]', period=833.333333, sinks=3)])
    pairs = dict(gap_root_pairs=[], land_owed=[dict(src_root=['clk_rx/pll_r0[0]'], dst_root=['clk_rx/pll_r1[0]'],
                                                    src_master='a', dst_master='b', bus='n_x', bits=8)])
    (tmp_path / 's.json').write_text(json.dumps(spec)); (tmp_path / 'p.json').write_text(json.dumps(pairs))
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qwen_regional_spec.py'),
                          '--spec', str(tmp_path / 's.json'), '--pairs', str(tmp_path / 'p.json'),
                          '--out-spec', str(tmp_path / 'o.json'), '--out-families', str(tmp_path / 'f.json'),
                          '--out-owed', str(tmp_path / 'w.json'), '--grid-center', '--safe-tree', '--neighbours'],
                         capture_output=True, text=True, check=True).stdout
    o = json.loads((tmp_path / 'o.json').read_text())
    assert o['safe_tree'] and o['grid_center'] and o['neighbours'] == [['r0', 'r1']] and o['spine']['balance'] is False
    assert 'neighbour_pairs 1' in out
