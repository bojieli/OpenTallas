#!/usr/bin/env python3
"""hbm-forks (2026-10-09, REVIEW_20261009 review-0400 R4 condition 1): the 8-entry-point attention split.

Rule (both goldens, no golden change): the positions of one attention row (Qwen: 0 .. P-1; DS: the selected rows in the
golden's index order) are cut into the R-ARITH chunks of 8 (hdc_golden_v41.csum), the chunk count padded to a power of two
NP, and pair g (g = 0..7) owns the CONTIGUOUS ALIGNED block of NP/8 chunks [g*NP/8, (g+1)*NP/8) (when NP < 8: blocks of
one chunk, pairs >= NP idle).  Each pair computes its block's partial Z and p.v with the same chunk-8 chains and the
pairwise tree of its block; the 8 partials merge in pair order by the tree's top log2(min(8, NP)) levels:
((P0+P1)+(P2+P3))+((P4+P5)+(P6+P7)).  Because every block is an aligned subtree of the golden's padded pairwise tree,
the merged result equals csum over all positions bit for bit.  The global row max (needed before exp) is order-free
(a max), so pass 1 merges maxima in any order.  The compiler lays block g's rows into PC group g of every stack (rows
channel-major per chunk block), so ATT pair g consumes ks<g> with no reorder hardware.

Checks (random FP32 incl. cancellation, +-0, subnormals; P = 1 .. 9000 incl. 8,192 and DS 2,048 selected rows):
  PASS  merge in pair order == csum(all)                (Z and every p.v column)
  FAIL  mutant: pairs 1 and 2 merged swapped            (must differ on some case)
  FAIL  mutant: interleaved assignment (chunk c -> pair c mod 8, in-pair tree, then the 8-way merge)
Prints ATT8_SPLIT PASS / FAIL; writes results/rtl/hbm_forks_20261009/att8_split_check.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as V  # noqa: E402
import hdc_golden as G  # noqa: E402

F = np.float32
C = 8


def chunk_sums(t):
    n = t.shape[-1]
    nc = max(1, -(-n // C))
    t = np.concatenate([t, np.zeros(t.shape[:-1] + (nc * C - n,), F)], -1).reshape(t.shape[:-1] + (nc, C))
    acc = np.zeros(t.shape[:-1], F)
    for i in range(C):
        acc = V.add(acc, t[..., i])
    return acc


def tree(acc):
    while acc.shape[-1] & (acc.shape[-1] - 1):
        acc = np.concatenate([acc, np.zeros(acc.shape[:-1] + (1,), F)], -1)
    while acc.shape[-1] > 1:
        acc = V.add(acc[..., 0::2], acc[..., 1::2])
    return acc[..., 0]


def split8(t, mode='aligned', swap=False):
    cs = chunk_sums(t)
    nc = cs.shape[-1]
    NP = 1 << (nc - 1).bit_length() if nc > 1 else 1
    cs = np.concatenate([cs, np.zeros(cs.shape[:-1] + (NP - nc,), F)], -1)
    G = min(8, NP)
    if mode == 'aligned':
        blocks = [cs[..., g * (NP // G):(g + 1) * (NP // G)] for g in range(G)]
    else:                                  # mutant: interleaved chunk -> pair assignment
        blocks = [cs[..., g::G] for g in range(G)]
    parts = [tree(b) for b in blocks]
    if swap and G >= 3:
        parts[1], parts[2] = parts[2], parts[1]
    return tree(np.stack(parts, -1))


def aligned_pieces(a, b):
    """maximal aligned power-of-two subtrees covering chunk range [a, b)"""
    out = []
    while a < b:
        k = 0
        while (a % (1 << (k + 1)) == 0) and a + (1 << (k + 1)) <= b:
            k += 1
        out.append((a, a + (1 << k)))
        a += 1 << k
    return out


def balanced(t, swap=False):
    """BALANCED runs: pair g owns chunks [g*nc//8, (g+1)*nc//8) (contiguous, +-1 chunk), computes the sums of the maximal
    aligned subtrees inside its run (its partials), and the merge evaluates the golden tree taking those nodes from the
    partials (padding leaves +0).  Exact by construction; this checks the decomposition."""
    cs = chunk_sums(t)
    nc = cs.shape[-1]
    NP = 1 << (nc - 1).bit_length() if nc > 1 else 1
    part = {}
    for g in range(8):
        a, b = g * nc // 8, (g + 1) * nc // 8
        for (x, y) in aligned_pieces(a, b):
            part[(x, y)] = tree(cs[..., x:y])
    keys = sorted(part)
    if swap and len(keys) >= 2:
        part[keys[0]], part[keys[1]] = part[keys[1]], part[keys[0]]
    zero = np.zeros(cs.shape[:-1], F)

    def node(x, y):
        if (x, y) in part:
            return part[(x, y)]
        if x >= nc:
            return zero
        m = (x + y) // 2
        return V.add(node(x, m), node(m, y))
    return node(0, NP), max((g + 1) * nc // 8 - g * nc // 8 for g in range(8)), nc


def rnd(rng, shape):
    x = (rng.standard_normal(shape) * np.exp2(rng.integers(-30, 30, shape))).astype(F)
    x[rng.random(shape) < 0.02] = F(0.0)
    x[rng.random(shape) < 0.01] = F(-0.0)
    x[rng.random(shape) < 0.01] = F(1e-40)
    return x


def main():
    rng = np.random.default_rng(20261009)
    sizes = [1, 7, 8, 9, 63, 64, 65, 100, 513, 1000, 2048, 2049, 4095, 8192, 9000]
    res, bad, mut_swap, mut_il, mut_bal, load, mut_lmax = [], 0, 0, 0, 0, [], 0
    for P in sizes:
        for trial in range(3):
            sc = (rng.standard_normal(P) * 6).astype(F)      # raw scores (scaled q.k)
            mx = sc.max()                                    # GLOBAL row max (order-free; merged across the 8 pairs)
            e = G.exp(V.add(sc, -mx))
            # mutant: each pair subtracts its LOCAL max (no cross-pair max merge) -> e differs
            nc_ = max(1, -(-P // C)); runs = [(g * nc_ // 8 * C, min(P, (g + 1) * nc_ // 8 * C)) for g in range(8)]
            el = np.concatenate([G.exp(V.add(sc[a:b], -sc[a:b].max())) for a, b in runs if b > a]) if P > 0 else e
            mut_lmax += int(V.csum(el).view(np.uint32) != V.csum(e).view(np.uint32))
            v = rnd(rng, (16, P))                            # 16 p.v columns
            pv = V.mul(e[None, :], v)
            want = np.concatenate([[V.csum(e)], V.csum(pv)])
            got = np.concatenate([[split8(e)], split8(pv)])
            ok = np.array_equal(got.view(np.uint32), want.view(np.uint32))
            sw = np.concatenate([[split8(e, swap=True)], split8(pv, swap=True)])
            il = np.concatenate([[split8(e, 'interleaved')], split8(pv, 'interleaved')])
            mut_swap += int(not np.array_equal(sw.view(np.uint32), want.view(np.uint32)))
            mut_il += int(not np.array_equal(il.view(np.uint32), want.view(np.uint32)))
            bz, bmax, nc = balanced(e)
            bpv = np.stack([balanced(pv[j])[0] for j in range(pv.shape[0])])
            bok = np.array_equal(np.concatenate([[bz], bpv]).view(np.uint32), want.view(np.uint32))
            bs = np.concatenate([[balanced(e, swap=True)[0]], np.stack([balanced(pv[j], swap=True)[0] for j in range(16)])])
            mut_bal += int(not np.array_equal(bs.view(np.uint32), want.view(np.uint32)))
            bad += int(not bok)
            NPc = 1 << (nc - 1).bit_length() if nc > 1 else 1
            load.append(dict(P=P, chunks=nc, aligned_max_chunks=-(-NPc // 8), balanced_max_chunks=bmax,
                             aligned_eff=round(nc / (8 * -(-NPc // 8)), 3), balanced_eff=round(nc / (8 * bmax), 3)) if trial == 0 else None)
            bad += int(not ok)
            res.append(dict(P=P, trial=trial, exact=bool(ok)))
    verdict = 'PASS' if bad == 0 and mut_swap > 0 and mut_il > 0 and mut_bal > 0 and mut_lmax > 0 else 'FAIL'
    load = [x for x in load if x]
    out = dict(schema='opentallas.hgi_att8_split.v1', rule=__doc__.split('Checks')[0].strip(), cases=len(res),
               mismatches=bad, mutant_swap_detected_cases=mut_swap, mutant_interleaved_detected_cases=mut_il, mutant_balanced_swap_detected_cases=mut_bal, mutant_local_max_detected_cases=mut_lmax, per_pair_load=load,
               verdict=verdict, sizes=sizes)
    p = ROOT / 'results/rtl/hbm_forks_20261009/att8_split_check.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1) + '\n')
    print(f'ATT8_SPLIT {verdict} cases={len(res)} mismatches={bad} mut_swap={mut_swap} mut_interleaved={mut_il} mut_balanced={mut_bal} mut_local_max={mut_lmax}')
    for x in load: print(x)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
