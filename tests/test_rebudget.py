"""tools/budgets/rebudget.py: link model, need parsing, split rule and the closed-neighbour protection (owner rule 4)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'budgets'))
import rebudget as RB  # noqa: E402

DUMP = '\n'.join([
    '# ot_rb_dump max 2 instances, UI per ps 1.0',
    #  P mm inst bus dir start end sclk eclk T lat_s lat_r arr_out arr_in req margin slack
    'P\tmax\tu2\ti\tinput\tu1/od[3]\tu2/i[3]\tc\tc\t833.333\t100.0\t300.0\t309.9\t409.9\t958.0\t-22.4\t548.1',
    'E\tmax\tu3\tq\toutput\tu3/q[0]\tr1/d[0]\t35.0',
])
DUMP_FF = '\n'.join([
    'P\tmin\tu2\ti\tinput\tu1/od[3]\tu2/i[3]\tc\tc\t833.333\t100.0\t300.0\t289.2\t299.2\t267.8\t56.9\t31.4',
    'L\tu3/ck\t500.0\tclk_stream',
])


def test_parse_dump_and_link_components():
    P, E, L = RB.parse_dump(DUMP + '\n' + DUMP_FF)
    assert len(P) == 2 and len(E) == 1 and L == {'u3': 500.0}
    ctx = dict(inst_master={'u1': 'A', 'u2': 'B', 'u3': 'X', 'r1': 'rly'}, ins={'u1': [0, 40.0, 50.0], 'u2': [0, 80.0, 100.0]},
               lat=dict(tt={'r1': 450.0}, ff={'r1': 450.0}))
    cfg = dict(unc=dict(tt=85.0, ff=50.0))
    links = {(l['snd_inst'], l['rcv_inst']): l for l in RB.build_links('t', cfg, P, E, {'u3': 500.0}, ctx)}
    l = links[('u1', 'u2')]
    tt = l['tt']
    # targets: u1 100 + 50 = 150, u2 300 + 100 = 400 -> dskew -250; W = 100
    assert tt['W'] == 100.0 and tt['dskew'] == -250.0
    assert tt['C'] == round(833.333 - RB.U_S - 100.0 + 250.0, 1)
    assert tt['S_kit'] == round(309.9 - 100.0 - 50.0, 1) and tt['R_kit'] == round(-22.4 + 100.0, 1)
    ff = l['ff']
    # hold credit: W_min 10 + (target_s - target_r) (140 - 380 = -240) - U_H
    assert ff['H'] == round(10.0 - 240.0 - RB.U_H, 1)
    # the wire-only bus: latencies from the L line / plan, no timed path
    w = links[('u3', 'r1')]
    assert w['src'].startswith('die GRT wire') and w['tt']['W'] == 35.0 and w['tt']['dskew'] == 50.0


def test_needs_from_ports_per_domain():
    tt = {'i[0]': ('in', 700.0, None), 'i[1]': ('in', 650.0, None), 'o[0]': ('out', 600.0, None), 'x[0]': ('in', None, None)}
    ff = {'i[0]': ('in', None, -20.0), 'i[1]': ('in', None, 5.0), 'o[0]': ('out', None, 40.0)}
    refs = {'core_clk': dict(L=200.0, T=833.333)}
    dom = {'i': 'core_clk', 'o': 'core_clk', 'x': None}
    b = RB.needs_from(tt, ff, refs, dom)
    assert b['i']['R'] == round(833.333 - 650.0, 1) and b['i']['h'] == 20.0
    assert b['o']['S'] == round(833.333 - 600.0, 1) and b['o']['smin'] == 40.0
    assert 'R' not in b['x']


def test_split_never_exceeds_link():
    sb, rb = RB.split_setup(300.0, 100.0, 600.0)
    assert abs(sb + rb - 600.0) < 1e-9 and sb >= 300.0 and rb >= 100.0
    sb, rb = RB.split_setup(500.0, 300.0, 600.0)       # short link: both short, proportionally
    assert abs(sb + rb - 600.0) < 1e-9 and sb < 500.0 and rb < 300.0


def _derive(tmp_path, monkeypatch, other_view, need_S, C=600.0, R_kit=200.0):
    out = tmp_path / 'rb'
    (out / 'needs').mkdir(parents=True)
    monkeypatch.setattr(RB, 'OUT', out)
    monkeypatch.setattr(RB, 'ROOT', tmp_path)
    monkeypatch.setattr(RB, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(RB, 'load_jobs', lambda: {})
    monkeypatch.setattr(RB, 'slab_map', lambda: ({}, None))
    monkeypatch.setattr(RB, 'DIES', {'d': {}})
    (out / 'masters_d.json').write_text(json.dumps({'A': 'interim', 'B': other_view}))
    link = dict(snd_inst='a0', snd_master='A', snd_bus='o', rcv_inst='b0', rcv_master='B', rcv_bus='i', src='die GRT STA path',
                tt=dict(T=833.333, C=C, S_kit=150.0, R_kit=R_kit), ff=dict(H=-40.0, smin_kit=30.0, h_kit=-10.0))
    (out / 'links_d.json').write_text(json.dumps(dict(die='d', links=[link])))
    nd = dict(job='j1', block='A', die='d', die_master='A', tile=None, internal_ok=True, r2r=dict(tt=10, ff=5),
              ref=dict(tt={'core_clk': dict(L=200.0, T=833.333)}),
              ports={'o': dict(dir='out', bits=8, clock='core_clk', T=833.333, S=need_S, smin=60.0)})
    (out / 'needs' / 'j1.json').write_text(json.dumps(nd))
    RB.cmd_derive(SimpleNamespace(rb=1, no_publish=True))
    return json.loads((out / 'budget_rb1' / 'summary.json').read_text())['jobs']['j1']


def test_derive_rederives_with_real_neighbour(tmp_path, monkeypatch):
    j = _derive(tmp_path, monkeypatch, 'closed', need_S=300.0)
    row = j['links'][0]
    assert row['setup'] == 're-derived' and row['budget'] == round(600.0 * 300 / 500, 1) and row['slack_pred'] > 0
    assert row['hold'] == 're-derived' and j['ports_rebudgeted'] == 1 and j['sdc']
    sdc = (tmp_path / j['sdc']).read_text()
    assert 'ot_rb_v_core_clk' in sdc and 'set_output_delay -max' in sdc and 'proc ot_rb_vclocks' in sdc


def test_derive_keeps_old_budget_next_to_closed_short_link(tmp_path, monkeypatch):
    # S 500 + R 200 > C 600: the receiver is CLOSED -> rule 4, the link keeps its old budget
    j = _derive(tmp_path, monkeypatch, 'closed', need_S=500.0)
    assert j['links'][0]['setup'].startswith('kept old') and j['ports_rebudgeted'] == 0 and j['sdc'] is None


def test_derive_no_real_model_keeps_old(tmp_path, monkeypatch):
    j = _derive(tmp_path, monkeypatch, 'interim', need_S=300.0)
    assert 'no real model' in j['links'][0]['setup'] and j['sdc'] is None


def test_measure_sdc_has_procs_markers():
    t = (ROOT / 'physical/common_flow/rebudget_measure.sdc').read_text()
    assert '# --- OT_RB_PROCS begin' in t and '# --- OT_RB_PROCS end ---' in t
    assert 'OT_RB_PORT' in t and 'OT_RB_DOMAIN' in t
    assert 'REBUDGET hook' in (ROOT / 'physical/common_flow/link_budget_consistent.sdc').read_text()


FWD_TT = 'P\tmax\thq\tod\toutput\thq/od[5]\tst1/di0[5]\tclk_stream\tot_fw_0\t833.333\t500.0\t760.0\t760.0\t990.0\t1100.0\t30.0\t50.0\t-\t-\t140.0\thq/fo[0]'
# the hold check is reported launched one period later (data arrival + T): edge T/2 vs launch T
FWD_FF = 'P\tmin\thq\tod\toutput\thq/od[5]\tst1/di0[5]\tclk_stream\tot_fw_0\t833.333\t500.0\t720.0\t700.0\t1733.3\t1196.7\t10.0\t536.6\t-\t-\t120.0\thq/fo[0]'


def test_forwarded_clock_link_and_needs():
    P, E, L = RB.parse_dump(FWD_TT + '\n' + FWD_FF)
    assert P[0]['fo_pin'] == 'hq/fo[0]' and P[0]['cap_time'] is None and P[0]['fo_arc'] == 140.0
    ctx = dict(inst_master={'hq': 'H', 'st1': 'STN'}, ins={}, lat={})
    l_ = RB.build_links('t', dict(unc=dict(tt=85.0, ff=50.0)), P, E, L, ctx)[0]
    assert l_['src'].endswith('(forwarded clock)') and l_['fwd']['fo_bus'] == 'fo'
    tt, ff = l_['tt'], l_['ff']
    # sender need in the forwarded frame: od pin (760 - 500 = 260) - fo arc 140 = 120; C = slack + S_fw + R (same U)
    assert tt['S_kit'] == 120.0 and tt['C'] == round(50.0 + 120.0 + 30.0, 1)
    assert abs(tt['T_cap'] - 416.6665) < 0.01 and tt['cap_tr'] == 'fall'
    assert abs(ff['T_hold'] + 416.6665) < 0.01 and ff['W'] == round(1733.3 - 700.0 - 833.333, 1)
    # hold: link margin with the kit sender = slack 536.6 (session U = U_H), H rebuilds it from smin_fw / h
    assert ff['smin_kit'] == round(700.0 - 500.0 - 120.0, 1) and ff['H'] == round(536.6 - ff['smin_kit'] + 10.0, 1)
    log = 'OT_RB_FWDCLK fo[0] w_cks 17.4 26.9\nOT_RB_REF w_cks 124.3 T 833.331 in 1 out 2\n'
    _, refs, _ = RB.parse_ports(log)
    assert refs['_fwd']['fo'] == dict(clock='w_cks', A=17.4, A_min=26.9)


def test_derive_forwarded_output_sdc(tmp_path, monkeypatch):
    out = tmp_path / 'rb'
    (out / 'needs').mkdir(parents=True)
    monkeypatch.setattr(RB, 'OUT', out)
    monkeypatch.setattr(RB, 'ROOT', tmp_path)
    monkeypatch.setattr(RB, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(RB, 'load_jobs', lambda: {})
    monkeypatch.setattr(RB, 'slab_map', lambda: ({}, None))
    monkeypatch.setattr(RB, 'DIES', {'d': {}})
    (out / 'masters_d.json').write_text(json.dumps({'H': 'interim', 'STN': 'closed'}))
    link = dict(snd_inst='hq', snd_master='H', snd_bus='od', rcv_inst='st1', rcv_master='STN', rcv_bus='di0',
                src='die GRT STA path (forwarded clock)', fwd=dict(fo_pin='hq/fo[0]', fo_bus='fo'),
                tt=dict(T=833.333, T_cap=416.7, cap_tr='fall', C=300.0, S_kit=120.0, R_kit=30.0, fwd=True),
                ff=dict(T_hold=-416.7, H=200.0, smin_kit=80.0, h_kit=10.0, fwd=True))
    (out / 'links_d.json').write_text(json.dumps(dict(die='d', links=[link])))
    nd = dict(job='j1', block='H', die='d', die_master='H', tile=None, internal_ok=True, r2r=dict(tt=10, ff=5),
              ref=dict(tt={'w_cks': dict(L=124.3, T=833.333)}), fwd={'fo': dict(clock='w_cks', A=17.4, A_min=26.9)},
              ports={'od': dict(dir='out', bits=514, clock='w_cks', T=833.333, S=264.8, smin=126.8)})
    (out / 'needs' / 'j1.json').write_text(json.dumps(nd))
    RB.cmd_derive(SimpleNamespace(rb=1, no_publish=True))
    j = json.loads((out / 'budget_rb1' / 'summary.json').read_text())['jobs']['j1']
    row = j['links'][0]
    S_fw = round(264.8 - 17.4, 1)
    assert row['setup'] == 're-derived' and row['need'] == S_fw and row['budget'] == round(300.0 * S_fw / (S_fw + 30.0), 1)
    sdc = (tmp_path / j['sdc']).read_text()
    assert 'create_generated_clock -name ot_rb_fwo_fo' in sdc and '-clock ot_rb_fwo_fo -clock_fall' in sdc
