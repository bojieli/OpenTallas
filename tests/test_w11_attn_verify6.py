"""W11 position-interleaved MTP verify record (results/rtl/w11_attn_verify6.json) and one small RTL run."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = json.loads((ROOT / 'results/rtl/w11_attn_verify6.json').read_text())


def test_sources_are_pinned():
    # this test file is pinned in the record as committed with it (3c1b7c62); it has since gained the
    # withdrawal checks, so that one file is checked at its commit
    import subprocess
    for name, digest in REC['sources_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            assert name == 'tests/test_w11_attn_verify6.py', name
            old = subprocess.run(['git', 'show', f"3c1b7c62:{name}"], cwd=ROOT, capture_output=True,
                                 check=True).stdout
            assert hashlib.sha256(old).hexdigest() == digest, name


def test_every_position_is_exact_and_the_set_checker_is_clean():
    fg = REC['full_geometry']
    exp = REC['vectors']['expected']
    assert exp['scores'] == 16 * sum(REC['vectors']['T']) and exp['pv'] == 6 * 512 * 16
    for mode in ('interleaved', 'serial'):
        for r in fg[mode]:
            assert r['exact'], (mode, r['L0'])
            assert [p['T'] for p in r['positions']] == [635, 636, 637, 638, 639, 640]
            assert r['positions'][-1]['last_pv'] == r['total']
    for r in fg['interleaved']:
        assert r['setcheck']['errors'] == 0 and r['setcheck']['reads'] > 0
    assert REC['verdict']['synthetic_rule_status'] == 'pass'


def test_interleaving_beats_serial_at_every_su_latency():
    t = REC['verify6_cycles']
    assert set(t) >= {'0', str(REC['su_model']['L0'])}
    for l0, v in t.items():
        assert v['interleaved'] < v['serial'], l0
        assert v['interleaved_utilisation'] > v['serial_utilisation'], l0


def test_su_model_numbers_come_from_the_su_record():
    su = REC['su_model']
    rec = json.loads((ROOT / 'results/rtl/w11_su_spec.json').read_text())
    ch = rec['configs']['N1024_M256_B4R5']['cases']['T640']['chained']
    assert su['L0'] == ch['ops'][1]['write']['first'] == 188 and su['chain_end_cycle'] == ch['end_cycle'] == 451


def test_interleaved_positions_respect_the_su_order():
    for r in REC['full_geometry']['interleaved']:
        pos = r['positions']
        for a, b in zip(pos, pos[1:]):
            assert b['su_start'] >= a['p_last'] and b['su_start'] >= b['last_score']
        for p in pos:
            assert p['p_first'] >= p['su_start'] + r['L0']


def test_default_mode_is_identical():
    d = REC['default_identity']
    assert all(v['identical'] for v in d['full_geometry_pwords2'].values())
    assert [v['cycles'] for k, v in sorted(d['full_geometry_pwords2'].items())] == [449, 449, 202, 193]
    assert len(d['small_config_old_vs_new']) == 8 and all(' identical ' in x for x in d['small_config_old_vs_new'])


def test_guard_is_tight_and_storage_cost():
    assert REC['negative']['caught']
    st = REC['storage']
    assert (st['ilv0']['stationary_bytes'], st['ilv1']['stationary_bytes'], st['delta_bytes']) == (262144, 327680, 65536)


@pytest.mark.skipif(shutil.which('verilator') is None and not (
        Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator').is_file(), reason='verilator missing')
def test_small_interleaved_verify_rtl(tmp_path):
    import w11_attn_verify6 as W
    import rtl_hdc_v41x_attn_campaign as C
    man = W.vectors('h4d64', tmp_path / 'v')
    cfg = W.CFGS['h4d64']
    exe = C.build_engine(tmp_path, {k: cfg[k] for k in ('H', 'D', 'TD', 'NL', 'TROWS')}, man['counts'],
                         {'PWORDS': 2, 'ILV': 1})
    r, _ = W.run_exe(exe, tmp_path / 'v', 1, 60)
    assert r['exact'] and r['jobs'] == 6, r
    s, _ = W.run_exe(exe, tmp_path / 'v', 1, 0)
    assert s['exact'] and s['total_cycles'] <= r['total_cycles']


def test_real_mtp_claim_is_withdrawn_with_history():
    v = REC['verdict']
    assert v['status'] == 'withdrawn_for_model_order' and 'WITHDRAWN' in v['withdrawn']
    assert REC['verdict_history'][0]['status'] == 'pass' and REC['verdict_history'][0]['scope'] == 'rows-last synthetic rule'
