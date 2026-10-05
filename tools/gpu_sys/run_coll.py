#!/usr/bin/env python3
"""Build and run tb_gpu_coll (Verilator --binary --timing): the R = 2 collective path (ot_gpu_coll_endpoint x 2 +
ot_gpu_coll_fabric with the reused rtl/link/ot_link_nvls_switch.sv), check it bit exact, and lint the new modules
(verilator --lint-only -Wall, ENABLE = 0 and 1).

    python3 tools/gpu_sys/run_coll.py [--out results/rtl/hbm_system_rtl_20261003/coll.json] [--nt 160] [--seed 1]

Checks (all in Python against the bench's response dump):
  ALL_REDUCE  rsp lane l < count == float32(r0[l]) + float32(r1[l]) (numpy, RNE), a zero result as +0 (the switch's
              adder canonicalises every zero); lanes >= count == 0.
  ALL_GATHER  rsp lane r*count + i == rank r's raw 32-bit lane i; other lanes 0.
  ranks       both ranks' responses identical bits.
  bench       no fault, ENABLE = 0 instances all-zero, no timeout.
Lint: violations are judged on rtl/gpu_sys/ot_gpu_coll_*.sv only (the reused switch / adder / afifo are unmodified and
not ours); in our files only UNUSED* is tolerated (ot_gpu_cdc_fifo leaves afifo's wfreed/rcount unconsumed).
Latency: clk_sm cycles from the request handshake to the first cycle coll_rsp_v is high, on the measure cases (both
ranks idle first, issue within one cycle of each other, response always ready), count 128 ALL_REDUCE and count 64
ALL_GATHER (= 128 response lanes); reported per rank, max over ranks is the headline.
Exits nonzero on any FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
OURS = [ROOT / "rtl/gpu_sys/ot_gpu_coll_endpoint.sv", ROOT / "rtl/gpu_sys/ot_gpu_coll_fabric.sv"]
REUSED = [ROOT / "rtl/gpu_sys/ot_gpu_cdc_fifo.sv", ROOT / "rtl/link/ot_link_afifo.sv",
          ROOT / "rtl/link/ot_link_nvls_switch.sv", ROOT / "rtl/hdc/ot_hdc_fastfp.sv"]
RTL = OURS + REUSED
BENCH = ROOT / "rtl/test/gpu_sys/tb_gpu_coll.sv"
DEFAULT_OUT = ROOT / "results/rtl/hbm_system_rtl_20261003/coll.json"
SCHEMA = "opentallas.gpu_sys.coll.v1"
R, NL = 2, 128
CLK_SM_PS, CLK_LINK_PS = 833, 900


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


# ---------------------------------------------------------------- stimulus
def _lane_values(rng: np.random.Generator, n: int) -> np.ndarray:
    """n float32 bit patterns mixing +0/-0, subnormals, normals of every scale, large values."""
    kind = rng.integers(0, 8, n)
    out = np.empty(n, dtype=np.uint32)
    sign = rng.integers(0, 2, n).astype(np.uint32) << 31
    man = rng.integers(0, 1 << 23, n, dtype=np.uint32)
    for i in range(n):
        k = kind[i]
        if k == 0:
            out[i] = sign[i]                                                  # +0 / -0
        elif k == 1:
            out[i] = sign[i] | max(int(man[i]), 1)                            # subnormal
        elif k == 2:
            out[i] = sign[i] | (int(rng.integers(1, 4)) << 23) | man[i]       # tiny normal (subnormal sums)
        elif k == 3:
            out[i] = sign[i] | (int(rng.integers(240, 254)) << 23) | man[i]   # large
        elif k == 4:
            out[i] = sign[i] | (int(rng.integers(1, 255)) << 23) | man[i]     # any finite exponent
        else:
            out[i] = np.float32(rng.standard_normal()).view(np.uint32)        # activation-like
    return out


def make_cases(nt: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    cases = []
    for t in range(nt):
        mode = int(rng.integers(0, 2))
        cnt = int(rng.integers(1, NL + 1)) if mode == 0 else int(rng.integers(1, NL // R + 1))
        if t < 4:                                                              # edges first
            mode, cnt = [(0, 1), (0, NL), (1, 1), (1, NL // R)][t]
        if mode == 0:
            a = _lane_values(rng, NL)
            b = _lane_values(rng, NL)
            # some exact cancellations (x + -x = +0) and equal operands
            sel = rng.integers(0, 10, NL)
            b = np.where(sel == 0, a ^ np.uint32(0x80000000), np.where(sel == 1, a, b)).astype(np.uint32)
            with np.errstate(over="ignore", invalid="ignore"):
                s = a.view(np.float32) + b.view(np.float32)
            bad = ~np.isfinite(s)
            b[bad] = a[bad] ^ np.uint32(0x80000000)                           # keep every sum finite (the switch
            data = [a, b]                                                      # fails closed on overflow)
        else:
            data = [rng.integers(0, 1 << 32, NL, dtype=np.uint64).astype(np.uint32) for _ in range(R)]
        cases.append(dict(mode=mode, count=cnt, measure=False, data=data))
    for mode, cnt in [(0, NL), (1, NL // R), (0, NL), (1, NL // R)]:            # latency cases
        data = [_lane_values(rng, NL) for _ in range(R)]
        if mode == 0:
            with np.errstate(over="ignore", invalid="ignore"):
                s = data[0].view(np.float32) + data[1].view(np.float32)
            data[1][~np.isfinite(s)] = 0
        cases.append(dict(mode=mode, count=cnt, measure=True, data=data))
    return cases


def write_stim(cases: list[dict], path: Path) -> None:
    words = [len(cases)]
    for c in cases:
        words.append((int(c["measure"]) << 16) | (c["mode"] << 8) | c["count"])
        words.append(0)
        for r in range(R):
            words.extend(int(x) for x in c["data"][r])
    path.write_text("\n".join(f"{w:08x}" for w in words) + "\n")


def expected(c: dict) -> np.ndarray:
    cnt = c["count"]
    out = np.zeros(NL, dtype=np.uint32)
    if c["mode"] == 0:
        s = (c["data"][0][:cnt].view(np.float32) + c["data"][1][:cnt].view(np.float32)).view(np.uint32).copy()
        s[s == 0x80000000] = 0                                                 # canonical +0
        out[:cnt] = s
    else:
        for r in range(R):
            out[r * cnt:(r + 1) * cnt] = c["data"][r][:cnt]
    return out


# ---------------------------------------------------------------- lint / build / run
def lint(top: str, enable: int) -> dict:
    cmd = [str(VERILATOR), "--lint-only", "-Wall", "--top-module", top, f"-GENABLE={enable}", *map(str, RTL)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    msgs = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith("%")]
    ours = [ln for ln in msgs if "rtl/gpu_sys/ot_gpu_coll_" in ln]
    errors = [ln for ln in msgs if ln.startswith("%Error") and "Exiting due to" not in ln]
    waived = [ln for ln in ours if re.match(r"%Warning-UNUSED", ln)]
    bad = [ln for ln in ours if ln not in waived and not ln.startswith("%Error")] + errors
    forbidden = [ln for ln in msgs if re.match(r"%Warning-(IMPLICIT|UNDRIVEN|MULTIDRIVEN)", ln)]
    return {"top": top, "enable": enable, "pass": not bad and not forbidden, "waived_unused": waived,
            "violations": bad + [f for f in forbidden if f not in bad],
            "reused_file_warnings": len([ln for ln in msgs if ln.startswith("%Warning") and ln not in ours])}


def elab_refusal(r_val: int) -> dict:
    """The fabric must refuse R != 2 at elaboration."""
    cmd = [str(VERILATOR), "--lint-only", "--top-module", "ot_gpu_coll_fabric", "-GENABLE=1", f"-GR={r_val}",
           *map(str, RTL)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    refused = r.returncode != 0 and "R must be 2" in (r.stdout + r.stderr)
    return {"R": r_val, "refused": refused, "pass": refused}


def build(bdir: Path, sw_pipe: int, link_pipe: int) -> Path:
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "2", "-Wno-fatal", "-Wno-lint", "-Wno-style",
           "--top-module", "tb_gpu_coll", f"-GSW_PIPE={sw_pipe}", f"-GLINK_PIPE={link_pipe}",
           "-Mdir", str(bdir / "obj"), str(BENCH), *map(str, RTL)]
    r = subprocess.run(cmd, cwd=bdir, capture_output=True, text=True, env={**os.environ, "MAKEFLAGS": "-j2"})
    (bdir / "build.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"verilator build failed, see {bdir / 'build.log'}")
    return bdir / "obj" / "Vtb_gpu_coll"


def check(cases: list[dict], dump: str) -> dict:
    rsp: dict[tuple[int, int], tuple[int, np.ndarray]] = {}
    done = None
    for ln in dump.splitlines():
        if m := re.match(r"RSP (\d+) (\d+) (-?\d+) ([0-9a-fA-F]+)", ln):
            v = int(m[4], 16)
            lanes = np.array([(v >> (32 * i)) & 0xFFFFFFFF for i in range(NL)], dtype=np.uint32)
            rsp[(int(m[1]), int(m[2]))] = (int(m[3]), lanes)
        elif m := re.match(r"DONE faults=(\d+) en0_bad=(\d+) rsp_held=(\d+) req_held=(\d+)", ln):
            done = (int(m[1]), int(m[2]), int(m[3]), int(m[4]))
    per_case, n_fail = [], 0
    for t, c in enumerate(cases):
        exp = expected(c)
        got = [rsp.get((r, t)) for r in range(R)]
        ok_present = all(g is not None for g in got)
        ok_bits = ok_present and all(np.array_equal(g[1], exp) for g in got)
        ok_agree = ok_present and all(np.array_equal(got[0][1], g[1]) for g in got)
        bad_lanes = [] if not ok_present else sorted({int(i) for g in got for i in np.nonzero(g[1] != exp)[0]})
        ok = ok_bits and ok_agree
        n_fail += not ok
        per_case.append(dict(t=t, mode=["ALL_REDUCE", "ALL_GATHER"][c["mode"]], count=c["count"],
                             measure=c["measure"], latency_sm=[g[0] if g else None for g in got],
                             pass_=ok, bad_lanes=bad_lanes[:8]))
    return dict(cases=per_case, n_fail=n_fail, done=done)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--build-dir", type=Path, default=None)
    ap.add_argument("--nt", type=int, default=160)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sw-pipe", type=int, default=4)
    ap.add_argument("--link-pipe", type=int, default=2)
    ap.add_argument("--no-lint", action="store_true")
    a = ap.parse_args()

    lints = [] if a.no_lint else [lint(t, e) for t in ("ot_gpu_coll_endpoint", "ot_gpu_coll_fabric") for e in (0, 1)]
    for li in lints:
        print(f"{'PASS' if li['pass'] else 'FAIL'} lint -Wall {li['top']} ENABLE={li['enable']} "
              f"(waived UNUSED: {len(li['waived_unused'])}) {li['violations'] or ''}")
    refusals = [] if a.no_lint else [elab_refusal(4), elab_refusal(3)]
    for rf in refusals:
        print(f"{'PASS' if rf['pass'] else 'FAIL'} fabric refuses R={rf['R']} at elaboration")

    bdir = a.build_dir or Path(tempfile.mkdtemp(prefix="gpu_coll_"))
    bdir.mkdir(parents=True, exist_ok=True)
    cases = make_cases(a.nt, a.seed)
    write_stim(cases, bdir / "stim.hex")
    exe = build(bdir, a.sw_pipe, a.link_pipe)
    r = subprocess.run([str(exe), f"+stim={bdir / 'stim.hex'}", f"+out={bdir / 'out.txt'}",
                        f"+verilator+seed+{a.seed}"], cwd=bdir, capture_output=True, text=True)
    (bdir / "sim.log").write_text(r.stdout + r.stderr)
    dump = (bdir / "out.txt").read_text() if (bdir / "out.txt").exists() else ""
    res = check(cases, dump)
    tb_done = res["done"] is not None
    faults_ok = tb_done and res["done"][0] == 0
    en0_ok = tb_done and res["done"][1] == 0
    print(f"{'PASS' if tb_done else 'FAIL'} bench completed (no timeout)  {r.stdout.strip().splitlines()[-1:]}")
    print(f"{'PASS' if faults_ok else 'FAIL'} no endpoint/switch fault")
    print(f"{'PASS' if en0_ok else 'FAIL'} ENABLE=0 instances all outputs 0")
    stress_ok = tb_done and res["done"][2] > 0 and res["done"][3] > 0
    print(f"{'PASS' if stress_ok else 'FAIL'} stress exercised: response-backpressure cycles "
          f"{res['done'][2] if tb_done else '-'}, request-held-while-busy cycles {res['done'][3] if tb_done else '-'}")
    nred = sum(1 for c in cases if c["mode"] == 0)
    print(f"{'PASS' if res['n_fail'] == 0 else 'FAIL'} {len(cases) - res['n_fail']}/{len(cases)} collectives bit "
          f"exact and rank-identical ({nred} ALL_REDUCE, {len(cases) - nred} ALL_GATHER)")
    for c in res["cases"]:
        if not c["pass_"]:
            print(f"   FAIL t={c['t']} {c['mode']} count={c['count']} bad_lanes={c['bad_lanes']}")
    meas = [c for c in res["cases"] if c["measure"]]
    lat = {}
    for c in meas:
        key = f"{c['mode']}_count{c['count']}"
        lat.setdefault(key, []).append(c["latency_sm"])
    lat_summary = {k: dict(per_rank_per_case=v, max_sm_cycles=max(max(x for x in p if x is not None) for p in v),
                           max_ns=round(max(max(x for x in p if x is not None) for p in v) * CLK_SM_PS / 1000, 3))
                   for k, v in lat.items()}
    for k, v in lat_summary.items():
        print(f"LATENCY {k}: {v['max_sm_cycles']} clk_sm cycles ({v['max_ns']} ns) per rank/case {v['per_rank_per_case']}")
    all_lat = [x for c in res["cases"] for x in c["latency_sm"] if x is not None]

    ok = (all(li["pass"] for li in lints) and all(rf["pass"] for rf in refusals) and tb_done and faults_ok and en0_ok
          and stress_ok and res["n_fail"] == 0)
    rec = {
        "schema": SCHEMA,
        "verdict": "PASS" if ok else "FAIL",
        "sources": {rel(p): sha(p) for p in [*RTL, BENCH, Path(__file__)]},
        "simulator": {"name": "verilator", "version": subprocess.run([str(VERILATOR), "--version"], capture_output=True,
                                                                     text=True).stdout.strip(),
                      "flags": "--binary --timing -j 2"},
        "config": {"R": R, "NL": NL, "LANES": 16, "clk_sm_ps": CLK_SM_PS, "clk_link_ps": CLK_LINK_PS,
                   "SW_PIPE": a.sw_pipe, "LINK_PIPE": a.link_pipe, "switch_DEPTH": 16, "tx_AW": 3, "rx_AW": 4,
                   "seed": a.seed, "nt_random": a.nt, "sw_pipe_note":
                       "REDUCED switch latency for the end-to-end token simulation; the W15-priced switch core is "
                       "~250 ns (tools/w15_collectives.py HBM_SWITCH) -> SW_PIPE ~ round(250/0.9) - (2 + 3L)"},
        "lint": lints,
        "elaboration_refusals": refusals,
        "bench": {"completed": tb_done, "fault_free": faults_ok, "enable0_inert": en0_ok,
                  "rsp_backpressure_cycles": res["done"][2] if tb_done else None,
                  "req_held_while_busy_cycles": res["done"][3] if tb_done else None,
                  "n_cases": len(cases), "n_fail": res["n_fail"],
                  "n_all_reduce": nred, "n_all_gather": len(cases) - nred,
                  "latency_all_cases_sm_cycles": {"min": min(all_lat) if all_lat else None,
                                                  "max": max(all_lat) if all_lat else None}},
        "latency": lat_summary,
        "cases": res["cases"],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{rec['verdict']} tb_gpu_coll -> {a.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
