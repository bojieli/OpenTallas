#!/usr/bin/env python3
"""V4.1 lightning-indexer engine and its HBM key stream (block `idx`): bit-exact and performance campaign.

The engine (rtl/hdc/v41x/ot_hdc_v41x_idx.sv) against tools/hdc_golden_v41.py Model.indexer under R-ARITH
(chunk8):

    score[h] = to_bf16(dots_q4(q, key));  term[h] = to_bf16(mul(max(score, 0), wts[h]))
    s = to_bf16(reduce_rows(term.T));     masked keys -> -inf

Vectors come from two sources: RANDOM (seeded; FP4 codes and UE8M0 scales across the whole exponent range --
subnormal block values and products, zeros and negative zeros, BF16 ties, all-zero blocks, masked keys, and a
fault class whose golden intermediates overflow) and REAL -- every indexer call the golden makes while it runs
the reduced vehicle (build/models/deepseek-v4.1-flash-reduced-v2) over the oracle prompt and a continuation,
captured by wrapping the golden's own indexer (the query, keys and mask it scores; the expected scores are
re-derived from them by the golden's own lines and checked against the scores the golden itself produced).
Expected outputs are the golden's; where a golden intermediate is not finite the engine must raise `fault`.

Benches (Verilator, rtl/test/tb_hdc_v41x_idx.sv):
  * shipped shape (32 heads x 128 dims, 68-B keys) and reduced shape (32 x 32): bit exact under random source
    bubbles and sink back-pressure;
  * throughput: one long back-to-back scan, keys/cycle over the accepted span against NK;
  * latency: key beat accepted -> score beat valid, against the spec budget.
The HBM key-stream scan is a separate bench (--hbm; see hbm_scan()).

Writes results/rtl/hdc_v41x_idx_campaign.json.
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

G.set_arith("chunk8")
F = np.float32
OUT = ROOT / "results/rtl/hdc_v41x_idx_campaign.json"
RTL = [ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx.sv", ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
       ROOT / "rtl/hdc/ot_hdc_fastfp.sv", ROOT / "rtl/hdc/ot_hdc_delay.sv"]
TB = ROOT / "rtl/test/tb_hdc_v41x_idx.sv"
VLT = ROOT / "rtl/test/tb_hdc_v41x_idx.vlt"
HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
SCAN_RTL = [ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv", ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv"]
SCAN_TB = ROOT / "rtl/test/tb_hdc_v41x_idx_scan.sv"
SRE = re.compile(r"V41XSCAN ns=(\d+) wb=(\d+) ga=(\d+) qd=(\d+) refpb=(\d+) keys=(\d+) delivered=(\d+) errors=(\d+) "
                 r"cycles=(\d+) win_keys=(\d+) win_cycles=(\d+)")
HRE = re.compile(r"V41XHBM stack=(\d+) rd=(\d+) ref=(\d+) lat_sum=(\d+) lat_max_ps=(\d+)")
CLK_PS, BURST_PS, SECTOR_B, NPC = 967, 1024, 32, 32
STACK_PEAK_B_PER_CYCLE = NPC * SECTOR_B * CLK_PS / BURST_PS      # 967 B/cycle: 1.0 TB/s at 1.034 GHz
LRE = re.compile(r"V41XIDX keys=(\d+) checked=(\d+) errors=(\d+) faults_expected_and_raised=(\d+) beats=(\d+) "
                 r"span=(\d+) stall=(\d+) lat_min=(-?\d+) lat_max=(-?\d+) cycles=(\d+)")
E2M1 = G.E2M1_VALUES                        # 0, .5, 1, 1.5, 2, 3, 4, 6
CLOCK_HZ = 1.034e9

# the spec row (docs/ARCH_SPEC_V41.md 5-6; results/arch/arch_budget_v41.json required_spec)
SPEC = {
    "idx_macs_per_cycle_per_die": 228864,
    "keys_per_cycle_per_die_required": 228864 / (32 * 128),       # 55.875
    "keys_per_cycle_per_die_built": 64,
    "latency_key_to_score_cycles": 30,
    "idx_bytes_per_cycle_per_die": 3799.5,
    "key_bytes": 68,
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# -- FP4 codes <-> values ------------------------------------------------------------------------------
def values(codes, u):
    """codes [..., nb*32] (E2M1, sign in bit 3), u [..., nb] UE8M0 bytes -> binary32 values (as the golden's
    qdq output: code * 2^(u - 127), exact in BF16)."""
    codes = np.asarray(codes)
    mag = E2M1[codes & 7] * np.where(codes & 8, -1.0, 1.0)
    sc = np.repeat(np.exp2(np.asarray(u, dtype=np.float64) - 127.0), 32, axis=-1)
    with np.errstate(over="ignore", invalid="ignore"):
        return (mag * sc).astype(F)


def to_codes(v):
    """BF16-exact values of FP4-quantised 32-blocks -> (codes, UE8M0 bytes).  Any exact decomposition gives the
    same products; the largest scale that makes every element an E2M1 value is taken."""
    v = np.asarray(v, dtype=np.float64)
    shp = v.shape
    blk = v.reshape(-1, 32)
    codes = np.zeros(blk.shape, dtype=np.int64)
    us = np.zeros(blk.shape[0], dtype=np.int64)
    for i, b in enumerate(blk):
        a = np.max(np.abs(b))
        if a == 0:
            us[i] = 127
            continue
        e0 = int(np.floor(np.log2(a))) - 2
        for e in (e0 + 1, e0, e0 - 1, e0 - 2):
            m = np.abs(b) / 2.0 ** e
            idx = np.searchsorted(E2M1, m)
            idx = np.minimum(idx, 7)
            if np.all(E2M1[idx] == m):
                codes[i] = idx + 8 * (b < 0)
                us[i] = e + 127
                break
        else:
            raise ValueError("block is not FP4 x UE8M0")
        assert 0 <= us[i] <= 252
    assert np.array_equal(values(codes.reshape(-1, 32), us[:, None]), blk.astype(F))
    return codes.reshape(shp), us.reshape(shp[:-1] + (shp[-1] // 32,))


# -- the golden ------------------------------------------------------------------------------------------
def golden(q, wts, keys, keep, qu=None, ku=None):
    """Model.indexer's score lines on (q [ih, ihd], wts [ih], keys [n, ihd]), then the mask.  Returns
    (bf16 bits [n], fault [n]).  fault: a golden intermediate is not finite (block dot, score, product, term,
    sum), or a block scale byte >= 253 (refused by contract)."""
    with np.errstate(all="ignore"):
        a64, b64 = q.astype(np.float64), keys.astype(np.float64)
        nb = q.shape[1] // 32
        blk = np.stack([a64[:, i * 32:(i + 1) * 32] @ b64[:, i * 32:(i + 1) * 32].T for i in range(nb)], -1)
        blkf = blk.astype(F)
        sc32 = G.dots_q4(q, keys)                                          # [ih, n]
        score = G.to_bf16(sc32)
        prod = G.mul(np.maximum(score, F(0)), wts[:, None])
        terms = G.to_bf16(prod)
        s32 = G.reduce_rows(terms.T, cls="idx")
        s = G.to_bf16(s32)
    bad = ~np.isfinite(blkf).all(axis=(0, 2)) | ~np.isfinite(sc32).all(0) | ~np.isfinite(score).all(0) \
        | ~np.isfinite(prod).all(0) | ~np.isfinite(terms).all(0) | ~np.isfinite(s32) | ~np.isfinite(s)
    bad |= ~np.isfinite(q).all() | ~np.isfinite(keys).all(1)
    if qu is not None and np.any(np.asarray(qu) >= 253):
        bad[:] = True
    if ku is not None:
        bad |= np.any(np.asarray(ku) >= 253, axis=1)
    sm = np.where(np.asarray(keep, dtype=bool), s.astype(np.float64), -np.inf).astype(F)
    out = (G.bits(sm) >> 16).astype(np.int64)
    out[bad] = 0
    return out, bad


# -- random tokens -------------------------------------------------------------------------------------------
def rand_bf16(rng, n, lo, hi, p_zero=0.0, p_sub=0.0):
    e = rng.integers(lo, hi + 1, n)
    e = np.where(rng.random(n) < p_sub, 0, e)
    b = (rng.integers(0, 2, n) << 15) | (e << 7) | rng.integers(0, 128, n)
    b = np.where(rng.random(n) < p_zero, rng.integers(0, 2, n) << 15, b)
    return G.from_bits((b << 16).astype(np.uint32))


def rand_codes(rng, shape, p_zero):
    c = rng.integers(0, 16, shape)
    z = rng.random(shape) < p_zero
    return np.where(z, rng.integers(0, 2, shape) * 8, c)


CLASSES = ("typical", "wide", "underflow", "sparse", "masked", "fault")


def rand_token(rng, ih, nb, n, cls):
    ihd = nb * 32
    if cls == "typical":
        qu = 127 + rng.integers(-8, 5, (ih, nb)); ku = 127 + rng.integers(-8, 5, (n, nb))
        w = rand_bf16(rng, ih, 110, 128)
        pz = 0.1
    elif cls == "wide":
        c = rng.integers(20, 230)
        qu = np.clip(c + rng.integers(-20, 21, (ih, nb)), 0, 252); ku = np.clip(254 - c + rng.integers(-40, 21, (n, nb)), 0, 252)
        w = rand_bf16(rng, ih, 1, 254, p_sub=0.05)
        pz = 0.2
    elif cls == "underflow":
        qu = rng.integers(0, 70, (ih, nb)); ku = rng.integers(0, 70, (n, nb))
        w = rand_bf16(rng, ih, 60, 140, p_sub=0.3)
        pz = 0.3
    elif cls == "sparse":
        qu = 127 + rng.integers(-3, 3, (ih, nb)); ku = 127 + rng.integers(-3, 3, (n, nb))
        w = rand_bf16(rng, ih, 100, 130, p_zero=0.2)
        pz = rng.choice([0.6, 0.9, 0.99, 1.0])
    elif cls == "masked":
        qu = 127 + rng.integers(-6, 4, (ih, nb)); ku = 127 + rng.integers(-6, 4, (n, nb))
        w = rand_bf16(rng, ih, 110, 128)
        pz = 0.1
    else:   # fault: large scales, some refused scale bytes, huge weights
        qu = rng.integers(150, 256, (ih, nb)); ku = rng.integers(150, 256, (n, nb))
        w = rand_bf16(rng, ih, 120, 254)
        pz = 0.1
    qc = rand_codes(rng, (ih, ihd), pz)
    kc = rand_codes(rng, (n, ihd), pz)
    if cls == "sparse":
        kc[rng.random(n) < 0.2] = 0                                    # all-zero keys
    keep = rng.random(n) < (0.5 if cls == "masked" else 1.0)
    return dict(qc=qc, qu=qu, w=w, kc=kc, ku=ku, keep=keep, cls=cls)


def finish(tok):
    """Expected outputs of a token given by codes."""
    q = values(tok["qc"], tok["qu"])
    k = values(tok["kc"], tok["ku"])
    tok["exp"], tok["fault"] = golden(q, tok["w"], k, tok["keep"], tok["qu"], tok["ku"])
    return tok


# -- real vehicle ---------------------------------------------------------------------------------------------
def vehicle_tokens(positions, seed=7):
    """Every indexer call of the golden over the oracle prompt followed by pseudo-random continuation tokens
    (real weights, real activations), captured at Model.indexer.  Returns token dicts."""
    model = G.Model()
    prompt, _ = G.prompt_and_expected()
    rng = np.random.default_rng(seed)
    toks = list(prompt) + [int(t) for t in rng.integers(0, model.c["vocab_size"], max(0, positions - len(prompt)))]
    toks = toks[:positions]
    got = []
    orig_ix, orig_dq = G.Model.indexer, G.dots_q4
    cap = {}

    def dq(a, b, block=32, **kw):
        cap["q"], cap["k"] = np.array(a), np.array(b)
        return orig_dq(a, b, block, **kw)

    def ix(self, L, x, qr, pos, state, trace, ctx, **kw):
        tr = {}
        cand_before = ctx.get("cand")
        sel = orig_ix(self, L, x, qr, pos, state, tr, ctx, **kw)
        n = (pos + 1) // self.ratio[L]
        if n == 0:
            return sel
        wts = G.to_bf16(G.mul(G.linear_bf16(self.lw(L, "attn.indexer.weights_proj.weight"), x), self.index_w_scale))
        keep = np.ones(n, dtype=bool)
        if 0 <= self.cand_src < L:
            keep = np.asarray(cand_before[:n], dtype=bool)
        s_gold = np.asarray(tr[f"L{L}.index_scores"], dtype=np.float64)
        got.append(dict(L=L, pos=pos, q=cap["q"], w=np.asarray(wts, dtype=F), k=cap["k"], keep=keep,
                        s_gold=s_gold))
        return sel

    G.Model.indexer, G.dots_q4 = ix, dq
    try:
        state = model.new_state()
        for p, t in enumerate(toks):
            model.decode_token(t, p, state)
    finally:
        G.Model.indexer, G.dots_q4 = orig_ix, orig_dq
    out = []
    for c in got:
        qc, qu = to_codes(c["q"])
        kc, ku = to_codes(c["k"])
        tok = finish(dict(qc=qc, qu=qu, w=c["w"], kc=kc, ku=ku, keep=c["keep"], cls=f"vehicle.L{c['L']}"))
        # the re-derived scores equal the golden's own (which masked with -inf)
        gold = (G.bits(c["s_gold"].astype(F)) >> 16).astype(np.int64)
        assert not tok["fault"].any() and np.array_equal(tok["exp"], gold), (c["L"], c["pos"])
        out.append(tok)
    return out


# -- mem files, build, run -------------------------------------------------------------------------------------
def hexline(fields):
    """[(value, width_bits)] low field first -> hex string."""
    acc, sh = 0, 0
    for v, w in fields:
        acc |= (int(v) & ((1 << w) - 1)) << sh
        sh += w
    return f"{acc:0{(sh + 3) // 4}x}"


def write_mems(d: Path, toks, ih, nb):
    d.mkdir(parents=True, exist_ok=True)
    ql, nl, kl, el = [], [], [], []
    for t in toks:
        for h in range(ih):
            f = [(c, 4) for c in t["qc"][h]] + [(u, 8) for u in t["qu"][h]] + [(int(G.bits(t["w"][h])) >> 16, 16)]
            ql.append(hexline(f))
        n = len(t["keep"])
        nl.append(f"{n:08x}")
        for j in range(n):
            f = [(c, 4) for c in t["kc"][j]] + [(u, 8) for u in t["ku"][j]] + [(int(t["keep"][j]), 1)]
            kl.append(hexline(f))
            el.append(hexline([(t["exp"][j], 16), (int(t["fault"][j]), 1)]))
    for name, lines in (("idx_q.mem", ql), ("idx_n.mem", nl), ("idx_k.mem", kl), ("idx_e.mem", el)):
        (d / name).write_text("\n".join(lines) + "\n")
    return len(toks), len(kl)


def build(work: Path, nk, ih, nb, fd, jobs=16):
    obj = work / f"obj_nk{nk}_ih{ih}_nb{nb}_fd{fd}"
    exe = obj / "Vtb_hdc_v41x_idx"
    stamp = hashlib.sha256(b"".join(p.read_bytes() for p in RTL + [VLT, TB, HARNESS])).hexdigest()
    if exe.exists() and (obj / "stamp").exists() and (obj / "stamp").read_text() == stamp:
        return exe
    cmd = ["verilator", "--cc", "--exe", "--build", "-O3", "--x-assign", "fast", "--x-initial", "fast",
           "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-DECLFILENAME", "-Wno-UNOPTFLAT",
           "--top-module", "tb_hdc_v41x_idx", f"-GNK={nk}", f"-GIH={ih}", f"-GNB={nb}", f"-GFD={fd}",
           "-CFLAGS", "-DVTOP=Vtb_hdc_v41x_idx -O1", "-j", str(jobs), "--Mdir", str(obj),
           str(VLT), str(TB)] + [str(p) for p in RTL] + [str(HARNESS)]
    t0 = time.time()
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    (obj / "stamp").write_text(stamp)
    print(f"  built {obj.name} in {time.time() - t0:.0f} s", flush=True)
    return exe


def run(exe: Path, d: Path, ntok, nkey, seed=1, bubble=0, ordy=0):
    r = subprocess.run([str(exe), f"+NTOK={ntok}", f"+NKEY={nkey}", f"+SEED={seed}", f"+BUBBLE={bubble}",
                        f"+ORDY={ordy}"], cwd=d, capture_output=True, text=True, timeout=36000)
    m = LRE.search(r.stdout)
    if not m:
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
    k = ("keys", "checked", "errors", "faults_expected_and_raised", "beats", "span", "stall", "lat_min", "lat_max",
         "cycles")
    res = dict(zip(k, map(int, m.groups())))
    res["mismatch_lines"] = [ln for ln in r.stdout.splitlines() if ln.startswith(("MISMATCH", "MISS-FAULT"))][:10]
    return res


def shape_bench(work, name, ih, nb, nk, fd, toks, long_n, rng):
    """Correctness under bubbles/back-pressure on `toks`, then one long back-to-back scan for throughput and
    latency."""
    exe = build(work, nk, ih, nb, fd)
    rec = {"shape": {"index_heads": ih, "index_head_dim": 32 * nb, "blocks_per_head": nb, "keys_per_cycle": nk,
                     "fifo_beats": fd}}
    d = work / f"{name}_mixed"
    ntok, nkey = write_mems(d, toks, ih, nb)
    rec["mixed"] = run(exe, d, ntok, nkey, seed=11, bubble=4, ordy=4)
    rec["mixed"]["tokens"] = ntok
    rec["mixed"]["classes"] = {c: int(sum(len(t["keep"]) for t in toks if t["cls"].startswith(c)))
                               for c in sorted({t["cls"].split(".")[0] for t in toks})}
    rec["mixed"]["expected_faults"] = int(sum(int(t["fault"].sum()) for t in toks))
    # back-to-back: one long scan, sink always ready
    lt = finish(rand_token(rng, ih, nb, long_n, "typical"))
    d = work / f"{name}_b2b"
    ntok, nkey = write_mems(d, [lt], ih, nb)
    r = run(exe, d, ntok, nkey, seed=3, bubble=0, ordy=0)
    r["keys_per_cycle"] = r["keys"] / r["span"]
    rec["back_to_back"] = r
    return rec


# -- HBM key-stream scan -------------------------------------------------------------------------------------
POLICIES = {   # name: (REFPB, QD, REFI_PS or None)
    "refpb_aware_mru": (3, 64, None),
    "refpb_aware": (2, 64, None),
    "refab_q512": (0, 512, None),
    "refresh_free": (2, 64, 10 ** 12),
}


def scan_build(work: Path, tag, params):
    obj = work / f"scan_{tag}"
    exe = obj / "Vtb_hdc_v41x_idx_scan"
    stamp = hashlib.sha256(b"".join(p.read_bytes() for p in SCAN_RTL + [SCAN_TB, HARNESS]) + repr(params).encode()).hexdigest()
    if exe.exists() and (obj / "stamp").exists() and (obj / "stamp").read_text() == stamp:
        return exe, None
    cmd = ["verilator", "--cc", "--exe", "--build", "-O3", "--x-assign", "fast", "--x-initial", "fast", "-Wno-fatal",
           "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-DECLFILENAME", "-Wno-UNOPTFLAT",
           "--top-module", "tb_hdc_v41x_idx_scan"] + [f"-G{k}={v}" for k, v in params.items()] + \
          ["-CFLAGS", "-DVTOP=Vtb_hdc_v41x_idx_scan -O1", "-j", "4", "--Mdir", str(obj), str(SCAN_TB)] + \
          [str(p) for p in SCAN_RTL] + [str(HARNESS)]
    return exe, (subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), obj, stamp)


def hbm_scan(work: Path, quick=False):
    """The die's index-key scan through the HBM model of results/rtl/hdc_hbm_campaign.json (agent a8c77c67,
    rtl/hdc/kv/ot_hdc_hbm_model.sv @ a4e66ca8 / be30614a, copied with per-pseudo-channel request ports):
      * die: 5 stacks -> 5 streams -> merge -> a 64-key/cycle sink (the engine), the 1M-context layer-20 scan
        (262,144 keys, 17.8 MB) and a 5x longer one for the steady state;
      * stack: 1 stack, a 16-key/cycle sink (above the stack's 14.2 keys/cycle peak), so the stream itself is
        the limit: sustained fraction of the channels' raw peak.
    Every delivered key is checked against the bytes its position's layout puts in HBM."""
    die_keys = [262144] if quick else [262144, 1310720]
    stack_keys = 50000 if quick else 1000000
    runs = []
    for pol, (refpb, qd, refi) in POLICIES.items():
        for scope in ("die", "stack"):
            params = {"NS": 5 if scope == "die" else 1, "SINKW": 64 if scope == "die" else 16, "QD": qd,
                      "GA": 120, "WB": 128, "REFPB": refpb}
            if refi:
                params["REFI_PS"] = refi
            runs.append((pol, scope, params))
    procs = []
    for pol, scope, params in runs:
        exe, pr = scan_build(work, f"{scope}_{pol}", params)
        procs.append((pol, scope, params, exe, pr))
    for *_, pr in procs:
        if pr:
            pr[0].wait()
            if pr[0].returncode:
                raise RuntimeError(f"scan build failed: {pr[1]}")
            (pr[1] / "stamp").write_text(pr[2])
    jobs = []
    for pol, scope, params, exe, _ in procs:
        for n in (die_keys if scope == "die" else [stack_keys]):
            jobs.append((pol, scope, params, n, subprocess.Popen([str(exe), f"+NKEYS={n}"], cwd=exe.parent,
                                                                 stdout=subprocess.PIPE, text=True)))
    out = {"model": "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv = rtl/hdc/kv/ot_hdc_hbm_model.sv @ a4e66ca8 (unchanged "
                    "at be30614a) with one request port per pseudo-channel; REFPB 3 adds a most-recently-"
                    "activated tie-break to the refresh-aware choice",
           "clock_ps": CLK_PS, "stack_peak_bytes_per_cycle": STACK_PEAK_B_PER_CYCLE, "key_bytes": 68,
           "policies": {"refpb_aware_mru": "REFpb (tRFCpb 200 ns), refresh-aware: of the banks not yet refreshed "
                                            "in the set, the one the fewest queued bursts need (never the head "
                                            "burst's), ties to the most recently activated bank",
                        "refpb_aware": "the record's policy: the same, ties to a closed bank before an open one",
                        "refab_q512": "all-bank refresh, 512-beat queues",
                        "refresh_free": "no refresh (the raw-peak denominator)"},
           "stream": {"queue_beats_per_pseudo_channel": "QD", "request_lookahead_blocks": 120,
                      "rob_blocks": 128, "rob_bytes_per_stack": 128 * 4096}, "rows": {}}
    for pol, scope, params, n, pr in jobs:
        so, _ = pr.communicate(timeout=36000)
        m = SRE.search(so)
        if not m:
            raise RuntimeError(so[-2000:])
        g = list(map(int, m.groups()))
        hb = [list(map(int, h)) for h in HRE.findall(so)]
        row = dict(params=params, keys=g[5], delivered=g[6], errors=g[7], cycles=g[8], win_keys=g[9],
                   win_cycles=g[10], sectors_read=sum(h[1] for h in hb), refreshes=sum(h[2] for h in hb),
                   read_latency_max_ns=max(h[4] for h in hb) / 1000)
        ns = params["NS"]
        row["bytes_per_cycle"] = g[5] * 68 / g[8]
        row["win_bytes_per_cycle"] = g[9] * 68 / g[10]
        row["fraction_of_peak"] = row["bytes_per_cycle"] / (ns * STACK_PEAK_B_PER_CYCLE)
        row["win_fraction_of_peak"] = row["win_bytes_per_cycle"] / (ns * STACK_PEAK_B_PER_CYCLE)
        row["scan_us"] = g[8] * CLK_PS / 1e6
        out["rows"].setdefault(scope, {}).setdefault(str(n), {})[pol] = row
    for scope, byn in out["rows"].items():
        for n, byp in byn.items():
            nr = byp["refresh_free"]
            for pol, row in byp.items():
                row["efficiency_vs_refresh_free"] = nr["cycles"] / row["cycles"]
                row["win_efficiency_vs_refresh_free"] = nr["win_cycles"] / row["win_cycles"]
    st = out["rows"]["stack"][str(stack_keys)]
    d1 = out["rows"]["die"]["262144"]
    out["verdict"] = {
        "bit_exact": all(r["errors"] == 0 and r["delivered"] == r["keys"]
                         for byn in out["rows"].values() for byp in byn.values() for r in byp.values()),
        "stack_win_fraction_of_peak": {p: st[p]["win_fraction_of_peak"] for p in st},
        "die_1m_layer20_scan_us": {p: d1[p]["scan_us"] for p in d1},
        "die_1m_layer20_efficiency_vs_refresh_free": {p: d1[p]["efficiency_vs_refresh_free"] for p in d1},
        "chosen": "refpb_aware_mru",
        "fallback": "refab_q512",
        "tie_break_note": "the refresh-aware tie-break is workload-dependent: be30614a chose closed-before-open on "
                          "QE weight streams (not one sequential scan); on a sequential scan every bank the stream "
                          "has left stays open and only the banks it is about to enter are closed, so closed-first "
                          "refreshes the next bank set just before it is needed (tRFCpb 200 ns > the 64-beat "
                          "queue's ~70 ns horizon); the most-recently-activated tie-break refreshes the set just "
                          "left.  REFab with 512-beat queues is the recorded fallback (at the 0.90 floor).",
        "meets_90pct_of_peak_with_refresh": st["refpb_aware_mru"]["win_fraction_of_peak"] >= 0.90,
        "record_policy_meets_90pct": st["refpb_aware"]["win_fraction_of_peak"] >= 0.90,
    }
    return out


PHYS = ROOT / "results/physical_abi3/asap7/hdc/v41x"


def die_summary(rec):
    """The per-die build: tiles x tile = the spec, the latency budget by stage, the routed tiles."""
    def phys(m):
        f = PHYS / m / "physical.json"
        if not f.exists():
            return None
        d = json.loads(f.read_text())["design"]
        return {k: d.get(k) for k in ("closed", "fmax_hz", "area_um2", "cells", "setup_wns_ns", "clock_period_ns")}
    chunk, tail, kctl = phys("ot_hdc_v41x_idx_chunk"), phys("ot_hdc_v41x_idx_tail"), phys("ot_hdc_v41x_idx_kctl")
    keys = SPEC["keys_per_cycle_per_die_built"]
    out = {
        "tile": "ot_hdc_v41x_idx_chunk (NB=4, NKT=1): 8 heads x 1 key/cycle = 1,024 FP4 x FP4 MACs/cycle",
        "tiles_per_die": 4 * keys, "tails_per_die": keys,
        "macs_per_cycle_per_die": 4 * keys * 1024, "spec_macs_per_cycle_per_die": SPEC["idx_macs_per_cycle_per_die"],
        "tiles_for_spec": -(-SPEC["idx_macs_per_cycle_per_die"] // 1024),
        "key_stream": "5 x ot_hdc_v41x_idx_kstream (one per HBM3E stack: ot_hdc_v41x_idx_kctl + a 32-bank ROB of "
                      "128 x 4 KB = 512 KB SRAM) + ot_hdc_v41x_idx_kmerge -> 64 keys/cycle",
        "latency_shipped_cycles": {
            "input register": 1, "block dots (exact, rounded once)": 3, "3 sequential block adds": 9,
            "to_bf16 + ReLU": 1, "x head weight, to_bf16": 2, "7 sequential head adds (chunk of 8)": 21,
            "chunk output register": 1, "tail input register": 1, "2 tree levels": 6,
            "to_bf16 + mask + output register": 1, "engine output register": 1},
        "latency_note": "R-ARITH fixes the dependent adds: 3 block adds + 7 head adds + 2 tree levels = 12 x 3 "
                        "cycles = 36 of the 47.  The per-head score (the dot product the spec's ~30-cycle budget "
                        "covers) is ready 13 cycles after the key arrives; the fused ReLU-weight head sum, which "
                        "spec section 6 item 5 places on the stream unit, adds the other 34.",
        "routed": {"chunk": chunk, "tail": tail, "kctl": kctl},
    }
    if chunk and tail:
        out["logic_area_mm2_per_die"] = round((4 * keys * chunk["area_um2"] + keys * tail["area_um2"]
                                               + (5 * kctl["area_um2"] if kctl else 0)) / 1e6, 3)
    for k in ("shipped", "reduced"):
        if k in rec:
            out[f"{k}_latency_cycles_measured"] = rec[k]["back_to_back"]["lat_min"]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", default=os.environ.get("OT_SCRATCH", "/tmp/claude-1000/idx_campaign"))
    ap.add_argument("--quick", action="store_true", help="small vector counts (pytest)")
    ap.add_argument("--nk", type=int, default=8)
    ap.add_argument("--positions", type=int, default=40, help="vehicle positions decoded")
    ap.add_argument("--output", default=str(OUT))
    ap.add_argument("--only", choices=("shipped", "reduced", "hbm"), default=None)
    ap.add_argument("--reuse-engine", default=None,
                    help="take the shipped/reduced sections from an earlier output of this tool, if every engine "
                         "source (RTL, bench, golden) it recorded is byte-identical now; the HBM scan is re-run")
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260926)
    rec = {"schema": "opentallas-hdc-v41x-idx-campaign-v1", "block": "idx",
           "tool": "tools/rtl_hdc_v41x_idx_campaign.py", "arith": G.ARITH, "spec": SPEC,
           "sources": {str(p.relative_to(ROOT)): sha(p) for p in RTL + [VLT, TB, HARNESS, ROOT / "tools/hdc_golden_v41.py",
                                                                        Path(__file__).resolve()]}}
    per_class = 2 if a.quick else 12
    nkeys = (lambda: int(rng.integers(1, 40))) if a.quick else (lambda: int(rng.integers(1, 400)))
    long_n = 512 if a.quick else 16384
    shapes = {"shipped": (32, 4), "reduced": (32, 1)}
    if a.only in (None, "hbm"):
        print("hbm scan", flush=True)
        rec["hbm_scan"] = hbm_scan(work, a.quick)
        rec["sources"].update({str(p.relative_to(ROOT)): sha(p) for p in SCAN_RTL + [SCAN_TB]})
    reused = None
    if a.reuse_engine:
        old = json.loads(Path(a.reuse_engine).read_text())
        eng = [p for p in RTL + [VLT, TB, HARNESS, ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py"]]
        for p in eng:
            k = str(p.relative_to(ROOT))
            if k in old["sources"]:
                assert old["sources"][k] == sha(p), f"{k} changed since {a.reuse_engine}"
        reused = old
        rec["engine_sections_from"] = {"tool_sha256": old["sources"].get("tools/rtl_hdc_v41x_idx_campaign.py"),
                                       "note": "shipped/reduced sections produced by an earlier run of this tool; "
                                               "every engine source it recorded is byte-identical"}
        for k in ("shipped", "reduced", "vehicle_capture_s"):
            if k in old:
                rec[k] = old[k]
    for name, (ih, nb) in shapes.items():
        if reused is not None or (a.only and a.only != name):
            continue
        toks = [finish(rand_token(rng, ih, nb, nkeys(), c)) for c in CLASSES for _ in range(per_class)]
        if name == "reduced":
            t0 = time.time()
            veh = vehicle_tokens(8 if a.quick else a.positions)
            rec["vehicle_capture_s"] = round(time.time() - t0, 1)
            toks += veh
        print(f"{name}: {len(toks)} tokens, {sum(len(t['keep']) for t in toks)} keys", flush=True)
        rec[name] = shape_bench(work, name, ih, nb, a.nk, 64, toks, long_n, rng)
        if name == "reduced":
            rec[name]["vehicle"] = {"tokens": len(veh), "keys": int(sum(len(t["keep"]) for t in veh)),
                                    "layers": sorted({t["cls"] for t in veh})}
    ok = True
    for name in shapes:
        if name not in rec:
            continue
        r = rec[name]
        m, b = r["mixed"], r["back_to_back"]
        exact = m["errors"] == 0 and m["checked"] == m["keys"] and b["errors"] == 0 and b["checked"] == b["keys"] \
            and m["faults_expected_and_raised"] == m["expected_faults"]
        thr = b["keys_per_cycle"] >= 0.99 * a.nk * (1 - 1.0 / max(1, b["beats"]))
        r["verdict"] = {"bit_exact": exact, "throughput_keys_per_cycle": b["keys_per_cycle"],
                        "throughput_ok": thr, "latency_cycles": b["lat_min"],
                        "latency_ok": b["lat_min"] <= SPEC["latency_key_to_score_cycles"]}
        ok &= exact and thr
    if "hbm_scan" in rec:
        ok &= rec["hbm_scan"]["verdict"]["bit_exact"] and rec["hbm_scan"]["verdict"]["meets_90pct_of_peak_with_refresh"]
    rec["die"] = die_summary(rec)
    rec["status"] = "pass" if ok else "fail"
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(rec, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)) + "\n")
    print(json.dumps({k: rec[k].get("verdict") for k in shapes if k in rec}, indent=1))
    print("status", rec["status"])


if __name__ == "__main__":
    main()
