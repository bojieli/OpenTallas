"""Source-pin reset planner: obstacle reach/refusal and actual RTL fixed ages."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reset_forest_geometry import Geometry, GeometryError
from reset_forest_layer import build


def lef(path, name, w, h, pins):
    body = f'MACRO {name}\n SIZE {w} BY {h} ;\n'
    for p, (x, y) in pins.items():
        body += f' PIN {p}\n DIRECTION INPUT ;\n PORT\n LAYER M4 ;\n RECT {x-.01} {y-.01} {x+.01} {y+.01} ;\n END\n END {p}\n'
    path.joinpath(name + '.lef').write_text(body + f'END {name}\n')


@pytest.fixture
def case(tmp_path):
    lef(tmp_path, 'ck', 40, 40, {'por_stream': (40, 20)})
    lef(tmp_path, 'sink', 100, 100, {'rst_n': (0, 50), 'rst_lanes[0]': (0, 40), 'rst_lanes[1]': (0, 60)})
    for kind in ('sync', 'hop'):
        lef(tmp_path, 'hbfd_rrl_' + kind, 4, 4, {'clk': (2, 4), 'rst_n_in': (0, 2), 'rst_n': (4, 2)})
    pl = {'hb_ckgen': dict(m='ck', x=20, y=20, w=40, h=40, o='R0'),
          'a': dict(m='sink', x=500, y=100, w=100, h=100, o='R0'),
          'b': dict(m='sink', x=1300, y=600, w=100, h=100, o='MY')}
    c = dict(instances={n: dict(master=v['m']) for n, v in pl.items()}, edges=[], clock_resets=[
        dict(instance=n, port='rst_n', bits=1, kind='reset', domain='stream', source=['hb_ckgen', 'por_stream'])
        for n in ('a', 'b')])
    return c, dict(placement=pl, die_um=[1800, 1000]), tmp_path


def run(case, **kw):
    c, m, v = case
    return build(c, m, v, reach=200, zones='quadrant', **kw)


def assert_geometry(case, spec, report):
    _, m, v = case
    g = Geometry(m, v, v, 200)
    homes = list(report['homes'].values())
    for i, h in enumerate(homes):
        assert 0 <= h['x'] < h['x'] + h['w'] <= 1800
        assert 0 <= h['y'] < h['y'] + h['h'] <= 1000
        for other in list(m['placement'].values()) + homes[:i]:
            assert h['x'] + h['w'] <= other['x'] or other['x'] + other['w'] <= h['x'] or h['y'] + h['h'] <= other['y'] or other['y'] + other['h'] <= h['y']
    assert all(d['actual_leaf_ages'] == [d['age']] for d in report['domains'].values())
    assert report['max_actual_pin_hop_um'] <= 200
    assert report['geometry_gate'] == 'PASS'
    assert report['physical_signoff'] == 'OPEN'
    assert len(report['consumed_lef_sha256']) == 4


def test_real_pin_not_centre_and_orientation(case):
    _, m, v = case
    g = Geometry(m, v, v, 200)
    assert g.pin('a', 'rst_n') == (500, 150)
    assert g.pin('b', 'rst_n') == (1400, 650)
    spec, rep = run(case)
    assert_geometry(case, spec, rep)
    assert len(spec['reset_forest_ports']) == 2


def test_multibit_reset(case):
    c, _, _ = case
    c['clock_resets'][0].update(port='rst_lanes', bits=2)
    spec, rep = run(case)
    assert_geometry(case, spec, rep)
    assert [e['dst'] for e in spec['edges'] if e['dst'][0] == 'a'] == [['a', 'rst_lanes', 0, 1], ['a', 'rst_lanes', 1, 2]]


def test_obstacle_detour(case):
    c, m, _ = case
    m['placement']['wall'] = dict(m='wall', x=700, y=0, w=300, h=780, o='R0')
    c['instances']['wall'] = dict(master='wall')
    spec, rep = run(case)
    assert_geometry(case, spec, rep)
    assert any(h['y'] > 780 for h in rep['homes'].values())


def test_no_fixed_reach_across_wall(case):
    c, m, _ = case
    m['placement']['wall'] = dict(m='wall', x=700, y=0, w=300, h=1000, o='R0')
    c['instances']['wall'] = dict(master='wall')
    with pytest.raises(GeometryError, match='no reset route|no legal reset relay'):
        run(case)


@pytest.mark.parametrize('defect', ['missing_pin', 'missing_view', 'unplaced', 'buried', 'orientation'])
def test_bad_geometry_refused(case, defect):
    c, m, v = case
    if defect == 'missing_pin':
        c['clock_resets'][0]['port'] = 'absent'
    elif defect == 'missing_view':
        (v / 'sink.lef').unlink()
    elif defect == 'unplaced':
        del m['placement']['a']
    elif defect == 'buried':
        m['placement']['cover'] = dict(m='cover', x=450, y=120, w=100, h=100, o='R0')
    else:
        m['placement']['a']['o'] = 'R90'
    with pytest.raises(GeometryError):
        run(case)


def test_bridge_fixed_source_age(case):
    c, m, v = case
    lef(v, 'bridge', 100, 100, {'bridge_rst_n': (100, 50)})
    m['placement']['subr'] = dict(m='bridge', x=200, y=700, w=100, h=100, o='R0')
    c['instances']['subr'] = dict(master='bridge')
    c['edges'] = [dict(source=['subr', 'bridge_rst_n'], sink=[n, 'rst_n'], bits=1) for n in ('a', 'b')]
    spec, rep = run(case)
    assert len(spec['drop_edges']) == 2
    assert rep['domains']['bridge:subr']['age'] >= 1


def rtl_bench(spec, report, tmp_path):
    """Instantiate the emitted actual sync/hop RTL topology; assert every sink edge."""
    names = {t['name'] for t in spec['instances']}
    inputs, sinks = {}, []
    for e in spec['edges']:
        src, dst = e['src'], e['dst']
        signal = 'por' if src[0] == 'hb_ckgen' else src[0]
        if dst[0] in names:
            inputs[dst[0]] = signal
        else:
            sinks.append(signal)
    age = report['domains']['stream:por_stream']['age']
    body = 'module tb; reg clk=0; always #5 clk=~clk; reg por=0; integer k;\n'
    for t in spec['instances']:
        n = t['name']
        body += f'wire {n}; {t["master"]} u_{n}(.clk(clk), .rst_n_in({inputs[n]}), .rst_n({n}));\n'
    body += 'initial begin #12; por=1;\n'
    body += f'for(k=1;k<={age+3};k=k+1) begin @(posedge clk); #1;\n'
    for s in sinks:
        body += f'if ({s} !== (k >= {age})) $fatal(1,"wrong compiler reset age at edge %0d", k);\n'
    body += 'end\n #2; por=0; #1;\n'
    for s in sinks:
        body += f'if ({s} !== 0) $fatal(1,"async assertion failed");\n'
    body += '$finish; end endmodule\n'
    tb = tmp_path / 'tb.sv'
    tb.write_text(body)
    root = Path(__file__).resolve().parents[2]
    exe = tmp_path / 'sim'
    subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(exe), str(tb),
                    str(root / 'rtl/hbm_accel/die_glue/hbfd_rrl.sv'), str(root / 'rtl/lib/ot_rst_relay.sv')], check=True)
    return subprocess.run(['vvp', str(exe)], capture_output=True, text=True)


def test_actual_rtl_release_age_and_skew_mutant(case, tmp_path):
    if not shutil.which('iverilog'):
        pytest.skip('requires Icarus for actual RTL bench')
    spec, report = run(case)
    result = rtl_bench(spec, report, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    spec, report = run(case, mut_skew=True)
    assert report['geometry_gate'] == 'FAIL_MUTANT_RELEASE_AGE'
    result = rtl_bench(spec, report, tmp_path)
    assert result.returncode != 0 and 'wrong compiler reset age' in result.stdout


def test_placement_manifest_lef_hash_binding(case):
    _, m, v = case
    m['consumed_view_sha256'] = {'sink.lef': '0' * 64}
    with pytest.raises(GeometryError, match='LEF bytes differ'):
        run(case)


def test_cli_diag_still_refuses_layer(case, tmp_path):
    c, m, v = case
    c['clock_resets'][0]['port'] = 'absent'
    cp, mp, out, report = [tmp_path / n for n in ('contract.json', 'manifest.json', 'layer.json', 'report.json')]
    cp.write_text(json.dumps(c))
    mp.write_text(json.dumps(m))
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('reset_forest_layer.py')),
                             '--contract', str(cp), '--manifest', str(mp), '--views', str(v),
                             '--out', str(out), '--report', str(report), '--diag'], capture_output=True, text=True)
    assert result.returncode == 3
    assert not out.exists()
    assert json.loads(report.read_text())['geometry_gate'] == 'FAIL'


def test_full_rectangles_fit_narrow_channel(case):
    _, m, v = case
    # A twelve-um gap contains a legal four-um relay. Full-cell obstacle
    # rasterization plus a halo incorrectly erased this channel.
    m['placement'] = {'left': dict(m='left', x=0, y=0, w=139, h=1000, o='R0'),
                      'right': dict(m='right', x=151, y=0, w=1649, h=1000, o='R0')}
    g = Geometry(m, v, v, 200)
    a = g.reserve('hop', (145, 55), max_distance=0)
    b = g.reserve('hop', (145, 65), max_distance=0)
    assert a['home'] == (143, 53)
    assert b['home'] == (143, 63)


def test_real_kit_sized_relay_outlines(case):
    _, _, v = case
    for kind in ('sync', 'hop'):
        lef(v, 'hbfd_rrl_' + kind, 32.4, 32.4, {'clk': (0, 8), 'rst_n_in': (0, 24), 'rst_n': (32.4, 16)})
    spec, rep = run(case)
    assert_geometry(case, spec, rep)
