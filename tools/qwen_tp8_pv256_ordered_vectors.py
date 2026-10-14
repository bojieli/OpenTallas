#!/usr/bin/env python3
"""Full-context product merge proof, not a composed attention throughput gate."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import qwen_nearhbm_attn_ref as R


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rtl-leaves', type=Path)
    args = ap.parse_args()
    G = R.G
    R.NH, R.KVH, R.GQ, R.GROUPS = 4, 1, 4, 3072
    R.S_SC, R.S_PV = G.attn_splits(128, 3072)
    assert (R.S_SC, R.S_PV) == (128, 256)
    ctx = 8192  # position8191, including the newly committed KV row.
    q, k, v = R.make_case(ctx, 1, 'normal')
    products = np.zeros((4, ctx, 128), dtype=np.float32)
    den = []
    exp_bf16 = np.zeros((ctx, 4), dtype=np.uint16)
    for h in range(4):
        scores = G.mul(G.matvec_il(k[:, 0, :], G.to_bf16(q[h]), 128), R.SCALE)
        e = G.exp(G.add(scores, G.neg(scores.max())))
        den.append(G.lane_sum(e))
        exp_bf16[:, h] = (G.bits(G.to_bf16(e)) >> 16).astype(np.uint16)
        products[h] = G.mul(v[:, 0, :], G.to_bf16(e)[:, None])
    leaves = np.zeros((4, 256, 128), dtype=np.float32)
    map_rows = []
    for c in range(256):
        seq = list(range(c, ctx, 256))
        for i, t in enumerate(seq):
            stack = (t % 512) // 128
            assert stack == (c // 128) + 2 * (i % 2)
            assert t == 512 * (t // 512) + 128 * stack + t % 128
            leaves[:, c] = G.add(leaves[:, c], products[:, t])
            map_rows.append([c, i, t, stack, t // 512, t % 128])
    def finish(ls):
        while ls.shape[1] > 1:
            ls = G.add(ls[:, 0::2], ls[:, 1::2])
        return G.mul(ls[:, 0], G.reciprocal(np.array(den))[:, None])
    golden = R.golden_die(q, k, v)
    assert np.array_equal(G.bits(finish(leaves)), G.bits(golden))
    args.out.mkdir(parents=True, exist_ok=True)
    G.bits(products).astype('<u4').tofile(args.out / 'products.bin')
    G.bits(leaves).astype('<u4').tofile(args.out / 'leaves.bin')
    R.fp8_encode(v[:, 0]).tofile(args.out / 'v-fp8.bin')
    exp_bf16.astype('<u2').tofile(args.out / 'exp-bf16.bin')
    (args.out / 'ownership.json').write_text(json.dumps(map_rows) + '\n')
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.is_file()}
    report = dict(context=ctx, position=ctx-1, query_heads=4, kv_heads=1, hd=128,
                  splits=[128, 256], denominator_chunk=G.CHUNK,
                  products=4*ctx*128, vector_products=4*ctx*8,
                  cross_stack_product_vectors=4*ctx*8//2,
                  cross_stack_product_bits=4*ctx*128*32//2,
                  invocations=4*256*8, files=files,
                  scope='ORDERED_PRODUCT_MERGE_ONLY; PRODUCT_MULTIPLY_AND_PHYSICAL_TRANSPORT_NOT_IN_THIS_RTL',
                  arithmetic_source_sha256=hashlib.sha256(Path(G.__file__).read_bytes()).hexdigest(),
                  reference_source_sha256=hashlib.sha256(Path(R.__file__).read_bytes()).hexdigest())
    if args.rtl_leaves:
        actual = np.fromfile(args.rtl_leaves, dtype='<u4').reshape(4, 256, 128).view(np.float32)
        report['rtl_leaf_mismatches'] = int((G.bits(actual) != G.bits(leaves)).sum())
        report['normalized_output_mismatches'] = int((G.bits(finish(actual)) != G.bits(golden)).sum())
        assert report['rtl_leaf_mismatches'] == report['normalized_output_mismatches'] == 0
    (args.out / 'receipt.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
