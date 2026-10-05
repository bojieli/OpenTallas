#!/usr/bin/env python3
"""Kernel builder for OTG-1 (tools/gpu_sys/isa.py): virtual vector registers, constant cache, linear-scan
register allocation onto the SM's NV physical vector registers.  Straight-line kernels (the decode step's
control flow is static; position and token enter through uniform registers at launch)."""
from __future__ import annotations

import numpy as np

from isa import enc, OPS, BINARY, UNARY, ESZ


class V:
    """A virtual vector register."""
    __slots__ = ("n",)

    def __init__(self, n):
        self.n = n

    def __repr__(self):
        return f"v{self.n}"


class Kernel:
    def __init__(self, name, nv=256):
        self.name = name
        self.nv = nv
        self.ins = []            # (op, d, a, b, imm) with V or int fields
        self.nvreg = 0
        self.consts = {}

    def _new(self):
        self.nvreg += 1
        return V(self.nvreg)

    def emit(self, op, d=0, a=0, b=0, imm=0):
        self.ins.append((op, d, a, b, imm & 0xFFFFFFFF))

    # ------------------------------------------------------------------ vector ops
    def op(self, name, a, b=None):
        d = self._new()
        if name in BINARY:
            self.emit(name, d, a, b)
        elif name in UNARY:
            self.emit(name, d, a, 0)
        else:
            raise ValueError(name)
        return d

    def const(self, bits):
        bits = int(bits) & 0xFFFFFFFF
        if bits not in self.consts:
            d = self._new()
            self.emit("MOVI", d, 0, 0, bits)
            self.consts[bits] = d
        return self.consts[bits]

    def fconst(self, x):
        return self.const(int(np.asarray(x, dtype=np.float32).view(np.uint32)))

    def movi(self, bits):
        d = self._new()
        self.emit("MOVI", d, 0, 0, bits)
        return d

    def laneid(self):
        if "lane" not in self.consts:
            d = self._new()
            self.emit("LANEID", d)
            self.consts["lane"] = d
        return self.consts["lane"]

    def movu(self, u):
        d = self._new()
        self.emit("MOVU", d, u)
        return d

    def shfl(self, a, idx):
        d = self._new()
        self.emit("SHFL", d, a, idx)
        return d

    # ------------------------------------------------------------------ uniform ops
    def umovi(self, u, imm):
        self.emit("UMOVI", u, 0, 0, imm)

    def uaddi(self, u, ua, imm):
        self.emit("UADDI", u, ua, 0, imm)

    def uadd(self, u, ua, ub):
        self.emit("UADD", u, ua, ub)

    def umuli(self, u, ua, imm):
        self.emit("UMULI", u, ua, 0, imm)

    def ufromv(self, u, a, lane=0):
        self.emit("UFROMV", u, a, 0, lane)

    # ------------------------------------------------------------------ memory
    def ldg(self, u, imm, esz=4, count=None, strided=False):
        d = self._new()
        self.emit("LDG", d, (u & 15) | (ESZ[esz] << 4) | (int(strided) << 6), (count or 128) - 1, imm)
        return d

    def stg(self, v, u, imm, esz=4, count=128, strided=False):
        self.emit("STG", v, (u & 15) | (ESZ[esz] << 4) | (int(strided) << 6), count - 1, imm)

    def lds(self, u, imm, count=128):
        d = self._new()
        self.emit("LDS", d, u & 15, count - 1, imm)
        return d

    def sts(self, v, u, imm, count=128):
        self.emit("STS", v, u & 15, count - 1, imm)

    def ldsx(self, idx, imm):
        d = self._new()
        self.emit("LDSX", d, idx, 0, imm)
        return d

    def stsx(self, v, idx, imm, count=128):
        self.emit("STSX", v, idx, count - 1, imm)

    # ------------------------------------------------------------------ tensor core, sync, collective
    def tcx(self, v, word):
        self.emit("TCX", 0, v, 0, word)

    def tcmma(self, uw, us, g, c, rows):
        self.emit("TCMMA", uw, us, g, (c << 16) | rows)

    def tcwait(self):
        self.emit("TCWAIT")

    def coll(self, v, mode, count):
        d = self._new()
        self.emit("COLL", d, v, mode, count)
        return d

    def bar(self):
        self.emit("BAR")

    def membar(self):
        self.emit("MEMBAR")

    def result(self, u):
        self.emit("RESULT", 0, u)

    def exit(self):
        self.emit("EXIT")

    # ------------------------------------------------------------------ register allocation and encoding
    def assemble(self):
        """Linear scan over the straight-line code.  A register is freed after its last read; a defined but
        never-read value still occupies its register until the definition retires (the SM's scoreboard also
        blocks a write-after-write)."""
        last = {}
        for i, (op, d, a, b, imm) in enumerate(self.ins):
            for x in (d, a, b):
                if isinstance(x, V):
                    last[x.n] = i
        phys = {}
        free = list(range(self.nv - 1, -1, -1))
        words = []
        peak = 0
        for i, (op, d, a, b, imm) in enumerate(self.ins):
            def p(x):
                if isinstance(x, V):
                    if x.n not in phys:
                        raise ValueError(f"{self.name}: v{x.n} read before definition at {i} {op}")
                    return phys[x.n]
                return x
            pa, pb = p(a), p(b)
            if isinstance(d, V) and op not in ("STG", "STS", "STSX"):
                if d.n in phys:
                    raise ValueError("SSA violation")
                if not free:
                    raise ValueError(f"{self.name}: out of vector registers at {i}")
                phys[d.n] = free.pop()
                pd = phys[d.n]
            else:
                pd = p(d)
            peak = max(peak, self.nv - len(free))
            words.append(enc(op, pd, pa, pb, imm))
            for x in (a, b, d):
                if isinstance(x, V) and last.get(x.n) == i and x.n in phys:
                    free.append(phys.pop(x.n))
        self.peak = peak
        return words
