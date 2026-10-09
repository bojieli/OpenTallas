#!/usr/bin/env python3
"""hbm-indexer (Claude 2026-10-08): exact die-level bench of the real HBM indexer die blocks.

DUT: physical/hbm_accel_die_views/index/rtl/{hfd_idx_score (x4, one per HBM stack), hfd_idx_sel} connected by LEG-stage
relay chains in physical/hbm_accel_die_views/index/tb/tb_hfd_idx_die.sv.

Golden: tools/hdc_golden_v41.py through tools/rtl_hdc_v41x_idx_campaign.golden (Model.indexer's score lines, chunk8),
G.qdq_fp4_e8m0 (the query quantiser), topk_lowest_index (the local top-k, ties to the lower ID) and Model.candidate_blocks'
block-max / newest-pin rule (ot_hbm_accel_index_candidate, K 2048 >= the die's blocks).

Frames (one simulation, back to back, the blocks are reused):
  F0  layer-20 type: the RETAINED REAL encoded keys of rank 0 at 1M context (results/rtl/hbm_index_path_20261005/
      connected_29a9_r1/input/keys.mem, 10,928 keys = 4 full stacks), golden-quantised random query, candidates on;
  F1  layer-24 type: the same keys, a new query, keep bitmap (cand mask) on, candidates off;
  F2  partial die: golden-quantised random keys, rank 37, 4,100 keys (stack 0 full, stack 1 partial incl. a partial last
      beat, stacks 2-3 EMPTY), position = this rank's newest key (the newest block is pinned), candidates on;
  F3  fault path: 40 keys with one refused key (scale byte 253): the frame must end in fault.
Mutants (each must FAIL the comparison): MUT_LANE (two key lanes swapped), MUT_GID (rank stride off by one),
MUT_KEEP (cand mask ignored), MUT_SVAL (score LSB flip on stack 1 at the selector landing), MUT_QORD (top-k quarter
order 1,0,2,3).

  prepare  --work DIR             write lines.mem / qblk.mem / keep.mem / frames.txt + expected.json
  compare  --work DIR [--run R]   compare R/out_*.txt with the expected outputs -> verdict json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41x_idx_campaign as C  # noqa: E402  (sets chunk8)

F = np.float32
IH, NB = 32, 4
QK = 2736                      # keys a stack (342 blocks)
KEYS_MEM = ROOT / "results/rtl/hbm_index_path_20261005/connected_29a9_r1/input/keys.mem"


def qdq_codes(x):
    """G.qdq_fp4_e8m0 rows -> (codes, UE8M0 bytes) (same as tools/rtl_w11_idx_array.qdq_codes)."""
    x = np.asarray(x, dtype=F)
    shp = x.shape
    blk = x.reshape(-1, 32)
    amax = np.maximum(np.max(np.abs(blk), axis=1), G.FP4_AMAX_FLOOR_E8M0).astype(F)
    e = G._ceil_log2(G.mul(amax, G.FP4_MAX_INV)).astype(np.int64)
    v = G.qdq_fp4_e8m0(x.reshape(-1)).reshape(-1, 32).astype(np.float64)
    m = np.abs(v) * np.exp2(-e.astype(np.float64))[:, None]
    idx = np.minimum(np.searchsorted(C.E2M1, m), 7)
    assert np.array_equal(C.E2M1[idx], m)
    codes = idx + 8 * (v < 0)
    u = e + 127
    codes, u = codes.reshape(shp), u.reshape(shp[:-1] + (shp[-1] // 32,))
    assert np.array_equal(C.values(codes, u), v.reshape(shp).astype(F))
    return codes, u


def key_word(codes, u):
    w = 0
    for i, c in enumerate(codes):
        w |= int(c) << (4 * i)
    for b, s in enumerate(u):
        w |= int(s) << (512 + 8 * b)
    return w


def decode_key(w):
    codes = np.array([(w >> (4 * i)) & 15 for i in range(128)], dtype=np.int64)
    u = np.array([(w >> (512 + 8 * b)) & 255 for b in range(4)], dtype=np.int64)
    return codes, u


def real_keys():
    """Rank-0 keys of the retained 1M operands, ascending global ID -> [(gid, word)]."""
    out = []
    for ln in KEYS_MEM.read_text().split():
        v = int(ln, 16)
        if (v >> 566) & 1:
            out.append(((v >> 546) & ((1 << 20) - 1), v & ((1 << 544) - 1)))
    out.sort()
    return out


def gid_of(rank, k):
    return 8 * (96 * (k // 8) + rank) + (k % 8)


def query(rng):
    q = (rng.standard_normal((IH, NB * 32)) * 1.7).astype(F)
    lin = G.to_bf16((rng.standard_normal(IH) * 3.0).astype(F))
    w = G.to_bf16(G.mul(lin, F((NB * 32) ** -0.5 * IH ** -0.5)))
    return q, w


def qblocks(q, w):
    """VM FP32 query blocks {w16, data1024, blk2, head5}, head-major."""
    out = []
    for h in range(IH):
        wb = int(G.bits(F(w[h]))) >> 16
        for b in range(NB):
            data = 0
            for l in range(32):
                data |= int(G.bits(F(q[h, 32 * b + l]))) << (32 * l)
            out.append(h | (b << 5) | (data << 7) | (wb << 1031))
    return out


def bf16_val(bits):
    return float(np.frombuffer(np.uint32(int(bits) << 16).tobytes(), dtype=np.float32)[0])


def frame(name, rank, pos, words, q, w, keep_blocks, cand, keep_en, expfault=False):
    """words: die-local keys in order (k = 0..n-1).  Returns the frame record with golden expectations."""
    n = len(words)
    qc, qu = qdq_codes(q)
    qv = C.values(qc, qu)
    kc = np.zeros((n, 128), dtype=np.int64)
    ku = np.zeros((n, 4), dtype=np.int64)
    for i, wd in enumerate(words):
        kc[i], ku[i] = decode_key(wd)
    keep = np.ones(n, dtype=bool)
    if keep_en:
        keep = np.repeat(keep_blocks, 8)[:n]
    exp, bad = C.golden(qv, np.asarray(w, dtype=F), C.values(kc, ku), keep, qu, ku)
    gids = [gid_of(rank, k) for k in range(n)]
    rec = dict(name=name, rank=rank, pos=pos, n=n, cand_en=int(cand), keep_en=int(keep_en), expfault=int(expfault),
               n_fault_keys=int(bad.sum()))
    rec["scores"] = {str(g): int(e) for g, e in zip(gids, exp)}
    if not expfault:
        s = np.array([bf16_val(e) for e in exp], dtype=np.float64)
        s[~keep] = -np.inf
        sel = sorted(int(i) for i in G.topk_lowest_index(s, min(512, n)))
        rec["topk"] = [[gids[i], int(exp[i]) if keep[i] else 0xff80, int(not keep[i])] for i in sel]
        if cand:
            nb_ = -(-n // 8)
            cl = []
            for b in range(nb_):
                lo, hi = 8 * b, min(8 * b + 8, n)
                blk = gids[lo] >> 3
                vals = s[lo:hi]
                if blk == (pos >> 3):
                    cl.append([blk, 0x7f80])
                    continue
                if np.all(vals == -np.inf):
                    continue
                cl.append([blk, int(exp[lo + int(np.argmax(vals))])])
            rec["cand_list"] = cl
    return rec


def prepare(work: Path, seed=20261008):
    work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    lines, qbl, keepm, frames, meta = [], [], [], [], []
    real = real_keys()
    assert len(real) == 10928 and all(g == gid_of(0, k) for k, (g, _) in enumerate(real)), "keys.mem layout"
    real_words = [wd for _, wd in real]
    # synthetic keys (golden-quantised normal rows) for the partial / fault frames
    syn_c, syn_u = qdq_codes(rng.standard_normal((4100, 128)).astype(F))
    syn_words = [key_word(syn_c[i], syn_u[i]) for i in range(4100)]
    fault_words = list(syn_words[:40])
    c3, u3 = decode_key(fault_words[17])
    u3[2] = 253
    fault_words[17] = key_word(c3, u3)
    specs = []
    q0, w0 = query(rng)
    specs.append(("F0_L20_real_rank0_1M", 0, 1048575, real_words, q0, w0, None, True, False, False))
    q1, w1 = query(rng)
    kb = rng.random(1366) < 0.3
    specs.append(("F1_L24_real_rank0_keep", 0, 1048575, real_words, q1, w1, kb, False, True, False))
    q2, w2 = query(rng)
    specs.append(("F2_partial_rank37_pin", 37, gid_of(37, 4099), syn_words, q2, w2, None, True, False, False))
    q3, w3 = query(rng)
    specs.append(("F3_refused_key_fault", 5, gid_of(5, 39), fault_words, q3, w3, None, False, False, True))
    for fi, (name, rank, pos, words, q, w, kbl, cand, ken, ef) in enumerate(specs):
        rec = frame(name, rank, pos, words, q, w, kbl, cand, ken, ef)
        meta.append(rec)
        n = len(words)
        offs = []
        for st in range(4):
            nq = max(0, min(QK, n - QK * st))
            nl = 0 if nq == 0 else 8 * (-(-nq // 16))
            offs.append((len(lines), nl))
            for li in range(nl):
                pair = []
                for j in (0, 1):
                    k = QK * st + 2 * li + j
                    pair.append(words[k] if k < n else 0)
                lines.append(pair[0] | (pair[1] << 544))
        qoff = len(qbl)
        qbl += qblocks(q, w)
        for st in range(4):
            bits = 0
            if ken:
                for b in range(342):
                    if 342 * st + b < len(kbl) and kbl[342 * st + b]:
                        bits |= 1 << b
            keepm.append(bits)
        frames.append(f"{n} {rank} {pos} {int(cand)} {int(ken)} 512 {qoff} {int(ef)}\n"
                      + " ".join(f"{o} {nl}" for o, nl in offs))
    (work / "lines.mem").write_text("\n".join(f"{v:0272x}" for v in lines) + "\n")
    (work / "qblk.mem").write_text("\n".join(f"{v:0262x}" for v in qbl) + "\n")
    (work / "keep.mem").write_text("\n".join(f"{v:086x}" for v in keepm) + "\n")
    (work / "frames.txt").write_text(f"{len(frames)}\n" + "\n".join(frames) + "\n")
    (work / "expected.json").write_text(json.dumps(dict(seed=seed, frames=meta)))
    print(json.dumps([dict(name=m["name"], n=m["n"], topk=len(m.get("topk", [])), cand=len(m.get("cand_list", [])),
                           fault_keys=m["n_fault_keys"]) for m in meta]))


def compare(work: Path, run: Path):
    exp = json.loads((work / "expected.json").read_text())["frames"]
    res = dict(frames=[], pass_=True)
    fr_lines = {int(l.split()[0]): dict(kv.split("=") for kv in l.split()[1:])
                for l in (run / "out_frames.txt").read_text().splitlines() if l.strip()}
    sc, tk, cd = {}, {}, {}
    for l in (run / "out_scores.txt").read_text().splitlines():
        f, g, v, flt = l.split()
        sc.setdefault(int(f), []).append((int(g), int(v, 16), int(flt)))
    for l in (run / "out_topk.txt").read_text().splitlines():
        f, g, v, ni = l.split()
        tk.setdefault(int(f), []).append([int(g), int(v, 16), int(ni)])
    for l in (run / "out_cand.txt").read_text().splitlines():
        f, b, v = l.split()
        cd.setdefault(int(f), []).append([int(b), int(v, 16)])
    for fi, e in enumerate(exp):
        r = dict(name=e["name"], ok=True, why=[])
        fl = fr_lines.get(fi)
        if fl is None:
            r["ok"], r["why"] = False, ["frame not run"]
            res["frames"].append(r); res["pass_"] = False
            continue
        r["cycles"] = int(fl["cycles"]); r["first_score"] = int(fl["first_score"]); r["last_score"] = int(fl["last_score"])
        if e["expfault"]:
            if fl["fault"] != "1":
                r["ok"] = False; r["why"].append("expected fault not raised")
        else:
            if fl["done"] != "1" or fl["fault"] != "0":
                r["ok"] = False; r["why"].append(f"done={fl['done']} fault={fl['fault']}")
            got = sc.get(fi, [])
            want = e["scores"]
            seen = set()
            bad = 0
            for g, v, flt in got:
                if str(g) not in want or g in seen or want[str(g)] != v or flt:
                    bad += 1
                seen.add(g)
            if bad or len(seen) != len(want):
                r["ok"] = False; r["why"].append(f"scores: {bad} bad, {len(seen)}/{len(want)} keys")
            r["scores_checked"] = len(got)
            # top-k: ordered list, values compared as BF16 numbers (+0 == -0), ninf flag
            gt = tk.get(fi, [])
            wt = e["topk"]
            same = len(gt) == len(wt) and all(a[0] == b[0] and a[2] == b[2] and
                                              (a[2] or bf16_val(a[1]) == bf16_val(b[1])) for a, b in zip(gt, wt))
            if not same:
                r["ok"] = False; r["why"].append(f"topk: got {len(gt)} want {len(wt)}; first diff "
                                                 f"{next(([i, a, b] for i, (a, b) in enumerate(zip(gt, wt)) if a != b), None)}")
            r["topk_checked"] = len(gt)
            if e["cand_en"]:
                gc, wc = cd.get(fi, []), e["cand_list"]
                same = len(gc) == len(wc) and all(a[0] == b[0] and bf16_val(a[1]) == bf16_val(b[1]) for a, b in zip(gc, wc))
                if not same:
                    r["ok"] = False; r["why"].append(f"cand: got {len(gc)} want {len(wc)}")
                r["cand_checked"] = len(gc)
        res["pass_"] &= r["ok"]
        res["frames"].append(r)
    res["verdict"] = "PASS" if res.pop("pass_") else "FAIL"
    print(json.dumps(res, indent=1))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["prepare", "compare"])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--run", type=Path)
    a = ap.parse_args()
    if a.mode == "prepare":
        prepare(a.work)
    else:
        r = compare(a.work, a.run or a.work)
        (Path(a.run or a.work) / "verdict.json").write_text(json.dumps(r, indent=1))
        return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
