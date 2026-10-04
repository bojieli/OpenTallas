#!/usr/bin/env python3
"""Exactness and cycle gate of the 1.2 GHz DS HBM SM successor (rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv).

Runs W13's own SM benches with the successor as the DUT (rtl/test/tb_hbm_accel_sm_v.sv, ENABLE = 0 is the original
ot_gpu_sm_v, ENABLE = 1 the successor), on the same vectors, and reports per case: bit-exact vs golden for both,
result rows identical between them, and the cycle delta (start -> done, first / last result).

    python3 tools/hbm_accel_sm_v_gate.py synth --out R.json [--cols 1 2 8]          # rtl_gpu_sm_exact smv vectors
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


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def runner(enable, workdir):
    def run(params, d):
        key = (enable,) + tuple(sorted(params.items()))
        return S.run_sim(_compile(enable, params), d, 0)
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
    list(ThreadPoolExecutor(8).map(lambda k: _cache_for(*k), [(en, NC) for NC in a.cols for en in (0, 1)]))
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
            _exe[key] = S.compile_tb(SRC, TB, dict(params, ENABLE=en),
                                     tempfile.mkdtemp(prefix=f"b{en}_", dir=ARGS.workdir))
    return _exe[key]


_klocks = {}


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


def main():
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["synth", "real"])
    ap.add_argument("--dump")
    ap.add_argument("--cols", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    a.workdir = a.workdir or tempfile.mkdtemp(prefix="smv_gate_")
    os.makedirs(a.workdir, exist_ok=True)
    ARGS = a
    cases = cmd_synth(a) if a.mode == "synth" else cmd_real(a)
    for c in cases:
        print(f"{c['case']:34s} exact {c['exact_original']}/{c['exact_successor']} done {c['cycles_start_to_done']} "
              f"d_done {c['delta_done']:+d} d_first {c['delta_first']:+d} d_last {c['delta_last']:+d}", flush=True)
    ok = all(c["exact_original"] and c["exact_successor"] for c in cases)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(schema="opentallas.hbm_accel.sm_v_gate.v1", mode=a.mode, status="pass" if ok else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               source_commit=head, simulator=subprocess.run(["iverilog", "-V"], capture_output=True,
                                                            text=True).stdout.splitlines()[0],
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
