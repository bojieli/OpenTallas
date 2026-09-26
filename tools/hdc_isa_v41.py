#!/usr/bin/env python3
"""Instruction set of the DeepSeek-V4.1 configuration of the hardwired decode core.

The V4.1 core (rtl/hdc/v41/ot_hdc_core_v41.sv) is the reduced-Qwen3 core
(tools/hdc_isa.py) with more units and a wider stream pipeline.  Its matrix-
vector engine is the Qwen3 core's (exact BF16 lanes, ot_hdc_matvec's field
semantics) with head groups added (ot_hdc_v41_matvec, below); the other units
are:

* The matrix engine's KV-sourced ops may take HEAD GROUPS (`me_hg`, H = 2^hg,
  ot_hdc_v41_matvec): the G lane groups form H head groups of G/H groups; head
  group h reads x at + h*xcs and writes at + h*ogs (words), and a round covers
  G/H tiles of 16 rows instead of G.  With hg = 0 it is ot_hdc_matvec.
* HE, the hyper-connection projection engine (ot_hdc_v41_hcproj): the FP32-
  weight mixes matvec(fn, flat, HC_SPLIT), HC_SPLIT x NL lanes x IL
  interleaved outputs of the qualified binary32 multiplier and adder; K is cut
  into HC_SPLIT chunks of he_k, each sequential in its lane, the chunk sums a
  pairwise tree; word wbase + k*IL + j holds, in lane c*NL + l, row j*NL + l at
  column c*he_k + k.  It runs beside the matrix engine.

* SU, the V4.1 stream unit (ot_hdc_v41_stream): a 2-D element loop (outer o,
  inner i) over SU_LANES lanes.  `su_vec` picks what a cycle issues: SCALAR
  (one element, lane 0), VEC_I (lanes take i .. i+SU_LANES-1 of one o) or
  VEC_O (lanes take o .. o+SU_LANES-1 at one i: each lane owns whole
  segments, so per-segment reductions keep the scalar order).  Lane 0 has every
  SFU function; the other lanes lack rsqrt, sqrt, sqrt(softplus) and the Engram
  gate (those ops are SCALAR).  Four operand streams A, B, C, D (vector
  memory, constant ROM lo/hi word, or -- A only -- the BF16 weight ROM), and a
  fixed pipeline every element passes:

      A' = min(relu(rnd?(A)), imm3)          C' = clip(C, -imm3, imm3)
      P  = A' | A'*B | A'*A' | A'*imm1 | A'/B | A'/imm1 | max(A', B)
      P2 = P | P*C' | P*imm1                 Q = C'*(+-D)   (sign per mode / parity)
      R  = P2 | P2+Q | P2+C' | P2-B | P2+imm2 | P2+D
      S  = sfu(R): R | exp | rsqrt | sqrt | sigmoid | silu | sqrt(softplus) | engram gate
      T  = S | S*C' | S+C' | S*imm2 | S+imm2
      U  = T | T*B | T*imm1
      out = rnd?(U)  -> vector memory / KV SRAM (linear or transposed-KV address)

  sigmoid(R) = 1/(exp(-R)+1) and silu(R) = R/(exp(-R)+1) divide (IEEE), as the
  golden does.  The reducer takes out (or out*out) per outer segment, or over
  the whole op (`red_whole`, SCALAR only); SUM (P=8 interleaved partials, pairwise tree),
  MAX, or SEQ (one sequential partial: the unit issues one element every 8
  cycles); `red_tree` sums each segment (<= 16) and adds the segment sums by a
  pairwise tree padded with +0 (hdc_golden_v41.split_sum); `red_rnd` rounds
  the result to BF16.  A may be GATHERED: its i- or
  o-offset is an integer index read from the vector memory (`a_ind`).
  Pair mode (`c_pair`) reads C at A's address XOR 1 and B at i >> 1
  (`b_half`): the interleaved-pair RoPE in one pass.
* QE, the quantised engine (ot_hdc_v41_qe): the activation quantiser
  (ot_hdc_actquant) and BL block-dot lanes (ot_hdc_blockdot).  LINQ is the
  golden's linear_q: the op quantises nb 32-element blocks of x, then streams
  rows (round, block, slot) exactly as the matrix engine streams (round, k,
  slot); the weight base may add an expert id read from the vector memory.
  QDQ8 / QDQ4 / QDQ4E write the quantise-dequantise of nb blocks.
* XU, the auxiliary unit (ot_hdc_v41_xu): SEL (streaming top-k, ascending
  index order, ot_hdc_select), SINK (the 40 Sinkhorn normalisations of a
  4 x 4 mix; ot_hdc_sinkhorn's port list), EHASH (the Engram hash of the new
  token, ot_hdc_engram_hash) and EGATHER (24 Engram rows, dequantised).

Sequencing.  An instruction names the units whose in-flight work it must see
drained (`wait`, a mask; bit u-1 for unit u, u = ME, SU, QE, XU, HE); the program generator computes
it from region hazards, so independent units overlap.  A stream op that reads the
previous stream op's element writes may instead CHASE it (`su_chase` = D > 0,
same class): it is accepted behind that op and emits a vector only while fewer
than D vectors are in flight, D derived from the two ops' write and read orders
so no read overtakes its write.  `pred` skips an
instruction by position parity (group-completing compressor steps) or at
position 0 (an empty index set).  A count that evaluates to zero skips.

`python3 tools/hdc_isa_v41.py` regenerates rtl/hdc/v41/ot_hdc_isa_v41.svh.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh"

W_LANES = 16          # lanes per ME group; vector/KV word width
GROUPS = 4            # ME lane groups
INTERLEAVE = 8        # ME / QE outputs in flight per lane
BL = 16               # QE block-dot lanes
HE_LANES = 3          # HE lanes (x INTERLEAVE outputs)
SU_LANES = int(os.environ.get("HDC_SW", 8))    # SU lanes: elements per cycle (a power of two, >= 4)
T_MAX = 144           # attention rows per layer: window 128 + 16 selected
POS_MAX = 128         # positions provisioned (max_seq_len of the reduced model)
VM_ELEMS = 65536
KV_WORDS = 32768
INSTR_BITS = 1536

A = 24   # address / stride width
N = 16   # count width
D = 5    # DYN select width

UNIT_END, UNIT_ME, UNIT_SU, UNIT_QE, UNIT_XU, UNIT_HE = range(6)
UNITS = (UNIT_ME, UNIT_SU, UNIT_QE, UNIT_XU, UNIT_HE)
PRED_ALWAYS, PRED_ODD, PRED_NZ = range(3)

# DYN values, derived by the sequencer from (token, pos) at the start of a token.
DYN_NAMES = [
    "ZERO", "EMBED", "ROPE", "ROPE_G2", "POS", "POS1", "N2", "N2M1",
    "NSEL1", "NSEL2", "T1", "T2", "RND_POS1", "RND_N2", "RND_T1", "RND_T2",
    "ROW", "ROW1", "SLOTW", "SLOTE", "CKV2", "RND16_POS1", "RND16_N2", "RND16_T1", "RND16_T2",
]
DYN = {n: i for i, n in enumerate(DYN_NAMES)}
TOPK, RH, HDIM, DIM = 16, 2, 32, 160


def dyn_values(token, pos):
    n2 = (pos + 1) >> 1
    ns1, ns2 = min(TOPK, pos + 1), min(TOPK, n2)
    rnd = lambda x: (x - 1) // (W_LANES * GROUPS) + 1 if x > 0 else 0
    rnd16 = lambda x: (x - 1) // W_LANES + 1 if x > 0 else 0          # 16-row tiles (head-group KV ops)
    v = [0, token * DIM, pos * RH, (pos - 1) * RH if pos else 0, pos, pos + 1, n2, n2 - 1 if n2 else 0,
         ns1, ns2, pos + 1 + ns1, pos + 1 + ns2, rnd(pos + 1), rnd(n2), rnd(pos + 1 + ns1), rnd(pos + 1 + ns2),
         pos * HDIM, (pos + 1) * HDIM, (pos & 1) * 4, (pos & 1) * 64, (n2 - 1) * HDIM if n2 else 0,
         rnd16(pos + 1), rnd16(n2), rnd16(pos + 1 + ns1), rnd16(pos + 1 + ns2)]
    return v + [0] * (32 - len(v))


# stream-unit encodings
SRC_VM, SRC_CLO, SRC_CHI, SRC_WROM = range(4)
IND_NONE, IND_I, IND_O = range(3)
M1_BYP, M1_AB, M1_AA, M1_AIMM, M1_DIVB, M1_DIVIMM, M1_MAXB = range(7)
M2_BYP, M2_C, M2_IMM = range(3)
QM_OFF, QM_POS, QM_NEG, QM_ALT_NP, QM_ALT_PN = range(5)     # ALT_NP: even -D, odd +D
AD_BYP, AD_Q, AD_C, AD_NEGB, AD_IMM, AD_D = range(6)
SFU_NONE, SFU_EXP, SFU_RSQRT, SFU_SQRT, SFU_SIGM, SFU_SILU, SFU_SPSQRT, SFU_EGATE = range(8)
E1_BYP, E1_MULC, E1_ADDC, E1_MULIMM, E1_ADDIMM = range(5)
E2_BYP, E2_MULB, E2_MULIMM = range(3)
DST_NONE, DST_VM, DST_KV, DST_KVT = range(4)
RED_NONE, RED_SUM, RED_MAX, RED_SEQ = range(4)
VEC_SCALAR, VEC_I, VEC_O = range(3)
# QE / XU
QE_LINQ, QE_QDQ8, QE_QDQ4, QE_QDQ4E = range(4)
XU_SEL, XU_SINK, XU_EHASH, XU_EGATHER = range(4)

FIELDS = [
    ("unit", 3), ("wait", 5), ("pred", 2),
    # ME (tools/hdc_isa.py semantics)
    ("me_nout", N), ("me_tiles", N), ("me_k", N), ("me_wsrc", 1),
    ("me_wbase", A), ("me_ts", A), ("me_ks", A), ("me_js", A),
    ("me_xbase", A), ("me_round", 1), ("me_obase", A), ("me_oen", 1), ("me_amax", 1),
    ("me_d_wbase", D), ("me_d_xbase", D), ("me_d_obase", D),
    ("me_d_nout", D), ("me_d_tiles", D), ("me_d_k", D),
    ("me_xks", A), ("me_xjs", A), ("me_jsh", 3), ("me_ots", A), ("me_ojs", A), ("me_mmode", 1),
    ("me_split", 2), ("me_xcs", A), ("me_hg", 2), ("me_ogs", A),
    # SU
    ("su_nout", N), ("su_nin", N), ("su_d_nout", D), ("su_d_nin", D),
    ("a_src", 2), ("a_base", A), ("a_so", A), ("a_si", A), ("a_d", D), ("a_ind", 2), ("a_ibase", A),
    ("b_src", 2), ("b_base", A), ("b_so", A), ("b_si", A), ("b_d", D), ("b_half", 1),
    ("c_src", 2), ("c_base", A), ("c_so", A), ("c_si", A), ("c_d", D), ("c_pair", 1),
    ("d_src", 2), ("d_base", A), ("d_so", A), ("d_si", A), ("d_d", D),
    ("a_rnd", 1), ("a_relu", 1), ("a_min", 1), ("c_clip", 1),
    ("m1", 3), ("m2", 2), ("qm", 3), ("ad", 3), ("sfu", 3), ("e1", 3), ("e2", 2), ("rnd", 1),
    ("dst", 2), ("o_base", A), ("o_so", A), ("o_si", A), ("o_d", D),
    ("red", 2), ("red_sq", 1), ("red_whole", 1), ("red_rnd", 1), ("r_base", A), ("r_so", A),
    ("imm1", 32), ("imm2", 32), ("imm3", 32),
    # QE
    ("qe_mode", 2), ("qe_fp4", 1), ("qe_xbase", A), ("qe_nb", 8), ("qe_nout", N), ("qe_tiles", N),
    ("qe_wbase", A), ("qe_ind", 1), ("qe_ibase", A), ("qe_istride", A), ("qe_obase", A), ("qe_d_obase", D),
    # XU
    ("xu_op", 2), ("xu_src", A), ("xu_dst", A), ("xu_n", N), ("xu_d_n", D), ("xu_k", 5), ("xu_d_k", D),
    ("xu_layer", 1),
    # HE
    ("he_nout", N), ("he_k", N), ("he_wbase", A), ("he_xbase", A), ("he_obase", A),
    # SU lane axis (SCALAR, VI, VO) and the segmented-tree reduction
    ("su_vec", 2), ("red_tree", 1), ("su_chase", N),
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
        if name.startswith("_"):
            continue
        off, width = LAYOUT[name]
        value = int(value)
        assert 0 <= value < (1 << width), (name, value)
        word |= value << off
    return word


def decode(word):
    return {name: (word >> off) & ((1 << width) - 1) for name, (off, width) in LAYOUT.items()}


def emit_package():
    lines = [
        "// GENERATED by tools/hdc_isa_v41.py -- do not edit.",
        "// Field offsets of one V4.1 HDC instruction word; see the tool for semantics.",
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
