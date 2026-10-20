"""L2H-GEN2D-RST 10-19: compact carrier tiles + dedicated HBM reset carrier built from a corridor topology."""
import collections
import subprocess
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reset_forest_geometry import GeometryError
from reset_forest_layer import build
from test_reset_forest_layer import lef

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def case(tmp_path):
    subprocess.run([sys.executable, str(ROOT / 'results/arch/hbm_die_d4g/rstcarrier/gen_lef.py'), str(tmp_path)], check=True,
                   capture_output=True)
    lef(tmp_path, 'ck', 40, 40, {'por_hbm': (40, 20), 'por_stream': (40, 30)})
    lef(tmp_path, 'sink', 100, 100, {'rst_n': (0, 50), 'rst_lanes[0]': (0, 40), 'rst_lanes[1]': (0, 60)})
    # a wall between the source and the far sink: the carrier corridor goes around it
    pl = {'hb_ckgen': dict(m='ck', x=20, y=20, w=40, h=40, o='R0'),
          'a': dict(m='sink', x=300, y=100, w=100, h=100, o='R0'),
          'b': dict(m='sink', x=1300, y=600, w=100, h=100, o='MY'),
          's': dict(m='sink', x=900, y=100, w=100, h=100, o='R0'),
          'wall': dict(m='sink', x=600, y=0, w=100, h=100, o='R0')}
    rs = [dict(instance='a', port='rst_n', bits=1, kind='reset', domain='hbm', source=['hb_ckgen', 'por_hbm']),
          dict(instance='b', port='rst_lanes', bits=2, kind='reset', domain='hbm', source=['hb_ckgen', 'por_hbm']),
          dict(instance='s', port='rst_n', bits=1, kind='reset', domain='stream', source=['hb_ckgen', 'por_stream'])]
    c = dict(instances={n: dict(master=v['m']) for n, v in pl.items()}, edges=[], clock_resets=rs)
    # corridor: root at the source, trunk east then north to b; a branch lands a
    st = [(0, -1, (64.8, 40.0), []), (1, 0, (280.0, 40.0), [0]), (2, 1, (580.0, 140.0), []), (3, 2, (880.0, 300.0), []),
          (4, 3, (1180.0, 400.0), []), (5, 4, (1280.0, 600.0), [1, 2])]
    kids = collections.defaultdict(list)
    for i, p, _, _ in st:
        if p >= 0:
            kids[p].append(i)
    topo = [dict(id=i, parent_id=p, center_um=list(xy), children=kids[i], sink_indices=s, path_um=0.0) for i, p, xy, s in st]
    sinks = [dict(instance='a', port='rst_n', bit=0), dict(instance='b', port='rst_lanes', bit=0),
             dict(instance='b', port='rst_lanes', bit=1)]
    carrier = dict(domain='hbm', por='por_hbm', topology=topo, sinks=sinks, sha256='t')
    return c, dict(placement=pl, die_um=[1800, 1000]), tmp_path, carrier


def run(case, **kw):
    c, m, v, car = case
    return build(c, m, v, reach=405, zones='quadrant', compact=True, carrier=car, **kw)


def ages(spec, report):
    """simulate release ages through the emitted tiles: csync 3, chop 1, cpad<N> N"""
    st = {t['name']: (3 if t['master'] == 'hbfd_rrl_csync' else 1 if t['master'] == 'hbfd_rrl_chop'
                      else int(t['master'][len('hbfd_rrl_cpad'):])) for t in spec['instances']}
    drv = {tuple(e['dst'][:2]): e['src'] for e in spec['edges']}
    def age(n):
        s = drv[(n, 'rst_n_in')]
        return st[n] + (0 if s[0] == 'hb_ckgen' else age(s[0]))
    return {tuple(e['dst']): age(e['src'][0]) for e in spec['edges'] if e['dst'][0] not in st}


def test_carrier_builds_equal_age_two_stage_landings(case):
    spec, rep = run(case)
    assert rep['geometry_gate'] == 'PASS' and rep['max_actual_pin_hop_um'] <= 405
    car = rep['carrier']
    assert car['stations'] == 6 and car['landings'] == 2
    masters = collections.Counter(t['master'] for t in spec['instances'])
    assert masters['hbfd_rrl_csync'] == 3   # carrier ingress + planner stream ingress + stream regional root
    assert all(t['source'] == 'rtl/hbm_accel/die_glue/hbfd_rrl_c.sv' for t in spec['instances'])
    hbm = {k: v for k, v in ages(spec, rep).items() if k[0] in ('a', 'b')}
    assert set(hbm.values()) == {rep['domains']['hbm:por_hbm']['age']}
    lands = [t for t in spec['instances'] if 'face landing' in t['note']]
    assert all(int(t['master'][len('hbfd_rrl_cpad'):]) >= 2 for t in lands)
    # stream leaf lands in two stages too (compact mode)
    st = [t for t in spec['instances'] if t['name'].startswith('rrf_stream') and 'leaf' in t['note']]
    assert st and all(int(t['master'][len('hbfd_rrl_cpad'):]) >= 2 for t in st)
    # homes disjoint from placed blocks and each other
    homes = list(rep['homes'].values())
    _, m, _, _ = case
    for i, h in enumerate(homes):
        for o in list(m['placement'].values()) + homes[:i]:
            assert h['x'] + h['w'] <= o['x'] or o['x'] + o['w'] <= h['x'] or h['y'] + h['h'] <= o['y'] or o['y'] + o['h'] <= h['y']


def test_carrier_refuses_missing_sink(case):
    c, m, v, car = case
    car['sinks'] = car['sinks'][:2]
    car['topology'][5]['sink_indices'] = [1]
    with pytest.raises(GeometryError, match='covers 2 of 3'):
        build(c, m, v, reach=405, zones='quadrant', compact=True, carrier=car)


def test_carrier_refuses_overreach_station(case):
    c, m, v, car = case
    car['topology'][4]['center_um'] = [1100.0, 900.0]   # 1100 -> 880,300: > 405 um from its parent
    with pytest.raises(GeometryError, match='no legal hop home'):
        build(c, m, v, reach=405, zones='quadrant', compact=True, carrier=car)


def test_carrier_needs_compact(case):
    c, m, v, car = case
    with pytest.raises(GeometryError, match='needs --compact'):
        build(c, m, v, reach=405, zones='quadrant', carrier=car)


def test_compact_planner_only(case):
    c, m, v, _ = case
    spec, rep = build(c, m, v, reach=405, zones='quadrant', compact=True)
    assert rep['geometry_gate'] == 'PASS'
    assert all(t['master'].startswith('hbfd_rrl_c') for t in spec['instances'])
