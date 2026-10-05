#!/usr/bin/env python3
"""HA3 fused-epilogue gate (Verilator, rtl/test/hbm_accel/tb_hbm_accel_ha3_epi.sv): the receive-path epilogue of
ot_hbm_accel_coll_port against the SM's own two-op program and against the golden.

Per case: two dies x two SMs (ot_hbm_accel_simt_sm, HA3 = 1), SM s of die d holds partial rows P (64 lanes, its rows
s*64..s*64+63 of die d's partial) and the residual X (128 lanes, identical on every SM, as the decode step keeps it).
  kernel A (two-op): red = COLLX(P) (cut-through, no fuse); x' = FADD(X, red); ss = Lib.seg_sum8(FMUL(x', x'), 128)
  kernel B (fused):  x' = COLLX.fuse(P, X); ss = COLLSS
  golden: x' = add(X, add(P_die0, P_die1)), ss = reduce_chunked(mul(x', x')) (tools/hdc_golden.py)
Verdict per case (resolving, not overwriting, the two FAILED ROM fused-epilogue verdicts of
claude/qwen-async-collective-20261003, results/rtl/qwen_async_collective_20261003/FAILED_fused_epilogue_gate_*):
  finite (golden x' and ss finite, no fault):   A == B == golden, bit for bit, on all four SMs
  non-finite operand / overflow (golden inf/NaN anywhere): both kernels FAULT (fail closed, the SM's pipes' rule) on
      every SM with identical stored bits -- the RTL never returns IEEE specials, so the golden's inf/NaN is not the
      reference there (FAILED_..._nonfinite_ieee); the wide set is bounded so its sum of squares is finite, and the
      overflowing sums form their own set judged by the fault (FAILED_..._wide_overflow)
  a case where A faults but the golden is finite is classified separately (the two-op program's seg_sum8 also adds
      wrapped garbage lanes that can overflow); B must then equal the golden.

    python3 tools/hbm_accel_ha3_epilogue_gate.py --work W --result W/gate.json [--seeds 3]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "gpu_sys"))
sys.path.insert(0, str(HERE))
import hbm_accel_ha3 as H  # noqa: E402  (registers COLLX / COLLSS)
import hdc_golden as G  # noqa: E402
import qwen_hbm as Q  # noqa: E402
from asm import Kernel  # noqa: E402

F, U = np.float32, np.uint32
VERILATOR = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
RS_DEP = ["rtl/gpu_sys/ot_gpu_cdc_fifo.sv", "rtl/gpu_sys/ot_gpu_coll_fabric.sv", "rtl/gpu_sys/ot_gpu_simt_lane.sv",
          "rtl/gpu_sys/ot_gpu_simt_divlane.sv", "rtl/gpu_sys/ot_gpu_bd_line.sv"]
SRC = ["rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv", "rtl/hbm_accel/collective/ot_hbm_accel_coll_port.sv",
       "rtl/test/hbm_accel/tb_hbm_accel_ha3_epi.sv"]


def kernels():
    def common(k, s):
        k.umovi(8, 0)
        v = k.lds(8, 0x0000, 64)
        x = k.lds(8, 0x0400, 128)
        return v, x

    out = []
    for fused in (False, True):
        per = {}
        for d in range(2):
            for s in range(2):
                k = Kernel(f"{'B' if fused else 'A'}.d{d}.s{s}")
                lib = Q.Lib(k)
                v, x = common(k, s)
                if fused:
                    xn = H.collx(k, v, 128, s * 64, 64, 0, True, x)
                    ss = H.collss(k)
                    k.sts(xn, 8, 0x1800, 128)
                    k.sts(ss, 8, 0x1C00, 1)
                else:
                    red = H.collx(k, v, 128, s * 64, 64)
                    xn = lib.add(x, red)
                    ss = lib.seg_sum8(lib.mul(xn, xn), 128)
                    k.sts(xn, 8, 0x1000, 128)
                    k.sts(ss, 8, 0x1400, 1)
                k.exit()
                per[(d, s)] = k.assemble()
        out.append(per)
    return out


def f32(a):
    return np.asarray(a, dtype=F)


def gen_cases(seeds):
    """sets: uniform, wide, adversarial, wide_overflow, nonfinite; each case = P[die][128] and X[128] (float32)."""
    cases = []
    for sd in range(seeds):
        rng = np.random.default_rng(1000 + sd)
        # uniform
        P = f32(rng.normal(0, 1, (2, 128)) * 10.0 ** rng.integers(-3, 3, (2, 128)))
        X = f32(rng.normal(0, 1, 128) * 10.0 ** rng.integers(-2, 2, 128))
        cases.append((f"uniform{sd}", P, X))
        # wide: exponents across the range, bounded so that every x'^2 and the sum stay finite (|x'| < 2^60)
        e = rng.integers(-140, 60, (3, 128)).astype(np.float64)
        sgn = rng.choice([-1.0, 1.0], (3, 128))
        raw = sgn * (1 + rng.random((3, 128))) * 2.0 ** e
        cases.append((f"wide{sd}", f32(raw[:2]), f32(raw[2])))
        # adversarial: cancellation to +0, signed zeros, subnormals, ties, near-overflow of x' (sumsq still finite
        # in a few lanes only: x' at 2^62)
        P = f32(rng.normal(0, 1, (2, 128)))
        X = f32(rng.normal(0, 1, 128))
        P[1, 0:16] = -P[0, 0:16]                                 # red = +0 exactly
        X[0:8] = F(0.0)
        X[8:16] = F(-0.0)
        P[0, 16:24] = F(-0.0); P[1, 16:24] = F(-0.0)              # (-0) + (-0) -> canonical +0
        X[16:24] = F(-0.0)
        tiny = np.float32(1.4e-45)
        P[0, 24:40] = tiny * rng.integers(1, 1 << 20, 16).astype(F)   # subnormal partials
        P[1, 24:40] = -tiny * rng.integers(1, 1 << 20, 16).astype(F)
        X[24:40] = tiny * rng.integers(-(1 << 20), 1 << 20, 16).astype(F)
        one = F(1.0); ulp = np.spacing(one)
        P[0, 40:56] = one; P[1, 40:56] = ulp / F(2)              # round-to-even ties: 1 + ulp/2 -> 1
        X[40:56] = F(2.0 ** 24)
        P[0, 56:60] = F(2.0 ** 62); P[1, 56:60] = F(-2.0 ** 40)  # large but finite squares (2^124)
        X[56:60] = F(2.0 ** 50)
        cases.append((f"adversarial{sd}", P, X))
        # wide overflow: the sum of squares overflows (x' ~ 2^64..2^127) -> the golden is inf
        P = f32(rng.normal(0, 1, (2, 128)))
        X = f32(rng.normal(0, 1, 128))
        X[rng.integers(0, 128, 4)] = F(2.0 ** 66) * F(1 + rng.random())
        cases.append((f"wide_overflow{sd}", P, X))
        # non-finite operands
        P = f32(rng.normal(0, 1, (2, 128)))
        X = f32(rng.normal(0, 1, 128))
        P[sd % 2, 5 + sd] = F(np.inf) if sd != 1 else F(np.nan)
        X[70 + sd] = F(-np.inf)
        cases.append((f"nonfinite{sd}", P, X))
        # garbage-lane check: finite golden whose wrapped two-op lanes could overflow (top lanes large, lane 0 small)
        P = f32(rng.normal(0, 1e-3, (2, 128)))
        X = f32(rng.normal(0, 1, 128))
        X[120:128] = F(1.3e19)                                   # chunk 15: 8 x 1.69e38 overflows in every program
        cases.append((f"chunk_overflow{sd}", P, X))
    return cases


def golden(P, X):
    with np.errstate(all="ignore"):
        red = G.add(P[0], P[1])
        xp = G.add(X, red)
        ss = G.reduce_chunked(G.mul(xp, xp))
    return xp.view(U), U(np.asarray(ss, dtype=F).view(U))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--result", required=True)
    ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    A, B = kernels()
    na = max(len(c) for c in A.values())
    nb = max(len(c) for c in B.values())
    for (d, s), ca in A.items():
        words = ca + [0] * (na - len(ca)) + B[(d, s)] + [0] * (nb - len(B[(d, s)]))
        (work / f"prog_d{d}_s{s}.hex").write_text("\n".join(f"{w:016x}" for w in words) + "\n")
    cases = gen_cases(a.seeds)
    for ci, (tag, P, X) in enumerate(cases):
        words = []
        for d in range(2):
            for s in range(2):
                words += list(P[d][s * 64:(s + 1) * 64].view(U)) + list(X.view(U))
        (work / f"case{ci}.hex").write_text("\n".join(f"{int(w):08x}" for w in words) + "\n")
    obj = work / "obj"
    exe = obj / "Vtb_hbm_accel_ha3_epi"
    t0 = time.time()
    if not exe.exists():
        cmd = [str(VERILATOR), "--binary", "--timing", "-O2", "-j", "16", "-Wno-fatal", "-Wno-lint", "-Wno-style",
               "-Wno-WIDTH", "--x-assign", "0", "--x-initial", "0", "--top-module", "tb_hbm_accel_ha3_epi",
               "--Mdir", str(obj)] + [str(ROOT / x) for x in RS_DEP + DEP + SRC]
        b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if b.returncode != 0:
            print(b.stdout[-3000:], b.stderr[-3000:])
            raise SystemExit("build failed")
    tb = time.time() - t0
    t1 = time.time()
    r = subprocess.run([str(exe), f"+DIR={work}", f"+N={len(cases)}", "+PA=0", f"+PB={na}", f"+IMEM={na + nb}"],
                       cwd=work, capture_output=True, text=True)
    tr = time.time() - t1
    res = parse(work / "out.txt")
    out = dict(cases={}, counts={})
    ok = r.returncode == 0 and "TB_HA3_EPI DONE" in r.stdout
    for ci, (tag, P, X) in enumerate(cases):
        gx, gs = golden(P, X)
        fin = bool(np.all(np.isfinite(gx.view(F))) and np.isfinite(gs.view(F)))
        ka, kb = res[ci][0], res[ci][1]
        fa = [ka[s]["fault"] for s in range(4)]
        fb = [kb[s]["fault"] for s in range(4)]
        same = all(ka[s]["x"] == kb[s]["x"] and ka[s]["ss"] == kb[s]["ss"] for s in range(4))
        b_gold = all(kb[s]["x"] == [int(v) for v in gx] and kb[s]["ss"] == int(gs) for s in range(4))
        a_gold = all(ka[s]["x"] == [int(v) for v in gx] and ka[s]["ss"] == int(gs) for s in range(4))
        case = dict(set=tag.rstrip("0123456789"), golden_finite=fin, fault_two_op=fa, fault_fused=fb,
                    two_op_eq_fused=same, fused_eq_golden=b_gold, two_op_eq_golden=a_gold,
                    cycles_two_op=[ka[s]["cyc"] for s in range(4)], cycles_fused=[kb[s]["cyc"] for s in range(4)],
                    golden_ss=f"{int(gs):08x}", ss_two_op=f"{ka[0]['ss']:08x}", ss_fused=f"{kb[0]['ss']:08x}",
                    subnormal_x=int(np.sum((gx & U(0x7F800000)) == 0) - np.sum((gx & U(0x7FFFFFFF)) == 0)),
                    zero_x=int(np.sum((gx & U(0x7FFFFFFF)) == 0)), neg_zero_inputs=int(np.sum(X.view(U) == 0x80000000)))
        if fin and not any(fa) and not any(fb):
            v = same and b_gold and a_gold
            case["verdict"] = "PASS_BIT_EXACT" if v else "FAIL"
        elif not fin:
            v = all(fa) and all(fb) and same
            case["verdict"] = "PASS_BOTH_FAIL_CLOSED" if v else "FAIL"
        elif any(fa) and not any(fb):
            v = b_gold
            case["verdict"] = "TWO_OP_SPURIOUS_FAULT_FUSED_EXACT" if v else "FAIL"
        else:
            v = False
            case["verdict"] = "FAIL"
        ok &= v
        out["cases"][tag] = case
        out["counts"][case["verdict"]] = out["counts"].get(case["verdict"], 0) + 1
    srcs = RS_DEP + DEP + SRC + ["tools/hbm_accel_ha3.py", "tools/hbm_accel_ha3_epilogue_gate.py", "tools/hdc_golden.py",
                                 "tools/gpu_sys/qwen_hbm.py", "tools/gpu_sys/asm.py", "tools/gpu_sys/isa.py"]
    rec = dict(schema="opentallas.hbm_accel.ha3_epilogue_gate.v1", status="pass" if ok else "fail",
               simulator=subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
               build_seconds=round(tb, 1), run_seconds=round(tr, 1), n_cases=len(cases), **out,
               criterion=__doc__.split("Verdict per case")[1].split("python3 tools")[0].strip(),
               resolves=["results/rtl/qwen_async_collective_20261003/FAILED_fused_epilogue_gate_nonfinite_ieee.json",
                         "results/rtl/qwen_async_collective_20261003/FAILED_fused_epilogue_gate_wide_overflow.json"],
               source_sha256={x: hashlib.sha256((ROOT / x).read_bytes()).hexdigest() for x in srcs})
    Path(a.result).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(status=rec["status"], counts=out["counts"]), indent=1))
    if not ok:
        print(r.stdout[-2000:])
    sys.exit(0 if ok else 1)


def parse(path):
    res = {}
    ci = None
    for line in path.read_text().splitlines():
        if line.startswith("CASE"):
            ci = int(line.split()[1])
            res.setdefault(ci, {0: {}, 1: {}})
        elif line.startswith("K "):
            f = line.split()
            k, sm = int(f[1]), int(f[3])
            res[ci][k][sm] = dict(fault=int(f[5]), portf=int(f[7]), cyc=int(f[9]), ss=int(f[11], 16),
                                  x=[int(v, 16) for v in f[13:13 + 128]])
    return res


DEP = ["rtl/hdc/ot_hdc_fpu.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
       "rtl/hdc/ot_hdc_fastfp.sv", "rtl/link/ot_link_afifo.sv", "rtl/link/ot_link_nvls_switch.sv",
       "rtl/gpu/ot_gpu_sm.sv", "rtl/gpu/ot_gpu_bulk_copy.sv", "rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv",
       "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv",
       "rtl/hdc/ot_hdc_prefix.sv", "rtl/abi3/ot_a3_fp32_div_rne_pipe.sv", "rtl/abi3/ot_a3_fp32_sqrt_rne.sv"]


if __name__ == "__main__":
    main()
