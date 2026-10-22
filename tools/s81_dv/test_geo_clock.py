"""S81.CLK geometric regional clock roots (geo_clock.py + dv_bind reset tree crossings)."""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_bind as D  # noqa: E402
import geo_clock as GC  # noqa: E402


def test_grid_s81_die_is_11x6_and_fits_80ps():
    g = GC.Grid(33000.0, 26000.0)
    assert (g.nx, g.ny) == (11, 6)
    assert g.cw == pytest.approx(3000.0) and g.ch == pytest.approx(4333.333, abs=1e-2)
    assert GC.region_spread_ps(g.cw, g.ch) == pytest.approx(77.1, abs=0.05)
    assert GC.region_spread_ps(g.cw, g.ch) <= GC.SPREAD_PS
    # the S81 column blocks (svc_rs 3802, SerDes 3845, bk_sel 4190 um tall) fit one row
    assert max(3802, 3845, 4190) <= g.ch
    # coarser grids do not fit the in-region budget in the same model
    assert GC.region_spread_ps(33000 / 10, 26000 / 6) > GC.SPREAD_PS
    assert GC.region_spread_ps(33000 / 8, 26000 / 6) > GC.SPREAD_PS
    assert (GC.Grid(9000.0, 3000.0, 3000.0).nx, GC.Grid(9000.0, 3000.0, 3000.0).ny) == (3, 1)
    # same wire model as tools/die_clock_check.wire_ps
    assert GC.wire_ps(420.0) == pytest.approx(25 + 8.6e-4 * 420 * 420)
    assert GC.wire_ps(840.0) == pytest.approx(2 * GC.wire_ps(420.0))


def test_grid_regions_and_clamp():
    g = GC.Grid(33000.0, 26000.0)
    assert g.region(0, 0) == 'g0_0'
    assert g.region(32999.9, 25999.9) == 'g10_5'
    assert g.region(33000.0, 26000.0) == 'g10_5'           # clamped on the die edge
    assert g.region(3100.0, 4300.0) == 'g1_0'
    x0, y0, x1, y1 = g.box('g1_0')
    assert x0 <= 3100.0 < x1 and y0 <= 4300.0 < y1
    h = GC.Grid.from_spec(g.spec())
    assert (h.nx, h.ny, h.maxc) == (g.nx, g.ny, g.maxc)
    assert h.xs == pytest.approx(g.xs, abs=1e-3) and h.ys == pytest.approx(g.ys, abs=1e-3)
    assert h.region(3100.0, 4300.0) == 'g1_0'


TABLE = {'masters': {'f': {'clk': 'ck_r0'}, 'u': {'clk': 'clk'}, 'phy': {'clk': 'ck', 'clock_port': 'ck_hbm'}},
         'instance_clock_ports': {'fr': {'ck_r0': 'ck_frame_fr_r0'}}}


def test_block_regions_kinds():
    g = GC.Grid(33000.0, 26000.0)
    blocks = [dict(name='fr', master='f', x=100, y=100, w=1500, h=5000),        # table clock (frame), oversize anyway
              dict(name='small', master='u', x=4000, y=100, w=400, h=300),
              dict(name='col', master='u', x=9134, y=2724, w=1728, h=3802),     # svc_rs-like column cut by y 4333
              dict(name='colin', master='u', x=9134, y=4400, w=1728, h=3802),   # the same column inside row 1
              dict(name='tall', master='u', x=9000, y=10000, w=1253, h=6739),   # slice-like: own root
              dict(name='phy', master='phy', x=12000, y=100, w=8500, h=1177)]   # fixed clock_port
    reg, info = GC.block_regions(blocks, g, TABLE)
    assert info['fr']['kind'] == 'table_clock' and reg['fr'] == 'frame_fr_r0' and info['fr']['cell'] == 'g0_0'
    assert reg['small'] == 'g1_0' and info['small']['kind'] == 'grid'
    assert reg['col'] == 'b_col' and info['col']['why'] == 'cut by a region edge'
    assert reg['colin'] == 'g3_1' and info['colin']['kind'] == 'grid'
    assert info['tall']['why'] == 'oversize'
    assert reg['tall'] == 'b_tall' and info['tall']['kind'] == 'own_root'
    assert info['phy']['kind'] == 'table_clock'
    ext = GC.extents(g, blocks, reg)
    assert ext['b_tall'] == (9000, 10000, 10253, 16739)
    assert ext['g1_0'] == g.box('g1_0')                 # 'small' lies inside its cell
    assert ext['g3_1'] == g.box('g3_1')                 # every grid region's blocks lie inside its cell
    assert ext['b_col'] == (9134, 2724, 10862, 6526)
    assert len([r for r in ext if r.startswith('g')]) == 66


def test_aligned_grid_avoids_cutting_blocks_and_pairs():
    # a uniform 3 x 1 grid on 9 x 4 mm cuts 'mid' (x 2900-3100) and the 0-stage pair p/q across x 6000
    blocks = [dict(name='mid', master='u', x=2900.0, y=1000.0, w=200.0, h=200.0),
              dict(name='p', master='u', x=5700.0, y=1000.0, w=200.0, h=200.0),
              dict(name='q', master='u', x=6100.0, y=1000.0, w=200.0, h=200.0)]
    uni = GC.Grid(9000.0, 4000.0, (3000.0, 4334.0))
    reg_u, _ = GC.block_regions(blocks, uni, TABLE)
    assert reg_u['mid'] == 'b_mid' and reg_u['p'] != reg_u['q']
    g = GC.Grid.aligned(9000.0, 4000.0, blocks, TABLE, (3000.0, 4334.0), step=50.0, pairs=[('p', 'q')])
    assert g.nx >= 3 and max(b - a for a, b in zip(g.xs, g.xs[1:])) <= 3000.0
    reg, info = GC.block_regions(blocks, g, TABLE)
    assert all(v['kind'] == 'grid' for v in info.values())
    assert reg['p'] == reg['q']
    assert GC.region_spread_ps(g.cw, g.ch) <= GC.SPREAD_PS
    # cost first, cells second: the block b (x 2905-3100) is never cut; a third cell is added so the pair p/q is not cut
    # either (2 cells would need one edge in x 2900-3000, between p and q)
    g2 = GC.Grid.aligned(5900.0, 4000.0, [dict(name='b', master='u', x=2905.0, y=0.0, w=195.0, h=200.0),
                                          dict(name='p', master='u', x=2800.0, y=1000.0, w=100.0, h=100.0),
                                          dict(name='q', master='u', x=3100.0, y=1000.0, w=100.0, h=100.0)],
                         TABLE, (3000.0, 4334.0), pairs=[('p', 'q')])
    assert g2.nx == 3 and not any(2905.0 < x < 3100.0 for x in g2.xs)
    assert not any(2850.0 < x < 3150.0 for x in g2.xs)


def test_root_gate():
    g = GC.Grid(33000.0, 26000.0)
    ext = GC.extents(g, [], {})
    ok = GC.root_gate({'g0_0': [('a', 10, 10), ('b', 3000 + 400, 4333 + 400)]}, ext)
    assert ok['verdict'] == 'PASS' and ok['roots']['g0_0']['sinks'] == 2
    bad = GC.root_gate({'g0_0': [('a', 10, 10), ('far', 20000, 20000)], 'cl0N': [('x', 1, 1)]}, ext)
    assert bad['verdict'] == 'FAIL' and set(bad['fails']) == {'g0_0', 'cl0N'}
    assert bad['roots']['g0_0']['outside'] == 1
    assert bad['max_span_um'] == pytest.approx(19990.0)


# ---------------------------------------------------------------- reset tree regression
def plan(blocks, W=9000.0, H=3000.0):
    return {'facts': {'die_um': [W, H]}, 'blocks': blocks}


BLOCKS = [dict(name='a', x=500.0, y=1200.0, w=600.0, h=600.0), dict(name='b', x=7600.0, y=1200.0, w=600.0, h=600.0)]
PTS = {'l0': [(2000.0, 1000.0), (2400.0, 1000.0), (2800.0, 1000.0)]}
STATION = re.compile(r'^\s*(\S+) (st_\S+) \(\.ck\((\S+?)\), \.rs\((\S+?)\), \.i\((\S+?)\), \.o\((\S+?)\)\);')


def stations(verilog):
    out = {}
    for line in verilog:
        m = STATION.match(line)
        if m:
            out[m.group(2)] = dict(ck=m.group(3), up=m.group(4), o=m.group(6))
    return out


def base_dv_bind():
    """dv_bind.py as of the S81.CLK base commit (2de6acded), for the legacy-mode regression; None outside git"""
    src = subprocess.run(['git', '-C', str(HERE), 'show', '2de6acded:tools/s81_dv/dv_bind.py'], capture_output=True)
    if src.returncode:
        return None
    td = tempfile.mkdtemp()
    p = Path(td) / 'dv_bind_base.py'
    p.write_bytes(src.stdout)
    spec = importlib.util.spec_from_file_location('dv_bind_base', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reset_tree_legacy_mode_unchanged(monkeypatch):
    monkeypatch.delenv('OT_RESET_GATE', raising=False)
    base = base_dv_bind()
    if base is None:
        pytest.skip('base commit not reachable')
    reg = {'a': 'clA', 'b': 'clB'}
    old = base.reset_tree(plan(BLOCKS), reg, PTS, {})
    new = D.reset_tree(plan(BLOCKS), reg, PTS, {})
    assert new['verilog'] == old['verilog']
    assert new['depth'] == old['depth'] and new['block_leaf'] == old['block_leaf']
    assert new['summary']['release_crossings'] == 0 and new['summary']['crossings'] == []


def test_reset_tree_geometric_crossings(monkeypatch):
    monkeypatch.delenv('OT_RESET_GATE', raising=False)
    g = GC.Grid(9000.0, 3000.0, 3000.0)                 # 3 x 1 cells of 3 mm
    reg = {'a': 'g0_0', 'b': 'g2_0'}
    leg = D.reset_tree(plan(BLOCKS), reg, PTS, {})
    geo = D.reset_tree(plan(BLOCKS), reg, PTS, {}, grid=g)
    st_leg, st_geo = stations(leg['verilog']), stations(geo['verilog'])
    xk = {k for k in st_geo if k.endswith('_xk')}
    # same tree: every legacy station is still there, the only additions are the crossing stages
    assert set(st_geo) - xk == set(st_leg)
    s = geo['summary']
    assert s['release_crossings'] == len(xk) >= 2       # the tree runs from the middle cell into both outer cells
    pos = {p['inst']: p['xy'] for p in geo['place']}
    for x in s['crossings']:
        child, stage, parent = st_geo[x['child']], st_geo[x['stage']], st_geo[x['parent']]
        assert x['src_region'] != x['dst_region']
        assert stage['ck'] == f"ck_{x['dst_region']}" == child['ck']         # receiving region clocks both flops
        assert parent['ck'] == f"ck_{x['src_region']}"
        assert stage['up'] == parent['o'] and child['up'] == stage['o']   # parent -> xk -> child
        assert geo['depth'][stage['o']] == geo['depth'][parent['o']] + 1
        assert geo['depth'][child['o']] == geo['depth'][parent['o']] + 2
        assert pos[x['stage']] == pos[x['child']]
    # every station is clocked by the cell of its own point; non-crossing edges keep one release edge per hop
    for inst, row in st_geo.items():
        if inst.startswith('st_rs') or inst.startswith('st_rsl'):
            assert row['ck'] == f'ck_{g.region(*pos[inst])}'
        if not inst.endswith('_xk') and row['up'] in geo['depth'] and row['up'] != 'rst_sync1':
            up_is_parent_station = not row['up'].endswith('_xk')
            if up_is_parent_station:
                assert geo['depth'][row['o']] == geo['depth'][row['up']] + 1
    # release depth = legacy depth + crossings on the path; calendars read it through the leaves
    assert s['max_release_depth'] == max(geo['depth'][k] for k in geo['depth'] if not k.endswith('_xk'))
    assert s['max_release_depth'] >= leg['summary']['max_release_depth'] + 1
    assert s['max_crossings_on_path'] >= 1
    for b, leaf in geo['block_leaf'].items():
        assert geo['depth'][leaf] >= leg['depth'][leaf]
        assert s['block_release_depth'][b] == geo['depth'][leaf] + 1
    assert set(s['clock_regions']) <= {'g0_0', 'g1_0', 'g2_0'}
    assert s['stations'] == len(st_geo) + 2 == leg['summary']['stations'] + len(xk)   # + the 2 root synchronisers


def test_emit_geometric_prunes_unused_region_ports():
    import test_port_clock_bind as T
    t = T.PortClockBind('test_production_emission_A_A_B_B_C')
    t.setUp()
    t.table['clock_regions'] = {'mode': 'geometric'}
    text = t.emitted()
    # region roots are geometric cells, never logical groups, and every declared region root has a load
    assert not re.search(r'\bck_cl', text)
    declared = re.findall(r'input wire (ck_(?:g\d+_\d+|b_\w+));', text)
    assert declared == ['ck_g0_0']             # 'other' (centre 650, 150) on the 800 x 400 test die: one cell
    for net in declared:
        assert re.search(r'\(' + net + r'\)', text)


def test_reset_local_leaf_crossing_is_reused_and_priced(monkeypatch):
    monkeypatch.delenv('OT_RESET_GATE', raising=False)
    g = GC.Grid(9000.0, 3000.0, 3000.0)
    rst = D.reset_tree(plan(BLOCKS), {'a': 'g0_0', 'b': 'g2_0'}, PTS, {}, grid=g)
    leaf = rst['block_leaf']['a']
    before = rst['summary']['release_crossings']
    depth = rst['depth'][leaf]
    master = D.RST_RLY['EW']
    net = D.reset_local_leaf(rst, leaf, 'ck_frame_a', [10, 20], master, 'u_a')
    assert net != leaf and rst['depth'][net] == depth + 1
    assert rst['net_clocks'][net] == 'ck_frame_a'
    assert D.reset_local_leaf(rst, leaf, 'ck_frame_a', [10, 20], master, 'ld_a') == net
    assert rst['summary']['release_crossings'] == before + 1
    row = rst['summary']['leaf_crossings'][0]
    assert row['release_dst'] == row['release_src'] + 1
    text = '\n'.join(rst['verilog'])
    assert f'.ck(ck_frame_a), .rs({leaf}), .i({leaf}), .o({net})' in text
    assert sum(p['kind'] == 'reset_leaf_crossing' for p in rst['place']) == 1
    # A second actual root needs its own stage, with the same input age.
    other = D.reset_local_leaf(rst, leaf, 'ck_ep_a_K', [10, 20], master, 'ld_b')
    assert other != net and rst['depth'][other] == depth + 1


def test_reset_local_leaf_same_root_and_legacy_do_not_change_tree(monkeypatch):
    monkeypatch.delenv('OT_RESET_GATE', raising=False)
    rst = D.reset_tree(plan(BLOCKS), {'a': 'g0_0', 'b': 'g2_0'}, PTS, {})
    leaf = rst['block_leaf']['a']
    before = '\n'.join(rst['verilog'])
    assert D.reset_local_leaf(rst, leaf, rst['net_clocks'][leaf], [0, 0], D.RST_RLY['EW'], 'u_a') == leaf
    assert D.reset_local_leaf(rst, leaf, 'ck_other', [0, 0], D.RST_RLY['EW'], 'u_a', False) == leaf
    assert '\n'.join(rst['verilog']) == before
