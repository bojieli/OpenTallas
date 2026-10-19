#!/usr/bin/env python3
"""QLB-C4b/3b 10-18 unit tests of the matrix-side DV slice lowering (tools/qwen_layerbench/dv_lower_mat.py).

  python3 -m pytest -q tools/qwen_layerbench/test_dv_lower_mat.py      (repository root)
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dv_lower as D  # noqa: E402
import dv_lower_mat as M  # noqa: E402

np = pytest.importorskip('numpy')
AGES = dict(l8_ar=30, ar_hop=2, amax_ami=3, arx_after_amv=20, xc_cc=1)   # placeholder (structure tests only)


def ages():
    p = ROOT / M.STN_AGES
    return M.load_ages() if p.exists() else AGES


def test_regions_and_btab():
    own = D.ownership()
    reg = M.vm_regions(own)
    assert reg['GU']['base'] + reg['GU']['size'] == D.VM_EL and reg['QKV']['base'] + 128 == reg['GU']['base']
    lay = M.btab_layout(own)
    assert [e['sbase'] for e in lay['o'][0]] == [8, 16, 24] and [e['sbase'] for e in lay['gu'][5]] == [32, 40]
    assert lay['lm_head'][0][-1]['sbase'] == 72 + 8 * 24 and sorted(lay['qkv']) == [0, 2, 4, 6, 8, 10]
    sc = (np.arange(4096, dtype=np.float32) + 1).astype(np.float32)
    sc = (sc.view(np.uint32) & 0xFFFF0000).view(np.float32)
    tab = M.btab_stream(lay, {'o': sc})
    w0, pay = tab[1][0]                                 # slice 1, block 1 first words at BTAB 8..11
    assert w0 == 8 and (pay & 0xFFFF) == int(sc[128].view(np.uint32)) >> 16


def test_stn_fields_match_slice2_decode():
    c = D.cmd_stn(3, 2, 0, 8, 0x1AB, 2, 0x12345, amax=1)
    f = lambda lo, w: (c >> lo) & ((1 << w) - 1)
    assert (f(1, 3), f(4, 2), f(6, 1), f(7, 8), f(15, 9), f(24, 2), f(26, 24), f(50, 1), c >> 112) == \
        (2, 2, 0, 8, 0x1AB, 2, 0x12345, 1, 3)
    x = D.cmd_xc(0, 1, 0x100, 0xCAFE)
    assert (x >> 1) & 7 == 0 and (x >> 4) & 3 == 0 and (x >> 6) & 1 == 1 and (x >> 7) & 0xFFFF == 0x100 and \
        (x >> 23) & 0xFFFFFFFF == 0xCAFE


def test_ar_stagger_is_collision_free_and_hr_delivery_is_not():
    for name in ('o', 'down'):
        low = M.lower_matvec(name, 500, ages(), M.Chain(D.slice_map()))
        assert M.ar_collisions(low, ages()) == []
        edges = sorted(e['edge'] for e in low['expected_ar'])
        assert edges == list(range(500, 756))               # one word an edge at W5, global row order
        assert [e['tag'] for e in sorted(low['expected_ar'], key=lambda e: e['edge'])] == list(range(0, 4096, 16))
    bad = M.lower_matvec('o', 500, ages(), M.Chain(D.slice_map()), mutant='nostagger')
    assert len(M.ar_collisions(bad, ages())) > 0


def test_xc_lands_two_before_word0():
    ch = M.Chain(D.slice_map())
    x = M.lower_xc(ch, ages(), 900, 256, 3)
    assert x['cc_edge'] == 898 and x['dst'] == 0 and x['cc_word'] == (1 << 49) | (256 << 32) | 3


def test_embed_ports_exact_and_distinct():
    ch = M.Chain(D.slice_map())
    em = M.lower_embed(100, ch)
    assert len(ch.used) == 2 * 32
    assert sum(len(v) for v in em['expected_vm'].values()) == 256


def test_lm_programme_and_calendar():
    p = M.lm_programme()
    assert len(p) == 8 and all(len(d['me']) == 4 for d in p)
    lm = M.lower_lm(1000, ages(), M.Chain(D.slice_map()))
    assert len(lm['matvec']['stn']) == 25 * 12 - 2 and sorted(lm['emits']) == [0, 2, 4, 6, 8, 10]
    cal = M.lm_calendar(lm, ages(), 40)
    assert [r['unit'] for r in cal['rows']] == [1, 1, 1, 1, 0]


def test_splice_fits_cmd_cal():
    r = M.splice(ages=ages())
    assert r['cal_model']['ok'] and not any('broadcast' in e['label'] and 'PC0 ' in e['label'] for e in r['events'])
    assert {x['tag'] for x in r['xc_lowered']} == {0, 1}
