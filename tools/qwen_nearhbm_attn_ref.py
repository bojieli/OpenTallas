#!/usr/bin/env python3
"""Near-HBM attention for the Qwen3-8B ROM die (TP4): the PARTITIONED exact scheme, and its proof against the golden.

One die holds 8 query heads and 2 KV heads (GQA 4), head_dim 128, FP8 E4M3 KV.  The golden attention is
tools/hdc_golden.py decode_token_tp: per head
    sc  = mul(matvec_il(K, bf16(q), s_sc), F(1/sqrt(128)))         s_sc = 128 at G = 6144
    out = attend(sc, V, s_pv)                                        s_pv = 512 at G = 6144
          = mul(matvec_il(V^T, bf16(e), 512), reciprocal(reduce_chunked(e))),  e = exp(sc - max(sc))

The partitioned scheme (what rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_{stack,hub}.sv compute):
  * KV position t lives in HBM stack s = (t mod 512) div 128.  Round k = t div 512, local residue r = t mod 128.
  * K pass (stack): every score in golden order (product per d, 7-level pairwise tree, x scale), stored; local max.
  * hub: M_h = max over the 4 stacks' local maxima (order-free), broadcast back.
  * exp pass (stack): e = exp(s - M) in FP32; bf16(e) stored for P.V; Z per 128-position block (k, s): the 16
    contiguous 8-position chunks summed sequentially from +0, then the 4-level pairwise tree -> block sum.
  * V pass (stack): P.V chunk c = 128 s + r: positions t = c (mod 512) in increasing t, sequentially from +0
    (exact BF16 x FP8 products); the 7-level pairwise tree over the stack's 128 residues -> S_s.
  * hub: Z = pairwise tree over the 64 blocks b = 4 k + s (zeros for empty blocks) = Z tree levels 5..10;
    P.V = (S_0 + S_1) + (S_2 + S_3) = P.V tree levels 8..9; out = P.V x reciprocal(Z).
Every padding element is +0 and every summand is >= +0 or the sum it pads is never -0 (the adders canonicalise),
so x + 0 = x and the zero-padded trees equal the golden's.  This file proves it bit for bit on random cases and
writes the RTL bench's vectors.

    python3 tools/qwen_nearhbm_attn_ref.py prove --cases 400 --out results/.../exactness.json
    python3 tools/qwen_nearhbm_attn_ref.py vectors --ctx 8192 --seed 1 --kind normal --out DIR
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_SU_WIDTH", "8")          # the vector stream unit: R-ARITH reduce_chunked, FP8 KV
import hdc_golden as G  # noqa: E402

F = G.F
NH, KVH = 8, 2                     # per die at TP4
HD = int(os.environ.get("NHB_HD", "128"))   # 128 is Qwen3-8B; a smaller HD is a DEBUG vehicle only (see below)
GQ = NH // KVH                     # 4 query heads per KV head
GROUPS = 6144                      # model-r3 baseline lane groups per die
if HD == 128:
    S_SC, S_PV = G.attn_splits(HD, GROUPS)
    assert (S_SC, S_PV) == (128, 512), (S_SC, S_PV)
else:                              # debug: the same golden functions with the splits the hardware uses
    S_SC, S_PV = HD, 512
STACKS = 4
RES = S_PV // STACKS               # 128 residues per stack
CTX_MAX = 8192
SCALE = F(1.0 / np.sqrt(HD))       # 0x3DB504F3 -- NOT 0.25: the golden's comment "0.25: exact" holds for hd = 16 only
assert HD != 128 or int(G.bits(SCALE)) == 0x3DB504F3


# -- golden (verbatim calls into tools/hdc_golden.py) -------------------------------------------------------------
def golden_die(q, K, V):
    """q [NH, HD] float32 (rounded to BF16 here, as decode_token_tp does); K, V [T, KVH, HD] FP8-valued float32."""
    out = np.zeros((NH, HD), dtype=F)
    for h in range(NH):
        g = h // GQ
        sc = G.mul(G.matvec_il(K[:, g, :], G.to_bf16(q[h]), S_SC), SCALE)
        out[h] = G.attend(sc, V[:, g, :], S_PV)
    return out


# -- partitioned scheme ---------------------------------------------------------------------------------------------
def tree(parts):
    """pairwise tree ((p0 + p1) + (p2 + p3)) over a power-of-two list"""
    parts = list(parts)
    assert len(parts) & (len(parts) - 1) == 0
    while len(parts) > 1:
        parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


def stack_positions(s, T):
    return [t for t in range(T) if (t % S_PV) // RES == s]


def scores_stack(q, K, s, T):
    """K pass of stack s: {t: [NH] scores} in golden order (tree over d of exact products, then x SCALE)."""
    qb = G.to_bf16(q)                                     # [NH, HD]
    pos = np.array(stack_positions(s, T), dtype=np.int64)
    out = {}
    if len(pos) == 0:
        return out, None
    sc = np.zeros((len(pos), NH), dtype=F)
    for h in range(NH):
        g = h // GQ
        prods = G.add(F(0), G.mul(K[pos, g, :], qb[h][None, :]))      # chunk d = +0 + product   [P, HD]
        sc[:, h] = G.mul(tree([prods[:, d] for d in range(HD)]), SCALE)
    for i, t in enumerate(pos):
        out[int(t)] = sc[i]
    return out, sc.max(axis=0)                          # local max (order-free)


def exp_pass_stack(sc, M, s, T):
    """e (FP32) for the stack's positions, and the Z block sums {k: [NH]} (chunk chains + levels 1-4)."""
    e = {t: G.exp(G.add(v, G.neg(M))) for t, v in sc.items()}
    blocks = {}
    for k in range((T + S_PV - 1) // S_PV):
        base = S_PV * k + RES * s
        if base >= T:
            continue
        chunks = []
        for c in range(RES // 8):
            acc = np.zeros(NH, dtype=F)
            for i in range(8):
                t = base + 8 * c + i
                if t < T:
                    acc = G.add(acc, e[t])
            chunks.append(acc)
        blocks[k] = tree(chunks)                        # 16 chunks -> levels 1..4
    return e, blocks


def pv_stack(V, e, s, T):
    """P.V partial of stack s: [NH, HD] = 7-level tree over its 128 residues of the sequential chunk sums."""
    leaves = []
    for r in range(RES):
        c = RES * s + r
        acc = np.zeros((NH, HD), dtype=F)
        for t in range(c, T, S_PV):
            eb = G.to_bf16(e[t])                       # [NH]
            for h in range(NH):
                acc[h] = G.add(acc[h], G.mul(V[t, h // GQ, :], eb[h]))
        leaves.append(acc)
    return tree(leaves)


MUTANT = None   # negative controls: "pv_fold" sequential hub P.V fold; "z_seq" stack-order Z fold


def hub(maxes, blocks, pvs, T):
    nblk = CTX_MAX // RES                               # 64 blocks b = 4 k + s
    zl = [np.zeros(NH, dtype=F)] * nblk
    for s in range(STACKS):
        for k, v in blocks[s].items():
            zl[STACKS * k + s] = v
    Z = tree(zl)                                        # Z levels 5..10
    pv = G.add(G.add(pvs[0], pvs[1]), G.add(pvs[2], pvs[3]))        # P.V levels 8..9
    if MUTANT == "pv_fold":
        pv = G.add(G.add(G.add(pvs[0], pvs[1]), pvs[2]), pvs[3])
    if MUTANT == "z_seq":                                # each stack's blocks summed first, then the stacks
        Z = G.add(G.add(tree(zl[0::4]), tree(zl[1::4])), G.add(tree(zl[2::4]), tree(zl[3::4])))
    return G.mul(pv, G.reciprocal(Z)[:, None]), Z


def partitioned_die(q, K, V, return_parts=False):
    T = K.shape[0]
    sc, lmax = zip(*[scores_stack(q, K, s, T) for s in range(STACKS)])
    M = np.max(np.stack([m for m in lmax if m is not None]), axis=0).astype(F)
    eb = [exp_pass_stack(sc[s], M, s, T) for s in range(STACKS)]
    pvs = [pv_stack(V, eb[s][0], s, T) for s in range(STACKS)]
    out, Z = hub(lmax, [b for _, b in eb], pvs, T)
    if return_parts:
        return out, dict(M=M, Z=Z, pvs=pvs, lmax=lmax, blocks=[b for _, b in eb])
    return out


# -- FP8 E4M3 encoding (bytes as HBM holds them) ------------------------------------------------------------------
def fp8_table():
    """value of every E4M3 byte (bias 7, no inf; 0x7F/0xFF NaN excluded)"""
    v = np.zeros(256, dtype=np.float64)
    for b in range(256):
        s, e, m = b >> 7, (b >> 3) & 15, b & 7
        mag = (m / 8.0) * 2.0 ** -6 if e == 0 else (1 + m / 8.0) * 2.0 ** (e - 7)
        v[b] = -mag if s else mag
    return v


FP8_VAL = fp8_table()


def fp8_encode(x):
    """FP8-valued float32 -> byte (the golden never makes -0; +0 -> 0x00)"""
    x = np.asarray(x, dtype=F)
    lut = {float(FP8_VAL[b]): b for b in range(256) if b not in (0x7F, 0xFF, 0x80)}
    flat = [lut[float(v)] for v in x.reshape(-1)]
    return np.array(flat, dtype=np.uint8).reshape(x.shape)


# -- random cases ---------------------------------------------------------------------------------------------------
KINDS = ("normal", "peaky", "flat", "wide", "tiny", "mixed")


def make_case(T, seed, kind):
    rng = np.random.default_rng(seed)
    if kind == "normal":
        qs, ks, vs = 2.0, 1.0, 1.0
    elif kind == "peaky":          # a few huge scores: exp underflows to the clamp for most positions
        qs, ks, vs = 30.0, 8.0, 4.0
    elif kind == "flat":           # all scores nearly equal
        qs, ks, vs = 1e-3, 1e-3, 1.0
    elif kind == "wide":           # saturating FP8 (448) and large q
        qs, ks, vs = 200.0, 300.0, 300.0
    elif kind == "tiny":           # FP8 subnormals and BF16 tiny / -0 q
        qs, ks, vs = 1e-30, 0.01, 0.01
    else:
        qs, ks, vs = 10.0 ** rng.uniform(-3, 2), 10.0 ** rng.uniform(-2, 2.5), 10.0 ** rng.uniform(-2, 2.5)
    q = (rng.standard_normal((NH, HD)) * qs).astype(F)
    K = G.to_fp8((rng.standard_normal((T, KVH, HD)) * ks).astype(F))
    V = G.to_fp8((rng.standard_normal((T, KVH, HD)) * vs).astype(F))
    # sprinkle exact zeros, -0 in q, and a few repeated rows (ties in the max)
    q[rng.random((NH, HD)) < 0.03] = F(0)
    neg0 = rng.random((NH, HD)) < 0.03
    q[neg0] = F(-0.0)
    if kind == "tiny":
        q[rng.random((NH, HD)) < 0.2] = F(-1e-41)        # rounds to BF16 -0 / subnormal
    K[rng.random(K.shape) < 0.02] = F(0)
    V[rng.random(V.shape) < 0.02] = F(0)
    if T > 4:
        for _ in range(3):
            a, b = rng.integers(0, T, 2)
            K[a] = K[b]
    return q, K, V


def same_bits(a, b):
    return np.array_equal(G.bits(a), G.bits(b))


def prove(n_cases, out_path, seed0=1000):
    fixed = [1, 2, 3, 7, 8, 9, 15, 16, 17, 63, 64, 65, 127, 128, 129, 255, 256, 383, 384, 385, 511, 512, 513,
             640, 1000, 1023, 1024, 1025, 1536, 2047, 2048, 2049, 3000, 4095, 4096, 4097, 5000, 6143, 6144,
             7000, 8191, 8192]
    rng = np.random.default_rng(seed0)
    ctxs = fixed + [int(x) for x in rng.integers(1, CTX_MAX + 1, max(0, n_cases - len(fixed)))]
    rows, fails = [], 0
    mutant_exact = {"pv_fold": 0, "z_seq": 0}
    t0 = time.time()
    for i, T in enumerate(ctxs):
        kind = KINDS[i % len(KINDS)]
        q, K, V = make_case(T, seed0 + i, kind)
        g = golden_die(q, K, V)
        p, parts = partitioned_die(q, K, V, return_parts=True)
        ok = same_bits(g, p)
        fails += (not ok)
        global MUTANT
        mut = {}
        for m in ("pv_fold", "z_seq"):
            MUTANT = m
            mut[m] = bool(same_bits(g, partitioned_die(q, K, V)))
            MUTANT = None
        for m, v in mut.items():
            mutant_exact[m] += v
        e_min = None
        rows.append(dict(ctx=T, seed=seed0 + i, kind=kind, bit_exact=bool(ok),
                         out_sha256=hashlib.sha256(G.bits(g).tobytes()).hexdigest()[:16],
                         Z_min=float(np.min(parts["Z"])), Z_max=float(np.max(parts["Z"])),
                         nonfinite=int((~np.isfinite(g)).sum()), mutants_exact=mut))
        print(f"[{i + 1}/{len(ctxs)}] ctx={T} kind={kind} exact={ok} ({time.time() - t0:.0f}s)", flush=True)
    rec = dict(schema="qwen-nearhbm-attn-partition-exactness.v1", golden="tools/hdc_golden.py",
               golden_sha256=hashlib.sha256((ROOT / "tools/hdc_golden.py").read_bytes()).hexdigest(),
               reference="tools/qwen_nearhbm_attn_ref.py",
               reference_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               shape=dict(q_heads=NH, kv_heads=KVH, head_dim=HD, stacks=STACKS, groups=GROUPS,
                          attn_splits=[S_SC, S_PV], scale_bits=hex(int(G.bits(SCALE))), kv="FP8 E4M3"),
               cases=len(rows), failures=fails, verdict="PASS" if fails == 0 else "FAIL",
               negative_controls=dict(cases_where_mutant_was_still_exact=mutant_exact,
                                      note="a wrong reduction order must be caught: pv_fold = ((S0+S1)+S2)+S3 at the hub; "
                                           "z_seq = each stack's blocks summed first, then the stacks"),
               rows=rows)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("cases", "failures", "verdict", "negative_controls")}))
    return fails == 0


# -- bench vectors --------------------------------------------------------------------------------------------------
def write_vectors(T, seed, kind, outdir):
    """hex files for the Verilator bench: q (BF16), K/V bytes, the golden out and the intermediate checkpoints"""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    q, K, V = make_case(T, seed, kind)
    g = golden_die(q, K, V)
    p, parts = partitioned_die(q, K, V, return_parts=True)
    assert same_bits(g, p), "partitioned reference disagrees with the golden"
    qb = (G.bits(G.to_bf16(q)) >> 16).astype(np.uint32)
    kb, vb = fp8_encode(K), fp8_encode(V)
    with open(outdir / "q.hex", "w") as f:                 # NH*HD lines, h-major
        f.writelines(f"{int(x):04x}\n" for x in qb.reshape(-1))
    # KV: one line per (t, g): 128 bytes, byte d at bits [8d +: 8]
    with open(outdir / "kv.hex", "w") as f:
        for arr in (kb, vb):
            for t in range(T):
                for gg in range(KVH):
                    f.write(bytes(arr[t, gg, ::-1]).hex() + "\n")
    with open(outdir / "gold.hex", "w") as f:
        f.writelines(f"{int(x):08x}\n" for x in G.bits(g).reshape(-1))
    with open(outdir / "check.hex", "w") as f:            # M[8], Z[8]
        f.writelines(f"{int(x):08x}\n" for x in np.concatenate([G.bits(parts["M"]), G.bits(parts["Z"])]))
    meta = dict(ctx=T, seed=seed, kind=kind, hd=HD, out_sha256=hashlib.sha256(G.bits(g).tobytes()).hexdigest())
    (outdir / "meta.json").write_text(json.dumps(meta))
    print(json.dumps(meta))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("prove")
    a.add_argument("--cases", type=int, default=200)
    a.add_argument("--seed", type=int, default=1000)
    a.add_argument("--out")
    b = sub.add_parser("vectors")
    b.add_argument("--ctx", type=int, required=True)
    b.add_argument("--seed", type=int, default=1)
    b.add_argument("--kind", default="normal", choices=KINDS)
    b.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "prove":
        sys.exit(0 if prove(args.cases, args.out, args.seed) else 1)
    write_vectors(args.ctx, args.seed, args.kind, args.out)


if __name__ == "__main__":
    main()
