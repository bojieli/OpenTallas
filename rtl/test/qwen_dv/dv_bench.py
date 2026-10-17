#!/usr/bin/env python3
"""Q-DV slice benches (rtl/qwen_dv/qfd_dv_slice.sv) bit-exact against the Qwen ROM die golden (tools/hdc_golden.py:
add / mul / rsqrt / reciprocal / exp / reduce_chunked (R-ARITH csum8) / rmsnorm / rope / silu / to_bf16 / to_fp8 /
matvec split order).  Each bench writes an event file for tb_qfd_dv.sv, runs Icarus, and compares the logged port
words with the golden.

    python3 rtl/test/qwen_dv/dv_bench.py [a|b|c|d|e ...] [--mut N] [--work DIR]

Exit status 0 iff every requested bench PASSES (with --mut, the expectation is reversed by the caller: run_all.sh).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402

F = np.float32
EPS = F(1e-6)

SRCS = """rtl/qwen_dv/qfd_dv_slice.sv rtl/qwen_dv/qfd_dv_redstn.sv rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_scalar.sv
rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_sys/static_schedule_20261014/ot_hdc_vstream_static_entries.sv
rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv
rtl/hdc/ot_hdc_sfu_q.sv rtl/physical/ot_hdc_vred_pending_guard.sv rtl/test/full_sm_service/sram_models.sv
rtl/test/hbm_rf_visibility/scale_sram_model.sv rtl/test/qwen_dv/tb_qfd_dv.sv""".split()


def u32(x):
    return int(np.asarray(x, dtype=F).view(np.uint32))


def fbits(x):
    return np.asarray(x, dtype=F).view(np.uint32).astype(np.uint64)


def pack(fields):
    """fields: list of (value, width) LSB first."""
    v, s = 0, 0
    for val, w in fields:
        v |= (int(val) & ((1 << w) - 1)) << s
        s += w
    return v


# ------------------------------------------------------------------------------------------------- encodings
MA_BYP, MA_AB, MA_AA, MA_AIMM = range(4)
MB_OFF, MB_POS, MB_NEG = range(3)
AD_BYP, AD_Q, AD_C, AD_NEGB, AD_IMM = range(5)
SFU_NONE, SFU_EXP, SFU_RECIP, SFU_RSQRT, SFU_SIGM = range(5)
DST_NONE, DST_VM, DST_KV = range(3)
W_VM, W_X, W_D2D, W_SC = 0, 1 << 22, 2 << 22, 3 << 22


def su(nout=1, nin=1, asrc=0, a=0, aso=0, asi=0, bsrc=0, b=0, bso=0, bsi=0, csrc=0, c=0, cso=0, csi=0,
       ma=0, mb=0, ad=0, sfu=0, mc=0, md=0, dst=0, d=0, dso=0, dsi=0, red=0, redsq=0, rb=0, rso=0, imm1=0.0, imm2=0.0):
    """The qfd_seq_su SU issue word, bits [456:0] (go bit 0 is set by the slice)."""
    return pack([(0, 1), (nout, 18), (nin, 18), (asrc, 1), (a, 24), (aso, 24), (asi, 24), (bsrc, 1), (b, 24),
                 (bso, 24), (bsi, 24), (csrc, 1), (c, 24), (cso, 24), (csi, 24), (ma, 2), (mb, 2), (ad, 3), (sfu, 3),
                 (mc, 1), (md, 1), (dst, 2), (d, 24), (dso, 24), (dsi, 24), (red, 2), (redsq, 1), (rb, 24), (rso, 24),
                 (u32(F(imm1)), 32), (u32(F(imm2)), 32)])


def cmd_su(pidx):
    return pack([(1, 1), (1, 3), (pidx, 9)])


def cmd_stn(mode, wsrc, nwords, sbase, dst, dbase):
    return pack([(1, 1), (2, 3), (mode, 2), (wsrc, 1), (nwords, 8), (sbase, 9), (dst, 2), (dbase, 24)])


def cmd_root(root, nb, ss):
    return pack([(1, 1), (3, 3), (root, 1), (nb, 6), (ss, 24)])


def cmd_ports(ar_base, dd_base):
    return pack([(1, 1), (4, 3), (ar_base, 24), (dd_base, 24)])


def cmd_stream(dirs, tag):
    return pack([(1, 1), (5, 3), (dirs, 2), (tag, 28)])


def stream_word(kind, dst, eaddr, payload, src=0xE, tag=0):
    ctl = pack([(tag, 28), (eaddr, 24), (src, 4), (dst, 4), (kind, 3), (1, 1)])
    return (ctl << 1024) | payload


def word16(vals):
    return sum(u32(v) << (32 * i) for i, v in enumerate(vals))


def cluster_word(vals):
    return (1 << 512) | word16(vals)


def ar_word(vals, last=0):
    return (1 << 517) | (last << 512) | word16(vals)


class Ev:
    def __init__(self):
        self.ev = []
        self.t = 16          # the slice's reset synchroniser releases 2 edges after rst_n

    def at(self, port, val, t=None):
        self.ev.append((self.t if t is None else t, port, val))

    def step(self, n=1):
        self.t += n

    def write(self, path):
        with open(path, "w") as f:
            for t, p, v in sorted(self.ev, key=lambda e: (e[0], e[1])):
                f.write(f"{t} {p} {v:x}\n")


P_CMD, P_CW0, P_CW1, P_AR, P_DD, P_SWI = 0, 2, 4, 6, 8, 10


def load_prog(ev, sl, progs):
    """SU programs -> slice `sl` program store via stream PROG words (2 instructions per word)."""
    progs = list(progs) + ([0] if len(progs) % 2 else [])
    for i in range(0, len(progs), 2):
        ev.at(P_SWI, stream_word(3, sl, i // 2, progs[i] | (progs[i + 1] << 512)))
        ev.step()


def load_crom(ev, sl, base, lo, hi=None):
    """(lo, hi) pairs at CROM entries base.. (base 16-aligned)."""
    n = len(lo)
    hi = np.zeros(n, dtype=F) if hi is None else hi
    assert base % 16 == 0
    for w in range(0, n, 16):
        pay = 0
        for j in range(min(16, n - w)):
            pay |= (u32(lo[w + j]) | (u32(hi[w + j]) << 32)) << (64 * j)
        ev.at(P_SWI, stream_word(1, sl, (base + w) // 16, pay))
        ev.step()


def load_btab(ev, sl, word0, bf16_vals):
    assert word0 % 4 == 0
    v = np.asarray(bf16_vals, dtype=F)
    hw = (v.view(np.uint32) >> 16).astype(np.uint64)
    for w in range(0, len(hw), 64):
        pay = sum(int(h) << (16 * j) for j, h in enumerate(hw[w:w + 64]))
        ev.at(P_SWI, stream_word(2, sl, word0 + w // 16, pay))
        ev.step()


def load_vm(ev, sl, base, vals):
    """FP32 vector into slice VM at `base` over the AR-return port (16 per word)."""
    ev.at(P_CMD + sl, cmd_ports(base, 0))
    ev.step(2)
    for w in range(0, len(vals), 16):
        ev.at(P_AR + sl, ar_word(vals[w:w + 16]))
        ev.step()
    ev.step(4)


def run_sim(name, ev, work, mut, ncyc):
    work.mkdir(parents=True, exist_ok=True)
    evf, lgf = work / f"{name}.ev", work / f"{name}.log"
    exe = work / "obj" / "Vtb_qfd_dv"
    ev.write(evf)
    if not exe.exists():
        cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-j", "16", "-Wno-fatal", "-Wno-lint", "-Wno-style",
               "-Wno-TIMESCALEMOD", "--x-assign", "0", "--x-initial", "0", "--top-module", "tb_qfd_dv",
               f"-GMUT={mut}", "-Mdir", str(work / "obj"), str(HERE / "main.cpp")] + [str(ROOT / s) for s in SRCS]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([str(exe), f"+EV={evf}", f"+LOG={lgf}", f"+NCYC={ncyc}"], check=True, stdout=subprocess.DEVNULL)
    out = {}
    for line in lgf.read_text().split("\n"):
        if line.strip():
            c, n, h = line.split()
            out.setdefault(n, []).append((int(c), int(h.replace('x', '0').replace('X', '0').replace('z', '0'), 16)))
    return out


def status_ok(log):
    bad = []
    for s in ("S0ST", "S1ST"):
        v = log[s][0][1]
        if v >> 44:
            bad.append(f"{s} fault bits {v >> 38:07b} (any,su,vm,stn,sc,stm,port)")
    return bad


def f32_of(v):
    return np.array([v & 0xFFFFFFFF], dtype=np.uint32).view(F)[0]


def dd_values(log, name, kind=None):
    """D2D out words -> {element address: FP32 bits} for the given kind."""
    res = {}
    for _, w in log.get(name, []):
        k = (w >> 545) & 3
        if kind is not None and k != kind:
            continue
        mask = (w >> 537) & 0xFF
        for l in range(8):
            if mask >> l & 1:
                a = (w >> (89 + 256 + 24 * l)) & 0xFFFFFF
                res[a] = (w >> (89 + 32 * l)) & 0xFFFFFFFF
    return res


def cmp(tag, got, exp_bits, errs):
    n = len(exp_bits)
    bad = [i for i in range(n) if got.get(i) != int(exp_bits[i])]
    if bad:
        i = bad[0]
        g = got.get(i)
        errs.append(f"{tag}: {len(bad)}/{n} mismatches, first [{i}] got {g if g is None else hex(g)} "
                    f"exp {hex(int(exp_bits[i]))}")
    return n - len(bad)


def gap(nvec, depth=160):
    return nvec + depth


# ================================================================================================= bench (a)
def bench_a(work, mut, trials=3, seed=1):
    """2 slices: block sums of x^2 (csum8 subtrees, 16 blocks each), PSUMs over the scalar ring to the root,
    pairwise top levels, *1/4096 + eps, rsqrt on the root's SU, r broadcast back (RB), r read back on both slices."""
    rng = np.random.default_rng(seed)
    ev = Ev()
    X, SSX, RX = 0x0000, 0x3000, 0x3008
    progs = {}
    for sl in (0, 1):
        progs[sl] = [
            su(nout=16, nin=128, a=X, aso=128, asi=1, red=1, redsq=1, rb=W_SC | (16 * sl), rso=1),          # 0
            su(nout=1, nin=1, a=SSX, ma=MA_AIMM, imm1=1.0 / 4096, ad=AD_IMM, imm2=EPS, sfu=SFU_RSQRT,
               dst=DST_VM, d=W_SC | RX),                                                                 # 1
            su(nout=1, nin=1, a=RX, dst=DST_VM, d=W_D2D | 0x10),                                         # 2 r -> D2D
        ]
        load_prog(ev, sl, progs[sl])
    exp = []
    for t in range(trials):
        x = (rng.standard_normal(4096) * rng.choice([0.05, 1.0, 30.0])).astype(F)
        x[rng.integers(0, 4096, 8)] *= F(50)
        r = G.rsqrt(G.add(G.mul(G.reduce_chunked(G.mul(x, x)), F(1.0 / 4096)), EPS))
        exp.append(u32(r))
        for sl in (0, 1):
            load_vm(ev, sl, X, x[2048 * sl:2048 * (sl + 1)])
        ev.at(P_CMD + 0, cmd_root(1, 32, SSX)); ev.at(P_CMD + 1, cmd_root(0, 32, SSX)); ev.step(2)
        ev.at(P_CMD + 0, cmd_su(0)); ev.at(P_CMD + 1, cmd_su(0)); ev.step(gap(256) + 200)
        ev.at(P_CMD + 0, cmd_su(1)); ev.step(gap(1, 120))
        for sl in (0, 1):
            ev.at(P_CMD + sl, cmd_su(2)); ev.step(gap(1, 60))
    log = run_sim("a", ev, work, mut, ev.t + 50)
    errs = status_ok(log)
    # RB words leaving the root (S0SC kind 2) and the r read back on each slice (D2D kind 0, element 0x10)
    rb = [w & 0xFFFFFFFF for _, w in log.get("S0SC", []) if (w >> 92) & 7 == 2]
    rds = {sl: [w >> 89 & 0xFFFFFFFF for _, w in log.get(f"S{sl}DD", [])] for sl in (0, 1)}
    ok = 0
    for t in range(trials):
        for tag, lst in (("RB", rb), ("S0 r", rds[0]), ("S1 r", rds[1])):
            if t < len(lst) and lst[t] == exp[t]:
                ok += 1
            else:
                errs.append(f"trial {t} {tag}: got {hex(lst[t]) if t < len(lst) else None} exp {hex(exp[t])}")
    return ok, 3 * trials, errs


# ================================================================================================= bench (b)
def bench_b(work, mut, seed=2):
    """1 slice owning all 32 blocks: residual add x + t (t over the AR-return port) with the sum of squares chased
    on the add, root combine, rsqrt, broadcast r, h = (x * r) * g at the consumer, BF16 RNE, 64 x-words on the stream;
    the updated residual read back through D2D."""
    rng = np.random.default_rng(seed)
    ev = Ev()
    X, T, SSX, RX, GAM = 0x0000, 0x1000, 0x3000, 0x3008, 0
    x = (rng.standard_normal(4096) * 0.7).astype(F)
    t = (rng.standard_normal(4096) * 0.3).astype(F)
    x[rng.integers(0, 4096, 6)] *= F(80)
    g = G.to_bf16((1.0 + 0.4 * rng.standard_normal(4096)).astype(F))
    progs = [
        su(nout=32, nin=128, a=X, aso=128, asi=1, c=T, cso=128, csi=1, ad=AD_C, dst=DST_VM, d=X, dso=128, dsi=1,
           red=1, redsq=1, rb=W_SC, rso=1),                                                              # 0
        su(nout=1, nin=1, a=SSX, ma=MA_AIMM, imm1=1.0 / 4096, ad=AD_IMM, imm2=EPS, sfu=SFU_RSQRT,
           dst=DST_VM, d=W_SC | RX),                                                                     # 1
        su(nout=1, nin=4096, a=X, asi=1, ma=MA_AB, b=RX, csrc=1, c=GAM, csi=1, mc=1, dst=DST_VM,
           d=W_X, dsi=1),                                                                                # 2
        su(nout=1, nin=4096, a=X, asi=1, dst=DST_VM, d=W_D2D, dsi=1),                                    # 3
    ]
    load_prog(ev, 0, progs)
    load_crom(ev, 0, GAM, g)
    load_vm(ev, 0, X, x)
    load_vm(ev, 0, T, t)
    ev.at(P_CMD, cmd_root(1, 32, SSX)); ev.at(P_CMD, cmd_stream(1, 0x5A5), t=ev.t + 1); ev.step(3)
    ev.at(P_CMD, cmd_su(0)); ev.step(gap(512) + 200)
    ev.at(P_CMD, cmd_su(1)); ev.step(gap(1, 120))
    ev.at(P_CMD, cmd_su(2)); ev.step(gap(512))
    ev.at(P_CMD, cmd_su(3)); ev.step(gap(512))
    log = run_sim("b", ev, work, mut, ev.t + 50)
    errs = status_ok(log)
    xn = G.add(x, t)
    h = G.to_bf16(G.rmsnorm(xn, g, EPS))
    hb = (fbits(h) >> 16).astype(np.int64)
    got = {}
    for _, w in log.get("S1E", []):
        e0 = (w >> 1052) & 0xFFFFFF
        for i in range(64):
            got[e0 + i] = (w >> (16 * i)) & 0xFFFF
    ok = cmp("h bf16 (stream)", got, hb, errs)
    ok += cmp("x + t (D2D)", dd_values(log, "S0DD", 0), fbits(xn), errs)
    return ok, 2 * 4096, errs


# ================================================================================================= bench (c)
def l6_parts(w, x, S):
    """Golden chunk sums (K cut into S contiguous chunks, each sequential from +0) grouped per cluster of 64
    chunks and reduced by the pairwise tree inside the cluster (levels 1..6): the cluster result words."""
    xb = G.to_bf16(x)
    kc = w.shape[1] // S
    parts = [G.matvec_fp32(w[:, c * kc:(c + 1) * kc], xb[c * kc:(c + 1) * kc]) for c in range(S)]
    out = []
    for cl in range(S // 64):
        p = parts[64 * cl:64 * (cl + 1)]
        while len(p) > 1:
            p = [G.add(p[i], p[i + 1]) for i in range(0, len(p), 2)]
        out.append(p[0])
    return out


def bench_c(work, mut, seed=3):
    rng = np.random.default_rng(seed)
    ev = Ev()
    kc = 2

    def mat(S):
        w = rng.integers(-127, 128, size=(128, S * kc)).astype(F)
        x = (rng.standard_normal(S * kc) * 2.0).astype(F)
        s = G.to_bf16((rng.random(128) * 0.02 + 1e-3).astype(F))
        return w, x, s

    tests = []
    SB = 0
    # L7 gate / up (S = 128), scaled -> AR
    wg, xg, sg = mat(128)
    wu, xu, su_ = mat(128)
    load_btab(ev, 0, SB, np.concatenate([sg, su_]))
    # L8 (S = 256) scaled -> AR + VM; L8 unscaled (wsrc); L9 (S = 512) across the pair
    w8, x8, s8 = mat(256)
    load_btab(ev, 0, 16, s8)
    w9, x9, s9 = mat(512)
    load_btab(ev, 0, 32, s9)
    ev.step(4)
    # --- L7
    lg, lu = l6_parts(wg, xg, 128), l6_parts(wu, xu, 128)
    ev.at(P_CMD, cmd_stn(0, 0, 16, SB, 2, 0x2000)); ev.step(3)
    for k in range(8):
        ev.at(P_CW0, cluster_word(lg[0][16 * k:16 * k + 16])); ev.at(P_CW1, cluster_word(lg[1][16 * k:16 * k + 16]))
        ev.step()
    for k in range(8):
        ev.at(P_CW0, cluster_word(lu[0][16 * k:16 * k + 16])); ev.at(P_CW1, cluster_word(lu[1][16 * k:16 * k + 16]))
        ev.step()
    ev.step(40)
    tests.append(("L7 gate/up", 0, 0x2000, np.concatenate([G.mul(G.matvec(wg, xg, 128), sg),
                                                          G.mul(G.matvec(wu, xu, 128), su_)])))
    # --- L8 scaled, then the same L8 unscaled
    l8 = l6_parts(w8, x8, 256)
    for wsrc, base in ((0, 0x2400), (1, 0x2800)):
        ev.at(P_CMD, cmd_stn(1, wsrc, 8, 16, 3, base)); ev.step(3)
        for half in (0, 1):
            for k in range(8):
                ev.at(P_CW0, cluster_word(l8[2 * half][16 * k:16 * k + 16]))
                ev.at(P_CW1, cluster_word(l8[2 * half + 1][16 * k:16 * k + 16]))
                ev.step()
        ev.step(50)
        y = G.matvec(w8, x8, 256)
        tests.append((f"L8 {'unscaled' if wsrc else 'scaled'}", 0, base, G.mul(y, F(1.0)) if wsrc else G.mul(y, s8)))
    # --- L9: slice 0 = even column group (clusters 0..3), slice 1 = odd (clusters 4..7)
    l9 = l6_parts(w9, x9, 512)
    ev.at(P_CMD + 0, cmd_stn(2, 0, 8, 32, 2, 0x2C00)); ev.at(P_CMD + 1, cmd_stn(3, 0, 8, 0, 0, 0)); ev.step(3)
    for half in (0, 1):
        for k in range(8):
            for sl in (0, 1):
                ev.at(P_CW0 + sl, cluster_word(l9[4 * sl + 2 * half][16 * k:16 * k + 16]))
                ev.at(P_CW1 + sl, cluster_word(l9[4 * sl + 2 * half + 1][16 * k:16 * k + 16]))
            ev.step()
    ev.step(60)
    tests.append(("L9 pair", 0, 0x2C00, G.mul(G.matvec(w9, x9, 512), s9)))
    log = run_sim("c", ev, work, mut, ev.t + 20)
    errs = status_ok(log)
    got = {}
    for _, w in log.get("S0AR", []):
        tag = (w >> 513) & 0xFFFFFFFF
        for l in range(16):
            got[tag + l] = (w >> (32 * l)) & 0xFFFFFFFF
    ok = n = 0
    for name, _, base, y in tests:
        g = {i: got.get(base + i) for i in range(len(y))}
        ok += cmp(name, g, fbits(y), errs)
        n += len(y)
    if any((w >> 545) & 1 for _, w in log.get("S1AR", [])):
        errs.append("L9 sender produced a local AR word")
    return ok, n, errs


# ================================================================================================= bench (d)
def bench_d(work, mut, seed=4, pos=1234):
    rng = np.random.default_rng(seed)
    ev = Ev()
    QKV, SS, RS, QN, ROPE = 0x0000, 0x3000, 0x3010, 0x0400, 256
    q = (rng.standard_normal(128) * 2.0).astype(F)
    k = (rng.standard_normal(128) * 3.0).astype(F)
    qn = G.to_bf16((1.0 + 0.3 * rng.standard_normal(128)).astype(F))
    kn = G.to_bf16((1.0 + 0.3 * rng.standard_normal(128)).astype(F))
    cos, sin, half = G.rope_tables(pos, 128, 1000000.0)
    progs = [
        su(nout=2, nin=128, a=QKV, aso=128, asi=1, ma=MA_AA, red=1, rb=SS, rso=1),                       # 0
        su(nout=1, nin=2, a=SS, asi=1, ma=MA_AIMM, imm1=1.0 / 128, ad=AD_IMM, imm2=EPS, sfu=SFU_RSQRT,
           dst=DST_VM, d=RS, dsi=1),                                                                     # 1
        su(nout=2, nin=128, a=QKV, aso=128, asi=1, ma=MA_AB, b=RS, bso=1, csrc=1, c=0, cso=128, csi=1, mc=1,
           dst=DST_VM, d=QN, dso=128, dsi=1),                                                            # 2
    ]
    for kk, (ab, cb, dst, d) in enumerate([(QN, QN + 64, DST_VM, W_D2D), (QN + 128, QN + 192, DST_KV, 1 << 22)]):
        progs.append(su(nin=64, a=ab, asi=1, bsrc=1, b=ROPE, bsi=1, ma=MA_AB, c=cb, csi=1, mb=MB_NEG, ad=AD_Q,
                        dst=dst, d=d, dsi=1))
        progs.append(su(nin=64, a=cb, asi=1, bsrc=1, b=ROPE, bsi=1, ma=MA_AB, c=ab, csi=1, mb=MB_POS, ad=AD_Q,
                        dst=dst, d=d + 64, dsi=1))
    load_prog(ev, 0, progs)
    load_crom(ev, 0, 0, np.concatenate([qn, kn]))
    load_crom(ev, 0, ROPE, cos, sin)
    load_vm(ev, 0, QKV, np.concatenate([q, k]))
    for p, gp in ((0, 300), (1, 200), (2, 200), (3, 200), (4, 200), (5, 200), (6, 200)):
        ev.at(P_CMD, cmd_su(p)); ev.step(gp)
    log = run_sim("d", ev, work, mut, ev.t + 20)
    errs = status_ok(log)
    qr = G.rope(G.rmsnorm(q, qn, EPS), cos, sin, half)
    kr = G.to_fp8(G.rope(G.rmsnorm(k, kn, EPS), cos, sin, half))
    ok = cmp("q norm+rope", dd_values(log, "S0DD", 0), fbits(qr), errs)
    ok += cmp("k norm+rope fp8", dd_values(log, "S0DD", 1), fbits(kr), errs)
    return ok, 256, errs


# ================================================================================================= bench (e)
def bench_e(work, mut, seed=5):
    rng = np.random.default_rng(seed)
    ev = Ev()
    n = 1024
    g = (rng.standard_normal(n) * 3.0).astype(F)
    g[:8] = F([-100.0, -88.5, -20.0, 0.0, 95.0, 1e-30, -1e-30, 40.0])
    u = (rng.standard_normal(n) * 2.0).astype(F)
    GB, UB = 0x0000, 0x1000
    progs = [su(nout=1, nin=n, a=GB, asi=1, ma=MA_AIMM, imm1=-1.0, sfu=SFU_SIGM, c=GB, csi=1, mc=1, b=UB, bsi=1,
                md=1, dst=DST_VM, d=W_D2D, dsi=1)]
    load_prog(ev, 0, progs)
    load_vm(ev, 0, GB, g)
    load_vm(ev, 0, UB, u)
    ev.at(P_CMD, cmd_su(0)); ev.step(gap(n // 8, 300))
    log = run_sim("e", ev, work, mut, ev.t + 20)
    errs = status_ok(log)
    exp = G.mul(G.silu(g), u)
    got = dd_values(log, "S0DD", 0)
    ok = cmp("silu*up", got, fbits(exp), errs)
    # informational: the HGI-1 / r25 form (IEEE divide) differs from the ROM die's Newton reciprocal
    with np.errstate(all="ignore"):
        ieee = G.mul(G.z(g / G.add(G.exp(G.mul(g, F(-1.0))), F(1.0))), u)
    diff = int(np.sum(fbits(ieee) != fbits(exp)))
    print(f"  (info) ROM-golden SiLU vs IEEE-divide SiLU: {diff}/{n} values differ")
    return ok, n, errs


BENCHES = {"a": bench_a, "b": bench_b, "c": bench_c, "d": bench_d, "e": bench_e}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("benches", nargs="*", default=list("abcde"))
    ap.add_argument("--mut", type=int, default=0)
    ap.add_argument("--work", default="/tmp/qdv_bench")
    a = ap.parse_args()
    work = Path(a.work)
    allpass = True
    for b in a.benches:
        ok, n, errs = BENCHES[b](work / f"m{a.mut}", a.mut)
        verdict = "PASS" if (ok == n and not errs) else "FAIL"
        allpass &= verdict == "PASS"
        print(f"bench ({b}) MUT={a.mut}: {verdict} {ok}/{n}")
        for e in errs[:6]:
            print("   ", e)
    sys.exit(0 if allpass else 1)


if __name__ == "__main__":
    main()
