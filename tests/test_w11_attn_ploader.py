"""Consistency of the W11 two-word probability-loader record (results/rtl/w11_attn_ploader.json); no simulation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = json.loads((ROOT / 'results/rtl/w11_attn_ploader.json').read_text())
FULL = REC['full_geometry']
MANIFEST = ROOT / 'results/rtl/v41_full_attention_numeric/vector_manifest.json'


def test_sources_are_pinned():
    for name, digest in REC['sources_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_every_full_geometry_case_is_exact_against_the_golden():
    cases = json.loads(MANIFEST.read_text())['cases']
    for key, run in FULL.items():
        assert run['status'] == 'pass' and run['build']['status'] == 'build_pass', key
        assert [c['name'] for c in run['cases']] == [c['name'] for c in cases], key
        for c, m in zip(run['cases'], cases):
            assert c['exact'] and c['sc_errors'] == 0 and c['pv_errors'] == 0, (key, c['name'])
            assert c['sc_checked'] == m['expected']['scores'] and c['pv_checked'] == m['expected']['pv'] == 8192
            assert c['faults'] == m['expected']['score_faults'] + m['expected']['pv_faults']
            assert c['T'] == m['rows']


def test_windows_are_consistent_with_the_log_fields():
    for run in FULL.values():
        for c in run['cases']:
            assert c['qk_window'] == c['qk_last'] - c['qk_first'] + 1
            assert c['pv_window'] == c['pv_last'] - c['pv_first'] + 1
            assert c['pv_bubbles'] == c['pv_window'] - c['pv_beats']
            assert c['qk_beats'] == -(-c['T'] // 4)
            assert c['pv_beats'] == -(-c['T'] // 32) * 8
            assert c['last_pv'] == c['job_cycles']


def test_pwords1_is_cycle_identical_to_the_committed_gate():
    base = {r['name']: r['fields'] for r in json.loads(
        (ROOT / 'results/rtl/v41_full_attention_numeric/result.json').read_text())['results']}
    for c in FULL['pwords1_psup1']['cases']:
        assert c['job_cycles'] == base[c['name']]['cycles'], c['name']
    m = {c['name']: c for c in FULL['pwords1_psup1']['cases']}['mixed640']
    assert (m['qk_first'], m['qk_last'], m['pv_first'], m['pv_last'], m['last_pv']) == (23, 182, 248, 559, 609)
    assert REC['verdict']['pwords1_cycle_identical']


def test_pwords2_meets_the_pv_target_only_with_two_words_supplied():
    s = REC['summary']['mixed640']
    assert s['pwords2_supply2']['pv_beats'] == 160 and s['pwords2_supply2']['pv_window'] <= 170
    assert s['pwords2_supply2']['job'] < s['pwords1']['job']
    assert s['pwords2_supply1']['pv_window'] > s['pwords2_supply2']['pv_window']
    assert s['pwords1']['qk_window'] == s['pwords2_supply2']['qk_window'] == 160


def test_storage_cost_arithmetic():
    st = REC['storage']
    assert st['pwords1']['stationary_bytes'] == 196608 and st['pwords2']['stationary_bytes'] == 262144
    assert st['delta_stationary_bits'] == 65536 * 8
    assert (st['pwords1']['p_ingress_bits'], st['pwords2']['p_ingress_bits']) == (512, 1024)


def test_reduced_benches_pass():
    red = REC['reduced']
    assert all(r['status'] == 'pass' and r['errors'] == 0 for r in red['tile']['results'])
    assert {(r['PWORDS'], r['NBANK']) for r in red['tile']['results']} == {(1, 3), (2, 4)}
    assert any(r['load_stats']['unpaired_high_garbage'] > 0 for r in red['tile']['results'])
    assert 'engine_h8d64' in red
    for k in ('engine_h16d128', 'engine_h8d64'):
        if k in red:
            assert all(r['exact'] for r in red[k]['results']), k
    for r in red['engine_h8d64']['results']:
        assert r['cycles'] > 0 and not r['timeout']
    assert {(r['PWORDS'], r['psup']) for r in red['engine_h8d64']['results']} == {(1, 1), (2, 2), (2, 1)}
    assert REC['verdict']['status'] == 'pass'


def test_mtp_verify6_positions():
    v = REC['mtp_verify6']
    for pw in (1, 2):
        r = v[f'pwords{pw}']
        assert r['exact'] and r['jobs'] == 6 and r['score_errors'] == 0 and r['pv_errors'] == 0 and not r['timeout']
        assert r['scores_checked'] == 6 * 640 * 16 and r['pv_checked'] == 6 * 512 * 16
        pp = r['per_position']
        assert len(pp) == 6 and pp[-1]['last_pv'] == r['total_cycles']
        assert sum(x['position_cycles'] for x in pp) == r['total_cycles']
        assert all(x['pv_beats'] == 160 and x['qk_beats'] == 160 for x in pp)
    assert v['pwords2']['total_cycles'] < v['pwords1']['total_cycles']
