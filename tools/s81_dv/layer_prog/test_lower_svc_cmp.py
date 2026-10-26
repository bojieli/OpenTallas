"""TOK-DS-CMP: compressed-row svc frames decode exactly as dsdv_svc_att does (SEL_IDS, ROWS, held-row HBM image)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lower_svc as L  # noqa: E402


def fake_job(mutant=None):
    j = L.Job.__new__(L.Job)
    rng = np.random.default_rng(7)
    j.tag, j.mutant = 0x21, mutant
    j.sel = np.array([3, 17, 256 + 5, 4096 + 9, 70000], np.int64)
    j.held = (((j.sel >> 4) & 3) == L.DIE_ID) & (((j.sel >> 6) & 3) == L.ST)
    T = L.WIN + len(j.sel)
    j.codes_all = rng.integers(0, 16, (T, L.D))
    j.sc_all = rng.integers(0, 256, (T, L.D // 16))
    return j


def rtl_rows_bits(q, tile):
    rh = tile & 1
    return ((q >> (290 + 16 * rh)) & 0xFFFF) << 128 | (q >> (34 + 128 * rh)) & ((1 << 128) - 1)


def test_sel_ids_and_rows_decode():
    j = fake_job()
    fr = dict(j._sel_frames())
    h = fr['SEL_IDS'][0]
    assert h >> 508 == 7 and h & 1023 == 0 and (h >> 10) & 1023 == len(j.sel)
    ids = [(fr['SEL_IDS'][1 + i // 16] >> (32 * (i % 16))) & 0xFFFFFFFF for i in range(len(j.sel))]
    assert ids == list(j.sel)
    rows = fr['ROWS'][1:]
    assert fr['ROWS'][0] >> 508 == 6 and len(rows) == 8 * int((~j.held).sum())
    for q in rows:
        k, pair = q & 1023, (q >> 31) & 7
        assert not j.held[k]
        for t in (2 * pair, 2 * pair + 1):
            assert rtl_rows_bits(q, t) == j.tile_row(L.WIN + k, t)


def test_held_image_matches_fetch_landing():
    j = fake_job()
    j.T, j.wfirst = L.WIN + len(j.sel), 0
    j.codes = np.zeros((L.WIN, L.D), np.int64)
    j.e8 = np.zeros((L.WIN, 16), np.int64)
    img = j.hbm_image()
    for k in np.flatnonzero(j.held):
        g = int(j.sel[k])
        o = 144 * (g & 15)
        for sd in range(16):
            pc = (g >> 8) & 1
            a = L.SB + 9 * (g >> 9) + (o >> 8)
            two = img.get(((2 * sd + pc) << 32) | a, 0) | img.get(((2 * sd + pc) << 32) | (a + 1), 0) << 256
            assert (two >> (o & 255)) & ((1 << 144) - 1) == j.tile_row(L.WIN + int(k), L.tile_of(sd))


def test_mutants_change_words():
    base, sid, rp = (dict(fake_job(m)._sel_frames()) for m in (None, 'sel_id', 'rows_pair'))
    assert base['SEL_IDS'] != sid['SEL_IDS'] and base['ROWS'] == sid['ROWS']
    assert base['ROWS'] != rp['ROWS']


def test_pio_scales_with_rows():
    assert L.pio_for(297, 128) == 297
    assert L.pio_for(297, 640) > L.pio_for(297, 256) > 297


def test_bound_ages_need_every_route(tmp_path):
    import json
    import pytest
    rec = json.loads((L.ROOT / 'results/token_pass/bound_die_1026/svc_routes.json').read_text())
    ag = L._ages(None, L.ROOT / 'results/token_pass/bound_die_1026/svc_routes.json')
    assert (ag['j_w'], ag['j_e'], ag['q_w'], ag['q_e']) == (6, 12, 20, 23)
    rec['routes'] = [r for r in rec['routes'] if r.get('target_port') != 's_jd_e']
    p = tmp_path / 'r.json'
    p.write_text(json.dumps(rec))
    with pytest.raises(ValueError):
        L.bound_ages(p)
