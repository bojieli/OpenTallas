#!/usr/bin/env python3
"""Vectors for tb_hgi_coll_tkm (hgi-1010/k): the hardware COLL.TOPK_MERGE merge sink (ot_hgi_coll_ep TKM = 1).

Golden = tools/hgi_sim/machine.py u_coll_topk_merge, verbatim: over the group's concatenated (value, id) lists (rank order),
top = lexsort((id, -value))[:k], then re-ordered by ascending id (stable); O = ids, R = values (FP32 bits); NaN faults.

    python3 tools/hgi_coll_tkm_vectors.py --out DIR [--export EXPDIR]

Cases (one directory each: cfg.hex, a.hex / b.hex = every rank's A / B, rank-major, NMAX words a rank; o.hex / r.hex =
the expected O / R):
  prod_sel_L<l>_k<rec>   production DS indexer selection (G 96, n 512, k 512), from an hgi_e2e export (coll_<rec>.bin /
                         collb_<rec>.bin: every rank's real IDX.INDEX output);
  prod_cand_L20_k<rec>   production DS layer-20 candidate merge (G 96, n 1,366, k 2,048, values + R), same source;
  syn_sel / syn_cand     production-shaped synthetic stand-ins (BF16 index scores of the DS distribution, owned-key ids);
  edge cases             small groups (G 1 / 2 / 4 / 8), n not a multiple of 8, ties (few distinct values), +-0 / +-inf,
                         duplicate ids across ranks, k > G n, adversarial ascending arrival, a NaN (must fault).
cfg.hex words: G, n, k, rank (this die), has_r, nout, expect_fault, abase, bbase, obase, rbase, seed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

NMAX = 2048


def golden(vals, ids):
    """vals: list per rank of float32 arrays; ids: list per rank of uint32 arrays -> (O ids, R value bits) or None (NaN)"""
    v = np.concatenate([np.asarray(x, np.float32).astype(np.float64) for x in vals])
    i = np.concatenate([np.asarray(x, np.int64) for x in ids])
    if np.isnan(v).any():
        return None
    return v, i


def topk(vals, ids, k):
    g = golden(vals, ids)
    if g is None:
        return None, None
    v, i = g
    top = np.lexsort((i, -v))[:k]
    top = top[np.argsort(i[top], kind="stable")]
    return i[top].astype(np.uint32), v[top].astype(np.float32).view(np.uint32)


def bf16(x):
    b = np.asarray(x, np.float32).view(np.uint32).astype(np.uint64)
    return ((b + 0x7FFF + ((b >> 16) & 1)) >> 16 << 16).astype(np.uint32).view(np.float32)


def owned_ids(q, nkeys, G, count, rng, block=8):
    blocks = np.arange(q, -(-nkeys // block), G)
    idx = (blocks[:, None] * block + np.arange(block)[None, :]).reshape(-1)
    idx = idx[idx < nkeys]
    return np.sort(rng.choice(idx, size=count, replace=False)).astype(np.uint32)


def write_case(out: Path, name, G, n, k, rank, vals, ids, has_r, seed=0, expect_fault=None, M=0):
    """n = the largest per-rank count (vals / ids may be shorter per rank); M = the record's param[11:0] (0 = own n)"""
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    o, r = topk(vals, ids, k)
    fault = o is None if expect_fault is None else expect_fault
    ns = [len(x) for x in vals]
    nout = min(k, sum(ns))
    abase, bbase, obase, rbase = 0x20000, 0x10000, 0x30000, 0x34000
    cfg = [G, n, k, rank, int(has_r), nout, int(fault), abase, bbase, obase, rbase, seed, M]
    (d / "n.hex").write_text("".join(f"{x:08x}\n" for x in ns))
    (d / "cfg.hex").write_text("".join(f"{x:08x}\n" for x in cfg))
    a = np.zeros((G, NMAX), np.uint32)
    b = np.zeros((G, NMAX), np.uint32)
    for q in range(G):
        a[q, :ns[q]] = np.asarray(vals[q], np.float32).view(np.uint32)
        b[q, :ns[q]] = np.asarray(ids[q], np.uint32)
    (d / "a.hex").write_text("".join(f"{x:08x}\n" for x in a.reshape(-1)))
    (d / "b.hex").write_text("".join(f"{x:08x}\n" for x in b.reshape(-1)))
    oo = np.zeros(NMAX, np.uint32)
    rr = np.zeros(NMAX, np.uint32)
    if not fault:
        oo[:nout] = o
        rr[:nout] = r
    (d / "o.hex").write_text("".join(f"{x:08x}\n" for x in oo))
    (d / "r.hex").write_text("".join(f"{x:08x}\n" for x in rr))
    return dict(name=name, G=G, n=n, ns=sorted(set(ns)), M=M, k=k, rank=rank, has_r=bool(has_r), nout=nout, fault=bool(fault))


def from_export(out, exp: Path, rank):
    meta = json.loads((exp / "meta.json").read_text())
    cases = []
    for r in meta["records"]:
        if r["unit"] != "COLL" or r["op"] != "TOPK_MERGE":
            continue
        k = r["k"]
        fa, fb = exp / f"coll_{k}.bin", exp / f"collb_{k}.bin"
        if not fb.exists():
            continue
        G = meta["group"]
        A = np.fromfile(fa, "<u4").view(np.float32).reshape(G, -1)
        B = np.fromfile(fb, "<u4").reshape(G, -1)
        n = A.shape[1]
        hdr = bytes.fromhex(r["hdr"])[::-1]
        imm_a = int.from_bytes(hdr[4:8], "little")
        has_r = "R" in r["eff"]
        kind = "cand" if has_r else "sel"
        cases.append(write_case(out, f"prod_{kind}_L{meta['layer']}_k{k}", G, n, imm_a, rank,
                                list(A), list(B), has_r, seed=k))
    return cases


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--export", type=Path, action="append", default=[], help="hgi_e2e export dir (repeatable)")
    ap.add_argument("--rank", type=int, default=0)
    ap.add_argument("--values", type=Path, help="production sel values (coll_<k>.bin) for syn_sel")
    a = ap.parse_args()
    rng = np.random.default_rng(20261010)
    cases = []
    for e in a.export:
        cases += from_export(a.out, e, a.rank)
    G = 96
    # production-shaped synthetic selection: BF16 scores (the DS indexer's narrow range: ~190 distinct values)
    if a.values and a.values.exists():
        V = np.fromfile(a.values, "<u4").view(np.float32).reshape(G, -1)
    else:
        V = bf16(np.abs(rng.normal(1.2, 0.15, (G, 512)))).astype(np.float32)
    ids = [owned_ids(q, 524288, G, 512, rng) for q in range(G)]
    cases.append(write_case(a.out, "syn_sel", G, 512, 512, a.rank, list(V), ids, False, seed=1))
    cases.append(write_case(a.out, "syn_sel_r", G, 512, 512, 37, list(V), ids, True, seed=2))
    # production-shaped candidate merge: block maxima sorted (value desc, id asc) per rank, the newest block +inf
    nb = 1366
    cv, ci = [], []
    for q in range(G):
        blocks = np.arange(q, 131072 + 2 * G, G)[:nb].astype(np.int64)
        s = bf16(rng.normal(1.0, 0.4, len(blocks))).astype(np.float64)
        if q == (131071 % G):
            s[np.argmax(blocks)] = np.inf
        o = np.lexsort((blocks, -s))
        cv.append(s[o].astype(np.float32))
        ci.append(blocks[o].astype(np.uint32))
    cases.append(write_case(a.out, "syn_cand", G, nb, 2048, a.rank, cv, ci, True, seed=3))
    # adversarial arrival: values ascending with the element index (every element survives the filter)
    av = [np.float32(np.arange(512) * 96 + q) for q in range(G)]
    cases.append(write_case(a.out, "adv_ascending", G, 512, 512, a.rank, av, ids, True, seed=4))
    # edge cases on small groups
    def rnd_vals(n, kind):
        if kind == "ties":
            return rng.choice(np.array([0.0, 1.0, 2.0, -1.0], np.float32), size=n)
        if kind == "zinf":
            return rng.choice(np.array([0.0, -0.0, 1.0, -np.inf, np.inf, -2.0], np.float32), size=n)
        return bf16(rng.normal(0, 4, n)).astype(np.float32)
    for Gs in (1, 2, 4, 8):
        for (n, k, kind, hr) in ((13, 5, "ties", True), (64, 64, "zinf", True), (100, 2048, "bf16", True),
                                 (37, 1, "ties", False), (512, 300, "bf16", True)):
            vals = [rnd_vals(n, kind) for _ in range(Gs)]
            idl = [rng.permutation(4096)[:n].astype(np.uint32) for _ in range(Gs)]
            rk = int(rng.integers(0, 96)) if Gs == 96 else int(rng.integers(0, 96)) // Gs * Gs + int(rng.integers(0, Gs))
            cases.append(write_case(a.out, f"g{Gs}_n{n}_k{k}_{kind}", Gs, n, k, rk, vals, idl, hr, seed=Gs * 1000 + n))
    # duplicate ids across ranks (same value, ids repeated; +-0 pairs with the same id)
    vals = [np.array([0.0, -0.0, 1.0, 1.0, -0.0, 0.0, 2.0, 2.0], np.float32) for _ in range(4)]
    idl = [np.array([5, 5, 7, 7, 9, 9, 3, 3], np.uint32) for _ in range(4)]
    cases.append(write_case(a.out, "g4_dup_ids", 4, 8, 11, 2, vals, idl, True, seed=11))
    # G 96, n not a multiple of 8, k > G n
    vals = [rnd_vals(21, "ties") for _ in range(G)]
    idl = [rng.permutation(1 << 20)[:21].astype(np.uint32) for _ in range(G)]
    cases.append(write_case(a.out, "g96_n21_kall", G, 21, 2048, 50, vals, idl, True, seed=12))
    # unequal per-rank n (the DS candidate merge at other contexts: 341 / 342 owned blocks); one flit count (pf 43)
    nsx = [342 if q < 40 else 341 for q in range(G)]
    vals = [bf16(rng.normal(0, 1, m)).astype(np.float32) for m in nsx]
    idl = [owned_ids(q, 32768 * 8, G, m, rng) for q, m in zip(range(G), nsx)]
    cases.append(write_case(a.out, "g96_unequal_341_342", G, 342, 2048, 60, vals, idl, True, seed=14))
    # unequal ceil(n / 8): needs param M (the group's largest n); the DUT has the short list
    nsx = [130 if q % 3 else 121 for q in range(8)]
    vals = [rnd_vals(m, "ties") for m in nsx]
    idl = [rng.permutation(1 << 16)[:m].astype(np.uint32) for m in nsx]
    cases.append(write_case(a.out, "g8_unequal_M130", 8, 130, 200, 3, vals, idl, True, seed=15, M=130))
    # a NaN with the canonical-NaN payload and a negative NaN (both fault; the pad marker is not data)
    vals = [rnd_vals(16, "bf16") for _ in range(8)]
    vals[1][2] = np.uint32(0xFFFFFFFF).view(np.float32)       # in the DUT's own list (rank 1)
    idl = [rng.permutation(4096)[:16].astype(np.uint32) for _ in range(8)]
    cases.append(write_case(a.out, "g8_negnan_fault", 8, 16, 8, 1, vals, idl, True, seed=16))
    # NaN: must fault
    vals = [rnd_vals(16, "bf16") for _ in range(8)]
    vals[3][5] = np.float32(np.nan)
    idl = [rng.permutation(4096)[:16].astype(np.uint32) for _ in range(8)]
    cases.append(write_case(a.out, "g8_nan_fault", 8, 16, 8, 1, vals, idl, True, seed=13))
    # write-port phase: the final partial O line lands one cell after a full line (cells % 4 == 1) and must not
    # share the single write edge with the previous line's R write; cover every cells % 4 phase (appended last so
    # every earlier case keeps its random stream)
    for (Gs, n, k) in ((1, 20, 17), (1, 20, 20), (2, 9, 18), (1, 24, 21), (1, 30, 25), (1, 32, 32)):
        vals = [rnd_vals(n, "bf16") for _ in range(Gs)]
        idl = [rng.permutation(4096)[:n].astype(np.uint32) for _ in range(Gs)]
        cases.append(write_case(a.out, f"port_g{Gs}_n{n}_k{k}", Gs, n, k, Gs - 1, vals, idl, True, seed=20 + n))
    (a.out / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(f"{len(cases)} cases -> {a.out}")


if __name__ == "__main__":
    main()
