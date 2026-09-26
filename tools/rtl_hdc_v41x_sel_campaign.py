#!/usr/bin/env python3
"""Performance + exactness campaign for the V4.1x index SELECT (block `sel`):
rtl/hdc/v41x/ot_hdc_v41x_sel.sv -- a streaming exact filter with in-place GC in front of a
threshold select, Q = 4 contiguous position quarters x W = 16 lanes = 64 scores/cycle.

Every segment is checked bit-exactly against tools/hdc_golden_v41.py `topk_lowest_index`
(value descending, ties to the lower index, -0 == +0, -inf lowest; emitted in ascending
position order, quarter q's part on port q).  Stimulus families:
  * shipped sizes, per die: 50,000 scores (200K context, layer 20) and 262,144 (1M), k = 512,
    dense beats at the full 64 scores/cycle, value families normal / uniform / lognormal /
    recency trend / real reduced-vehicle scores resampled to the shipped size / the real
    L20 score streams tiled in position order;
  * filter worst cases: ascending (every score survives -> survivor overflow -> the replay
    fallback), descending, all equal, few distinct values, masked (-inf) keys including
    fewer than k finite;
  * coverage: random sizes, random lane masks, random k (0 .. past K), random quarter cuts
    with empty quarters, raw NaN-free BF16 patterns, input bubbles and output back-pressure,
    tiny memories that overflow;
  * the real reduced DeepSeek-V4.1 indexer selections (k = 16) on a reduced instance;
  * the cross-die final select: 4 dies' local top-512 selections, one die per quarter;
  * a mutation check (each mutation must fail; an unmutated control must pass).
Measured per segment: tail = edges from the final last accept to the last quarter's
registered out_last, ingest stall cycles (must be 0: 64 scores/cycle), survivors (lines
written), lines at pass 2 / pass 3, overflow.  Spec (docs/ARCH_SPEC_V41.md section 6 item 6):
tail <= 181 at 1M per die, <= 155 at 200K; 64 scores/cycle; exact.

Writes results/rtl/hdc_v41x_sel_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41_select_campaign as SC  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_sel_campaign.json"
RTL = [ROOT / "rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv", ROOT / "rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv",
       ROOT / "rtl/hdc/v41x/ot_hdc_v41x_sel.sv"]
TB = ROOT / "rtl/test/tb_hdc_v41x_sel.sv"
HARNESS = ROOT / "rtl/test/hdc_v41x_sel_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/rtl_hdc_v41_select_campaign.py", Path(__file__)]
SUMMARY = re.compile(r"V41XSEL Q=(\d+) W=(\d+) IW=(\d+) K=(\d+) AW=(\d+) segments=(\d+) beats=(\d+) elements=(\d+) "
                     r"outputs=(\d+) out_beats=(\d+) errors=(\d+) tail_min=(-?\d+) tail_max=(-?\d+) ovf_segs=(\d+) "
                     r"stall=(\d+) cycles=(\d+)")
SEG = re.compile(r"SEG (\d+) tail=(-?\d+) first=(-?\d+) last=(-?\d+) ovf=(\d+) rep=(\d+) stall=(\d+) k=(\d+) "
                 r"nhead=([\d,]+)\s+n2=([\d,]+)\s+n3=([\d,]+)")
SPEC_TAIL = {50000: 155, 262144: 181}
NINF = 0xFF80
SCRATCH = Path(os.environ.get("OT_SCRATCH", tempfile.gettempdir()))
_V5 = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
VERILATOR = str(_V5) if _V5.exists() else "verilator"   # 5.x builds the W = 16 bench ~10x faster than 4.038


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- values -------------------------------------------------------------------------------
def bf16_bits(x):
    """float -> BF16 bit patterns, round to nearest even (the golden's to_bf16)."""
    return (np.asarray(G.to_bf16(np.asarray(x, np.float32)), np.float32).view(np.uint32) >> 16).astype(np.int64)


def vals_of(bits):
    return (np.asarray(bits, np.uint32) << 16).view(np.float32).astype(np.float64)


def family(rng, name, n, k, pool=None, streams=None):
    """BF16 bit patterns of one segment of the named family."""
    if name == "normal":
        return bf16_bits(rng.standard_normal(n))
    if name == "uniform":
        return bf16_bits(rng.random(n))
    if name == "lognormal":
        return bf16_bits(np.exp(rng.standard_normal(n)))
    if name == "recency":                        # later positions score higher on average
        return bf16_bits(rng.standard_normal(n) + 3.0 * np.arange(n) / n)
    if name == "ascending":
        return bf16_bits(np.sort(rng.standard_normal(n)))
    if name == "descending":
        return bf16_bits(np.sort(rng.standard_normal(n))[::-1])
    if name == "all_equal":
        return np.full(n, int(bf16_bits(np.array([1.5]))[0]), np.int64)
    if name == "ties":
        alpha = bf16_bits(rng.standard_normal(int(rng.integers(2, 9))))
        return rng.choice(alpha, n)
    if name == "masked":                         # 90% of keys masked to -inf
        b = bf16_bits(rng.standard_normal(n))
        return np.where(rng.random(n) < 0.9, NINF, b)
    if name == "masked_few":                     # fewer than k finite
        b = np.full(n, NINF, np.int64)
        idx = rng.choice(n, min(n, max(0, k // 3)), replace=False)
        b[idx] = bf16_bits(rng.standard_normal(len(idx)))
        return b
    if name == "raw":
        return SC.fbits(SC.random_values(rng, n, 16), 16)
    if name == "real_resampled":                 # real reduced-vehicle index scores, shipped size
        return rng.choice(pool, n)
    if name == "real_tiled":                     # real L20 score streams, position order, tiled
        out, total = [], 0
        while total < n:
            s = streams[int(rng.integers(0, len(streams)))]
            out.append(s)
            total += len(s)
        return np.concatenate(out)[:n]
    raise ValueError(name)


# -- the real reduced vehicle --------------------------------------------------------------
def real_sets(positions, cache: Path | None):
    """Index scores of every indexed layer at every position of the golden's reduced decode
    (checked against the golden's own selection), cached as a pickle."""
    if cache and cache.exists():
        d = pickle.loads(cache.read_bytes())
        if d.get("positions") == positions:
            return d
    prompt, gen = G.prompt_and_expected()
    model = G.Model()
    state = model.new_state()
    seq = list(prompt) + list(gen)
    sets, checks = [], 0
    for p in range(positions):
        tr = {}
        logits = model.decode_token(seq[p], p, state, trace=tr)
        if p + 1 >= len(seq):
            seq.append(int(np.argmax(logits)))
        for L in range(model.L):
            if f"L{L}.index_scores" in tr:
                s = np.asarray(tr[f"L{L}.index_scores"], np.float64)
                sel = sorted(int(i) for i in G.topk_lowest_index(s, min(model.topk, len(s))))
                assert sel == list(tr[f"L{L}.index_select"])
                checks += 1
                sets.append((L, p, SC.fbits(s, 16)))
    d = {"positions": positions, "tokens": seq[:positions + 1], "sets": sets, "checks": checks,
         "index_topk": model.topk, "candidate_topk_blocks": model.cand_k, "candidate_block_size": model.cand_b,
         "cand_src": model.cand_src}
    if cache:
        cache.write_bytes(pickle.dumps(d))
    return d


# -- segments -> vectors ----------------------------------------------------------------------
def cuts_of(rng, n, Q, mode):
    if Q == 1:
        return [0, n]
    if mode == "even":
        return [(n * j) // Q for j in range(Q + 1)]
    c = sorted(int(x) for x in rng.integers(0, n + 1, Q - 1))
    return [0] + c + [n]


def to_beats(rng, bits, pos, W, dense):
    beats, i, n = [], 0, len(bits)
    while i < n:
        lanes = [None] * W
        if dense:
            fill = np.ones(W, bool)
        else:
            p = rng.choice([1.0, 0.9, 0.5, 0.1, 0.0], p=[0.5, 0.2, 0.15, 0.1, 0.05])
            fill = rng.random(W) < p
        for j in range(W):
            if fill[j] and i < n:
                lanes[j] = (int(bits[i]), int(pos[i]))
                i += 1
        beats.append(lanes)
    if not beats:
        beats.append([None] * W)
    return beats


def segment(rng, bits, k, K, Q, W, cut="even", dense=True, pos=None):
    """(per-quarter beats, k, per-quarter expected [(pos, bits, ninf)], meta)."""
    bits = np.asarray(bits, np.int64)
    n = len(bits)
    pos = np.arange(n) if pos is None else np.asarray(pos)
    v = vals_of(bits)
    sel = sorted(int(i) for i in G.topk_lowest_index(v, min(k, K, n)))
    cuts = cuts_of(rng, n, Q, cut)
    beats, exps = [], []
    for q in range(Q):
        lo, hi = cuts[q], cuts[q + 1]
        beats.append(to_beats(rng, bits[lo:hi], pos[lo:hi], W, dense))
        exps.append([(int(pos[i]), int(bits[i]), int(bits[i] == NINF)) for i in sel if lo <= i < hi])
    return beats, k, exps, {"n": n}


def write_vectors(segs, Q, W, d: Path, tag):
    pfx = d / tag
    h = hashlib.sha256()
    stats = dict(elements=0, expected_outputs=0, beats=0)
    for q in range(Q):
        li, le = [], []
        for beats, k, exps, _ in segs:
            bq = beats[q]
            for bi, lanes in enumerate(bq):
                lv = sum(1 << j for j, e in enumerate(lanes) if e is not None)
                fields = " ".join(f"{e[0]:x} {e[1]:x}" if e else "0 0" for e in lanes)
                li.append(f"{int(bi == len(bq) - 1)} {k} {lv:x} {fields}\n")
                stats["elements"] += sum(e is not None for e in lanes)
            stats["beats"] += len(bq)
            le.append(f"S {len(exps[q])} {len(bq)}\n")
            le += [f"{p:x} {vb:x} {ni}\n" for p, vb, ni in exps[q]]
            stats["expected_outputs"] += len(exps[q])
        Path(f"{pfx}.in{q}").write_text("".join(li))
        Path(f"{pfx}.exp{q}").write_text("".join(le))
        h.update(Path(f"{pfx}.in{q}").read_bytes() + Path(f"{pfx}.exp{q}").read_bytes())
    stats["vectors_sha256"] = h.hexdigest()
    return pfx, stats


# -- build / run ---------------------------------------------------------------------------------
def build(obj: Path, Q, W, IW, K, AW, maxb, rtl=None):
    obj.mkdir(parents=True, exist_ok=True)
    srcs = [str(p) for p in (rtl or RTL)]
    subprocess.run([VERILATOR, "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "--top-module", "tb_hdc_v41x_sel",
                    f"-GQ={Q}", f"-GW={W}", f"-GIW={IW}", f"-GK={K}", f"-GAW={AW}", f"-GMAXB={maxb}",
                    "-Mdir", str(obj), *srcs, str(TB), str(HARNESS), "-CFLAGS", "-O1"],
                   check=True, capture_output=True)
    return obj / "Vtb_hdc_v41x_sel"


def simulate(binary, pfx, bub=0, ordy=0, seed=1):
    r = subprocess.run([str(binary), f"+PFX={pfx}", f"+BUBBLE={bub}", f"+ORDY={ordy}", f"+SEED={seed}"],
                       capture_output=True, text=True)
    return parse(r.stdout)


def parse(out):
    m = SUMMARY.search(out)
    if not m:
        return {"pass": False, "log": out[-3000:]}
    (q, w, iw, k, aw, segs, beats, el, outs, obeats, err, tmin, tmax, ovf, stall, cyc) = map(int, m.groups())
    per = []
    for s in SEG.finditer(out):
        per.append(dict(seg=int(s[1]), tail=int(s[2]), first=int(s[3]), last=int(s[4]), ovf=int(s[5]),
                        replays=int(s[6]), stall=int(s[7]), k=int(s[8]),
                        nhead=[int(x) for x in s[9].split(",")], n2=[int(x) for x in s[10].split(",")],
                        n3=[int(x) for x in s[11].split(",")]))
    return {"segments": segs, "beats": beats, "elements": el, "outputs": outs, "out_beats": obeats, "errors": err,
            "tail_min": tmin, "tail_max": tmax, "ovf_segments": ovf, "stall_cycles": stall, "cycles": cyc,
            "per_segment": per, "pass": ("PASS" in out) and err == 0,
            "log": "\n".join(ln for ln in out.splitlines() if ln.startswith("E "))[:2000]}


# -- configurations --------------------------------------------------------------------------------
def shipped_segments(rng, n, fams, reps, K, Q, W, pool, streams):
    segs, labels = [], []
    for f in fams:
        for _ in range(reps):
            b = family(rng, f, n, K, pool, streams)
            segs.append(segment(rng, b, K, K, Q, W, "even", True))
            labels.append(f)
    return segs, labels


def coverage_segments(rng, nseg, K, Q, W, IW, AW, pool):
    cap = min(1 << IW, Q * W * (1 << AW) * 4)
    segs, labels = [], []
    fams = ["normal", "uniform", "raw", "ties", "all_equal", "ascending", "descending", "masked", "masked_few",
            "recency", "real_resampled"]
    kmax = (1 << int(np.ceil(np.log2(K + 1)))) - 1
    for _ in range(nseg):
        r = rng.random()
        n = int(1 if r < 0.03 else rng.integers(1, K + 1) if r < 0.2 else
                rng.integers(max(1, K - 2), K + 3) if r < 0.35 else rng.integers(K, min(cap, 40 * K) + 1))
        n = max(1, min(n, cap // 2))
        k = K if rng.random() < 0.6 else int(rng.integers(0, kmax + 1))
        f = fams[int(rng.integers(0, len(fams)))]
        b = family(rng, f, n, max(k, 1), pool, None)
        dense = rng.random() < 0.5
        if rng.random() < 0.5:
            pos = np.arange(n)
        else:
            pos = np.sort(rng.choice(1 << IW, n, replace=False))
        segs.append(segment(rng, b, k, K, Q, W, "random" if rng.random() < 0.7 else "even", dense, pos))
        labels.append(f)
    return segs, labels


def cross_die_segments(rng, nseg, K, Q, W, pool):
    """The final select over Q dies' local selections: die q owns positions [q*N, (q+1)*N) and
    streams its local top-K (positions ascending) on port q."""
    segs, labels = [], []
    N = 262144
    for s in range(nseg):
        fam = ["normal", "real_resampled", "ties", "recency"][s % 4]
        allb, allp = [], []
        for q in range(Q):
            b = family(rng, fam, 8192, K, pool, None)
            v = vals_of(b)
            loc = sorted(int(i) for i in G.topk_lowest_index(v, K))
            p = np.sort(rng.choice(N, 8192, replace=False))
            allb.append(b[loc])
            allp.append(q * N + p[loc])
        bits = np.concatenate(allb)
        pos = np.concatenate(allp)
        # quarters = dies: cut at the die boundaries
        n = len(bits)
        v = vals_of(bits)
        sel = sorted(int(i) for i in G.topk_lowest_index(v, K))
        beats, exps = [], []
        for q in range(Q):
            lo, hi = q * K, (q + 1) * K
            beats.append(to_beats(rng, bits[lo:hi], pos[lo:hi], W, True))
            exps.append([(int(pos[i]), int(bits[i]), int(bits[i] == NINF)) for i in sel if lo <= i < hi])
        segs.append((beats, K, exps, {"n": n}))
        labels.append("cross_die_" + fam)
    return segs, labels


def real_reduced_segments(rng, real, K, Q, W):
    segs, labels = [], []
    for (L, p, b) in real["sets"]:
        segs.append(segment(rng, b, real["index_topk"], K, Q, W, "random" if rng.random() < 0.5 else "even",
                            rng.random() < 0.5))
        labels.append(f"real_L{L}")
    return segs, labels


MUTATIONS = [
    ("filter keeps only strictly greater keys", "assign i1_s_d[gl]  = i0_lv[gl] && (k >= r_T);",
     "assign i1_s_d[gl]  = i0_lv[gl] && (k > r_T);"),
    ("coarse bound ignores the verification", "wire          use_c = (st == C_ING) && kseen && (hold_c == 0) && cres_ok;",
     "wire          use_c = (st == C_ING) && kseen && (hold_c == 0);"),
    ("fine bound used right after a bucket change", "wire          use_f = (st == C_ING) && kseen && (hold_c == 0) && (hold_f == 0) && fres_ok;",
     "wire          use_f = (st == C_ING) && kseen && (hold_c == 0) && fres_ok;"),
    ("GC keeps only strictly greater keys", "assign c1_eq_d[gl] = lv && (k == tsw);", "assign c1_eq_d[gl] = lv && (k == tsw) && (sw_k != K_GC);"),
    ("tie to the higher index", "c2_pre[(LW+1)*ll +: LW+1]} < rem)", "c2_pre[(LW+1)*ll +: LW+1]} <= rem)"),
    ("tie quota ignores earlier quarters", "rem_d[QC*i +: QC] = ({{(CB+3-QC){1'b0}}, t} > pre) ? t - pre[QC-1:0] : {QC{1'b0}};",
     "rem_d[QC*i +: QC] = t;"),
    ("abort loses the unread range", "else if (ab_seg == 2'd0) begin b_st <= rd_ab; b_end <= a_end; end",
     "else if (ab_seg == 2'd0) begin b_st <= 0; b_end <= 0; end"),
    ("-0 not canonicalised", "fkey = (v[14:0] == 0) ? 16'h8000", "fkey = (v[15:0] == 0) ? 16'h8000"),
    ("pass 2 drops the boundary bucket", "c_st <= {bs, 8'h00}; c_p2 <= 1'b1;", "c_st <= {bs, 8'h01}; c_p2 <= 1'b1;"),
    ("search result taken early", "localparam integer WAIT = 11;", "localparam integer WAIT = 7;"),
]


def mutate(d: Path):
    """Return {mutation: pass?} running a small tie-heavy config on each mutated copy."""
    rng = np.random.default_rng(99)
    Q, W, IW, K, AW = 4, 4, 16, 16, 6
    segs, _ = coverage_segments(rng, 150, K, Q, W, IW, AW, np.array([0x3F80, 0x4000, 0xBF80, 0x3F00]))
    pfx, _ = write_vectors(segs, Q, W, d, "mut")
    res = []

    def one(mi):
        name, old, new = mi
        md = d / f"mut{abs(hash(name)) % 10**8}"
        md.mkdir(exist_ok=True)
        srcs = []
        hit = False
        for p in RTL:
            s = p.read_text()
            if old in s:
                s = s.replace(old, new, 1)
                hit = True
            q = md / p.name
            q.write_text(s)
            srcs.append(q)
        if not hit and name != "control":
            return {"mutation": name, "applied": False, "pass": None}
        b = build(md / "obj", Q, W, IW, K, AW, 4096, rtl=srcs)
        r = simulate(b, pfx, bub=5, ordy=20, seed=3)
        return {"mutation": name, "applied": True, "pass": r["pass"], "errors": r.get("errors")}

    with ThreadPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(one, [("control", "@@none@@", "")] + MUTATIONS))
    return res


def run_config(name, Q, W, IW, K, AW, segs, labels, d: Path, runs=((0, 0, 1),), maxb=8192):
    pfx, st = write_vectors(segs, Q, W, d, name)
    b = build(d / f"obj_{name}", Q, W, IW, K, AW, maxb)
    out = []
    for bub, ordy, seed in runs:
        r = simulate(b, pfx, bub, ordy, seed)
        for ps, lab, sg in zip(r.get("per_segment", []), labels, segs):
            ps["family"] = lab
            ps["n"] = sg[3]["n"]
        out.append({"bubble_pct": bub, "out_ready_low_pct": ordy, "seed": seed, **r})
    return {"name": name, "Q": Q, "W": W, "IW": IW, "K": K, "AW": AW, **st, "runs": out,
            "pass": all(r["pass"] for r in out)}


def summarise_shipped(cfg):
    """Spec rows from a shipped-size config's full-rate run."""
    r = cfg["runs"][0]
    rows = []
    for ps in r.get("per_segment", []):
        n = ps["n"]
        ingest_cycles = ps["last"] - ps["first"] + 1
        rows.append(dict(family=ps["family"], n=n, k=ps["k"], tail=ps["tail"], spec_tail=SPEC_TAIL.get(n),
                         tail_met=(ps["tail"] <= SPEC_TAIL[n]) if n in SPEC_TAIL else None,
                         ingest_cycles=ingest_cycles, scores_per_cycle=round(n / ingest_cycles, 3),
                         stall=ps["stall"], ovf=ps["ovf"], survivor_lines=ps["nhead"], pass2_lines=ps["n2"],
                         pass3_lines=ps["n3"]))
    return rows


def run(quick=False, real_positions=160, workers=8) -> dict:
    d = Path(tempfile.mkdtemp(prefix="v41xsel_", dir=SCRATCH))
    cache = SCRATCH / f"v41xsel_real_{real_positions}.pkl"
    real = real_sets(real_positions, cache)
    pool = np.concatenate([b for (_, _, b) in real["sets"]])
    streams = [b for (L, p, b) in real["sets"] if L == real["cand_src"] and len(b) >= 16]
    rng = np.random.default_rng(20260926)
    Q, W, IW, K, AW = 4, 16, 20, 512, 8
    reps = 1 if quick else 3
    fams = ["normal", "uniform", "lognormal", "recency", "real_resampled", "real_tiled"]
    jobs = []
    s200, l200 = shipped_segments(rng, 50000, fams, reps, K, Q, W, pool, streams)
    s1m, l1m = shipped_segments(rng, 262144, fams, reps, K, Q, W, pool, streams)
    jobs.append(("shipped_200k", Q, W, IW, K, AW, s200, l200, ((0, 0, 1),)))
    jobs.append(("shipped_1m", Q, W, IW, K, AW, s1m, l1m, ((0, 0, 1),)))
    worst = ["ascending", "descending", "all_equal", "ties", "masked", "masked_few"]
    sw, lw = shipped_segments(rng, 50000, worst, 1, K, Q, W, pool, streams)
    sw2, lw2 = shipped_segments(rng, 262144, ["ascending", "descending", "all_equal"], 1, K, Q, W, pool, streams)
    jobs.append(("worst_cases", Q, W, IW, K, AW, sw + sw2, lw + lw2, ((0, 0, 1),)))
    sc, lc = coverage_segments(rng, 60 if quick else 400, K, Q, W, IW, 6, pool)
    jobs.append(("coverage_q4_w16_k512_aw6", Q, W, IW, K, 6, sc, lc, ((0, 0, 1), (10, 30, 2))))
    sr, lr = real_reduced_segments(rng, real, 16, 4, 4)
    sr2, lr2 = coverage_segments(rng, 100 if quick else 1500, 16, 4, 4, 16, 4, pool)
    jobs.append(("reduced_real_q4_w4_k16", 4, 4, 16, 16, 4, sr + sr2, lr + lr2, ((0, 0, 1), (15, 40, 5))))
    sx, lx = cross_die_segments(rng, 4 if quick else 12, K, Q, W, pool)
    jobs.append(("cross_die_final_q4_w16_k512", Q, W, IW, K, 6, sx, lx, ((0, 0, 1),)))
    se, le = coverage_segments(rng, 100 if quick else 1500, 7, 2, 8, 10, 3, pool)
    jobs.append(("edge_q2_w8_k7_aw3", 2, 8, 10, 7, 3, se, le, ((0, 0, 1), (20, 50, 7))))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(run_config, n, q, w, iw, k, aw, s, lab, d, runs) for (n, q, w, iw, k, aw, s, lab, runs) in jobs]
        configs = [f.result() for f in futs]
    muts = [] if quick else mutate(d)
    ship = {c["name"]: summarise_shipped(c) for c in configs if c["name"] in ("shipped_200k", "shipped_1m", "worst_cases")}
    typical = [r for n in ("shipped_200k", "shipped_1m") for r in ship.get(n, [])]
    tail_1m = max((r["tail"] for r in typical if r["n"] == 262144), default=None)
    tail_200k = max((r["tail"] for r in typical if r["n"] == 50000), default=None)
    min_rate = min((r["scores_per_cycle"] for r in typical), default=None)
    all_pass = all(c["pass"] for c in configs) and all(
        (m["pass"] is True) if m["mutation"] == "control" else (m["pass"] is False) for m in muts if m["applied"])
    spec = {
        "exact_golden_equality": {"spec": "every segment bit-exact", "measured": all(c["pass"] for c in configs),
                                  "met": all(c["pass"] for c in configs)},
        "ingest_scores_per_cycle": {"spec": 64, "measured_min": min_rate,
                                    "stall_cycles": sum(r["stall"] for r in typical),
                                    "met": min_rate is not None and min_rate >= 63.9 and
                                    sum(r["stall"] for r in typical) == 0},
        "tail_1m_per_die": {"spec_max_cycles": 181, "measured_max": tail_1m,
                            "met": tail_1m is not None and tail_1m <= 181,
                            "families": sorted({r["family"] for r in typical if r["n"] == 262144})},
        "tail_200k_per_die": {"spec_max_cycles": 155, "measured_max": tail_200k,
                              "met": tail_200k is not None and tail_200k <= 155},
        "overflow_fallback": {"spec": "exact, slower (full replay)",
                              "measured": [dict(family=r["family"], n=r["n"], tail=r["tail"], ovf=r["ovf"])
                                           for r in ship.get("worst_cases", [])]},
    }
    return {
        "schema": "opentallas-rtl-campaign-v1",
        "block": "sel (index top-512 streaming-filter select)",
        "rtl": {str(p.relative_to(ROOT)): sha(p) for p in RTL},
        "bench": {str(p.relative_to(ROOT)): sha(p) for p in (TB, HARNESS)},
        "tools": {str(p.relative_to(ROOT)): sha(p) for p in TOOLS},
        "simulator": subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
        "real_vehicle": {"positions": real["positions"], "index_sets": len(real["sets"]), "golden_checks": real["checks"],
                         "tokens": real["tokens"], "index_topk": real["index_topk"]},
        "status": "pass" if all_pass else "fail",
        "spec": spec,
        "shipped": ship,
        "configs": [{k: v for k, v in c.items()} for c in configs],
        "mutations": muts,
        "quick": quick,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--real-positions", type=int, default=160)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--output", type=Path, default=OUT)
    a = ap.parse_args()
    res = run(a.quick, a.real_positions, a.workers)
    for c in res["configs"]:
        for r in c["runs"]:
            r.pop("log", None) if r.get("pass") else None
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(res, indent=1, default=int) + "\n")
    print(json.dumps(res["spec"], indent=1, default=int))
    print("status", res["status"])
    return 0 if res["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
