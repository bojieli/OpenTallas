#!/usr/bin/env python3
"""Exactness and timing campaign of the GPU-organised HBM comparator's SM element (rtl/gpu).

    python3 tools/rtl_gpu_sm_exact.py lanes    [--out results/rtl/gpu_sm_exact.json]
    python3 tools/rtl_gpu_sm_exact.py blockdot [--out results/rtl/gpu_sm_blockdot_exact.json]

For every case it draws an op (rows x K, golden K split), writes the SM's inputs in the element's own layout
(the lockstep weight-line stream, the x store words, the row scales), runs the RTL under Icarus, and
compares every output bit with the golden:
  lanes / qwen_int8   hdc_golden.matvec(codes, x, split) then one FP32 x BF16 row-scale multiply
                      (qwen3_deployment_quality.int8_mv_t, the O4 INT8 contract)
  lanes / v41_bf16    hdc_golden_v41.csum(mul(w, bf16(x))), the R-ARITH chunk-8 contract (matvec_c, chunk8)
  blockdot / v41_fp8, v41_fp4
                      hdc_golden_v41.linear_q FP32 accumulator (chunk8): exact k32 block dot, one rounding,
                      2^(e_w + e_x) scale, csum over blocks
It also records the element's measured cycles: start -> last result, and the drain (last weight line ->
last result), which replace the model's formula drain (tools/uarch_model.GPU_MEASURED).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402

F = np.float32
IL = 8


def issue_order(R, Gn, c, gs):
    """The SM's lockstep weight-line order (rtl/gpu/ot_gpu_issue.sv): row-slot  rb, g, t, s  with slot s =
    row rb + s; group-slot  wave, t, s  over (row, group) items in row-major order.  Yields (row, g, t)."""
    if not gs:
        for rb in range(0, R, IL):
            for g in range(Gn):
                for t in range(c):
                    for s in range(IL):
                        if rb + s < R:
                            yield rb + s, g, t
    else:
        items = [(r, g) for r in range(R) for g in range(Gn)]
        for wb in range(0, len(items), IL):
            for t in range(c):
                for s in range(IL):
                    if wb + s < len(items):
                        r, g = items[wb + s]
                        yield r, g, t
LANE_SRC = ["rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv", "rtl/gpu/ot_gpu_sm.sv",
            "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
            "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/test/tb_gpu_sm.sv"]
SMQ_SRC = ["rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv",
           "rtl/gpu/ot_gpu_bulk_copy.sv", "rtl/gpu/ot_gpu_xstore.sv", "rtl/gpu/ot_gpu_sm_q.sv",
           "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
           "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv",
           "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v",
           "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
           "rtl/test/tb_gpu_sm_q.sv"]
SMV_SRC = ["rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv",
           "rtl/gpu/ot_gpu_bd_col.sv", "rtl/hdc/v41/ot_hdc_blockdot.sv", "rtl/gpu/ot_gpu_bulk_copy.sv",
           "rtl/gpu/ot_gpu_sm_v.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
           "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv",
           "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v",
           "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
           "rtl/test/tb_gpu_sm_v.sv"]
BD_SRC = ["rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_bd_col.sv", "rtl/gpu/ot_gpu_sm_bd.sv",
          "rtl/hdc/v41/ot_hdc_blockdot.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
          "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv",
          "rtl/test/tb_gpu_sm_bd.sv"]


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def bf16_bits(a):
    return (G.bits(G.to_bf16(np.asarray(a, dtype=F))) >> 16).astype(np.uint32)


def hexw(vals, width_bits, lane_bits):
    """Pack little-endian lane values (lane 0 in the low bits) into a hex word."""
    v = 0
    for i, x in enumerate(vals):
        v |= (int(x) & ((1 << lane_bits) - 1)) << (lane_bits * i)
    return f"{v:0{width_bits // 4}x}"


def compile_tb(src, top, params, outdir):
    exe = Path(outdir) / "sim.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(exe), "-s", top] + [f"-P{top}.{k}={v}" for k, v in params.items()] \
        + [str(ROOT / s) for s in src]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return exe


def run_sim(exe, d, gap):
    subprocess.run(["vvp", "-n", str(exe), f"+DIR={d}", f"+GAP={gap}"], check=True, cwd=d,
                   stdout=subprocess.DEVNULL)
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


# ---------------------------------------------------------------------------------------------------------
# lane SM (Qwen INT8, V4.1 BF16)
# ---------------------------------------------------------------------------------------------------------
def lane_case(name, fmt, R, K, split, NC, SUB, LS, rng=None, gap=0, gs=False, bench="sm", xdepth=96, rmax=256, lev=5, workdir=None,
              exe_cache={}):
    L = SUB * LS
    if fmt == "qwen_int8":
        c = K // split
        C = split
        codes = rng.integers(-128, 128, size=(R, K)).astype(np.int8)
        w = codes.astype(F)
        scale = G.to_bf16(rng.uniform(2e-4, 4e-3, size=R).astype(F))
        X = [rng.standard_normal(K).astype(F) * F(rng.choice([0.05, 1.0, 20.0])) for _ in range(NC)]
        gold = [G.mul(G.matvec(w, x, split), scale) for x in X]
        wbits = (codes.astype(np.int64) & 0xFF)
        wlane = 8
    else:                                   # v41_bf16: chunk-8 csum, BF16 weights
        c = 8
        C = -(-K // 8)
        w = G.to_bf16(rng.standard_normal((R, K)).astype(F) * F(0.02))
        scale = np.ones(R, dtype=F)
        X = [rng.standard_normal(K).astype(F) for _ in range(NC)]
        gold = [V.csum(G.mul(w, G.to_bf16(x)[None, :])) for x in X]
        wbits = bf16_bits(w).astype(np.int64)
        wlane = 16
    Gn = -(-C // L)
    assert c * Gn <= xdepth, (c, Gn)
    # weight lines in the lockstep order rb, g, t, s (rows past R are bubbles: no line)
    lines = []
    if True:
        for r, g, t in issue_order(R, Gn, c, gs):
                    vals = []
                    for j in range(L):
                        ch = g * L + j
                        k = ch * c + t
                        vals.append(int(wbits[r, k]) if (ch < C and k < K) else 0)
                    lines.append(hexw(vals, L * wlane, wlane))
    xw = []
    xb = [bf16_bits(x) for x in X]
    for a in range(xdepth):
        g, t = divmod(a, c)
        vals = []
        for n in range(NC):
            for j in range(L):
                ch = g * L + j
                k = ch * c + t
                vals.append(int(xb[n][k]) if (g < Gn and ch < C and k < K) else 0)
        xw.append(hexw(vals, L * NC * 16, 16))
    d = Path(tempfile.mkdtemp(prefix=f"gsm_{name}_", dir=workdir))
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    (d / "scale.hex").write_text("\n".join(f"{int(v):04x}" for v in bf16_bits(scale)) + "\n")
    (d / "cfg.hex").write_text("\n".join(f"{v:08x}" for v in (R, c, Gn, 1 if fmt == "qwen_int8" else 0,
                                                                len(lines), int(gs), 0, 0)) + "\n")
    if bench == "sm_q":
        assert fmt == "qwen_int8" and not gs
        params = dict(SUB=SUB, LS=LS, NC=NC, XDEPTH=xdepth, RMAX=rmax, LEV=lev, NXM=max(1, SUB * LS * NC * 16 // 256 // 8))
        key = ("q",) + tuple(sorted(params.items()))
        if key not in exe_cache:
            exe_cache[key] = compile_tb(SMQ_SRC, "tb_gpu_sm_q", params, tempfile.mkdtemp(prefix="gsmq_build_", dir=workdir))
    else:
        params = dict(SUB=SUB, LS=LS, NC=NC, XDEPTH=xdepth, RMAX=rmax, LEV=lev, INT8=1 if fmt == "qwen_int8" else 0)
        key = tuple(sorted(params.items()))
        if key not in exe_cache:
            exe_cache[key] = compile_tb(LANE_SRC, "tb_gpu_sm", params, tempfile.mkdtemp(prefix="gsm_build_", dir=workdir))
    res, meta = run_sim(exe_cache[key], d, gap)
    mism = 0
    for r in range(R):
        h = res.get(r)
        if h is None:
            mism += NC
            continue
        v = int(h, 16)
        for n in range(NC):
            got = (v >> (32 * n)) & 0xFFFFFFFF
            if got != int(G.bits(gold[n][r])):
                mism += 1
    return dict(case=name, bench=bench, fmt=fmt, issue="group_slot" if gs else "row_slot", rows=R, K=K, chunk_len=c,
                chunks=C, split=split, groups=Gn, lanes=L,
                sub_partitions=SUB, cols=NC, stream_gap_pct=gap, weight_lines=len(lines), results=len(res),
                mismatches=mism, exact=(mism == 0 and len(res) == R and not meta.get("timeout")
                                        and meta.get("fault", 1) == 0), rtl=meta)


def _run_specs(fn, specs, jobs, seed):
    """Run case specs (name, *args, kw): the first serially (compiles the bench), the rest in a thread pool.
    Each case draws from its own seeded generator, so the vectors do not depend on scheduling."""
    from concurrent.futures import ThreadPoolExecutor
    def one(i_spec):
        i, (args, kw) = i_spec
        return fn(*args, rng=np.random.default_rng(seed + i), **kw)
    items = list(enumerate(specs))
    out = [one(items[0])]
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        out += list(ex.map(one, items[1:]))
    return out


def lanes_campaign(args):
    V.set_arith("chunk8")
    SUB, LS, NC = 4, 32, args.cols
    kw = dict(workdir=args.workdir)
    specs = [
        # Qwen INT8 at the SM's shape (128 lanes): the golden splits of the shipped matrices at small K
        (("q_kc1_tree", "qwen_int8", 16, 512, 512, NC, SUB, LS), kw),          # q/k/v/o: kc = 1
        (("q_kc4", "qwen_int8", 13, 1024, 256, NC, SUB, LS), kw),              # lm_head-like kc 4, partial row block
        (("q_kc3_down", "qwen_int8", 9, 768, 256, NC, SUB, LS), kw),           # down: kc = 3
        (("q_kc32_gateup", "qwen_int8", 8, 4096, 128, NC, SUB, LS), kw),       # gate/up: split 128, kc 32
        (("q_split64_pad", "qwen_int8", 8, 256, 64, NC, SUB, LS), kw),         # split < lanes: +0 leaves
        (("q_kc1_gaps", "qwen_int8", 16, 512, 512, NC, SUB, LS), dict(kw, gap=35)),  # stream underflow
        # V4.1 BF16 matrices on the V4.1 SM's 64 BF16 lanes (4 x 16), chunk-8 csum
        (("v_bf16_k512", "v41_bf16", 16, 512, 0, NC, 4, 16), kw),
        (("v_bf16_k1004_pad", "v41_bf16", 11, 1004, 0, NC, 4, 16), kw),        # tail chunk + pow2 pad
        (("v_bf16_k5120", "v41_bf16", 8, 5120, 0, NC, 4, 16), kw),             # lm_head/router K: G = 10 -> 16
        # group-slot issue (a row's groups on different slots): 1-3-row slices, the V4.1 per-die case
        (("v_bf16_k5120_gs_r1", "v41_bf16", 1, 5120, 0, NC, 4, 16), dict(kw, gs=True)),
        (("v_bf16_k1004_gs_r3", "v41_bf16", 3, 1004, 0, NC, 4, 16), dict(kw, gs=True, gap=25)),
        (("q_kc4_gs_r2", "qwen_int8", 2, 2048, 512, NC, SUB, LS), dict(kw, gs=True)),
        # the SM macro top (ot_gpu_sm_q): weights through its own bulk copy and SRAM ring, x from its SRAM store
        (("smq_kc1_tree", "qwen_int8", 16, 512, 512, NC, SUB, LS), dict(kw, bench="sm_q")),
        (("smq_kc3_down", "qwen_int8", 9, 768, 256, NC, SUB, LS), dict(kw, bench="sm_q")),
        (("smq_kc32_gateup", "qwen_int8", 8, 4096, 128, NC, SUB, LS), dict(kw, bench="sm_q", xdepth=32)),
    ]
    return _run_specs(lane_case, specs, args.jobs, 20260929)


# ---------------------------------------------------------------------------------------------------------
# block-dot SM (V4.1 FP8 dense, FP4 routed experts)
# ---------------------------------------------------------------------------------------------------------
def _codes():
    import rtl_hdc_v41_blockdot_campaign as BC
    return BC.e4m3_codes, BC.e2m1_codes


def bd_case(name, fmt, R, K, NC, rng=None, SUB=4, LBS=2, gap=0, gs=False, xdepth=64, rmax=256, lev=3, workdir=None,
            exe_cache={}):
    e4m3_codes, e2m1_codes = _codes()
    LB = SUB * LBS
    fp4 = fmt == "v41_fp4"
    LA = LB if fp4 else LB // 2
    nb = K // 32
    c = 8
    C = -(-nb // c)
    Gn = -(-C // LA)
    assert c * Gn <= xdepth
    if fp4:
        mag = rng.integers(0, 8, size=(R, K))
        wv = V.E2M1_VALUES[mag] * np.where(rng.random((R, K)) < 0.5, -1.0, 1.0)
        wcode = e2m1_codes(wv.reshape(-1)).reshape(R, K)
        we = rng.integers(-6, 0, size=(R, nb))
    else:
        cc = rng.integers(0, 256, size=(R, K))
        cc = np.where((cc & 0x7F) == 0x7F, cc ^ 0x01, cc)          # no NaN codes
        wv = V.E4M3[cc].astype(np.float64)
        wcode = e4m3_codes(wv.reshape(-1)).reshape(R, K)
        we = rng.integers(-14, -8, size=(R, nb))
    wq = V.Q8(wv, we.astype(np.int64))
    X = [rng.standard_normal(K).astype(F) * F(rng.choice([0.1, 1.0, 8.0])) for _ in range(NC)]
    gold, xqs = [], []
    for x in X:
        xq, xe = V.quant_fp8(x)
        terms = np.stack([np.ldexp((wq.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F),
                                   wq.e[:, b] + xe[b]).astype(F) for b in range(nb)], axis=-1)
        gold.append(V.csum(terms))
        xqs.append((e4m3_codes(xq), xe))
    def lane_field(codes32, e):
        v = 0
        for i, cd in enumerate(codes32):
            v |= (int(cd) & 0xFF) << (8 * i)
        return v | ((int(e) & 0x3FF) << 256)
    lines = []
    if True:
        for r, g, t in issue_order(R, Gn, c, gs):
                    word = 0
                    for j in range(LB):
                        ch = g * LA + j
                        b = ch * c + t
                        if j < LA and ch < C and b < nb:
                            word |= lane_field(wcode[r, b * 32:(b + 1) * 32], we[r, b]) << (266 * j)
                    lines.append(f"{word:0{LB * 266 // 4 + 1}x}")
    xw = []
    for a in range(xdepth):
        g, t = divmod(a, c)
        word = 0
        for n in range(NC):
            codes, xe = xqs[n]
            for j in range(LB):
                ch = g * LA + j
                b = ch * c + t
                if g < Gn and j < LA and ch < C and b < nb:
                    word |= lane_field(codes[b * 32:(b + 1) * 32], xe[b]) << (266 * (n * LB + j))
        xw.append(f"{word:0{LB * NC * 266 // 4 + 1}x}")
    d = Path(tempfile.mkdtemp(prefix=f"gbd_{name}_", dir=workdir))
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    (d / "cfg.hex").write_text("\n".join(f"{v:08x}" for v in (R, c, Gn, 1 if fp4 else 0, len(lines), int(gs), 0, 0)) + "\n")
    params = dict(SUB=SUB, LBS=LBS, NC=NC, XDEPTH=xdepth, RMAX=rmax, LEV=lev)
    key = ("bd",) + tuple(sorted(params.items()))
    if key not in exe_cache:
        exe_cache[key] = compile_tb(BD_SRC, "tb_gpu_sm_bd", params, tempfile.mkdtemp(prefix="gbd_build_", dir=workdir))
    res, meta = run_sim(exe_cache[key], d, gap)
    mism = 0
    for r in range(R):
        h = res.get(r)
        if h is None:
            mism += NC
            continue
        v = int(h, 16)
        for n in range(NC):
            if ((v >> (32 * n)) & 0xFFFFFFFF) != int(G.bits(gold[n][r])):
                mism += 1
    return dict(case=name, bench="sm_bd", fmt=fmt, issue="group_slot" if gs else "row_slot", rows=R, K=K, blocks=nb, chunk_len=c, chunks=C, active_lanes=LA, groups=Gn,
                lanes=LB, sub_partitions=SUB, cols=NC, stream_gap_pct=gap, weight_lines=len(lines),
                results=len(res), mismatches=mism,
                exact=(mism == 0 and len(res) == R and not meta.get("timeout") and meta.get("fault", 1) == 0),
                rtl=meta)


def smv_case(name, fmt, R, K, NC, rng=None, gs=False, gap=0, SUB=4, LBS=2, LSB=16, xdepth=128, rmax=256, lev=4,
             workdir=None, exe_cache={}):
    """The V4.1 SM macro top (ot_gpu_sm_v): packed 136-B weight lines through its bulk copy and SRAM ring,
    fragments from its per-cycle SRAM x store.  Goldens as bd_case (FP8/FP4 linear_q) and lane_case (BF16)."""
    e4m3_codes, e2m1_codes = _codes()
    LB, LF = SUB * LBS, SUB * LSB
    XC = LB * 266 + LF * 16
    X = [rng.standard_normal(K).astype(F) * F(rng.choice([0.1, 1.0, 8.0])) for _ in range(NC)]
    c = 8
    if fmt == "v41_bf16":
        C = -(-K // 8)
        LA = LF
        w = G.to_bf16(rng.standard_normal((R, K)).astype(F) * F(0.02))
        gold = [V.csum(G.mul(w, G.to_bf16(x)[None, :])) for x in X]
        wb = bf16_bits(w).astype(np.int64)
        xb = [bf16_bits(x) for x in X]
    else:
        fp4 = fmt == "v41_fp4"
        nb = K // 32
        C = -(-nb // c)
        LA = LB if fp4 else LB // 2
        if fp4:
            mag = rng.integers(0, 8, size=(R, K))
            wv = V.E2M1_VALUES[mag] * np.where(rng.random((R, K)) < 0.5, -1.0, 1.0)
            wcode = e2m1_codes(wv.reshape(-1)).reshape(R, K)
            we = rng.integers(-6, 0, size=(R, nb))
        else:
            cc = rng.integers(0, 256, size=(R, K))
            cc = np.where((cc & 0x7F) == 0x7F, cc ^ 0x01, cc)
            wv = V.E4M3[cc].astype(np.float64)
            wcode = e4m3_codes(wv.reshape(-1)).reshape(R, K)
            we = rng.integers(-14, -8, size=(R, nb))
        wq = V.Q8(wv, we.astype(np.int64))
        gold, xqs = [], []
        for x in X:
            xq, xe = V.quant_fp8(x)
            terms = np.stack([np.ldexp((wq.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F),
                                       wq.e[:, b] + xe[b]).astype(F) for b in range(nb)], axis=-1)
            gold.append(V.csum(terms))
            xqs.append((e4m3_codes(xq), xe))
    Gn = -(-C // LA)
    assert Gn * c <= xdepth, (Gn, c, xdepth)
    lines = []
    for r, g, t in issue_order(R, Gn, c, gs):
        word = 0
        for j in range(LA):
            ch = g * LA + j
            if fmt == "v41_bf16":
                k = ch * c + t
                if ch < C and k < K:
                    word |= int(wb[r, k]) << (16 * j)
            else:
                b = ch * c + t
                if ch < C and b < nb:
                    codes = wcode[r, b * 32:(b + 1) * 32]
                    if fp4:
                        for i, cd in enumerate(codes):
                            word |= (int(cd) & 0xF) << (128 * j + 4 * i)
                    else:
                        for i, cd in enumerate(codes):
                            word |= (int(cd) & 0xFF) << (256 * j + 8 * i)
                    word |= ((int(we[r, b]) + 127) & 0xFF) << (1024 + 8 * j)
        lines.append(f"{word:0272x}")
    xw = []
    for a in range(xdepth):
        g, t = divmod(a, c)
        word = 0
        for n in range(NC):
            for j in range(LA):
                ch = g * LA + j
                if g >= Gn or ch >= C:
                    continue
                if fmt == "v41_bf16":
                    k = ch * c + t
                    if k < K:
                        word |= int(xb[n][k]) << (n * XC + LB * 266 + 16 * j)
                else:
                    b = ch * c + t
                    if b < nb:
                        codes, xe = xqs[n]
                        f = 0
                        for i, cd in enumerate(codes[b * 32:(b + 1) * 32]):
                            f |= (int(cd) & 0xFF) << (8 * i)
                        f |= (int(xe[b]) & 0x3FF) << 256
                        word |= f << (n * XC + 266 * j)
        xw.append(f"{word:0{(NC * XC + 3) // 4}x}")
    d = Path(tempfile.mkdtemp(prefix=f"gsmv_{name}_", dir=workdir))
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    fmt_code = {"v41_bf16": 0, "v41_fp8": 1, "v41_fp4": 2}[fmt]
    (d / "cfg.hex").write_text("\n".join(f"{v:08x}" for v in (R, c, Gn, fmt_code, len(lines), int(gs), 0, 0)) + "\n")
    params = dict(SUB=SUB, LBS=LBS, LSB=LSB, NC=NC, XDEPTH=xdepth, RMAX=rmax, LEV=lev)
    key = ("v",) + tuple(sorted(params.items()))
    if key not in exe_cache:
        exe_cache[key] = compile_tb(SMV_SRC, "tb_gpu_sm_v", params, tempfile.mkdtemp(prefix="gsmv_build_", dir=workdir))
    res, meta = run_sim(exe_cache[key], d, gap)
    mism = 0
    for r in range(R):
        h = res.get(r)
        if h is None:
            mism += NC
            continue
        v = int(h, 16)
        for n in range(NC):
            if ((v >> (32 * n)) & 0xFFFFFFFF) != int(G.bits(gold[n][r])):
                mism += 1
    return dict(case=name, bench="sm_v", fmt=fmt, issue="group_slot" if gs else "row_slot", rows=R, K=K,
                chunk_len=c, chunks=C, active_lanes=LA, groups=Gn, cols=NC, weight_lines=len(lines),
                results=len(res), mismatches=mism,
                exact=(mism == 0 and len(res) == R and not meta.get("timeout") and meta.get("fault", 1) == 0),
                rtl=meta)


def bd_campaign(args):
    V.set_arith("chunk8")
    kw = dict(workdir=args.workdir)
    NC = args.cols
    specs = [
        (("fp4_k2304_down", "v41_fp4", 16, 2304, NC), kw),      # expert down: 72 blocks, 9 chunks
        (("fp4_k5120_gu", "v41_fp4", 11, 5120, NC), kw),        # expert gate/up: 160 blocks, 20 chunks
        (("fp8_k5120_dense", "v41_fp8", 9, 5120, NC), kw),      # dense FP8: 4 active lanes
        (("fp8_k1280_wqb", "v41_fp8", 8, 1280, NC), kw),        # wq_b: 40 blocks, 5 chunks
        (("fp8_k544_tail", "v41_fp8", 5, 544, NC), dict(kw, gap=30)),  # 17 blocks: short tail chunk, gaps
        # group-slot issue on 1-2-row slices (the V4.1 1/96 die slice)
        (("fp8_k5120_gs_r1", "v41_fp8", 1, 5120, NC), dict(kw, gs=True)),
        (("fp4_k5120_gs_r2", "v41_fp4", 2, 5120, NC), dict(kw, gs=True)),
        (("fp8_k2048_gs_r3", "v41_fp8", 3, 2048, NC), dict(kw, gs=True, gap=25)),
    ]
    out = _run_specs(bd_case, specs, args.jobs, 20260930)
    # the V4.1 SM macro top (ot_gpu_sm_v): packed lines through its bulk copy, per-cycle SRAM x store
    specs_v = [
        (("smv_fp8_k5120_gs_r1", "v41_fp8", 1, 5120, NC), dict(kw, gs=True)),
        (("smv_fp4_k5120_gs_r2", "v41_fp4", 2, 5120, NC), dict(kw, gs=True)),
        (("smv_bf16_k1004_gs_r3", "v41_bf16", 3, 1004, NC), dict(kw, gs=True)),
        (("smv_fp8_k1280_rowslot", "v41_fp8", 9, 1280, NC), kw),
    ]
    return out + _run_specs(smv_case, specs_v, args.jobs, 20261001)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("which", choices=["lanes", "blockdot"])
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--out")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    if a.which == "lanes":
        cases = lanes_campaign(a)
        src = LANE_SRC + [x for x in SMQ_SRC if x not in LANE_SRC]
    else:
        cases = bd_campaign(a)
        src = BD_SRC + [x for x in SMV_SRC if x not in BD_SRC]
    for c in cases:
        print(f"{c['case']:22s} {c['fmt']:10s} R{c['rows']:3d} K{c['K']:5d} G{c['groups']:2d}  exact={c['exact']}"
              f"  mism={c['mismatches']}  {c['rtl']}")
    ok = all(c["exact"] for c in cases)
    rec = dict(schema="opentallas.rtl.gpu_sm_exact.v1", tool="tools/rtl_gpu_sm_exact.py", which=a.which,
               status="pass" if ok else "fail", simulator="icarus " + subprocess.run(
                   ["iverilog", "-V"], capture_output=True, text=True).stdout.split("\n")[0],
               source_sha256={s: sha(s) for s in src + ["tools/rtl_gpu_sm_exact.py", "tools/hdc_golden.py",
                                                         "tools/hdc_golden_v41.py"]},
               cases=cases)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
