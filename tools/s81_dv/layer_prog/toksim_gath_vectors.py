#!/usr/bin/env python3
"""TOKSIM-S81C/GATH (10-19): attn.gather vehicle vectors for the 16-slice dsdv_svc_rs bench, from a REAL layer fixture.

The case format is that of tools/v41_ckv_sel_attn_vectors.py (cfg / sel / win / hkey / hdat / q / p / kv / sc / pv hex,
read by rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_rs.sv and its observation copy tb_toksim_gath.sv), but every
operand is the fixture's (released DeepSeek-V4.1-Flash checkpoint + golden shard, tools/s81_dv/dv_layer_fixtures.py):
  * selection     ops/attn.idx.topk_final (512 ascending compressed positions of the layer)
  * compressed    state/kv.ckv2|ckv1.codes/scale (the stored 288-B main-KV rows: 512 E2M1 nibbles low first + 32 E4M3
                  scales) of every selected row and of its +-1 / +-256 neighbours (real rows, so an addressing error
                  reads a wrong but present row); a selected id == compressed_rows (this position's new row) takes the
                  fixture's attn.cmp.row_qdq through the golden's own fp4 quantiser
  * window        state/kv.window.codes/scale (127 rows) + the own row (fp8 codes of attn.own_row_write)
  * q / p         attn.q_rope / BF16(attn.exp) of the rank's 16 heads
Anchors (asserted, bitwise): stored rows decode to ops/attn.rows_allgather (window = attn.window_load, selected =
attn.gather); engine products x attn_scale == ops/attn.scores, P.V == ops/attn.pv for the rank's heads.
--view D,S relabels the owner field of every id (die bits [5:4] ^= D, stack bits [7:6] ^= S): the DIE 0 / ST 0 bench
then sees exactly the rows die D / stack S owns (PC = id[8], block = id >> 8 and row = id[3:0] are unchanged).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / 'tools', ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import rtl_hdc_v41x_attn_campaign as C  # noqa: E402

V = C.V
H, D, TD, WIN = 16, 512, 32, 128


def owner(g):
    return (g >> 4) & 3, (g >> 6) & 3, ((g >> 8) << 4) | (g & 15)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixture', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--view', default='0,0')
    a = ap.parse_args()
    V.set_arith('chunk8')
    fx = a.fixture
    meta = json.loads((fx / 'meta.json').read_text())
    files = json.loads((fx / 'files.json').read_text())
    ops = json.loads((fx / 'ops.json').read_text())

    def ld(rel, info):
        b = (fx / rel).read_bytes()
        assert hashlib.sha256(b).hexdigest() == info['sha256'], rel
        return np.frombuffer(b, dtype=np.dtype(info['dtype'])).reshape(info['shape'])

    def op(n):
        return ld(f'ops/{n}.bin', ops[n])
    vd, vs = (int(x) for x in a.view.split(','))
    relab = lambda g: g ^ (vd << 4) ^ (vs << 6)
    h0, h1 = meta['tp_split']['heads'][meta['rank']]
    assert h1 - h0 == H
    (lk, st), = meta['state']['rows'].items()
    n = int(st['compressed_rows'])
    ckc = ld(f'state/kv.ckv{lk}.codes.bin', files[f'state/kv.ckv{lk}.codes.bin'])   # [n, 256] packed
    cks = ld(f'state/kv.ckv{lk}.scale.bin', files[f'state/kv.ckv{lk}.scale.bin'])   # [n, 32]
    sel0 = [int(x) for x in op('attn.idx.topk_final')]
    nsel = len(sel0)
    T = WIN + nsel

    def row_codes(g):
        if g < n:
            pk = ckc[g].astype(np.int64)
            codes = np.empty(D, np.int64); codes[0::2] = pk & 15; codes[1::2] = pk >> 4
            return codes, cks[g].astype(np.int64), bytes(ckc[g]) + bytes(cks[g])
        assert g == n, g
        codes, sc = C.fp4_row_codes(op('attn.cmp.row_qdq'))
        pk = (codes[0::2] | (codes[1::2] << 4)).astype(np.uint8)
        return codes, sc, bytes(pk) + bytes(sc.astype(np.uint8))
    # window rows (stored fp8) + own row
    wc = ld('state/kv.window.codes.bin', files['state/kv.window.codes.bin']).astype(np.int64)
    we = ld('state/kv.window.scale.bin', files['state/kv.window.scale.bin']).astype(np.int64)
    oc, os16 = C.fp8_row_codes(op('attn.own_row_write'))
    wcodes = np.vstack([wc, oc[None]])
    we8 = np.vstack([we, os16[0::2][None]])
    win_words = []
    for r in range(WIN):
        w = sum(int(c) << (8 * e) for e, c in enumerate(wcodes[r]))
        w |= sum(int(we8[r, g]) << (4096 + 8 * g) for g in range(16))
        win_words.append(w)
    # selected rows
    sc_codes, sc_scales = [], []
    for g in sel0:
        c_, s_, _ = row_codes(g)
        sc_codes.append(c_); sc_scales.append(s_)
    fmt = np.array([0] * WIN + [1] * nsel, np.int64)
    codes = np.vstack([wcodes] + [c[None] for c in sc_codes])
    scales = np.vstack([np.repeat(we8, 2, axis=1)] + [s[None] for s in sc_scales])
    q = np.asarray(op('attn.q_rope')[h0:h1], np.float32)
    p = V.to_bf16(op('attn.exp')[h0:h1])
    job = C.Job(q, fmt, codes, scales, p, f'{meta["layer"]} gather view {vd},{vs}')
    kvm = job.kvm()
    sc, pv = job.expected()
    scale = np.float32(meta.get('attn_scale', D ** -0.5))
    anchor = dict(
        window_rows=bool(np.array_equal(V.bits(kvm[:WIN]), V.bits(op('attn.window_load')))),
        gathered_rows=bool(np.array_equal(V.bits(kvm[WIN:]), V.bits(op('attn.gather')))),
        rows_allgather=bool(np.array_equal(V.bits(kvm), V.bits(op('attn.rows_allgather')))),
        scores=bool(np.array_equal(V.bits(V.mul(sc, scale)), V.bits(op('attn.scores')[h0:h1]))),
        pv=bool(np.array_equal(V.bits(pv), V.bits(op('attn.pv')[h0:h1]))),
        q_bf16=bool(np.all((C.u32(q) & 0xFFFF) == 0)))
    assert all(anchor.values()), anchor
    # HBM image: every selected row + real neighbours, at the relabelled id's owner address
    sel = [relab(g) for g in sel0]
    ids = set(sel0)
    nbr = {g + dd for g in sel0 for dd in (-256, -1, 1, 256) if 0 <= g + dd <= n - 1} - ids
    max_local = ((max(n, max(sel0)) >> 8) << 4) + 15
    base = [1_000_003 * (s + 1) for s in range(4)]
    count = [9 * (max_local + 1)] * 4
    hkey, hdat = [], []
    for g0 in sorted(ids | nbr):
        g = relab(g0)
        die, stack, local = owner(g)
        packed = row_codes(g0)[2]
        assert len(packed) == 288
        for k in range(9):
            hkey.append((die << 32) | (stack << 30) | (base[stack] + 9 * local + k))
            hdat.append(int.from_bytes(packed[32 * k:32 * (k + 1)], 'little'))
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    counts, stats = C.write_jobs(out, [job], H, D, TD)
    C.write_hex(out / 'sel.hex', sel, 32)
    C.write_hex(out / 'win.hex', win_words, 4224)
    C.write_hex(out / 'hkey.hex', hkey, 64)
    C.write_hex(out / 'hdat.hex', hdat, 256)
    qs = 8 * (n // 32)
    qc = [sum(1 for g in sel if b0 <= g < b1) for b0, b1 in zip([0, qs, 2 * qs, 3 * qs], [qs, 2 * qs, 3 * qs, 1 << 30])]
    cfg = [WIN, nsel, n, len(hkey), T, *qc, *base, *count]
    C.write_hex(out / 'cfg.hex', cfg + [0] * (32 - len(cfg)), 32)
    own = [g for g in sel if owner(g)[:2] == (0, 0)]
    rec = dict(schema='opentallas.toksim_s81c.gath_case.v1', layer=meta['layer'], kind=meta['kind'], rank=meta['rank'],
               heads=[h0, h1], fixture=str(fx), fixture_shard=meta.get('shard'), checkpoint=meta.get('checkpoint'),
               view=dict(die=vd, stack=vs), compressed_rows=n, n_sel=nsel, T=T, owned_rows=len(own),
               owned_pc=[sum(1 for g in own if (g >> 8) & 1 == pc) for pc in (0, 1)],
               held_rows=sum(1 for g in sel if owner(g)[1] == 0), neighbour_rows=len(nbr), hbm_sectors=len(hkey),
               anchors=anchor, counts=counts, expected=stats,
               golden='fixture ops attn.gather / attn.window_load / attn.rows_allgather (stored rows, bitwise), '
                      'attn.scores (x attn_scale) and attn.pv of heads %d..%d (bitwise)' % (h0, h1 - 1),
               images={x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(out.glob('*.hex'))})
    (out / 'case.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('layer', 'view', 'owned_rows', 'owned_pc', 'held_rows', 'hbm_sectors', 'anchors')}))


if __name__ == '__main__':
    main()
