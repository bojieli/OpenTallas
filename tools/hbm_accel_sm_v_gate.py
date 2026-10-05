#!/usr/bin/env python3
"""Exactness and cycle gate of the target-1.2 GHz DS HBM SM candidate (rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv).

Runs W13's own SM benches with the successor as the DUT (rtl/test/tb_hbm_accel_sm_v.sv, ENABLE = 0 is the original
ot_gpu_sm_v, ENABLE = 1 the successor), on the same vectors, and reports per case: bit-exact vs golden for both,
result rows identical between them, and the cycle delta (start -> done, first / last result).
The bench clock is 1 ns; these are simulation cycles, not contextual SS/FF closure.
Verilator uses the identical timed bench and native arithmetic without substitution.
Do not start this backend alongside the preserved live Icarus gate.

    python3 tools/hbm_accel_sm_v_gate.py synth --out R.json [--cols 1 2 8]          # rtl_gpu_sm_exact smv vectors
    python3 tools/hbm_accel_sm_v_gate.py synth --simulator verilator --cols 8 --out R.json
    python3 tools/hbm_accel_sm_v_gate.py shapes --out R.json                         # every measured DS token shape
    python3 tools/hbm_accel_sm_v_gate.py edges --out R.json                          # FP edge operands
    python3 tools/hbm_accel_sm_v_gate.py real --dump sm_dump.pkl --out R.json       # w19_sm_real_ops real operands
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_gpu_sm_exact as S  # noqa: E402

SRC = ["rtl/hdc/ot_hdc_prefix.sv"] + [s for s in S.SMV_SRC if s != "rtl/test/tb_gpu_sm_v.sv"] + [
    "rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv",
    "physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v",
    "rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv", "rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv", "rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv", "rtl/test/tb_hbm_accel_sm_v.sv"]
TB = "tb_hbm_accel_sm_v"
_lock = __import__("threading").RLock()
_exe = {}
_build_commands = {}
_icarus_run_sim = S.run_sim


def run_sim(exe, d, gap):
    if ARGS.simulator == "iverilog":
        return _icarus_run_sim(exe, d, gap)
    # Same DIR/GAP protocol and out.txt decoder as rtl_gpu_sm_exact.run_sim.
    with (Path(d) / "runtime.log").open("x") as log:
        subprocess.run([str(exe), f"+DIR={d}", f"+GAP={gap}"], check=True,
                       cwd=d, stdout=log, stderr=subprocess.STDOUT)
    res, meta = {}, {}
    for line in (Path(d) / "out.txt").read_text().splitlines():
        if line.startswith("#"):
            toks = line[1:].split()
            for i in range(0, len(toks) - 1, 2):
                meta[toks[i]] = int(toks[i + 1]) if toks[i + 1].lstrip("-").isdigit() else toks[i + 1]
            if "TIMEOUT" in line:
                meta["timeout"] = True
            continue
        r, h = line.split()
        res[int(r)] = h
    return res, meta


def compile_verilator(en, params, outdir):
    outdir = Path(outdir).resolve()
    effective = dict(params, ENABLE=en)
    command = [ARGS.verilator, "--binary", "--timing", "-Wno-fatal",
               "--top-module", TB, "--Mdir", str(outdir), "-j", str(ARGS.build_jobs),
               *[f"-G{k}={v}" for k, v in effective.items()],
               *[str(ROOT / src) for src in SRC]]
    # Retain compiler errors/progress; no timeout/FSIZE/AS/memory cap or retry.
    with (outdir / "build.log").open("x") as log:
        subprocess.run(command, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    exe = outdir / ("V" + TB)
    if not exe.is_file():
        raise RuntimeError("Verilator exited without the actual bench executable")
    return exe, command


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def runner(enable, workdir):
    def run(params, d):
        return run_sim(_compile(enable, params), d, 0)
    return run


def compare(name, r0, r1):
    m0, m1 = r0["rtl"], r1["rtl"]
    return dict(case=name, exact_original=r0["exact"], exact_successor=r1["exact"],
                cycles_start_to_done=[m0.get("cycles_start_to_done"), m1.get("cycles_start_to_done")],
                first_result=[m0.get("first_result"), m1.get("first_result")],
                last_result=[m0.get("last_result"), m1.get("last_result")],
                delta_done=(m1.get("cycles_start_to_done") or 0) - (m0.get("cycles_start_to_done") or 0),
                delta_first=(m1.get("first_result") or 0) - (m0.get("first_result") or 0),
                delta_last=(m1.get("last_result") or 0) - (m0.get("last_result") or 0),
                successor=r1, original=r0)


def cmd_synth(a):
    """W13's smv vectors (rtl_gpu_sm_exact.bd_campaign specs_v), through the successor bench; the original runs the
    same vectors (same seeds) for the lockstep comparison."""
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    list(ThreadPoolExecutor(min(a.jobs, 2*len(a.cols))).map(lambda k: _cache_for(*k), [(en, NC) for NC in a.cols for en in (0, 1)]))
    out = []
    for NC in a.cols:
        specs = [("smv_fp8_k5120_gs_r1", "v41_fp8", 1, 5120, dict(gs=True)),
                 ("smv_fp4_k5120_gs_r2", "v41_fp4", 2, 5120, dict(gs=True)),
                 ("smv_bf16_k1004_gs_r3", "v41_bf16", 3, 1004, dict(gs=True)),
                 ("smv_fp8_k1280_rowslot", "v41_fp8", 9, 1280, {}),
                 ("smv_bf16_k5120_rowslot_r11", "v41_bf16", 11, 5120, {}),
                 ("smv_fp4_k2304_gs_r2_gap", "v41_fp4", 2, 2304, dict(gs=True, gap=30))]
        def one(i_spec):
            i, (name, fmt, R, K, kw) = i_spec
            res = []
            for en in (0, 1):
                res.append(S.smv_case(f"{name}_nc{NC}", fmt, R, K, NC, rng=np.random.default_rng(20261001 + i),
                                      workdir=a.workdir, exe_cache=_cache_for(en, NC), **kw))
            return compare(f"{name}_nc{NC}", res[0], res[1])
        out += list(ThreadPoolExecutor(a.jobs).map(one, enumerate(specs)))
    return out


_caches = {}


def _cache_for(en, NC):
    """smv_case looks its executable up in exe_cache by its param key: pre-seed it with the successor bench."""
    params = dict(SUB=4, LBS=2, LSB=16, NC=NC, XDEPTH=128, RMAX=256, LEV=4)
    key = ("v",) + tuple(sorted(params.items()))
    exe = _compile(en, params)
    with _lock:
        _caches.setdefault((en, NC), {key: exe})
    return _caches[(en, NC)]


def _compile(en, params):
    """One bench executable per (ENABLE, params), compiled once; different keys compile in parallel."""
    key = (en,) + tuple(sorted(params.items()))
    with _lock:
        kl = _klocks.setdefault(key, __import__("threading").Lock())
    with kl:
        if key not in _exe:
            directory = tempfile.mkdtemp(prefix=f"b{en}_", dir=ARGS.workdir)
            if ARGS.simulator == "verilator":
                _exe[key], _build_commands[repr(key)] = compile_verilator(en, params, directory)
            else:
                _exe[key] = S.compile_tb(SRC, TB, dict(params, ENABLE=en), directory)
    return _exe[key]


_klocks = {}


def cmd_shapes(a):
    """Every matvec shape of the measured DS token (results/rtl/dshbm_baseline_measured_20261004/sm_real_ops.json:
    format, K, rows on the busiest SM, one column) on seeded operands, original and successor in lockstep.  The SM's
    cycles depend on the shape only (the bench's HBM latency is seeded), so the original's cycles must reproduce the
    record's; the successor's are the measured per-op element cycles of the 1.2 GHz element."""
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    rec = json.loads((ROOT / a.record).read_text())
    shapes, seen = [], set()
    for c in rec["cases"]["ar"]:
        key = (c["fmt"], c["K"], c["sm_rows"][1] - c["sm_rows"][0])
        if key not in seen:
            seen.add(key)
            shapes.append((key, c))
    list(ThreadPoolExecutor(2).map(lambda en: _cache_for(en, 1), (0, 1)))

    def one(i_item):
        i, ((fmt, K, R), c) = i_item
        name = f"{fmt}_k{K}_r{R}"
        res = [S.smv_case(name, fmt, R, K, 1, rng=np.random.default_rng(20261004 + i), gs=True, workdir=a.workdir,
                          exe_cache=_cache_for(en, 1)) for en in (0, 1)]
        out = compare(name, res[0], res[1])
        rr = c["rtl"]
        out.update(fmt=fmt, K=K, rows=R, ops=[x["op"] for x in rec["cases"]["ar"]
                                             if (x["fmt"], x["K"], x["sm_rows"][1] - x["sm_rows"][0]) == (fmt, K, R)],
                   record_original=dict(cycles_start_to_done=rr["cycles_start_to_done"], lines=rr["lines"],
                                        drain=rr["drain_last_line_to_last_result"]),
                   original_reproduces_record=(res[0]["rtl"].get("cycles_start_to_done") == rr["cycles_start_to_done"]
                                               and res[0]["rtl"].get("drain_last_line_to_last_result")
                                               == rr["drain_last_line_to_last_result"]),
                   drain=[res[0]["rtl"].get("drain_last_line_to_last_result"),
                          res[1]["rtl"].get("drain_last_line_to_last_result")])
        return out
    return list(ThreadPoolExecutor(a.jobs).map(one, enumerate(shapes)))


def edge_operands(fmt, R, K, rng):
    """Floating-point edge operands: zeros and signed zeros, subnormal inputs, the format's largest magnitudes,
    extreme (finite-result) block scales, and large-exponent cancellation (pairs of equal and opposite large terms
    leaving a small remainder), mixed with random values.  Non-finite inputs are excluded: the SM fails closed on
    them (fault) in both the original and the successor."""
    import hdc_golden_v41 as V
    import hdc_golden as G
    F = np.float32
    x = rng.standard_normal(K).astype(F)
    x[0:32] = 0.0
    x[32:64] = -0.0
    x[64:96] = np.float32(1.2e-39) * np.sign(rng.standard_normal(32)).astype(F)     # FP32 subnormal inputs
    x[96:128] = np.float32(3.0e30) * np.sign(rng.standard_normal(32)).astype(F)     # max-scale block
    x[128:160:2], x[129:160:2] = np.float32(1.0e20), np.float32(1.0e20)            # cancellation partner block
    if fmt == "v41_bf16":
        w = (rng.standard_normal((R, K)) * 0.02).astype(F)
        w[:, 160:192] = 0.0
        w[:, 192:224] = -0.0
        w[:, 64:96] = 1.5                                   # subnormal x times O(1): exact subnormal products
        w[:, 96:128] = np.float32(2.0e-31)                  # large x times small w: finite
        w[:, 128:160:2], w[:, 129:160:2] = 1.0, -1.0       # 1e20 - 1e20 + ... cancellation
        w[0, 224:256] = np.float32(2.0e-36)                 # weight-side near-underflow values (x ~ N(0,1))
        return G.to_bf16(w), [x]
    fp4 = fmt == "v41_fp4"
    grid = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]) if fp4 else \
        np.array([0.0, 2.0 ** -9, 2.0 ** -7, 2.0 ** -6, 0.5, 1.0, 1.75, 2.0, 15.0, 240.0, 448.0])
    q = rng.choice(grid, size=(R, K)) * np.where(rng.random((R, K)) < 0.5, -1.0, 1.0)
    q[:, 160:192] = 0.0
    q[:, 192:224] = -0.0
    q[:, 128:160:2], q[:, 129:160:2] = grid[-1], -grid[-1]                 # largest magnitude, cancelling pairs
    nb = K // 32
    e = rng.integers(-8, 3, size=(R, nb)).astype(np.int64)
    e[:, 3] = -60                                           # tiny block scale against the 3e30 x block
    e[:, 4] = 40                                            # huge block scale against the 1e20 cancellation block
    e[:, 5] = -100
    return V.Q8(q, e), [x]


def cmd_edges(a):
    import hdc_golden_v41 as V
    import hdc_golden as G
    import w19_sm_real_ops as SM
    V.set_arith("chunk8")
    specs = [("v41_fp8", 2, 5120), ("v41_fp4", 2, 5120), ("v41_bf16", 2, 5120), ("v41_fp8", 3, 2304),
             ("v41_fp4", 1, 2304), ("v41_bf16", 1, 1024)]

    def one(i_spec):
        i, (fmt, R, K) = i_spec
        w, X = edge_operands(fmt, R, K, np.random.default_rng(777 + i))
        res = []
        for en in (0, 1):
            acc, gold, meta = SM.smv_real(f"edge_{fmt}_{R}_{K}", fmt, w, X, workdir=a.workdir,
                                          sim_runner=runner(en, a.workdir))
            mism = int(np.sum(G.bits(acc[0]) != G.bits(gold[0]))) + int(np.isnan(acc[0]).sum())
            res.append(dict(exact=(mism == 0 and not meta.get("timeout") and meta.get("fault", 1) == 0),
                            mismatches=mism, rtl=meta, acc_bits=[int(v) for v in G.bits(acc[0])]))
        out = compare(f"edge_{fmt}_r{R}_k{K}", res[0], res[1])
        out["successor_equals_original_bits"] = res[0]["acc_bits"] == res[1]["acc_bits"]
        return out
    return list(ThreadPoolExecutor(a.jobs).map(one, enumerate(specs)))


def cmd_real(a):
    import w19_sm_real_ops as SM
    import rtl_v41_fullshape_layer_campaign as LC
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    dump = pickle.loads(Path(a.dump).read_bytes())
    groups = {}
    for k, e in dump.items():
        op, _, p = k.rpartition(".p")
        groups.setdefault(op, []).append((int(p), e))
    jobs = [(op, [e for _, e in sorted(v, key=lambda t: t[0])]) for op, v in sorted(groups.items())]
    for _, ents in jobs:
        for nm in (ents[0]["w"] if isinstance(ents[0]["w"], list) else [ents[0]["w"]]):
            m.w[nm]

    def one(j):
        r0 = SM.case(m, j[0], j[1], a.workdir, sim_runner=runner(0, a.workdir))
        r1 = SM.case(m, j[0], j[1], a.workdir, sim_runner=runner(1, a.workdir))
        c = compare(j[0], r0, r1)
        c.update(tag=r1["tag"], fmt=r1["fmt"], K=r1["K"], sm_rows=r1["sm_rows"])
        return c
    return list(ThreadPoolExecutor(a.jobs).map(one, jobs))


ARGS = None


def main(argv=None):
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["synth", "real", "shapes", "edges"])
    ap.add_argument("--record", default="results/rtl/dshbm_baseline_measured_20261004/sm_real_ops.json")
    ap.add_argument("--dump")
    ap.add_argument("--simulator", choices=("iverilog", "verilator"), default="iverilog")
    ap.add_argument("--verilator", default="verilator")
    ap.add_argument("--build-jobs", type=int, default=1,
                    help="CXX workers per compile; account for simultaneous parameter keys")
    ap.add_argument("--cols", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    a.workdir = a.workdir or tempfile.mkdtemp(prefix="smv_gate_")
    os.makedirs(a.workdir, exist_ok=True)
    ARGS = a
    if a.jobs < 1 or a.build_jobs < 1 or any(n < 1 for n in a.cols):
        ap.error("jobs/build-jobs/column counts must be positive")
    if a.mode == "real" and not a.dump:
        ap.error("real mode requires the retained actual operand dump")
    if a.simulator == "verilator":
        S.run_sim = run_sim  # smv_case consumes the SAME native result protocol.
    cases = {"synth": cmd_synth, "real": cmd_real, "shapes": cmd_shapes, "edges": cmd_edges}[a.mode](a)
    for c in cases:
        print(f"{c['case']:34s} exact {c['exact_original']}/{c['exact_successor']} done {c['cycles_start_to_done']} "
              f"d_done {c['delta_done']:+d} d_first {c['delta_first']:+d} d_last {c['delta_last']:+d}", flush=True)
    ok = all(c["exact_original"] and c["exact_successor"] for c in cases)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(schema="opentallas.hbm_accel.sm_v_gate.v1", mode=a.mode, status="pass" if ok else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               source_commit=head, simulator=subprocess.run(
                   [a.verilator, "--version"] if a.simulator == "verilator" else ["iverilog", "-V"],
                   capture_output=True, text=True).stdout.splitlines()[0],
               simulator_backend=a.simulator, build_commands=_build_commands,
               benchmark_clock_ns=1.0, contextual_SS_FF_qualified=False,
               dump=dict(path=a.dump, sha256=hashlib.sha256(Path(a.dump).read_bytes()).hexdigest()) if a.dump else None,
               cases=len(cases), mismatching_cases=sum(1 for c in cases if not (c["exact_original"] and c["exact_successor"])),
               delta_done_set=sorted({c["delta_done"] for c in cases}),
               delta_first_set=sorted({c["delta_first"] for c in cases}),
               results=cases, source_sha256={s: sha(s) for s in SRC + ["tools/hbm_accel_sm_v_gate.py",
                                                                      "tools/rtl_gpu_sm_exact.py",
                                                                      "tools/w19_sm_real_ops.py"]})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print("PASS" if ok else "FAIL", a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
