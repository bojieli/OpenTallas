#!/usr/bin/env python3
"""Bit-exact and performance campaign of the V4.1 attention engine (rtl/hdc/v41x/ot_hdc_v41x_attn*.sv).

The engine computes the two products of tools/hdc_golden_v41.py Model.attend under R-ARITH (chunk8):

    s[h, t]  = dots(q, kvm)[h, t]            (q BF16, csum over the head_dim)
    pv[h, d] = dots(to_bf16(e), kvm.T)[h, d]  (csum over the T rows, in the golden's row order)

with the KV rows given in their STORED format (window rows FP8 E4M3 + UE8M0 per 32, compressed rows FP4 E2M1
+ E4M3 per 16) and dequantised in the engine.  The softmax between them stays on the stream unit.

Vectors:
  * RANDOM (seeded): BF16 operands over the whole exponent range (zeros, subnormals, near-overflow), KV codes
    over every code and a wide scale range, tie-heavy coarse values; FP8 and FP4 rows mixed.
  * VEHICLE: every attention call of the reduced DeepSeek-V4.1 vehicle (build/models/deepseek-v4.1-flash-reduced-v2)
    decoded by the golden itself -- q, the KV rows (their codes captured by wrapping the golden's own qdq_fp8 /
    qdq_fp4_e4m3), and the probabilities the golden feeds its p.v product.

Expected values are the golden's own functions (hdc_golden_v41.dots, .mul, .csum); where the golden's value is
not finite the engine must raise its fault instead.

Benches (Verilator):
  * tile   -- ot_hdc_v41x_attn_tile (the routed unit): random loads/issues, both load modes, bank rotation.
  * engine -- ot_hdc_v41x_attn: the staging buffer, q.k and p.v jobs back to back, at the reduced shape
    (head_dim 32, T <= 144, vehicle + random) and at the shipped shape (16 heads x 512 dims, T = 640, random),
    asserting bit-exactness on every output, sustained MACs/cycle and the latency budget.

Writes results/rtl/hdc_v41x_attn_campaign.json.
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
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402

V.set_arith("chunk8")
F = np.float32
OUT = ROOT / "results/rtl/hdc_v41x_attn_campaign.json"
RTL_TILE = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv"
RTL_ENG = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn.sv"
LIB = [ROOT / "rtl/hdc/ot_hdc_fastfp.sv"]
TB_TILE = ROOT / "rtl/test/tb_hdc_v41x_attn_tile.sv"
TB_ENG = ROOT / "rtl/test/tb_hdc_v41x_attn.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_harness.cpp"
VERILATOR5 = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / \
    "verilator-5.050/bin/verilator"
VERILATOR = str(VERILATOR5) if VERILATOR5.is_file() else "verilator"

CLOCK_HZ = 1.034e9
SPEC = {"macs_per_cycle": 34176, "kv_read_bytes_per_cycle": 2202.75, "buffer_rows": 640, "row_bytes": 528,
        "first_score_latency_cycles": 50, "last_pv_latency_cycles": 70,
        "source": "results/arch/arch_budget_v41.json required_spec att_macs / kv_bytes; docs/ARCH_SPEC_V41.md 6.4"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def u32(x):
    return V.bits(np.asarray(x, dtype=F)).astype(np.int64)


def bf16_bits(x):
    b = u32(x)
    assert np.all((b & 0xFFFF) == 0), "not a BF16 value"
    return b >> 16


def from_bf16(b):
    return V.from_bits((np.asarray(b, dtype=np.int64) << 16).astype(np.uint32))


# -- KV element storage format ------------------------------------------------------------
E2M1_SIGNED = np.concatenate([V.E2M1_VALUES, -V.E2M1_VALUES])


def deq_value(fmt, code, scale):
    """The golden's stored KV value of one element: qdq_fp8 (E4M3 code x 2^(UE8M0 - 127), to_bf16) or qdq_fp4_e4m3
    (E2M1 code x E4M3 scale, to_bf16).  Arrays in, float32 out (NaN/inf where the code or scale is not finite)."""
    fmt, code, scale = (np.asarray(a, dtype=np.int64) for a in (fmt, code, scale))
    with np.errstate(over="ignore", invalid="ignore"):
        e = np.where(scale == 255, np.nan, np.exp2(scale.astype(np.float64) - 127))
        v8 = V.E4M3[code & 255] * e
        v4 = E2M1_SIGNED[code & 15] * V.E4M3[scale & 255]
        v = np.where(fmt == 0, v8, v4).astype(F)
    return V.to_bf16(v)


def deq_in_domain(fmt, code, scale):
    """True where the engine's dequantiser is exact: the stored value is 0 or a binary32 NORMAL (the quantisers
    only produce those: FP8 scales >= 2^-22 by act_quant's amax floor), or not finite (then both fault)."""
    v = deq_value(fmt, code, scale).astype(np.float64)
    return (v == 0) | (np.abs(v) >= 2.0 ** -126) | ~np.isfinite(v)


def elem_word(pad, fmt, code, scale):
    return (int(pad) << 17) | (int(fmt) << 16) | ((int(code) & 255) << 8) | (int(scale) & 255)


# -- golden products ------------------------------------------------------------------------
def golden_dot(a, b):
    """dots(a, b) of the golden (chunk8): out[i, j] = csum_k mul(a[i, k], b[j, k])."""
    with np.errstate(over="ignore", invalid="ignore"):
        return V.dots(np.asarray(a, dtype=F), np.asarray(b, dtype=F))


# -- random operand distributions ------------------------------------------------------------
def rand_bf16(rng, shape, kind="wide"):
    n = int(np.prod(shape))
    s = rng.integers(0, 2, n)
    m = rng.integers(0, 128, n)
    if kind == "wide":
        e = rng.integers(1, 255, n)
        r = rng.random(n)
        e = np.where(r < 0.5, rng.integers(110, 145, n), e)          # most near 1
        e = np.where(r > 0.93, 0, e)                                   # subnormal
        m = np.where((r > 0.97), 0, m)                                 # zero
        e = np.where((r > 0.90) & (r <= 0.93), rng.integers(1, 20, n), e)   # tiny normals
    elif kind == "coarse":                                             # few bits, close exponents: ties
        e = rng.integers(124, 131, n)
        m = rng.integers(0, 4, n) << 5
    elif kind == "prob":                                               # softmax probabilities in (0, 1]
        e = np.where(rng.random(n) < 0.8, rng.integers(110, 127, n), rng.integers(0, 110, n))
        s = np.zeros(n, dtype=np.int64)
        m = np.where(rng.random(n) < 0.03, 0, m)
    else:
        raise ValueError(kind)
    return ((s << 15) | (e << 7) | m).reshape(shape)


def rand_kv_elems(rng, shape, fmt=None, kind="wide"):
    """Random stored KV elements (fmt, code, scale) inside the dequantiser's domain."""
    n = int(np.prod(shape))
    f = rng.integers(0, 2, n) if fmt is None else np.full(n, fmt)
    code = rng.integers(0, 256, n)
    code = np.where((code & 0x7F) == 0x7F, code ^ 1, code)             # E4M3 NaN codes: separate test
    if kind == "wide":
        u = np.where(rng.random(n) < 0.7, rng.integers(110, 140, n), rng.integers(16, 240, n))
    else:
        u = rng.integers(122, 130, n)
    s4 = rng.integers(0, 0x7F, n)                                      # positive E4M3 scale, never NaN
    s4 = np.where(rng.random(n) < 0.05, s4 | 0x80, s4)                 # a few negative scales
    code = np.where(f == 1, code & 15, code)
    scale = np.where(f == 1, s4, u)
    ok = deq_in_domain(f, code, scale)
    assert np.all(ok)
    return f.reshape(shape), code.reshape(shape), scale.reshape(shape)


# -- tile bench -------------------------------------------------------------------------------
def tile_vectors(rng, H, TD, nbeats, nbank=3):
    """Random load/issue program for one tile and its expected outputs.  Returns (stim words, exp words)."""
    R = TD // H
    A = np.zeros((nbank, H, TD), dtype=np.int64)                      # BF16 bits
    stim, exp = [], []
    # initial loads of all banks (mix of both modes)
    prog = []
    for b in range(nbank):
        prog.append(("load", b, int(rng.integers(0, 2))))
    kinds = ["wide", "coarse", "prob"]
    for i in range(nbeats):
        if rng.random() < 0.25:
            prog.append(("load", int(rng.integers(0, nbank)), int(rng.integers(0, 2))))
        prog.append(("issue", int(rng.integers(0, nbank)), kinds[i % 3]))
    busy_until = [-1] * nbank          # last cycle a bank is read (issue cycle + max skew)
    cyc = 0
    for op in prog:
        if op[0] == "load":
            _, b, mode = op
            kind = kinds[int(rng.integers(0, 3))]
            words = rand_bf16(rng, (H, TD), kind)
            if rng.random() < 0.1:                                     # a nonfinite A element -> faults
                words[int(rng.integers(0, H)), int(rng.integers(0, TD))] = 0x7F80 | int(rng.integers(0, 2)) << 15
            for g in range(H):
                while cyc <= busy_until[b] + 1:               # keep the write-after-read distance
                    stim.append(0)
                    cyc += 1
                w = words[g]
                if mode == 0:
                    A[b, g, :] = w
                else:
                    for j in range(R):
                        for h in range(H):
                            A[b, h, R * g + j] = w[j * H + h]
                word = 0
                for k in range(TD):
                    word |= int(w[k]) << (16 * k)
                word |= (g << (TD * 16)) | (b << (TD * 16 + 8)) | (mode << (TD * 16 + 10)) | (1 << (TD * 16 + 11))
                stim.append(word)
                cyc += 1
        else:
            _, b, kind = op
            f, c, s = rand_kv_elems(rng, (TD,), None, "wide" if kind != "coarse" else "coarse")
            pad = (rng.random(TD) < 0.05).astype(np.int64)
            if rng.random() < 0.05:                                    # a nonfinite element -> fault
                k = int(rng.integers(0, TD))
                f[k], c[k], s[k], pad[k] = 0, 0x7F, 127, 0
            bv = deq_value(f, c, s)
            bv = np.where(pad == 1, F(0), bv).astype(F)
            av = from_bf16(A[b])
            # expected: products with pad forced to +0 (the golden pads with +0 terms)
            with np.errstate(over="ignore", invalid="ignore"):
                prod = V.mul(av, bv[None, :])
            prod = np.where(pad[None, :] == 1, F(0), prod).astype(F)
            with np.errstate(over="ignore", invalid="ignore"):
                y = V.csum(prod)
            ew = 0
            for h in range(H):
                fin = bool(np.isfinite(y[h]))
                ew |= ((0 if fin else 1) << 32 | (int(u32(y[h])) if fin else 0)) << (33 * h)
            exp.append(ew)
            ib = 0
            for k in range(TD):
                ib |= elem_word(pad[k], f[k], c[k], s[k]) << (18 * k)
            word = ib << (TD * 16 + 12)
            word |= (b << (TD * 16 + 12 + TD * 18)) | (1 << (TD * 16 + 14 + TD * 18))
            stim.append(word)
            busy_until[b] = cyc + 18
            cyc += 1
    return stim, exp


def write_hex(path: Path, words, width_bits):
    nd = -(-width_bits // 4)
    path.write_text("".join(f"{w:0{nd}x}\n" for w in words))


def verilator_build(tb: Path, top: str, srcs, obj: Path, params: dict, jobs: int = 8):
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-j", str(jobs), "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "--top-module", top, "--prefix", "Vtb", "-Mdir", str(obj),
           *[f"-G{k}={v}" for k, v in params.items()], *map(str, srcs), str(tb), str(HARNESS),
           "-CFLAGS", "-O1", "--x-assign", "fast", "--x-initial", "fast"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"[verilator] {top} {params} built in {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-4000:])
    return obj / "Vtb"


TILE_RE = re.compile(r"V41XTILE beats=(\d+) checked=(\d+) errors=(\d+) faults=(\d+) first_ov=(-?\d+) last_ov=(-?\d+)")


def run_tile(scratch: Path, H=16, TD=64, nbeats=200, seed=1):
    rng = np.random.default_rng(seed)
    stim, exp = tile_vectors(rng, H, TD, nbeats)
    win = 1 + 2 + TD * 18 + 1 + 1 + 2 + 8 + TD * 16
    d = scratch / f"tile_h{H}_td{TD}_s{seed}"
    d.mkdir(parents=True, exist_ok=True)
    write_hex(d / "in.hex", stim, win)
    write_hex(d / "exp.hex", exp, 33 * H)
    exe = verilator_build(TB_TILE, "tb_hdc_v41x_attn_tile", [RTL_TILE, *LIB], d / "obj",
                          {"H": H, "TD": TD, "NCYC": len(stim), "NOUT": len(exp)})
    out = subprocess.run([str(exe), f"+in={d / 'in.hex'}", f"+exp={d / 'exp.hex'}"], capture_output=True,
                         text=True, check=True).stdout
    m = TILE_RE.search(out)
    assert m, out
    beats, checked, errors, faults, fo, lo = map(int, m.groups())
    return {"H": H, "TD": TD, "seed": seed, "beats": beats, "expected_beats": len(exp), "checked": checked,
            "errors": errors, "faults_expected_and_raised": faults, "status": "pass" if errors == 0 and
            beats == len(exp) else "fail", "log_tail": out.strip().splitlines()[-12:]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["tile", "engine", "all"], default="all")
    ap.add_argument("--scratch", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        s = args.scratch or Path(td)
        if args.only in ("tile", "all"):
            print(json.dumps(run_tile(s, 16, 64, 120, 1), indent=1))


if __name__ == "__main__":
    main()
