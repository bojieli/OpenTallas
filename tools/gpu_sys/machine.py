#!/usr/bin/env python3
"""Functional (untimed) reference of the GPU-organised HBM comparator system executing OTG-1 kernels:
ND dies, each with NSM SIMT SMs (NL lanes, NV vector registers, 16 uniform registers, shared memory, one
exact tensor core of L lanes behind a bulk-copy weight stream), a die-global byte-addressed memory (HBM
behind the L2 slices), a grid barrier per die, and an NVLS-style collective across dies.

The RTL (rtl/gpu_sys) must produce the same architectural results; this model is what the compiler is
checked against before any RTL runs, and what the RTL is diffed against when it does not match."""
from __future__ import annotations

import numpy as np

from isa import dec, lane_op, e4m3_decode, e4m3_encode, fadd, fmul, cvt_bf16, NUR

U = np.uint32


class Die:
    def __init__(self, die, nsm, nl, mem_bytes, smem_bytes, L, il=8):
        self.die = die
        self.mem = np.zeros(mem_bytes, dtype=np.uint8)
        self.sms = [SM(self, s, nl, smem_bytes, L, il) for s in range(nsm)]


class SM:
    def __init__(self, die, sid, nl, smem_bytes, L, il):
        self.die, self.sid, self.nl, self.L, self.il = die, sid, nl, L, il
        self.vr = np.zeros((256, nl), dtype=U)
        self.ur = np.zeros(NUR, dtype=U)
        self.smem = np.zeros(smem_bytes // 4, dtype=U)
        self.xstore = {}
        self.imem = []
        self.result = None
        self.stats = {"instr": 0, "tc_lines": 0, "ldg_bytes": 0, "stg_bytes": 0}

    # ------------------------------------------------------------------ memory helpers
    def _addrs(self, ua, imm, esz, strided, count):
        stride = int(self.ur[15]) if strided else esz
        base = (int(self.ur[ua]) + imm) & 0xFFFFFFFF
        return [(base + l * stride) & 0xFFFFFFFF for l in range(count)]

    def load_elem(self, addr, esz):
        m = self.die.mem
        if esz == 4:
            return int(m[addr]) | int(m[addr + 1]) << 8 | int(m[addr + 2]) << 16 | int(m[addr + 3]) << 24
        if esz == 2:
            return (int(m[addr]) | int(m[addr + 1]) << 8) << 16
        return int(e4m3_decode(np.uint32(m[addr])))

    def store_elem(self, addr, esz, val):
        m = self.die.mem
        if esz == 4:
            for k in range(4):
                m[addr + k] = (val >> (8 * k)) & 0xFF
        elif esz == 2:
            m[addr] = (val >> 16) & 0xFF
            m[addr + 1] = (val >> 24) & 0xFF
        else:
            m[addr] = int(e4m3_encode(np.uint32(val)))

    # ------------------------------------------------------------------ the tensor core (ot_gpu_sm semantics)
    def tcmma(self, wbase, sbase, g, c, rows):
        """Lines in the lockstep row-slot order (rb, g, t, s), each L BF16 weights (L*2 bytes); lane j of
        group gg holds chunk gg*L+j; chunk sums sequential from +0, then the L-leaf pairwise tree and the
        pairwise stack over the G groups (hdc_golden.matvec with split = number of chunks)."""
        L, il = self.L, self.il
        acc = np.zeros((rows, g * L), dtype=U)
        addr = wbase
        for rb in range(0, rows, il):
            for gg in range(g):
                for t in range(c):
                    xw = self.xstore.get(gg * c + t, np.zeros(L, dtype=U))
                    for s in range(il):
                        r = rb + s
                        if r >= rows:
                            continue
                        raw = self.die.mem[addr:addr + 2 * L].view(np.uint16).astype(U) << 16
                        addr += 2 * L
                        cols = slice(gg * L, gg * L + L)
                        acc[r, cols] = fadd(acc[r, cols], fmul(raw, xw))
                        self.stats["tc_lines"] += 1
        parts = acc
        while parts.shape[1] > 1:
            parts = fadd(parts[:, 0::2], parts[:, 1::2])
        for r in range(rows):
            self.smem[(sbase >> 2) + r] = parts[r, 0]


class Machine:
    def __init__(self, nd=2, nsm=2, nl=128, mem_bytes=1 << 23, smem_bytes=1 << 15, L=16):
        self.nl = nl
        self.dies = [Die(d, nsm, nl, mem_bytes, smem_bytes, L) for d in range(nd)]

    def sms(self):
        return [sm for d in self.dies for sm in d.sms]

    def launch(self, kernels, token, pos):
        """Run one kernel (its per-SM code list kernels[(die, sm)]) on every SM to EXIT, honouring BAR (all
        SMs of a die) and COLL (die 0..ND-1 SM issuing it, in program order)."""
        runs = {}
        for d in self.dies:
            for sm in d.sms:
                sm.ur[:] = 0
                sm.ur[0], sm.ur[1], sm.ur[2], sm.ur[3] = token, pos, sm.sid, d.die
                runs[(d.die, sm.sid)] = self._run(sm, kernels[(d.die, sm.sid)])
        state = {k: next(g) for k, g in runs.items()}       # each yields ('BAR'|'COLL'|'EXIT', payload)
        while True:
            if all(s[0] == "EXIT" for s in state.values()):
                return
            progressed = False
            for d in self.dies:
                keys = [(d.die, sm.sid) for sm in d.sms]
                if all(state[k][0] in ("BAR", "EXIT") for k in keys) and any(state[k][0] == "BAR" for k in keys):
                    if any(state[k][0] == "EXIT" for k in keys):
                        raise RuntimeError("BAR with an exited SM")
                    for k in keys:
                        state[k] = runs[k].send(None)
                    progressed = True
            colls = {k: v for k, v in state.items() if v[0] == "COLL"}
            if colls and len(colls) == len(self.dies):
                keys = sorted(colls)
                outs = self._collective([colls[k][1] for k in keys])
                for k, o in zip(keys, outs):
                    state[k] = runs[k].send(o)
                progressed = True
            if not progressed:
                raise RuntimeError(f"deadlock: { {k: v[0] for k, v in state.items()} }")

    def _collective(self, reqs):
        mode, count = reqs[0][0], reqs[0][1]
        assert all(r[0] == mode and r[1] == count for r in reqs), "collective mismatch"
        out = np.zeros(self.nl, dtype=U)
        if mode == 0:
            acc = reqs[0][2][:count].copy()
            for r in reqs[1:]:
                acc = fadd(acc, r[2][:count])
            out[:count] = acc
        else:
            for i, r in enumerate(reqs):
                out[i * count:(i + 1) * count] = r[2][:count]
        return [out.copy() for _ in reqs]

    def _run(self, sm, code):
        vr, ur, nl = sm.vr, sm.ur, sm.nl
        lane = np.arange(nl, dtype=U)
        pc = 0
        while True:
            op, d, a, b, imm = dec(code[pc])
            pc += 1
            sm.stats["instr"] += 1
            if op in ("FADD", "FMUL", "XOR", "AND", "OR", "SHR", "SHL", "IADD", "ISUB", "UGT", "ULT", "FCMPGT",
                      "FDIV", "IMUL"):
                vr[d] = lane_op(op, vr[a], vr[b])
            elif op in ("F2I", "CVTBF16", "CVTE4M3", "FSQRT"):
                vr[d] = lane_op(op, vr[a], vr[a])
            elif op == "MOVI":
                vr[d] = imm
            elif op == "LANEID":
                vr[d] = lane
            elif op == "MOVU":
                vr[d] = ur[a]
            elif op == "SHFL":
                vr[d] = vr[a][vr[b] % nl]
            elif op == "UMOVI":
                ur[d] = imm
            elif op == "UADDI":
                ur[d] = (int(ur[a]) + imm) & 0xFFFFFFFF
            elif op == "UADD":
                ur[d] = (int(ur[a]) + int(ur[b])) & 0xFFFFFFFF
            elif op == "UMULI":
                ur[d] = (int(ur[a]) * imm) & 0xFFFFFFFF
            elif op == "UFROMV":
                ur[d] = vr[a][imm % nl]
            elif op in ("LDG", "STG"):
                ua, esz, strided, count = a & 15, (4, 2, 1)[(a >> 4) & 3], (a >> 6) & 1, b + 1
                addrs = sm._addrs(ua, imm, esz, strided, count)
                if op == "LDG":
                    v = np.zeros(nl, dtype=U)
                    for l, ad in enumerate(addrs):
                        v[l] = sm.load_elem(ad, esz)
                    vr[d] = v
                    sm.stats["ldg_bytes"] += esz * count
                else:
                    for l, ad in enumerate(addrs):
                        sm.store_elem(ad, esz, int(vr[d][l]))
                    sm.stats["stg_bytes"] += esz * count
            elif op in ("LDS", "STS"):
                base = (int(ur[a & 15]) + imm) >> 2
                count = b + 1
                if op == "LDS":
                    v = np.zeros(nl, dtype=U)
                    v[:count] = sm.smem[base:base + count]
                    vr[d] = v
                else:
                    sm.smem[base:base + count] = vr[d][:count]
            elif op == "LDSX":
                vr[d] = sm.smem[((vr[a].astype(np.int64) + imm) >> 2) & (len(sm.smem) - 1)]
            elif op == "STSX":
                idx = ((vr[a][:b + 1].astype(np.int64) + imm) >> 2) & (len(sm.smem) - 1)
                sm.smem[idx] = vr[d][:b + 1]
            elif op == "TCX":
                sm.xstore[imm] = vr[a][:sm.L] & U(0xFFFF0000)
            elif op == "TCMMA":
                sm.tcmma(int(ur[d & 15]), int(ur[a & 15]), b, imm >> 16, imm & 0xFFFF)
            elif op == "BRA":
                pc = imm
            elif op == "BNZ":
                if int(ur[a & 15]) != 0:
                    pc = imm
            elif op in ("FMAX", "FMIN", "IMULHI"):            # additions (isa.py): lane-wise binary
                vr[d] = lane_op(op, vr[a], vr[b])
            elif op in ("CVTE2M1", "CVTE4M3B"):
                vr[d] = lane_op(op, vr[a], vr[a])
            elif op == "TCXB":
                bd_tcxb(sm, vr[a], vr[b], imm)
            elif op == "TCXE":
                bd_tcxe(sm, vr[a], imm)
            elif op == "TCBMMA":
                bd_tcbmma(sm, int(ur[d & 15]), int(ur[a & 15]), b, imm)
            elif op in ("TCWAIT", "MEMBAR", "NOP"):
                pass
            elif op == "BAR":
                yield ("BAR", None)
            elif op == "COLL":
                out = yield ("COLL", (b & 1, imm & 0xFF, vr[a].copy()))
                vr[d] = out
            elif op == "RESULT":
                sm.result = int(ur[a])
            elif op == "EXIT":
                yield ("EXIT", None)
                return
            else:
                raise ValueError(op)


# ---------------------------------------------------------------------------------------------------------------------
# Block-scaled tensor core (additions for tools/gpu_sys/v41_hbm.py): the exact SM element rtl/gpu/ot_gpu_sm_bd.sv
# (SUB 4 x LBS 2 = 8 bd-lanes, NC = 1, IL = 8; ot_gpu_bd_col: a k32 FP8/FP4 x FP8 block dot formed exactly, rounded
# once to FP32, scaled by 2^(we + xe); per lane the terms of one golden chunk accumulate sequentially from +0; the
# lanes, then the groups, a pairwise tree) -- hdc_golden_v41.linear_q's FP32 accumulator under R-ARITH chunk8.
#
#   TCXB a, b, imm   x-store word w = imm[7:0]: bd-lane j < 4 codes byte i = vr[a][32j + i] & 0xFF, bd-lanes 4..7
#                    from vr[b] the same way (E4M3 codes, as CVTE4M3B leaves them)
#   TCXE a, imm      x-store word w = imm[7:0]: bd-lane j exponent = vr[a][j][9:0], two's complement
#   TCBMMA uw, us, g, imm   rows = imm[11:0], fp4 = imm[12], c = imm[23:16] (k-steps per chunk), g = groups.
#                    Weight lines at UR[uw], 288 B (9 sectors) each, in the ot_gpu_issue row-slot order (rb, gg, t,
#                    s; slot s = row rb + s; IL = 8): sector j (j < 8) = bd-lane j's 32 codes (E4M3 bytes, or E2M1 in
#                    the low nibble), sector 8 = the 8 exponents as int16 little-endian (sign-extended 10-bit).
#                    Lane j of group gg holds chunk gg*LA + j (LA = 8 FP4, 4 FP8; lanes past the op's chunks carry
#                    zero codes) and meets x-store word gg*c + t.  Row r's FP32 result -> SMEM word (UR[us] >> 2) + r;
#                    TCWAIT completes it.
# ---------------------------------------------------------------------------------------------------------------------
_E4M3_VAL = None
_E2M1_VAL = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, -0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0])
BD_LINE = 288


def _e4m3_table():
    global _E4M3_VAL
    if _E4M3_VAL is None:
        c = np.arange(256)
        s, e, m = c >> 7, (c >> 3) & 15, c & 7
        v = np.where(e == 0, m / 8.0 * 2.0 ** -6, (1 + m / 8.0) * np.exp2(e.astype(np.float64) - 7))
        v = np.where((e == 15) & (m == 7), np.nan, v)
        _E4M3_VAL = np.where(s == 1, -v, v)
    return _E4M3_VAL


def _bdx(sm):
    if not hasattr(sm, "bdxq"):
        sm.bdxq, sm.bdxe = {}, {}
    return sm.bdxq, sm.bdxe


def bd_tcxb(sm, va, vb, imm):
    q, _ = _bdx(sm)
    q[imm & 0xFF] = np.concatenate([va, vb]).astype(np.uint32).reshape(8, 32) & 0xFF


def bd_tcxe(sm, va, imm):
    _, e = _bdx(sm)
    x = (np.asarray(va[:8], dtype=np.int64) & 0x3FF)
    e[imm & 0xFF] = np.where(x >= 512, x - 1024, x)


_BD_ORDER = {}


def bd_issue(rows, g, c):
    """(row, gg, t) of every line in the row-slot issue order."""
    key = (rows, g, c)
    if key not in _BD_ORDER:
        out = []
        for rb in range(0, rows, 8):
            for gg in range(g):
                for t in range(c):
                    for s_ in range(8):
                        if rb + s_ < rows:
                            out.append((rb + s_, gg, t))
        _BD_ORDER[key] = np.array(out, dtype=np.int64).reshape(-1, 3)
    return _BD_ORDER[key]


def bd_tcbmma(sm, wbase, sbase, g, imm):
    rows, fp4, c = imm & 0xFFF, (imm >> 12) & 1, (imm >> 16) & 0xFF
    xq, xe = _bdx(sm)
    order = bd_issue(rows, g, c)
    n = len(order)
    raw = sm.die.mem[wbase:wbase + n * BD_LINE].reshape(n, BD_LINE)
    codes = raw[:, :256].reshape(n, 8, 32)
    wv = _E2M1_VAL[codes & 15] if fp4 else _e4m3_table()[codes]
    we = raw[:, 256:272].copy().view(np.int16).astype(np.int64) & 0x3FF
    we = np.where(we >= 512, we - 1024, we)
    e4 = _e4m3_table()
    xtab = np.zeros((g * c, 8, 32))
    etab = np.zeros((g * c, 8), dtype=np.int64)
    for a_ in range(g * c):
        if a_ in xq:
            xtab[a_] = e4[xq[a_]]
        if a_ in xe:
            etab[a_] = xe[a_]
    xa = order[:, 1] * c + order[:, 2]
    with np.errstate(all="ignore"):
        dot = np.einsum("nji,nji->nj", wv, xtab[xa])          # exact: < 42 significant bits
        term = np.ldexp(dot.astype(np.float32), we + etab[xa]).astype(np.float32).view(U)
    acc = np.zeros((rows, g * 8), dtype=U)
    cols = order[:, 1:2] * 8 + np.arange(8)[None, :]
    for t in range(c):                                         # each lane's chunk: sequential over t from +0
        m = order[:, 2] == t
        r_ = np.repeat(order[m, 0], 8)
        c_ = cols[m].reshape(-1)
        acc[r_, c_] = fadd(acc[r_, c_], term[m].reshape(-1))
    width = 1
    while width < g * 8:
        width *= 2
    parts = np.zeros((rows, width), dtype=U)
    parts[:, :g * 8] = acc
    while parts.shape[1] > 1:
        parts = fadd(parts[:, 0::2], parts[:, 1::2])
    sm.smem[(sbase >> 2):(sbase >> 2) + rows] = parts[:, 0]
    sm.stats["bd_lines"] = sm.stats.get("bd_lines", 0) + n
