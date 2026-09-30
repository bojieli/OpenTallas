#!/usr/bin/env python3
"""W11: the V4.1 indexer scoring array at spec width (NS=16 slices x NK=4 keys = 64 keys/cycle), bit exact
against tools/hdc_golden_v41.py Model.indexer (chunk8).

The array (rtl/hdc/v41x/ot_hdc_v41x_idx_array.sv) replicates one element, the full-geometry score slice
ot_hdc_v41x_idx_score_slice (NK keys x 32 heads x 128 FP4 dims per cycle), behind one beat handshake.
A flat NS=16/NK=4 elaboration is not simulable locally (a 4-slice NK=4 lint reached ~58 GiB), so:

  * small N, full arithmetic: the array itself at NS=4/NK=1 and NS=2/NK=4 (and NS=4/NK=4 with --quarter),
    random tokens of every numeric class of rtl_hdc_v41x_idx_campaign (typical, wide, underflow, sparse,
    masked, fault) plus golden-quantised normal tokens, candidate masks, reader refusals (scale byte >= 253,
    the collector's rule), source bubbles and sink back-pressure; every score, fault and index compared and
    beat order checked;
  * full N by runtime composition: the spec beat is the reader's 64-slot beat (slot 16q+l = quarter q's key
    l).  Slices share nothing but the beat handshake and the query load, so the NS=2/NK=4 array is run eight
    times, run p carrying beat slots 8p..8p+7 (slices 2p, 2p+1 of the spec array) for all 4,096 beats of a
    262,144-key scan: every key of the scan is scored by the slice position it occupies at NS=16 and compared
    with the golden.  Timing composes as query load + 4,096 beats at the measured II + measured latency.

Data: golden-quantised (qdq_fp4_e8m0) random normal query and keys, golden-formula head weights from random
projections; NOT the checkpoint key image.  Writes results/rtl/w11_idx_array.json.
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41x_idx_campaign as C  # noqa: E402  (sets chunk8)

F = np.float32
OUT = ROOT / "results/rtl/w11_idx_array.json"
RTL = ["rtl/hdc/v41x/ot_hdc_v41x_idx_array.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_idx.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
       "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_delay.sv"]
TB = "rtl/test/tb_hdc_v41x_idx_array.sv"
VLT = "rtl/test/tb_hdc_v41x_idx_array.vlt"
HARNESS = "rtl/test/hdc_v41_tb_harness.cpp"
SOURCES = RTL + [TB, VLT, HARNESS, "tools/rtl_w11_idx_array.py", "tools/rtl_hdc_v41x_idx_campaign.py",
                 "tools/hdc_golden_v41.py", "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_quarter_collect.sv"]
IH, NB, IW, MD = 32, 4, 30, 64
KW = NB * 136
N_FULL = 262144           # L20 keys per die at 1M context (262,144 compressed positions / die)
BEAT = 64                 # reader beat, slots
RE = re.compile(r"V41XARR slots=(\d+) checked=(\d+) errors=(\d+) faults_expected_and_raised=(\d+) refused=(\d+) "
                r"masked=(\d+) beats_in=(\d+) beats_out=(\d+) span=(\d+) in_stall=(\d+) out_stall=(\d+) "
                r"lat_min=(-?\d+) lat_max=(-?\d+) tok_cycles=(\d+) cycles=(\d+)")
RES = re.compile(r"V41XARRSLICE s=(\d+) checked=(\d+) errors=(\d+)")
KEYS = ("slots", "checked", "errors", "faults_expected_and_raised", "refused", "masked", "beats_in", "beats_out",
        "span", "in_stall", "out_stall", "lat_min", "lat_max", "tok_cycles", "cycles")


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


# -- golden-quantised data ---------------------------------------------------------------------------------
def qdq_codes(x):
    """G.qdq_fp4_e8m0 of rows x [..., 128] as (codes, UE8M0 bytes), checked equal to the golden's output."""
    x = np.asarray(x, dtype=F)
    shp = x.shape
    blk = x.reshape(-1, 32)
    amax = np.maximum(np.max(np.abs(blk), axis=1), G.FP4_AMAX_FLOOR_E8M0).astype(F)
    e = G._ceil_log2(G.mul(amax, G.FP4_MAX_INV)).astype(np.int64)
    v = G.qdq_fp4_e8m0(x.reshape(-1)).reshape(-1, 32).astype(np.float64)
    m = np.abs(v) * np.exp2(-e.astype(np.float64))[:, None]
    idx = np.searchsorted(C.E2M1, m)
    idx = np.minimum(idx, 7)
    assert np.array_equal(C.E2M1[idx], m), "qdq output not on the E2M1 x 2^e grid"
    codes = idx + 8 * (v < 0)
    u = e + 127
    assert u.min() >= 0 and u.max() <= 252
    codes, u = codes.reshape(shp), u.reshape(shp[:-1] + (shp[-1] // 32,))
    assert np.array_equal(C.values(codes, u), v.reshape(shp).astype(F))
    return codes, u


def normal_token(rng, n, refuse=0, cand_block=128, keep_p=0.85, name="normal"):
    """Golden-quantised query/keys from normal vectors; weights by the golden's weight line
    to_bf16(mul(linear, index_w_scale)) on a random projection; block-structured candidate mask; `refuse`
    keys given a refused UE8M0 byte (>= 253) as the reader would flag them."""
    qc, qu = qdq_codes(rng.standard_normal((IH, NB * 32)).astype(F))
    kc, ku = qdq_codes(rng.standard_normal((n, NB * 32)).astype(F))
    lin = G.to_bf16((rng.standard_normal(IH) * 3.0).astype(F))
    w = G.to_bf16(G.mul(lin, F((NB * 32) ** -0.5 * IH ** -0.5)))
    nblk = -(-n // cand_block)
    keep = np.repeat(rng.random(nblk) < keep_p, cand_block)[:n]
    keep[-1] = True
    if refuse:
        r = rng.choice(n, refuse, replace=False)
        ku[r, rng.integers(0, NB, refuse)] = rng.integers(253, 256, refuse)
    return C.finish(dict(qc=qc, qu=qu, w=w, kc=kc, ku=ku, keep=keep, cls=name))


def random_tokens(rng, n_each):
    toks = [C.finish(C.rand_token(rng, IH, NB, n_each, cls)) for cls in C.CLASSES]
    return toks


# -- beat layouts ------------------------------------------------------------------------------------------
def reader_beats(n):
    """The collector's 64-slot beats for an n-key scan: [beats, 64] global key index or -1 (empty slot)."""
    qs = (n >> 5) << 3
    qlen = [qs, qs, qs, n - 3 * qs]
    nbeats = max(1, -(-max(qlen) // 16))
    m = np.full((nbeats, BEAT), -1, dtype=np.int64)
    for q in range(4):
        for b in range(nbeats):
            for l in range(16):
                if 16 * b + l < qlen[q]:
                    m[b, 16 * q + l] = q * qs + 16 * b + l
    return m


def contig_beats(n, w):
    nbeats = -(-n // w)
    m = np.arange(nbeats * w, dtype=np.int64).reshape(nbeats, w)
    m[m >= n] = -1
    return m


def slot_index(m, b, j, w):
    """Index to present in slot j of beat b (valid slot: its key; empty slot: the consecutive value)."""
    if m[b, j] >= 0:
        return int(m[b, j])
    g0 = (j // w) * w
    return int(max(m[b, g0], 0) + (j - g0)) if m[b, g0] >= 0 else 0


def write_mems(d: Path, jobs, nk):
    """jobs: [(token, slot map [beats, W])].  Returns (ntok, nslot)."""
    d.mkdir(parents=True, exist_ok=True)
    ql, nl, kl, el = [], [], [], []
    for t, m in jobs:
        for h in range(IH):
            f = [(c, 4) for c in t["qc"][h]] + [(u, 8) for u in t["qu"][h]] + [(int(G.bits(t["w"][h])) >> 16, 16)]
            ql.append(C.hexline(f))
        nl.append(f"{m.shape[0]:08x}")
        ref = np.any(np.asarray(t["ku"]) >= 253, axis=1)
        if "kbits" not in t:
            t["kbits"] = [int(C.hexline([(c, 4) for c in t["kc"][k]] + [(u, 8) for u in t["ku"][k]]), 16)
                          for k in range(len(t["keep"]))]
        kbits = t["kbits"]
        for b in range(m.shape[0]):
            for j in range(m.shape[1]):
                k = int(m[b, j])
                idx = slot_index(m, b, j, nk)
                if k < 0:
                    kl.append(C.hexline([(0, KW), (0, 1), (0, 1), (idx, IW), (0, 1)]))
                    el.append("00000")
                else:
                    word = kbits[k]
                    kl.append(C.hexline([(word, KW), (int(t["keep"][k]), 1), (int(ref[k]), 1), (idx, IW), (1, 1)]))
                    el.append(C.hexline([(t["exp"][k], 16), (int(t["fault"][k]), 1)]))
    for name, lines in (("arr_q.mem", ql), ("arr_n.mem", nl), ("arr_k.mem", kl), ("arr_e.mem", el)):
        (d / name).write_text("\n".join(lines) + "\n")
    return len(jobs), len(kl)


# -- build / run -------------------------------------------------------------------------------------------
VERILATOR = os.environ.get("OT_VERILATOR", "verilator")


def verilator_version():
    return subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip()


# element arithmetic latencies (FPL, FML, QL; ot_hdc_v41x_idx_engine): 3/3/3 as built, --lat for the 1.2 GHz
# streaming build (adds ot_hdc_fp32_add_lat.sv)
LAT = {"FPL": 3, "FML": 3, "QL": 3}


def rtl():
    return RTL + (["rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv"] if LAT["FPL"] != 3 else [])


def build(work: Path, ns, nk, jobs=8):
    tag = re.sub(r"[^0-9.]", "", verilator_version().split()[1])
    lt = "" if LAT == {"FPL": 3, "FML": 3, "QL": 3} else "_lat{FPL}_{FML}_{QL}".format(**LAT)
    obj = work / f"obj_ns{ns}_nk{nk}_v{tag}{lt}"
    exe = obj / "Vtb_hdc_v41x_idx_array"
    stamp = hashlib.sha256(b"".join((ROOT / p).read_bytes() for p in rtl() + [TB, VLT, HARNESS])).hexdigest()
    if exe.exists() and (obj / "stamp").exists() and (obj / "stamp").read_text() == stamp:
        return exe, None
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-O3", "--x-assign", "fast", "--x-initial", "fast",
           "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-DECLFILENAME", "-Wno-UNOPTFLAT",
           "--top-module", "tb_hdc_v41x_idx_array", f"-GNS={ns}", f"-GNK={nk}"] + \
          [f"-G{k}={v}" for k, v in LAT.items()] + [
           "-CFLAGS", "-DVTOP=Vtb_hdc_v41x_idx_array -O1", "-j", str(jobs), "--Mdir", str(obj),
           str(ROOT / VLT), str(ROOT / TB)] + [str(ROOT / p) for p in rtl()] + [str(ROOT / HARNESS)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
    (obj / "stamp").write_text(stamp)
    dt = time.time() - t0
    print(f"  built {obj.name} in {dt:.0f} s", flush=True)
    return exe, dt


def run(exe: Path, d: Path, ntok, nslot, seed=1, bubble=0, ordy=0):
    t0 = time.time()
    r = subprocess.run([str(exe), f"+NTOK={ntok}", f"+NSLOT={nslot}", f"+SEED={seed}", f"+BUBBLE={bubble}",
                        f"+ORDY={ordy}"], cwd=d, capture_output=True, text=True, timeout=86400)
    m = RE.search(r.stdout)
    if not m:
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
    res = dict(zip(KEYS, map(int, m.groups())))
    res["per_slice"] = [dict(slice=int(a), checked=int(b), errors=int(c)) for a, b, c in RES.findall(r.stdout)]
    res["mismatch_lines"] = [ln for ln in r.stdout.splitlines()
                             if ln.startswith(("MISMATCH", "MISS-FAULT", "INDEX", "KV-SLOT", "LAST-TAG"))][:10]
    res["bubble_16ths"], res["sink_refuse_16ths"], res["seed"] = bubble, ordy, seed
    res["wall_s"] = round(time.time() - t0, 1)
    return res


# -- cases: prepare (golden, numpy) / sim (Verilator only) / record ------------------------------------------
SMALL_CFG = [(4, 1, 21), (2, 4, 22)]
QUARTER_CFG = [(4, 4, 23)]
SMALL_RUNS = [dict(seed=3, bubble=4, ordy=6), dict(seed=5, bubble=0, ordy=0)]


def prepare_small(work: Path, ns, nk, seed):
    """Array exactness at reduced replica count, full arithmetic: mem files + meta."""
    rng = np.random.default_rng(seed)
    w = ns * nk
    toks = random_tokens(rng, 181) + [normal_token(rng, 517, refuse=9, cand_block=32, keep_p=0.7, name="normal.a"),
                                      normal_token(rng, 1000, refuse=3, cand_block=128, name="normal.b")]
    jobs, layouts = [], []
    for i, t in enumerate(toks):
        n = len(t["keep"])
        if BEAT % w == 0 and i % 2 == 1:           # a window of the reader's 64-slot beat
            p = (i // 2) % (BEAT // w)
            m = reader_beats(n)[:, p * w:(p + 1) * w]
            layouts.append(f"reader64.slots{p * w}-{p * w + w - 1}")
        else:
            m = contig_beats(n, w)
            layouts.append("contiguous")
        jobs.append((t, m))
    d = work / f"small_ns{ns}_nk{nk}"
    ntok, nslot = write_mems(d, jobs, nk)
    return dict(kind="small", ns=ns, nk=nk, dir=d.name, ntok=ntok, nslot=nslot, keys_per_cycle=w,
                token_classes=[t["cls"] for t, _ in jobs], layouts=layouts,
                keys=int(sum(int((m >= 0).sum()) for _, m in jobs)),
                expected_faults=int(sum(int(np.sum(t["fault"][m[m >= 0]])) for t, m in jobs)),
                expected_refused=int(sum(int(np.any(np.asarray(t["ku"])[m[m >= 0]] >= 253, axis=1).sum())
                                         for t, m in jobs)),
                expected_masked=int(sum(int((~np.asarray(t["keep"])[m[m >= 0]]).sum()) for t, m in jobs)),
                runs=SMALL_RUNS)


def prepare_full(work: Path, seed, ns=2, nk=4):
    """262,144 keys at the spec NS=16/NK=4 beat, as 64/(ns*nk) runs of the reduced array over slot windows."""
    rng = np.random.default_rng(seed)
    t0 = time.time()
    tok = normal_token(rng, N_FULL, refuse=64, cand_block=128, name="normal.L20.full")
    gen_s = time.time() - t0
    m64 = reader_beats(N_FULL)
    assert m64.shape == (N_FULL // BEAT, BEAT) and (m64 >= 0).all()
    w = ns * nk
    parts = []
    for p in range(BEAT // w):
        d = work / f"full_p{p}"
        m = m64[:, p * w:(p + 1) * w]
        ntok, nslot = write_mems(d, [(tok, m)], nk)
        shares = []
        for s in range(ns):
            sidx = p * ns + s
            keys = m64[:, sidx * nk:(sidx + 1) * nk]
            shares.append(dict(spec_slice=sidx, quarter=sidx // 4, beat_slots=[sidx * nk, sidx * nk + nk - 1],
                               keys=int(keys.size), index_range=[int(keys.min()), int(keys.max())],
                               expected_faults=int(tok["fault"][keys.reshape(-1)].sum())))
        parts.append(dict(dir=d.name, ntok=ntok, nslot=nslot, seed=11 + p, shares=shares))
    return dict(kind="full", ns=ns, nk=nk, keys=N_FULL, gen_s=round(gen_s, 1), parts=parts,
                expected_faults=int(tok["fault"].sum()), masked_keys=int((~tok["keep"]).sum()),
                refused_keys=int(np.any(tok["ku"] >= 253, axis=1).sum()))


def phase_prepare(work: Path, quarter: bool, skip_full: bool):
    cfg = SMALL_CFG + (QUARTER_CFG if quarter else [])
    meta = dict(small=[prepare_small(work, ns, nk, sd) for ns, nk, sd in cfg],
                full=None if skip_full else prepare_full(work, 31))
    (work / "meta.json").write_text(json.dumps(meta, indent=1))
    print("prepared", work)


def phase_sim(work: Path, par: int, only: str = ""):
    meta = json.loads((work / "meta.json").read_text())
    if only:
        keep = {tuple(map(int, c.split("x"))) for c in only.split(",")}
        meta["small"] = [c for c in meta["small"] if (c["ns"], c["nk"]) in keep]
        if meta["full"] and (meta["full"]["ns"], meta["full"]["nk"]) not in keep:
            meta["full"] = None
    cfgs = sorted({(c["ns"], c["nk"]) for c in meta["small"]} | ({(meta["full"]["ns"], meta["full"]["nk"])}
                                                                    if meta["full"] else set()))
    def try_build(c):
        try:
            return build(work, *c)
        except Exception as e:  # noqa: BLE001  (a killed or failed build is recorded, not fatal)
            return None, f"build failed: {str(e)[-400:]}"
    with ThreadPoolExecutor(len(cfgs)) as ex:
        built = dict(zip(cfgs, ex.map(try_build, cfgs)))
    tasks = []
    for c in meta["small"]:
        if built[(c["ns"], c["nk"])][0] is None:
            continue
        for r in c["runs"]:
            tasks.append((("small", c["ns"], c["nk"], r["seed"]), built[(c["ns"], c["nk"])][0], work / c["dir"],
                          c["ntok"], c["nslot"], r))
    if meta["full"]:
        f = meta["full"]
        for pt in f["parts"]:
            tasks.append((("full", f["ns"], f["nk"], pt["dir"]), built[(f["ns"], f["nk"])][0], work / pt["dir"],
                          pt["ntok"], pt["nslot"], dict(seed=pt["seed"], bubble=0, ordy=0)))
    with ThreadPoolExecutor(par) as ex:
        res = list(ex.map(lambda t: run(t[1], t[2], t[3], t[4], **t[5]), tasks))
    out = dict(host=os.uname().nodename, verilator=verilator_version(),
               driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), builds={f"{a}x{b}": v[1] for (a, b), v in built.items()},
               results=[dict(key=list(t[0]), **r) for t, r in zip(tasks, res)])
    (work / f"sims{('_' + only.replace(',', '_')) if only else ''}.json").write_text(json.dumps(out, indent=1))
    print("simulated", len(res))


def phase_record(work: Path):
    meta = json.loads((work / "meta.json").read_text())
    sims = dict(host=set(), verilator=set(), builds={}, results=[], sim_phase=[])
    for fp in sorted(work.glob("sims*.json")):
        d = json.loads(fp.read_text())
        sims["host"].add(d["host"])
        sims["sim_phase"].append(dict(file=fp.name, host=d["host"], verilator=d["verilator"],
                                      driver_sha256=d.get("driver_sha256"),
                                      configs=sorted({f"{r['key'][1]}x{r['key'][2]}" for r in d["results"]})))
        sims["verilator"].add(d["verilator"])
        sims["builds"].update(d["builds"])
        sims["results"] += d["results"]
    sims["host"], sims["verilator"] = sorted(sims["host"]), sorted(sims["verilator"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--"] + SOURCES, cwd=ROOT, capture_output=True,
                           text=True).stdout.strip()
    small = []
    for c in meta["small"]:
        runs = [r for r in sims["results"] if r["key"][:3] == ["small", c["ns"], c["nk"]]]
        c = dict(c, build=sims["builds"].get(f"{c['ns']}x{c['nk']}"), runs=runs)
        c["exact"] = len(runs) == len(SMALL_RUNS) and all(
            r["errors"] == 0 and r["checked"] == c["keys"] and r["faults_expected_and_raised"] == c["expected_faults"]
            and r["refused"] == c["expected_refused"] and r["masked"] == c["expected_masked"]
            and r["beats_in"] == r["beats_out"] for r in runs)
        if not runs:
            c["exact"] = None
            c["status"] = "not simulated: " + str(c["build"] or "no sim-phase result for this configuration")
        small.append(c)
    gated = [c for c in small if c["runs"]]
    nostall = [c["runs"][1] for c in gated]
    rec_full = None
    f = meta["full"]
    if f:
        byd = {r["key"][3]: r for r in sims["results"] if r["key"][0] == "full"}
        runs = [byd[pt["dir"]] for pt in f["parts"]]
        shares = []
        for pt, r in zip(f["parts"], runs):
            for sh, ps in zip(pt["shares"], r["per_slice"]):
                shares.append(dict(sh, checked=ps["checked"], errors=ps["errors"]))
        errors = sum(r["errors"] for r in runs)
        checked = sum(r["checked"] for r in runs)
        beats = N_FULL // BEAT
        span = max(r["span"] for r in runs)
        lat, lat_min = max(r["lat_max"] for r in runs), min(r["lat_min"] for r in runs)
        tokc = max(r["tok_cycles"] for r in runs)
        rec_full = dict(
            keys=N_FULL, beats=beats, beat_slots=BEAT, spec_ns=16, spec_nk=4,
            simulated_array=dict(ns=f["ns"], nk=f["nk"], runs=len(runs),
                                 method="run p carries reader-beat slots 8p..8p+7 (spec slices 2p, 2p+1) for all "
                                        "4,096 beats of the scan; the reader beat layout is the collector's "
                                        "(slot 16q+l = quarter q's key l)"),
            data=dict(kind="golden-quantised random normal query/keys (G.qdq_fp4_e8m0), golden-formula BF16 head "
                           "weights on a random projection, candidate mask in 128-key blocks (~85% kept), 64 keys "
                           "with a refused UE8M0 byte; NOT the checkpoint key image",
                      seed=31, generation_s=f["gen_s"], expected_faults=f["expected_faults"],
                      masked_keys=f["masked_keys"], refused_keys=f["refused_keys"]),
            checked=checked, errors=errors,
            faults_expected_and_raised=sum(r["faults_expected_and_raised"] for r in runs),
            per_share=shares,
            runs=[{k: v for k, v in r.items() if k != "per_slice"} for r in runs],
            timing=dict(query_load_cycles=IH, accept_span_cycles=span, measured_ii=span / beats,
                        latency_first_beat_cycles=lat_min, latency_max_cycles=lat,
                        in_stall=sum(r["in_stall"] for r in runs),
                        in_stall_note="3 cycles per run after the last query-load beat (the engine's qsettle: "
                                      "the query registers are written 3 edges after the q-load beat); none "
                                      "inside the 4,096-beat accept span",
                        composed_cycles_query_to_last_score=tokc,
                        composition="each run streams the same 4,096 beats with an always-ready sink; the spec "
                                    "array's i_ready is the AND of identical slice readies, so it accepts on the "
                                    "same edges as every run: cycles = max over runs (query-load start to last "
                                    "score beat consumed)",
                        model=dict(array_floor_beats=beats, reader_bound_cycles=5120,
                                   floor_plus_query_plus_latency=beats + IH + lat)),
            exact=errors == 0 and checked == N_FULL and len(shares) == 16
            and all(s["errors"] == 0 and s["checked"] == s["keys"] for s in shares)
            and sum(r["faults_expected_and_raised"] for r in runs) == f["expected_faults"])
    nk = 4
    q4dot = nk * IH * NB
    qbits = IH * (NB * 136 + 16)
    meta_bits = MD * (IW + nk + 1)
    ofifo_bits = MD * nk * 18
    elem = dict(module="ot_hdc_v41x_idx_score_slice", nk=nk, heads=IH, head_dim=NB * 32,
                q4dot_units=q4dot, logical_fp4_macs_per_cycle=q4dot * 32,
                key_in_bits_per_cycle=nk * KW, key_meta_in_bits_per_cycle=nk * 3 + 1 + IW,
                query_load_port_bits=8 + NB * 128 + NB * 8 + 16, query_register_bits=qbits,
                score_out_bits_per_cycle=nk * 16, index_out_bits_per_cycle=nk * IW,
                out_flag_bits_per_cycle=2 * nk + 1,
                metadata_fifo_bits=meta_bits, metadata_fifo=f"{MD} x {IW + nk + 1}",
                engine_output_fifo_bits=ofifo_bits, engine_output_fifo=f"{MD} x {nk * 18}",
                query_load_pipeline_bits=(IH // 8) * (1 + 8 + 2 * (NB * 128 + NB * 8 + 16) + 8),
                query_load_pipeline="per 8-head chunk tile: valid, head, two staged q beats, 8 write enables")
    ns = 16
    arr = dict(module="ot_hdc_v41x_idx_array", ns=ns, nk=nk, keys_per_cycle=ns * nk,
               q4dot_units=ns * q4dot, logical_fp4_macs_per_cycle=ns * q4dot * 32,
               beat_key_bits_per_cycle=ns * nk * KW, beat_key_bits_check=BEAT * 544,
               beat_meta_bits_per_cycle=ns * nk * (IW + 3) + ns,
               query_register_bits=ns * qbits, query_register_kib=ns * qbits / 8 / 1024,
               metadata_fifo_bits=ns * meta_bits, engine_output_fifo_bits=ns * ofifo_bits,
               score_out_bits_per_cycle=ns * nk * 16, index_out_bits_per_cycle=ns * nk * IW,
               out_beat_bits_per_cycle=ns * nk * (16 + IW + 2) + ns,
               handshake="single i_valid/i_ready = AND of 16 slice readies; atomic o_valid = AND of 16 slice "
                         "valids, one o_ready broadcast; query load broadcast, ql_ready = AND")
    assert arr["beat_key_bits_per_cycle"] == 34816

    ok_small = all(s["exact"] for s in gated) and {(s["ns"], s["nk"]) for s in gated} >= {(4, 1), (2, 4)}
    ok_full = rec_full["exact"] if rec_full else None
    rec = dict(
        schema="opentallas.w11-idx-array.v1",
        block="V4.1 indexer scoring array (dedicated unit), spec NS=16 x NK=4 = 64 keys/cycle per die",
        tool="tools/rtl_w11_idx_array.py",
        git_head=head, sources_dirty_at_run=bool(dirty),
        source_sha256={p: sha(p) for p in SOURCES + [x for x in rtl() if x not in SOURCES]},
        element_latencies=dict(LAT),
        golden="tools/hdc_golden_v41.py Model.indexer lines under chunk8: dots_q4 (block dots rounded once, csum), "
               "to_bf16, relu*w to_bf16, reduce_rows(csum) to_bf16; candidate mask -inf; faults/refusals -> 0+fault",
        parameters=dict(spec_ns=16, spec_nk=4, nb=NB, ih=IH, iw=IW, md=MD, verilator=sims.get("verilator")),
        element=elem, array=arr,
        sim_host=sims.get("host"),
        sim_phase=sims["sim_phase"],
        sim_phase_note="the sim phase (Verilator build + runs) executed on the listed host from a byte-identical "
                       "copy of every RTL/bench source pinned above; the driver's record phase was edited after "
                       "the sim phase ran, so the sim-phase driver hash is listed separately",
        small_n=small,
        element_timing_from_small_n=[dict(ns=s["ns"], nk=s["nk"], lat_min=r["lat_min"], lat_max=r["lat_max"],
                                          beats=r["beats_in"], span=r["span"], in_stall=r["in_stall"],
                                          query_settle_stalls=r["in_stall"],
                                          ii=r["span"] / max(1, r["beats_in"]))
                                     for s, r in zip(gated, nostall)],
        full_n=rec_full,
        verdict=dict(small_n_exact=ok_small, full_n_exact=ok_full,
                     pass_=bool(ok_small and (ok_full is None or ok_full))),
        limits=["flat NS=16/NK=4 array not elaborated; full N is composed from NS=2/NK=4 array runs over the "
                "spec beat's slot windows (the slices share only the beat handshake and the query load)",
                "data are golden-quantised random normal vectors, not the released checkpoint's key image",
                "no reader or selector in this gate; reader-bound 5,120 cycles is the model figure",
                "no synthesis/place-and-route: the 16-way ready AND and 34,816-bit beat fanout are not timed"])
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(OUT, "small", ok_small, "full", ok_full)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/tmp/claude-1000/w11sim/idx/work")
    ap.add_argument("--phase", choices=("all", "prepare", "sim", "record"), default="all",
                    help="prepare (golden, needs numpy 2) / sim (Verilator; may run on another host) / record")
    ap.add_argument("--quarter", action="store_true", help="also gate NS=4/NK=4 (the four-slice quarter)")
    ap.add_argument("--skip-full", action="store_true")
    ap.add_argument("--par", type=int, default=12)
    ap.add_argument("--configs", default="", help="sim only these NSxNK configs, e.g. 2x4,4x1")
    ap.add_argument("--lat", default=None, help="FPL,FML,QL element latencies (default 3,3,3 = as built)")
    ap.add_argument("--output", default=None, help="record path (default results/rtl/w11_idx_array.json)")
    a = ap.parse_args()
    global OUT
    if a.lat:
        LAT.update(zip(("FPL", "FML", "QL"), map(int, a.lat.split(","))))
    if a.output:
        OUT = Path(a.output)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    if a.phase in ("all", "prepare"):
        phase_prepare(work, a.quarter, a.skip_full)
    if a.phase in ("all", "sim"):
        phase_sim(work, a.par, a.configs)
    if a.phase in ("all", "record"):
        phase_record(work)


if __name__ == "__main__":
    main()
