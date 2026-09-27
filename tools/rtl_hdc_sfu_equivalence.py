#!/usr/bin/env python3
"""Equivalence of the decode core's shortened special-function pipelines.

The stream unit's exp / reciprocal / rsqrt (rtl/hdc/ot_hdc_sfu.sv) now run on
the low-latency binary32 units (3 stages instead of 5) and form exp's n and
n*ln2 with an integer step and a table instead of two adds and two multiplies.
The numerics must not move by a bit.  This campaign checks that three ways:

1. exp range reduction, EXHAUSTIVELY: for every one of the 2^32 input words,
   the RTL's integer rint and table give the golden's n, n*LN2_HI and
   RN(n*LN2_LO) (tools/check_hdc_exp_reduction.py); after that point both
   designs apply the same operation sequence to the same operands.
2. the pipelines against the previous ones (rtl/test/ot_hdc_sfu_ref.sv), in
   RTL under Verilator (rtl/test/tb_hdc_sfu_equiv.sv): exp, reciprocal, rsqrt
   and the sigmoid denominator path reciprocal(exp(x) + 1), every result bit
   and every fault, on every 64th input word over all 2^32 (67,108,864 per
   function) plus every word of eight edge ranges (zero, the clamps, the
   subnormal/normal boundary, the top of the range, both signs);
3. the adder and multiplier themselves against the qualified pipes on
   edge-biased random pairs (also in tools/rtl_hdc_decode_campaign.py).

Writes results/rtl/hdc_sfu_equivalence.json.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/hdc_sfu_equivalence.json"
FP = [ROOT / "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", ROOT / "rtl/hdc/ot_hdc_fpu.sv", ROOT / "rtl/hdc/ot_hdc_fastfp.sv",
      ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
SRC = [ROOT / "rtl/hdc/ot_hdc_delay.sv", *FP, ROOT / "rtl/hdc/ot_hdc_sfu.sv"]
REF = ROOT / "rtl/test/ot_hdc_sfu_ref.sv"
TB = ROOT / "rtl/test/tb_hdc_sfu_equiv.sv"
HARNESS = ROOT / "rtl/test/hdc_sfu_equiv_harness.cpp"
TB_FAST = ROOT / "rtl/test/tb_hdc_fastfp_equiv.sv"
HARNESS_FAST = ROOT / "rtl/test/hdc_fastfp_equiv_harness.cpp"
CHECK = ROOT / "tools/check_hdc_exp_reduction.py"
FUNCS = {0: "exp", 1: "reciprocal", 2: "rsqrt", 3: "sigmoid_denominator"}
STRIDE = 64
SLICES = 8
EDGES = [("00000000", "00100000"), ("80000000", "80100000"), ("3f000000", "3f100000"),
         ("42ac0000", "42b20000"), ("c2ac0000", "c2b20000"), ("7f700000", "7f900000"),
         ("ff700000", "ff900000"), ("00700000", "00900000")]
LINE = re.compile(r"SFUEQ func=(\d+) lo=(\w+) hi=(\w+) checked=(\d+) mismatches=(\d+) blocks=(\d+) "
                  r"fault_blocks=(\d+) fault_mismatches=(\d+)")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(jobs, fast_vectors):
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O3", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                        "-Wno-BLKSEQ", "--top-module", "tb_hdc_sfu_equiv", "-Mdir", str(s / "obj"),
                        *map(str, SRC), str(REF), str(TB), str(HARNESS), "-CFLAGS", "-O2"],
                       check=True, capture_output=True)
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                        "-Wno-BLKSEQ", "--top-module", "tb_hdc_fastfp_equiv", "-Mdir", str(s / "objq"),
                        *map(str, FP), str(TB_FAST), str(HARNESS_FAST), "-CFLAGS", "-O1"],
                       check=True, capture_output=True)
        exe = str(s / "obj" / "Vtb_hdc_sfu_equiv")
        runs = []
        for f in FUNCS:
            for k in range(SLICES):
                span = (1 << 32) // SLICES
                runs.append((f, "sweep", [f"+LO={k * span:x}", f"+HI={(k + 1) * span:x}", f"+STRIDE={STRIDE}"]))
            for lo, hi in EDGES:
                runs.append((f, "edge", [f"+LO={lo}", f"+HI={hi}"]))
        runs += [(None, "fast", [f"+N={fast_vectors}", f"+SEED={seed}"]) for seed in (11, 22, 33, 44)]

        def one(r):
            f, kind, args = r
            if kind == "fast":
                out = subprocess.run([str(s / "objq" / "Vtb_hdc_fastfp_equiv"), *args], check=True,
                                     capture_output=True, text=True).stdout
                m = re.search(r"FASTFP checked=(\d+) add_mismatches=(\d+) mul_mismatches=(\d+)", out)
                return kind, None, dict(checked=int(m.group(1)), add_mismatches=int(m.group(2)),
                                        mul_mismatches=int(m.group(3)), passed="PASS" in out)
            out = subprocess.run([exe, f"+FUNC={f}", *args], check=True, capture_output=True, text=True).stdout
            m = LINE.search(out)
            return kind, f, dict(lo=m.group(2)[-8:], hi=m.group(3)[-8:], checked=int(m.group(4)),
                                 mismatches=int(m.group(5)), fault_blocks=int(m.group(7)),
                                 fault_mismatches=int(m.group(8)), passed="PASS" in out)

        with ThreadPoolExecutor(jobs) as ex:
            results = list(ex.map(one, runs))
    red = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
    mr = re.search(r"EXP_REDUCTION words=(\d+) mismatches=(\d+)", red.stdout)
    funcs = {}
    for f, name in FUNCS.items():
        rows = [r for k, ff, r in results if ff == f]
        sweep = [r for (k, ff, r) in results if ff == f and k == "sweep"]
        funcs[name] = {"inputs_checked": sum(r["checked"] for r in rows),
                       "sweep_inputs": sum(r["checked"] for r in sweep),
                       "edge_ranges": [[r["lo"], r["hi"]] for (k, ff, r) in results if ff == f and k == "edge"],
                       "mismatches": sum(r["mismatches"] for r in rows),
                       "fault_blocks": sum(r["fault_blocks"] for r in rows),
                       "fault_mismatches": sum(r["fault_mismatches"] for r in rows),
                       "pass": all(r["passed"] for r in rows)}
    fast = [r for k, _, r in results if k == "fast"]
    fast_rec = {"pairs": sum(r["checked"] for r in fast), "add_mismatches": sum(r["add_mismatches"] for r in fast),
                "mul_mismatches": sum(r["mul_mismatches"] for r in fast), "pass": all(r["passed"] for r in fast)}
    exp_red = {"words": int(mr.group(1)), "mismatches": int(mr.group(2)), "pass": red.returncode == 0}
    status = "pass" if exp_red["pass"] and fast_rec["pass"] and all(v["pass"] for v in funcs.values()) else "fail"
    return {
        "schema": "opentallas.hdc-sfu-equivalence.v1",
        "status": status,
        "claim": "the shortened special-function pipelines (exp 49, reciprocal 28, rsqrt 37 cycles; were 92 / "
                 "46 / 61) compute the previous pipelines' results bit for bit, faults included",
        "depth_cycles": {"exp": [92, 49], "reciprocal": [46, 28], "rsqrt": [61, 37],
                         "sigmoid_path": [143, 80], "fp_add": [5, 3], "fp_mul": [5, 3]},
        "exp_range_reduction_exhaustive": exp_red,
        "functions": funcs,
        "method": {"sweep_stride": STRIDE, "fault_block_inputs": 4096,
                   "reference": str(REF.relative_to(ROOT))},
        "low_latency_fp_units": fast_rec,
        "input_sha256": {str(p.relative_to(ROOT)): sha(p)
                         for p in (*SRC, REF, TB, HARNESS, TB_FAST, HARNESS_FAST, CHECK, Path(__file__))},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--jobs", type=int, default=min(32, os.cpu_count() or 8))
    ap.add_argument("--fast-vectors", type=int, default=100_000_000, help="pairs per seed (4 seeds)")
    args = ap.parse_args()
    rec = run(args.jobs, args.fast_vectors)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(rec["status"], json.dumps({k: (v["inputs_checked"], v["mismatches"]) for k, v in rec["functions"].items()}))
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
