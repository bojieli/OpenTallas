#!/usr/bin/env python3
"""RTL campaign of the V4.1 vector stream unit (rtl/hdc/v41x/ot_hdc_v41x_vec.sv).

The unit is docs/ARCH_SPEC_V41.md section 6 item 2: N light lanes, M SFU lanes, a scalar
side pipe, an R-ARITH (chunk8) reducer and vector chaining.  This tool runs:

* THE REFERENCE (`ref_op`): tools/hdc_program_v41.Machine.su's element semantics
  (A..D, gather, pair mode, PRE / M1 / M2 / Q / AD / S / E1 / E2 / RND, KV and
  transposed-KV writes).  Its reductions follow R-ARITH: every sum is
  hdc_golden_v41.csum; red_whole and red_tree are csum over the whole op; MAX is on
  ordered keys.  `check_ref_vs_isa` confirms that the element results equal
  Machine.su1's on every op that has no reduction.
* THE PROGRAMS, sequences of ops run on the bench rtl/test/tb_hdc_v41x_vec.sv:
    random    random ops of every class, source, layout, reduction and chaining
              mode, over random data;
    vehicle   the stream ops of the reduced V4.1 vehicle's one-token program
              (hdc_program_v41.Builder), run on the vector-memory state the
              ISA-level simulator reaches before each op (build/models/...);
    perf      throughput (a 20,480-element hc_post-shaped op; back-to-back
              chained ops), depth per class, reducer latency, and chaining
              latency behind an external producer.
  Every program's final vector memory and KV SRAM must equal the reference's,
  word for word, and the unit must raise neither fault nor order_fault.
* Performance figures from the bench trace (emit / retire / result cycles per
  op), graded against the spec row.

Writes results/rtl/hdc_v41x_vec_campaign.json.
    python3 tools/rtl_hdc_v41x_vec_campaign.py [--quick] [--no-1024]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G          # noqa: E402
import hdc_golden_v41 as V      # noqa: E402
import hdc_isa_v41 as I         # noqa: E402

F = np.float32
OUT = ROOT / "results/rtl/hdc_v41x_vec_campaign.json"
RTL = [ROOT / f"rtl/hdc/v41x/{n}.sv" for n in
       ("ot_hdc_v41x_sfu", "ot_hdc_v41x_vec_lane", "ot_hdc_v41x_vec_side", "ot_hdc_v41x_vec_red", "ot_hdc_v41x_vec")]
LIB = [ROOT / p for p in ("rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
                          "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
                          "rtl/hdc/v41/ot_hdc_fsqrt.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41/ot_hdc_softplus.sv")]
TB = ROOT / "rtl/test/tb_hdc_v41x_vec.sv"
TB_SFU = ROOT / "rtl/test/tb_hdc_v41x_vec_sfu.sv"
FIELDS_SVH = ROOT / "rtl/test/tb_hdc_v41x_vec_fields.svh"
HARNESS = ROOT / "rtl/test/hdc_v41_harness.cpp"
TOOLS = [Path(__file__).resolve(), ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py",
         ROOT / "tools/hdc_program_v41.py", ROOT / "tools/hdc_isa_v41.py"]

# bench memories (log2 words)
VMA, KVA, CRA, WRA, XBA = 18, 19, 15, 16, 14
KVT_SH = 9                       # log2(head_dim 32 x 16 rows): the reduced vehicle's transposed-KV tile
CLOCK_GHZ = 1.034
_PINNED = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / \
    "verilator-5.050/bin/verilator"
VERILATOR = str(_PINNED) if _PINNED.exists() else "verilator"

# depths the RTL implements (ot_hdc_v41x_vec_lane / _red): emit -> write, per stage
D_FETCH, D_FETCH_G, D_PRE, D_M1, D_DIV, D_STAGE, D_OUT = 4, 6, 1, 3, 19, 3, 1   # fetch includes the broadcast reg
SFU_DEPTH = {I.SFU_NONE: 0, I.SFU_EXP: 49, I.SFU_SIGM: 71, I.SFU_SILU: 71, I.SFU_RSQRT: 37, I.SFU_SQRT: 31,
             I.SFU_SPSQRT: 162, I.SFU_EGATE: 104}
SCALAR_SFU = (I.SFU_RSQRT, I.SFU_SQRT, I.SFU_SPSQRT, I.SFU_EGATE)
VEC_SFU = (I.SFU_EXP, I.SFU_SIGM, I.SFU_SILU)
CH_NONE, CH_SELF, CH_RES, CH_EXT = range(4)

# ---- the bench's program word (rtl/test/tb_hdc_v41x_vec_fields.svh) --------------------------------
PFIELDS = [
    ("nout", 16), ("nin", 16), ("asrc", 2), ("bsrc", 2), ("csrc", 2), ("dsrc", 2),
    ("abase", 24), ("aso", 24), ("asi", 24), ("aibase", 24), ("aind", 2),
    ("bbase", 24), ("bso", 24), ("bsi", 24), ("bhalf", 1),
    ("cbase", 24), ("cso", 24), ("csi", 24), ("cpair", 1),
    ("dbase", 24), ("dso", 24), ("dsi", 24),
    ("arnd", 1), ("arelu", 1), ("amin", 1), ("cclip", 1),
    ("m1", 3), ("m2", 2), ("qm", 3), ("ad", 3), ("sfu", 3), ("e1", 3), ("e2", 2), ("rnd", 1), ("dst", 2),
    ("obase", 24), ("oso", 24), ("osi", 24), ("orow", 24),
    ("red", 2), ("redsq", 1), ("redwhole", 1), ("redtree", 1), ("redrnd", 1), ("rbase", 24), ("rso", 24),
    ("imm1", 32), ("imm2", 32), ("imm3", 32),
    ("ch_src", 2), ("ch_seq", 8), ("ch_lead", 16), ("ch_mul", 16),
    ("w_idle", 1), ("w_rseq_en", 1), ("w_rseq", 8), ("w_dseq_en", 1), ("w_dseq", 8), ("x_start", 1),
]
POFF = {}
_o = 0
for _n, _w in PFIELDS:
    POFF[_n] = (_o, _w)
    _o += _w
PW = _o


def write_fields_svh():
    lines = ["// GENERATED by tools/rtl_hdc_v41x_vec_campaign.py -- do not edit.",
             "// Field offsets of the bench's program word (tb_hdc_v41x_vec).",
             f"localparam integer PW = {PW};"]
    for n, (o, _) in POFF.items():
        lines.append(f"localparam integer F_{n.upper()} = {o};")
    text = "\n".join(lines) + "\n"
    if not FIELDS_SVH.exists() or FIELDS_SVH.read_text() != text:
        FIELDS_SVH.write_text(text)


def encode(op):
    word = 0
    for n, v in op.items():
        if n.startswith("_"):
            continue
        o, w = POFF[n]
        v = int(v)
        assert 0 <= v < (1 << w), (n, v)
        word |= v << o
    return word


def op_defaults():
    return {n: 0 for n, _ in PFIELDS}


# ---- bits -------------------------------------------------------------------------------------------
def fbits(x):
    return np.asarray(x, dtype=F).view(np.uint32)


def ffrom(b):
    return np.asarray(b, dtype=np.uint32).view(F)


def f32u(x):
    return int(np.asarray(F(x)).view(np.uint32))


def u32f(u):
    return np.uint32(u).view(F)


def okey(x):
    b = fbits(x).astype(np.uint64)
    return np.where(b >> 31, (~b) & 0xFFFFFFFF, b | 0x80000000)


def kmin(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, dtype=F), np.asarray(b, dtype=F))
    return np.where(okey(a) <= okey(b), a, b).astype(F)


def kmax(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, dtype=F), np.asarray(b, dtype=F))
    return np.where(okey(a) >= okey(b), a, b).astype(F)


def pow2(x):
    return x > 0 and (x & (x - 1)) == 0


def clog2(x):
    return max(0, int(math.ceil(math.log2(x)))) if x > 1 else 0


# ---- memory state ------------------------------------------------------------------------------------
class Mem:
    def __init__(self, vm, kv, cr, wr):
        self.vm = np.asarray(vm, dtype=np.uint32).copy()      # 2^VMA words
        self.kv = np.asarray(kv, dtype=np.uint32).copy()
        self.cr = np.asarray(cr, dtype=np.uint32).copy()      # [2^CRA, 2]: lo, hi
        self.wr = np.asarray(wr, dtype=np.uint16).copy()

    def copy(self):
        return Mem(self.vm, self.kv, self.cr, self.wr)


# ---- the reference -----------------------------------------------------------------------------------
def addrs(f, s, no, ni, idx=None):
    o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
    if s in "bd" and f["bhalf"]:
        i = i >> 1
    if s == "a" and f["aind"] == I.IND_I:
        i = idx[i]
    if s == "a" and f["aind"] == I.IND_O:
        o = idx[o]
    return (f[f"{s}base"] + o * f[f"{s}so"] + i * f[f"{s}si"]).reshape(-1).astype(np.int64)


def fetch(m, src, e):
    if src == I.SRC_VM:
        return ffrom(m.vm[e & ((1 << VMA) - 1)])
    if src == I.SRC_CLO:
        return ffrom(m.cr[e & ((1 << CRA) - 1), 0])
    if src == I.SRC_CHI:
        return ffrom(m.cr[e & ((1 << CRA) - 1), 1])
    return ffrom(m.wr[e & ((1 << WRA) - 1)].astype(np.uint32) << 16)


def elements(f, m):
    """Machine.su1's element pipeline on memory m: (out [no*ni], finite?, reads {vm addrs})."""
    no, ni = f["nout"], f["nin"]
    idx = None
    reads = set()
    if f["aind"]:
        cnt = ni if f["aind"] == I.IND_I else no
        ia = np.arange(f["aibase"], f["aibase"] + cnt)
        reads.update(ia.tolist())
        idx = m.vm[ia].astype(np.int64)
    ea = addrs(f, "a", no, ni, idx)
    eb = addrs(f, "b", no, ni)
    ec = (ea ^ 1) if f["cpair"] else addrs(f, "c", no, ni)
    ed = addrs(f, "d", no, ni)
    for s, e in zip("abcd", (ea, eb, ec, ed)):
        if f[f"{s}src"] == I.SRC_VM:
            reads.update(e.tolist())
    a, b, c, d = (fetch(m, f[f"{s}src"], e) for s, e in zip("abcd", (ea, eb, ec, ed)))
    imm1, imm2, imm3 = (u32f(f[k]) for k in ("imm1", "imm2", "imm3"))
    with np.errstate(all="ignore"):
        if f["arnd"]:
            a = G.to_bf16(a)
        if f["arelu"]:
            a = np.where(fbits(a) >> 31, F(0), a).astype(F)
        if f["amin"]:
            a = kmin(a, imm3)
        if f["cclip"]:
            c = kmin(kmax(c, ffrom(f["imm3"] | 0x80000000)), imm3)
        p = {I.M1_BYP: lambda: a, I.M1_AB: lambda: G.mul(a, b), I.M1_AA: lambda: G.mul(a, a),
             I.M1_AIMM: lambda: G.mul(a, imm1), I.M1_DIVB: lambda: V.div(a, b), I.M1_DIVIMM: lambda: V.div(a, imm1),
             I.M1_MAXB: lambda: np.where(okey(b) > okey(a), b, a).astype(F)}[f["m1"]]()
        p2 = {I.M2_BYP: lambda: p, I.M2_C: lambda: G.mul(p, c), I.M2_IMM: lambda: G.mul(p, imm1)}[f["m2"]]()
        par = np.tile(np.arange(ni) & 1, no)
        qd = {I.QM_OFF: None, I.QM_POS: d, I.QM_NEG: G.neg(d),
              I.QM_ALT_NP: np.where(par == 0, G.neg(d), d).astype(F),
              I.QM_ALT_PN: np.where(par == 0, d, G.neg(d)).astype(F)}[f["qm"]]
        q = None if qd is None else G.mul(c, qd)
        r = {I.AD_BYP: lambda: p2, I.AD_Q: lambda: G.add(p2, q), I.AD_C: lambda: G.add(p2, c),
             I.AD_NEGB: lambda: G.add(p2, G.neg(b)), I.AD_IMM: lambda: G.add(p2, imm2),
             I.AD_D: lambda: G.add(p2, d)}[f["ad"]]()

        def egate(x):
            mag = V.sqrt(np.maximum(np.abs(x), F(1e-6)).astype(F))
            return V.sigmoid(np.where(x < 0, G.neg(mag), mag).astype(F))

        s = {I.SFU_NONE: lambda: r, I.SFU_EXP: lambda: G.exp(r), I.SFU_RSQRT: lambda: G.rsqrt(r),
             I.SFU_SQRT: lambda: V.sqrt(r), I.SFU_SIGM: lambda: V.sigmoid(r), I.SFU_SILU: lambda: V.silu(r),
             I.SFU_SPSQRT: lambda: V.sqrt(V.softplus(r)), I.SFU_EGATE: lambda: egate(r)}[f["sfu"]]()
        t = {I.E1_BYP: lambda: s, I.E1_MULC: lambda: G.mul(s, c), I.E1_ADDC: lambda: G.add(s, c),
             I.E1_MULIMM: lambda: G.mul(s, imm2), I.E1_ADDIMM: lambda: G.add(s, imm2)}[f["e1"]]()
        u = {I.E2_BYP: lambda: t, I.E2_MULB: lambda: G.mul(t, b), I.E2_MULIMM: lambda: G.mul(t, imm1)}[f["e2"]]()
        out = np.asarray(u, dtype=F).reshape(-1)
        if f["rnd"]:
            out = G.to_bf16(out)
        stages = [a, b, c, d, p, p2, r, s, t, out] + ([q] if q is not None else [])
        # a refusal anywhere: a nonfinite value reaching a unit (the RTL faults; so does the golden's pipe)
        finite = all(np.all(np.isfinite(np.asarray(x, dtype=F))) for x in stages)
        if f["sfu"] in (I.SFU_RSQRT, I.SFU_SQRT, I.SFU_SPSQRT) and np.any(r < 0):
            finite = False
        if f["m1"] in (I.M1_DIVB, I.M1_DIVIMM):
            den = b if f["m1"] == I.M1_DIVB else np.full_like(a, imm1)
            finite = finite and not np.any(den == 0)
    return out, finite, reads


def reduce_ref(f, out):
    """R-ARITH reductions: [(address, value)]."""
    if not f["red"]:
        return [], True
    no, ni = f["nout"], f["nin"]
    with np.errstate(all="ignore"):
        v = G.mul(out, out) if f["redsq"] else out
    segs = v.reshape(1, -1) if (f["redwhole"] or f["redtree"]) else v.reshape(no, ni)
    vals = []
    for sg in segs:
        if f["red"] == I.RED_MAX:
            vals.append(sg[np.argmax(okey(sg))])
        else:
            with np.errstate(all="ignore"):
                vals.append(V.csum(sg))
    vals = np.asarray(vals, dtype=F)
    finite = bool(np.all(np.isfinite(vals))) and bool(np.all(np.isfinite(v)))
    if f["redrnd"]:
        vals = G.to_bf16(vals)
    return [(f["rbase"] + k * f["rso"], x) for k, x in enumerate(vals)], finite


def out_addrs(f):
    no, ni = f["nout"], f["nin"]
    if f["dst"] == I.DST_KVT:
        o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
        row = f["orow"] + o
        return (f["obase"] + (row >> 4) * (1 << KVT_SH) + i * 16 + (row & 15)).reshape(-1)
    return addrs(f, "o", no, ni)


def ref_op(f, m):
    """Apply op f to memory m (in place).  Returns (ok, element reads, element writes, result writes)."""
    with np.errstate(all="ignore"):
        out, finite, reads = elements(f, m)
        res, rfin = reduce_ref(f, out)
    ok = finite and rfin
    rw = set()
    for a, x in res:
        m.vm[a & ((1 << VMA) - 1)] = fbits(x)
        rw.add(a)
    ew = set()
    if f["dst"]:
        ed = out_addrs(f)
        if f["dst"] == I.DST_VM:
            m.vm[ed & ((1 << VMA) - 1)] = fbits(out)
            ew.update(ed.tolist())
        else:
            m.kv[ed & ((1 << KVA) - 1)] = fbits(G.to_bf16(out))
    return ok, reads, ew, rw


def check_ref_vs_isa(f, m):
    """The reference's element results against tools/hdc_program_v41.Machine.su1 (no reduction)."""
    import hdc_program_v41 as P
    mach = P.Machine.__new__(P.Machine)
    mach.vm = ffrom(m.vm.copy())
    mach.kv = ffrom(m.kv.copy())
    mach.crom = ffrom(m.cr.copy())
    mach.wrom = m.wr.copy()
    mach.dyn = [0] * 32
    g = {n: 0 for n, _ in I.FIELDS}
    ren = {"nout": "su_nout", "nin": "su_nin", "asrc": "a_src", "bsrc": "b_src", "csrc": "c_src", "dsrc": "d_src",
           "abase": "a_base", "aso": "a_so", "asi": "a_si", "aibase": "a_ibase", "aind": "a_ind",
           "bbase": "b_base", "bso": "b_so", "bsi": "b_si", "bhalf": "b_half", "cbase": "c_base", "cso": "c_so",
           "csi": "c_si", "cpair": "c_pair", "dbase": "d_base", "dso": "d_so", "dsi": "d_si", "arnd": "a_rnd",
           "arelu": "a_relu", "amin": "a_min", "cclip": "c_clip", "obase": "o_base", "oso": "o_so", "osi": "o_si",
           "m1": "m1", "m2": "m2", "qm": "qm", "ad": "ad", "sfu": "sfu", "e1": "e1", "e2": "e2", "rnd": "rnd",
           "dst": "dst", "imm1": "imm1", "imm2": "imm2", "imm3": "imm3"}
    for k, v in ren.items():
        g[v] = f[k]
    g["red"] = 0
    if f["dst"] == I.DST_KVT:
        return None                              # Machine.su1 takes the transposed-KV row from DYN
    if f["dst"] == 0:
        g["dst"] = I.DST_VM
        g["o_base"], g["o_so"], g["o_si"] = 60000, f["nin"], 1
    mach.vm = mach.vm.copy()
    with np.errstate(all="ignore"):
        P.Machine.su1(mach, g)
    mine = m.copy()
    fm = dict(f, red=0)
    if f["dst"] == 0:
        fm.update(dst=I.DST_VM, obase=60000, oso=f["nin"], osi=1)
    ref_op(fm, mine)
    return bool(np.array_equal(fbits(mach.vm), mine.vm) and np.array_equal(fbits(mach.kv), mine.kv))


# ---- the reducer's order, modelled: the claim that lanes reproduce csum -------------------------------------
def unit_sum(x, S, width):
    """The reducer's order on one segment x laid out in slots of S lanes (S >= 8, a power of two) of a
    `width`-lane vector (ot_hdc_v41x_vec_red): per vector, 7-add chains over 8 adjacent lanes from the
    lane's first element, a pairwise tree over the vector's width/8 chunk sums (lanes past the segment +0),
    tapped at the slot's level; across vectors (a spanning segment, S = width) a streaming binary counter:
    level t holds a left operand until its right sibling arrives, the LAST item combines with what is
    held or passes.  Returns the result bit pattern."""
    x = np.asarray(x, dtype=F)
    n = len(x)
    nv = max(1, -(-n // S))
    vsum = []
    for v in range(nv):
        lanes = np.zeros(width, dtype=F)
        seg = x[v * S:(v + 1) * S]
        lanes[:len(seg)] = seg
        ch = []
        for c in range(width // 8):
            acc = lanes[8 * c]
            for j in range(1, 8):
                acc = G.add(acc, lanes[8 * c + j])
            ch.append(F(acc))
        lvl, size = ch, 8
        while size < S:                                # tree level log2(size / 8): nodes of `size` lanes
            lvl = [F(G.add(lvl[2 * i], lvl[2 * i + 1])) for i in range(len(lvl) // 2)]
            size *= 2
        vsum.append(lvl[0])
    if nv == 1:
        return fbits(vsum[0])
    L = clog2(nv)
    held = [None] * (L + 1)
    out = None
    for v, item in enumerate(vsum):
        last = v == nv - 1
        for t in range(1, L + 1):
            if held[t] is not None:
                item, held[t] = F(G.add(held[t], item)), None
            elif last:
                pass
            else:
                held[t] = item
                item = None
                break
        if last:
            out = item
    return fbits(out)


def check_reducer_claim(rng, trials=3000):
    """unit_sum == hdc_golden_v41.csum on random segments, slot sizes and widths (bit for bit)."""
    bad, cases = 0, 0
    for _ in range(trials):
        width = int(rng.choice([8, 16, 64, 256, 1024]))
        n = int(rng.integers(1, 40 * width if rng.random() < 0.3 else 2 * width))
        S = min(width, 1 << clog2(max(n, 8)))
        x = rand_vals(rng, n, "any")
        cases += 1
        if unit_sum(x, S, width) != fbits(V.csum(x)):
            bad += 1
    return dict(segments=cases, mismatches=bad)


# ---- the unit's layout (mirrors ot_hdc_v41x_vec's set-up) -------------------------------------------------
def layout(f, N, M):
    no, ni = f["nout"], f["nin"]
    scalar = f["sfu"] in SCALAR_SFU
    sfuc = f["sfu"] in VEC_SFU or f["m1"] in (I.M1_DIVB, I.M1_DIVIMM)
    vw = 1 if scalar else (M if sfuc else N)
    lvw = int(math.log2(vw))
    red = f["red"] != 0
    mk = (1 << 24) - 1
    half = f["bhalf"]
    even = ni % 2 == 0
    cand = (not red) or f["redwhole"] or f["redtree"]
    ok = (f["aind"] == 0 and f["dst"] != I.DST_KVT and (even or not (half or f["qm"] in (I.QM_ALT_NP, I.QM_ALT_PN)))
          and f["aso"] == (ni * f["asi"]) & mk
          and f["bso"] == ((ni >> 1 if half else ni) * f["bsi"]) & mk
          and (f["cpair"] or f["cso"] == (ni * f["csi"]) & mk)
          and f["dso"] == ((ni >> 1 if half else ni) * f["dsi"]) & mk
          and (f["dst"] == 0 or f["oso"] == (ni * f["osi"]) & mk))
    flat = cand and ok
    wnf = red and (f["redwhole"] or f["redtree"]) and not ok and no > 1
    bad = wnf and ni % 8 != 0
    ni_f, no_f = (no * ni, 1) if flat else (ni, no)
    smin = 8 if red else 1
    if wnf:
        tz = (ni & -ni).bit_length() - 1
        ls = min(lvw, tz)
    else:
        ls = min(lvw, clog2(max(ni_f, smin)))
    S = 1 << ls
    packed = (not wnf) and ni_f <= S
    nsh = (lvw - ls) if (packed and (not red or pow2(f["rso"]))) else 0
    span = red and not packed
    nvs = no_f * (ni_f >> ls) if wnf else -(-ni_f // S)
    L = clog2(nvs)
    gstr = f["asi"] if f["aind"] == I.IND_I else f["aso"]
    bad = bad or (red and scalar) or (span and L > 6) or (f["aind"] and not pow2(gstr))
    # vectors: lanes -> original (o, i)
    vecs = []
    o_v = i_v = 0
    nslot = 1 << nsh
    use = 1 << (ls + nsh)
    while True:
        lanes = np.arange(use)
        d_o, d_i = lanes >> ls, lanes & (S - 1)
        oo, ii = o_v + d_o, i_v + d_i
        live = (oo < no_f) & (ii < ni_f)
        if flat:
            g = ii[live]
            vecs.append((g // ni, g % ni))
        else:
            vecs.append((oo[live], ii[live]))
        wrap = packed or (i_v + S >= ni_f)
        last = wrap and (o_v + nslot >= no_f)
        if last:
            break
        if wrap:
            o_v, i_v = o_v + nslot, 0
        else:
            i_v += S
    gather = f["aind"] != 0
    dF = D_FETCH_G if gather else D_FETCH
    dM = dF + D_PRE + (D_DIV if f["m1"] in (I.M1_DIVB, I.M1_DIVIMM) else D_M1)
    dS = dM + 2 * D_STAGE + SFU_DEPTH[f["sfu"]]
    dP = dS + 2 * D_STAGE + D_OUT
    lt = ls - 3 if red else 0
    dR = dP + 26 + 3 * lt + (3 * L if span else 0)
    return dict(flat=flat, wnf=wnf, bad=bad, vw=vw, ls=ls, S=S, nsh=nsh, packed=packed, span=span, L=L, lt=lt, vecs=vecs,
                dP=dP, dR=dR, nv=len(vecs))


def elem_index(f, oo, ii):
    return oo * f["nin"] + ii


def vec_reads_writes(f, lay, m):
    """Per vector: the vector-memory addresses it reads, and (dst VM) writes."""
    no, ni = f["nout"], f["nin"]
    idx = None
    if f["aind"]:
        cnt = ni if f["aind"] == I.IND_I else no
        idx = m.vm[f["aibase"]:f["aibase"] + cnt].astype(np.int64)
    ea = addrs(f, "a", no, ni, idx)
    eb = addrs(f, "b", no, ni)
    ec = (ea ^ 1) if f["cpair"] else addrs(f, "c", no, ni)
    ed = addrs(f, "d", no, ni)
    eo = out_addrs(f) if f["dst"] == I.DST_VM else None
    rs, ws = [], []
    for oo, ii in lay["vecs"]:
        k = elem_index(f, oo, ii)
        r = set()
        for s, e in zip("abcd", (ea, eb, ec, ed)):
            if f[f"{s}src"] == I.SRC_VM:
                r.update(e[k].tolist())
        if f["aind"]:
            r.update((f["aibase"] + (ii if f["aind"] == I.IND_I else oo)).tolist())
        rs.append(r)
        ws.append(set(eo[k].tolist()) if eo is not None else set())
    return rs, ws


# ---- programs: dependences and chaining ---------------------------------------------------------------------
def schedule(ops, mem0, N, M, chain=True):
    """Run the reference over ops (in order), and give each op its chaining fields and bench waits.
    Returns (final memory, [op], [layout], ok)."""
    m = mem0.copy()
    lays, hist = [], []           # hist: per op (vector writes list, result writes, seq)
    out_ops = []
    ok_all = True
    for k, f in enumerate(ops):
        f = dict(f)
        lay = layout(f, N, M)
        rs, ws = vec_reads_writes(f, lay, m)
        reads = set().union(*rs) if rs else set()
        # producers: latest op whose element writes this op reads; ops whose results it reads
        elem_dep = [j for j in range(len(hist)) if hist[j][0] & reads]
        res_dep = [j for j in range(len(hist)) if hist[j][1] & reads]
        f.setdefault("ch_src", CH_NONE)
        if f["ch_src"] != CH_EXT:
            f["ch_src"], f["ch_seq"], f["ch_lead"], f["ch_mul"] = CH_NONE, 0, 0, 0
        if res_dep:
            j = max(res_dep)
            f["w_rseq_en"], f["w_rseq"] = 1, j & 255
        if elem_dep and f["ch_src"] != CH_EXT:
            j = max(elem_dep)
            if not chain:
                f["w_dseq_en"], f["w_dseq"] = 1, j & 255
            elif j == k - 1:
                pw = hist[j][2]
                writer = {}
                for v, w in enumerate(pw):
                    for a in w:
                        writer[a] = v
                older = any(hist[jj][0] & reads for jj in range(j))
                need = []
                for r in rs:
                    n = max((writer.get(a, -1) for a in r), default=-1) + 1
                    need.append(max(n, 1 if older else 0))
                nP, nC = len(pw), len(need)
                mul = min(0xFFFF, int(round(256 * nP / nC))) if nC > 1 else 0
                lead = max(0, max(n - (v * mul >> 8) for v, n in enumerate(need)))
                f["ch_src"], f["ch_seq"], f["ch_lead"], f["ch_mul"] = CH_SELF, j & 255, min(lead, 0xFFFF), mul
            else:
                f["ch_src"], f["ch_seq"] = CH_SELF, j & 255
        ok, _, ew, rw = ref_op(f, m)
        ok_all = ok_all and ok and not lay["bad"]
        hist.append((ew, rw, [w for w in ws]))
        lays.append(lay)
        out_ops.append(f)
    return m, out_ops, lays, ok_all


# ---- random programs ---------------------------------------------------------------------------------------
def rand_vals(rng, n, kind="any"):
    if kind == "exp":
        v = rng.uniform(-20, 20, n)
    elif kind == "pos":
        v = np.exp(rng.uniform(-8, 8, n))
    elif kind == "small":
        v = rng.uniform(-3, 3, n)
    else:
        v = rng.standard_normal(n) * np.exp2(rng.integers(-6, 6, n))
    v = v.astype(F)
    # sprinkle exact zeros, BF16-exact values and ties
    z = rng.random(n)
    v[z < 0.02] = F(0)
    t = (z >= 0.02) & (z < 0.06)
    v[t] = G.to_bf16(v[t])
    return v


class Alloc:
    def __init__(self, lo, hi):
        self.p, self.hi = lo, hi

    def get(self, n, align=1):
        self.p = -(-self.p // align) * align
        a = self.p
        self.p += n
        assert self.p < self.hi, "vector memory exhausted"
        return a


def random_program(rng, N, M, nops, alloc):
    """Random ops: each reads fresh or earlier-written regions and writes a fresh region.
    Returns (ops, [(address, values)] initial vector memory contents)."""
    init = []
    regions = []                                  # (base, extent) written by an earlier op: readable
    ops = []

    def fresh(n, kind="any"):
        a = alloc.get(n)
        init.append((a, rand_vals(rng, n, kind)))
        return a

    for k in range(nops):
        f = op_defaults()
        cls = str(rng.choice(["lin", "lin", "lin", "div", "exp", "sig", "silu", "scalar", "gather", "pair", "red",
                              "red", "tree", "kvt", "hcp"]))
        big = rng.random() < 0.3
        no = int(rng.integers(1, 6 if big else 12))
        ni = int(rng.integers(1, (6 * N if big else 3 * N // 2) + 1))
        if cls == "scalar":
            no, ni = int(rng.integers(1, 4)), int(rng.integers(1, 20))
        if cls == "kvt":
            ni = min(ni, 32)
        if cls == "hcp":                      # hc_post's shape: a broadcast row, a per-row scalar, rows of whole chunks
            no, ni = int(rng.integers(2, 6)), 8 * int(rng.integers(1, 3 * N // 8 + 2))
        if cls == "pair" and ni % 2:
            ni += 1
        red = 0
        if cls in ("red", "tree") or (cls not in ("scalar", "kvt") and rng.random() < 0.15):
            red = int(rng.choice([I.RED_SUM, I.RED_SUM, I.RED_MAX, I.RED_SEQ])) if cls != "tree" else I.RED_SUM
        if cls == "hcp":
            red = I.RED_SUM
        if red == I.RED_SEQ:
            ni = min(ni, 8)
        vsfu = cls in ("exp", "sig", "silu", "div")
        vw = M if vsfu else N
        if red:
            whole = cls in ("tree", "hcp")
            tot = no * ni if whole else ni
            if tot > 64 * vw:
                ni = max(8, (64 * vw) // (no if whole else 1)) // 8 * 8
        while no * ni > 3000:
            ni = max(1, ni // 2)
            if cls == "pair" and ni % 2:
                ni += 1
        f["nout"], f["nin"] = no, ni
        vkind = {"exp": "exp", "sig": "small", "silu": "small"}.get(cls, "any")
        contig = cls == "tree" or rng.random() < 0.6

        def stream(s, kind="any"):
            src = I.SRC_VM
            if s == "a" and rng.random() < 0.12:
                src = I.SRC_WROM
            elif rng.random() < 0.15:
                src = int(rng.choice([I.SRC_CLO, I.SRC_CHI]))
            si = 1 if (contig or rng.random() < 0.5) else int(rng.integers(1, 4))
            so = ni * si if contig else int(rng.choice([0, ni * si + int(rng.integers(0, 5))]))
            ext = (no - 1) * so + (ni - 1) * si + 1
            if src == I.SRC_VM and regions and rng.random() < 0.45:
                base, n = regions[int(rng.integers(len(regions)))]
                if ext <= n:
                    return src, base, so, si
            if src == I.SRC_VM:
                base = fresh(ext, kind)
            else:
                base = int(rng.integers(0, (1 << (WRA if src == I.SRC_WROM else CRA)) - ext))
            return src, base, so, si

        for s in "abcd":
            f[f"{s}src"], f[f"{s}base"], f[f"{s}so"], f[f"{s}si"] = stream(s, vkind)
        f["arnd"] = int(rng.random() < 0.15)
        f["arelu"] = int(rng.random() < 0.1)
        f["amin"] = int(rng.random() < 0.08)
        f["cclip"] = int(rng.random() < 0.08)
        f["imm3"] = f32u(rng.uniform(0.5, 4))
        f["imm1"] = f32u(rng.uniform(-2, 2))
        f["imm2"] = f32u(rng.uniform(-2, 2))
        f["m1"] = int(rng.choice([I.M1_BYP, I.M1_AB, I.M1_AA, I.M1_AIMM, I.M1_MAXB]))
        f["m2"] = int(rng.choice([I.M2_BYP, I.M2_C, I.M2_IMM]))
        f["qm"] = int(rng.choice([I.QM_OFF, I.QM_OFF, I.QM_POS, I.QM_NEG]))
        f["ad"] = int(rng.choice([I.AD_BYP, I.AD_Q, I.AD_C, I.AD_NEGB, I.AD_IMM, I.AD_D]))
        if f["ad"] == I.AD_Q and f["qm"] == I.QM_OFF:
            f["qm"] = I.QM_POS
        f["e1"] = int(rng.choice([I.E1_BYP, I.E1_MULC, I.E1_ADDC, I.E1_MULIMM, I.E1_ADDIMM]))
        f["e2"] = int(rng.choice([I.E2_BYP, I.E2_MULB, I.E2_MULIMM]))
        f["rnd"] = int(rng.random() < 0.3)
        if cls == "div":
            f["m1"] = int(rng.choice([I.M1_DIVB, I.M1_DIVIMM]))
            if f["m1"] == I.M1_DIVB:
                f["bsrc"], f["bbase"], f["bso"], f["bsi"] = I.SRC_VM, fresh(no * ni, "pos"), ni, 1
                if not contig:
                    f["bso"] = ni + 1
                    f["bbase"] = fresh(no * (ni + 1), "pos")
        if cls in ("exp", "sig", "silu"):
            f["sfu"] = {"exp": I.SFU_EXP, "sig": I.SFU_SIGM, "silu": I.SFU_SILU}[cls]
            f["m1"], f["m2"], f["qm"] = I.M1_BYP, I.M2_BYP, I.QM_OFF
            f["ad"] = int(rng.choice([I.AD_BYP, I.AD_NEGB, I.AD_IMM]))
            f["arnd"] = f["arelu"] = f["amin"] = 0
            if f["asrc"] != I.SRC_VM:
                f["asrc"], f["abase"] = I.SRC_VM, fresh((no - 1) * f["aso"] + (ni - 1) * f["asi"] + 1, vkind)
        if cls == "scalar":
            f["sfu"] = int(rng.choice(SCALAR_SFU))
            f["m1"], f["m2"], f["qm"], f["ad"], f["e2"] = 0, 0, 0, 0, 0
            f["e1"] = int(rng.choice([0, 3]))
            kind = "small" if f["sfu"] in (I.SFU_SPSQRT, I.SFU_EGATE) else "pos"
            f["asrc"], f["abase"], f["aso"], f["asi"] = I.SRC_VM, fresh(no * ni, kind), ni, 1
            f["arnd"] = f["arelu"] = f["amin"] = 0
        if cls == "gather":
            f["aind"] = int(rng.choice([I.IND_I, I.IND_O]))
            cnt = ni if f["aind"] == I.IND_I else no
            st = int(rng.choice([1, 2, 4, 16]))
            rows = int(rng.integers(2, 40))
            if f["aind"] == I.IND_I:
                f["asi"], f["aso"] = st, rows * st * 2
                tab = fresh(no * f["aso"] + rows * st + 1)
            else:
                f["asi"] = 1
                f["aso"] = st * (1 << clog2(max(ni, 1)))
                tab = fresh(rows * f["aso"] + ni)
            ids = rng.integers(0, rows, cnt)
            f["asrc"], f["abase"] = I.SRC_VM, tab
            f["aibase"] = alloc.get(cnt)
            init.append((f["aibase"], ffrom(ids.astype(np.uint32))))
        if cls == "pair":
            f["cpair"], f["bhalf"] = 1, 1
            f["qm"] = int(rng.choice([I.QM_ALT_NP, I.QM_ALT_PN]))
            f["asrc"], f["abase"], f["aso"], f["asi"] = I.SRC_VM, fresh(no * ni), ni, 1
            f["bsrc"], f["bbase"], f["bso"], f["bsi"] = I.SRC_VM, fresh(no * ni // 2 + 1, "small"), ni // 2, 1
            f["dsrc"], f["dbase"], f["dso"], f["dsi"] = I.SRC_VM, fresh(no * ni // 2 + 1, "small"), ni // 2, 1
            f["m1"], f["m2"], f["ad"] = I.M1_BYP, I.M2_C, I.AD_Q
            f["csrc"] = I.SRC_VM
        if cls == "hcp":
            f["asrc"], f["abase"], f["aso"], f["asi"] = I.SRC_VM, fresh(ni, "small"), 0, 1
            f["bsrc"], f["bbase"], f["bso"], f["bsi"] = I.SRC_VM, fresh(no, "small"), 1, 0
            f["csrc"], f["cbase"], f["cso"], f["csi"] = I.SRC_VM, fresh(no * ni, "small"), ni, 1
            f["m1"], f["m2"], f["qm"], f["ad"], f["e1"], f["e2"] = I.M1_AB, I.M2_BYP, I.QM_OFF, I.AD_C, 0, 0
            f["arnd"] = f["arelu"] = f["amin"] = f["cclip"] = 0
        if red:
            f["red"] = red
            f["redsq"] = int(red == I.RED_SUM and rng.random() < 0.4)
            f["redrnd"] = int(rng.random() < 0.3)
            if cls == "hcp":
                f["redtree"] = 1
            if cls == "tree":
                f["redtree" if rng.random() < 0.5 else "redwhole"] = 1
            nres = 1 if (f["redwhole"] or f["redtree"]) else no
            f["rso"] = int(rng.choice([1, 1, 2, 3]))
            f["rbase"] = alloc.get(nres * f["rso"] + 1)
        dsel = rng.random()
        if cls == "kvt":
            f["dst"] = I.DST_KVT
            f["orow"] = int(rng.integers(0, 48))
            f["obase"] = int(rng.integers(0, 4)) << (KVT_SH + 2)
        elif dsel < 0.1 and not red:
            f["dst"] = I.DST_NONE
        elif dsel < 0.2:
            f["dst"] = I.DST_KV
            f["osi"], f["oso"] = 1, ni
            f["obase"] = int(rng.integers(0, (1 << KVA) - no * ni - 1))
        else:
            f["dst"] = I.DST_VM
            osi = 1 if contig else int(rng.integers(1, 3))
            f["osi"], f["oso"] = osi, ni * osi
            ext = (no - 1) * f["oso"] + (ni - 1) * osi + 1
            f["obase"] = alloc.get(ext + 1)
            regions.append((f["obase"], ext))
        ops.append(f)
    return ops, init


def fresh_mem(rng, init):
    vm = fbits(rand_vals(rng, 1 << VMA))
    for a, vals in init:
        vm[a:a + len(vals)] = fbits(vals)
    kv = fbits(rand_vals(rng, 1 << KVA))
    cr = np.stack([fbits(rand_vals(rng, 1 << CRA, "small")), fbits(rand_vals(rng, 1 << CRA, "small"))], axis=1)
    wr = (fbits(rand_vals(rng, 1 << WRA, "small")) >> 16).astype(np.uint16)
    return Mem(vm, kv, cr, wr)


# ---- bench files, build, run ----------------------------------------------------------------------------
def write_hex(path, words, width):
    nd = width // 4
    with open(path, "w") as fh:
        fh.write("\n".join(format(int(w), f"0{nd}x") for w in words))
        fh.write("\n")


def write_case(d: Path, mem: Mem, ops, xb=None):
    d.mkdir(parents=True, exist_ok=True)
    write_hex(d / "vm.hex", mem.vm, 32)
    write_hex(d / "kv.hex", mem.kv, 32)
    write_hex(d / "cr.hex", (mem.cr[:, 1].astype(np.uint64) << 32) | mem.cr[:, 0].astype(np.uint64), 64)
    write_hex(d / "wr.hex", mem.wr, 16)
    write_hex(d / "prog.hex", [encode(f) for f in ops] or [0], ((PW + 3) // 4) * 4)
    write_hex(d / "xb.hex", xb if xb is not None else [0], 32)


def read_hex(path):
    return np.array([int(x, 16) for x in Path(path).read_text().split() if not x.startswith("//")], dtype=np.uint64)


def build(N, M, obj: Path, pmax=4096):
    write_fields_svh()
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-UNOPTFLAT", "--top-module", "tb_hdc_v41x_vec", "--prefix", "Vtb", "-Mdir", str(obj),
           f"-GN={N}", f"-GM={M}", f"-GPMAX={pmax}", f"-GVMA={VMA}", f"-GKVA={KVA}", f"-GCRA={CRA}", f"-GWRA={WRA}", f"-GXBA={XBA}", f"-I{ROOT / 'rtl/test'}",
           *map(str, LIB), *map(str, RTL), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout[-4000:] + r.stderr[-4000:])
    return obj / "Vtb", time.time() - t0


def run_case(exe: Path, d: Path, nops, x=None, timeout=36000):
    args = [str(exe), f"+VM={d / 'vm.hex'}", f"+KV={d / 'kv.hex'}", f"+CR={d / 'cr.hex'}", f"+WR={d / 'wr.hex'}",
            f"+PROG={d / 'prog.hex'}", f"+XB={d / 'xb.hex'}", f"+VMO={d / 'vmo.hex'}", f"+KVO={d / 'kvo.hex'}",
            f"+NPROG={nops}"]
    if x:
        args += [f"+XVEC={x['vec']}", f"+XNV={x['nv']}", f"+XPER={x['per']}", f"+XBASE={x['base']}",
                 f"+XSEQ={x['seq']}"]
    t0 = time.time()
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    tr = parse_trace(r.stdout)
    tr["wall_s"] = time.time() - t0
    tr["vm"] = read_hex(d / "vmo.hex").astype(np.uint32) if (d / "vmo.hex").exists() else None
    tr["kv"] = read_hex(d / "kvo.hex").astype(np.uint32) if (d / "kvo.hex").exists() else None
    return tr


def parse_trace(text):
    acc, emits, rets, ress, xs = {}, {}, {}, {}, []
    faults = orders = 0
    end = None
    for line in text.splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "A":
            acc[int(p[2])] = int(p[1])
        elif p[0] == "C":
            c = int(p[1])
            for tok in p[2:]:
                if tok[0] == "e":
                    emits.setdefault(int(tok[1:]), []).append(c)
                elif tok[0] == "r":
                    rets.setdefault(int(tok[1:]), []).append(c)
                elif tok[0] == "s":
                    ress.setdefault(int(tok[1:]), []).append(c)
        elif p[0] == "F":
            faults += 1
        elif p[0] == "O":
            orders += 1
        elif p[0] == "X":
            xs.append(int(p[1]))
        elif p[0] == "END":
            end = (int(p[1]), p[2] if len(p) > 2 else "")
    return dict(acc=acc, emits=emits, rets=rets, ress=ress, faults=faults, orders=orders, end=end, xs=xs)


def compare(tr, mref):
    ok_end = tr["end"] is not None and tr["end"][1] == "ok"
    vm_bad = int(np.sum(tr["vm"] != mref.vm)) if tr["vm"] is not None else -1
    kv_bad = int(np.sum(tr["kv"] != mref.kv)) if tr["kv"] is not None else -1
    return dict(ended=ok_end, vm_mismatch_words=vm_bad, kv_mismatch_words=kv_bad, faults=tr["faults"],
                order_faults=tr["orders"], cycles=tr["end"][0] if tr["end"] else None,
                pass_=bool(ok_end and vm_bad == 0 and kv_bad == 0 and tr["faults"] == 0 and tr["orders"] == 0))


def seqmap(k):
    return k & 255


# ---- campaigns -----------------------------------------------------------------------------------------------
def random_campaign(exe, N, M, seeds, nops, scratch: Path, chain=True):
    res = []

    def one(seed):
        rng = np.random.default_rng(seed)
        alloc = Alloc(64, (1 << VMA) - 64)
        ops, init = random_program(rng, N, M, nops, alloc)
        mem0 = fresh_mem(rng, init)
        mref, sops, lays, ok = schedule(ops, mem0, N, M, chain=chain)
        # drop ops the reference refuses (nonfinite) or the unit cannot lay out, and reschedule
        keep = []
        mm = mem0.copy()
        for f in ops:
            lay = layout(f, N, M)
            t = mm.copy()
            okf, *_ = ref_op(dict(f), t)
            if okf and not lay["bad"]:
                keep.append(f)
                mm = t
        mref, sops, lays, ok = schedule(keep, mem0, N, M, chain=chain)
        d = scratch / f"rand_{N}_{seed}"
        write_case(d, mem0, sops)
        tr = run_case(exe, d, len(sops))
        c = compare(tr, mref)
        classes = {}
        for f in sops:
            key = ("sfu%d" % f["sfu"]) if f["sfu"] else ("div" if f["m1"] in (4, 5) else "lin")
            classes[key] = classes.get(key, 0) + 1
        chained = sum(1 for f in sops if f["ch_src"] == CH_SELF and f.get("ch_mul", 0) > 0)
        r = dict(seed=seed, ops=len(sops), vectors=sum(l["nv"] for l in lays),
                    elements=int(sum(f["nout"] * f["nin"] for f in sops)),
                    reductions=sum(1 for f in sops if f["red"]), gathers=sum(1 for f in sops if f["aind"]),
                    pair_ops=sum(1 for f in sops if f["cpair"]), kvt_ops=sum(1 for f in sops if f["dst"] == 3),
                    flattened=sum(1 for l in lays if l["flat"]), spanning=sum(1 for l in lays if l["span"]),
                    packed_multi=sum(1 for l in lays if l["packed"] and l["nsh"] > 0),
                    chained_by_credit=chained, classes=classes, **c)
        print(f"  random N={N} seed={seed} ops={len(sops)} pass={c['pass_']} vm_bad={c['vm_mismatch_words']} "
              f"kv_bad={c['kv_mismatch_words']} faults={c['faults']} order={c['order_faults']} cycles={c['cycles']}",
              flush=True)
        return r
    with ThreadPoolExecutor(max_workers=min(8, len(seeds))) as ex:
        res = list(ex.map(one, seeds))
    return res


# ---- the reduced vehicle's stream ops -------------------------------------------------------------------------
def vehicle_records():
    """Run the ISA-level simulator over the reduced vehicle's one-token program and record, before every
    stream op, its DYN-resolved fields and the vector memory and KV SRAM it starts from."""
    import hdc_program_v41 as P
    model = V.Model()
    prompt, _ = V.prompt_and_expected()
    lay = P.Layout(model)
    prog = P.Builder(lay).build()
    token, pos = prompt[-1], len(prompt) - 1
    st = P.golden_prefill(model, prompt[:-1])
    kv, vm = lay.kv_image(st), lay.vm_image(st, pos)
    mach = P.Machine(lay, kv, vm)
    mach.tokens = list(prompt[:-1])
    recs = []
    orig = P.Machine.su1

    def rec(self, f):
        recs.append((dict(f), list(self.dyn), fbits(self.vm).copy(), fbits(self.kv).reshape(-1).copy()))
        orig(self, f)
    P.Machine.su1 = rec
    try:
        mach.run(prog, token, pos)
    finally:
        P.Machine.su1 = orig
    cr = fbits(np.asarray(lay.crom, dtype=F).reshape(-1, 2))
    wrom = mach.wrom.astype(np.uint16)
    return recs, cr, wrom, dict(position=int(pos), token=int(token), program_instructions=len(prog),
                                stream_ops=sum(1 for f in prog if f["unit"] == I.UNIT_SU))


def resolve(f, dyn):
    """An ISA stream op with its DYN selections added (the sequencer's job) -> the bench's op."""
    d = lambda k: dyn[f.get(k, 0)]
    g = op_defaults()
    g.update(nout=f["su_nout"] + d("su_d_nout"), nin=f["su_nin"] + d("su_d_nin"))
    for s in "abcd":
        g[f"{s}src"], g[f"{s}base"] = f[f"{s}_src"], f[f"{s}_base"] + d(f"{s}_d")
        g[f"{s}so"], g[f"{s}si"] = f[f"{s}_so"], f[f"{s}_si"]
    g.update(aibase=f["a_ibase"], aind=f["a_ind"], bhalf=f["b_half"], cpair=f["c_pair"], arnd=f["a_rnd"],
             arelu=f["a_relu"], amin=f["a_min"], cclip=f["c_clip"], m1=f["m1"], m2=f["m2"], qm=f["qm"], ad=f["ad"],
             sfu=f["sfu"], e1=f["e1"], e2=f["e2"], rnd=f["rnd"], dst=f["dst"], oso=f["o_so"], osi=f["o_si"],
             red=f["red"], redsq=f["red_sq"], redwhole=f["red_whole"], redtree=f["red_tree"], redrnd=f["red_rnd"],
             rbase=f["r_base"], rso=f["r_so"], imm1=f["imm1"], imm2=f["imm2"], imm3=f["imm3"])
    if f["dst"] == I.DST_KVT:
        g.update(obase=f["o_base"], orow=d("o_d"))
    else:
        g.update(obase=f["o_base"] + d("o_d"))
    return g


def rebase_rom(g, wrom, win):
    """An op reading the BF16 weight ROM gets a copy of the rows it reads at the bench ROM's `win`, and
    its A base moved there (the op is address-relative)."""
    if g["asrc"] != I.SRC_WROM:
        return g, None
    lo = g["abase"]
    ext = (g["nout"] - 1) * g["aso"] + (g["nin"] - 1) * g["asi"] + 1
    return dict(g, abase=win), (win, wrom[lo:lo + ext])


def vehicle_cases(recs, cr, wrom, batch=48):
    """Batches of consecutive stream ops, each run from the vector memory and KV SRAM the ISA simulator
    had before the batch's first op."""
    cases = []
    for b0 in range(0, len(recs), batch):
        grp = recs[b0:b0 + batch]
        f0, dyn0, vm0, kv0 = grp[0]
        vm = np.zeros(1 << VMA, dtype=np.uint32)
        vm[:len(vm0)] = vm0
        kv = np.zeros(1 << KVA, dtype=np.uint32)
        kv[:len(kv0)] = kv0
        crm = np.zeros((1 << CRA, 2), dtype=np.uint32)
        crm[:len(cr)] = cr
        wr = np.zeros(1 << WRA, dtype=np.uint16)
        ops, win = [], 0
        for f, dyn, _, _ in grp:
            g = resolve(f, dyn)
            if g["nout"] == 0 or g["nin"] == 0:
                continue
            g, cp = rebase_rom(g, wrom, win)
            if cp is not None:
                wr[cp[0]:cp[0] + len(cp[1])] = cp[1]
                win += len(cp[1])
            ops.append(g)
        cases.append((b0, Mem(vm, kv, crm, wr), ops))
    return cases


def filter_ok(ops, mem0, N, M):
    """Drop ops the reference refuses (a nonfinite operand) or the unit cannot lay out; keep the rest."""
    keep, drop = [], []
    m = mem0.copy()
    for f in ops:
        t = m.copy()
        okf, *_ = ref_op(dict(f), t)
        lay = layout(f, N, M)
        if okf and not lay["bad"]:
            keep.append(f)
            m = t
        else:
            drop.append(("refused" if not okf else "layout", f["sfu"], f["red"]))
    return keep, drop


def run_program(exe, d, mem0, ops, N, M, chain=True, x=None, xb=None):
    mref, sops, lays, ok = schedule(ops, mem0, N, M, chain=chain)
    write_case(d, mem0, sops, xb)
    tr = run_case(exe, d, len(sops), x)
    c = compare(tr, mref)
    return c, tr, sops, lays


def vehicle_campaign(exe, N, M, scratch, recs, cr, wrom, limit=None):
    cases = vehicle_cases(recs[:limit] if limit else recs, cr, wrom)

    def one(case):
        b0, mem0, ops = case
        keep, drop = filter_ok(ops, mem0, N, M)
        c, tr, sops, lays = run_program(exe, scratch / f"veh_{N}_{b0}", mem0, keep, N, M)
        return dict(first_op=b0, ops=len(sops), dropped=len(drop), drop_reasons=sorted(set(map(str, drop))),
                    vectors=sum(l["nv"] for l in lays), elements=int(sum(f["nout"] * f["nin"] for f in sops)),
                    reductions=sum(1 for f in sops if f["red"]), red_tree=sum(1 for f in sops if f["redtree"]),
                    whole_unflattened=sum(1 for l in lays if l["wnf"]),
                    chained_by_credit=sum(1 for f in sops if f["ch_src"] == CH_SELF and f["ch_lead"] > 0), **c)
    with ThreadPoolExecutor(max_workers=8) as ex:
        out = list(ex.map(one, cases))
    return out


# ---- performance programs ----------------------------------------------------------------------------------
def op_trace(tr, k):
    s = seqmap(k)
    return tr["emits"].get(s, []), tr["rets"].get(s, []), tr["ress"].get(s, [])


def perf_hcpost(exe, N, M, scratch, rng, dim=None):
    """The hyper-connection post-mix at the shipped shape: 4 copies x dim, dim = 5 N (5,120 at N = 1,024), so
    each op is 20,480 elements.  Four chained ops as hdc_program_v41.Builder.hc_post issues them: three mixes
    into T, then the output with the sum of squares over all 4 x dim elements (red_tree: one csum)."""
    dim = dim or 5 * N
    al = Alloc(64, (1 << VMA) - 64)
    H = al.get(4 * dim)
    Y = al.get(dim)
    T = al.get(4 * dim)
    comb = al.get(16)
    post = al.get(4)
    ssx = al.get(4)
    init = [(H, rand_vals(rng, 4 * dim, "small")), (Y, rand_vals(rng, dim, "small")),
            (comb, rand_vals(rng, 16, "small")), (post, rand_vals(rng, 4, "small"))]
    mem0 = fresh_mem(rng, init)
    base = op_defaults()
    base.update(nout=4, nin=dim, asi=1, dst=I.DST_VM, obase=T, oso=dim, osi=1)
    ops = [dict(base, abase=H, bbase=comb, bso=1, m1=I.M1_AB, cbase=H + dim, csi=1, dbase=comb + 4, dso=1,
                qm=I.QM_POS, ad=I.AD_Q)]
    for j in (2, 3):
        ops.append(dict(base, abase=H + dim * j, bbase=comb + 4 * j, bso=1, m1=I.M1_AB, cbase=T, cso=dim, csi=1,
                        ad=I.AD_C))
    ops.append(dict(base, abase=Y, bbase=post, bso=1, m1=I.M1_AB, cbase=T, cso=dim, csi=1, ad=I.AD_C, rnd=1,
                    obase=H, red=I.RED_SUM, redsq=1, redtree=1, rbase=ssx))
    c, tr, sops, lays = run_program(exe, scratch / f"perf_hcpost_{N}", mem0, ops, N, M)
    per = []
    for k, (f, lay) in enumerate(zip(sops, lays)):
        em, rt, rs = op_trace(tr, k)
        if not em:
            per.append(dict(missing=True))
            continue
        per.append(dict(elements=f["nout"] * f["nin"], vectors=len(em), first_emit=em[0], last_emit=em[-1],
                        emit_span_cycles=em[-1] - em[0] + 1,
                        elements_per_cycle=f["nout"] * f["nin"] / (em[-1] - em[0] + 1),
                        first_write=rt[0], last_write=rt[-1], depth=rt[0] - em[0],
                        chase=[f["ch_src"], f["ch_lead"], f["ch_mul"]],
                        layout="whole-unflattened" if lay["wnf"] else ("flat" if lay["flat"] else "rows"),
                        result_cycles=rs, result_after_last_write=(rs[-1] - rt[-1]) if rs else None))
    if any(p.get("missing") for p in per):
        return dict(dim=dim, ops=per, check=c)
    t0 = per[0]["first_emit"]
    tot_el = sum(p["elements"] for p in per)
    span = per[-1]["last_emit"] - t0 + 1
    return dict(dim=dim, elements_per_op=4 * dim, ops=per, check=c,
                sequence=dict(elements=tot_el, first_emit_to_last_emit=span, elements_per_cycle=tot_el / span,
                              first_emit_to_result=per[-1]["result_cycles"][-1] - t0 if per[-1]["result_cycles"]
                              else None, vectors=sum(p["vectors"] for p in per)))


def depth_ops(N, rng, al, init):
    """One op of every class, each a single vector, each issued alone (w_idle)."""
    n = 8
    src = al.get(n)
    init.append((src, rand_vals(rng, n, "small")))
    pos = al.get(n)
    init.append((pos, rand_vals(rng, n, "pos")))
    idx = al.get(n)
    init.append((idx, ffrom(np.arange(n, dtype=np.uint32))))
    b = op_defaults()
    b.update(nout=1, nin=n, asi=1, bsi=1, csi=1, dsi=1, abase=src, bbase=pos, cbase=src, dbase=pos, dst=I.DST_VM,
             osi=1, w_idle=1)
    classes = {
        "linear (M1, M2, Q, AD, E1, E2 all used)": dict(m1=I.M1_AB, m2=I.M2_C, qm=I.QM_POS, ad=I.AD_Q,
                                                        e1=I.E1_MULC, e2=I.E2_MULB),
        "linear (copy)": dict(),
        "gather (IND_I)": dict(aind=I.IND_I, aibase=idx, m1=I.M1_AB),
        "divide (M1 A'/B)": dict(m1=I.M1_DIVB),
        "exp": dict(sfu=I.SFU_EXP),
        "sigmoid": dict(sfu=I.SFU_SIGM),
        "silu": dict(sfu=I.SFU_SILU),
        "rsqrt (side pipe)": dict(sfu=I.SFU_RSQRT, abase=pos),
        "sqrt (side pipe)": dict(sfu=I.SFU_SQRT, abase=pos),
        "sqrt(softplus) (side pipe)": dict(sfu=I.SFU_SPSQRT),
        "Engram gate (side pipe)": dict(sfu=I.SFU_EGATE),
    }
    ops, names = [], []
    for name, kw in classes.items():
        ops.append(dict(b, obase=al.get(n), **kw))
        names.append(name)
    return ops, names


def perf_depths(exe, N, M, scratch, rng):
    al = Alloc(64, (1 << VMA) - 64)
    init = []
    ops, names = depth_ops(N, rng, al, init)
    src = al.get(20 * N)
    init.append((src, rand_vals(rng, 20 * N, "small")))
    r = op_defaults()
    r.update(asi=1, abase=src, red=I.RED_SUM, redsq=1, w_idle=1)
    ops.append(dict(r, nout=1, nin=N, rbase=al.get(2)))
    names.append(f"reduce: one packed row of {N}")
    ops.append(dict(r, nout=1, nin=20 * N, rbase=al.get(2)))
    names.append(f"reduce: one spanning row of {20 * N} (20 vectors)")
    ops.append(dict(r, nout=N // 8, nin=8, aso=8, rbase=al.get(N // 8 + 1), rso=1))
    names.append(f"reduce: {N // 8} packed rows of 8")
    mem0 = fresh_mem(rng, init)
    c, tr, sops, lays = run_program(exe, scratch / f"perf_depth_{N}", mem0, ops, N, M)
    out = {}
    for k, (name, f, lay) in enumerate(zip(names, sops, lays)):
        em, rt, rs = op_trace(tr, k)
        e = dict(emit_to_write=rt[0] - em[0] if em and rt else None, model=lay["dP"], vectors=len(em))
        if f["red"]:
            e.update(result_after_last_write=rs[-1] - rt[-1] if (rs and rt) else None,
                     model_result=lay["dR"] - lay["dP"], time_levels=lay["L"] if lay["span"] else 0,
                     tap_level=lay["lt"])
        out[name] = e
    return dict(classes=out, check=c)


def perf_chain_ext(exe, N, M, scratch, rng, nv=24, per=3):
    """Vector chaining behind an EXTERNAL producer: it writes one N-element vector every `per` cycles into a
    region that holds poison (NaN) until then; the consumer op (ch_src = EXT, lead 1, mul 1) reads each vector
    as soon as its credit arrives.  Latency = the consumer's emit of vector v - the producer's write of v."""
    al = Alloc(64, (1 << VMA) - 64)
    X = al.get(nv * N)
    O = al.get(nv * N)
    data = rand_vals(rng, nv * N, "small")
    mem0 = fresh_mem(rng, [])
    mem0.vm[X:X + nv * N] = 0x7FC00000
    f = op_defaults()
    f.update(nout=1, nin=nv * N, abase=X, asi=1, m1=I.M1_AIMM, imm1=f32u(1.5), dst=I.DST_VM, obase=O, osi=1,
             ch_src=CH_EXT, ch_seq=7, ch_lead=1, ch_mul=256, x_start=1)
    mref = mem0.copy()
    mref.vm[X:X + nv * N] = fbits(data)
    ref_op(dict(f), mref)
    d = scratch / f"perf_chain_{N}"
    write_case(d, mem0, [f], fbits(data))
    tr = run_case(exe, d, 1, dict(vec=N, nv=nv, per=per, base=X, seq=7))
    c = compare(tr, mref)
    em = tr["emits"].get(0, [])
    lat = [e - w for e, w in zip(em, tr["xs"])]
    return dict(producer_vectors=nv, producer_period_cycles=per, write_to_emit_cycles=sorted(set(lat)),
                max_write_to_emit=max(lat) if lat else None, check=c)


def perf_mix(exe, N, M, scratch, rng):
    """Independent back-to-back ops of different classes: the stalls the checkpoint rule costs."""
    al = Alloc(64, (1 << VMA) - 64)
    init = []
    seq = [dict(), dict(sfu=I.SFU_EXP), dict(), dict(m1=I.M1_DIVB), dict(sfu=I.SFU_SIGM), dict(), dict(m1=I.M1_AB)]
    ops = []
    for kw in seq:
        n = 4 * N
        a = al.get(n)
        init.append((a, rand_vals(rng, n, "small")))
        bb = al.get(n)
        init.append((bb, rand_vals(rng, n, "pos")))
        f = op_defaults()
        f.update(nout=1, nin=n, abase=a, asi=1, bbase=bb, bsi=1, dst=I.DST_VM, obase=al.get(n), osi=1, **kw)
        ops.append(f)
    mem0 = fresh_mem(rng, init)
    c, tr, sops, lays = run_program(exe, scratch / f"perf_mix_{N}", mem0, ops, N, M)
    rows = []
    for k, (f, lay) in enumerate(zip(sops, lays)):
        em, rt, _ = op_trace(tr, k)
        rows.append(dict(cls=("sfu%d" % f["sfu"]) if f["sfu"] else ("div" if f["m1"] == I.M1_DIVB else "linear"),
                         vectors=len(em), first_emit=em[0] if em else None, last_emit=em[-1] if em else None,
                         depth=lay["dP"]))
    gaps = [rows[k + 1]["first_emit"] - rows[k]["last_emit"] - 1 for k in range(len(rows) - 1)
            if rows[k + 1]["first_emit"] is not None and rows[k]["last_emit"] is not None]
    return dict(ops=rows, bubbles_between_ops=gaps, check=c)


def sfu_equivalence(scratch, n=200000):
    exe = scratch / "obj_sfu" / "Vtb"
    if not exe.exists():
        cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
               "-Wno-BLKSEQ", "--top-module", "tb_hdc_v41x_vec_sfu", "--prefix", "Vtb", "-Mdir",
               str(scratch / "obj_sfu"), *map(str, LIB), str(RTL[0]), str(TB_SFU), str(HARNESS), "-CFLAGS", "-O1"]
        subprocess.run(cmd, check=True, capture_output=True)
    r = subprocess.run([str(exe), f"+N={n}"], capture_output=True, text=True)
    m = re.search(r"V41XSFU n=(\d+) div=(\d+) div_err=(\d+) exp=(\d+) exp_err=(\d+) rsq=(\d+) rsq_err=(\d+) "
                  r"rsq_fault_timing=(\d+) sp=(\d+) sp_err=(\d+)", r.stdout)
    v = list(map(int, m.groups()))
    return dict(operands=v[0], fdiv_vs_ot_hdc_fdiv=dict(checked=v[1], errors=v[2]),
                exp_vs_ot_hdc_exp=dict(checked=v[3], errors=v[4]),
                rsqrt_vs_ot_hdc_rsqrt=dict(checked=v[5], errors=v[6], fault_timing_differences=v[7]),
                softplus_vs_ot_hdc_softplus=dict(checked=v[8], errors=v[9]),
                pass_=v[2] == 0 and v[4] == 0 and v[6] == 0 and v[9] == 0)


def spec_rows(rec):
    """docs/ARCH_SPEC_V41.md section 6 item 2, graded on the N = 1,024 / M = 256 bench."""
    P = rec.get("perf_N1024_M256")
    if not P:
        return None
    d = P["depths"]["classes"]
    copy = d["linear (copy)"]["emit_to_write"]
    sdepth = lambda k: d[k]["emit_to_write"] - copy
    hp = P["hc_post"]
    ex = [o for o in P["mixed_classes"]["ops"] if o["cls"] == "sfu1"][0]
    exp_rate = 4 * 1024 / (ex["last_emit"] - ex["first_emit"] + 1)
    span = d["reduce: one spanning row of 20480 (20 vectors)"]
    rows = [
        dict(item="light lanes: elements/cycle, a 20,480-element hc_post op", required=1024,
             measured=min(o["elements_per_cycle"] for o in hp["ops"]), meets=None),
        dict(item="light lanes: sustained over 4 back-to-back chained hc_post ops (81,920 elements)",
             required=1024, measured=hp["sequence"]["elements_per_cycle"], meets=None,
             note="the first op's vector 0 of each consumer waits for the producer's vector 0 to be written"),
        dict(item="SFU lanes: elements/cycle of an exp op", required=256, measured=exp_rate, meets=None),
        dict(item="linear op depth (emit -> write, every stage used)", required=21,
             measured=d["linear (M1, M2, Q, AD, E1, E2 all used)"]["emit_to_write"], meets=None, le=True),
        dict(item="exp (S stage)", required=49, measured=sdepth("exp"), meets=None, le=True),
        dict(item="sigmoid (S stage: exp, +1, IEEE divide)", required=80, measured=sdepth("sigmoid"), meets=None,
             le=True),
        dict(item="rsqrt (S stage, side pipe)", required=37, measured=sdepth("rsqrt (side pipe)"), meets=None,
             le=True),
        dict(item="reducer: csum-exact, lane-parallel", required="bit-exact on every program",
             measured="see random / vehicle / perf checks", meets=None),
        dict(item="reducer: result after the last element is written, 20 vectors x 1,024", required=25,
             measured=span["result_after_last_write"], meets=None, le=True,
             note="the R-ARITH order itself sets a floor of 3 cycles x (7 chain adds + log2(1024/8) tree levels + "
                  "ceil(log2 20) vector levels) = 57 at a 3-cycle add, plus the input, square and result registers; "
                  "~25 is not reachable under chunk8 with the 3-cycle adder"),
        dict(item="vector chaining: producer write -> consumer emit of the vector that reads it", required=2,
             measured=P["chain_ext"]["max_write_to_emit"], meets=None, le=True),
    ]
    for r in rows:
        m = r["measured"]
        if isinstance(m, (int, float)) and isinstance(r["required"], (int, float)):
            r["meets"] = bool(m <= r["required"]) if r.get("le") else bool(m >= r["required"] * 0.999)
            r["graded"] = True
    exact = all(x["pass_"] for runs in rec.get("random", {}).values() for x in runs) and \
        all(b["pass_"] for b in rec.get("vehicle", {}).get("batches", [])) and \
        all(P[k]["check"]["pass_"] for k in ("hc_post", "depths", "chain_ext", "mixed_classes"))
    rows[7]["meets"] = bool(exact)
    rows[7]["graded"] = True
    for r in rows:
        r["expected_meets"] = r is not rows[8]
    return dict(clock_ghz=CLOCK_GHZ, rows=rows)


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="a few seeds, a slice of the vehicle, no N = 1,024")
    ap.add_argument("--no-1024", action="store_true")
    ap.add_argument("--scratch", default=None)
    ap.add_argument("--only", default=None, help="comma list: sfu,random,vehicle,perf64,perf1024")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    scratch = Path(args.scratch or tempfile.mkdtemp(prefix="v41xvec_"))
    only = set(args.only.split(",")) if args.only else {"sfu", "random", "vehicle", "perf64", "perf1024"}
    if args.no_1024 or args.quick:
        only.discard("perf1024")
    print("scratch", scratch, flush=True)
    rec = dict(schema="opentallas.rtl.hdc_v41x_vec_campaign/1",
               generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    rng = np.random.default_rng(20260926)
    exes = {}

    def exe_for(N, M):
        if (N, M) not in exes:
            t0 = time.time()
            exes[(N, M)] = build(N, M, scratch / f"obj_{N}_{M}")[0]
            rec.setdefault("verilator_build_seconds", {})[f"N{N}_M{M}"] = round(time.time() - t0, 1)
            print(f"built N={N} M={M}", flush=True)
        return exes[(N, M)]
    if "sfu" in only:
        rec["sfu_equivalence"] = sfu_equivalence(scratch, 50000 if args.quick else 1000000)
        print("sfu", rec["sfu_equivalence"]["pass_"], flush=True)
    if "random" in only:
        rr = {}
        for N, M, seeds, nops in ((16, 8, range(1, 4 if args.quick else 25), 40),
                                  (64, 16, range(101, 103 if args.quick else 117), 40)):
            rr[f"N{N}_M{M}"] = random_campaign(exe_for(N, M), N, M, list(seeds), nops, scratch)
            print("random", N, sum(x["pass_"] for x in rr[f"N{N}_M{M}"]), "/", len(rr[f"N{N}_M{M}"]), flush=True)
        rec["random"] = rr
    if "vehicle" in only:
        recs, cr, wrom, meta = vehicle_records()
        vr = vehicle_campaign(exe_for(64, 16), 64, 16, scratch, recs, cr, wrom, 200 if args.quick else None)
        rec["vehicle"] = dict(meta, batches=vr)
        print("vehicle", sum(x["pass_"] for x in vr), "/", len(vr), flush=True)
    for N, M, key in ((64, 16, "perf64"), (1024, 256, "perf1024")):
        if key not in only:
            continue
        e = exe_for(N, M)
        rec[f"perf_N{N}_M{M}"] = dict(hc_post=perf_hcpost(e, N, M, scratch, rng),
                                      depths=perf_depths(e, N, M, scratch, rng),
                                      chain_ext=perf_chain_ext(e, N, M, scratch, rng),
                                      mixed_classes=perf_mix(e, N, M, scratch, rng))
        print(key, json.dumps(rec[f"perf_N{N}_M{M}"]["hc_post"].get("sequence")), flush=True)
    rec["spec"] = spec_rows(rec)
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in RTL + [TB, TB_SFU, FIELDS_SVH] + TOOLS}
    out = Path(args.out) if args.out else OUT
    out.write_text(json.dumps(rec, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
