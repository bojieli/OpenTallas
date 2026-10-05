#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM EDGE INDEX SCORER: bit-exact campaign (Verilator 5.050).

The unit (rtl/dsrom_sys/ot_dsrom_idx_edge.sv, default-off) scans each HBM stack's index keys beside its service
strip, keeps the stack's exact top-512 in a streamed fold (ot_dsrom_edge_lsel) and merges the four stacks' lists by
position in the hub (ot_dsrom_edge_hub).  The golden is tools/hdc_golden_v41.py:

    s   = Model.indexer's scores (to_bf16(dots_q4), ReLU x head weight, reduce_rows, to_bf16; candidate mask -inf)
    sel = sorted(topk_lowest_index(s, min(512, n)))

Benches
  select   rtl/test/dsrom_sys/tb_dsrom_edge_select.sv: the four per-stack selectors + hub, driven with BF16 score
           streams at the HBM stack rate (11 keys/cycle per stack = 0.9 TB/s at 1.2 GHz, 68 B keys), checked
           against the golden selection.  Cases: tie-heavy random (the select campaign's alphabet: +-0, +-inf,
           subnormals, few distinct values), real reduced-vehicle index scores scaled to the shipped context, the
           layer-20 full scan at 200K and 1M positions (50,000 and 262,144 compressed keys, ratio 4), all-equal,
           ascending (every score survives: worst-case fold throughput), descending, candidate-masked (-inf
           outside 2,048 blocks), uneven stack fills (n not a multiple of 64), n < K, n = K +- 1, n = 0 and 1.
  score    rtl/test/dsrom_sys/tb_dsrom_idx_edge.sv: the full unit, keys in, positions out: the qualified score
           slices (ot_hdc_v41x_idx_score_slice_l at the 1.2 GHz latencies FPL 7 / FML 5 / QL 5) on every stack,
           against the golden's own score lines (tools/rtl_hdc_v41x_idx_campaign.golden) then the selection.

Writes results/rtl/dsrom_edge_scorer_20261003/<bench>.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402

OUT = ROOT / "results/rtl/dsrom_edge_scorer_20261003"
VERILATOR = os.environ.get("VERILATOR", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
K, LI, W, IW, LO = 512, 16, 64, 20, 16
RATE = 11                     # keys/cycle/stack: 0.9 TB/s / 68 B / 1.2 GHz = 11.03
SEL_RTL = ["rtl/dsrom_sys/ot_dsrom_edge_lsel.sv", "rtl/dsrom_sys/ot_dsrom_edge_merge.sv",
           "rtl/dsrom_sys/ot_dsrom_edge_hub.sv", "rtl/hdc/v41/ot_hdc_tselect.sv"]
SEL_TB = "rtl/test/dsrom_sys/tb_dsrom_edge_select.sv"
HARNESS = "rtl/test/dsrom_sys/dsrom_edge_harness.cpp"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def dirty(paths) -> list:
    r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", *paths], capture_output=True, text=True)
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


# -- golden -------------------------------------------------------------------------------------------------
def bits16(v):
    return (np.asarray(v, np.float32).view(np.uint32) >> 16).astype(np.int64)


def golden_select(vals):
    """sorted(topk_lowest_index(s, min(K, n))) -- the indexer's own line."""
    v = np.asarray(vals, np.float64)
    if len(v) == 0:
        return []
    return sorted(int(i) for i in G.topk_lowest_index(v, min(K, len(v))))


def boundaries(n):
    """Frozen block8-aligned writer/reader layout; changing N needs migration."""
    groups = (n + 7) // 8
    return np.minimum(n, 8 * (np.arange(5) * groups // 4))


def stack_of(p, n=None):
    if n is None:
        return (np.asarray(p) >> 4) & 3
    return np.searchsorted(boundaries(n)[1:], np.asarray(p), side="right")


# -- vectors -------------------------------------------------------------------------------------------------
def query_beats(vals_bits, contiguous=False):
    """Per stack: list of (last, lv, [(val, pos)] * LI), stack-local ascending, valid prefix per beat."""
    n = len(vals_bits)
    pos = np.arange(n)
    st = stack_of(pos, n if contiguous else None)
    out = []
    for s in range(4):
        ps = pos[st == s]
        beats = []
        for b in range(0, len(ps), LI):
            chunk = ps[b:b + LI]
            beats.append(chunk)
        if not beats:
            beats = [np.array([], dtype=np.int64)]
        rows = []
        for i, chunk in enumerate(beats):
            lanes = [(int(vals_bits[p]), int(p)) for p in chunk] + [(0, 0)] * (LI - len(chunk))
            rows.append((int(i == len(beats) - 1), (1 << len(chunk)) - 1, lanes))
        out.append(rows)
    return out


def write_queries(d: Path, queries, contiguous=False):
    """queries: list of float arrays (score values, BF16-exact).  Writes S0..S3 and EXP."""
    fs = [open(d / f"s{s}.txt", "w") for s in range(4)]
    fe = open(d / "exp.txt", "w")
    nexp = 0
    for vals in queries:
        b = bits16(vals)
        for s, rows in enumerate(query_beats(b, contiguous)):
            f = fs[s]
            f.write(f"Q {len(rows)}\n")
            for last, lv, lanes in rows:
                f.write(f"{last} {lv:x}" + "".join(f" {v:x} {p:x}" for v, p in lanes) + "\n")
        sel = golden_select(vals)
        fe.write(f"Q {len(sel)}\n")
        for p in sel:
            fe.write(f"{p:x} {int(b[p]):x}\n")
        nexp += len(sel)
    for f in fs + [fe]:
        f.close()
    return nexp


def bf16(x):
    return G.to_bf16(np.asarray(x, np.float32)).astype(np.float64)


def alphabet_values(rng, n):
    """Tie-heavy BF16 scores: a few distinct values incl. +-0, +-inf, subnormals, extremes."""
    pool = np.array([0.0, -0.0, np.inf, -np.inf, 1.0, -1.0, 2.0, 0.5, 3.0e38, -3.0e38, 1e-40, -1e-40,
                     1.5, 1.0078125, 65504.0, -2.0], np.float64)
    k = int(rng.integers(2, len(pool) + 1))
    sub = rng.choice(pool, k, replace=False)
    sub = sub[~np.isnan(sub)]
    v = rng.choice(sub, n)
    if rng.random() < 0.5:                         # sprinkle raw BF16 values
        m = rng.random(n) < 0.3
        raw = rng.integers(0, 1 << 16, n)
        raw = raw[(raw & 0x7F80) != 0x7F80] if False else raw
        f = G.from_bits((raw << 16).astype(np.uint32)).astype(np.float64)
        f = np.where(np.isnan(f), 0.0, f)
        v = np.where(m, f, v)
    return bf16(v)


def random_scores(rng, n):
    """Index-score-like BF16: ReLU x weights sums, positive-heavy with zeros."""
    v = rng.standard_normal(n) * rng.choice([0.1, 1.0, 30.0])
    v = np.where(rng.random(n) < 0.15, 0.0, v)
    return bf16(v)


def real_arrays(cache: Path | None):
    """The reduced DeepSeek-V4.1 vehicle's real index scores (every indexer call), from the select campaign."""
    import pickle
    import rtl_hdc_v41_select_campaign as SC
    if cache and cache.exists():
        sets = pickle.loads(cache.read_bytes())[0]
    else:
        sets = SC.real_sets(SC.REAL_POSITIONS)
        if cache:
            cache.write_bytes(pickle.dumps((sets, None, None)))
    arrays = [np.asarray(v, np.float64) for v, _, _ in sets["index"]]
    return [a[np.isfinite(a)] for a in arrays if np.isfinite(a).any()]


def scaled(rng, arrays, n):
    out, have = [], 0
    while have < n:
        a = arrays[int(rng.integers(len(arrays)))]
        out.append(a)
        have += len(a)
    return np.concatenate(out)[:n] if n else np.zeros(0)


def candidate_masked(rng, base, n):
    nb = -(-n // 8)
    keep = np.zeros(nb, bool)
    keep[rng.choice(nb, min(nb, 2048), replace=False)] = True
    keep[nb - 1] = True
    return np.where(np.repeat(keep, 8)[:n], base, -np.inf)


# -- build / run ---------------------------------------------------------------------------------------------
def build(work: Path, tb: str, srcs, top: str, params: dict, jobs: int = 8) -> Path:
    obj = work / f"obj_{top}"
    gp = [f"-G{k}={v}" for k, v in params.items()]
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", top,
           f"-CFLAGS", f"-DEDGE_TOPH=\\\"V{top}.h\\\" -DEDGE_TOP=V{top} -O1", "-j", str(jobs), "--Mdir", str(obj), *gp,
           str(ROOT / tb), *[str(ROOT / s) for s in srcs], str(ROOT / HARNESS)]
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout[-4000:] + r.stderr[-4000:])
        raise SystemExit("verilator build failed")
    print(f"built {top} in {time.time() - t:.0f}s", flush=True)
    return obj / f"V{top}"


QRE = re.compile(r"EDGEQ q=(\d+) n=(\d+) start=(-?\d+) first=(-?\d+) last_in=(-?\d+),(-?\d+),(-?\d+),(-?\d+) "
                 r"cand_last=(-?\d+),(-?\d+),(-?\d+),(-?\d+) out=(-?\d+) errors=(\d+)")
SRE = re.compile(r"EDGEST q=(\d+) folds=([\d,]+) pass=([\d,]+) lines=([\d,]+) stall=([\d,]+)")


def run_select(binary: Path, d: Path, rate=RATE, bubble=0, seed=1):
    args = [str(binary)] + [f"+S{s}={d / f's{s}.txt'}" for s in range(4)] + [
        f"+EXP={d / 'exp.txt'}", f"+RATE={rate}", f"+BUBBLE={bubble}", f"+SEED={seed}"]
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True)
    out = r.stdout + r.stderr
    (d / f"run_rate{rate}_bubble{bubble}_seed{seed}.log").write_text(out)
    rows = {}
    for m in QRE.finditer(out):
        q = int(m.group(1))
        g = [int(x) for x in m.groups()]
        rows[q] = dict(selected=g[1], cyc_start=g[2], cyc_first=g[3], last_in=g[4:8], cand_last=g[8:12],
                       cyc_out=g[12], errors=g[13])
    for m in SRE.finditer(out):
        q = int(m.group(1))
        rows.setdefault(q, {}).update(folds=[int(x) for x in m.group(2).split(",")],
                                      passed=[int(x) for x in m.group(3).split(",")],
                                      lines=[int(x) for x in m.group(4).split(",")],
                                      stall=[int(x) for x in m.group(5).split(",")])
    done = re.search(r"EDGEDONE queries=(\d+) errors=(\d+)", out)
    mism = [ln for ln in out.splitlines() if "MISMATCH" in ln or "fatal" in ln.lower() or "Error" in ln][:12]
    return dict(rc=r.returncode, done=bool(done), queries=int(done.group(1)) if done else None,
                errors=int(done.group(2)) if done else None, rows=rows, mismatch_lines=mism,
                wall_s=round(time.time() - t, 1))


def derived(row, n):
    """Cycle accounting of one query."""
    li = max(row["last_in"])
    return dict(n_keys=n, scan_cycles=li - row["cyc_first"] + 1,
                keys_per_cycle_die=round(n / max(1, li - row["cyc_first"] + 1), 3),
                last_key_to_stack_lists=max(row["cand_last"]) - li,
                last_key_to_selection_out=row["cyc_out"] - li)


def select_cases(rng, arrays, quick=False):
    """(name, scores) cases.  n = compressed keys (positions / 4 at the scanning layers)."""
    cases = []
    for n in (0, 1, 2, 15, 16, 17, 63, 64, 65, 511, 512, 513, 1000, 2047, 2048, 2049, 4097):
        cases.append((f"edge_n{n}", alphabet_values(rng, n)))
    for i in range(6 if quick else 40):
        n = int(rng.choice([rng.integers(1, 600), rng.integers(500, 5000), rng.integers(4000, 40000)]))
        cases.append((f"ties_{i}_n{n}", alphabet_values(rng, n)))
    for i in range(3 if quick else 12):
        n = int(rng.integers(1, 30000))
        cases.append((f"random_{i}_n{n}", random_scores(rng, n)))
    n = 20000
    cases.append(("all_equal_n20000", np.full(n, 1.0)))
    cases.append(("all_zero_signed_n20000", np.where(rng.random(n) < 0.5, 0.0, -0.0)))
    cases.append(("ascending_n20000", bf16(np.arange(n, dtype=np.float64))))      # every score survives
    cases.append(("descending_n20000", bf16(-np.arange(n, dtype=np.float64))))
    cases.append(("all_neg_inf_n3000", np.full(3000, -np.inf)))
    cases.append(("neg_inf_but_100_n5000", np.where(rng.random(5000) < 0.02, 1.0, -np.inf)))
    cases.append(("ties_at_threshold_n9000",
                  np.where(np.arange(9000) % 7 == 0, 2.0, np.where(np.arange(9000) % 3 == 0, 1.0, 0.5))))
    if arrays:
        for i in range(2 if quick else 8):
            n = int(rng.integers(512, 1 << 16))
            cases.append((f"real_scaled_{i}_n{n}", scaled(rng, arrays, n)))
    return cases


def shipped_cases(rng, arrays):
    """The layer-20 full scan: ratio 4, 200K and 1M positions."""
    out = []
    for ctx in (200000, 1048576):
        n = ctx // 4
        base = scaled(rng, arrays, n) if arrays else random_scores(rng, n)
        out.append((f"l20_full_scan_ctx{ctx}_n{n}", base))
        out.append((f"l20_ties_ctx{ctx}_n{n}", alphabet_values(rng, n)))
        out.append((f"reuse_masked_ctx{ctx}_n{n}", candidate_masked(rng, base, n)))
    out.append(("ascending_ctx1048576_n262144", bf16(np.arange(262144, dtype=np.float64))))
    return out


def bench_select(args):
    work = Path(args.work) / "select"
    work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    arrays = [] if args.no_real else real_arrays(Path(args.real_cache) if args.real_cache else None)
    binary = build(work, SEL_TB, SEL_RTL, "tb_dsrom_edge_select", dict(LI=LI, IW=IW, K=K, CONTIGUOUS=int(args.contiguous)), jobs=args.jobs)
    rec = dict(schema="opentallas.dsrom-edge-select.v1", bench=SEL_TB, golden="tools/hdc_golden_v41.py "
               "sorted(topk_lowest_index(s, min(512, n))) on the BF16 index scores", groups={})
    ok = True
    groups = [("functional", select_cases(rng, arrays, args.quick))]
    if not args.quick:
        groups.append(("shipped", shipped_cases(rng, arrays)))
    for gname, cases in groups:
        d = work / gname
        d.mkdir(exist_ok=True)
        nexp = write_queries(d, [v for _, v in cases], args.contiguous)
        modes = [("hbm_rate", RATE, 0, 1)] + ([("bubbles", RATE, 30, 7), ("mac_rate", 0, 0, 3)]
                                                if gname == "functional" else [])
        grec = dict(cases=len(cases), expected_positions=nexp, modes={})
        for mode, rate, bub, seed in modes:
            r = run_select(binary, d, rate, bub, seed)
            per = []
            for qi, (name, v) in enumerate(cases):
                row = r["rows"].get(qi)
                if row is None:
                    per.append(dict(case=name, missing=True))
                    continue
                per.append(dict(case=name, **derived(row, len(v)), errors=row["errors"],
                                folds=row.get("folds"), passed=row.get("passed"), stall=row.get("stall")))
            mp = bool(r["done"] and r["errors"] == 0 and r["queries"] == len(cases) and r["rc"] == 0)
            ok &= mp
            grec["modes"][mode] = dict(rate_keys_per_cycle_per_stack=rate or "every cycle (16)",
                                       bubble_percent=bub, seed=seed, passed=mp, errors=r["errors"],
                                       queries=r["queries"], wall_s=r["wall_s"], mismatch_lines=r["mismatch_lines"],
                                       per_case=per)
            print(gname, mode, "pass" if mp else "FAIL", r["errors"], r["queries"], r["wall_s"], flush=True)
        rec["groups"][gname] = grec
    rec["pass"] = bool(ok)
    return rec


# -- the full stack element: score slices + streamed top-K ------------------------------------------------------
STK_RTL = ["rtl/dsrom_sys/ot_dsrom_edge_layout.sv", "rtl/dsrom_sys/ot_dsrom_idx_edge.sv", "rtl/dsrom_sys/ot_dsrom_edge_lsel.sv",
           "rtl/hdc/v41/ot_hdc_tselect.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv",
           "rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx.sv",
           "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_delay.sv",
           "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv",
           "rtl/dsrom_sys/ot_dsrom_edge_merge.sv", "rtl/dsrom_sys/ot_dsrom_edge_hub.sv"]
STK_TB = "rtl/test/dsrom_sys/tb_dsrom_edge_stack.sv"
STRE = re.compile(r"STQ q=(\d+) beats=(\d+) start=(-?\d+) first=(-?\d+) last=(-?\d+) cand=(-?\d+) folds=(\d+) "
                  r"pass=(\d+) stall=(\d+) fault=(\d+)")


def idx_tools():
    import rtl_hdc_v41x_idx_campaign as IC
    return IC


def make_token(rng, n, cls, nb=4, ih=32):
    """A token of n keys: the idx campaign's random classes, or golden-quantised normal vectors ('normal')."""
    IC = idx_tools()
    if cls != "normal":
        return IC.finish(IC.rand_token(rng, ih, nb, n, cls))
    ihd = nb * 32
    q = G.qdq_fp4_e8m0(rng.standard_normal((ih, ihd)).astype(np.float32)).reshape(ih, ihd)
    kk = rng.standard_normal((n, ihd)).astype(np.float32) * np.exp(rng.standard_normal((n, 1)) * 0.5).astype(np.float32)
    keys = G.qdq_fp4_e8m0(kk).reshape(n, ihd)          # per 32-block, the golden's own line
    qc, qu = IC.to_codes(q)
    kc, ku = IC.to_codes(keys)
    w = G.to_bf16(rng.standard_normal(ih).astype(np.float32) * np.float32(0.1))
    tok = dict(qc=qc, qu=qu, w=w, kc=kc, ku=ku, keep=np.ones(n, bool), cls=cls)
    return IC.finish(tok)


def write_stack(d: Path, toks, s, nb=4, ih=32, contiguous=False):
    """The stack-s files of tb_dsrom_edge_stack for a list of tokens.  Returns (nbeat, ncand, per-token info)."""
    IC = idx_tools()
    d.mkdir(parents=True, exist_ok=True)
    ql, nl, kl, el, cl, info = [], [], [], [], [], []
    layout_lines = []
    for t in toks:
        n = len(t["keep"])
        for h in range(ih):
            f = [(c, 4) for c in t["qc"][h]] + [(u, 8) for u in t["qu"][h]] + [(int(G.bits(t["w"][h])) >> 16, 16)]
            ql.append(IC.hexline(f))
        pos = np.arange(n)
        mine = pos[stack_of(pos, n if contiguous else None) == s]
        nbq = max(1, -(-len(mine) // LI))
        nl.append(f"{nbq:08x}")
        layout_lines.append(f"{n:x}")
        for b in range(nbq):
            chunk = mine[b * LI:(b + 1) * LI]
            fields = []
            for l in range(LI):
                if l < len(chunk):
                    j = chunk[l]
                    fields += [(c, 4) for c in t["kc"][j]] + [(u, 8) for u in t["ku"][j]]
                    el.append(IC.hexline([(t["exp"][j], 16), (int(t["fault"][j]), 1)]))
                else:
                    fields += [(0, 4)] * (nb * 32) + [(127, 8)] * nb
                    el.append("0")
            kv = (1 << len(chunk)) - 1
            keep = sum(int(t["keep"][chunk[l]]) << l for l in range(len(chunk)))
            # {kv[LI], keep[LI], key[LI*KB]}: key slot 0 lowest
            kl.append(IC.hexline(fields + [(keep, LI), (kv, LI)]))
        sc = np.array([t["exp"][j] for j in mine], dtype=np.int64)
        vals = G.from_bits((sc << 16).astype(np.uint32)).astype(np.float64) if len(mine) else np.zeros(0)
        loc = sorted(int(i) for i in G.topk_lowest_index(vals, min(K, len(mine)))) if len(mine) else []
        cl.append(f"{len(loc):09x}")
        for i in loc:
            cl.append(IC.hexline([(int(sc[i]), 16), (int(mine[i]), IW)]))
        info.append(dict(n=n, stack_keys=int(len(mine)), beats=nbq, candidates=len(loc),
                         faults=int(np.sum(t["fault"][mine])) if len(mine) else 0))
    for name, lines in (("st_q.mem", ql), ("st_n.mem", nl), ("st_k.mem", kl), ("st_e.mem", el), ("st_c.mem", cl), ("st_layout.mem", layout_lines)):
        (d / name).write_text("\n".join(lines) + "\n")
    return len(kl), len(cl), info


def run_stack(binary: Path, d: Path, nq, nbeat, ncand, s, rate=RATE):
    t = time.time()
    r = subprocess.run([str(binary), f"+NQ={nq}", f"+NBEAT={nbeat}", f"+NCAND={ncand}", f"+STACK={s}",
                        f"+RATE={rate}"], cwd=d, capture_output=True, text=True)
    out = r.stdout + r.stderr
    (d / f"run_stack{s}_rate{rate}.log").write_text(out)
    m = re.search(r"STDONE queries=(\d+) checked=(\d+) score_errors=(\d+) faults=(\d+) cand_errors=(\d+)", out)
    rows = []
    for mm in STRE.finditer(out):
        g = [int(x) for x in mm.groups()]
        rows.append(dict(beats=g[1], start=g[2], first=g[3], last=g[4], cand=g[5], folds=g[6], passed=g[7],
                         stall=g[8], fault=g[9], last_key_to_list=g[5] - g[4], scan_cycles=g[4] - g[3] + 1))
    res = dict(rc=r.returncode, wall_s=round(time.time() - t, 1), rows=rows,
               mismatch_lines=[ln for ln in out.splitlines() if "MISMATCH" in ln or "COUNT" in ln or "atal" in ln][:10])
    if m:
        res.update(zip(("queries", "checked", "score_errors", "faults", "cand_errors"), map(int, m.groups())))
    return res


def bench_score(args):
    work = Path(args.work) / "score"
    work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed + 1)
    params = dict(NSL=4, NK=4, NB=4, IH=32, IW=IW, K=K, FPL=7, FML=5, QL=5, MAXQ=64, MAXB=1 << 13, MAXC=1 << 14, CONTIGUOUS=int(args.contiguous))
    if args.contexts:
        params["MAXB"] = 1 << 13
    binary = build(work, STK_TB, STK_RTL, "tb_dsrom_edge_stack", params, jobs=args.jobs)
    rec = dict(schema="opentallas.dsrom-edge-stack-score.v1", bench=STK_TB, parameters=params,
               golden="tools/rtl_hdc_v41x_idx_campaign.golden (Model.indexer's score lines, chunk8) per key; the "
                      "stack's candidate list = sorted(topk_lowest_index(stack scores, min(512, n_stack))), mapped "
                      "to global positions 64*(j>>4)+16*s+(j&15); the die selection of the four lists is the select "
                      "bench's (same lsel/hub RTL)", groups={})
    ok = True
    groups = []
    if not args.contexts:
        toks = [make_token(rng, int(n), c) for n, c in
                ((700, "typical"), (3000, "normal"), (1500, "wide"), (900, "underflow"), (1200, "sparse"),
                 (2100, "masked"), (600, "fault"), (5000, "normal"), (64, "typical"), (17, "typical"), (1, "normal"))]
        groups.append(("mixed", toks))
    else:
        for ctx in args.contexts:
            groups.append((f"ctx{ctx}", [make_token(rng, ctx // 4, "normal")]))
    for gname, toks in groups:
        grec = dict(tokens=[dict(n=len(t["keep"]), cls=t["cls"]) for t in toks], stacks={})
        for s in range(4):
            d = work / gname / f"s{s}"
            nbeat, ncand, info = write_stack(d, toks, s, contiguous=args.contiguous)
            r = run_stack(binary, d, len(toks), nbeat, ncand, s)
            sp = bool(r["rc"] == 0 and r.get("queries") == len(toks) and r.get("score_errors") == 0 and
                      r.get("cand_errors") == 0 and r.get("checked") == sum(i["stack_keys"] for i in info) and
                      r.get("faults") == sum(i["faults"] for i in info) and len(r["rows"]) == len(info) and
                      all(row["fault"] == bool(i["faults"]) for row, i in zip(r["rows"], info)))
            ok &= sp
            grec["stacks"][s] = dict(passed=sp, info=info, **r)
            print(gname, "stack", s, "pass" if sp else "FAIL", r.get("checked"), r.get("score_errors"),
                  r.get("cand_errors"), r["wall_s"], flush=True)
        rec["groups"][gname] = grec
    rec["pass"] = bool(ok)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bench", choices=["select", "score"])
    ap.add_argument("--work", default="/tmp/dsrom_edge_work")
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int, default=20261003)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--contiguous", action="store_true", help="opt-in frozen block8 contiguous layout + concat")
    ap.add_argument("--no-real", action="store_true")
    ap.add_argument("--real-cache")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--contexts", type=int, nargs="*", help="score bench: one token per context (n = ctx/4)")
    args = ap.parse_args()
    srcs = SEL_RTL + [SEL_TB, HARNESS, "tools/dsrom_edge_scorer_campaign.py", "tools/hdc_golden_v41.py"]
    if args.bench == "score":
        srcs = STK_RTL + [STK_TB, HARNESS, "tools/dsrom_edge_scorer_campaign.py", "tools/hdc_golden_v41.py",
                          "tools/rtl_hdc_v41x_idx_campaign.py"]
    t = time.time()
    rec = bench_select(args) if args.bench == "select" else bench_score(args)
    rec.update(contiguous=args.contiguous, git_head=git_head(), dirty=dirty(srcs), source_sha256={s: sha(s) for s in sorted(set(srcs))},
               verilator=subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
               wall_s=round(time.time() - t, 1), argv=sys.argv[1:])
    out = Path(args.out) if args.out else OUT / f"{args.bench}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("wrote", out, "pass" if rec["pass"] else "FAIL")
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
