#!/usr/bin/env python3
"""TOKSIM-S81D/APSP (10-20): a REDUCED layer fixture holding the inputs of the sparse-layer a_proj NODE: the 448 a_proj
rows (wq_a ++ wkv, FP8) PLUS the BF16 rows the old DAG node also carried -- compressor.wkv (+ compressor.wgate at ratio 2)
and indexer.weights_proj -- which all read the SAME x (the layer's attn_norm output).  Same writer, golden, split and file
names as tools/s81_dv/dv_layer_fixtures.py (and TOKSIM-S81C/FSGU toksim_fsgu_ffnfix.py):

  ops/attn.norm.scale   = the pinned w17 golden shard's L<L>.attn_norm                    (x of every row below)
  ops/attn.a_proj       = linear_q(wq_a) ++ linear_q(wkv)                                 (dv_layer_fixtures.attention)
  ops/attn.cmp.wkv      = ratio 2: mv(wkv ++ wgate, x) FP32 (kv[512] then gate[512]);
                          ratio 1: linear_bf16(wkv, x)                                    (dv_layer_fixtures.compressor)
  ops/attn.idx.weights  = to_bf16(mul(linear_bf16(weights_proj, x), index_w_scale))     (dv_layer_fixtures.indexer)
  weights/{wq_a,wkv}[.scale], compressor.{wkv,wgate}, indexer.weights_proj = LC.die_slices rank slices (LC._raw)
The compressor rows exist only on a KV-source layer (L in kv_src), weights_proj only on an index-source layer (idx_src),
exactly as die_slices / the full generator decide.  Validation: --compare FULL_FIXTURE_DIR (L2 / L20): every file written
here must be byte-identical to the full fixture's.

    HDC_V41_ARITH=chunk8 toksim_apsp_fix.py --layer 24 --out DIR [--compare FULL_FIXTURE_DIR]
"""
import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 's81_dv'))
import numpy as np  # noqa: E402
import dv_layer_fixtures as D  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--layer', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rank', type=int, default=0)
    p.add_argument('--compare', default=None)
    a = p.parse_args()
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    assert V.ARITH == 'chunk8' and not V.FUSE
    L = a.layer
    shard = D.GOLD / f'ctx{D.CTX}_L{L:02d}.npz'
    sj = json.loads((D.GOLD / f'ctx{D.CTX}_L{L:02d}.json').read_text())
    z = np.load(shard)
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=False)
    o = D.Out(a.out)
    xa = z[f'L{L}.attn_norm'].astype(D.F)
    rec = D.Rec()
    rec('attn.norm.scale', xa, 'the w17 golden shard L%d.attn_norm' % L)
    qa = V.linear_q(m.lw(L, 'attn.wq_a.weight'), xa)
    kraw = V.linear_q(m.lw(L, 'attn.wkv.weight'), xa)
    rec('attn.a_proj', np.concatenate([qa, kraw]), 'wq_a out [1280] then wkv out [512] (BF16): one a_proj sweep')
    is_kv, is_idx = L in m.kv_src, L in m.idx_src
    ratio = m.ratio[L]
    if is_kv:                                   # dv_layer_fixtures.compressor (only the projection: pooling is later)
        if ratio == 1:
            rec('attn.cmp.wkv', V.linear_bf16(m.lw(L, 'attn.compressor.wkv.weight'), xa))
        else:
            wkv = np.concatenate([m.lw(L, 'attn.compressor.wkv.weight'), m.lw(L, 'attn.compressor.wgate.weight')])
            kv, sc = np.split(V.mv(wkv, xa), 2)
            rec('attn.cmp.wkv', np.concatenate([kv, sc]), 'kv[512] then gate[512] (FP32)')
    if is_idx:                                  # dv_layer_fixtures.indexer (only the weights projection)
        rec('attn.idx.weights', V.to_bf16(V.mul(V.linear_bf16(m.lw(L, 'attn.indexer.weights_proj.weight'), xa),
                                                m.index_w_scale)))
    ops = OrderedDict((k, o.put(f'ops/{k}.bin', v, note=rec.note.get(k))) for k, v in rec.v.items())
    s = dict(tp=D.TP, dim=m.dim, hd=m.hd, heads=m.heads, q_rank=1280, o_groups=m.groups, o_rank=m.o_rank,
             n_exp=m.n_exp, moe_ff=2304, hc=m.hc, ratio=m.ratio)
    LC.R_KV_SRC, LC.R_IDX_SRC = (lambda: m.kv_src), (lambda: m.idx_src)
    keep = {'wq_a', 'wq_a.scale', 'wkv', 'wkv.scale', 'compressor.wkv', 'compressor.wgate', 'indexer.weights_proj'}
    for name, tensor, rows, cols in LC.die_slices(L, a.rank, s, [], False):
        if name in keep:
            arr, dt = LC._raw(ck, tensor, rows, cols)
            o.put(f'weights/{name}.bin', arr, tensor=tensor, rows=rows, cols=cols, format=dt)
    meta = OrderedDict(schema=D.SCHEMA + '+reduced_apsp', layer=f'L{L}', layer_index=L, kind=sj['kind'], context=D.CTX,
                       position=D.CTX - 1, seed=D.SEED, rank=a.rank, tp=D.TP, experts=sj.get('experts', []),
                       arith=V.ARITH, fuse=sorted(V.FUSE), ratio=int(ratio), kv_source=bool(is_kv),
                       index_source=bool(is_idx), index_w_scale=float(m.index_w_scale),
                       shard=dict(path=str(shard), sha256=D.sha_b(shard.read_bytes()), input_sha256=sj['input_sha256'],
                                  output_sha256=sj['output_sha256']),
                       checkpoint=str(LC.HF), golden_init_sha256=init_sha, sources=D.src_pins(), tp_split=D.tp_split(m),
                       op_order=list(ops), reduced='a_proj + compressor.wkv/wgate + indexer.weights_proj inputs only '
                                                    '(toksim_apsp_fix.py)',
                       command=f'HDC_V41_ARITH=chunk8 python3 tools/s81_dv/layer_prog/qf_producer/toksim_apsp_fix.py '
                               f'--layer {L} --out DIR')
    o.text('ops.json', json.dumps(ops, indent=1) + '\n')
    o.text('files.json', json.dumps(o.files, indent=1) + '\n')
    o.text('meta.json', json.dumps(meta, indent=1, default=str) + '\n')
    o.manifest()
    rc = 0
    if a.compare:
        cf = json.loads((Path(a.compare) / 'files.json').read_text())
        bad = [k for k, v in o.files.items() if k not in cf or cf[k]['sha256'] != v['sha256']]
        print('COMPARE', a.compare, f'{len(o.files) - len(bad)}/{len(o.files)} files byte-identical', bad[:10])
        cm = json.loads((Path(a.compare) / 'meta.json').read_text())
        print('COMPARE tp_split', cm['tp_split'] == meta['tp_split'])
        rc = 1 if bad else 0
    print('TOKSIM_APSP_FIX', f'L{L}', sj['kind'], 'ratio', ratio, 'kv_source', is_kv, 'index_source', is_idx,
          len(o.files), 'files', list(ops))
    return rc


if __name__ == '__main__':
    sys.exit(main())
