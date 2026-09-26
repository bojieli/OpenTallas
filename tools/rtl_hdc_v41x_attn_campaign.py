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


# -- the engine's summation order, in numpy (checks the csum equivalence claim without RTL) ----------------
def _tree(parts):
    parts = list(parts)
    while len(parts) > 1:
        parts = [V.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


def _tile_sum(prod):
    """One tile beat: TD products -> TD/8 sequential chunks (from the first term) -> pairwise tree."""
    nc = prod.shape[-1] // 8
    cs = []
    for c in range(nc):
        acc = prod[..., 8 * c]
        for i in range(1, 8):
            acc = V.add(acc, prod[..., 8 * c + i])
        cs.append(acc)
    return _tree(cs)


def engine_order_model(q, kvm, p, TD):
    """Scores and pv in the ENGINE's order: q.k = tile sums over TD-dim slices + the lane tree; p.v = tile sums
    over TD-row blocks (rows past T are +0 terms) + the streaming binary-counter merge (level l adds its stored
    2^l-block sum when bit l of the block index is set; the last block flushes upward, adding +0 elsewhere)."""
    q, kvm, p = (np.asarray(a, dtype=F) for a in (q, kvm, p))
    H, D = q.shape
    T = kvm.shape[0]
    with np.errstate(over="ignore", invalid="ignore"):
        prod = V.mul(q[:, None, :], kvm[None, :, :])                     # [H, T, D]
        sc = _tree([_tile_sum(prod[..., s * TD:(s + 1) * TD]) for s in range(D // TD)])
        nb = -(-T // TD)
        pad = np.zeros((nb * TD - T, D), dtype=F)
        kp = np.concatenate([kvm, pad]) if len(pad) else kvm
        pp = np.concatenate([p, np.zeros((H, nb * TD - T), dtype=F)], axis=1)
        mlev = max(1, int(np.ceil(np.log2(max(nb, 1)))))
        stack = [None] * mlev
        out = None
        for b in range(nb):
            prod = V.mul(pp[:, None, b * TD:(b + 1) * TD], kp[None, b * TD:(b + 1) * TD, :].transpose(0, 2, 1))
            x = _tile_sum(prod)                                            # [H, D]
            final = b == nb - 1
            for lvl in range(mlev):
                if (b >> lvl) & 1:
                    x = V.add(stack[lvl], x)
                elif final:
                    x = V.add(F(0), x)
                else:
                    stack[lvl] = x
                    x = None
                    break
            if final:
                out = x
    return sc, out


def check_order_model(rng, trials=40):
    """engine_order_model == golden dots (chunk8), bitwise where the golden is finite, over random shapes and
    every T class (partial chunks, partial blocks, 1 .. 1024 rows)."""
    bad = 0
    cases = []
    for i in range(trials):
        TD = [8, 16, 32, 64][i % 4]
        D = TD * [1, 2, 4, 8][(i // 4) % 4]
        T = int(rng.integers(1, 1100)) if i % 3 else int(rng.choice([1, 7, 8, 9, 63, 64, 65, 640, 1023, 1024]))
        q = from_bf16(rand_bf16(rng, (2, D), "coarse" if i % 2 else "wide"))
        kv = from_bf16(rand_bf16(rng, (T, D), "coarse" if i % 2 else "wide"))
        p = from_bf16(rand_bf16(rng, (2, T), "prob"))
        sc, pv = engine_order_model(q, kv, p, TD)
        gs, gp = golden_dot(q, kv), golden_dot(p, kv.T)
        fin_s, fin_p = np.isfinite(gs), np.isfinite(gp)
        ok = (np.array_equal(u32(sc)[fin_s], u32(gs)[fin_s]) and np.array_equal(u32(pv)[fin_p], u32(gp)[fin_p]))
        bad += not ok
        cases.append({"TD": TD, "D": D, "T": T, "bit_exact": bool(ok)})
    return {"trials": trials, "mismatching_trials": bad, "cases": cases}


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


VL_EXTRA = os.environ.get("OT_ATTN_VL_EXTRA", "--output-split 20000 --output-split-cfuncs 2000 -fno-inline").split()
VL_CFLAGS = os.environ.get("OT_ATTN_VL_CFLAGS", "-O1")


def verilator_build(tb: Path, top: str, srcs, obj: Path, params: dict, jobs: int = 16):
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-j", str(jobs), "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "--top-module", top, "--prefix", "Vtb", "-Mdir", str(obj),
           *[f"-G{k}={v}" for k, v in params.items()], *map(str, srcs), str(tb), str(HARNESS),
           "-CFLAGS", VL_CFLAGS, "--x-assign", "fast", "--x-initial", "fast", *VL_EXTRA]
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



# -- engine jobs --------------------------------------------------------------------------------
class Job:
    """One layer's attention on one die: q [H, D] BF16, the KV rows in stored format, probabilities [H, T] BF16."""

    def __init__(self, q, fmt, codes, scales, p, source):
        self.q = np.asarray(q, dtype=F)                 # [H, D]
        self.fmt = np.asarray(fmt, dtype=np.int64)      # [T]
        self.codes = np.asarray(codes, dtype=np.int64)  # [T, D]
        self.scales = np.asarray(scales, dtype=np.int64)  # [T, D // 16]: FP8 rows repeat the per-32 scale
        self.p = np.asarray(p, dtype=F)                 # [H, T]
        self.source = source
        self.T = len(self.fmt)

    def kvm(self):
        """The golden's stored rows (dequantised), [T, D]."""
        f = np.repeat(self.fmt[:, None], self.codes.shape[1], axis=1)
        sc = np.repeat(self.scales, 16, axis=1)
        return deq_value(f, self.codes, sc)

    def expected(self):
        kvm = self.kvm()
        return golden_dot(self.q, kvm), golden_dot(self.p, kvm.T)   # [H, T], [H, D]


def row_word(fmt, codes, scales):
    """A staging-buffer row: D/32 group words of 265 bits {fmt, payload}."""
    D = len(codes)
    w = 0
    for g in range(D // 32):
        c = codes[g * 32:(g + 1) * 32]
        if fmt == 0:
            gw = sum(int(c[x]) << (8 * x) for x in range(32)) | (int(scales[2 * g]) << 256)
        else:
            gw = sum((int(c[x]) & 15) << (4 * x) for x in range(32)) | (int(scales[2 * g]) << 128) | \
                (int(scales[2 * g + 1]) << 136) | (1 << 264)
        w |= gw << (265 * g)
    return w


def random_job(rng, H, D, T, n_win, kind="wide"):
    fmt = np.array([0 if t < n_win else 1 for t in range(T)], dtype=np.int64)
    codes = np.zeros((T, D), dtype=np.int64)
    scales = np.zeros((T, D // 16), dtype=np.int64)
    for t in range(T):
        f, c, sc = rand_kv_elems(rng, (D // 16, 16), int(fmt[t]), kind)
        c = c.reshape(-1)
        if fmt[t] == 0:
            u = sc[0::2, 0]                                       # one UE8M0 per 32
            codes[t] = c
            scales[t] = np.repeat(u, 2)
        else:
            codes[t] = c & 15
            scales[t] = sc[:, 0]
    q = from_bf16(rand_bf16(rng, (H, D), "wide" if kind == "wide" else "coarse"))
    p = from_bf16(rand_bf16(rng, (H, T), "prob" if kind == "wide" else "coarse"))
    j = Job(q, fmt, codes, scales, p, f"random T={T} win={n_win} {kind}")
    assert np.all(deq_in_domain(np.repeat(fmt[:, None], D, 1), codes, np.repeat(scales, 16, 1)))
    return j


def write_jobs(d: Path, jobs, H, D, TD):
    R = TD // H
    d.mkdir(parents=True, exist_ok=True)
    jl, ql, kl, pl, sl, vl = [], [], [], [], [], []
    stats = {"scores": 0, "pv": 0, "score_faults": 0, "pv_faults": 0, "macs": 0}
    for j in jobs:
        sc, pv = j.expected()
        jl.append((len(vl) << 128) | (len(sl) << 96) | (len(pl) << 64) | (len(kl) << 32) | j.T)
        for h in range(H):
            ql.append(sum(int(b) << (16 * k) for k, b in enumerate(bf16_bits(j.q[h]))))
        for t in range(j.T):
            kl.append(row_word(int(j.fmt[t]), j.codes[t], j.scales[t]))
        pb = bf16_bits(j.p)
        for w in range(-(-j.T // R)):
            word = 0
            for jj in range(R):
                t = w * R + jj
                for h in range(H):
                    if t < j.T:
                        word |= int(pb[h, t]) << (16 * (jj * H + h))
            pl.append(word)
        for t in range(j.T):
            sl.append(pack_vals(sc[:, t]))
        for dd in range(D):
            vl.append(pack_vals(pv[:, dd]))
        stats["scores"] += sc.size
        stats["pv"] += pv.size
        stats["score_faults"] += int(np.sum(~np.isfinite(sc)))
        stats["pv_faults"] += int(np.sum(~np.isfinite(pv)))
        stats["macs"] += 2 * H * j.T * D
    write_hex(d / "jobs.hex", jl, 160)
    write_hex(d / "q.hex", ql, D * 16)
    write_hex(d / "kv.hex", kl, 265 * (D // 32))
    write_hex(d / "p.hex", pl, TD * 16)
    write_hex(d / "sc.hex", sl, 33 * H)
    write_hex(d / "pv.hex", vl, 33 * H)
    return {"NJOB": len(jobs), "NKV": len(kl), "NP": len(pl), "NSC": len(sl), "NPV": len(vl)}, stats


def pack_vals(v):
    w = 0
    for h, x in enumerate(np.asarray(v, dtype=F)):
        fin = bool(np.isfinite(x))
        w |= (((0 if fin else 1) << 32) | (int(u32(x)) if fin else 0)) << (33 * h)
    return w


JOB_RE = re.compile(r"V41XJOB job=(\d+) T=(\d+) qk_first=(-?\d+) qk_last=(-?\d+) qk_beats=(\d+) pv_first=(-?\d+) "
                    r"pv_last=(-?\d+) pv_beats=(\d+) last_score=(-?\d+) last_p=(-?\d+) last_pv=(-?\d+)")
ENG_RE = re.compile(r"V41XATTN jobs=(\d+) sc_checked=(\d+) sc_errors=(\d+) pv_checked=(\d+) pv_errors=(\d+) "
                    r"faults=(\d+) lat_score_max=(-?\d+) lat_score_min=(-?\d+) lat_pv_max=(-?\d+) cycles=(\d+) "
                    r"timeout=(\d+)")


def build_engine(scratch: Path, cfg: dict, counts: dict, extra: dict):
    cap = {("NJOBMAX" if k == "NJOB" else k): 1 << max(4, int(v - 1).bit_length()) for k, v in counts.items()}
    params = {"H": cfg["H"], "D": cfg["D"], "TD": cfg["TD"], "NL": cfg["NL"], "TROWS": cfg["TROWS"], **cap,
              **extra}
    tag = "_".join(f"{k}{v}" for k, v in sorted(params.items()))
    obj = scratch / ("obj_" + hashlib.sha1(tag.encode()).hexdigest()[:12])
    exe = obj / "Vtb"
    if not exe.is_file():
        verilator_build(TB_ENG, "tb_hdc_v41x_attn", [RTL_TILE, RTL_ENG, *LIB], obj, params, jobs=16)
    return exe


def run_engine(scratch: Path, name: str, cfg: dict, jobs, extra=None, seed=1):
    extra = dict(extra or {})
    d = scratch / name
    counts, stats = write_jobs(d, jobs, cfg["H"], cfg["D"], cfg["TD"])
    exe = build_engine(scratch, cfg, counts, extra)
    t0 = time.time()
    out = subprocess.run([str(exe), f"+dir={d}", f"+seed={seed}", f"+njob={counts['NJOB']}"], capture_output=True,
                         text=True, check=True).stdout
    sim_s = time.time() - t0
    m = ENG_RE.search(out)
    assert m, out[-3000:]
    njob, scc, sce, pvc, pve, flt, lsmax, lsmin, lpmax, cyc, tmo = map(int, m.groups())
    per = [dict(zip(("job", "T", "qk_first", "qk_last", "qk_beats", "pv_first", "pv_last", "pv_beats",
                     "last_score", "last_p", "last_pv"), map(int, g.groups()))) for g in JOB_RE.finditer(out)]
    H, D, TD, NL = cfg["H"], cfg["D"], cfg["TD"], cfg["NL"]
    NT = NL * (D // TD)
    macs_beat = NT * H * TD
    for pj in per:
        pj["qk_cycles"] = pj["qk_last"] - pj["qk_first"] + 1
        pj["pv_cycles"] = pj["pv_last"] - pj["pv_first"] + 1
        pj["qk_macs_per_cycle"] = H * pj["T"] * D / pj["qk_cycles"]
        pj["pv_macs_per_cycle"] = H * pj["T"] * D / pj["pv_cycles"]
        pj["qk_beat_bubbles"] = pj["qk_cycles"] - pj["qk_beats"]
        pj["pv_beat_bubbles"] = pj["pv_cycles"] - pj["pv_beats"]
        pj["last_pv_after_last_p"] = pj["last_pv"] - pj["last_p"]
    rec = {"name": name, "config": cfg, "extra": extra, "jobs": njob, "expected_jobs": len(jobs),
           "sources": sorted({j.source.split(" T=")[0] for j in jobs}),
           "T_values": sorted({j.T for j in jobs}),
           "scores_checked": scc, "score_errors": sce, "pv_checked": pvc, "pv_errors": pve,
           "faults_expected_and_raised": flt, "expected": stats,
           "latency": {"first_score_after_row_entry_max": lsmax, "first_score_after_row_entry_min": lsmin,
                       "last_pv_after_last_probability_max": lpmax},
           "cycles": cyc, "timeout": bool(tmo), "sim_seconds": round(sim_s, 1),
           "macs_per_issue_beat": macs_beat, "per_job": per,
           "log_tail": [x for x in out.strip().splitlines() if not x.startswith("V41XJOB")][-12:]}
    rec["bit_exact"] = (sce == 0 and pve == 0 and njob == len(jobs) and scc == stats["scores"] and
                        pvc == stats["pv"] and not tmo)
    return rec



# -- vehicle capture -------------------------------------------------------------------------------
_E4M3_CODE = {}
for _c in range(256):
    if (_c & 0x7F) != 0x7F:
        _E4M3_CODE.setdefault((float(abs(V.E4M3[_c])), _c >> 7), _c)


def e4m3_code(v):
    return _E4M3_CODE[(abs(float(v)), int(np.signbit(v)))]


def fp8_row_codes(x):
    """(codes, per-16 scale codes) of qdq_fp8(x): the golden's own quant_fp8, E4M3 codes + UE8M0 scale."""
    q, e = V.quant_fp8(x)
    codes = np.array([e4m3_code(v) for v in q], dtype=np.int64)
    return codes, np.repeat(np.asarray(e, dtype=np.int64) + 127, 2)


def fp4_row_codes(x, block=16):
    """(codes, per-16 E4M3 scale codes) of qdq_fp4_e4m3(x): the golden function's own lines."""
    x = np.asarray(x, dtype=F).reshape(-1, block)
    amax = np.maximum(np.max(np.abs(x), axis=1), V.FP4_AMAX_FLOOR_E4M3).astype(F)
    s = V._e4m3_round(amax.astype(np.float64) / V.FP4_MAX)
    a = np.abs(x.astype(np.float64))
    code = np.zeros(a.shape, dtype=np.int64)
    for i, m in enumerate(V.E2M1_MIDPOINTS):
        t = m * s[:, None]
        code = np.where((a > t) | ((a == t) & ((i + 1) % 2 == 0)), i + 1, code)
    code = code + 8 * np.signbit(x)
    sc = np.array([e4m3_code(v) for v in s], dtype=np.int64)       # KeyError: scale beyond E4M3
    return code.reshape(-1), sc


def capture_vehicle(n_positions, keep, log=print):
    """Decode the reduced vehicle greedily for n_positions and capture every attention call at the positions in
    `keep`: q, the rows' stored codes, and the probabilities the golden feeds its p.v product."""
    M = V.Model()
    rows8, rows4 = {}, {}
    o8, o4 = V.qdq_fp8, V.qdq_fp4_e4m3

    def w8(x, block=32):
        y = o8(x, block)
        rows8[y.tobytes()] = fp8_row_codes(x)
        return y

    def w4(x, block=16):
        y = o4(x, block)
        rows4[y.tobytes()] = fp4_row_codes(x, block)
        return y
    V.qdq_fp8, V.qdq_fp4_e4m3 = w8, w4
    calls = []
    cur = {"pos": -1}
    orig_attention, orig_attend = M.attention, M.attend

    def attention(L, x, pos, state, trace, ctx):
        cur["pos"], cur["L"] = pos, L
        return orig_attention(L, x, pos, state, trace, ctx)

    def attend(L, q, kvm, cs, blocks=None):
        if cur["pos"] in keep:
            calls.append((cur["pos"], L, np.array(q, dtype=F), np.array(kvm, dtype=F)))
        return orig_attend(L, q, kvm, cs, blocks)
    M.attention, M.attend = attention, attend
    try:
        prompt, _ = V.prompt_and_expected()
        st = M.new_state()
        toks = list(prompt)
        t0 = time.time()
        for pos in range(n_positions):
            lg = M.decode_token(toks[pos], pos, st)
            if pos + 1 >= len(toks):
                toks.append(int(np.argmax(lg)))
            if pos % 16 == 0:
                log(f"[vehicle] position {pos} ({time.time() - t0:.0f} s)")
    finally:
        V.qdq_fp8, V.qdq_fp4_e4m3 = o8, o4
    jobs = []
    unmatched = 0
    for pos, L, q, kvm in calls:
        T, D = kvm.shape
        fmt, codes, scales, ok = [], [], [], True
        for t in range(T):
            key = kvm[t].tobytes()
            if key in rows8:
                c, sc = rows8[key]
                fmt.append(0)
            elif key in rows4:
                c, sc = rows4[key]
                fmt.append(1)
            else:
                ok = False
                break
            codes.append(c)
            scales.append(sc)
        if not ok:
            unmatched += 1
            continue
        # the probabilities exactly as Model.attend forms them (one block: the two-pass softmax)
        s = V.mul(V.dots(q, kvm), M.attn_scale)
        mb = np.max(s, axis=1)
        e = V.exp(V.add(s, V.neg(mb)[:, None]))
        p = V.to_bf16(e)
        for g in range(q.shape[0] // 16):
            j = Job(q[16 * g:16 * (g + 1)], fmt, codes, scales, p[16 * g:16 * (g + 1)],
                    f"vehicle pos={pos} L={L} heads={16 * g}-{16 * g + 15} T={T}")
            assert np.array_equal(u32(j.kvm()), u32(kvm)), "stored codes do not dequantise to the golden's rows"
            jobs.append(j)
    return jobs, {"attention_calls": len(calls), "calls_without_captured_codes": unmatched,
                  "positions_decoded": n_positions, "positions_kept": sorted(keep), "jobs": len(jobs),
                  "tokens": toks[:n_positions]}


SHIPPED = dict(H=16, D=512, TD=64, NL=4, TROWS=640)      # one die: 16 heads, 4 row lanes x 8 slices = 32 tiles
REDUCED = dict(H=16, D=32, TD=32, NL=4, TROWS=160)       # the vehicle's head_dim, T <= 144
PHYS = ROOT / "results/physical_abi3/asap7/hdc/v41x/ot_hdc_v41x_attn_tile/physical.json"


def reduced_jobs(rng, vehicle_jobs):
    rj = [random_job(rng, 16, 32, T, min(T, 128), "wide" if i % 2 == 0 else "coarse")
          for i, T in enumerate((144, 1, 7, 8, 9, 31, 32, 33, 64, 65, 127, 128, 129, 143, 144, 100))]
    return rj + list(vehicle_jobs)


def shipped_jobs(rng):
    return [random_job(rng, 16, 512, 640, 128, "wide"), random_job(rng, 16, 512, 640, 128, "coarse"),
            random_job(rng, 16, 512, 300, 128, "wide")]


def perf_summary(rec, cfg):
    H, D, TD, NL = cfg["H"], cfg["D"], cfg["TD"], cfg["NL"]
    full = [j for j in rec["per_job"] if j["T"] == cfg["TROWS"]]
    out = {"tiles": NL * (D // TD), "tile_macs": H * TD, "issue_macs_per_cycle": NL * (D // TD) * H * TD,
           "full_jobs": len(full)}
    if full:
        macs = sum(H * j["T"] * D for j in full)
        out.update({"qk_macs_per_cycle_sustained": macs / sum(j["qk_cycles"] for j in full),
                    "pv_macs_per_cycle_sustained": macs / sum(j["pv_cycles"] for j in full),
                    "qk_bubbles": sum(j["qk_beat_bubbles"] for j in full),
                    "pv_bubbles": sum(j["pv_beat_bubbles"] for j in full),
                    "rows_per_cycle": NL, "kv_read_bytes_per_cycle": NL * D * 528 / 512,
                    "layer_cycles_engine_busy": [j["qk_cycles"] + j["pv_cycles"] for j in full]})
    return out


def physical_summary():
    if not PHYS.is_file():
        return None
    d = json.loads(PHYS.read_text())
    des = d.get("design", {})
    argv = d.get("runner", {}).get("argv", [])
    prm = [argv[i + 1] for i, a in enumerate(argv) if a == "--param"]
    return {"record": str(PHYS.relative_to(ROOT)), "params": prm, "fmax_hz": des.get("fmax_hz"),
            "closed": des.get("closed"), "area_um2": des.get("area_um2"), "setup_wns_ns": des.get("setup_wns_ns"),
            "target_clock_period_ns": d.get("target_clock_period_ns")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scratch", type=Path, required=True, help="build/vector directory (outside the worktree)")
    ap.add_argument("--vehicle-positions", type=int, default=131)
    ap.add_argument("--vehicle-cache", type=Path, default=None, help="pickle of capture_vehicle's result")
    ap.add_argument("--skip-shipped", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    s = args.scratch
    s.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = {"schema": "hdc_v41x_attn_campaign/1", "tool": "tools/rtl_hdc_v41x_attn_campaign.py",
           "arith": V.ARITH, "spec": SPEC, "verilator": VERILATOR,
           "sources": {str(p.relative_to(ROOT)): sha(p) for p in (RTL_TILE, RTL_ENG, *LIB, TB_TILE, TB_ENG,
                                                                  ROOT / "tools/hdc_golden_v41.py",
                                                                  ROOT / "tools/hdc_golden.py",
                                                                  Path(__file__).resolve())}}
    rec["order_model"] = check_order_model(np.random.default_rng(1), 40)
    rec["tile"] = [run_tile(s, 4, 16, 200, 1), run_tile(s, 16, 64, 80, 2)]
    if args.vehicle_cache and args.vehicle_cache.is_file():
        import pickle
        vj, info = pickle.loads(args.vehicle_cache.read_bytes())
    else:
        vj, info = capture_vehicle(args.vehicle_positions, {0, 7, 31, 63, 64, 100, 127, 128, 129, 130})
    red = run_engine(s, "reduced", REDUCED, reduced_jobs(np.random.default_rng(21), vj), extra={"MAXCYC": 4000000})
    red["vehicle"] = {k: v for k, v in info.items() if k != "tokens"}
    red["n_vehicle_jobs"] = len(vj)
    red["per_job"] = red["per_job"][:20]
    rec["reduced"] = red
    rec["reduced_bubbles"] = run_engine(s, "reduced_bub", REDUCED, reduced_jobs(np.random.default_rng(5), [])[:8],
                                        extra={"MAXCYC": 400000, "BUB": 30})
    if not args.skip_shipped:
        sh = run_engine(s, "shipped", SHIPPED, shipped_jobs(np.random.default_rng(33)), extra={"MAXCYC": 100000})
        sh["performance"] = perf_summary(sh, SHIPPED)
        rec["shipped"] = sh
    rec["physical"] = physical_summary()
    fails = []
    if rec["order_model"]["mismatching_trials"]:
        fails.append(f"order model: {rec['order_model']['mismatching_trials']} trials")
    fails += [f"tile H={t['H']}" for t in rec["tile"] if t["status"] != "pass"]
    for k in ("reduced", "reduced_bubbles", "shipped"):
        if k in rec and not rec[k]["bit_exact"]:
            fails.append(f"{k}: not bit exact")
    if "shipped" in rec:
        pf, lat = rec["shipped"]["performance"], rec["shipped"]["latency"]
        if pf.get("qk_bubbles") or pf.get("pv_bubbles"):
            fails.append("shipped: issue bubbles on full-window layers")
        if lat["first_score_after_row_entry_max"] > SPEC["first_score_latency_cycles"]:
            fails.append("shipped: first-score latency over budget")
        if lat["last_pv_after_last_probability_max"] > SPEC["last_pv_latency_cycles"]:
            fails.append("shipped: last-pv latency over budget")
        rec["spec_check"] = {
            "macs_per_cycle": {"spec": SPEC["macs_per_cycle"], "measured": pf.get("qk_macs_per_cycle_sustained"),
                               "met": (pf.get("qk_macs_per_cycle_sustained") or 0) >= SPEC["macs_per_cycle"]},
            "kv_read_bytes_per_cycle": {"spec": SPEC["kv_read_bytes_per_cycle"],
                                        "measured": pf.get("kv_read_bytes_per_cycle")},
            "first_score_latency": {"spec": SPEC["first_score_latency_cycles"],
                                    "measured": lat["first_score_after_row_entry_max"]},
            "last_pv_latency": {"spec": SPEC["last_pv_latency_cycles"],
                                "measured": lat["last_pv_after_last_probability_max"]}}
    rec["failures"] = fails
    rec["status"] = "pass" if not fails else "fail"
    rec["elapsed_s"] = round(time.time() - t0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps({"status": rec["status"], "failures": fails}, indent=1))


if __name__ == "__main__":
    main()
