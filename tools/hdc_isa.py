#!/usr/bin/env python3
"""Instruction set of the hardwired decode core (HDC): the single source of truth.

The core runs a static program of macro-operations.  Two units execute them:

* ME, the matrix-vector engine: G groups of W lanes, I interleaved outputs per
  lane.  Each lane is a pipelined multiply feeding a pipelined FP32 add whose
  result circulates back after exactly I cycles, so every output accumulates
  its products in order at one MAC per lane per cycle.  With split S = 2^split
  the K range is cut into S contiguous chunks of kc = me_k; group g = q*S + c
  takes chunk c of tile t = r*(G/S) + q, and a pairwise tree adds the S chunk
  sums ((c0+c1)+(c2+c3)).  Element (round r, k, slot j), lane l of group g:
      weight  lane g*W+l of word  wbase + r*ts + k*ks + (j >> jsh)*js
      x       element             xbase + c*xcs + k*xks + j*xjs
      result  lane l of word      obase + t*ots + j*ojs   (after the last k)
  valid when (t*I + j)*W + l < nout (mmode 0, rows) or t*W + l < nout (mmode 1,
  lanes: every slot is its own vector, e.g. one attention head per slot).
  KV-sourced ops (wsrc 1) spread over all groups (tile t = r*G + g, word
  wbase + t*ts + ..., one KV port per group).  Every product is BF16 x BF16.
  `chase` (either unit): instead of waiting for a barrier, start once the
  OTHER unit's latest instruction has made `chase_n` progress -- elements
  written for the stream unit, result slots (one per slot per round) for the
  matrix engine.  The program generator derives chase_n from the order in
  which the producer writes what the consumer reads (element chaining).
* SU, the stream unit: a 2-D loop (outer o, inner i) over elements.  Each
  element passes a fixed pipeline

      P = mA(A, B)        Q = C * (+-B.hi)
      R = P  (+ Q | + C | - B | + imm2 | bypass)
      S = sfu(R)          (exp | reciprocal | rsqrt | sigmoid-denominator | bypass)
      out = (S (* C | bypass)) (* B | bypass)
  where the sigmoid class computes 1 / (exp(R) + 1).

  and may feed a segmented reducer (one segment per outer iteration): SUM in
  P=8 interleaved partials plus a pairwise tree, or MAX; `red_sq` reduces
  out*out instead of out (a sum of squares fused into the producing op).

Address fields are element addresses (ME weight/output bases are word
addresses).  A base may add one of the DYN values the sequencer derives from
(token, position) at the start of a token; a count may be replaced by one.

`python3 tools/hdc_isa.py` regenerates rtl/hdc/ot_hdc_isa.svh, included inside the
core module (Yosys takes no package import in a module header).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "rtl/hdc/ot_hdc_isa.svh"

W_LANES = 16          # lanes per ME group, and the vector/KV memory word width
GROUPS = int(os.environ.get("HDC_GROUPS", 4))   # ME lane groups: W_LANES * GROUPS MACs per cycle
INTERLEAVE = 8        # ME outputs in flight per lane (adder latency 5 + 3)
T_MAX = 64            # KV positions provisioned
VM_ELEMS = 4096       # vector memory, FP32 elements
INSTR_BITS = 1024

A = 24   # address / stride width
N = 16   # count width
D = 3    # DYN select width

UNIT_END, UNIT_ME, UNIT_SU = 0, 1, 2
# DYN values (sequencer): 0 is zero.
DYN_NONE, DYN_EMBED, DYN_ROPE, DYN_KWRITE, DYN_VWRITE, DYN_T, DYN_TTILES = range(7)
# DYN_TTILES = pos // (W * GROUPS) + 1: rounds of G lane tiles covering the context.
# SU source / mode encodings
SRC_VM, SRC_ALT = 0, 1                 # ALT: A -> weight ROM (bf16), B/C -> constant ROM
MA_BYP, MA_AB, MA_AA, MA_AIMM = range(4)
MB_OFF, MB_POS, MB_NEG = range(3)
AD_BYP, AD_Q, AD_C, AD_NEGB, AD_IMM = range(5)
SFU_NONE, SFU_EXP, SFU_RECIP, SFU_RSQRT, SFU_SIGM = range(5)
MC_BYP, MC_C = range(2)
MD_BYP, MD_B = range(2)
DST_NONE, DST_VM, DST_KV = range(3)
RED_NONE, RED_SUM, RED_MAX = range(3)

FIELDS = [
    ("unit", 2), ("barrier", 1), ("chase", 1), ("chase_n", N),
    # ME
    ("me_nout", N), ("me_tiles", N), ("me_k", N), ("me_wsrc", 1),
    ("me_wbase", A), ("me_ts", A), ("me_ks", A), ("me_js", A),
    ("me_xbase", A), ("me_round", 1), ("me_obase", A), ("me_oen", 1), ("me_amax", 1),
    ("me_d_wbase", D), ("me_d_xbase", D), ("me_d_obase", D),
    ("me_d_nout", D), ("me_d_tiles", D), ("me_d_k", D),
    ("me_xks", A), ("me_xjs", A), ("me_jsh", 3), ("me_ots", A), ("me_ojs", A), ("me_mmode", 1),
    ("me_split", 2), ("me_xcs", A),
    # SU
    ("su_nout", N), ("su_nin", N), ("su_d_nin", D),
    ("a_src", 1), ("a_base", A), ("a_so", A), ("a_si", A), ("a_d", D),
    ("b_src", 1), ("b_base", A), ("b_so", A), ("b_si", A), ("b_d", D),
    ("c_src", 1), ("c_base", A), ("c_so", A), ("c_si", A), ("c_d", D),
    ("ma", 2), ("mb", 2), ("ad", 3), ("sfu", 3), ("mc", 1), ("md", 1),
    ("dst", 2), ("d_base", A), ("d_so", A), ("d_si", A), ("d_d", D),
    ("red", 2), ("r_base", A), ("r_so", A), ("red_sq", 1),
    ("imm1", 32), ("imm2", 32),
]


def layout():
    off, out = 0, {}
    for name, width in FIELDS:
        out[name] = (off, width)
        off += width
    assert off <= INSTR_BITS, off
    return out


LAYOUT = layout()


def encode(**kw):
    word = 0
    for name, value in kw.items():
        off, width = LAYOUT[name]
        value = int(value)
        assert 0 <= value < (1 << width), (name, value)
        word |= value << off
    return word


def decode(word):
    return {name: (word >> off) & ((1 << width) - 1) for name, (off, width) in LAYOUT.items()}


def emit_package():
    lines = [
        "// GENERATED by tools/hdc_isa.py -- do not edit.",
        "// Field offsets of one HDC instruction word; see the tool for semantics.",
        "// Included inside a module body.",
        f"localparam integer ISA_INSTR_BITS = {INSTR_BITS};",
    ]
    for name, (off, width) in LAYOUT.items():
        lines.append(f"localparam integer O_{name.upper()} = {off};")
        lines.append(f"localparam integer W_{name.upper()} = {width};")
    PKG.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    emit_package()
    print(f"{PKG.relative_to(ROOT)}: {sum(w for _, w in FIELDS)} bits used of {INSTR_BITS}")
