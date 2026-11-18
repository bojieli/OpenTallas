"""Matched-leg star trunk of a pad clock (FABLE-FIX-S81-SERDES 11-18): planner geometry, plan key, generator hook."""
import copy
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pad_clock as PC          # noqa: E402
import rck_star as RS           # noqa: E402
from test_pad_clock_entries import plan      # noqa: E402


def geom(pad=(1448.0, 1063.8)):
    """t13-like: full rows below y 920, a row-less PHY block above it, one macro hole, a dense island and a sparse face strip."""
    rows = []
    y = 4.32
    while y < 920.0:
        if 430.0 <= y < 570.0:
            rows += [(4.32, y, 1290.0, y + 0.27), (1580.0, y, 2881.44, y + 0.27)]
        else:
            rows.append((4.32, y, 2881.44, y + 0.27))
        y += 0.27
    sinks = []
    for i in range(60):                      # island: columns of flops that share one x
        for j in range(40):
            sinks.append((1000.0 + 5.0 * i, 150.0 + 6.0 * j + (300.0 if j >= 20 else 0.0), f'ff_{i}_{j}', 'CLK', 'DFF', False))
    for i in range(545):                     # face strip under the PHY
        sinks.append((330.0 + 4.07 * i, 915.0, f'face_{i}', 'CLK', 'DFF', False))
    sinks.append((332.7, 1055.0, 'u_prx', 'pma_rck', 'ot_rxm', True))
    return dict(rows=rows, sinks=sinks, port=('io_pma_rck', pad[0], pad[1]))


def hops(e):
    pts = list(e['stations']) + [e['xy']]
    return [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]


@pytest.mark.parametrize('pad', [(1448.0, 1063.8), (332.7, 1063.8)])
def test_every_leg_has_the_same_stages_and_length(pad):
    g = geom(pad)
    entries, rep = RS.plan(g)
    rows = RS.Rows(g['rows'])
    assert rep['entries'] == len(entries) > 20 and sum(e['n'] for e in entries) == 60 * 40 + 545
    assert max(e['n'] for e in entries) <= 200
    assert {len(e['stations']) for e in entries} == {rep['hops']}
    for e in entries:
        assert all(rows.ok(*p) for p in e['stations']) and rows.ok(*e['xy'])
        if rep['nudged_stations'] == 0:
            assert max(hops(e)) <= rep['hop_um'] + 1e-6 and abs(sum(hops(e)) - rep['leg_um']) < 1e-6
    assert rep['nudged_stations'] <= 0.02 * rep['stations']
    # the regions tile the plane: every sink is inside exactly one region
    for x, y, *_ in g['sinks'][:-1]:
        assert sum(r[0] < x <= r[2] and r[1] < y <= r[3] for e in entries for r in [e['region']]) == 1
    # the macro pin is declared on exactly one entry
    assert sum(len(e['macros']) for e in entries) == 1


def test_far_pad_gets_one_common_feeder_and_a_central_hub():
    _e, c = RS.plan(geom((1448.0, 1063.8)))
    _e, w = RS.plan(geom((332.7, 1063.8)))
    assert w['feeder'] >= 8 and w['leg_um'] <= c['leg_um'] + 2 * w['hop_um']
    assert abs(w['hub'][0] - 1448.0) < 300.0
    f = w['feeder_um']
    assert max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(f, f[1:])) <= w['hop_um'] + 8.0


def test_cut_sits_between_columns_and_counts_are_near_equal():
    pts = [(float(i // 50), float(i % 50), f'f{i}', 'CLK') for i in range(1000)]      # 20 columns of 50 flops
    T = RS.tiles(pts, 200, 1e9, (-1, -1, 100, 100))
    assert sorted(len(p) for _r, p in T) == [200] * 5
    assert RS.tiles(pts[:1], 200, 100.0, (-1, -1, 100, 100))[0][1] == pts[:1]


def test_emit_is_the_hook_data(tmp_path):
    g = geom((332.7, 1063.8))
    entries, rep = RS.plan(g)
    out = tmp_path / 'e.tcl'
    RS.emit(entries, rep, out)
    t = out.read_text()
    assert 'set ::rks_cell BUFx24_ASAP7_75t_R' in t and 'set ::rks_feeder {{' in t
    assert len(re.findall(r'^  \{rck_r\d+ \{\{', t, re.M)) == len(entries)
    assign = [int(v) for v in re.search(r'set ::rks_assign \{([^}]*)\}', t).group(1).split()]
    assert len(assign) == len(g['sinks']) and set(assign) == set(range(len(entries)))
    # every sink goes to the entry whose region holds it; the macro pin to one entry
    for (x, y, *_), k in list(zip(g['sinks'], assign))[:-1]:
        r = entries[k]['region']
        assert r[0] < x <= r[2] and r[1] < y <= r[3]


def splan(**row):
    p = plan()
    p.types['mid']['clock']['pad_clock']['pins'][0]['star'] = {'evidence': 'test', **row}
    return p


def test_plan_key_exports_and_hook():
    p = plan()
    assert PC.star(p, 'mid') == [] and PC.star_exports(p, 'mid') == []
    p = splan(max_sinks=160)
    (n, r), = PC.star(p, 'mid')
    assert n == 'pma_rck' and r['max_sinks'] == 160 and r['hop_um'] == 92.0 and r['cell'] == 'BUFx24_ASAP7_75t_R'
    ex = PC.star_exports(p, 'mid')
    assert 'export OT_RCK_STAR_PORT = pma_rck' in ex and 'export OT_RCK_STAR_MAX_SINKS = 160' in ex
    assert all((HERE / f).is_file() for f in PC.STAR_FILES) and 'rck_star.tcl' in PC.STAR_HOOK and len(PC.STAR_FILES) == 2


@pytest.mark.parametrize('row', [dict(hop_um=140.0), dict(max_sinks=4), dict(max_sinks=1.5), dict(cell='a b'), dict(extra=1),
                                 dict(evidence=' ')])
def test_bad_star_row_fails_closed(row):
    with pytest.raises(ValueError):
        PC.star(splan(**row), 'mid')


def test_star_and_plan_entries_exclude_each_other():
    from test_pad_clock_entries import eplan
    p = eplan()
    p.types['mid']['clock']['pad_clock']['pins'][0]['star'] = {'evidence': 'test'}
    with pytest.raises(ValueError):
        PC.star(p, 'mid')


def test_hooks():
    body = (HERE / 'pad_clock_entry.tcl').read_text()
    assert 'string match pce_* [[$it getInst] getName]' in body
    hook = (HERE / 'rck_star.tcl').read_text()
    assert 'rck_star.py' in hook and 'rks_feed_' in hook and '0 left on the pad net' in hook and 'pad_clock_entry' not in hook
