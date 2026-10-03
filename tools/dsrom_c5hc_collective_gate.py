#!/usr/bin/env python3
"""DS-ROM C5hc collective gate: RTL-measured stage collectives for C5hc (TP-8, 4 packages x 2 dies) and C1 (PAR2,
4 owner dies in 4 packages), on the W15 physical link layer, re-priced in the unified model.

    python3 tools/dsrom_c5hc_collective_gate.py measure   # builds, calibrates release, measures (Verilator)
    python3 tools/dsrom_c5hc_collective_gate.py reprice   # re-prices C1 and C5hc with the measured fits, verdict
    python3 tools/dsrom_c5hc_collective_gate.py verify    # re-derives the reprice from the committed measurements

Bench: rtl/test/tb_dsrom_hcoll.sv; engine: rtl/rom/collectives/ot_rom_hcoll_die.sv; link layer (unchanged):
rtl/link/ot_w15_link_{tx,rx}.sv, ot_link_chan_model.sv, ot_link_afifo.sv, ot_link_crc32*.sv.
Decision rule (committed before measuring): results/rtl/dsrom_c5hc_collective_gate_20261003/decision_rule.json.
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "results/rtl/dsrom_c5hc_collective_gate_20261003"
SCRATCH = Path(os.environ.get("C5HC_SCRATCH", "/tmp/claude-review-20261003/c5hc"))
BUILD = SCRATCH / "build"
VEC = SCRATCH / "vec"
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
VFLAGS = ["--binary", "--timing", "-CFLAGS", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD", "-Wno-lint",
          "-Wno-style", "-Wno-MULTIDRIVEN"]
SRC = ["rtl/test/tb_dsrom_hcoll.sv", "rtl/rom/collectives/ot_rom_hcoll_die.sv", "rtl/link/ot_link_afifo.sv",
       "rtl/link/ot_link_crc32.sv", "rtl/link/ot_link_crc32_pipe.sv", "rtl/link/ot_w15_link_tx.sv",
       "rtl/link/ot_w15_link_rx.sv", "rtl/link/ot_link_chan_model.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
       "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv"]
CLOCK_HZ = 1 / 0.834e-9   # the bench's core clock (T_CORE): measured cycles convert at it, not at 1.2 GHz
T_CORE = 0.834          # 2 ps grid (see board_params); 1.199 GHz, cycles are reported at the core clock
MAXW = 2048
SPACING = 0       # self-timed: each die issues op k+1 GAP cycles after its own op k completed (the dies complete
GAP = 600         # within a few cycles of each other, so every op starts on idle links; latency = last commit on the
                  # slowest die - first issue on any die, so the issue skew is charged, not hidden)
GUARD = 3        # tools/w15_collectives.GUARD: release margin past the worst calibrated arrival

# ---- link basis ------------------------------------------------------------------------------------------------
# 112G PAM4 lanes, RS(272,257) light FEC (tools/w15_collectives.LINKS board_112g); fc4 package budget: 90 lanes,
# 5 links (3 quad + 2 stage-hop) = 18 lanes a package link (decode_critical_path.ArrayFabric, dies_per_package 2)
W15_CHAN_FIXED_NS = 3.0 + 2.0 + 50.0      # tx analog + flight + rx AFE/DSP
W15_DEC_NS = 10.0 + 45.0                  # deskew/align + RS(272,257) decode
W15_ENC_NS = 4.0
LANES_PER_PKG_LINK = 18


def board_params(lanes=None, bytes_s=None):
    """X_T (PCS clock = half a codeword), encode / decode stages and channel delay for a board link."""
    if lanes is not None:
        cw = 2720 / (lanes * 112.0)
    else:   # a frame of 4 x 64 B records per codeword at the given payload rate
        cw = 4 * 64 / (bytes_s / 1e9)
    # the PCS clock on a 2 ps grid: the bench's half period must be exact at the 1 ps timescale precision, or the
    # channel model's recovered clock (n x T_NS) drifts against the simulated transmit clock (measured: -70 cycles of
    # board latency over 140,000 cycles at X_T = 1.34921 ns, whose half period rounds to 0.675 ns)
    xt = round(cw / 2 / 0.002) * 0.002
    return dict(X_T=round(xt, 5), X_ENC=max(1, round(W15_ENC_NS / xt)), X_DEC=round(W15_DEC_NS / xt),
                X_DLY=round(W15_CHAN_FIXED_NS + cw, 3), codeword_ns=round(cw, 4),
                payload_GBps=round(4 * 64 / cw, 1))


def model_link_bw():
    if os.environ.get("C5HC_MODEL_LINK_BW"):          # remote hosts without the model's inputs
        return float(os.environ["C5HC_MODEL_LINK_BW"])
    import uarch_model_parallelism as M
    return M.fabric(8, "fc4").link_bw


CONFIGS = {
    # verdict basis: 112G lanes; C5hc's 18-lane package link split into two 9-lane counterpart planes
    "c5hc_phys": dict(PD=2, lanes=9, DEPTH=1024),
    "c1_phys": dict(PD=1, lanes=18, DEPTH=1024),
    # sensitivity: the model's fc4 link_bw (237 GB/s a package link)
    "c5hc_modelbw": dict(PD=2, bw_frac=0.5, DEPTH=1024),
    "c1_modelbw": dict(PD=1, bw_frac=1.0, DEPTH=1024),
    # backpressure / exactness stress: 64-word FIFOs and a VM write port stalled 30% of cycles
    "c5hc_bp": dict(PD=2, lanes=9, DEPTH=64, WSTALL=30),
    "c1_bp": dict(PD=1, lanes=18, DEPTH=64, WSTALL=30),
}


def cfg_params(name):
    c = CONFIGS[name]
    bp = board_params(lanes=c["lanes"]) if "lanes" in c else board_params(bytes_s=model_link_bw() * c["bw_frac"])
    gen = dict(PD=c["PD"], DEPTH=c["DEPTH"], ADD_LAT=7, T_CORE=T_CORE, U_WIRE=34, X_WIRE=45, MAXW=MAXW,
               X_T=bp["X_T"], X_ENC=bp["X_ENC"], X_DEC=bp["X_DEC"])
    return gen, bp


# ---- payloads -----------------------------------------------------------------------------------------------------
# per-position payloads (bytes, whole collective) of the stage collectives (dsrom_parallelism graph), C5hc span 8 and
# C1 span 4, at P = 1 (AR) and P = 6 (uarch_model.V41_POSITIONS, the MTP verify pass); sizes past MAXW words a rank
# are priced on the linear fit
GATHER_PAYLOADS = (32, 1536, 3648, 4672, 7744, 20480, 32768, 67584, 68096, 131072, 215040)
REDUCE_PAYLOADS = (20480,)


def op_list(pd):
    span = 4 * pd
    g = sorted({max(1, math.ceil(p * P / span / 64)) for p in GATHER_PAYLOADS for P in (1, 6)} | {1, 2, 4, 32, 128})
    r = sorted({max(1, math.ceil(p * P / 64)) for p in REDUCE_PAYLOADS for P in (1, 6)} | {1, 8, 40, 160})
    ops = [("all_gather", n) for n in g if n <= MAXW] + [("all_reduce", n) for n in r if n <= MAXW]
    return ops


# ---- golden ---------------------------------------------------------------------------------------------------------
def golden_mod():
    os.environ["HDC_V41_ARITH"] = "chunk8"
    import hdc_golden_v41 as G
    assert G.ARITH == "chunk8"
    return G


def wo_b_case(G, ranks, seed=20261003):
    """A full-shape wo_b (5,120 x 8,192, FP8 E4M3 weights, UE8M0 block scales) and an FP8 z: the golden linear_q
    block sums, the per-rank aligned subtree partials (K split `ranks` ways on chunk boundaries) and the golden
    csum.  Returns (partials [ranks, 5120] float32, golden acc float32, checks)."""
    rng = np.random.default_rng(seed)
    rows, k = 5120, 8192
    tab = G._e4m3_table()
    codes = rng.integers(0, 256, size=(rows, k))
    codes = np.where(np.isnan(tab[codes]), 0, codes)
    q = tab[codes]
    e = rng.integers(-9, -5, size=(rows, k // 32)).astype(np.int64)
    w = G.Q8(q, e)
    x = (rng.standard_normal(k) * 0.7).astype(G.F)
    xq, xe = G.quant_fp8(x)
    blocks = np.stack([np.ldexp((w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(G.F),
                                w.e[:, b] + xe[b]).astype(G.F) for b in range(k // 32)], axis=-1)
    acc = G.csum(blocks)
    per = blocks.shape[1] // ranks
    parts = np.stack([G.csum(blocks[:, r * per:(r + 1) * per]) for r in range(ranks)])
    t = list(parts)
    while len(t) > 1:
        t = [G.add(t[i], t[i + 1]) for i in range(0, len(t), 2)]
    tree_ok = bool(np.array_equal(t[0].view(np.uint32), acc.view(np.uint32)))
    lin = G.linear_q(w, x)
    lin_ok = bool(np.array_equal(G.to_bf16(acc).view(np.uint32), np.asarray(lin, dtype=G.F).view(np.uint32)))
    return parts.astype(np.float32), acc.astype(np.float32), dict(
        shape=[rows, k], k_blocks=k // 32, chunk=G.CHUNK, chunks=k // 32 // G.CHUNK, ranks=ranks,
        chunks_per_rank=k // 32 // G.CHUNK // ranks, tree_of_rank_partials_equals_golden_csum=tree_ok,
        to_bf16_equals_golden_linear_q=lin_ok, seed=seed)


def tree(G, parts):
    t = list(parts)
    while len(t) > 1:
        t = [G.add(t[i], t[i + 1]) for i in range(0, len(t), 2)]
    return t[0]


def fixture(name):
    gen, _ = cfg_params(name)
    pd = gen["PD"]
    N = 4 * pd
    ops = op_list(pd)
    d = VEC / f"pd{pd}"
    stamp = d / "ops.json"
    if stamp.exists() and json.loads(stamp.read_text())["ops"] == [list(o) for o in ops]:
        return d, ops, json.loads(stamp.read_text())
    G = golden_mod()
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7 + pd)
    parts, acc, chk = wo_b_case(G, N)
    part = np.zeros((len(ops), N, MAXW, 16), np.uint32)
    exp = np.zeros((len(ops), N * MAXW, 16), np.uint32)
    for i, (mode, n) in enumerate(ops):
        if mode == "all_reduce" and n == 320:
            v = parts.reshape(N, 320, 16)
            part[i, :, :n] = v.view(np.uint32)
            exp[i, :n] = acc.reshape(320, 16).view(np.uint32)
            continue
        v = (rng.standard_normal((N, n, 16)) * np.exp2(rng.integers(-20, 20, (N, n, 16)))).astype(np.float32)
        part[i, :, :n] = v.view(np.uint32)
        if mode == "all_gather":
            exp[i, :N * n] = v.view(np.uint32).reshape(N * n, 16)
        else:
            exp[i, :n] = tree(G, [v[r] for r in range(N)]).astype(np.float32).view(np.uint32)

    def wr(path, arr):
        with open(path, "w") as f:
            for row in arr.reshape(-1, 16):
                f.write("".join(f"{int(x):08x}" for x in row[::-1]) + "\n")
    wr(d / "part.hex", part)
    wr(d / "expected.hex", exp)
    with open(d / "desc.hex", "w") as f:
        for mode, n in ops:
            f.write(f"{((1 << 31) if mode == 'all_gather' else 0) | n:08x}\n")
    meta = dict(ops=[list(o) for o in ops], wo_b=chk, part_sha256=sha(d / "part.hex"),
                expected_sha256=sha(d / "expected.hex"), desc_sha256=sha(d / "desc.hex"))
    stamp.write_text(json.dumps(meta, indent=1))
    return d, ops, meta


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---- build / run ----------------------------------------------------------------------------------------------------
def build(name):
    gen, _ = cfg_params(name)
    d = BUILD / name
    exe = d / "Vtb_dsrom_hcoll"
    stamp = d / "stamp.json"
    want = dict(pins={p: sha(ROOT / p) for p in SRC}, gen=gen, vflags=VFLAGS)
    if exe.exists() and stamp.exists() and json.loads(stamp.read_text()) == want:
        return exe
    subprocess.run(["rm", "-rf", str(d)], check=True)
    d.mkdir(parents=True)
    cmd = [str(VERILATOR), *VFLAGS, "-j", "8", "--top-module", "tb_dsrom_hcoll", "-Mdir", str(d),
           *(["-DHC_N8"] if gen["PD"] == 2 else []), *[f"-G{k}={v}" for k, v in gen.items()], *SRC]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"build {name} failed:\n{r.stderr[-4000:]}")
    stamp.write_text(json.dumps(want))
    return exe


OPL = re.compile(r"OP op=(\d+) die=(\d+) mode=(\d+) words=(\d+) issue=(-?\d+) first_vm=(-?\d+) last_vm=(-?\d+) "
                 r"writes=(-?\d+)")
LKL = re.compile(r"LINK src=(\d+) dst=(\d+) class=(\w+) age_min=(\d+) age_max=(\d+) wait_max=(\d+) wire=(\d+) "
                 r"faults=(\d)(\d)(\d)(\d)")
DONE = re.compile(r"HCDONE seed=(-?\d+) det=(\d+) u_drel=(\d+) x_drel=(\d+) faults=(\d+) mismatches=(\d+)")


def run(name, seed, det, drel, chan=None, timeout=4 * 3600):
    gen, bp = cfg_params(name)
    exe = build(name)
    vec, ops, _ = fixture(name)
    c = CONFIGS[name]
    chan = dict(dict(X_DLY=bp["X_DLY"], X_JS=3.0, U_DLY=2.0, U_JS=0.5), **(chan or {}))
    tagd = "_".join(f"{k}{v}" for k, v in sorted({**drel, **chan}.items()))
    out = SCRATCH / "runs" / name / f"s{seed}_d{det}_{tagd}"
    out.mkdir(parents=True, exist_ok=True)
    args = [str(exe), f"+SEED={seed}", f"+VEC={vec}", f"+OPS={len(ops)}", f"+DET={det}", f"+SPACING={SPACING}", f"+GAP={GAP}",
            f"+WSTALL={c.get('WSTALL', 0)}"] + [f"+{k}={v}" for k, v in {**drel, **chan}.items()]
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    log = r.stdout + r.stderr
    (out / "log.txt").write_text(log)
    rows = [dict(zip(("op", "die", "mode", "words", "issue", "first_vm", "last_vm", "writes"), map(int, m.groups())))
            for m in OPL.finditer(log)]
    links = [dict(src=int(m[1]), dst=int(m[2]), cls=m[3], age_min=int(m[4]), age_max=int(m[5]),
                  wait_max=int(m[6]), wire=int(m[7]), faults=[int(m[8]), int(m[9]), int(m[10]), int(m[11])])
             for m in LKL.finditer(log)]
    dn = DONE.search(log)
    res = dict(seed=seed, det=det, drel=drel, chan=chan, completed=bool(dn), faults=int(dn[5]) if dn else None,
               mismatches=int(dn[6]) if dn else None, late=log.count("HCLATE"), fatal="%Error" in log or
               "%Fatal" in log, timeout="HCTIMEOUT" in log, ops=rows, links=links,
               timing_sha256=hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest())
    n = 4 * gen["PD"]
    res["writes_ok"] = all(r_["writes"] == (n * r_["words"] if r_["mode"] else r_["words"]) for r_ in rows) and \
        len(rows) == len(ops) * n
    res["passed"] = res["completed"] and res["faults"] == 0 and res["mismatches"] == 0 and not res["fatal"] and \
        res["late"] == 0 and res["writes_ok"]
    return res


def corners(name):
    _, bp = cfg_params(name)
    lo = dict(X_DLY=bp["X_DLY"], X_JS=0.0, U_DLY=2.0, U_JS=0.0)
    hi = dict(X_DLY=round(bp["X_DLY"] + 3.0, 4), X_JS=0.0, U_DLY=2.5, U_JS=0.0)
    return [lo, hi]


def arrivals(res):
    out = {}
    for l in res["links"]:
        a = out.setdefault(l["cls"], [10 ** 9, 0])
        a[0] = min(a[0], l["age_min"] + l["wire"])
        a[1] = max(a[1], l["age_max"] + l["wire"])
    return out


def summarize(res, ops):
    by = {}
    for r in res["ops"]:
        by.setdefault(r["op"], []).append(r)
    rows = []
    for k in sorted(by):
        dies = by[k]
        issue = min(o["issue"] for o in dies)
        last = max(o["last_vm"] for o in dies)
        lat = last - issue + 1
        mode, n = ops[k]
        rows.append(dict(op=k, mode=mode, words_per_rank=n if mode == "all_gather" else None,
                         words=n, payload_bytes=(n * 64 * len(dies) if mode == "all_gather" else n * 64),
                         issue_to_last_commit_cycles=lat, issue_to_last_commit_ns=round(lat / CLOCK_HZ * 1e9, 1),
                         per_die_issue_to_last_commit=[o["last_vm"] - o["issue"] + 1 for o in dies],
                         issue_to_first_commit_cycles=min(o["first_vm"] for o in dies) - issue + 1))
    return rows


def fit(rows):
    out = {}
    for mode in ("all_gather", "all_reduce"):
        pts = [(r["words"], r["issue_to_last_commit_cycles"]) for r in rows if r["mode"] == mode]
        x = np.array([p[0] for p in pts], float)
        y = np.array([p[1] for p in pts], float)
        b, a = np.polyfit(x, y, 1)
        resid = y - (a + b * x)
        out[mode] = dict(fixed_cycles=round(float(a), 2), cycles_per_word=round(float(b), 4),
                         max_abs_residual_cycles=round(float(np.max(np.abs(resid))), 2),
                         words="per rank" if mode == "all_gather" else "whole vector",
                         points=[list(map(int, p)) for p in pts])
    return out


def campaign(name, ncal=12, nmeas=8, jobs=8):
    build(name)
    _, ops, meta = fixture(name)
    big = dict(U_DREL=4000, X_DREL=4000)
    cal_jobs = [(s, 0, big, None) for s in range(1, ncal + 1)] + \
        [(1000 + i, 0, big, c) for i, c in enumerate(corners(name))]
    with ThreadPoolExecutor(jobs) as ex:
        cal = list(ex.map(lambda a: run(name, *a), cal_jobs))
    arr = {}
    for r in cal:
        for c, (lo, hi) in arrivals(r).items():
            a = arr.setdefault(c, [10 ** 9, 0])
            a[0], a[1] = min(a[0], lo), max(a[1], hi)
    drel = {"X_DREL": arr["board"][1] + GUARD, "U_DREL": arr.get("ucie", [0, 0])[1] + GUARD}
    meas_jobs = [(s, 1, drel, None) for s in range(1, nmeas + 1)] + \
        [(2000 + i, 1, drel, c) for i, c in enumerate(corners(name))]
    with ThreadPoolExecutor(jobs) as ex:
        meas = list(ex.map(lambda a: run(name, *a), meas_jobs))
    rows = summarize(meas[0], ops)
    det_ok = len({m["timing_sha256"] for m in meas}) == 1
    free = [summarize(r, ops) for r in cal]
    gen, bp = cfg_params(name)
    return dict(name=name, parameters=gen, board_link=bp, config=CONFIGS[name], fixture=meta,
                calibration=dict(runs=len(cal), all_passed=all(r["passed"] for r in cal),
                                 arrival_cycles=arr,
                                 free_running_latency_range={str(i): [min(f[i]["issue_to_last_commit_cycles"]
                                                                          for f in free),
                                                                      max(f[i]["issue_to_last_commit_cycles"]
                                                                          for f in free)]
                                                             for i in range(len(ops))}),
                release_delay_cycles=drel, release_guard_cycles=GUARD,
                deterministic=dict(runs=len(meas), all_passed=all(m["passed"] for m in meas),
                                   distinct_timings=len({m["timing_sha256"] for m in meas}),
                                   seeds=[m["seed"] for m in meas], corners=corners(name),
                                   faults=[m["faults"] for m in meas], mismatches=[m["mismatches"] for m in meas]),
                deterministic_timing=det_ok, collectives=rows, fit=fit(rows),
                links=meas[0]["links"])


def pins():
    return {p: sha(ROOT / p) for p in SRC + ["tools/dsrom_c5hc_collective_gate.py", "tools/hdc_golden_v41.py",
                                             "tools/hdc_golden.py", "tools/w15_collectives.py"]}


def git_state():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True,
                           text=True).stdout.split("\n")
    return dict(head=head, dirty=[d for d in dirty if d.strip()])


def cmd_measure(a):
    names = a.only.split(",") if a.only else ([] if a.merge else list(CONFIGS))
    out = Path(a.out) if a.out else OUT / "measurements.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    for extra in (a.merge or "").split(","):
        if extra:
            old.setdefault("configs", {}).update(json.loads(Path(extra).read_text())["configs"])
    cfgs = dict(old.get("configs", {}))
    for n in names:
        print("campaign", n, flush=True)
        cfgs[n] = campaign(n, ncal=a.ncal, nmeas=a.nmeas, jobs=a.jobs)
        print(json.dumps(dict(name=n, fit=cfgs[n]["fit"], det=cfgs[n]["deterministic"],
                              drel=cfgs[n]["release_delay_cycles"])), flush=True)
    rec = dict(schema="opentallas.dsrom.c5hc_collective_gate.measurements.v1", git=git_state(),
               source_sha256=pins(), verilator=subprocess.run([str(VERILATOR), "--version"], capture_output=True,
                                                               text=True).stdout.strip(),
               verilator_flags=VFLAGS, clock_hz=CLOCK_HZ, configs=cfgs,
               measured_on=a.host or os.uname().nodename)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("wrote", out)


# ---- re-price ------------------------------------------------------------------------------------------------------
CTXS = (1048576, 200000)
VERDICT_BASIS = dict(C5hc="c5hc_phys", C1="c1_phys")
SENSITIVITY = dict(C5hc="c5hc_modelbw", C1="c1_modelbw")


def _coll_table(g, P=1):
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    path = set(g.path(sink))
    agg = {}
    for n, nd in g.nodes.items():
        if nd["kind"] != "collective":
            continue
        key = n.split(".", 1)[1] if n.startswith("L") else n
        a = agg.setdefault(key, dict(calls=0, on_path=0, depth_ns=set(), path_us=0.0))
        a["calls"] += 1
        if n in path:
            a["on_path"] += 1
            a["path_us"] += sum(g.contrib[n].values()) * 1e6
        a["depth_ns"].add(round(nd["depth"] * 1e9, 1))
    return {k: dict(calls=v["calls"], on_path=v["on_path"], depth_ns=sorted(v["depth_ns"]),
                    path_us=round(v["path_us"], 3)) for k, v in sorted(agg.items())}


def price_all(meas, basis):
    import dsrom_parallelism as S
    import uarch_model as u
    cs = u.DIE_SHRUNK_INTERIM["coll_stages"]
    maps = {cid: (par2, cfg) for cid, par2, cfg, _ in S.mappings()}
    out = {}
    for cand, cid in (("C1", "C1_PP58_TP4_PAR2rows"), ("C5hc", "C5hc_hybrid_head8_chase")):
        par2, cfg = maps[cid]
        for kind in ("model", "measured"):
            for ctx in CTXS:
                c = dict(coll={}) if cfg is None else dict(cfg)
                if kind == "measured":
                    c["measured_coll"] = dict(fits=meas["configs"][basis[cand]]["fit"], coll_stages=cs, clock_hz=meas["clock_hz"],
                                              span=4 if cand == "C1" else 8)
                elif cfg is None:
                    c = None
                r, led = S.price(ctx, par2, c)
                p1 = next((x for x in led if x["P"] == 1), None)
                row = dict(ar_tok_s=r["ar_tok_s"], mtp_tok_s=r["mtp_tok_s"], ar_token_us=r["ar_token_us"],
                           path_us=r["path_us"])
                if p1 is not None:
                    row["collectives"] = _coll_table(p1["_g"])
                    if "measured_rest_ns" in p1:
                        row["kept_non_link_terms_ns"] = p1["measured_rest_ns"]
                out.setdefault(cand, {}).setdefault(kind, {})[str(ctx)] = row
                print(cand, kind, ctx, r["ar_tok_s"], r["mtp_tok_s"], r["path_us"]["tp_collectives"], flush=True)
    return out


def verdict(pr):
    m = {c: {ctx: pr[c]["measured"][str(ctx)]["ar_tok_s"] for ctx in CTXS} for c in ("C1", "C5hc")}
    g1 = m["C5hc"][1048576] / m["C1"][1048576] - 1
    g2 = m["C5hc"][200000] / m["C1"][200000] - 1
    return dict(c5hc_vs_c1_ar_1m_pct=round(100 * g1, 2), c5hc_vs_c1_ar_200k_pct=round(100 * g2, 2),
                thresholds=dict(ar_1m_pct=5.0, ar_200k_pct=1.0), rate_ok=bool(g1 >= 0.05 and g2 >= 0.01))


def exactness(meas):
    ok, why = True, []
    for n, c in meas["configs"].items():
        if not (c["deterministic"]["all_passed"] and c["calibration"]["all_passed"]):
            ok = False
            why.append(f"{n}: a run failed")
        if n.endswith(("_phys", "_modelbw")) and not c["deterministic_timing"]:
            ok = False
            why.append(f"{n}: timing not deterministic across seeds")
        w = c["fixture"]["wo_b"]
        if not (w["tree_of_rank_partials_equals_golden_csum"] and w["to_bf16_equals_golden_linear_q"]):
            ok = False
            why.append(f"{n}: wo_b golden tree check")
    return dict(all_passed=ok, failures=why)


def cmd_reprice(a):
    meas = json.loads((OUT / "measurements.json").read_text())
    pr = price_all(meas, VERDICT_BASIS)
    sens = price_all(meas, SENSITIVITY) if all(k in meas["configs"] for k in SENSITIVITY.values()) else None
    v = verdict(pr)
    ex = exactness(meas)
    dec = "ADOPT" if (v["rate_ok"] and ex["all_passed"]) else "REJECT"
    rec = dict(schema="opentallas.dsrom.c5hc_collective_gate.verdict.v1", git=git_state(), source_sha256=dict(
        pins(), **{p: sha(ROOT / p) for p in ("tools/uarch_model.py", "tools/uarch_model_parallelism.py",
                                              "tools/uarch_model_par2_boundary.py", "tools/dsrom_parallelism.py",
                                              "results/rtl/dsrom_c5hc_collective_gate_20261003/measurements.json",
                                              "results/rtl/dsrom_c5hc_collective_gate_20261003/decision_rule.json")}),
               decision_rule=json.loads((OUT / "decision_rule.json").read_text())["rule"],
               basis=VERDICT_BASIS, priced=pr, sensitivity_model_link_bw=dict(
                   basis=SENSITIVITY, priced=sens, verdict=verdict(sens) if sens else None),
               rate=v, exactness=ex, verdict=dec)
    b = (json.dumps(rec, indent=1, sort_keys=True) + "\n").encode()
    out = OUT / "verdict.json"
    if a.verify:
        old = json.loads(out.read_text())
        for k in ("priced", "rate", "exactness", "verdict"):
            if old[k] != json.loads(b)[k]:
                raise SystemExit(f"verify: {k} differs")
        print("verify OK", dec)
        return
    if out.exists() and out.read_bytes() != b:
        raise SystemExit(f"{out} exists with different bytes (failed verdicts are never overwritten)")
    out.write_bytes(b)
    print("wrote", out, dec, json.dumps(v))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    m = sp.add_parser("measure")
    m.add_argument("--only", default=None)
    m.add_argument("--jobs", type=int, default=8)
    m.add_argument("--ncal", type=int, default=10)
    m.add_argument("--nmeas", type=int, default=8)
    m.add_argument("--out", default=None)
    m.add_argument("--host", default=None, help="the host the merged campaigns ran on")
    m.add_argument("--merge", default=None, help="comma-separated per-config measurement files to fold in")
    sp.add_parser("fixture")
    rp = sp.add_parser("reprice")
    rp.add_argument("--verify", action="store_true")
    one = sp.add_parser("one")
    one.add_argument("name")
    one.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "measure":
        cmd_measure(a)
    elif a.cmd == "reprice":
        cmd_reprice(a)
    elif a.cmd == "fixture":
        for n in ("c5hc_phys", "c1_phys"):
            d, ops, meta = fixture(n)
            print(d, len(ops), json.dumps(meta["wo_b"]))
    elif a.cmd == "one":
        r = run(a.name, a.seed, 0, dict(U_DREL=4000, X_DREL=4000))
        _, ops, _ = fixture(a.name)
        print(json.dumps({k: v for k, v in r.items() if k not in ("ops", "links")}))
        for row in summarize(r, ops):
            print(row["mode"], row["words"], row["issue_to_last_commit_cycles"], row["per_die_issue_to_last_commit"])


if __name__ == "__main__":
    main()
