"""tools/token_compose_xdie.py: graded token composition with inter-die terms (TOKEN-COMPOSE 10-18)."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('token_compose_xdie', ROOT / 'tools/token_compose_xdie.py')
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)


@pytest.fixture(scope='module')
def out():
    o, _ = tc.run([], [])
    return o


def test_exposed_is_e_minus_o_shared_by_grade():
    parts = tc.xdie('L0.xdie.x', 2, [('measured-current-RTL', 300.0, 'a'), ('modelled-PHY', 100.0, 'b')], 150.0, 's', {})
    assert [round(p['cycles'], 2) for p in parts] == [187.5, 62.5]          # (400 - 150) split 3:1
    assert sum(p['total'] for p in parts) == pytest.approx(500.0)          # n = 2
    hidden = tc.xdie('L0.xdie.y', 1, [('priced', 80.0, '')], 120.0, 's', {})
    assert hidden[0]['cycles'] == 0.0                                       # max(0, E - O)


def test_union_overlap():
    assert tc.union_overlap(0, 100, [(10, 30), (20, 50), (90, 200), (300, 400)]) == pytest.approx(50.0)
    assert tc.union_overlap(0, 10, []) == 0.0


@pytest.mark.parametrize('design,wl', [('ds_rom', 'ar'), ('ds_rom', 'mtp'), ('hbm_gen_ds', 'ar'), ('hbm_gen_ds', 'mtp'),
                                       ('hbm_gen_qwen', 'ar')])
def test_terms_at_price_reproduce_the_price_of_record(out, design, wl):
    w = out[design][wl]
    assert w['T_at_price_cycles'] == pytest.approx(w['price_of_record']['cycles'], abs=1.0)


def test_every_term_graded_and_sourced(out):
    for d, wls in out.items():
        for wl, w in wls.items():
            if not w['available']:
                assert w['reason']
                continue
            assert sum(w['by_grade'].values()) == pytest.approx(w['T_token_cycles'], abs=1.0)
            for t in w['terms']:
                assert t['grade'] in tc.GRADES
                assert t['source']['record'] and t['source']['commit'] and t['source']['pointer']
                if t['kind'] == 'xdie':
                    assert 'O_source' in t and t['O'] >= 0


def test_override_raises_the_current_rtl_share(tmp_path):
    base, _ = tc.run([], [])
    rec = tmp_path / 'record.json'
    rec.write_text(json.dumps({'token_compose': {'terms': [
        {'design': 'qwen_rom', 'workload': 'ar', 'slot': 'Lc.xdie.d2d_attention', 'E': [
            {'grade': 'measured-current-RTL', 'E': 70.0}, {'grade': 'modelled-PHY', 'E': 10.0}], 'O': 0.0,
         'O_source': 'test schedule'}]}}))
    o, seen = tc.run([str(rec)], [])
    w0, w1 = base['qwen_rom']['ar'], o['qwen_rom']['ar']
    assert seen[0]['used'] is True
    assert w1['by_grade']['measured-current-RTL'] == pytest.approx(35 * 70.0)
    assert w1['T_token_cycles'] == pytest.approx(w0['T_token_cycles'] + 35 * (80.0 - 65.0))
    assert w1['pct_measured_current_rtl'] > w0['pct_measured_current_rtl']


def test_committed_outputs_match():
    o, _ = tc.run()                                   # default = discovery of every record
    for d, wls in o.items():
        ref = json.loads((tc.OUT / f'{d}.json').read_text())['workloads']
        for wl, w in wls.items():
            assert w.get('tok_s') == ref[wl].get('tok_s')
            assert w.get('by_grade') == ref[wl].get('by_grade')


# ---------------------------------------------------------------- ROOT-TOKTOOL 10-18: discovery + O_meas never assumed
def _w(p, doc):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc))


def test_discovery_finds_every_family_without_a_path_list(tmp_path):
    tcb = {'token_compose': {'terms': [{'design': 'qwen_rom', 'slot': 'x', 'cycles': 1.0, 'grade': 'priced'}]}}
    _w(tmp_path / 'results/rtl/s81_layer_tput_1018/record.json', {'token_compose': {'terms': []}})     # TOKEN-PASS top
    _w(tmp_path / 'results/rtl/hbm_ds_layer_tput_1019/slice_sw/run_ds_l0/record.json', tcb)          # LB2 per-layer, deep
    _w(tmp_path / 'results/rtl/hbm_ds_layer_tput_1019/fixtures/L00/manifest.json', {'a': 1})         # not a record
    _w(tmp_path / 'results/rtl/xdie_qwen_1018/record.json', {'schema': 'x'})                          # XDIE top, no block
    _w(tmp_path / 'results/rtl/xdie_qwen_1018/pair_r1/record.json', tcb)                              # XDIE sub-record
    _w(tmp_path / 'results/rtl/xdie_qtp8_1018/runs/c1/record.json', {'case': 1})                      # case record, no block
    got = dict(tc.discover_records(tmp_path))
    assert got == {'results/rtl/s81_layer_tput_1018/record.json': 'pass',
                   'results/rtl/hbm_ds_layer_tput_1019/slice_sw/run_ds_l0/record.json': 'pass',
                   'results/rtl/xdie_qwen_1018/record.json': 'xdie',
                   'results/rtl/xdie_qwen_1018/pair_r1/record.json': 'xdie'}


def test_default_run_reads_the_committed_records():
    rels = {r for r, _ in tc.discover_records()}
    assert 'results/rtl/xdie_qwen_1018/pair_r2/record.json' in rels
    assert 'results/rtl/xdie_s81_1018/record.json' in rels
    o, seen = tc.run()
    used = {s['record'] for s in seen if s['used']}
    assert {'results/rtl/xdie_s81_1019/record.json', 'results/rtl/xdie_qwen_1018/pair_r2/record.json'} <= used
    older = next(s for s in seen if s['record'] == 'results/rtl/xdie_s81_1018/record.json')
    assert not older['used'] and older['superseded_by'] == 'results/rtl/xdie_s81_1019/record.json'
    assert {s['record'] for s in seen} == rels
    for d, wls in o.items():                          # no two records silently fight over one slot
        for w in wls.values():
            assert not any('replaces_override_from' in u for u in w.get('overrides_used', []))


def test_exchange_override_without_o_meas_is_rejected(tmp_path):
    base, _ = tc.run([], [])
    rec = tmp_path / 'record.json'
    _w(rec, {'token_compose': {'terms': [{'design': 'qwen_rom', 'workload': 'ar', 'slot': 'Lc.xdie.d2d_attention',
                                          'E': [{'grade': 'measured-current-RTL', 'E': 70.0}]}]}})   # no O, no O_source
    o, seen = tc.run([str(rec)], [])
    assert seen[0]['used'] is False and seen[0]['rejected'][0]['slot'] == 'Lc.xdie.d2d_attention'
    assert o['qwen_rom']['ar']['T_token_cycles'] == base['qwen_rom']['ar']['T_token_cycles']
    _w(rec, {'token_compose': {'terms': [{'design': 'qwen_rom', 'workload': 'ar', 'slot': 'Lc.xdie.d2d_attention',
                                          'E': [{'grade': 'measured-current-RTL', 'E': 70.0}], 'O': 0.0, 'O_source': ' '}]}})
    assert tc.run([str(rec)], [])[1][0]['used'] is False                                           # empty O_source


def test_o_ref_reads_o_meas_from_the_schedule(tmp_path):
    _w(tmp_path / 'schedule.json', {'exchanges': [{'O_meas': 30.0}]})
    rec = tmp_path / 'record.json'
    _w(rec, {'token_compose': {'terms': [{'design': 'qwen_rom', 'workload': 'ar', 'slot': 'Lc.xdie.d2d_attention',
                                          'E': [{'grade': 'measured-current-RTL', 'E': 70.0}],
                                          'O_ref': {'record': 'schedule.json', 'pointer': 'exchanges.0.O_meas'}}]}})
    o, seen = tc.run([str(rec)], [])
    assert seen[0]['used'] is True
    t = [t for t in o['qwen_rom']['ar']['terms'] if t['slot'] == 'Lc.xdie.d2d_attention']
    assert t[0]['O'] == 30.0 and t[0]['cycles'] == pytest.approx(40.0) and 'exchanges.0.O_meas' in t[0]['O_source']


def test_inactive_historical_terms_cannot_change_current_price(tmp_path):
    p = tmp_path / 'historical.json'
    _w(p, {'token_compose': {'active': False, 'selection_note': 'replaced component measurement',
                            'terms': [{'design': 'qwen_rom', 'workload': 'ar', 'slot': 'head.die',
                                       'cycles': 1e12, 'grade': 'measured-current-RTL'}]}})
    baseline, _ = tc.run([], [])
    current, seen = tc.run([str(p)], [])
    assert current['qwen_rom']['ar']['tok_s'] == baseline['qwen_rom']['ar']['tok_s']
    assert not seen[0]['used'] and seen[0]['why'] == 'replaced component measurement'


def test_two_records_on_one_slot_are_reported(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    for p, c in ((a, 100.0), (b, 200.0)):
        _w(p, {'token_compose': {'terms': [{'design': 'qwen_rom', 'workload': 'ar', 'slot': 'head.die', 'cycles': c,
                                            'grade': 'measured-current-RTL'}]}})
    o, _ = tc.run([str(a), str(b)], [])
    u = o['qwen_rom']['ar']['overrides_used']
    assert u[-1]['replaces_override_from'] == [u[0]['record']]
