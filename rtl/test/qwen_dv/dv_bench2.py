#!/usr/bin/env python3
"""Q-DV slice2 benches (rtl/qwen_dv/qfd_dv_slice2.sv, dv2r8f2 port cut) on tb_qfd_dv2.sv: the step-1/2 benches
(a .. g, same goldens and checks as dv_bench.py) carried over to the chain ports, plus (h) the SETID enumeration of a
12-slice chain.  Differences from dv_bench.py are only in how stimulus reaches a slice:
  commands   on s0.cmd_i with dst = slice, injected 2 edges earlier per hop (cmd chain: 2 edges a hop);
             a SETID (id 0) opens every run
  x loads    AR-return words on s0.ch_dn_i (they climb the return chain); PORTS ar_en arms only the target slice
  rs words   rs_s / rs_n per slice: both level-7 pairs in parallel (lower pair on rs_s, upper on rs_n)
  outputs    every AR / D2D word leaves at the W5 edge (s0.ch_dn_o); scalar words are 48 b (converted here)

    python3 rtl/test/qwen_dv/dv_bench2.py [a .. h] [--mut N] [--work DIR]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_bench as B  # noqa: E402

G, F, EPS = B.G, B.F, B.EPS
ROOT = B.ROOT
SRCS2 = [s for s in B.SRCS if not s.endswith(("qfd_dv_slice.sv", "qfd_dv_redstn.sv", "qfd_dv_scalar.sv",
                                                "tb_qfd_dv.sv"))] + \
    ["rtl/qwen_dv/qfd_dv_slice2.sv", "rtl/qwen_dv/qfd_dv_redstn2.sv", "rtl/qwen_dv/qfd_dv_scalar2.sv",
     "rtl/test/qwen_dv/tb_qfd_dv2.sv", "rtl/test/qwen_dv/safe_storage/sram_model.sv", "rtl/qwen_dv/mu/qfd_dv_amax_mu.sv", "rtl/qwen_dv/qfd_dv_slice2_faces.sv"]
NATIVE_SRAM = os.environ.get("DV2_NATIVE_SRAM", "0") == "1"
if NATIVE_SRAM:
    SRCS2 = [s.replace("rtl/test/qwen_dv/safe_storage/sram_model.sv", "physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v") for s in SRCS2]
    SRCS2.append("rtl/test/qwen_dv/safe_storage/native_collision_checker.sv")
SAFE_RESET = os.environ.get("DV2_SAFE_RESET", "0") == "1"
SAFE_AMAX_RESET = os.environ.get("DV2_SAFE_AMAX_RESET", "0") == "1"
if SAFE_AMAX_RESET and not SAFE_RESET:
    raise SystemExit("DV2_SAFE_AMAX_RESET requires DV2_SAFE_RESET")
SAFE_SCALAR_RESET = os.environ.get("DV2_SAFE_SCALAR_RESET", "0") == "1"
if SAFE_SCALAR_RESET and not SAFE_AMAX_RESET:
    raise SystemExit("DV2_SAFE_SCALAR_RESET requires DV2_SAFE_AMAX_RESET")
SAFE_STATION_CFG = os.environ.get("DV2_SAFE_STATION_CFG", "0") == "1"
if SAFE_STATION_CFG and not SAFE_RESET:
    raise SystemExit("DV2_SAFE_STATION_CFG requires DV2_SAFE_RESET")
SAFE_STATION_MATH = os.environ.get("DV2_SAFE_STATION_MATH", "0") == "1"
if SAFE_STATION_MATH and not SAFE_STATION_CFG:
    raise SystemExit("DV2_SAFE_STATION_MATH requires DV2_SAFE_STATION_CFG")
SAFE_STREAM_RESET = os.environ.get("DV2_SAFE_STREAM_RESET", "0") == "1"
if SAFE_STREAM_RESET and not SAFE_RESET:
    raise SystemExit("DV2_SAFE_STREAM_RESET requires DV2_SAFE_RESET")
SAFE_CFG = os.environ.get("DV2_SAFE_CFG", "0") == "1"
if SAFE_CFG and not SAFE_SCALAR_RESET:
    raise SystemExit("DV2_SAFE_CFG requires DV2_SAFE_SCALAR_RESET")
RESET_WARM = 16 if (SAFE_SCALAR_RESET or SAFE_STATION_MATH) else 8 if SAFE_RESET else 0  # deterministic boot guard, outside steady execution
if SAFE_RESET:
    SRCS2 = [s.replace("rtl/qwen_dv/qfd_dv_slice2.sv", "rtl/qwen_dv/qfd_dv_slice2_rsafe.sv").replace("rtl/qwen_dv/qfd_dv_redstn2.sv", "rtl/qwen_dv/qfd_dv_redstn2_rsafe.sv") for s in SRCS2]
    SRCS2.append("rtl/qwen_dv/qfd_dv_reset_tree.sv")
if SAFE_AMAX_RESET:
    SRCS2 = [s.replace("rtl/qwen_dv/mu/qfd_dv_amax_mu.sv", "rtl/qwen_dv/mu/qfd_dv_amax_mu_rsafe.sv") for s in SRCS2]
    SRCS2.append("rtl/qwen_dv/qfd_dv_reset_bank.sv")
if SAFE_SCALAR_RESET:
    SRCS2 = [s.replace("rtl/qwen_dv/qfd_dv_scalar2.sv", "rtl/qwen_dv/qfd_dv_scalar2_rsafe.sv") for s in SRCS2]
    SRCS2.extend(["rtl/qwen_dv/qfd_dv_ring_delay.sv", "rtl/common/landed_parent/ot_pl_land.sv"])
if SAFE_CFG:
    SRCS2 = [s.replace("qfd_dv_scalar2_rsafe.sv", "qfd_dv_scalar2_csafe.sv") for s in SRCS2]
if SAFE_STATION_CFG:
    SRCS2 = [s.replace("qfd_dv_redstn2_rsafe.sv", "qfd_dv_redstn2_csafe.sv") for s in SRCS2]
if SAFE_STATION_MATH:
    SRCS2 = [s.replace("qfd_dv_redstn2_csafe.sv", "qfd_dv_redstn2_gsafe.sv") for s in SRCS2]
    SRCS2.append("rtl/qwen_dv/qfd_dv_station_math_g.sv")
    SRCS2.append("rtl/common/landed_parent/ot_pl_land_physical.sv")
    for dep in ["rtl/qwen_dv/qfd_dv_ring_delay.sv", "rtl/common/landed_parent/ot_pl_land.sv"]:
        if dep not in SRCS2:
            SRCS2.append(dep)
# QW-SLICE 10-19: DV2_STATION_REGIONAL=1 swaps the station for the 8-region partition (qfd_dv_redstn2_regional.sv,
# +define+OT_STATION_REGIONAL); DV2_OT_ASSERT=1 builds the simulation-only landing epoch checkers (+define+OT_ASSERT),
# default = the physical (synthesized) landing source.
STATION_REGIONAL = os.environ.get("DV2_STATION_REGIONAL", "0") == "1"
if STATION_REGIONAL and not SAFE_STATION_MATH:
    raise SystemExit("DV2_STATION_REGIONAL requires DV2_SAFE_STATION_MATH")
if STATION_REGIONAL:
    SRCS2.append("rtl/qwen_dv/qfd_dv_redstn2_regional.sv")
OT_ASSERT = os.environ.get("DV2_OT_ASSERT", "0") == "1"
DEFINES2 = (["+define+OT_STATION_REGIONAL"] if STATION_REGIONAL else []) + (["+define+OT_ASSERT"] if OT_ASSERT else [])
if SAFE_STREAM_RESET:
    SRCS2 = [s.replace("rtl/qwen_dv/qfd_dv_stream.sv", "rtl/qwen_dv/qfd_dv_stream_rsafe.sv") for s in SRCS2]
# TOK-QW 10-24: DV2_S8DIE=1 -> the BOUND compute-die slice row (tb_qfd_dv2 FACE 3, s8die/qfd_dv_slice_die.sv): the s8
# sources FIRST (Verilator keeps the first declaration of a duplicated module -> the bound children win), then SRCS2.
# Flags (-GFACE=3 + the s8 defines) come from tools/qwen_tokfunc/s8die_srcs.py S8_FLAGS via --vflags / DV_LOWER_VFLAGS.
if os.environ.get("DV2_S8DIE", "0") == "1":
    sys.path.insert(0, str(ROOT / "tools/qwen_tokfunc"))
    import s8die_srcs as _S8  # noqa: E402
    _s8 = _S8.s8_files(ROOT)
    SRCS2 = _s8 + [s for s in SRCS2 if s not in _s8]
# MU-ADOPT-SLICE 10-19 (environment, default = today): DV2_MU_NU users of the LM-head argmax (qfd_dv_slice2 MU_NU);
# DV2_FACE 0 master qfd_dv_slice2 / 1 qfd_dv_slice2_w / 2 qfd_dv_slice2_e (tb_dv2_slice port map); DV2_AM_MUT bench-only
# qfd_dv_amax_mu mutant (+define+OT_DV_AMAX_MUT); DV2_GAP edges between an STN op's last data word and the next op (m).
# MU-DQ-SLICEKC 10-19 (merge of MU-SLICE-GATE c9276ad29 / 4180abc13 with main's FACE wrapper): -GMU_NU=<n> / -GFACE=<f>
# in --vflags override DV2_MU_NU / DV2_FACE; -GSU_LT=1 / -GHD_W130=1 (the kitted slice) reach every FACE through
# tb_qfd_dv2 -> tb_dv2_slice and add XSRCS (hard SU lane tile + its lane sources).
import os  # noqa: E402
MU_NU = int(os.environ.get("DV2_MU_NU", "1"))
FACE = int(os.environ.get("DV2_FACE", "0"))
AM_MUT = int(os.environ.get("DV2_AM_MUT", "0"))
P_RET_AR, P_RET_DD, P_SWI2 = 1001, 1040, 41      # pre-translation codes (TB ports 1 / 40 / 41)
SK = 14


def P_RSS(sl):
    return 2 + 2 * sl


def P_RSN(sl):
    return 3 + 2 * sl


def setid(i):
    return B.pack([(1, 1), (7, 3), (i, 4)])


def cmd_ports2(ar_base, dd_base, ar_en=0, dd_en=0, em_base=0, em_en=0):
    return B.pack([(1, 1), (4, 3), (ar_base, 24), (dd_base, 24), (ar_en, 1), (dd_en, 1), (em_base, 24), (em_en, 1)])


class Ev2(B.Ev):
    """Port translation onto the chain: CMD+sl -> s0.cmd_i at t - 2 sl with dst sl; SWI -> st_up_i of s0."""

    def write(self, path):
        out, used = [], {}
        out.append((2, 0, setid(0)))
        used[2] = 1
        for t, p, v in self.ev:
            if p in (B.P_CMD, B.P_CMD + 1):
                sl = p - B.P_CMD
                ti = t - 2 * sl
                while ti in used:                 # one command enters the chain an edge: arrive earlier
                    ti -= 1
                used[ti] = 1
                out.append((ti, 0, v | (sl << 112)))
            elif p == B.P_SWI:
                out.append((t, P_SWI2, v))
            elif p in (P_RET_AR, P_RET_DD):
                out.append((t, p - 1000, v))
            else:
                out.append((t, p, v))
        with open(path, "w") as f:
            for t, p, v in sorted(out, key=lambda e: (e[0], e[1])):
                f.write(f"{t + RESET_WARM} {p} {v:x}\n")


def load_vm2(ev, sl, base, vals):
    ev.at(B.P_CMD + sl, cmd_ports2(base, 0, ar_en=1))
    ev.at(B.P_CMD + (1 - sl), cmd_ports2(0, 0, ar_en=0), t=ev.t + 1)
    ev.step(8)
    for w in range(0, len(vals), 16):
        ev.at(P_RET_AR, B.ar_word(vals[w:w + 16]))
        ev.step()
    ev.step(6)


def conv48(w):
    """48-b scalar word -> the 96-b layout dv_bench reads (kind, idx at [87:64], value)."""
    kind = (w >> 44) & 7
    tag, val = (w >> 32) & 0xFFF, w & 0xFFFFFFFF
    k1 = {1: 1, 2: 2, 3: 3, 4: 3, 5: 4}.get(kind, 0)
    idx = val & 0xFFFFFF if kind == 5 else tag
    return (1 << 95) | (k1 << 92) | (idx << 64) | val


VFLAGS: list[str] = []          # S-QSLICE 10-18: --vflags (e.g. -GSU_LT=1 -GHD_W130=1); empty = the original build
# MU-SLICE-GATE 10-19: MU_NU follows -GMU_NU=<n> in --vflags (else DV2_MU_NU), FACE follows -GFACE=<f> (else DV2_FACE);
# DV2_AM_MUT adds +define+OT_DV_AMAX_MUT=<n> (bench-only qfd_dv_amax_mu / qfd_dv_scalar2 mutants, 7 = no mixed-merge check).
XSRCS = ["rtl/qwen_dv/qfd_dv_su_lane.sv", "rtl/hdc/ot_hdc_vstream_lane_t.sv", "rtl/hdc/ot_hdc_vstream_sfu_t.sv",
         "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
         "rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv"]


def run_sim2(name, ev, work, mut, ncyc, n=2):
    work.mkdir(parents=True, exist_ok=True)
    evf, lgf = work / f"{name}.ev", work / f"{name}.log"
    vtag = "".join(c for c in "_".join(f.lstrip("-+") for f in VFLAGS) if c.isalnum() or c in "_=")
    obj = work / (f"obj2_n{n}_nu{MU_NU}_f{FACE}_am{AM_MUT}" + ("_sr1" if SAFE_RESET else "") + ("_ar1" if SAFE_AMAX_RESET else "") + ("_sc1" if SAFE_SCALAR_RESET else "") + ("_cfg1" if SAFE_CFG else "") + ("_stm1" if SAFE_STREAM_RESET else "") + ("_stcfg1" if SAFE_STATION_CFG else "") + ("_stmath1" if SAFE_STATION_MATH else "") + ("_ns1" if NATIVE_SRAM else "") + ("_rg1" if STATION_REGIONAL else "") + ("_oa1" if OT_ASSERT else "")) / (vtag or "base")
    exe = obj / "Vtb"
    ev.write(evf)
    if not exe.exists():
        cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-j", "16", "-Wno-fatal", "-Wno-lint", "-Wno-style",
               "-Wno-TIMESCALEMOD", "--x-assign", "0", "--x-initial", "0", "--top-module", "tb_qfd_dv2",
               "--prefix", "Vtb", f"-GMUT={mut}", f"-GN={n}", f"-GMU_NU={MU_NU}", f"-GFACE={FACE}"] + \
              ([f"+define+OT_DV_AMAX_MUT={AM_MUT}"] if AM_MUT else []) + \
              DEFINES2 + \
              VFLAGS + ["-Mdir", str(obj), str(HERE / "main2.cpp")] + \
              [str(ROOT / s) for s in SRCS2 + (XSRCS if VFLAGS else [])]
        obj.mkdir(parents=True, exist_ok=True)
        with open(obj.parent / f"build_{obj.name}.log", "w") as bl:     # kept: a failed build names its error
            r = subprocess.run(cmd, stdout=bl, stderr=subprocess.STDOUT)
        if r.returncode:
            print("    VERILATOR BUILD FAIL:", "".join(open(obj.parent / f"build_{obj.name}.log").readlines()[-15:]))
            raise subprocess.CalledProcessError(r.returncode, cmd[:4])
    subprocess.run([str(exe), f"+EV={evf}", f"+LOG={lgf}", f"+NCYC={ncyc + RESET_WARM}"], check=True, stdout=subprocess.DEVNULL)
    out = {}
    for line in lgf.read_text().split("\n"):
        if line.strip():
            c, nm, h = line.split()
            out.setdefault(nm, []).append((int(c) - RESET_WARM, int(h.replace('x', '0').replace('X', '0').replace('z', '0'), 16)))
    # dv_bench names: root words leaving up = S0SC, slice 1's words leaving down = S1SC; D2D of any slice
    out["S0SC"] = [(c, conv48(w)) for c, w in out.get("S0SU", [])]
    out["S1SC"] = [(c, conv48(w)) for c, w in out.get("S1SD", [])]
    out["S1DD"] = out.get("S0DD", [])
    out["S1E"] = out.get("S1E", [])
    return out


def status_ok2(log):
    bad = []
    for _, ag in log.get("S0AG", [])[:1]:
        if (ag >> 9) & 1:
            bad.append(f"S0AG stn_busy still set at the end ({ag:010b})")
    for k in sorted(n for n in log if n.endswith("ST")):
        v = log[k][0][1]
        if (v >> 69) & 1:
            bad.append(f"{k} fault bits {(v >> 63) & 0x7F:07b} (any,su,vm,stn,sc,stm,port)")
    return bad


# ------------------------------------------------------------------------------------- overridden benches
def bench_a2(work, mut, trials=8, seed=1):
    """As dv_bench (a); the r read back by each slice goes to D2D element 0x10 + slice (one W5 edge port)."""
    rng = np.random.default_rng(seed)
    ev = B.Ev()
    X, SSX, RX = 0x0000, 0x3000, 0x3008
    for sl in (0, 1):
        B.load_prog(ev, sl, [
            B.su(nout=16, nin=128, a=X, aso=128, asi=1, red=1, redsq=1, rb=B.W_SC | (16 * sl), rso=1),
            B.su(nout=1, nin=1, a=SSX, ma=B.MA_AIMM, imm1=1.0 / 4096, ad=B.AD_IMM, imm2=EPS, sfu=B.SFU_RSQRT,
                 dst=B.DST_VM, d=B.W_SC | RX),
            B.su(nout=1, nin=1, a=RX, dst=B.DST_VM, d=B.W_D2D | (0x10 + sl)),
        ])
    exp, fused = [], []
    for t in range(trials):
        x = (rng.standard_normal(4096) * rng.choice([0.05, 1.0, 30.0])).astype(F)
        x[rng.integers(0, 4096, 8)] *= F(50)
        x = (x * np.repeat(F(10.0) ** rng.uniform(-1.5, 1.5, 32).astype(F), 128)).astype(F)
        exp.append(B.u32(G.rsqrt(G.add(G.mul(G.reduce_chunked(G.mul(x, x)), F(1.0 / 4096)), EPS))))
        fu = t % 2
        fused.append(fu)
        for sl in (0, 1):
            load_vm2(ev, sl, X, x[2048 * sl:2048 * (sl + 1)])
        ev.at(B.P_CMD + 0, B.cmd_root(1, 32, SSX, fuse=fu, rx=RX, eps=EPS, k=12))
        ev.at(B.P_CMD + 1, B.cmd_root(0, 32, SSX, rx=RX), t=ev.t + 1)
        ev.step(4)
        ev.at(B.P_CMD + 0, B.cmd_su(0)); ev.at(B.P_CMD + 1, B.cmd_su(0), t=ev.t + 1); ev.step(B.gap(256) + 120)
        if not fu:
            ev.at(B.P_CMD + 0, B.cmd_su(1)); ev.step(B.gap(1, 120))
        for sl in (0, 1):
            ev.at(B.P_CMD + sl, B.cmd_su(2)); ev.step(B.gap(1, 60))
    log = run_sim2("a", ev, work, mut, ev.t + 50)
    errs = status_ok2(log)
    rbw = [(c, w & 0xFFFFFFFF) for c, w in log.get("S0SC", []) if (w >> 92) & 7 == 2]
    rds = {sl: [] for sl in (0, 1)}
    for a, v in [(a, v) for _, w in log.get("S0DD", []) for a, v in [(((w >> 345) & 0xFFFFFF), (w >> 89) & 0xFFFFFFFF)]]:
        if a in (0x10, 0x11):
            rds[a - 0x10].append(v)
    ok = 0
    for t in range(trials):
        for tag, lst in (("RB", [v for _, v in rbw]), ("S0 r", rds[0]), ("S1 r", rds[1])):
            if t < len(lst) and lst[t] == exp[t]:
                ok += 1
            else:
                errs.append(f"trial {t} {tag}: got {hex(lst[t]) if t < len(lst) else None} exp {hex(exp[t])}")
    ps = [c for c, w in log.get("S1SC", []) if (w >> 92) & 7 == 1]
    lat = [rbw[t][0] - max(c for c in ps if c < rbw[t][0]) for t in range(trials) if fused[t] and t < len(rbw)]
    if lat:
        print(f"  (measured) fused root: last PSUM out of slice 1 -> r out of the root = {sorted(set(lat))} cycles")
    return ok, 3 * trials, errs


def pair2(ev, sl, lo_far, lo_near, hi_far, hi_near, t):
    """Both level-7 pairs of slice sl: far words at t, near words SKEW earlier."""
    if lo_far is not None:
        ev.at(P_RSS(sl), B.cluster_word(lo_far) << 514, t=t)
        ev.at(P_RSS(sl), B.cluster_word(lo_near), t=t - SK)
    if hi_far is not None:
        ev.at(P_RSN(sl), B.cluster_word(hi_far) << 514, t=t)
        ev.at(P_RSN(sl), B.cluster_word(hi_near), t=t - SK)


def bench_c2(work, mut, seed=3):
    rng = np.random.default_rng(seed)
    ev = B.Ev()
    kc = 2

    def mat(S):
        w = rng.integers(-127, 128, size=(128, S * kc)).astype(F)
        x = (rng.standard_normal(S * kc) * 2.0).astype(F)
        s = G.to_bf16((rng.random(128) * 0.02 + 1e-3).astype(F))
        return w, x, s

    tests = []
    wg, xg, sg = mat(128)
    wu, xu, su_ = mat(128)
    B.load_btab(ev, 0, 0, np.concatenate([sg, su_]))
    w8, x8, s8 = mat(256)
    B.load_btab(ev, 0, 16, s8)
    w9, x9, s9 = mat(512)
    B.load_btab(ev, 0, 32, s9)
    ev.step(4)
    # L7 gate (lower pair) and up (upper pair) on the same edges; up leaves 8 edges later from the buffer
    lg, lu = B.l6_parts(wg, xg, 128), B.l6_parts(wu, xu, 128)
    ev.at(B.P_CMD, B.cmd_stn(0, 0, 16, 0, 2, 0x2000)); ev.step(4 + SK)
    for k in range(8):
        sl_ = slice(16 * k, 16 * k + 16)
        pair2(ev, 0, lg[0][sl_], lg[1][sl_], lu[1][sl_], lu[0][sl_], ev.t); ev.step()
    ev.step(50)
    tests.append(("L7 gate/up", 0x2000, np.concatenate([G.mul(G.matvec(wg, xg, 128), sg),
                                                       G.mul(G.matvec(wu, xu, 128), su_)])))
    l8 = B.l6_parts(w8, x8, 256)
    for wsrc, base in ((0, 0x2400), (1, 0x2800)):
        ev.at(B.P_CMD, B.cmd_stn(1, wsrc, 8, 16, 3, base)); ev.step(4 + SK)
        for k in range(8):
            sl_ = slice(16 * k, 16 * k + 16)
            pair2(ev, 0, l8[0][sl_], l8[1][sl_], l8[3][sl_], l8[2][sl_], ev.t); ev.step()
        ev.step(50)
        y = G.matvec(w8, x8, 256)
        tests.append((f"L8 {'unscaled' if wsrc else 'scaled'}", base, G.mul(y, F(1.0)) if wsrc else G.mul(y, s8)))
    l9 = B.l6_parts(w9, x9, 512)
    ev.at(B.P_CMD + 0, B.cmd_stn(2, 0, 8, 32, 2, 0x2C00)); ev.at(B.P_CMD + 1, B.cmd_stn(3, 0, 8, 0, 0, 0), t=ev.t + 1)
    ev.step(4 + SK)
    for k in range(8):
        sl_ = slice(16 * k, 16 * k + 16)
        for sl in (0, 1):
            b = 4 * sl
            pair2(ev, sl, l9[b][sl_], l9[b + 1][sl_], l9[b + 3][sl_], l9[b + 2][sl_], ev.t)
        ev.step()
    ev.step(60)
    tests.append(("L9 pair", 0x2C00, G.mul(G.matvec(w9, x9, 512), s9)))
    log = run_sim2("c", ev, work, mut, ev.t + 20)
    errs = status_ok2(log)
    got = {}
    for _, w in log.get("S0AR", []):
        tag = (w >> 514) & 0xFFFFFFFF          # AR word {v, tag 32, mode, last, data 512}
        for l in range(16):
            got[tag + l] = (w >> (32 * l)) & 0xFFFFFFFF
    ok = n = 0
    for name, base, y in tests:
        ok += B.cmp(name, {i: got.get(base + i) for i in range(len(y))}, B.fbits(y), errs)
        n += len(y)
    return ok, n, errs


def bench_k2(work, mut, seed=11, users=(0, 0, 0), name="k"):
    """(k) redstn2 LAST-K selection (QW-DIEFIX 10-19): every pair streams JB = 8 words per (round, k) -- the tiles' running
    accumulator -- and only the k = kc - 1 block is the level-6 result.  L8 scaled kc 3, L7 gate/up kc 2 (two rounds of
    the lower pair would be a second op), L8 unscaled kc 1 (regression).  The k < kc - 1 blocks carry different
    (partial-sum-sized) words; MUT 14 (kcm1 ignored) must FAIL (wrong sums, more result words than nwords)."""
    rng = np.random.default_rng(seed)
    ev = B.Ev()
    kcl = 2

    def mat(S):
        w = rng.integers(-127, 128, size=(128, S * kcl)).astype(F)
        x = (rng.standard_normal(S * kcl) * 2.0).astype(F)
        s = G.to_bf16((rng.random(128) * 0.02 + 1e-3).astype(F))
        return w, x, s

    def junk(n):
        return [(rng.standard_normal(128) * 300.0).astype(F) for _ in range(n)]

    tests = []
    w8, x8, s8 = mat(256)
    wg, xg, sg = mat(128)
    wu, xu, su_ = mat(128)
    B.load_btab(ev, 0, 0, np.concatenate([sg, su_]))
    B.load_btab(ev, 0, 16, s8)
    ev.step(4)
    l8 = B.l6_parts(w8, x8, 256)
    for kc, wsrc, base, u in ((3, 0, 0x2400, users[0]), (1, 1, 0x2800, users[1])):
        ev.at(B.P_CMD, B.cmd_stn(1, wsrc, 8, 16, 3, base, kcm1=kc - 1) | (u << 51)); ev.step(4 + SK)
        for kk in range(kc):
            src = l8 if kk == kc - 1 else junk(4)
            for k in range(8):
                sl_ = slice(16 * k, 16 * k + 16)
                pair2(ev, 0, src[0][sl_], src[1][sl_], src[3][sl_], src[2][sl_], ev.t); ev.step()
        ev.step(50)
        y = G.matvec(w8, x8, 256)
        tests.append((f"L8 kc{kc} {'unscaled' if wsrc else 'scaled'}", base,
                      G.mul(y, F(1.0)) if wsrc else G.mul(y, s8)))
    lg, lu = B.l6_parts(wg, xg, 128), B.l6_parts(wu, xu, 128)
    ev.at(B.P_CMD, B.cmd_stn(0, 0, 16, 0, 2, 0x2000, kcm1=1) | (users[2] << 51)); ev.step(4 + SK)
    for kk in range(2):
        g_, u_ = (lg, lu) if kk == 1 else (junk(2), junk(2))
        for k in range(8):
            sl_ = slice(16 * k, 16 * k + 16)
            pair2(ev, 0, g_[0][sl_], g_[1][sl_], u_[1][sl_], u_[0][sl_], ev.t); ev.step()
    ev.step(60)
    tests.append(("L7 gate/up kc2", 0x2000, np.concatenate([G.mul(G.matvec(wg, xg, 128), sg),
                                                           G.mul(G.matvec(wu, xu, 128), su_)])))
    log = run_sim2(name, ev, work, mut, ev.t + 20)
    errs = status_ok2(log)
    got = {}
    for _, w in log.get("S0AR", []):
        tag = (w >> 514) & 0xFFFFFFFF
        for l in range(16):
            got[tag + l] = (w >> (32 * l)) & 0xFFFFFFFF
    ok = n = 0
    for name, base, y in tests:
        ok += B.cmp(name, {i: got.get(base + i) for i in range(len(y))}, B.fbits(y), errs)
        n += len(y)
    return ok, n, errs


def bench_q2(work, mut):
    """(q) MU-DQ-SLICEKC 10-19 (COORD 0kg): bench k with MU STN users 1 / 2 / 3 in cmd[52:51] TOGETHER with kc - 1 in
    cmd[66:59] (kc 3 / 1 / 2): the user field and the last-k count must not overlap.  MUT 15 (kcm1 read from the pre-fix
    field [58:51], whose low bits are the user) must FAIL; MUT 14 (kcm1 ignored) FAILs too."""
    return bench_k2(work, mut, users=(1, 2, 3), name="q")


def bench_f2(work, mut, seed=6):
    rng = np.random.default_rng(seed)
    ev = B.Ev()
    exp = []
    for t in range(3):
        v = (rng.standard_normal(768) * 4.0).astype(F)
        v[v == 0] = F(1.0)
        top = F(np.max(np.abs(v)) * 2 + 1)
        for r in {0: [200, 300, 640], 1: [500], 2: [383, 384]}[t]:
            v[r] = top
        exp.append(int(np.argmax(G.mul(G.add(v, F(0)), F(1.0)))))
        for sl in (0, 1):
            ev.at(B.P_CMD + sl, B.cmd_amax(clear=1), t=ev.t + sl)
        ev.at(B.P_CMD + 0, B.cmd_root(1, 0, 0, amnb=2), t=ev.t + 2)
        ev.at(B.P_CMD + 1, B.cmd_root(0, 0, 0), t=ev.t + 3)
        ev.step(6)
        for rd in range(3):
            for sl in (0, 1):
                ev.at(B.P_CMD + sl, B.cmd_stn(0, 1, 8, 0, 0, sl * 384 + rd * 128, amax=1), t=ev.t + sl)
            ev.step(4 + SK)
            for k in range(8):
                for sl in (0, 1):
                    base = sl * 384 + rd * 128 + 16 * k
                    pair2(ev, sl, v[base:base + 16], np.zeros(16, dtype=F), None, None, ev.t)
                ev.step()
            ev.step(30)
        ev.at(B.P_CMD + 1, B.cmd_amax(emit=1)); ev.at(B.P_CMD + 0, B.cmd_amax(emit=1), t=ev.t + 3)
        ev.step(30)
    log = run_sim2("f", ev, work, mut, ev.t + 20)
    errs = status_ok2(log)
    tok = [w & 0xFFFFFF for _, w in log.get("S0TOK", [])]
    ring = [(w >> 64) & 0xFFFFFF for _, w in log.get("S0SC", []) if (w >> 92) & 7 == 4]
    tok1 = [w & 0xFFFFFF for _, w in log.get("S1TOK", [])]
    ok = 0
    for t in range(3):
        g = [lst[t] if t < len(lst) else None for lst in (tok, ring, tok1)]
        if all(x == exp[t] for x in g):
            ok += 1
        else:
            errs.append(f"trial {t}: root token / broadcast / slice-1 token {g}, golden argmax {exp[t]}")
    return ok, 3, errs


def bench_h(work, mut, n=12):
    """SETID enumeration of an n-slice chain: slice k latches id k (status sid field)."""
    ev = B.Ev()
    ev.step(4 * n)
    log = run_sim2("h", ev, work, mut, ev.t + 20, n=n)
    errs = status_ok2(log)
    ok = 0
    for k in range(n):
        sid = (log[f"S{k}ST"][0][1] >> 70) & 0xF
        if sid == k:
            ok += 1
        else:
            errs.append(f"slice {k}: id {sid}")
    return ok, n, errs


def cmd_xc_coll(mode, words, tag):
    return B.pack([(1, 1), (0, 3), (0, 2), (mode, 1), (words, 16), (tag, 32)])


def cmd_amax2(clear=0, emit=0, arx=0, gather=0):
    return B.pack([(1, 1), (6, 3), (clear, 1), (emit, 1), (arx, 1), (gather, 1)])


def bench_i(work, mut):
    """XC COLL: the addressed slice puts {v, mode, words, tag} on cc_o for one edge, exactly (collective cmd_* set);
    a non-zero XC sub raises the port fault of that slice only."""
    ev = B.Ev()
    want = [(0, 1, 0x1234, 0xDEADBEEF), (1, 0, 0x0007, 0x00000005), (0, 0, 0xFFFF, 0x80000001), (1, 1, 0x0100, 0x7)]
    for sl, mode, words, tag in want:
        ev.at(B.P_CMD + sl, cmd_xc_coll(mode, words, tag))
        ev.step(5)
    ev.step(10)
    log = run_sim2("i", ev, work, mut, ev.t + 20)
    errs = status_ok2(log)
    got = {sl: [w for _, w in log.get(f"S{sl}CC", [])] for sl in (0, 1)}
    ok = 0
    for sl in (0, 1):
        exp = [(1 << 49) | (m << 48) | (wd << 32) | tg for s_, m, wd, tg in want if s_ == sl]
        if got[sl] == exp:
            ok += 1
        else:
            errs.append(f"slice {sl}: cc {[hex(x) for x in got[sl]]} want {[hex(x) for x in exp]}")
    # negative: an undefined XC sub faults (separate run, slice 1 only)
    ev = B.Ev()
    ev.at(B.P_CMD + 1, B.pack([(1, 1), (0, 3), (1, 2)]))
    ev.step(20)
    log = run_sim2("i_bad", ev, work, mut, ev.t + 20)
    st0, st1 = log["S0ST"][0][1], log["S1ST"][0][1]
    if not ((st1 >> 63) & 1) or ((st0 >> 63) & 1) or log.get("S1CC"):
        errs.append(f"XC sub 1: slice-1 port fault {(st1 >> 63) & 1} slice-0 {(st0 >> 63) & 1} cc {log.get('S1CC')}")
    else:
        ok += 1
    return ok, 3, errs


def okey(v):
    return (~v & 0xFFFFFFFF) if v >> 31 else (v | 0x80000000)


def bench_j(work, mut, seed=11):
    """Cross-die argmax: (1) the root's die-wide argmax leaves as ONE AR word {v, tag {0, idx}, mode 1, last 1,
    {0, idx, val}} (AMAX ARX); (2) GATHER: 8 rank-ordered AR returns are merged on every slice (strictly greater okey,
    a tie keeps the earlier rank), not landed, and the last one sets every slice's status token."""
    rng = np.random.default_rng(seed)
    ev = B.Ev()
    v = (rng.standard_normal(768) * 4.0).astype(F)
    v[v == 0] = F(1.0)
    v[517] = F(np.max(np.abs(v)) * 2 + 1)
    exp_idx = int(np.argmax(G.mul(G.add(v, F(0)), F(1.0))))
    exp_val = int(B.fbits(G.mul(G.add(v, F(0)), F(1.0)))[exp_idx])
    for sl in (0, 1):
        ev.at(B.P_CMD + sl, cmd_amax2(clear=1), t=ev.t + sl)
    ev.at(B.P_CMD + 0, B.cmd_root(1, 0, 0, amnb=2), t=ev.t + 2)
    ev.at(B.P_CMD + 1, B.cmd_root(0, 0, 0), t=ev.t + 3)
    ev.at(B.P_CMD + 0, cmd_amax2(arx=1), t=ev.t + 4)
    ev.step(8)
    for rd in range(3):
        for sl in (0, 1):
            ev.at(B.P_CMD + sl, B.cmd_stn(0, 1, 8, 0, 0, sl * 384 + rd * 128, amax=1), t=ev.t + sl)
        ev.step(4 + SK)
        for k in range(8):
            for sl in (0, 1):
                base = sl * 384 + rd * 128 + 16 * k
                pair2(ev, sl, v[base:base + 16], np.zeros(16, dtype=F), None, None, ev.t)
            ev.step()
        ev.step(30)
    ev.at(B.P_CMD + 1, B.cmd_amax(emit=1)); ev.at(B.P_CMD + 0, B.cmd_amax(emit=1), t=ev.t + 3)
    ev.step(40)
    # gather: 8 ranks; rank 2 and rank 5 tie at the maximum -> rank 2's index
    for sl in (0, 1):
        ev.at(B.P_CMD + sl, cmd_amax2(gather=1), t=ev.t + sl)
    ev.step(8)
    vals = [u for u in B.fbits(rng.standard_normal(8).astype(F))]
    top = int(B.fbits(np.array([50.0], dtype=F))[0])
    vals[2] = vals[5] = top
    vals[6] = int(B.fbits(np.array([-60.0], dtype=F))[0])
    idxs = [1000 * r + 7 for r in range(8)]
    for r in range(8):
        data = (idxs[r] << 32) | int(vals[r])
        ev.at(P_RET_AR, (1 << 517) | (r << 513) | ((1 if r == 7 else 0) << 512) | data)
        ev.step()
    ev.step(20)
    log = run_sim2("j", ev, work, mut, ev.t + 20)
    errs = status_ok2(log)
    ok = 0
    ar = [w for _, w in log.get("S0AR", [])]
    want = (1 << 546) | (exp_idx << 514) | (1 << 513) | (1 << 512) | (exp_idx << 32) | exp_val
    if ar == [want]:
        ok += 1
    else:
        errs.append(f"ARX words {[hex(x) for x in ar]} want [{hex(want)}] (argmax {exp_idx})")
    best = max(range(8), key=lambda r: (okey(int(vals[r])), -r))
    for sl in (0, 1):
        toks = [w & 0xFFFFFF for _, w in log.get(f"S{sl}TOK", [])]
        stv = (log[f"S{sl}ST"][0][1] >> 74) & 0xFFFFFFFF
        if toks and toks[-1] == idxs[best] and stv == int(vals[best]):
            ok += 1
        else:
            errs.append(f"slice {sl}: gather tokens {toks} value {stv:08x}, want last {idxs[best]} (rank {best})")
    return ok, 3, errs


def cmd_stn_u(mode, wsrc, nwords, sbase, dst, dbase, amax=0, user=0):
    """STN with the MU-QWEN R4 user field cmd[52:51]."""
    return B.cmd_stn(mode, wsrc, nwords, sbase, dst, dbase, amax=amax) | ((user & 3) << 51)


def cmd_amax_u(clear=0, emit=0, user=0):
    """AMAX with the MU-QWEN R4 user field cmd[9:8]."""
    return cmd_amax2(clear=clear, emit=emit) | ((user & 3) << 8)


def bench_m(work, mut, seed=21, rounds=2, nu=4, nch=4):
    """MU-ADOPT-SLICE (MU-QWEN R4 on the slice / face RTL): 4 users' LM heads as row chunks interleaved op by op on a
    2-slice chain, as the static calendar runs them.  Per round every user u has 2 x nch x 128 rows (slice sl rows
    sl*512 + c*128 ..); its op sequence is a random interleave of all users' (u, c) chunk ops (chunk order permuted);
    AMAX clear of u just before u's first chunk, AMAX emit of u at a random later point (often after another user's
    STN, so the emit must select the AMAX command's user); ties of the top value inside a slice across chunks, at a
    chunk boundary and across slices (the lowest index must win).  STN ops are spaced DV2_GAP edges after the last
    data word (default 18: the next STN issues while the previous op's last results are still in the compare tree, so
    the user must travel down the tree).  Check: per emit, the root token, the ring broadcast and slice 1's token
    equal the golden single-shot argmax of that user's rows (np.argmax: lowest index of the maximum); no fault.
    At MU_NU 1 (no per-user state) the heads collide and the bench must FAIL.  One ROOT cfg at the start: at MU_NU > 1
    the root restarts its argmax merge after each token (qfd_dv_scalar2 MU_NU; a ROOT cfg per user token would clear
    other users' PSUM slots); DV2_AM_MUT 6 removes that restart and must FAIL (every token = the largest head so far).
    DV2_GAP 12 / 14 issue the next STN while the previous op's results are pending: the stn_pend fault must fire (FAIL).
    MU-QW-AMIX 10-19 (MU_NU > 1): every token also carries its USER -- the root's and slice 1's status st[27:26] on the
    tok_v edge (contract with MU-QW-B1-RTL: ss5[27:26]) and the TOK broadcast word's tag[1:0] -- and must equal the
    emitted user."""
    seed = int(os.environ.get("DV2_SEED", seed))
    rng = np.random.default_rng(seed)
    gap = int(os.environ.get("DV2_GAP", "18"))
    ev = B.Ev()
    R = 2 * 512
    exp = []
    ev.at(B.P_CMD + 0, B.cmd_root(1, 0, 0, amnb=2), t=ev.t)
    ev.at(B.P_CMD + 1, B.cmd_root(0, 0, 0), t=ev.t + 1)
    ev.step(8)
    ntie = 0
    for rnd in range(rounds):
        vals = {}
        for u in range(nu):
            v = (rng.standard_normal(R) * 4.0).astype(F)
            v[v == 0] = F(1.0)
            top = F(np.max(np.abs(v)) * 2 + 1)
            kind = (rnd * nu + u) % 4
            if kind == 0:      # chunk boundary inside slice 0 + a later chunk
                rows = [127, 128, 300 + int(rng.integers(0, 100))]
            elif kind == 1:    # across slices (slice 1 lower chunk vs slice 0 higher chunk)
                rows = [512 + int(rng.integers(0, 128)), 3 * 128 + int(rng.integers(0, 128))]
            elif kind == 2:    # chunk boundary inside slice 1 + slice 0's last chunk
                rows = [512 + 255, 512 + 256, 383]
            else:              # no tie, random position
                rows = [int(rng.integers(0, R))]
            for r in rows:
                v[r] = top
            ntie += len(rows) > 1
            vals[u] = v
        ops = [(u, c) for u in range(nu) for c in range(nch)]
        rng.shuffle(ops)
        first = {u: min(i for i, o in enumerate(ops) if o[0] == u) for u in range(nu)}
        last = {u: max(i for i, o in enumerate(ops) if o[0] == u) for u in range(nu)}
        emit_at = {u: int(rng.integers(last[u], len(ops))) for u in range(nu)}   # emit after op index emit_at[u]
        done_t = {}
        last_emit = -100
        pend = []
        for i, (u, c) in enumerate(ops):
            if i == first[u]:
                for sl in (0, 1):
                    ev.at(B.P_CMD + sl, cmd_amax_u(clear=1, user=u), t=ev.t + sl)
                ev.step(3)
            for sl in (0, 1):
                ev.at(B.P_CMD + sl, cmd_stn_u(0, 1, 8, 0, 0, sl * 512 + c * 128, amax=1, user=u), t=ev.t + sl)
            ev.step(4 + SK)
            for k in range(8):
                for sl in (0, 1):
                    base = sl * 512 + c * 128 + 16 * k
                    pair2(ev, sl, vals[u][base:base + 16], np.zeros(16, dtype=F), None, None, ev.t)
                ev.step()
            if i == last[u]:
                done_t[u] = ev.t
            ev.step(gap)
            for w in sorted(x for x in range(nu) if emit_at[x] == i):
                pend.append(w)
            # an emit waits until its user's last results merged (40 edges after the data) and the root finished the
            # previous user's token (30 edges); meanwhile the next ops run
            while pend and ev.t >= done_t[pend[0]] + 40 and ev.t >= last_emit + 30:
                w = pend.pop(0)
                ev.at(B.P_CMD + 1, cmd_amax_u(emit=1, user=w)); ev.at(B.P_CMD + 0, cmd_amax_u(emit=1, user=w), t=ev.t + 3)
                exp.append((rnd, w, int(np.argmax(G.mul(G.add(vals[w], F(0)), F(1.0))))))
                last_emit = ev.t
                ev.step(6)
        while pend:
            w = pend.pop(0)
            ev.step(max(0, done_t[w] + 40 - ev.t, last_emit + 30 - ev.t))
            ev.at(B.P_CMD + 1, cmd_amax_u(emit=1, user=w)); ev.at(B.P_CMD + 0, cmd_amax_u(emit=1, user=w), t=ev.t + 3)
            exp.append((rnd, w, int(np.argmax(G.mul(G.add(vals[w], F(0)), F(1.0))))))
            last_emit = ev.t
            ev.step(6)
        ev.step(40)
    log = run_sim2(f"m_g{gap}_s{seed}", ev, work, mut, ev.t + 20)
    errs = status_ok2(log)
    tok = [w & 0xFFFFFF for _, w in log.get("S0TOK", [])]
    ring = [(w >> 64) & 0xFFFFFF for _, w in log.get("S0SC", []) if (w >> 92) & 7 == 4]
    tok1 = [w & 0xFFFFFF for _, w in log.get("S1TOK", [])]
    # MU-QW-AMIX: token users (status [27:26] at the tok_v edge, TOK word tag[1:0] = raw scalar word [33:32])
    utok = [(w >> 26) & 3 for _, w in log.get("S0TOK", [])]
    utok1 = [(w >> 26) & 3 for _, w in log.get("S1TOK", [])]
    uring = [(w >> 32) & 3 for _, w in log.get("S0SU", []) if (w >> 44) & 7 == 5]
    ok = 0
    for i, (rnd, w, g) in enumerate(exp):
        got = [lst[i] if i < len(lst) else None for lst in (tok, ring, tok1)]
        gu = [lst[i] if i < len(lst) else None for lst in (utok, uring, utok1)]
        if all(x == g for x in got) and (MU_NU == 1 or all(x == w for x in gu)):
            ok += 1
        else:
            errs.append(f"round {rnd} user {w}: root token / broadcast / slice-1 token {got} users {gu}, golden argmax {g}")
    if len(tok) != len(exp):
        errs.append(f"{len(tok)} root tokens for {len(exp)} emits")
    print(f"    bench2 (m): seed {seed} gap {gap} MU_NU {MU_NU} FACE {FACE} AM_MUT {AM_MUT}: {len(exp)} emits, "
          f"{ntie} tie heads, end cycle {ev.t}")
    return ok, len(exp), errs


def bench_o(work, mut, seed=31):
    """MU-ADOPT-SLICE (F-TOK-1 / B2): an STN issued while the previous amax op's station results are still pending is a
    sticky port fault at MU_NU > 1 (it would drop / misattribute them).  Slice 0: STN amax user 1, its 8 data words,
    then DV2_OGAP edges later (default 4: results still streaming) an STN of user 2 (no amax).  Slice 1: the same first
    op, then the second STN 30 edges after the data (legal).  PASS iff slice 0's port fault (status bit 63) is set and
    slice 1's is clear; a second run with both second STNs legal must leave both clear."""
    rng = np.random.default_rng(seed)
    og = int(os.environ.get("DV2_OGAP", "4"))
    ok, errs = 0, []
    for case, g0 in (("ovl", og), ("legal", 30)):
        ev = B.Ev()
        v = (rng.standard_normal(256) * 4.0).astype(F)
        for sl in (0, 1):
            ev.at(B.P_CMD + sl, cmd_amax_u(clear=1, user=1), t=ev.t + sl)
        ev.step(4)
        for sl in (0, 1):
            ev.at(B.P_CMD + sl, cmd_stn_u(0, 1, 8, 0, 0, sl * 128, amax=1, user=1), t=ev.t + sl)
        ev.step(4 + SK)
        for k in range(8):
            for sl in (0, 1):
                pair2(ev, sl, v[sl * 128 + 16 * k:sl * 128 + 16 * k + 16], np.zeros(16, dtype=F), None, None, ev.t)
            ev.step()
        t0 = ev.t
        ev.at(B.P_CMD + 0, cmd_stn_u(0, 1, 8, 0, 0, 0x800, amax=0, user=2), t=t0 + g0)
        ev.at(B.P_CMD + 1, cmd_stn_u(0, 1, 8, 0, 0, 0x800, amax=0, user=2), t=t0 + 30 + 1)
        ev.step(80)
        log = run_sim2(f"o_{case}_g{g0}", ev, work, mut, ev.t + 20)
        pf = [(log[f"S{sl}ST"][0][1] >> 63) & 1 for sl in (0, 1)]
        want = [1, 0] if case == "ovl" else [0, 0]
        if pf == want:
            ok += 1
        else:
            errs.append(f"{case} (slice-0 second STN {g0} edges after the data): port fault slice0/slice1 {pf}, want {want}")
    print(f"    bench2 (o): ovl gap {og} MU_NU {MU_NU} FACE {FACE} AM_MUT {AM_MUT}")
    return ok, 2, errs


def bench_n(work, mut, seed=41):
    """MU-QW-AMIX 10-19: the root argmax merge must hold ONE user's candidates (qfd_dv_scalar2 MU_NU > 1 checks it).
    2-slice chain, root = slice 0 (amnb 2).  Users 1 and 2 each run one amax-armed STN chunk on both slices (rows
    sl*512 + {0, 128}..), heads cleared first.  Case 'mixed': slice 1 emits user 1 while the root emits user 2 (one merge,
    two users' candidates), then slice 1 emits user 2 while the root emits user 1.  Every per-slice command is legal for
    qfd_dv_amax_mu (both heads open), so only the root's mixed-merge check can see it: PASS iff the root's sc fault
    (status bit 65) is set, its port fault (63) is clear and slice 1 has no fault.  Case 'legal': the same heads, both
    slices emit user 1, then both user 2: no fault, root / slice-1 tokens = the golden argmax of each user's rows with
    the token user in status [27:26] and in the TOK word tag.  DV2_AM_MUT 7 (no check) must FAIL 'mixed'.  MU_NU > 1."""
    rng = np.random.default_rng(int(os.environ.get("DV2_SEED", seed)))
    users = (1, 2)
    ok, errs = 0, []
    for case in ("mixed", "legal"):
        ev = B.Ev()
        ev.at(B.P_CMD + 0, B.cmd_root(1, 0, 0, amnb=2), t=ev.t)
        ev.at(B.P_CMD + 1, B.cmd_root(0, 0, 0), t=ev.t + 1)
        ev.step(8)
        gold = {}
        for c, u in enumerate(users):
            v = (rng.standard_normal(2 * 128) * 4.0).astype(F)
            v[v == 0] = F(1.0)
            rows = [sl * 512 + c * 128 + j for sl in (0, 1) for j in range(128)]
            vv = G.mul(G.add(v, F(0)), F(1.0))
            gold[u] = rows[int(np.argmax(vv))]
            for sl in (0, 1):
                ev.at(B.P_CMD + sl, cmd_amax_u(clear=1, user=u), t=ev.t + sl)
            ev.step(3)
            for sl in (0, 1):
                ev.at(B.P_CMD + sl, cmd_stn_u(0, 1, 8, 0, 0, sl * 512 + c * 128, amax=1, user=u), t=ev.t + sl)
            ev.step(4 + SK)
            for k in range(8):
                for sl in (0, 1):
                    pair2(ev, sl, v[sl * 128 + 16 * k:sl * 128 + 16 * k + 16], np.zeros(16, dtype=F), None, None, ev.t)
                ev.step()
            ev.step(18)
        ev.step(40)
        pairs = [(1, 2), (2, 1)] if case == "mixed" else [(1, 1), (2, 2)]
        for u1, u0 in pairs:                       # (slice 1's emit user, the root's emit user)
            ev.at(B.P_CMD + 1, cmd_amax_u(emit=1, user=u1)); ev.at(B.P_CMD + 0, cmd_amax_u(emit=1, user=u0), t=ev.t + 3)
            ev.step(40)
        ev.step(20)
        log = run_sim2(f"n_{case}", ev, work, mut, ev.t + 20)
        st0, st1 = log["S0ST"][0][1], log["S1ST"][0][1]
        sc0, pf0, any1 = (st0 >> 65) & 1, (st0 >> 63) & 1, (st1 >> 69) & 1
        if case == "mixed":
            if sc0 == 1 and pf0 == 0 and any1 == 0:
                ok += 1
            else:
                errs.append(f"mixed: root sc fault {sc0} (want 1), root port fault {pf0} (want 0), slice-1 any fault {any1} (want 0)")
            continue
        bad = status_ok2(log)
        tok = [(w & 0xFFFFFF, (w >> 26) & 3) for _, w in log.get("S0TOK", [])]
        tok1 = [(w & 0xFFFFFF, (w >> 26) & 3) for _, w in log.get("S1TOK", [])]
        ring = [((w & 0xFFFFFF), (w >> 32) & 3) for _, w in log.get("S0SU", []) if (w >> 44) & 7 == 5]
        want = [(gold[u], u) for u in users]
        if not bad and tok == want and tok1 == want and ring == want:
            ok += 1
        else:
            errs.append(f"legal: faults {bad}; root {tok} / slice-1 {tok1} / TOK words {ring}, want {want}")
    print(f"    bench2 (n): MU_NU {MU_NU} FACE {FACE} AM_MUT {AM_MUT}")
    return ok, 2, errs


def install():
    B.Ev = Ev2
    B.load_vm = load_vm2
    B.run_sim = run_sim2
    B.status_ok = status_ok2


BENCHES = {"k": bench_k2, "q": bench_q2, "a": bench_a2, "b": B.bench_b, "c": bench_c2, "d": B.bench_d, "e": B.bench_e, "f": bench_f2,
           "g": B.bench_g, "h": bench_h, "i": bench_i, "j": bench_j, "m": bench_m, "o": bench_o, "n": bench_n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("benches", nargs="*", default=list("abcdefghij"))
    ap.add_argument("--mut", type=int, default=0)
    ap.add_argument("--work", default="/tmp/qdv_bench2v")
    ap.add_argument("--vflags", default="", help="extra Verilator flags (use a separate --work: objects are cached)")
    a = ap.parse_args()
    VFLAGS[:] = a.vflags.split()
    if SAFE_RESET and not any("OT_QFD_DV_SAFE_STORAGE" in f for f in VFLAGS):
        raise SystemExit("DV2_SAFE_RESET requires OT_QFD_DV_SAFE_STORAGE: station source is shape-specialized")
    global MU_NU, FACE
    for f in list(VFLAGS):        # MU_NU / FACE are passed by run_sim2 itself (one -G each)
        if f.startswith("-GMU_NU="):
            MU_NU = int(f.split("=", 1)[1]); VFLAGS.remove(f)
        elif f.startswith("-GFACE="):
            FACE = int(f.split("=", 1)[1]); VFLAGS.remove(f)
    install()
    allpass = True
    for b in a.benches:
        ok, n, errs = BENCHES[b](Path(a.work) / f"m{a.mut}", a.mut)
        verdict = "PASS" if (ok == n and not errs) else "FAIL"
        allpass &= verdict == "PASS"
        print(f"bench2 ({b}) MUT={a.mut}: {verdict} {ok}/{n}")
        for e in errs[:6]:
            print("   ", e)
    sys.exit(0 if allpass else 1)


if __name__ == "__main__":
    main()
