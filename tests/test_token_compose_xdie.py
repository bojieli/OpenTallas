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
    o, _ = tc.run([], [])
    for d, wls in o.items():
        ref = json.loads((tc.OUT / f'{d}.json').read_text())['workloads']
        for wl, w in wls.items():
            assert w.get('tok_s') == ref[wl].get('tok_s')
            assert w.get('by_grade') == ref[wl].get('by_grade')
