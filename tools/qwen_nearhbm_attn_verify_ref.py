#!/usr/bin/env python3
"""Verify-block vectors for the near-HBM attention successor (rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_vp.sv).

A speculative verify block holds p consecutive positions pos0 .. pos0+p-1 of one user.  Position i attends causally:
its context is T_i = pos0 + i + 1 rows of the layer's K/V (the block's own earlier rows included, its later rows not).
The golden of position i is tools/hdc_golden.py attention at context T_i, called through the parent reference's
golden_die (tools/qwen_nearhbm_attn_ref.py: matvec_il / attend at G = 6144, attn_splits (128, 512)), and each is also
asserted equal to the parent's partitioned scheme at T_i.  One K/V set of T_{p-1} rows is shared by every position.

    python3 tools/qwen_nearhbm_attn_verify_ref.py --ctx0 8189 --p 4 --seed 5 --kind normal --out DIR
writes kv.hex (T_{p-1} rows), q<i>.hex, gold<i>.hex and meta.json {ctx: [T_0 ..], p}.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import qwen_nearhbm_attn_ref as R

G = R.G


def write(ctx0, p, seed, kind, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ctx = [ctx0 + i for i in range(p)]
    if ctx[-1] > R.CTX_MAX:
        raise SystemExit("block exceeds the 8,192-position context")
    q0, K, V = R.make_case(ctx[-1], seed, kind)
    qs = [q0] + [R.make_case(1, seed + 7919 * i, kind)[0] for i in range(1, p)]
    golds = []
    for i, (q, T) in enumerate(zip(qs, ctx)):
        g = R.golden_die(q, K[:T], V[:T])
        assert R.same_bits(g, R.partitioned_die(q, K[:T], V[:T])), "partitioned reference disagrees with the golden"
        golds.append(g)
        qb = (G.bits(G.to_bf16(q)) >> 16).astype(np.uint32)
        (outdir / f"q{i}.hex").write_text("".join(f"{int(x):04x}\n" for x in qb.reshape(-1)))
        (outdir / f"gold{i}.hex").write_text("".join(f"{int(x):08x}\n" for x in G.bits(g).reshape(-1)))
    kb, vb = R.fp8_encode(K), R.fp8_encode(V)
    with open(outdir / "kv.hex", "w") as f:
        for arr in (kb, vb):
            for t in range(ctx[-1]):
                for gg in range(R.KVH):
                    f.write(bytes(arr[t, gg, ::-1]).hex() + "\n")
    # the mask matters: position i's golden differs from the unmasked (context T_{p-1}) attention whenever p > 1
    unmasked_differs = [bool(not R.same_bits(golds[i], R.golden_die(qs[i], K, V))) for i in range(p)]
    meta = dict(ctx=ctx, p=p, seed=seed, kind=kind, hd=R.HD,
                out_sha256=[hashlib.sha256(G.bits(g).tobytes()).hexdigest() for g in golds],
                unmasked_differs=unmasked_differs)
    (outdir / "meta.json").write_text(json.dumps(meta))
    print(json.dumps(meta))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ctx0", type=int, required=True, help="context of the block's first position (pos0 + 1)")
    ap.add_argument("--p", type=int, required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--kind", default="normal", choices=R.KINDS)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    write(a.ctx0, a.p, a.seed, a.kind, a.out)


if __name__ == "__main__":
    main()
