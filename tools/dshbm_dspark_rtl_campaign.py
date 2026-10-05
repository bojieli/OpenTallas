#!/usr/bin/env python3
"""DSpark (V4.1 MTP) on the V4.1 HBM comparator: RTL campaign of the control plane (default-off build).

    python3 tools/dshbm_dspark_rtl_campaign.py argmax --out PART.json
    python3 tools/dshbm_dspark_rtl_campaign.py bench --trace DIR [--mut 0] [--wr N] [--sr N] --out PART.json
    python3 tools/dshbm_dspark_rtl_campaign.py merge --parts P1.json ... --out results/rtl/dshbm_dspark_rtl_20261003/X.json

argmax  rtl/gpu/dshbm/ot_dshbm_argmax.sv (rtl/test/tb_dshbm_argmax.sv) against numpy.argmax on FP32 rows: adversarial
        rows (ties across and within lanes, -0 vs +0, all-negative, subnormals, infinities, NaNs: the first NaN wins),
        random rows, and Markov-biased rows (the golden's add, then argmax); plus the full-shape timing: one SM's
        epilogue (43 rows of a TP-96 die's 1,347 Markov-head rows), the die's 32-SM merge, one die-wide stream.
bench   rtl/test/tb_dshbm_dspark.sv on a tools/dshbm_dspark_trace.py directory: the whole speculative loop (prefill,
        DSpark draft commands, Markov chain, verify passes with expert unions streamed through W19's expert fetch
        and HBM model, accept, commit / rollback) against the golden's replayed engine events, the emitted tokens,
        the per-step accepts and the FINAL state at the last committed position against the autoregressive run.
        --mut 1/2/3 (control mutations), --wr W (window ring without the speculative headroom), --sr r (compressor
        slot ring without it): each must FAIL (detection), recorded as such.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.rtl.dshbm_dspark_rtl.v1"
DUT = ["rtl/gpu/dshbm/ot_dshbm_accept_port.sv", "rtl/gpu/dshbm/ot_dshbm_argmax.sv", "rtl/gpu/dshbm/ot_dshbm_expert_union.sv",
       "rtl/gpu/dshbm/ot_dshbm_spec_state.sv", "rtl/gpu/dshbm/ot_dshbm_dspark_ctl.sv",
       "rtl/gpu/dshbm/ot_dshbm_dspark_top.sv"]
REUSED = ["rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv", "rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv",
          "rtl/hdc/ot_hdc_accept.sv", "rtl/gpu/ot_gpu_router_topk.sv", "rtl/gpu/ot_gpu_expert_fetch.sv",
          "rtl/hdc/kv/ot_hdc_hbm_model.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
          "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_prefix.sv"]
ARGMAX_SRC = ["rtl/gpu/dshbm/ot_dshbm_argmax.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
              "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_prefix.sv",
              "rtl/test/tb_dshbm_argmax.sv"]
BENCH_SRC = DUT + REUSED + ["rtl/test/tb_dshbm_dspark.sv"]
F = np.float32


def sha(p) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def compile_tb(src, top, params, outdir):
    exe = Path(outdir) / "sim.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(exe), "-s", top] + [f"-P{top}.{k}={v}" for k, v in params.items()] \
        + [str(ROOT / s) for s in src]
    subprocess.run(cmd, check=True, cwd=ROOT, stderr=subprocess.DEVNULL)
    return exe


# -------------------------------------------------------------------------------------------------- argmax
def fb(x):
    return np.asarray(x, dtype=F).view(np.uint32)


def argmax_rows(rng, nv):
    rows, names = [], []

    def add(name, r):
        rows.append(np.asarray(r, dtype=F)); names.append(name)
    r = rng.standard_normal(nv).astype(F); r[[5, 13, 37, nv - 1]] = 9.0
    add("tie_across_lanes_lowest_wins", r)
    r = rng.standard_normal(nv).astype(F); r[[16, 24]] = 7.5
    add("tie_same_lane_lowest_wins", r)
    r = -np.abs(rng.standard_normal(nv)).astype(F) - 1; r[[100, 3]] = F(-0.0); r[7] = F(0.0)
    add("neg_zero_equals_pos_zero", r)
    r = -np.abs(rng.standard_normal(nv)).astype(F) - 0.5
    add("all_negative", r)
    r = np.full(nv, F(-1e-45), dtype=F); r[nv // 2] = F(1e-45); r[nv // 3] = F(1e-45)
    add("subnormals", r)
    r = rng.standard_normal(nv).astype(F); r[[11, 900]] = np.inf
    add("plus_infinity", r)
    r = rng.standard_normal(nv).astype(F); r[[30, 2000]] = np.nan; r[1] = np.inf
    add("first_nan_wins", r)
    r = np.zeros(nv, dtype=F)
    add("all_zero", r)
    r = np.full(nv, -np.inf, dtype=F); r[nv - 1] = F(-3.0e38)
    add("max_at_last_index", r)
    for i in range(7):
        add(f"random_{i}", (rng.standard_normal(nv) * (10 ** (i - 3))).astype(F))
    return rows, names


def run_argmax(rows, biases, nv, lp, workdir, label):
    d = Path(tempfile.mkdtemp(prefix=f"am_{label}_", dir=workdir))
    (d / "rows.hex").write_text("".join(f"{int(v):08x}\n" for r in rows for v in fb(r)))
    bias = biases is not None
    if bias:
        (d / "bias.hex").write_text("".join(f"{int(v):08x}\n" for r in biases for v in fb(r)))
    exe = compile_tb(ARGMAX_SRC, "tb_dshbm_argmax", dict(LP=lp, NV=nv, NROW=len(rows), BIAS=int(bias)), d)
    out = subprocess.run(["vvp", "-n", str(exe)], cwd=d, capture_output=True, text=True).stdout
    res = [dict(idx=int(m.group(1)), nan=int(m.group(2)), cycles=int(m.group(3)), fault=int(m.group(4)))
           for m in re.finditer(r"ROW \d+ idx (\d+) nan (\d+) cycles (\d+) fault (\d+)", out)]
    return res


def cmd_argmax(a):
    sys.path.insert(0, str(ROOT / "tools"))
    import hdc_golden as G
    rng = np.random.default_rng(20261003)
    os.makedirs(a.workdir, exist_ok=True)
    cases = []
    nv = 4040
    rows, names = argmax_rows(rng, nv)
    got = run_argmax(rows, None, nv, 8, a.workdir, "adv")
    for n, r, g in zip(names, rows, got):
        cases.append(dict(case=n, nv=nv, bias=False, want=int(np.argmax(r)), got=g["idx"], nan=g["nan"],
                          exact=g["idx"] == int(np.argmax(r)), cycles=g["cycles"]))
    # Markov-biased rows: golden add (RNE, every zero +0), then argmax
    rows = [(rng.standard_normal(nv) * 4).astype(F) for _ in range(6)]
    biases = [(rng.standard_normal(nv) * 4).astype(F) for _ in range(6)]
    rows[0][[9, 10]] = F(1.0); biases[0][[9, 10]] = F(-1.0)          # x + (-x) = +0 on two lanes
    rows[1][[3, 4]] = F(5.0); biases[1][[3, 4]] = F(5.0)             # tie after the add
    got = run_argmax(rows, biases, nv, 8, a.workdir, "bias")
    for i, (r, b, g) in enumerate(zip(rows, biases, got)):
        want = int(np.argmax(G.add(r, b)))
        cases.append(dict(case=f"markov_bias_{i}", nv=nv, bias=True, want=want, got=g["idx"], exact=g["idx"] == want,
                          fault=g["fault"], cycles=g["cycles"]))
    # full-shape timing (V4.1-Flash: vocab 129,280 over TP-96 -> 1,347 rows a die, 32 SMs -> 43 a SM)
    timing = {}
    for label, nvv, bias in (("sm_epilogue_43_bias", 43, True), ("sm_merge_32", 32, False),
                             ("die_stream_1347_bias", 1347, True)):
        rs = [(rng.standard_normal(nvv) * 3).astype(F) for _ in range(4)]
        bs = [(rng.standard_normal(nvv) * 3).astype(F) for _ in range(4)] if bias else None
        got = run_argmax(rs, bs, nvv, 8, a.workdir, label)
        ok = all(g["idx"] == int(np.argmax(G.add(r, b) if bias else r)) for r, b, g in
                 zip(rs, bs or [None] * 4, got))
        timing[label] = dict(values=nvv, lanes=8, bias=bias, cycles_first_beat_to_result=got[0]["cycles"],
                             beats=-(-nvv // 8), exact=ok)
    passed = all(c["exact"] for c in cases) and all(t["exact"] for t in timing.values())
    return dict(part="argmax", status="pass" if passed else "fail", cases=cases, timing=timing), passed


# -------------------------------------------------------------------------------------------------- union
UNION_SRC = ["rtl/gpu/dshbm/ot_dshbm_expert_union.sv", "rtl/test/tb_dshbm_union.sv"]


def cmd_union(a):
    """Full-shape union (384 experts, top-6, 6 verify positions): exactness and cycles flush -> last id."""
    rng = np.random.default_rng(20261003)
    NE, K, P = 384, 6, 6
    cases = []
    cases.append([[0, 1, 2, 3, 4, 383]] * P)                                   # identical: union 6, edges
    cases.append([list(range(j * K, j * K + K)) for j in range(P)])           # disjoint: union 36
    pop = rng.zipf(1.3, 20000) % NE                                            # skewed routing (overlapping)
    for _ in range(6):
        cs = []
        for j in range(P):
            ids = []
            while len(ids) < K:
                e = int(rng.choice(pop))
                if e not in ids:
                    ids.append(e)
            cs.append(sorted(ids))
        cases.append(cs)
    os.makedirs(a.workdir, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix="un_", dir=a.workdir))
    (d / "ids.hex").write_text("".join(f"{i:08x}\n" for cs in cases for col in cs for i in col))
    exe = compile_tb(UNION_SRC, "tb_dshbm_union", dict(NE=NE, K=K, P=P, NCASE=len(cases)), d)
    out = subprocess.run(["vvp", "-n", str(exe)], cwd=d, capture_output=True, text=True).stdout
    got = {}
    for m in re.finditer(r"U (\d+) (\d+) (\d+)", out):
        got.setdefault(int(m.group(1)), []).append((int(m.group(2)), int(m.group(3))))
    cyc = {int(m.group(1)): dict(flush_to_first=int(m.group(2)), flush_to_done=int(m.group(3)), count=int(m.group(4)))
           for m in re.finditer(r"CASE (\d+) flush_to_first (-?\d+) flush_to_done (\d+) count (\d+)", out)}
    res = []
    for c, cs in enumerate(cases):
        u = sorted(set(i for col in cs for i in col))
        want = [(i, sum(1 << j for j, col in enumerate(cs) if i in col)) for i in u]
        res.append(dict(case=c, union=len(u), exact=got.get(c) == want, **cyc.get(c, {})))
    passed = all(r["exact"] for r in res)
    return dict(part="union", status="pass" if passed else "fail", experts=NE, k=K, positions=P, cases=res), passed


# -------------------------------------------------------------------------------------------------- bench
def bench_params(cfg, a):
    m = cfg["model"]
    W = cfg.get("window_override") or m["window"]
    pmax = 8
    return dict(GAMMA=cfg["gamma"], FORCE=int(cfg["drafter"] == "forced"), NGEN=cfg["ngen"], PLEN=cfg["plen"],
                NL=m["layers"], B=m["block"], MUT=a.mut, W=W, WR=a.wr or (W + pmax), SR=a.sr or (max(m["ratios"]) + pmax),
                MAXPOS=m["max_seq_len"], ACCEPT_LEAF=a.leaf, NEXP=m["n_exp"], NDEXP=m["d_exp"], KV=m["k_exp"], KD=m["d_k"])


def cmd_bench(a):
    tdir = Path(a.trace)
    cfg = json.loads((tdir / "cfg.json").read_text())
    params = bench_params(cfg, a)
    os.makedirs(a.workdir, exist_ok=True)
    bdir = Path(tempfile.mkdtemp(prefix="bench_", dir=a.workdir))
    exe = compile_tb(BENCH_SRC, "tb_dshbm_dspark", params, bdir)
    t0 = time.time()
    p = subprocess.run(["vvp", "-n", str(exe)], cwd=tdir, capture_output=True, text=True)
    wall = time.time() - t0
    (bdir / "sim.log").write_text(p.stdout + p.stderr)
    line = next((ln for ln in p.stdout.splitlines() if ln.startswith("DSHBM ")), "DSHBM FAIL no-summary")
    st = line.split()[1]
    kv = dict(re.findall(r"(\w+)=(-?\d+)", line))
    kv = {k: int(v) for k, v in kv.items()}
    msgs = [ln for ln in p.stdout.splitlines() if "MISMATCH" in ln or "FINAL" in ln or "TIMEOUT" in ln][:12]
    expect_fail = bool(a.mut or a.wr or a.sr)
    rec = dict(part="bench", trace=dict(dir=str(tdir), drafter=cfg["drafter"], gamma=cfg["gamma"], ngen=cfg["ngen"],
                                        window=params["W"], n_final=cfg["n_final"], records=cfg["records"],
                                        accepted_per_step=[s["accepted"] for s in cfg["steps"]],
                                        script_sha256=hashlib.sha256((tdir / "script.hex").read_bytes()).hexdigest(),
                                        golden=cfg["golden"]),
               params=params, mutation=dict(mut=a.mut, wr=a.wr, sr=a.sr) if expect_fail else None,
               sim_status=st, summary=kv, messages=msgs, wall_s=round(wall, 1))
    if expect_fail:
        rec["detected"] = st != "PASS"
        passed = rec["detected"]
    else:
        passed = st == "PASS"
    rec["status"] = "pass" if passed else "fail"
    return rec, passed


# -------------------------------------------------------------------------------------------------- merge
def cmd_merge(a):
    parts = [json.loads(Path(p).read_text()) for p in a.parts]
    passed = all(p["status"] == "pass" for p in parts)
    return dict(part="merged", status="pass" if passed else "fail", parts=parts), passed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("argmax", "union", "bench", "merge"))
    ap.add_argument("--trace")
    ap.add_argument("--mut", type=int, default=0)
    ap.add_argument("--wr", type=int, default=0)
    ap.add_argument("--sr", type=int, default=0)
    ap.add_argument("--leaf", type=int, default=0, help="1: Codex's protected DS MTP accept leaf (ACCEPT_LEAF)")
    ap.add_argument("--parts", nargs="*")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workdir", default="/tmp/claude-1000/dshbm/rtl")
    a = ap.parse_args()
    rec, passed = {"argmax": cmd_argmax, "union": cmd_union, "bench": cmd_bench, "merge": cmd_merge}[a.cmd](a)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sim = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0]
    rec.update(schema=SCHEMA, generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               source_commit=head, simulator=sim,
               source_sha256={s: sha(s) for s in sorted(set(BENCH_SRC + ARGMAX_SRC + UNION_SRC + [
                   "tools/dshbm_dspark_rtl_campaign.py", "tools/dshbm_dspark_trace.py", "tools/hdc_golden_v41.py"]))})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print(rec["status"].upper(), a.out, json.dumps(rec.get("summary", {}))[:400])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
