"""W11 MTP verify-6 in model row order (results/rtl/w11_attn_verify6_model.json) and one small RTL run."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = json.loads((ROOT / 'results/rtl/w11_attn_verify6_model.json').read_text())


def test_sources_are_pinned():
    for name, digest in REC['sources_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_builds_are_the_model_order_variant():
    a, b = REC['builds']['full_a'], REC['builds']['full_b']
    assert {'ILV=1', 'REPL=1', 'NSTAGE=2'} <= set(a['params']) and 'OT_ATTN_SETCHECK' in a['defines']
    assert 'ILV=0' in b['params'] and a['pwords'] == b['pwords'] == 2


def test_every_position_is_exact_in_model_order():
    exp = REC['model_order']['vectors']['expected']
    assert REC['model_order']['vectors']['T'] == [640] * 6
    assert exp['scores'] == 6 * 640 * 16 and exp['pv'] == 6 * 512 * 16
    for mode in ('interleaved', 'serial'):
        for r in REC['full_geometry'][mode]:
            assert r['exact'], (mode, r['L0'])
            assert r['positions'][-1]['last_pv'] == r['total']
            assert sum(p['position_cycles'] for p in r['positions']) == r['total']
    for r in REC['full_geometry']['interleaved']:
        assert r['setcheck']['errors'] == 0 and r['setcheck']['reads'] > 0
    assert REC['verdict']['status'] == 'pass'


def test_interleaving_beats_serial_and_su_order_holds():
    t = REC['verify6_cycles']
    assert str(REC['su_model']['L0']) in t and '0' in t
    for l0, v in t.items():
        assert v['interleaved'] < v['serial'], l0
    for r in REC['full_geometry']['interleaved']:
        pos = r['positions']
        for a, b in zip(pos, pos[1:]):
            assert b['su_start'] >= a['p_last'] and b['su_start'] >= b['last_score']
        for p in pos:
            assert p['p_first'] >= p['su_start'] + r['L0']


def test_default_mode_identical_and_guard_tight():
    d = REC['default_identity']
    assert all(v['identical'] for v in d['full_geometry_pwords2'].values())
    assert len(d['small_config_old_vs_new']) == 8
    assert REC['negative']['caught'] and REC['negative']['engine_params'].get('NSTAGE') == 2


def test_storage_cost():
    st = REC['storage']
    assert st['staging']['buffers'] == 2 and st['staging']['sram_macros'] == 136 and st['staging']['delta_macros'] == 68
    assert st['stationary_banks']['bytes'] == 327680


@pytest.mark.skipif(shutil.which('verilator') is None and not (
        Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator').is_file(), reason='verilator missing')
def test_small_model_order_verify_rtl(tmp_path):
    import w11_attn_verify6 as W
    import rtl_hdc_v41x_attn_campaign as C
    man = W.vectors_model('h4d64', tmp_path / 'v')
    cfg = W.CFGS['h4d64']
    exe = C.build_engine(tmp_path, {k: cfg[k] for k in ('H', 'D', 'TD', 'NL', 'TROWS')}, man['counts'],
                         {'PWORDS': 2, 'ILV': 1, 'REPL': 1, 'NSTAGE': 2})
    r, _ = W.run_exe(exe, tmp_path / 'v', 1, 60)
    assert r['exact'] and r['jobs'] == 6, r
