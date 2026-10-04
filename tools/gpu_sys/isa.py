#!/usr/bin/env python3
"""OTG-1: the instruction set of the SIMT SM of the GPU-organised HBM comparator system (rtl/gpu_sys).

Ordinary GPU instructions only (HBM comparators take only what a real GPU or its software stack has, AGENTS.md):
two-source lane-wise FP32/integer ops, the CUDA-style conversions (cvt.rn.bf16.f32, cvt.rn.satfinite.e4m3),
IEEE div.rn / sqrt.rn, warp shuffles, uniform (scalar) registers, global and shared loads/stores, a
tensor-core (MMA) issue with its weight stream from the TMA-style bulk-copy engine, a grid barrier, a memory
fence, an NVLS-style collective (multimem ld_reduce / all-gather) and the kernel's completion payload.

Encoding, one 64-bit word:  [63:56] opcode  [55:48] d  [47:40] a  [39:32] b  [31:0] imm.
This module is the reference semantics; rtl/gpu_sys/ot_gpu_simt_sm.sv implements the same encoding.
"""
from __future__ import annotations

import numpy as np

F = np.float32
U = np.uint32

OPS = {
    "NOP": 0x00,
    # lane-wise, d = op(a, b)
    "FADD": 0x01, "FMUL": 0x02, "XOR": 0x03, "AND": 0x04, "OR": 0x05, "SHR": 0x06, "SHL": 0x07,
    "IADD": 0x08, "ISUB": 0x09, "UGT": 0x0A, "ULT": 0x0B, "FCMPGT": 0x0C,
    "F2I": 0x0D, "CVTBF16": 0x0E, "CVTE4M3": 0x0F, "FDIV": 0x10, "FSQRT": 0x11, "IMUL": 0x12,
    # moves / shuffles
    "MOVI": 0x20, "LANEID": 0x21, "MOVU": 0x22, "SHFL": 0x23,
    # uniform registers
    "UMOVI": 0x28, "UADDI": 0x29, "UMULI": 0x2A, "UFROMV": 0x2B, "UADD": 0x2C,
    # control
    "BRA": 0x30, "BNZ": 0x31, "EXIT": 0x32, "BAR": 0x33, "MEMBAR": 0x34, "RESULT": 0x35,
    # memory
    "LDG": 0x38, "STG": 0x39, "LDS": 0x3A, "STS": 0x3B, "LDSX": 0x3C, "STSX": 0x3D,
    # tensor core
    "TCX": 0x40, "TCMMA": 0x41, "TCWAIT": 0x42,
    # collective
    "COLL": 0x48,
}
# --- additions for the DeepSeek-V4.1 lowering (tools/gpu_sys/v41_hbm.py); ordinary GPU instructions:
#   FMAX / FMIN   FMNMX: d = a > b ? a : b  /  a < b ? a : b  (FP compare; operands are finite, NaN never reaches
#                 them because the FP pipes fail closed)
#   IMULHI        mul.hi.u32 (IMAD.HI): d = (a * b) >> 32, unsigned 32 x 32 -> high word
#   CVTE2M1       cvt.rn.satfinite.e2m1 (Blackwell): FP32 -> E2M1 grid {0, .5, 1, 1.5, 2, 3, 4, 6} with sign,
#                 round to nearest even code, saturating at 6, returned as FP32 bits, canonical +0
#   CVTE4M3B      cvt.rn.satfinite.e4m3 producing the CODE: d = E4M3 byte (in bits 7:0) of CVTE4M3(a)
#   TCXB / TCXE / TCBMMA   the block-scaled (MX FP8/FP4) tensor core rtl/gpu/ot_gpu_sm_bd.sv: x-store code and
#                 exponent writes and the k32 block-dot MMA (semantics: machine.py, bd_tcxb / bd_tcxe / bd_tcbmma)
OPS.update({"FMAX": 0x13, "FMIN": 0x14, "IMULHI": 0x15, "CVTE2M1": 0x16, "CVTE4M3B": 0x17,
            "TCXB": 0x43, "TCBMMA": 0x44, "TCXE": 0x45})
NAMES = {v: k for k, v in OPS.items()}
BINARY = {"FADD", "FMUL", "XOR", "AND", "OR", "SHR", "SHL", "IADD", "ISUB", "UGT", "ULT", "FCMPGT", "FDIV", "IMUL"}
UNARY = {"F2I", "CVTBF16", "CVTE4M3", "FSQRT"}
BINARY |= {"FMAX", "FMIN", "IMULHI"}
UNARY |= {"CVTE2M1", "CVTE4M3B"}
ESZ = {4: 0, 2: 1, 1: 2}          # LDG/STG element size code (F32, BF16 upper half, E4M3 byte)
NUR = 16                           # uniform registers; UR0 token, UR1 position, UR2 SM id, UR3 die id, UR15 stride


def enc(op, d=0, a=0, b=0, imm=0):
    return (OPS[op] << 56) | ((d & 0xFF) << 48) | ((a & 0xFF) << 40) | ((b & 0xFF) << 32) | (imm & 0xFFFFFFFF)


def dec(w):
    return NAMES[(w >> 56) & 0xFF], (w >> 48) & 0xFF, (w >> 40) & 0xFF, (w >> 32) & 0xFF, w & 0xFFFFFFFF


# ---------------------------------------------------------------------------------------------- lane semantics
def fbits(x):
    return np.asarray(x, dtype=F).view(U)


def ffrom(b):
    return np.asarray(b, dtype=U).view(F)


def _z(x):
    x = np.asarray(x, dtype=F)
    return np.where(x == 0, F(0), x).astype(F)


FP_ERR = [0]          # lanes that failed closed (nonfinite operand or result) since the last reset


def _nonfinite(bits):
    return ((np.asarray(bits, dtype=U) >> 23) & 0xFF) == 0xFF


def _closed(a, b, r):
    """The qualified FP pipes fail closed: a nonfinite operand or an overflowing result gives y = +0 and err."""
    bad = _nonfinite(a) | _nonfinite(b) | _nonfinite(r)
    FP_ERR[0] += int(np.sum(bad))
    return np.where(bad, U(0), r).astype(U)


def fadd(a, b):
    with np.errstate(all="ignore"):
        return _closed(a, b, fbits(_z(ffrom(a) + ffrom(b))))


def fmul(a, b):
    with np.errstate(all="ignore"):
        return _closed(a, b, fbits(_z(ffrom(a) * ffrom(b))))


def fdiv(a, b):
    with np.errstate(all="ignore"):
        return fbits(_z(ffrom(a) / ffrom(b)))


def fsqrt(a):
    with np.errstate(all="ignore"):
        return fbits(_z(np.sqrt(ffrom(a))))


def cvt_bf16(a):
    """cvt.rn.bf16.f32, returned as the FP32 bit pattern (low 16 bits zero): hdc_golden.to_bf16."""
    b = np.asarray(a, dtype=U).astype(np.uint64)
    return (((b + 0x7FFF + ((b >> 16) & 1)) >> 16) << 16).astype(U)


def cvt_e4m3(a):
    """FP32 -> E4M3 (bias 7, max 448, subnormal quantum 2^-9) RNE saturating, returned as FP32 bits:
    hdc_golden.to_fp8 (canonical +0)."""
    x = ffrom(a).astype(np.float64)
    m = np.abs(x)
    _, ex = np.frexp(m)
    e = np.maximum(ex - 1, -6)
    q = np.ldexp(1.0, e - 3)
    r = np.minimum(np.round(m / q) * q, 448.0)
    return fbits(_z(np.where(x < 0, -r, r).astype(F)))


def e4m3_encode(a):
    """An on-grid E4M3 value (FP32 bits) -> its byte."""
    x = ffrom(a).astype(np.float64)
    s = (x < 0).astype(np.uint32)
    m = np.abs(x)
    out = np.zeros(m.shape, dtype=np.uint32)
    for i, v in np.ndenumerate(m):
        if v == 0:
            c = 0
        elif v < 2.0 ** -6:
            c = int(round(v / 2.0 ** -9))
        else:
            ee = int(np.floor(np.log2(v)))
            mm = int(round((v / 2.0 ** ee - 1.0) * 8))
            c = ((ee + 7) << 3) | mm
        out[i] = c
    return (out | (s << 7)).astype(np.uint32)


def e4m3_decode(byte):
    c = np.asarray(byte, dtype=np.uint32)
    s = (c >> 7) & 1
    e = (c >> 3) & 15
    m = c & 7
    v = np.where(e == 0, m / 8.0 * 2.0 ** -6, (1 + m / 8.0) * np.exp2(e.astype(np.float64) - 7))
    v = np.where(s == 1, -v, v)
    return fbits(_z(v.astype(F)))


def lane_op(op, a, b):
    a = np.asarray(a, dtype=U)
    b = np.asarray(b, dtype=U)
    if op == "FADD":
        return fadd(a, b)
    if op == "FMUL":
        return fmul(a, b)
    if op == "FDIV":
        return fdiv(a, b)
    if op == "XOR":
        return a ^ b
    if op == "AND":
        return a & b
    if op == "OR":
        return a | b
    if op == "SHR":
        return (a >> (b & 31)).astype(U)
    if op == "SHL":
        return (a << (b & 31)).astype(U)
    if op == "IADD":
        return (a.astype(np.uint64) + b).astype(U)
    if op == "ISUB":
        return (a.astype(np.int64) - b.astype(np.int64)).astype(np.uint64).astype(U)
    if op == "IMUL":
        return (a.astype(np.uint64) * b.astype(np.uint64) & 0xFFFFFFFF).astype(U)
    if op == "UGT":
        return (a > b).astype(U)
    if op == "ULT":
        return (a < b).astype(U)
    if op == "FCMPGT":
        with np.errstate(all="ignore"):
            return (ffrom(a) > ffrom(b)).astype(U)
    if op == "F2I":
        with np.errstate(all="ignore"):
            return np.trunc(ffrom(a).astype(np.float64)).astype(np.int64).astype(np.uint64).astype(U)
    if op == "CVTBF16":
        return cvt_bf16(a)
    if op == "CVTE4M3":
        return cvt_e4m3(a)
    if op == "FSQRT":
        return fsqrt(a)
    if op in ("FMAX", "FMIN"):
        with np.errstate(all="ignore"):
            pick_a = (ffrom(a) > ffrom(b)) if op == "FMAX" else (ffrom(a) < ffrom(b))
        return np.where(pick_a, a, b).astype(U)
    if op == "IMULHI":
        return ((a.astype(np.uint64) * b.astype(np.uint64)) >> np.uint64(32)).astype(U)
    if op == "CVTE2M1":
        return cvt_e2m1(a)
    if op == "CVTE4M3B":
        return e4m3_encode(cvt_e4m3(a)).astype(U)
    raise ValueError(op)


E2M1_GRID = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])


def cvt_e2m1(a):
    """cvt.rn.satfinite.e2m1: |x| to the nearest E2M1 value, ties to the even code (codes 0..7 = the grid above),
    saturating at 6; sign kept; returned as FP32 bits, canonical +0."""
    x = ffrom(a).astype(np.float64)
    m = np.minimum(np.abs(x), 6.0)
    i = np.clip(np.searchsorted(E2M1_GRID, m), 1, 7)          # E2M1_GRID[i-1] < m <= E2M1_GRID[i]
    lo, hi = E2M1_GRID[i - 1], E2M1_GRID[i]
    up = (m - lo > hi - m) | ((m - lo == hi - m) & (i % 2 == 0))
    r = np.where(up, hi, lo)
    r = np.where(m == 0, 0.0, r)
    return fbits(_z(np.where(x < 0, -r, r).astype(F)))
