#!/usr/bin/env python3
"""Golden vectors for the P.V pair bench (tb_qwen_tp8_pv_wide_pair): one pair's partial at TP8 (s_pv = 256).

Pair p owns chunks c' = 128p + c (c = 0..127), chunk = rows t with t mod 256 = c', summed SEQUENTIALLY in increasing t
from +0 (exact BF16(e) x FP8(V) products, tools/hdc_golden.py add/mul), then the 7-level pairwise tree over c: exactly
the pair-level part of matvec_il(V^T, bf16(e), 256) (tools/qwen_attention_native/minparent_1015/fix_r3/ref_intermediates.py
p0/p1). 4 heads x 128 dims. Writes v.hex (T rows, 1024 b, dim 0 at the LSB byte), e.hex (T x {e3,e2,e1,e0} BF16) and
gold.hex (512 FP32 words, head-major) for one pair.
    pv_pair_ref.py --ctx T --pair P --seed S --out DIR"""
import argparse, os, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_SU_WIDTH", "8")
import hdc_golden as G  # noqa: E402
import qwen_nearhbm_attn_ref as R  # noqa: E402
F = np.float32


def tree(parts):
    parts = list(parts)
    while len(parts) > 1:
        parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx", type=int, required=True); ap.add_argument("--pair", type=int, required=True)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    T, p = a.ctx, a.pair
    rng = np.random.default_rng(a.seed)
    V = G.to_fp8((rng.standard_normal((T, 128)) * 2.0).astype(F))
    V[rng.random(V.shape) < 0.02] = F(0)
    e = G.to_bf16(np.exp(-np.abs(rng.standard_normal((T, 4)) * 3.0)).astype(F))
    e[rng.random(e.shape) < 0.01] = F(0)
    leaves = []
    for c in range(128):
        acc = np.zeros((4, 128), dtype=F)
        for t in range(128 * p + c, T, 256):
            for h in range(4):
                acc[h] = G.add(acc[h], G.mul(V[t], e[t, h]))
        leaves.append(acc)
    gold = tree(leaves)
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    vb = R.fp8_encode(V)
    (o / "v.hex").write_text("".join(bytes(vb[t][::-1]).hex() + "\n" for t in range(T)))
    eb = (G.bits(e) >> 16).astype(np.uint32)
    (o / "e.hex").write_text("".join("".join("%04x" % eb[t, h] for h in (3, 2, 1, 0)) + "\n" for t in range(T)))
    (o / "gold.hex").write_text("".join("%08x\n" % w for w in G.bits(gold).reshape(-1)))
    print(f"PV_PAIR_REF T={T} pair={p} rows={sum(1 for t in range(T) if (t >> 7) & 1 == p)}")


if __name__ == "__main__":
    main()
