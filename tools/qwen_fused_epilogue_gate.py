#!/usr/bin/env python3
"""Exactness gate of the fused post-all-reduce epilogue (Qwen3-8B ROM TP, level 1+5).

The pinned program applies the post-TP scale and the residual add as two
stream-unit ops (tools/hdc_qwen_fullshape_program_w12.py insert_post_tp_scales,
then the residual op of tools/hdc_program.build_program):

    T1 = fl(T1 x s)                 MC_C, s from the constant ROM
    X  = fl(X + T1), r = sum X^2    AD_C, reducer in the golden's chunked order

The fused op (tools/qwen_rom_async_coll.py) does the same two roundings in one
pass of the production unit: the multiply stage (MA_AB, b = s from the constant
ROM) then the add stage (AD_C, c = X), and the same reducer.  The golden is
hdc_golden: X' = add(X, mul(T1, s)), r = lane_sum(mul(X', X')).  Both programs
run on the production ot_hdc_vstream (SW 64, LV 7, the runtime's width) under
Verilator (rtl/test/tb_qwen_fused_epilogue_vl.sv); the outputs must be
bit-identical to each other and to the golden on every finite case, and the
fault flag must agree on the non-finite ones.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import hdc_golden as G

ROOT = Path(__file__).resolve().parents[1]
RTL = [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_fastfp", "ot_hdc_sfu",
                                   "ot_hdc_sfu_q", "ot_hdc_vstream_lane", "ot_hdc_vreduce", "ot_hdc_vstream")] + \
      ["rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/proto/ot_fp32_mul_rne_pipe.sv"]
TB = "rtl/test/tb_qwen_fused_epilogue_vl.sv"
SOURCES = RTL + [TB, "tools/hdc_golden.py", "tools/qwen_fused_epilogue_gate.py"]
VERILATOR = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
F = np.float32
NEL = 4096


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def case_vectors(kind, rng):
    """(T1, s, X) of 4,096 elements each."""
    if kind == "uniform":
        # folded raw o/down partial sums (integer-code dot products), row scales, a residual stream
        t1 = rng.uniform(-3000, 3000, NEL).astype(F)
        s = (rng.uniform(0.5, 2, NEL) * 2.0 ** rng.integers(-14, -4, NEL)).astype(F)
        x = rng.normal(0, 2, NEL).astype(F)
        return t1, s, x
    if kind == "wide":
        e = rng.integers(-40, 40, (3, NEL)).astype(np.float64)   # squares and their sum stay finite
        v = np.sign(rng.uniform(-1, 1, (3, NEL))) * rng.uniform(1, 2, (3, NEL)) * np.exp2(e)
        return v[0].astype(F), np.abs(v[1]).astype(F), v[2].astype(F)
    if kind == "adversarial":
        t1, s, x = case_vectors("uniform", rng)
        tiny = F(1.401298464324817e-45)
        n = 0

        def put(a, b, c):
            nonlocal n
            t1[n], s[n], x[n] = F(a), F(b), F(c)
            n += 1
        for _ in range(64):                            # exact cancellation: X = -(T1 s) -> canonical +0
            a, b = F(rng.uniform(-100, 100)), F(2.0 ** int(rng.integers(-10, 10)))
            put(a, b, -(a * b))
        for z1 in (0.0, -0.0):
            for z2 in (0.0, -0.0):
                put(z1, 1.0, z2)                        # signed zeros through mul and add
                put(1.0, 1.0, z2) if z1 == 0.0 else put(z1, 3.0, -1.0)
        for _ in range(64):                            # subnormal products, subnormal residuals
            put(F(rng.uniform(-4, 4)) * F(2.0 ** -120), F(2.0 ** -10), F(rng.choice([tiny, -tiny, 1e-40, -1e-40])))
        for _ in range(64):                            # products that round to the subnormal / zero boundary
            put(F(1.1754942e-38), F(rng.uniform(0.25, 1.0)), F(0))
            put(tiny, F(0.5), F(0))                     # 2^-150: RNE ties to even -> +0
        for _ in range(64):                            # sub-ulp addends: X dominates, ties to even
            a = F(rng.uniform(1, 2))
            put(F(2.0 ** -24), F(1.0), a)
            put(F(3 * 2.0 ** -25), F(1.0), F(1.0))
        for _ in range(64):                            # large but finite products and sums
            put(F(1.0e19), F(1.5e19), F(rng.uniform(-1e38, 1e38)))
        for _ in range(64):                            # catastrophic cancellation with rounding in the product
            a = F(rng.uniform(1, 2))
            b = F(1.0 + 2.0 ** -20)
            put(a, b, -a)
        return t1, s, x
    if kind == "nonfinite":
        t1, s, x = case_vectors("uniform", rng)
        t1[0], s[0] = F(3.0e38), F(1.5)                 # product overflow
        t1[1], s[1], x[1] = F(2.0e38), F(1.0), F(2.0e38)  # sum overflow
        t1[2] = F(np.inf)
        x[3] = F(np.nan)
        t1[4], x[4] = F(np.inf), F(-np.inf)
        return t1, s, x
    raise ValueError(kind)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    if args.result.exists():
        raise SystemExit("Refusing to overwrite an existing verdict")
    args.work.mkdir(parents=True, exist_ok=False)
    pins = {p: sha(ROOT / p) for p in SOURCES}
    result = {"schema": "opentallas.qwen-fused-epilogue-gate.v1", "status": "fail", "source_sha256": pins,
              "simulator": subprocess.check_output([VERILATOR, "--version"], text=True).strip(),
              "design_point": {"su_width": 64, "lv": 7, "elements": NEL},
              "golden": "X' = hdc_golden.add(X, hdc_golden.mul(T1, s)); r = hdc_golden.lane_sum(mul(X', X'))",
              "cases": {},
              "claim_boundary": "Production stream unit (ot_hdc_vstream) under Verilator with behavioural memories; "
                                "op-level exactness only (the layer/token check is the TP4 runtime run)."}
    try:
        mdir = args.work / "obj"
        t0 = time.monotonic()
        p = subprocess.run([VERILATOR, "--binary", "--timing", "-O3", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                            "-Wno-TIMESCALEMOD", "-Wno-PINMISSING", "-Wno-INITIALDLY", "-Wno-BLKSEQ",
                            "--top-module", "tb_qwen_fused_epilogue_vl", "--Mdir", str(mdir), "-j", "8",
                            *(str(ROOT / s) for s in RTL + [TB])], capture_output=True, text=True)
        (args.work / "build.log").write_text(p.stdout + p.stderr)
        result["build"] = {"returncode": p.returncode, "seconds": round(time.monotonic() - t0, 1)}
        if p.returncode:
            raise RuntimeError(f"verilator build failed: {p.stderr[-2000:]}")
        binary = mdir / "Vtb_qwen_fused_epilogue_vl"

        def run(vec, mode):
            p = subprocess.run([str(binary), f"+DIR={vec}", f"+MODE={mode}"], capture_output=True, text=True,
                               timeout=3600)
            (vec / f"mode{mode}.log").write_text(p.stdout + p.stderr)
            m = re.search(r"FUSEDEPI DONE mode=(\d) ops=(\d+) busy_cycles=(\d+) fault_cycles=(\d+) r=([0-9a-f]{8})",
                          p.stdout)
            if p.returncode or not m:
                raise RuntimeError(f"{vec.name} mode {mode}: no verdict\n{p.stdout[-1500:]}{p.stderr[-1500:]}")
            xs = np.zeros(NEL, dtype=np.uint32)
            for k, v in re.findall(r"^X (\d+) ([0-9a-f]{8})$", p.stdout, re.M):
                xs[int(k)] = int(v, 16)
            return {"ops": int(m[2]), "busy_cycles": int(m[3]), "fault_cycles": int(m[4]), "r": int(m[5], 16),
                    "x": xs}

        kinds = [(k, s) for k in ("uniform", "wide", "adversarial") for s in range(args.seeds)] + [("nonfinite", 0)]
        for kind, seed in kinds:
            tag = f"{kind}{seed}"
            vec = args.work / tag
            vec.mkdir()
            t1, s, x = case_vectors(kind, np.random.default_rng(20261003 + 17 * seed))
            vm = np.zeros(16384, dtype=np.uint32)
            vm[0:NEL], vm[NEL:2 * NEL] = G.bits(t1), G.bits(x)
            (vec / "vm.hex").write_text("".join(f"{v:08x}\n" for v in vm))
            (vec / "crom.hex").write_text("".join(f"00000000{v:08x}\n" for v in G.bits(s)))
            with np.errstate(over="ignore", invalid="ignore"):
                gx = G.add(x, G.mul(t1, s))
                gr = G.lane_sum(G.mul(gx, gx))
            gxb, grb = G.bits(gx), int(G.bits(np.asarray(gr, dtype=F)))
            two, fused = run(vec, 0), run(vec, 1)
            finite = bool(np.isfinite(gx).all()) and bool(np.isfinite(gr))   # X and its sum of squares
            nan_g = np.isnan(gx)
            same = bool((two["x"] == fused["x"]).all()) and two["r"] == fused["r"]
            vs_gold_two = int((two["x"] != gxb)[~nan_g].sum())
            vs_gold_fused = int((fused["x"] != gxb)[~nan_g].sum())
            nan_ok = bool(all(((fused["x"][nan_g] & 0x7F800000) == 0x7F800000) & ((fused["x"][nan_g] & 0x7FFFFF) != 0)))
            xb = G.bits(x)
            case = {"finite": finite, "two_op": {k: v for k, v in two.items() if k != "x"},
                    "fused": {k: v for k, v in fused.items() if k != "x"},
                    "fused_equals_two_op": same, "golden_r": f"{grb:08x}",
                    "x_mismatch_vs_golden_two_op": vs_gold_two, "x_mismatch_vs_golden_fused": vs_gold_fused,
                    "r_equals_golden_two_op": two["r"] == grb, "r_equals_golden_fused": fused["r"] == grb,
                    "golden_nan_lanes": int(nan_g.sum()), "fused_nan_where_golden_nan": nan_ok,
                    "fault_agrees": (two["fault_cycles"] > 0) == (fused["fault_cycles"] > 0),
                    "coverage": {"subnormal_results": int((((gxb & 0x7F800000) == 0) & ((gxb & 0x7FFFFFFF) != 0)).sum()),
                                 "zero_results": int(((gxb & 0x7FFFFFFF) == 0).sum()),
                                 "negative_zero_inputs": int((xb == 0x80000000).sum() + (G.bits(t1) == 0x80000000).sum())}}
            for k in ("two_op", "fused"):
                case[k]["r"] = f"{case[k]['r']:08x}"
            result["cases"][tag] = case
            # non-finite operands are a FAULT in this RTL (qmul/qadd err), not IEEE inf/NaN: there the criterion is
            # the two programs' identical bits and identical fault, not the golden's IEEE specials
            if not finite:
                if not (same and case["fault_agrees"] and two["fault_cycles"] > 0):
                    raise RuntimeError(f"{tag}: non-finite case: fused and two-op differ: {json.dumps(case)[:800]}")
                continue
            if not (same and vs_gold_two == 0 and vs_gold_fused == 0 and case["fault_agrees"] and nan_ok):
                raise RuntimeError(f"{tag}: fused epilogue not bit-exact: {json.dumps(case)[:800]}")
            if finite and not (case["r_equals_golden_two_op"] and case["r_equals_golden_fused"]
                               and two["fault_cycles"] == 0 and fused["fault_cycles"] == 0):
                raise RuntimeError(f"{tag}: reducer or fault mismatch on a finite case: {json.dumps(case)[:800]}")
        u = result["cases"]["uniform0"]
        result["cycles"] = {"two_op_busy": u["two_op"]["busy_cycles"], "fused_busy": u["fused"]["busy_cycles"],
                            "note": "issue-to-idle per op, each op issued on an idle unit (the runtime overlaps the "
                                    "two ops; the layer saving is measured on the TP4 runtime)"}
        result["source_stable"] = pins == {p: sha(ROOT / p) for p in SOURCES}
        if not result["source_stable"]:
            raise RuntimeError("source changed during the gate")
        result["status"] = "pass"
    except Exception as exc:  # the verdict is recorded either way
        result["error"] = str(exc)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    with args.result.open("x") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "cycles": result.get("cycles"), "error": result.get("error")},
                     indent=1))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
