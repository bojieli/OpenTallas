#!/usr/bin/env python3
"""TOK-ALL-17: HHP boot calendar emitter + kvspc_phase_delivery kit hook (fail closed).  python3 -m pytest -q this file"""
import importlib.util, json, shutil, sys, tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/qwen_kv_die'))
import hhp_boot_calendar as C  # noqa: E402

_s = importlib.util.spec_from_file_location('kpd', ROOT / 'physical/die_plan/qwen_kvsys/cores/harden/kvspc_phase_delivery.py')
KPD = importlib.util.module_from_spec(_s); _s.loader.exec_module(KPD)
ES = ROOT / 'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge_b.sv'


def test_real_calendar_admitted_c708_and_main():
    for d in (1, 0):
        r = C.emit(C.AGES, d)
        assert r['admitted'] and r['pcs'] == 128 and not r['violations']
        assert all(v['edges'] >= 0 for v in r['min_margin'].values())


@pytest.mark.parametrize('mut,key', [('writer', 'W_margin'), ('slice', 'S_margin'), ('emb', 'E_margin')])
def test_mutant_calendars_caught(mut, key):
    r = C.emit(C.AGES, 1, mut)
    assert not r['admitted'] and len(r['violations']) == 128
    assert r['min_margin'][key]['edges'] < 0


def test_kit_hook_fail_closed():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); shutil.copy(ES, t / ES.name)
        with pytest.raises(SystemExit, match='MISSING'):
            KPD.apply_kit(t)
        assert (t / ES.name).read_text() == ES.read_text()          # untouched on refusal
        bad = t / 'bad.json'; bad.write_text(json.dumps(C.emit(C.AGES, 1, 'slice')))
        with pytest.raises(SystemExit, match='BAD'):
            KPD.apply_kit(t, calendar_report=bad)
        d0 = t / 'd0.json'; d0.write_text(json.dumps(C.emit(C.AGES, 0)))
        with pytest.raises(SystemExit, match='FAIL'):
            KPD.apply_kit(t, calendar_report=d0)
        stale = t / 'stale.json'; r = C.emit(C.AGES, 1); r['guard_sha256'] = '0' * 64; stale.write_text(json.dumps(r))
        with pytest.raises(SystemExit, match='STALE'):
            KPD.apply_kit(t, calendar_report=stale)
        assert (t / ES.name).read_text() == ES.read_text()
        ok = t / 'ok.json'; ok.write_text(json.dumps(C.emit(C.AGES, 1)))
        assert KPD.apply_kit(t, calendar_report=ok)['admitted']
        assert 'own <= own_pin;' in (t / ES.name).read_text()


def test_committed_report_current():
    rep = json.loads((ROOT / 'results/token_pass/hhp_boot_calendar_1027/calendar_c708.json').read_text())
    assert C.require_admitted(ROOT / 'results/token_pass/hhp_boot_calendar_1027/calendar_c708.json')
    assert rep['ages_sha256'] == C.emit(C.AGES, 1)['ages_sha256']
