"""Tests of the shared die-flow safety checks (tools/die_safety, ROOT14 10-20).  Pure Python, no OpenROAD."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
from die_safety import corners, gen_check, ir_drop, kit_pins, m8  # noqa: E402


def facts(**kw):
    f = dict(schema=gen_check.SCHEMA_FACTS, design='t', reach_um=405,
             regions={'ck_a': {'root': 'ck_a'}, 'ck_b': {'root': 'ck_b'}},
             crossings=[dict(id='x0', src_region='ck_a', dst_region='ck_b', landing='ld_x0', bits=64)],
             wires=[dict(id='x0', pts=[[0, 0], [400, 0], [400, 300], [700, 300]])])
    f.update(kw)
    return f


# ---------------------------------------------------------------- (1) GEN hard checks
def test_gen_pass():
    r = gen_check.check_facts(facts())
    assert r['verdict'] == 'PASS', r['fails']
    assert r['counts']['crossings'] == 1 and r['counts']['wires'] == 1 and r['counts']['hops'] == 3
    assert r['max_hop_um'] == 400.0


def test_gen_fail_crossing_without_landing():
    f = facts(crossings=[dict(id='x0', src_region='ck_a', dst_region='ck_b', landing=None)])
    r = gen_check.check_facts(f)
    assert r['verdict'] == 'FAIL' and r['counts']['no_landing'] == 1
    assert r['fails'][0].startswith('C1') and r['examples']['no_landing'][0]['id'] == 'x0'


def test_gen_fail_crossing_without_root():
    f = facts(regions={'ck_a': {'root': 'ck_a'}, 'ck_b': {'root': None}})
    r = gen_check.check_facts(f)
    assert r['verdict'] == 'FAIL' and r['counts']['no_root'] == 1 and r['regions_without_root'] == ['ck_b']
    f = facts(regions={'ck_a': {'root': 'ck_a'}})          # unknown region = no root
    assert gen_check.check_facts(f)['counts']['no_root'] == 1


def test_gen_fail_wire_without_relay_site_within_405():
    f = facts(wires=[dict(id='long', pts=[[0, 0], [300, 0], [300, 410]])])    # second hop 410 um
    r = gen_check.check_facts(f)
    assert r['verdict'] == 'FAIL' and r['counts']['hops_over'] == 1 and r['counts']['wires_over'] == 1
    assert r['examples']['hops_over'][0]['hops'] == [(1, 410.0)]
    assert gen_check.check_facts(f, reach=420)['verdict'] == 'PASS'


def test_gen_fail_channels_no_site_stretch():
    # hops 0->380->760 are each < 405, but the station at x=380 sits on a macro (no channel there): channels cover
    # x in [0, 20] and [700, 800] only -> a 680-um stretch with no relay/repeater site
    f = facts(wires=[dict(id='w', pts=[[0, 0], [380, 0], [760, 0]])], channels=[[0, -5, 20, 5], [700, -5, 800, 5]])
    r = gen_check.check_facts(f)
    assert r['counts']['hops_over'] == 0 and r['counts']['wires_no_site'] == 1 and r['verdict'] == 'FAIL'
    assert r['examples']['wires_no_site'][0]['unsited_um'] == pytest.approx(680, abs=6)
    f['channels'].append([370, -5, 390, 5])                                    # relay channel at the station
    assert gen_check.check_facts(f)['verdict'] == 'PASS'


def test_gen_empty_is_fail():
    r = gen_check.check_facts(dict(schema=gen_check.SCHEMA_FACTS))
    assert r['verdict'] == 'FAIL' and r['fails'][0].startswith('EMPTY')


def test_gen_adapters():
    lp = dict(summary=dict(pairs=dict(INTRA=900, LANDED=40, NEIGHBOUR=3, GAP=1, NO_ROOT=2, FWD=100)))
    s = gen_check.from_landed_pairs(lp)
    assert s == dict(source='qwen_landed_pairs', crossings=46, no_landing=4, no_root=2)
    hb = dict(buses_checked=1000, over_buses_by_class=dict(sync=7, fwd=3, reset=50))
    assert gen_check.from_hbm_reach(hb)['hops_over'] == 10
    rs = dict(buses=[dict(span_um=1000, stages=1), dict(span_um=1000, stages=2), dict(stages=0)])
    s = gen_check.from_relay_stages(rs, 405)
    assert s['wires'] == 2 and s['wires_over'] == 1 and s['max_hop_um'] == 500.0
    r = gen_check.check_facts(dict(summaries=[gen_check.from_landed_pairs(lp)]))
    assert r['verdict'] == 'FAIL' and r['counts']['no_landing'] == 4 and r['counts']['no_root'] == 2


def test_gen_cli_packet_and_exit(tmp_path):
    good, bad = tmp_path / 'good.json', tmp_path / 'bad.json'
    good.write_text(json.dumps(facts()))
    bad.write_text(json.dumps(facts(crossings=[dict(id='x', src_region='ck_a', dst_region='ck_b', landing=None)])))
    pk = tmp_path / 'packet.json'; pk.write_text(json.dumps(dict(gen='g5r3')))
    cli = [sys.executable, str(HERE / 'gen_check.py'), '--design', 'qwen_compute']
    r = subprocess.run(cli + ['--facts', str(good), '--packet', str(pk)], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.startswith('DIE_GEN_SAFETY PASS')
    d = json.loads(pk.read_text())
    assert d['gen'] == 'g5r3' and d['gen_safety']['verdict'] == 'PASS' and d['gen_safety']['counts']['crossings'] == 1
    r = subprocess.run(cli + ['--facts', str(bad), '--packet', str(pk)], capture_output=True, text=True)
    assert r.returncode == 1 and 'no_landing=1' in r.stdout and json.loads(pk.read_text())['gen_safety']['verdict'] == 'FAIL'
    r = subprocess.run(cli + ['--facts', str(bad), '--diagnostic', 'pathfinding'], capture_output=True, text=True)
    assert r.returncode == 0 and 'FAIL (DIAGNOSTIC: pathfinding)' in r.stdout


def test_s81_rvcase_facts_negative():
    """dv_rvcase's adapter: a link between two regions with no landing tile and a 500-um hop both FAIL"""
    sys.path.insert(0, str(TOOLS / 's81_dv'))
    import dv_rvcase as RV
    T = dict(masters={'A': dict(module='ma', clk='clk'), 'B': dict(module='mb', clk='clk')})
    insts = [('ma', 'u_a', {}, {}), ('mb', 'u_b', {}, {}), ('dsfd_dvland_x', 'ld_l1', {}, {})]
    ibits = {'u_a': {'clk': [('ck_ra', 0)]}, 'u_b': {'clk': [('ck_rb', 0)]}, 'ld_l1': {'ck': [('ck_rb', 0)]}}
    links = {'l0': dict(src='a', dst='b', sxy=(0, 0), dxy=(900, 0), pts=[(500, 0)], bits=8, cls='lane'),
             'l1': dict(src='a', dst='b', sxy=(0, 10), dxy=(800, 10), pts=[(400, 10)], bits=8, cls='lane')}
    f = RV.gen_safety_facts(insts, ibits, T, {'ma': 'A', 'mb': 'B'}, {'ck_ra', 'ck_rb'}, links, dict(links=[]),
                            {'ld_l1': (0, 0, 1, 1, 'FIRM')}, {}, {'a': {}, 'b': {}}, 405)
    r = gen_check.check_facts(f)
    assert r['counts']['crossings'] == 2 and r['counts']['no_landing'] == 1          # l0 has no ld_l0
    assert r['counts']['no_root'] == 0 and r['counts']['hops_over'] == 1             # l0 hop 0->500
    assert r['examples']['no_landing'][0]['id'] == 'l0' and r['verdict'] == 'FAIL'
    ibits['ld_l1'] = {'ck': [('n_local', 0)]}                                         # ring read on no region root
    r = gen_check.check_facts(RV.gen_safety_facts(insts, ibits, T, {'ma': 'A', 'mb': 'B'}, {'ck_ra', 'ck_rb'}, links,
                                                  dict(links=[]), {'ld_l1': (0, 0, 1, 1, 'FIRM')}, {}, {'a': {}, 'b': {}}, 405))
    assert r['counts']['no_root'] == 1


# ---------------------------------------------------------------- (2) stand-in fidelity
KIT = 'physical/ref_tile/k1'
IO = '''# generated
place_pin -pin_name {d[0]} -layer M3 -location {10.000 0.000} -pin_size {0.018 0.144} -force_to_die_boundary
place_pin -pin_name {d[1]} -layer M5 -location {20.000 0.000} -pin_size {0.024 0.192} -force_to_die_boundary
place_pin -layer M4 -pin_name q -location {100.000 30.000}
'''


def reader(files):
    return lambda p: files.get(p)


def test_kit_pins_from_io_tcl_face_order_layer():
    files = {f'{KIT}/spec.json': json.dumps(dict(top='t', outline=dict(w=100, h=60), io_tcl=f'{KIT}/io_pins.tcl')),
             f'{KIT}/io_pins.tcl': IO}
    p = kit_pins.load_plan(reader(files), KIT)
    assert p['source'].endswith('io_pins.tcl') and p['outline'] == (100.0, 60.0)
    assert p['pins']['d[0]'] == ('S', 10.0, 'M3') and p['pins']['d[1]'] == ('S', 20.0, 'M5')
    assert p['pins']['q'] == ('E', 30.0, 'M4')
    # stand-in slot twice as wide: same face, same fraction, same layer
    assert kit_pins.place(p, 'd[1]', 200, 60) == ('S', 40.0, 'M5')
    assert kit_pins.place(p, 'nope', 200, 60) is None
    lay, rect = kit_pins.pin_rect('S', 40.0, 200, 60, 'M5')
    assert lay == 'M5' and rect[1] == 0.0 and abs((rect[0] + rect[2]) / 2 - 40.0) < 1e-9


def test_kit_pins_from_spec_faces_not_centroid():
    """the S81 PHY-funnel shape: a stand-in whose neighbour sits NE would get every pin on one face corner by centroid
    projection; the kit says W face for 'a' (spread in order) and N for 'b' -- the stand-in must follow the kit"""
    spec = dict(top='t', outline=dict(w=100, h=100), clock_port='clk', pins={'W': ['a'], 'N': ['b', 'clk']})
    p = kit_pins.load_plan(reader({f'{KIT}/spec.json': json.dumps(spec)}), KIT,
                           {'a': (4, True), 'b': (2, True), 'clk': (1, False)})
    assert p['source'].endswith('spec.json:pins')
    ws = [p['pins'][f'a[{i}]'] for i in range(4)]
    assert all(f == 'W' and lay == 'M4' for f, _, lay in ws)
    ts = [t for _, t, _ in ws]
    assert ts == sorted(ts) and ts[0] > 4.0 and ts[-1] < 96.0            # spread over the whole face, in bit order
    assert p['pins']['clk'][0] == 'N' and p['pins']['b[0]'][2] == 'M3' and p['pins']['clk'][2] == 'M5'
    # the centroid projection (old behaviour) toward a NE neighbour would put a[*] on N/E -- not what the kit says
    sys.path.insert(0, str(TOOLS / 's81_dv'))
    import dv_rvcase as RV
    assert RV.project((0, 0, 100, 100), 400, 300)[0] in 'NE'
    assert kit_pins.place(p, 'a[0]', 100, 100)[0] == 'W'


def test_kit_pins_assigned_json_and_missing():
    doc = dict(positions=dict(d=dict(layer='M4', xy_um=[[0.096, 5.0], [0.096, 6.0]])))
    files = {f'{KIT}/spec.json': json.dumps(dict(top='t', outline=dict(w=21.6, h=75.6))), f'{KIT}/assigned_pins.json': json.dumps(doc)}
    p = kit_pins.load_plan(reader(files), KIT)
    assert p['pins']['d[1]'] == ('W', 6.0, 'M4')
    assert kit_pins.load_plan(reader({}), KIT) is None
    assert kit_pins.load_plan(reader({f'{KIT}/spec.json': json.dumps(dict(top='t'))}), KIT) is None   # no outline


# ---------------------------------------------------------------- (3) M8 model + (4) corners
def test_m8_model():
    assert m8.model('M2-M8')['repeater_rc_layer'] == 'M8' and m8.model('M4-M9')['sta_wire_rc_layer'] == 'M8'
    assert m8.model('M7') == dict(m8.model('M2-M7'))
    assert m8.model('M7')['repeater_rc_layer'] == 'M4' and m8.model('M7')['sta_wire_rc_layer'] == 'M6'
    assert m8.model('M8')['ir_drop_required'] and 'set_wire_rc -signal -layer M8' in m8.sta_rc_tcl('M8')


def test_repeater_step_m8_default(monkeypatch):
    monkeypatch.delenv('OT_DIE_SIGNAL_TOP_LAYER', raising=False)
    from die_repeaters import step
    assert 'rc_layer {M8}' in step.tcl_call('qwen_kv', '/w/r.json', signal_top_layer='M9')
    assert 'rc_layer {M4}' in step.tcl_call('qwen_kv', '/w/r.json')
    assert 'rc_layer {M6}' in step.tcl_call('qwen_kv', '/w/r.json', signal_top_layer='M9', rc_layer='M6')   # explicit wins
    monkeypatch.setenv('OT_DIE_SIGNAL_TOP_LAYER', 'M8')
    assert 'rc_layer {M8}' in step.tcl_call('hbm', '/w/r.json')


def test_corners_always_tt_ff():
    assert corners.required(['tt']) == ['tt', 'ff']
    assert corners.required([]) == ['tt', 'ff'] and corners.required(None) == ['tt', 'ff']
    assert corners.required(['ss', 'tt']) == ['tt', 'ff', 'ss']
    assert corners.added(['tt']) == ['ff']
    with pytest.raises(corners.CornerError):
        corners.required(['xx'])
    r = subprocess.run([sys.executable, str(HERE / 'corners.py'), 'tt'], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == 'tt ff' and 'added' in r.stderr


# ---------------------------------------------------------------- (3) IR drop
GRT_LOG = '''[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Overflow
---------------------------------------------------------------------------------------
M7              500000        100000           20.00%             0 /  0 /  0
M8              400000        {d}           {u}%             0 /  0 /  0
'''


def write_insts(p):
    rows = ['#die\t0\t0\t3000\t3000', 'u_hot\tblk\t0\t0\t1300\t1300', 'u_cold\tblk\t1500\t1500\t3000\t3000', 'u_phy\tphy_k\t0\t2000\t500\t3000']
    p.write_text('\n'.join(rows) + '\n')


def fake_solve(wd, mv_vdd, mv_vss):
    man = json.loads((wd.parent / 'manifest.json').read_text())
    c = next(c for c in man['windows'] if c['name'] == wd.name)
    x0, y0, x1, y1 = c['inner_um']; bx, by = c['solved_um'][:2]
    cx, cy = (x0 + x1) / 2 - bx, (y0 + y1) / 2 - by
    (wd / 'ir_VDD.rpt').write_text(f'Instance,Terminal,Layer,X,Y,Voltage\nL,VDD,M8,{cx},{cy},{0.7 - mv_vdd / 1000}\n')
    (wd / 'ir_VSS.rpt').write_text(f'Instance,Terminal,Layer,X,Y,Voltage\nL,VSS,M8,{cx},{cy},{mv_vss / 1000}\n')
    (wd / 'run.log').write_text('OT_PDN PASS\nOT_PG net=VDD PASS\nOT_PG net=VSS PASS\nOT_DONE\n')
    (wd / 'run.exit').write_text('0\n')


def test_ir_m8_usage_parse():
    assert ir_drop.m8_usage_from_log(GRT_LOG.format(d=124000, u='31.00')) == pytest.approx(0.31)
    assert ir_drop.m8_usage_from_log('nothing') is None


def test_ir_generate_record_pass_fail(tmp_path):
    ins = tmp_path / 'insts.tsv'; write_insts(ins)
    den = tmp_path / 'd.json'; den.write_text(json.dumps({'phy_*': 0, 'default': 1.2}))
    log = tmp_path / 'grt.log'; log.write_text(GRT_LOG.format(d=124000, u='31.00'))
    out = tmp_path / 'ir'
    assert ir_drop.main(['generate', '--insts', str(ins), '--out', str(out), '--grt-log', str(log), '--density', str(den),
                         '--windows', '2', '--design', 's81']) == 0
    man = json.loads((out / 'manifest.json').read_text())
    assert len(man['windows']) == 2 and man['m8']['signal_usage'] == pytest.approx(0.31) and man['m8']['verdict'] == 'PASS'
    hot = man['windows'][0]['inner_um']
    assert hot[0] < 1300 and hot[1] < 1300                                     # the hottest window is on u_hot
    for k in ('w0', 'w1'):
        t = (out / k / 'run.tcl').read_text()
        assert 'analyze_power_grid -net $net' in t and 'add_pdn_stripe -grid top -layer M8' in t and (out / k / 'window.def').exists()
    for k in ('w0', 'w1'):
        fake_solve(out / k, 12.0, 8.0)
    assert ir_drop.main(['record', '--out', str(out)]) == 0
    assert json.loads((out / 'ir_drop.json').read_text())['verdict'] == 'PASS'
    fake_solve(out / 'w1', 30.0, 9.0)                                           # 39 mV > 35 mV
    assert ir_drop.main(['record', '--out', str(out)]) == 1
    r = json.loads((out / 'ir_drop.json').read_text())
    assert r['verdict'] == 'FAIL' and r['owner_report'] and r['worst_mv'] == pytest.approx(39.0)


def test_ir_m8_oversubscribed_and_not_run(tmp_path, capsys):
    ins = tmp_path / 'insts.tsv'; write_insts(ins)
    out = tmp_path / 'ir'
    assert ir_drop.main(['generate', '--insts', str(ins), '--out', str(out), '--m8-usage', '0.95', '--windows', '1']) == 0
    assert ir_drop.main(['record', '--out', str(out)]) == 1                    # window never solved -> FAIL incomplete
    fake_solve(out / 'w0', 5.0, 5.0)
    assert ir_drop.main(['record', '--out', str(out)]) == 1                    # solved, but M8 0.95 + straps > 1
    r = json.loads((out / 'ir_drop.json').read_text())
    assert r['m8']['verdict'] == 'FAIL' and any('M8 over-subscribed' in p for p in r['problems'])
    assert 'OWNER_REPORT' in capsys.readouterr().out


def test_ir_dump_tcl():
    t = ir_drop.dump_tcl('/work/ir/insts.tsv')
    assert 'proc ot_ir_dump' in t and 'ot_ir_dump /work/ir/insts.tsv' in t and '#die' in t
