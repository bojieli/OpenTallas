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
