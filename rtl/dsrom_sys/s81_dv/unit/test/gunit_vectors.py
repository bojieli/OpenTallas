#!/usr/bin/env python3
"""S81U-1: golden vectors for dsdv_gunit from tools/hdc_golden_v41 (R-ARITH chunk8).

Per case, $readmemh words:
  router  scale, 448 bias, 448 scores, K ids, K weights        (Model.moe's router lines, verbatim golden ops)
  hc      25 x 16 x 2 x 6 HP root words (acc, slice g, half h, word j), 24 bases, 3 scales, eps, 24 coefficients
The HC coefficients are Model.hc_mixes itself (full-K csum, rsqrt, sigmoid, exp, Sinkhorn) on a random BF16 residual
and fn; the HP roots are an INDEPENDENT slice model: chunk sums of 8 sequential from +0, then for slice g / copy k the
pairwise-tree roots of the maximal aligned subtrees of chunks [640 k + 40 g, + 40), sizes by g mod 4."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as g   # noqa: E402

g.set_arith('chunk8')
F = np.float32
NE, NEMAX, K = 384, 448, 6
D, HC, NO = 5120, 4, 24
KF = HC * D
SIZES = [[32, 8], [8, 16, 16], [16, 16, 8], [8, 32]]


def u32(x):
    return int(np.asarray(x, dtype=F).view(np.uint32))


def router_case(rng, kind):
    s = np.abs(rng.standard_normal(NE)).astype(F) * F(1.3)
    b = (rng.standard_normal(NE) * 0.05).astype(F)
    if kind == 1:            # ties on the biased score (lower index must win)
        s[:] = F(0.5); b[:] = F(0)
        b[rng.choice(NE, 10, replace=False)] = F(0.25)
    elif kind == 2:          # many equal scores, some zeros
        s[rng.choice(NE, 100, replace=False)] = F(0)
        s[rng.choice(NE, 60, replace=False)] = F(1.0)
        b[:] = F(0.0)
    scale = F([1.0, 2.5, 1.5, 0.75][rng.integers(4)])
    chosen = g.topk_lowest_index(g.add(s, b), K)
    ids = sorted(int(i) for i in chosen)
    den = g.add(g.seqsum([s[i] for i in ids]), F(1e-20))
    w = [g.mul(g.div(s[i], den), scale) for i in ids]
    words = [u32(scale)] + [u32(x) for x in b] + [0] * (NEMAX - NE) + [u32(x) for x in s] + [0] * (NEMAX - NE)
    return words + ids + [u32(x) for x in w]


def chunk_sums(t):
    """[..., KF] terms -> [..., KF / 8] chunk sums, each sequential from +0 (golden add)."""
    t = t.reshape(t.shape[:-1] + (KF // 8, 8))
    acc = np.zeros(t.shape[:-1], dtype=F)
    for i in range(8):
        acc = g.add(acc, t[..., i])
    return acc


def block(cs, c0, n):
    v = cs[..., c0:c0 + n]
    while v.shape[-1] > 1:
        v = g.add(v[..., 0::2], v[..., 1::2])
    return v[..., 0]


def hc_case(rng, kind):
    x = g.to_bf16((rng.standard_normal((HC, D)) * [1.0, 4.0, 0.25, 16.0][kind % 4]).astype(F))
    fn = (rng.standard_normal((NO, KF)) * 0.02).astype(F)
    scale = (rng.uniform(0.2, 2.0, 3)).astype(F)
    base = (rng.standard_normal(NO) * 0.5).astype(F)
    eps = F([1e-20, 1e-6][kind % 2])
    lw = {'hc_attn_fn': fn, 'hc_attn_scale': scale, 'hc_attn_base': base}
    m = SimpleNamespace(eps=eps, hc_eps=F(1e-6), hc=HC, sinkhorn_iters=20, lw=lambda L, n: lw[n])
    pre, post, comb = g.Model.hc_mixes(m, x, 0, 'attn')
    coef = np.concatenate([pre, post, comb.reshape(-1)]).astype(F)
    flat = x.reshape(-1)
    terms = np.concatenate([g.mul(fn, flat[None, :]), g.mul(flat, flat)[None, :]])     # acc 0..23 fn rows, 24 ss
    cs = chunk_sums(terms)
    words = []
    for a in range(25):
        for sl in range(16):
            for h in range(2):
                wd = [0] * 6
                for kk in range(2):
                    k = 2 * h + kk
                    c0 = 640 * k + 40 * sl
                    for j, n in enumerate(SIZES[sl % 4]):
                        wd[3 * kk + j] = u32(block(cs[a], c0, n))
                        c0 += n
                words += wd
    # self-check: the independent roots finish to the golden csum (top tree: level-5 groups, then csum of 80 nodes)
    root = []
    for a in range(25):
        l5 = [block(cs[a], 32 * i, 32) for i in range(80)]
        root.append(g.csum(np.array(l5, dtype=F), c=1))
    assert np.array_equal(np.array(root[:24], dtype=F).view(np.uint32), g.csum(terms[:24]).view(np.uint32))
    return words + [u32(v) for v in base] + [u32(v) for v in scale] + [u32(eps)] + [u32(v) for v in coef]


def main():
    out, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    rng = np.random.default_rng(seed)
    with open(out, 'w') as f:
        for c in range(n):
            for wd in router_case(rng, c % 3) + hc_case(rng, c):
                f.write(f'{wd:08x}\n')


if __name__ == '__main__':
    main()
