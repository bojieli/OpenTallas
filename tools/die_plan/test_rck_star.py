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


def tplan(**over):
    p = plan()
    pin = p.types['mid']['clock']['pad_clock']['pins'][0]
    x, y = pin['xy_um']
    row = {'from_xy_um': [x + 300.0, y], 'stations_um': [], 'layer': pin['layer'], 'host': 'die', 'evidence': 'test'}
    row.update(over)
    pin['die_trunk'] = row
    return p, pin


def test_die_trunk_row_validates_and_changes_no_kit_data():
    p = plan()
    assert PC.die_trunks(p, 'mid') == []
    p, pin = tplan()
    (n, r), = PC.die_trunks(p, 'mid')
    assert n == pin['name'] and r['host'] == 'die' and PC.star(p, 'mid') == [] and PC.entries_tcl(p, 'mid') == ''
    x, y = pin['xy_um']
    p, pin = tplan(from_xy_um=[x + 390.0, y], host='type')
    assert PC.die_trunks(p, 'mid')[0][1]['host'] == 'type'


@pytest.mark.parametrize('over', [dict(host='pad'), dict(layer='M99'), dict(evidence=''), dict(cell='BUFx24_ASAP7_75t_R'),
                                  dict(stations_um=[[1.0, 1.0]]), dict(extra=1), dict(from_xy_um=[1e9, 0.0])])
def test_bad_die_trunk_fails_closed(over):
    p, pin = tplan(**over)
    with pytest.raises(ValueError):
        PC.die_trunks(p, 'mid')


def test_die_trunk_hop_limit():
    p, pin = tplan()
    x, y = pin['xy_um']
    w = p.types['mid']['outline_um'][0]
    far = x + 410.0 if x + 410.0 <= w else x - 410.0
    if 0.0 <= far <= w:
        pin['die_trunk']['from_xy_um'] = [far, y]
        with pytest.raises(ValueError):
            PC.die_trunks(p, 'mid')


def test_host_type_trunk_moves_the_kit_port_and_emits_the_hook():
    p, pin = tplan()
    x, y = pin['xy_um']
    assert PC.trunk_tcl(p, 'mid') == '' and PC.port_xy(pin) == [x, y]            # host die: nothing in the kit
    w = p.types['mid']['outline_um'][0]
    step = 200.0 if x + 400.0 <= w else -200.0
    p, pin = tplan(host='type', from_xy_um=[x + 2 * step, y], stations_um=[[x + step, y]], cell='BUFx24_ASAP7_75t_R')
    assert PC.port_xy(pin) == [x + 2 * step, y]
    tcl = PC.trunk_tcl(p, 'mid')
    assert tcl.count('set ::pct_trunks {') == 1 and 'source /work/pad_clock_trunk.tcl' in tcl
    assert '{%s BUFx24_ASAP7_75t_R {{' % pin['name'] in tcl
    hook = (HERE / PC.TRUNK_FILE).read_text()
    assert 'pct_report' in hook and 'no placement row within' in hook and 'OT_PAD_CLOCK_TRUNK' in hook
    assert 'pct_report' in (HERE / 'cts_post.tcl').read_text()
    # a station-less host-type row moves the port but builds nothing
    p, pin = tplan(host='type')
    assert PC.trunk_tcl(p, 'mid') == '' and PC.port_xy(pin) == pin['die_trunk']['from_xy_um']


def test_host_type_kit_port_is_one_position_for_io_sidecar_and_pin_records(tmp_path):
    """FABLE-FIX-S81-SERDES-O 11-18 audit: every reader of the physical pad-clock port (io.tcl place_pin, the pad_clock.json
    sidecar that kit_contract clock_pin_geometry compares io.tcl against, gen_phys.plan_pin_records -> freeze.json / die
    abstracts) sees from_xy_um for a die_trunk host "type" row; the plan trunk end stays in the sidecar as plan_xy_um."""
    import json
    import gen_phys as GP
    import landing_contract as LC
    p, pin = tplan()
    x, y = pin['xy_um']
    w = p.types['mid']['outline_um'][0]
    step = 200.0 if x + 400.0 <= w else -200.0
    fx, fy = LC.on_track(p, pin['layer'], x + 2 * step, y)
    p, pin = tplan(host='type', from_xy_um=[fx, fy], stations_um=[[x + step, y]], cell='BUFx24_ASAP7_75t_R')
    name = pin['name']
    io = PC.io_tcl(p, 'mid')
    m = re.search(r'-pin_name \{%s\[0\]\} -layer \S+ -location \{(\S+) (\S+)\}' % name, io)
    assert m and abs(float(m.group(1)) - fx) < 1e-4 and abs(float(m.group(2)) - fy) < 1e-4
    PC.write_contract(p, 'mid', tmp_path)
    side = {q['name']: q for q in json.loads((tmp_path / 'pad_clock.json').read_text())['pins']}
    assert side[name]['xy_um'] == [fx, fy] and side[name]['plan_xy_um'] == [x, y]
    recs = {r['name']: r for r in GP.plan_pin_records(p, 'mid', GP.type_pins(p, 'mid'))}
    r = recs[name + '[0]']
    assert abs(float(r['x']) - fx) < 1e-4 and abs(float(r['y']) - fy) < 1e-4
    # host die: all three keep the declared xy_um and the sidecar has no plan_xy_um
    p, pin = tplan()
    PC.write_contract(p, 'mid', tmp_path)
    side = {q['name']: q for q in json.loads((tmp_path / 'pad_clock.json').read_text())['pins']}
    assert side[name]['xy_um'] == [x, y] and 'plan_xy_um' not in side[name]
    r = {r['name']: r for r in GP.plan_pin_records(p, 'mid', GP.type_pins(p, 'mid'))}[name + '[0]']
    assert abs(float(r['x']) - x) < 1e-4 and abs(float(r['y']) - y) < 1e-4
