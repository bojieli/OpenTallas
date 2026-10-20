#!/usr/bin/env python3
"""TOKSIM-S81D/GL24 (10-20): a REDUCED attention fixture for the re-index layers L24 / L28 / L32 / L36, which the full
fixture generator (tools/s81_dv/dv_layer_fixtures.py) refuses: they read the compressed KV of L20 (kv_of = 20, including
the row L20 appends this token) and a candidate set carried from L20 (candidate_source_layer 20).

Only what the attn.gather vehicle (toksim_gath_vectors.py) reads is produced, with the same golden, writer, split and
file names as dv_layer_fixtures:
  state/kv.window.codes|scale   the layer's 127 synthetic window rows (LC.synthetic_state, D.SEED, same streams)
  state/kv.ckv20.codes|scale    L20's 1,048,575 synthetic compressed rows + the row L20 appends this token (the w17 golden
                                shard ctx1048576_L20.npz ckv20) = 1,048,576 stored rows entering the layer
  ops/attn.idx.topk_final       the golden shard's L<L> selection (json ctx_out.sel; asserted == the 512 lowest-index top
                                of the shard's L<L>.index_scores)
  ops/attn.q_rope / own_row_write / window_load / gather / rows_allgather / scores / exp / pv / ...  (as
                                dv_layer_fixtures.attention / attend, from x = the shard's L<L>.attn_norm)
Golden checks (all bitwise, nothing written on a miss): state digest ckv20 == the L20 fixture's, own window row == shard
win<L>, attention output (wo_b, all 64 heads) == shard L<L>.attn, selection == shard index-score top-512.

    HDC_V41_ARITH=chunk8 python3 toksim_gl24_attnfix.py --layers 24 28 32 36 --out DIR   (writes DIR/L24 ...)
"""
import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 's81_dv'))
import numpy as np  # noqa: E402
import dv_layer_fixtures as D  # noqa: E402

L20_CKV_SHA = '1353e03cf9001e64da125b3984002ea44b4d9963ba3be75f0f173f89fb1d0e03'  # layerbench-s81 fixtures/L20 meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--layers', type=int, nargs='+', default=[24, 28, 32, 36])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rank', type=int, default=0)
    a = p.parse_args()
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    assert V.ARITH == 'chunk8' and not V.FUSE
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=False)
    for L in a.layers:
        assert m.ratio[L] == 1 and m.kv_of[L] == 20 and m.idx_of[L] == L and m.cand_src == 20, L
    st, sdesc = LC.synthetic_state(m, D.CTX, seed=D.SEED, layers=a.layers)
    assert sdesc['sha256']['ckv20'] == L20_CKV_SHA, 'ckv20 state differs from the L20 fixture'
    z20 = np.load(D.GOLD / f'ctx{D.CTX}_L20.npz')
    st['ckv'][20].append(z20['ckv20'].astype(D.F))           # the row L20 appends this token (golden shard)
    n = len(st['ckv'][20])
    nib, sc = LC.pack_fp4_e4m3(np.stack(st['ckv'][20]))
    pos = D.CTX - 1
    cs = V.rope_cs(m.freqs_yarn, pos)
    first = None
    for L in a.layers:
        shard = D.GOLD / f'ctx{D.CTX}_L{L:02d}.npz'
        sj = json.loads((D.GOLD / f'ctx{D.CTX}_L{L:02d}.json').read_text())
        z = np.load(shard)
        rec = D.Rec()
        x = z[f'L{L}.attn_norm'].astype(D.F)
        qa = V.linear_q(m.lw(L, 'attn.wq_a.weight'), x)
        kraw = V.linear_q(m.lw(L, 'attn.wkv.weight'), x)
        rec('attn.a_proj', np.concatenate([qa, kraw]), 'wq_a out [1280] then wkv out [512] (BF16)')
        qr = D.rms_parts(V, qa, m.lw(L, 'attn.q_norm.weight'), m.eps, rec, 'attn.q_norm')
        qb = rec('attn.wq_b', V.linear_q(m.lw(L, 'attn.wq_b.weight'), qr))
        q = rec('attn.q_rope', V.rope_tail(qb.reshape(m.heads, m.hd), cs))
        kvn = D.rms_parts(V, kraw, m.lw(L, 'attn.kv_norm.weight'), m.eps, rec, 'attn.kv_norm')
        kv = rec('attn.kv_rope_qdq', V.qdq_fp8(V.rope_tail(kvn, cs)))
        rec('attn.own_row_write', kv, 'the window row this position writes')
        win = list(st['win'][L][:m.window - 1])
        rows = (win + [kv])[-m.window:]
        rec('attn.window_load', np.stack(rows), f'window rows oldest first ({len(rows)} x {m.hd})')
        s = z[f'L{L}.index_scores'].astype(np.float64)
        sel = [int(i) for i in sj['ctx_out']['sel']]
        top = sorted(int(i) for i in V.topk_lowest_index(s, min(m.topk, n)))
        checks = OrderedDict(n_rows_equals_scores=len(s) == n, sel_equals_shard_score_topk=top == sel,
                             own_window_row_equals_shard=D.same(kv, z[f'win{L}']))
        rec('attn.idx.topk_final', np.asarray(sel, np.int64), 'ascending selected compressed positions (L20 rows)')
        g = [st['ckv'][20][i] for i in sel]
        rec('attn.gather', np.stack(g), f'selected compressed rows ({len(g)} x {m.hd})')
        rows = rows + g
        rec('attn.rows_allgather', np.stack(rows), 'the attended rows (window then selections)')
        y = D.attend(V, m, L, q, np.stack(rows), cs, rec)
        checks['attn_equals_shard'] = D.same(y, z[f'L{L}.attn'])
        print(f'L{L}', json.dumps(checks))
        if not all(checks.values()):
            raise SystemExit(f'L{L}: reduced attention NOT bit-exact vs the golden shard -- nothing published')
        o = D.Out(a.out / f'L{L}')
        c8, e8 = D.pack_fp8_exact(V, LC, np.stack(win))
        o.put('state/kv.window.codes.bin', c8, format='F8_E4M3', rows=len(win), note='127 rows before this position')
        o.put('state/kv.window.scale.bin', e8, format='F8_E8M0')
        for nm, arr, fm in (('codes', nib, 'E2M1 packed (low nibble first)'), ('scale', sc, 'F8_E4M3 per 16')):
            rel = f'state/kv.ckv20.{nm}.bin'
            if first is None or nm not in first:
                o.put(rel, arr, format=fm, rows=n, note='L20 rows entering the layer incl. the L20 row of this token')
                first = dict(first or {}, **{nm: (o.d / rel, o.files[rel])})
            else:
                (o.d / rel).parent.mkdir(parents=True, exist_ok=True)
                if (o.d / rel).exists():
                    (o.d / rel).unlink()
                os.link(first[nm][0], o.d / rel)
                o.files[rel] = first[nm][1]
        ops = OrderedDict((k, o.put(f'ops/{k}.bin', v, note=rec.note.get(k))) for k, v in rec.v.items())
        rows_desc = {'20': dict(ratio=1, compressed_rows=n, index_keys=n, open_group_slots=0,
                                note='entering L%d: L20 state + the L20 row of this token' % L)}
        meta = OrderedDict(schema=D.SCHEMA + '+reduced_gl24', layer=f'L{L}', layer_index=L, kind=sj['kind'],
                           context=D.CTX, position=pos, seed=D.SEED, rank=a.rank, tp=D.TP, arith=V.ARITH,
                           fuse=sorted(V.FUSE), checks=checks, attn_scale=float(m.attn_scale),
                           shard=dict(path=str(shard), sha256=D.sha_b(shard.read_bytes()),
                                      input_sha256=sj['input_sha256'], output_sha256=sj['output_sha256'],
                                      l20_shard=str(D.GOLD / f'ctx{D.CTX}_L20.npz')),
                           checkpoint=str(LC.HF), golden_init_sha256=init_sha,
                           state=dict(sdesc, rows=rows_desc), sources=D.src_pins(), tp_split=D.tp_split(m),
                           op_order=list(ops),
                           reduced='attention gather inputs only (toksim_gl24_attnfix.py); x = shard attn_norm, '
                                   'selection = shard ctx_out.sel',
                           command='HDC_V41_ARITH=chunk8 python3 tools/s81_dv/layer_prog/toksim_gl24_attnfix.py '
                                   f'--layers {L} --out DIR')
        o.text('ops.json', json.dumps(ops, indent=1) + '\n')
        o.text('files.json', json.dumps(o.files, indent=1) + '\n')
        o.text('meta.json', json.dumps(meta, indent=1, default=str) + '\n')
        print('TOKSIM_GL24_FIX', f'L{L}', sj['kind'], 'n', n, 'sel', len(sel), 'files', len(o.files))
    return 0


if __name__ == '__main__':
    sys.exit(main())
