#!/usr/bin/env python3
"""Multi-position verify on the W12 matrix engine: back-to-back issue of P copies of one op.

    python3 tools/qwen_rom_verify_burst_gate.py --workdir W --result R.json [--iverilog I] [--vvp V]

Builds rtl/test/tb_qwen_me_verify_burst_w12.sv with Icarus (-g2012) against the UNMODIFIED
ot_qwen_me_array_w12 at the TP4 runtime's wire stages (BD 41, XVM 1, NWS 5, TWS 38, ORD 7,
MEM_EXTRA 1; results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003/runtime/build_params.json), for the
four projection shapes of a layer's program (issue cycles tiles x k x IL: QKV 1x8, O 3x2, gate/up 1x32,
down 3x6; tools/hdc_qwen_fullshape_program_w12.py with QWEN_O4_TP=4) at P positions.  Each case checks
that the back-to-back results equal the solo results bit for bit, and reports the issue spacing and
the increment per extra position.  A MUTANT build (one position's x base shifted) must fail.
The engine is GT = 32 groups (the issue loop and the wire stages are independent of GT).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "rtl/test/tb_qwen_me_verify_burst_w12.sv"
RTL = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_qwen_me_array_w12", "ot_qwen_rom_tile_w12", "ot_hdc_matvec", "ot_hdc_fpu",
                                         "ot_hdc_fp32_mul_pipe", "ot_hdc_fastfp", "ot_hdc_delay", "ot_hdc_sfu",
                                         "ot_hdc_fp32_add_lat", "ot_hdc_prefix", "ot_qwen_w12_matvec", "ot_qwen_w12_arith")] \
    + [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
# (name, TILES, K, SPLIT, P): the TP4 layer-0 program's dense ops (rounds, k per split, IL 8)
CASES = [("qkv", 1, 8, 4, 4), ("o", 3, 2, 4, 4), ("gate_up", 1, 32, 4, 2), ("gate_up", 1, 32, 4, 4),
         ("gate_up", 1, 32, 4, 8), ("down", 3, 6, 4, 4)]
IL = 8


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--iverilog", default="iverilog")
    ap.add_argument("--vvp", default="vvp")
    a = ap.parse_args()
    if a.result.exists():
        raise SystemExit("Refusing to overwrite an existing verdict")
    out = a.workdir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pins = {str(p.relative_to(ROOT)): sha(p) for p in [TB, *RTL, Path(__file__)]}
    rows, steps = [], []

    vvp = out / "tb.vvp"
    t0 = time.monotonic()
    p = subprocess.run([a.iverilog, "-g2012", "-o", str(vvp), "-s", "tb_qwen_me_verify_burst_w12",
                        str(TB), *map(str, RTL)], capture_output=True, text=True)
    (out / "build.log").write_text(p.stdout + p.stderr)
    steps.append({"step": "build", "seconds": round(time.monotonic() - t0, 1), "rc": p.returncode})
    if p.returncode:
        raise SystemExit(f"build failed; see {out}/build.log")

    def run(tag, params):
        t0 = time.monotonic()
        s = subprocess.run([a.vvp, "-n", str(vvp), *[f"+{k}={v}" for k, v in params.items()]],
                           capture_output=True, text=True)
        (out / f"sim_{tag}.log").write_text(s.stdout + s.stderr)
        steps.append({"step": f"sim_{tag}", "seconds": round(time.monotonic() - t0, 1), "rc": s.returncode})
        print(tag, round(time.monotonic() - t0), "s", flush=True)
        return next((l for l in s.stdout.splitlines() if l.startswith(("PASS", "FAIL"))), "NO VERDICT")

    # every case and the negative control run concurrently (one single-threaded vvp each)
    jobs = {f"{n}_t{t}_k{k}_p{P}": dict(TILES=t, KK=k, SPLIT=sp, P=P) for n, t, k, sp, P in CASES}
    jobs["mutant"] = dict(TILES=1, KK=8, SPLIT=4, P=4, MUTANT=1)
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        verdicts = dict(zip(jobs, ex.map(lambda kv: run(*kv), jobs.items())))
    for name, tiles, k, split, P in CASES:
        v = verdicts[f"{name}_t{tiles}_k{k}_p{P}"]
        f = dict(re.findall(r"(\w+)=(-?\d+)", v))
        row = dict(case=name, tiles=tiles, k=k, split=split, P=P, verdict=v, passed=v.startswith("PASS"),
                   issue_cycles=tiles * k * IL)
        if row["passed"]:
            row.update({x: int(f[x]) for x in ("spacing_min", "spacing_max", "solo_latency", "burst_span",
                                                "increment_per_position", "writes")})
            row["solo_fixed_latency"] = row["solo_latency"] - row["issue_cycles"]
            row["increment_equals_issue_plus_gap"] = row["increment_per_position"] - row["issue_cycles"]
        rows.append(row)
    mut = verdicts["mutant"]
    stable = pins == {str(p.relative_to(ROOT)): sha(p) for p in [TB, *RTL, Path(__file__)]}
    passed = all(r["passed"] for r in rows) and mut.startswith("FAIL") and stable
    rec = {"schema": "opentallas.qwen-rom-verify-burst-gate.v1", "status": "pass" if passed else "fail",
           "question": "does the unmodified W12 matrix engine take P positions of one projection back to back, "
                       "bit-identical to P solo ops, at a cost per extra position equal to its issue cycles?",
           "engine": "ot_qwen_me_array_w12 GT=32 TG=4 SMIN=3 SMAX=5 TCUT=3 BD=41 XVM=1 NWS=5 TWS=38 ORD=7 MEM_EXTRA=1",
           "rows": rows, "negative_control": mut, "negative_control_rejected": mut.startswith("FAIL"),
           "simulator": subprocess.run([a.iverilog, "-V"], capture_output=True, text=True).stdout.splitlines()[0],
           "source_sha256": pins, "sources_stable": stable, "steps": steps,
           "claim_boundary": "matrix-engine issue and exactness only, reduced GT; no sequencer, SU, collective, "
                             "attention or LM head; no position-dependent DYN offsets; no physical timing"}
    a.result.parent.mkdir(parents=True, exist_ok=True)
    a.result.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["status"], [(r["case"], r["P"], r.get("increment_per_position"), r["issue_cycles"]) for r in rows], mut[:60])


if __name__ == "__main__":
    main()
