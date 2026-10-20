#!/usr/bin/env python3
"""TOKSIM-S81C/FSGU (10-19): a REDUCED layer fixture (a_proj + ffn.experts_gu inputs only) for layers the full fixture
generator refuses (tools/s81_dv/dv_layer_fixtures.py: L3 / L21 / L24 read KV / index sources appended by an earlier
layer this token; L1 is not in its LAYERS table).  Same writer, same golden, same split, same file names:
  ops/attn.norm.scale  = the pinned w17 golden shard's L<L>.attn_norm   (a_proj x)
  ops/attn.a_proj      = hdc_golden_v41.linear_q(wq_a) ++ linear_q(wkv)   (as dv_layer_fixtures.attention)
  ops/ffn.norm.scale   = the shard's L<L>.ffn_norm                       (experts_gu x)
  ops/ffn.experts.<e>.gu = linear_q(w1) ++ linear_q(w3)                  (as dv_layer_fixtures.expert)
  weights/{wq_a,wkv,exp<e>.w1,exp<e>.w3}[.scale] = LC.die_slices rank slices (LC._raw), meta.tp_split = tp_split(m)
The routed experts are re-derived from the shard x (router -> softplus.sqrt -> +bias -> top-6, as moe()) and must equal
the shard's.  Validation: --layer L0 must reproduce the full L0 fixture's files byte for byte (--compare DIR).

    HDC_V41_ARITH=chunk8 toksim_fsgu_ffnfix.py --layer 3 --out DIR [--compare FULL_FIXTURE_DIR]
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
    xf = z[f'L{L}.ffn_norm'].astype(D.F)
    # routed experts from the shard x (moe())
    logit = V.mv(m.lw(L, 'ffn.gate.weight'), xf)
    scores = V.sqrt(V.softplus(logit))
    biased = V.add(scores, m.lw(L, 'ffn.gate.bias'))
    ids = sorted(int(i) for i in V.topk_lowest_index(biased, m.k_exp))
    checks = OrderedDict(experts_equal_shard=ids == sj['experts'])
    rec = D.Rec()
    rec('attn.norm.scale', xa, 'the w17 golden shard L%d.attn_norm' % L)
    qa = V.linear_q(m.lw(L, 'attn.wq_a.weight'), xa)
    kraw = V.linear_q(m.lw(L, 'attn.wkv.weight'), xa)
    rec('attn.a_proj', np.concatenate([qa, kraw]), 'wq_a out [1280] then wkv out [512] (BF16): one a_proj sweep')
    rec('ffn.norm.scale', xf, 'the w17 golden shard L%d.ffn_norm' % L)
    for i in ids:
        pre = f'{m.P(L)}ffn.experts.{i}.'
        g = V.linear_q(m.w[pre + 'w1.weight'], xf)
        u = V.linear_q(m.w[pre + 'w3.weight'], xf)
        rec(f'ffn.experts.{i}.gu', np.concatenate([g, u]), 'w1 (gate) out then w3 (up) out (BF16)')
    print(json.dumps(checks))
    if not all(checks.values()):
        raise SystemExit('routed experts differ from the shard: nothing published')
    ops = OrderedDict((k, o.put(f'ops/{k}.bin', v, note=rec.note.get(k))) for k, v in rec.v.items())
    s = dict(tp=D.TP, dim=m.dim, hd=m.hd, heads=m.heads, q_rank=1280, o_groups=m.groups, o_rank=m.o_rank,
             n_exp=m.n_exp, moe_ff=2304, hc=m.hc, ratio=m.ratio)
    LC.R_KV_SRC, LC.R_IDX_SRC = (lambda: m.kv_src), (lambda: m.idx_src)
    keep = {'wq_a', 'wq_a.scale', 'wkv', 'wkv.scale'} | {f'exp{e}.{w}{t}' for e in ids for w in ('w1', 'w3') for t in ('', '.scale')}
    for name, tensor, rows, cols in LC.die_slices(L, a.rank, s, ids, False):
        if name in keep:
            arr, dt = LC._raw(ck, tensor, rows, cols)
            o.put(f'weights/{name}.bin', arr, tensor=tensor, rows=rows, cols=cols, format=dt)
    meta = OrderedDict(schema=D.SCHEMA + '+reduced_fsgu', layer=f'L{L}', layer_index=L, kind=sj['kind'], context=D.CTX,
                       position=D.CTX - 1, seed=D.SEED, rank=a.rank, tp=D.TP, experts=ids, arith=V.ARITH,
                       fuse=sorted(V.FUSE), checks=checks,
                       shard=dict(path=str(shard), sha256=D.sha_b(shard.read_bytes()), input_sha256=sj['input_sha256'],
                                  output_sha256=sj['output_sha256']),
                       checkpoint=str(LC.HF), golden_init_sha256=init_sha, sources=D.src_pins(), tp_split=D.tp_split(m),
                       op_order=list(ops), reduced='a_proj + ffn.experts_gu inputs only (toksim_fsgu_ffnfix.py)',
                       command=f'HDC_V41_ARITH=chunk8 python3 tools/s81_dv/layer_prog/qf_producer/toksim_fsgu_ffnfix.py '
                               f'--layer {L} --out DIR')
    o.text('ops.json', json.dumps(ops, indent=1) + '\n')
    o.text('files.json', json.dumps(o.files, indent=1) + '\n')
    o.text('meta.json', json.dumps(meta, indent=1, default=str) + '\n')
    o.manifest()
    if a.compare:
        cf = json.loads((Path(a.compare) / 'files.json').read_text())
        bad = [k for k, v in o.files.items() if k not in cf or cf[k]['sha256'] != v['sha256']]
        print('COMPARE', a.compare, f'{len(o.files) - len(bad)}/{len(o.files)} files byte-identical', bad[:10])
        cm = json.loads((Path(a.compare) / 'meta.json').read_text())
        print('COMPARE tp_split', cm['tp_split'] == meta['tp_split'], 'experts', cm['experts'] == ids)
        if bad:
            return 1
    print('TOKSIM_FSGU_FFNFIX', f'L{L}', sj['kind'], ids, len(o.files), 'files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
