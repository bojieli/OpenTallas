#!/usr/bin/env python3
"""H-MTP2 multi-position (P-row) record semantics on the hgi_sim machine units, at 1M context (unit tests, seconds).

1. WINDOW RING HAZARD of the batched verify: the column-serial verify appends position p's KV row then runs p's
   attention; a P-row verify appends ALL P rows of the layer (one DMA.KVWB_DS of P rows) before the P attention rows.
   With the shipped ring of 128 slots (= the window), the appends of positions p+1 .. p+P-1 land on ring slots of
   positions p+1-128 .. p+P-1-128, which are INSIDE row p's window: row p reads a later position's KV row (wrong).
   With a ring of 256 slots (power of two >= 128 + P - 1; no ISA change: KVWB O.m and ATT B.m = 256) every row reads
   exactly its own window.  The test asserts the 128-slot ring FAILS (the mutant) and the 256-slot ring is
   bit-identical to the column-serial order.
2. ROW EXECUTOR: a P-row record (rows = P; a descriptor with m = P steps by its stride per row, m = 1 broadcasts; row r
   runs with POS = POS0 + r) is bit-identical to P single-position records, for every per-position family the DS
   verify uses whose machine unit exists (ATT.QK / PV, DMA.KVWB_DS, FUSED.QDQ_FP8, IDX.TOPK, SU.VOP).

    python3 -m hgi_sim.test_mtp_rows          (from tools/)
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from hgi_sim import machine as MC  # noqa: E402
from hgi_sim.records import MDesc, Rec  # noqa: E402

F = np.float32
POS0 = 1048570                       # the verify block's first position (1M context: the ring has wrapped 8,191 times)
P = 6
HD = 512
DYN_WIN = 16
RING = 1 << 32


class Mach(MC.Machine):
    def doorbell(self, token, pos, slot_count=1):
        super().doorbell(token, pos, slot_count)
        for d in self.dies:
            d.dyn[DYN_WIN] = min(pos + 1, 128)


def set_pos(M, pos):
    M.doorbell(0, pos)


def make(m_slots, seed=7):
    rng = np.random.default_rng(seed)
    d = MC.Die(0, MC.Hbm())
    ring = np.full((m_slots, HD), np.nan, F)           # never-written slots: NaN (a read of one shows up)
    hist = rng.standard_normal((128, HD)).astype(F)     # the KV rows of positions POS0 - 128 .. POS0 - 1, by position
    for j in range(128):
        ring[(POS0 - 128 + j) % m_slots] = hist[j]
    d.hbm.add(RING, ring.view(np.uint8).reshape(-1).copy(), "RING")
    units = {("DMA", "KVWB_DS"): MC.u_dma_kvwb_ds, ("ATT", "QK"): MC.u_att_qk, ("ATT", "PV"): MC.u_att_pv}
    M = Mach([d], units)
    # rows of the block (one KV row a position) and the queries, in VM: row r at base + r * HD
    kv = rng.standard_normal((P, HD)).astype(F)
    q = rng.standard_normal((P, HD)).astype(F)
    d.vm[0:P * HD] = kv.reshape(-1).view(np.uint32)
    d.vm[8192:8192 + P * HD] = q.reshape(-1).view(np.uint32)
    return M, d


def kvwb(r, m_slots):
    return Rec("DMA", "KVWB_DS", desc=dict(A=MDesc(space="VM", fmt="FP32", base=r * HD, n=HD),
                                           O=MDesc(space="HBM", fmt="FP32", base=RING, n=HD, m=m_slots,
                                                   stride=HD * 4)), tag="kvwb")


def qk(r, m_slots):
    return Rec("ATT", "QK", param=1 | (1 << 8), desc=dict(
        A=MDesc(space="VM", fmt="FP32", base=8192 + r * HD, n=HD),
        B=MDesc(space="HBM", fmt="FP32", base=RING, n=128, m=m_slots, stride=HD * 4, n_sel=DYN_WIN),
        O=MDesc(space="VM", fmt="FP32", base=16384 + r * 256, n=128)), tag="qk")


def run(M, r, pos):
    set_pos(M, pos)
    M.cur = r
    M.units[(r.unit, r.op)](M, r, 0)


def ring_case(m_slots):
    """-> (serial scores, batched scores) [P, 128] for a ring of m_slots"""
    out = []
    for mode in ("serial", "batched"):
        M, d = make(m_slots)
        if mode == "serial":
            for r in range(P):
                run(M, kvwb(r, m_slots), POS0 + r)
                run(M, qk(r, m_slots), POS0 + r)
        else:
            for r in range(P):
                run(M, kvwb(r, m_slots), POS0 + r)
            for r in range(P):
                run(M, qk(r, m_slots), POS0 + r)
        out.append(d.vm[16384:16384 + P * 256].reshape(P, 256)[:, :128].copy())
    return out


def row_exec(M, r, rows, pos0, row_stride):
    """the P-row executor: row k = the record with every m == rows descriptor advanced k strides (m set to 1), m == 1
    descriptors broadcast, POS = pos0 + k"""
    for k in range(rows):
        rk = copy.copy(r)
        rk.desc = {}
        for nm, dsc in r.desc.items():
            if dsc.m == rows and nm in row_stride:
                rk.desc[nm] = MDesc(**{**dsc.__dict__, "base": dsc.base + k * row_stride[nm], "m": 1})
            else:
                rk.desc[nm] = dsc
        run(M, rk, pos0 + k)


def main():
    fails = 0
    s128, b128 = ring_case(128)
    s256, b256 = ring_case(256)
    bad128 = [r for r in range(P) if not np.array_equal(s128[r].view(np.uint32), b128[r].view(np.uint32))]
    bad256 = [r for r in range(P) if not np.array_equal(s256[r].view(np.uint32), b256[r].view(np.uint32))]
    print(f"ring 128 (shipped): batched != serial on rows {bad128}  (expected rows 0..{P - 2}: MUTANT MUST FAIL)")
    print(f"ring 256 (P-row design): batched != serial on rows {bad256}  (expected none)")
    if bad128 != list(range(P - 1)):
        fails += 1
    if bad256:
        fails += 1
    # the serial order itself must not depend on the ring size (both read the same window rows)
    if not all(np.array_equal(s128[r].view(np.uint32), s256[r].view(np.uint32)) for r in range(P)):
        print("serial 128 vs 256 differ: ring contents not position-addressed")
        fails += 1
    # row executor on the units: KVWB + QK as P-row records (rows 6, VM stride HD / 256) == serial (ring 256)
    M, d = make(256)
    row_exec(M, Rec("DMA", "KVWB_DS", desc=dict(A=MDesc(space="VM", fmt="FP32", base=0, n=HD, m=P, stride=HD),
                                                O=kvwb(0, 256).desc["O"])), P, POS0, {"A": HD})
    q6 = qk(0, 256)
    q6.desc["A"] = MDesc(space="VM", fmt="FP32", base=8192, n=HD, m=P, stride=HD)
    q6.desc["O"] = MDesc(space="VM", fmt="FP32", base=16384, n=128, m=P, stride=256)
    row_exec(M, q6, P, POS0, {"A": HD, "O": 256})
    got = d.vm[16384:16384 + P * 256].reshape(P, 256)[:, :128]
    ok = all(np.array_equal(got[r], s256[r].view(np.uint32)) for r in range(P))
    print(f"P-row KVWB_DS + ATT.QK (rows {P}) == column-serial: {ok}")
    fails += 0 if ok else 1
    print("PASS" if not fails else f"FAIL ({fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
