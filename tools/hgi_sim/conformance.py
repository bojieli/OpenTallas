#!/usr/bin/env python3
"""HGI-1 conformance-row test vectors (docs/HBM_GENERIC_INTERFACE.md section 8.4) for the hardware forks.

Every vector is a small HGI-1 program image in the owner-approved encoding (records.py: the D_* tables of
tools/hbm_generic_iface.py), ending in CTL.END, plus the die inputs it reads and the outputs it must produce, all
computed by the simulator's own generic unit models (tools/hgi_sim/machine.py) -- the models the bit-exact DS 1M and
Qwen P8191 tokens run on.  A vector names its conformance row (CF-*), its mode (DS = the DS reset / DS per-operation
values, the CF-1 equivalence side; QWEN = Qwen3-8B per-operation values; GENERIC = other models), and its mutants:
each mutant is a stated hardware or compiler defect whose outputs (or fault) differ from the expected ones.

    python3 -m hgi_sim.conformance --out results/arch/hgi_sim_20261009/conformance        (from tools/; seconds)

FILE FORMAT (one JSON per vector, plus index.json):
  records_hex     the program image (concatenated records, little-endian, spec 6.1), also as one hex per record
  records         the decoded records (unit, op, param, imm_a, imm_b, wait, pred, every descriptor field)
  cfg             the three static fields in force (cp_vocab, cp_ctx_max, coll_group_size)
  doorbell        {token, pos}
  dies[r]         rank, vm_in: [[word address, hex of little-endian uint32 words]], hbm_in: [[byte base, hex]]
  expect          status (0 OK, else the completion status of the fault) and, per die, vm_out / hbm_out: every
                  VM word range and HBM byte range the program changed, as [[address, hex]]
  mutants         [{name, defect, status, differs: true, outputs_sha256}]
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hbm_generic_iface as HGI  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

from hgi_sim import lib as A  # noqa: E402
from hgi_sim import machine as MC  # noqa: E402
from hgi_sim.qwen_compiler import sut  # noqa: E402
from hgi_sim.records import DYN, MDesc, Rec, decode_program, encode_program  # noqa: E402

F = np.float32
TOKW = MC.VM_WORDS - 1                       # VM word the closing CTL.END reads (token 0)
FLT_MAX = 0x7F7FFFFF
DS_CFG = dict(HGI.D_RESET)
QW_CFG = dict(cp_vocab=151936, cp_ctx_max=40960, coll_group_size=4)


def f32u(x):
    return int(np.asarray(F(x)).view(np.uint32))


def hx(a):
    return np.ascontiguousarray(a).view(np.uint8).tobytes().hex()


def runs(mask):
    """[start, end) runs of True in a boolean vector."""
    m = np.concatenate([[False], mask, [False]]).astype(np.int8)
    d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def V(base, n, m=1, stride=0, istride=0, fmt="FP32", **kw):
    return MDesc(space="VM", fmt=fmt, base=base, n=n, m=m, stride=stride, istride=istride, **kw)


def H(base, n, m=1, stride=0, fmt="FP32", **kw):
    return MDesc(space="HBM", fmt=fmt, base=base, n=n, m=m, stride=stride, **kw)


def END():
    return Rec("CTL", "END", desc=dict(A=V(TOKW, 1, fmt="U32")), tag="end")


class Case:
    """Die inputs: per rank, VM words {addr: uint32 array} and HBM regions {base: uint8 array}."""

    def __init__(self, ranks, cfg, pos=0, token=0):
        self.ranks, self.cfg, self.pos, self.token = ranks, dict(cfg), pos, token
        self.vm = [dict() for _ in range(ranks)]
        self.hbm = [dict() for _ in range(ranks)]

    def vm_f32(self, r, addr, vals):
        self.vm[r][addr] = np.asarray(vals, dtype=F).reshape(-1).view(np.uint32).copy()

    def vm_u32(self, r, addr, vals):
        self.vm[r][addr] = np.asarray(vals, dtype=np.uint32).reshape(-1).copy()

    def hbm_bytes(self, r, base, raw):
        self.hbm[r][base] = np.ascontiguousarray(raw).view(np.uint8).reshape(-1).copy()

    def build(self):
        dies = []
        for r in range(self.ranks):
            hb = MC.Hbm()
            for b, raw in self.hbm[r].items():
                hb.add(b, raw.copy(), f"in{b:#x}")
            d = MC.Die(r, hb)
            for a, w in self.vm[r].items():
                d.vm[a:a + w.size] = w
            dies.append(d)
        return dies


def execute(case: Case, recs, mutate=None):
    """Run the program; returns (status, dies)."""
    recs = copy.deepcopy(recs)
    if not (recs and recs[-1].unit == "CTL" and recs[-1].op == "END"):
        recs = recs + [END()]
    image = encode_program(recs)
    dec = decode_program(image)
    dies = case.build()
    M = MC.Machine(dies, MC.UNITS)
    M.cfg.update(case.cfg)
    if mutate:
        mutate(M, dec, dies)
    try:
        M.run(encode_program(dec), case.token, case.pos, hash_bufs=False, recs=dec)
        return 0, dies, image
    except MC.Fault as e:
        return e.status, dies, image


def diff_out(case, dies):
    base = case.build()
    out = []
    for d0, d in zip(base, dies):
        vm = [[int(a), hx(d.vm[a:b])] for a, b in runs(d.vm != d0.vm)]
        hb = []
        for (b0, raw0, _), (b1, raw1, _) in zip(d0.hbm.regions, d.hbm.regions):
            for a, b in runs(raw1 != raw0):
                hb.append([int(b0 + a), raw1[a:b].tobytes().hex()])
        out.append(dict(rank=d.rank, vm_out=vm, hbm_out=hb))
    return out


def rec_json(r):
    d = dict(unit=r.unit, op=r.op, param=r.param, imm_a=r.imm_a, imm_b=r.imm_b, wait=r.wait, pred=r.pred,
             slot=r.slot, tmpl=r.sut is not None)
    if r.sut is not None:
        d["sut"] = {k: v for k, v in r.sut.items() if v}
    d["desc"] = {k: {f: v for f, v in dataclasses.asdict(x).items()} for k, x in r.desc.items()}
    return d


VECTORS = []


def dedupe(rows):
    """A die entry identical (apart from its rank) to an earlier one is written as {rank, same_as_rank}.  An HBM
    input [base, null, nbytes] is all zero."""
    out, seen = [], {}
    for d in rows:
        key = json.dumps({k: v for k, v in d.items() if k != "rank"})
        if key in seen:
            out.append(dict(rank=d["rank"], same_as_rank=seen[key]))
        else:
            seen[key] = d["rank"]
            out.append(d)
    return out


def vector(row, mode, name, what, case, recs, mutants=(), expect_status=None):
    st, dies, image = execute(case, recs)
    if expect_status is not None and st != expect_status:
        raise AssertionError(f"{name}: status {st}, expected {expect_status}")
    exp = diff_out(case, dies) if st == 0 else []
    sha = hashlib.sha256(json.dumps(exp).encode()).hexdigest()
    mus = []
    for mname, defect, fn in mutants:
        if isinstance(fn, tuple):                 # (records', case') replacement
            r2, c2 = fn
            st2, dies2, _ = execute(c2 or case, r2)
            out2 = diff_out(c2 or case, dies2) if st2 == 0 else []
        else:
            st2, dies2, _ = execute(case, recs, mutate=fn)
            out2 = diff_out(case, dies2) if st2 == 0 else []
        s2 = hashlib.sha256(json.dumps(out2).encode()).hexdigest()
        if st2 == st and s2 == sha:
            raise AssertionError(f"{name}: mutant {mname} is not detected")
        mus.append(dict(name=mname, defect=defect, status=st2, differs=True, outputs_sha256=s2))
    recs_full = list(recs) + ([] if recs and recs[-1].op == "END" else [END()])
    dec = decode_program(image)
    VECTORS.append(dict(
        id=name, row=row, mode=mode, what=what, cfg=case.cfg, doorbell=dict(token=case.token, pos=case.pos),
        records_hex=image.hex(), record_hex=[r.encode().hex() for r in decode_program(image)],
        records=[rec_json(r) for r in dec], tags=[r.tag for r in recs_full],
        dies=dedupe([dict(rank=r, vm_in=[[int(a), hx(w)] for a, w in sorted(case.vm[r].items())],
                          hbm_in=[[int(b), None, int(raw.size)] if not raw.any() else [int(b), raw.tobytes().hex()]
                                  for b, raw in sorted(case.hbm[r].items())]) for r in range(case.ranks)]),
        expect=dict(status=st, dies=dedupe(exp), outputs_sha256=sha), mutants=mus))
    return st


# ----------------------------------------------------------------------------------------------------------------
# CF-COLL
# ----------------------------------------------------------------------------------------------------------------
def highest_id_merge(M, d, dies):
    def u(M_, r, L):
        for grp in M_.groups():
            ids = [int(dd.vm[M_.vm_addrs(r.desc["A"], dd, L, 1, 2)[1]]) for dd in grp]
            for dd in grp:
                dd.vm[M_.vm_addrs(r.desc["O"], dd, L, 1, 1)] = np.uint32(max(ids))
    M.units = {**M.units, ("COLL", "ARGMAX_MERGE"): u}


def cf_coll(rng):
    for G in (1, 2, 4, 8):
        c = Case(8, dict(QW_CFG, coll_group_size=G))
        for r in range(8):
            v = rng.standard_normal(256).astype(F)
            if r == 1:
                v[:8] = -0.0                                     # a -0 contributor
            c.vm_f32(r, 0, v)
        recs = [Rec("COLL", "ALL_REDUCE_SUM", desc=dict(A=V(0, 256), O=V(1024, 256)), tag="ar")]
        vector("CF-COLL", "QWEN" if G == 4 else "GENERIC", f"coll_all_reduce_g{G}",
               f"ALL_REDUCE_SUM of 256 words, groups of {G} over 8 dies (rank-order pairwise tree; -0 at rank 1)", c,
               recs, mutants=[("group_isolation", "rank 0's result leaks into the next group (one group of 8)",
                               lambda M, d, dies: M.cfg.update(coll_group_size=8 if G < 8 else 4))])
    # argmax merge with ties across ranks (Qwen group 4)
    c = Case(4, QW_CFG)
    for r in range(4):
        c.vm_f32(r, 0, [5.0, 0.0])
        c.vm_u32(r, 1, [[100, 37984 + 7, 2 * 37984 + 3, 151935][r]])
    c.vm_f32(3, 0, [5.0])
    recs = [Rec("COLL", "ARGMAX_MERGE", desc=dict(A=V(0, 2), O=V(16, 1, fmt="U32")), tag="merge")]
    vector("CF-COLL", "QWEN", "coll_argmax_merge_ties", "ARGMAX_MERGE: equal values on all 4 ranks -> lowest global "
           "id (100) wins", c, recs,
           mutants=[("highest_id", "ties resolved to the highest id", highest_id_merge)])
    # ALL_GATHER even split, G = 96 not dividing n (DS), and G = 4
    for G, n, mode in ((96, 1000, "DS"), (4, 1030, "QWEN")):
        c = Case(G, dict(DS_CFG if G == 96 else QW_CFG))
        for r in range(G):
            c.vm_f32(r, 0, rng.standard_normal(n).astype(F))
        recs = [Rec("COLL", "ALL_GATHER", desc=dict(A=V(0, n), O=V(2048, n)), tag="gather")]

        def uniform(M, d, dies, n=n, G=G):                        # defect: segments of ceil(n / G)
            def u(M_, r, L):
                seg = -(-n // G)
                full = np.zeros(n, dtype=np.uint32)
                for q, dd in enumerate(M_.dies):
                    full[q * seg:(q + 1) * seg] = dd.vm[q * seg:min((q + 1) * seg, n)]
                for dd in M_.dies:
                    dd.vm[2048:2048 + n] = full
            M.units = {**M.units, ("COLL", "ALL_GATHER"): u}
        vector("CF-COLL", mode, f"coll_all_gather_g{G}_n{n}", f"ALL_GATHER even-split segments, G = {G}, n = {n}",
               c, recs, mutants=[("ceil_segments", "segments of ceil(n / G) instead of floor(r n / G)", uniform)])
    # GROUP_REDUCE_MCAST s = 8 over 96, BF16 out (DS o-group reduce)
    c = Case(96, DS_CFG)
    for r in range(96):
        c.vm_f32(r, (r // 8) * 64, rng.standard_normal(64).astype(F))
    recs = [Rec("COLL", "GROUP_REDUCE_MCAST", param=8, desc=dict(A=V(0, 64), O=V(4096, 64 * 12, fmt="BF16")),
                tag="grm")]
    recs[0].desc["A"] = V(0, 64)                  # each die's contribution at VM 0 (its sub-group's slice)
    for r in range(96):
        c.vm[r] = {0: c.vm[r][(r // 8) * 64]}
    vector("CF-COLL", "DS", "coll_group_reduce_mcast_s8", "GROUP_REDUCE_MCAST s = 8 over 96 ranks, BF16 out: O = the 12 "
           "sub-groups' rank-order pairwise sums in sub-group order on every rank", c, recs,
           mutants=[("fp32_out", "the multicast result not rounded to BF16",
                     lambda M, d, dies: setattr(d[0].desc["O"], "fmt", "FP32")),
                    ("s4", "sub-group size 4 decoded", lambda M, d, dies: setattr(d[0], "param", 4))])
    # ROW_GATHER k = 7, 512, 2048 (B = 8, G = 96) with narrow rows (the owner rule is what is tested)
    for k, width in ((7, 64), (512, 8), (2048, 4)):
        c = Case(96, DS_CFG)
        N = 16384 if k > 7 else 4096
        ids = np.sort(rng.choice(N, size=k, replace=False)).astype(np.uint32)
        cap = -(-N // 768) * 8
        stores = [np.full((cap, width), np.nan, dtype=F) for _ in range(96)]
        for i in ids:
            own, loc = (int(i) // 8) % 96, (int(i) // 768) * 8 + int(i) % 8
            stores[own][loc] = rng.standard_normal(width).astype(F)
        for r in range(96):
            c.vm_u32(r, 0, ids)
            c.hbm_bytes(r, 1 << 33, stores[r])
            c.hbm_bytes(r, 1 << 35, np.zeros((k, width), dtype=F))
        recs = [Rec("COLL", "ROW_GATHER", param=8, imm_a=k, imm_b=64, desc=dict(
            A=H(1 << 33, width, stride=width * 4), O=H(1 << 35, width, stride=width * 4), I=V(0, k, fmt="U32")),
            tag="row_gather")]

        def swap2(M, d, dies, k=k):                                  # list order broken: ids 0 and 1 swapped
            for dd in dies:
                a, b = int(dd.vm[0]), int(dd.vm[1])
                dd.vm[0], dd.vm[1] = b, a
        vector("CF-COLL", "DS", f"coll_row_gather_k{k}", f"ROW_GATHER k = {k}: owner rank (i div 8) mod 96, local row "
               f"(i div 768) * 8 + i mod 8; ranks 0..63 receive the rows in list order ({width}-word rows)", c, recs,
               mutants=[("list_order", "two selected rows delivered out of list order", swap2)])
    # an unwritten row faults
    c = Case(96, DS_CFG)
    for r in range(96):
        c.vm_u32(r, 0, [3, 9])
        c.hbm_bytes(r, 1 << 33, np.full((8, 16), np.nan if r == 1 else 1.0, dtype=F))
        c.hbm_bytes(r, 1 << 35, np.zeros((2, 16), dtype=F))
    recs = [Rec("COLL", "ROW_GATHER", param=8, imm_a=2, imm_b=64, desc=dict(
        A=H(1 << 33, 16, stride=64), O=H(1 << 35, 16, stride=64), I=V(0, 2, fmt="U32")), tag="row_gather")]
    vector("CF-COLL", "DS", "coll_row_gather_unwritten_faults", "ROW_GATHER of a never-written row (id 9 on rank 1) "
           "faults: completion status 1", c, recs, expect_status=1)


# ----------------------------------------------------------------------------------------------------------------
# CF-TOPK, CF-ARG
# ----------------------------------------------------------------------------------------------------------------
def cf_topk(rng):
    for k, n, m, mode, asc in ((6, 384, 1, "DS", True), (512, 4096, 1, "DS", True), (1, 64, 3, "GENERIC", False),
                               (2, 64, 2, "GENERIC", False), (8, 128, 2, "GENERIC", False),
                               (512, 2048, 2, "GENERIC", False)):
        c = Case(1, DS_CFG)
        v = rng.standard_normal((m, n)).astype(F)
        v[:, 5] = v[:, 9] = np.max(v, axis=1) + 1.0                 # a tie at the top: id 5 before id 9
        c.vm_f32(0, 0, v)
        param = k | (MC.TOPK_ASC if asc else 0)
        recs = [Rec("IDX", "TOPK", param=param, desc=dict(A=V(0, n, m=m, stride=n), O=V(65536, k, m=m, stride=k,
                                                                                            fmt="U32"),
                                                          R=V(131072, k, m=m, stride=k)), tag="topk")]
        vector("CF-TOPK", mode, f"topk_k{k}_n{n}_m{m}{'_asc' if asc else ''}",
               f"IDX.TOPK k = {k} over {m} row(s) of {n}; ties to the lowest index; ids "
               + ("in ASCENDING ID order (param[12], open gap G15: the DS router / index order)" if asc
                  else "by descending score"), c, recs,
               mutants=[("tie_high", "ties resolved to the higher index",
                         lambda M, d, dies: [dd.vm.__setitem__(slice(0, n * m), np.asarray(
                             np.where(np.arange(n * m) % n == 9, np.nextafter(F(v[0, 9]), F(np.inf)),
                                      dd.vm[:n * m].view(F)), dtype=F).view(np.uint32)) for dd in dies])])
    c = Case(1, DS_CFG)
    v = rng.standard_normal(64).astype(F)
    v[7] = np.nan
    c.vm_f32(0, 0, v)
    vector("CF-TOPK", "GENERIC", "topk_nan_fails_closed", "IDX.TOPK with a NaN score faults (status 1)", c,
           [Rec("IDX", "TOPK", param=4, desc=dict(A=V(0, 64), O=V(1024, 4, fmt="U32")), tag="topk")], expect_status=1)


def cf_arg(rng):
    # Qwen die 3: local id 37,983 -> global 151,935 with imm_a = 37,984
    c = Case(4, QW_CFG)
    for r in range(4):
        v = rng.standard_normal(37984).astype(F)
        if r == 3:
            v[37983] = 50.0
        c.vm_f32(r, 0, v)
    recs = [Rec("ARGMAX", "LOCAL", imm_a=37984, desc=dict(A=V(0, 37984), O=V(40000, 2)), tag="argmax_local"),
            Rec("COLL", "ARGMAX_MERGE", desc=dict(A=V(40000, 2), O=V(40004, 1, fmt="U32")), tag="merge"),
            Rec("CTL", "END", desc=dict(A=V(40004, 1, fmt="U32")), tag="end")]
    vector("CF-ARG", "QWEN", "argmax_id_151935", "ARGMAX.LOCAL imm_a = 37,984 on 4 dies; the winner is local id "
           "37,983 on rank 3 = global id 151,935 (the CTL.END token, < cp_vocab)", c, recs,
           mutants=[("no_offset", "global id without RANK * imm_a", lambda M, d, dies: setattr(d[0], "imm_a", 0))])
    c = Case(1, DS_CFG)
    v = rng.standard_normal(1347).astype(F)
    v[[17, 300]] = 9.0
    c.vm_f32(0, 0, v)
    vector("CF-ARG", "DS", "argmax_tie_lowest", "ARGMAX.LOCAL lowest index on ties (17 before 300), O = {value, id}", c,
           [Rec("ARGMAX", "LOCAL", imm_a=1347, desc=dict(A=V(0, 1347), O=V(2048, 2)), tag="argmax_local")])


# ----------------------------------------------------------------------------------------------------------------
# CF-QDQ
# ----------------------------------------------------------------------------------------------------------------
def cf_qdq(rng):
    blocks = [rng.standard_normal(32) * 3, np.zeros(32), np.full(32, 448.0 * 6), rng.standard_normal(32) * 1e-38,
              np.r_[np.full(31, 0.5), 2784.0], np.r_[np.full(31, 0.5), 2785.0], np.r_[np.full(31, 1.0), 3000.0],
              np.r_[np.full(31, 1.0), 1e30], -rng.uniform(0, 1, 32), rng.standard_normal(32) * 1e4]
    x = np.concatenate(blocks).astype(F)
    for op, param, mode in (("QDQ_FP8", 0, "DS"), ("QDQ_FP4_E8M0", 0, "DS"), ("QDQ_FP4_E4M3", 16, "DS")):
        c = Case(1, DS_CFG)
        c.vm_f32(0, 0, x)
        recs = [Rec("FUSED", op, param=param, desc=dict(A=V(0, x.size), O=V(4096, x.size)), tag=op.lower())]

        def block_swap(M, d, dies, op=op):                          # defect: the wrong block size
            GV = MC._golden_v41()
            f = {"QDQ_FP8": lambda v: GV.qdq_fp8(v, 16), "QDQ_FP4_E8M0": lambda v: GV.qdq_fp4_e8m0(v, 16),
                 "QDQ_FP4_E4M3": lambda v: GV.qdq_fp4_e4m3(v, 32)}[op]

            def u(M_, r, L):
                for dd in M_.dies:
                    M_.vm_write(r.desc["O"], dd, L, np.asarray(f(M_.read(r.desc["A"], dd, L)), F))
            M.units = {**M.units, ("FUSED", op): u}
        vector("CF-QDQ", mode, op.lower(), f"FUSED.{op}: random, all-zero, maximum, subnormal, saturating (amax 2,784 "
               "tie / 2,785 / 3,000 / 1e30: the E4M3 scale saturates at 448) and large blocks; the reference is "
               "hdc_golden_v41 (the shipped ot_hdc_fp4qdq has no 448 clamp: its default is exact on DS, whose inputs "
               "stay below 26, but it fails the saturating blocks; SATFINITE opt-in required off DS)", c, recs,
               mutants=[("block_size", "scale blocks of 16 instead of 32 (32 instead of 16 for E4M3)", block_swap)])
    c = Case(1, DS_CFG)
    c.vm_f32(0, 0, x[:64])
    vector("CF-QDQ", "GENERIC", "qdq_fp4_e4m3_block32_undefined", "QDQ_FP4_E4M3 with param[7:0] = 32: undefined block "
           "size faults (status 3) until a vector defines it", c,
           [Rec("FUSED", "QDQ_FP4_E4M3", param=32, desc=dict(A=V(0, 64), O=V(4096, 64)), tag="qdq")], expect_status=3)


# ----------------------------------------------------------------------------------------------------------------
# CF-ATT (G12 ring + C), CF-KV (Qwen linear append + mask)
# ----------------------------------------------------------------------------------------------------------------
def cf_att(rng):
    # DS shape: ring of 128 slots x 512 FP32 (FP8-grid) rows, n = 128, then k selected rows (C); every phase class
    def fp8(a):
        return A.to_fp8(np.asarray(a, dtype=F))
    for pos, k, hd, m_ring, n in ((1048575, 7, 512, 128, 128), (1000, 3, 512, 128, 128),
                                  *[(p, 3, 64, 16, 16) for p in range(16, 32)], (5, 2, 64, 16, 6)):
        c = Case(1, DS_CFG, pos=pos)
        ring = fp8(rng.standard_normal((m_ring, hd)))
        sel = fp8(rng.standard_normal((k, hd)))
        q = A.to_bf16(rng.standard_normal(hd).astype(F))
        T = n + k
        p = A.to_bf16(rng.uniform(0, 1, T).astype(F))
        c.hbm_bytes(0, 1 << 34, ring)
        c.hbm_bytes(0, 1 << 35, sel)
        c.vm_f32(0, 0, q)
        c.vm_f32(0, 1024, p)
        att = dict(B=H(1 << 34, n, m=m_ring, stride=hd * 4), C=H(1 << 35, k, stride=hd * 4))
        prm = 1 | ((hd // 64 - 1) << 4) | (1 << 8)
        recs = [Rec("ATT", "QK", param=prm, desc=dict(A=V(0, hd), O=V(4096, T), **att), tag="qk"),
                Rec("ATT", "PV", param=prm, desc=dict(A=V(1024, T), O=V(8192, hd), **att), tag="pv")]
        first = (pos + 1 - n) % m_ring
        mut = [("ring_from_slot0", "the ring read from slot 0 instead of (POS1 - n) mod m",
                lambda M, d, dies: [setattr(r_, "param", r_.param & ~(1 << 8)) or setattr(r_.desc["B"], "n", n)
                                    for r_ in d[:2]])] if first else []
        mut.append(("no_C", "the second row source ignored", lambda M, d, dies: [r_.desc.pop("C") for r_ in d[:1]]))
        vector("CF-ATT", "DS", f"att_ring_pos{pos}_m{m_ring}_n{n}_k{k}_hd{hd}",
               f"ATT.QK + ATT.PV over a {m_ring}-slot ring (first slot (POS1 - n) mod m = {first}, wrapping) then "
               f"{k} C rows; pos {pos}", c, recs, mutants=mut)
    # Qwen: single B source, n_sel = POS1 (the mask), 4 lanes, FP8 rows
    for pos in (0, 63, 64, 65, 127):
        P = 128
        c = Case(1, QW_CFG, pos=pos)
        K = fp8(rng.standard_normal((P, 128)))
        q = A.to_bf16(rng.standard_normal((4, 128)).astype(F))
        c.hbm_bytes(0, 1 << 34, MC.fp8_encode(K.reshape(-1)))
        c.vm_f32(0, 0, q)
        recs = [Rec("ATT", "QK", param=4 | (1 << 4), desc=dict(
            A=V(0, 128, m=4, stride=128), B=H(1 << 34, 1, stride=128, fmt="FP8E4M3", n_sel=DYN["POS1"]),
            O=V(1024, 1, m=4, stride=P, n_sel=DYN["POS1"])), tag="qk")]
        vector("CF-ATT", "QWEN", f"att_qwen_pos{pos}", f"ATT.QK, 4 lanes, B = n_sel POS1 rows (the causal mask, "
               f"{pos + 1} rows) of a linear FP8 KV plane", c, recs,
               mutants=[("mask_plus1", "one row past the mask read", lambda M, d, dies: [
                   setattr(r_.desc["B"], "n_sel", 0) or setattr(r_.desc["B"], "n", pos + 2) or
                   setattr(r_.desc["O"], "n_sel", 0) or setattr(r_.desc["O"], "n", pos + 2) for r_ in d[:1]])])
    # CF-KV: DMA.STORE linear append at POS (FP8), then a read of the appended row
    c = Case(1, QW_CFG, pos=127)
    c.vm_f32(0, 0, fp8(rng.standard_normal((2, 128))))
    c.hbm_bytes(0, 1 << 34, np.zeros(2 * 2 * 128 * 128, dtype=np.uint8))
    recs = [Rec("DMA", "STORE", desc=dict(A=V(0, 128, m=2, stride=128), O=H(1 << 34, 128, m=2, stride=2 * 128 * 128,
                                                                            fmt="FP8E4M3", dyn_sel=DYN["POS"],
                                                                            dyn_mul=128)), tag="kv_append")]
    vector("CF-KV", "QWEN", "kv_linear_append_pos127", "DMA.STORE of 2 KV heads' K rows at POS (FP8, [kvh][K|V][pos]"
           "[128] planes of 128 positions)", c, recs,
           mutants=[("pos_minus1", "appended at POS - 1", lambda M, d, dies: setattr(d[0].desc["O"], "dyn_sel",
                                                                                      DYN["ZERO"]))])
    # DMA.KVWB_DS: the DS window-ring write-back at slot POS mod m
    for pos in (1048575, 130):
        c = Case(1, DS_CFG, pos=pos)
        c.vm_f32(0, 0, fp8(rng.standard_normal(512)))
        c.hbm_bytes(0, 1 << 34, np.zeros(128 * 2048, dtype=np.uint8))
        recs = [Rec("DMA", "KVWB_DS", desc=dict(A=V(0, 512), O=H(1 << 34, 512, m=128, stride=2048)), tag="kvwb")]
        vector("CF-KV", "DS", f"kvwb_ds_pos{pos}", f"DMA.KVWB_DS window row into ring slot POS mod 128 "
               f"= {pos % 128}", c, recs,
               mutants=[("slot0", "written at slot 0", lambda M, d, dies: setattr(d[0].desc["O"], "m", 1))])


# ----------------------------------------------------------------------------------------------------------------
# CF-NORM, CF-GLU, CF-ROPE, CF-BCAST, CF-EMB, CF-IDXD, CF-CP, CF-LOOP2, CF-0
# ----------------------------------------------------------------------------------------------------------------
def cf_blocks(rng):
    eps = f32u(1e-6)
    # Qwen D4096 prenorm BF16 out, QK-norm seg 128 FP32 out (8 q + 2 k heads a die) in one program
    c = Case(1, QW_CFG)
    x = rng.standard_normal(4096).astype(F) * 3
    qk = rng.standard_normal(1280).astype(F)
    c.vm_f32(0, 0, x)
    c.vm_f32(0, 8192, qk)
    c.hbm_bytes(0, 1 << 34, (A.to_bf16(rng.uniform(0.5, 1.5, 4096).astype(F)).view(np.uint32) >> 16).astype(np.uint16))
    c.hbm_bytes(0, 1 << 35, (A.to_bf16(rng.uniform(0.5, 1.5, 128).astype(F)).view(np.uint32) >> 16).astype(np.uint16))
    recs = [Rec("FUSED", "ROW_NORM", param=32, imm_a=eps, desc=dict(A=V(0, 4096), B=H(1 << 34, 4096, fmt="BF16"),
                                                                     O=V(4096, 4096, fmt="BF16")), tag="prenorm"),
            Rec("FUSED", "ROW_NORM", param=8 | (128 << 6), imm_a=eps, desc=dict(
                A=V(8192, 1024), B=H(1 << 35, 128, fmt="BF16"), O=V(12288, 1024)), tag="qknorm.q"),
            Rec("FUSED", "ROW_NORM", param=2 | (128 << 6), imm_a=eps, desc=dict(
                A=V(8192 + 1024, 256), B=H(1 << 35, 128, fmt="BF16"), O=V(12288 + 1024, 256)), tag="qknorm.k")]
    vector("CF-NORM", "QWEN", "norm_d4096_bf16_and_qknorm_seg128_fp32", "FUSED.ROW_NORM: D4096 BF16 out (d_units 32), "
           "then QK-norm seg 128 FP32 out for 8 q heads (d_units 8) and 2 k heads (d_units 2) in one program", c, recs,
           mutants=[("qknorm_bf16", "QK-norm published BF16", lambda M, d, dies: setattr(d[1].desc["O"], "fmt", "BF16")),
                    ("seg64", "segment decoded as 64",
                     lambda M, d, dies: setattr(d[1], "param", 8 | (64 << 6)))])
    # SFU.GLU Qwen: BF16 out, FLT_MAX clamp, route 1.0 by ibcast, 3,072 a die
    c = Case(1, QW_CFG)
    c.vm_f32(0, 0, rng.standard_normal(2 * 3072).astype(F) * 4)
    c.vm_f32(0, 8192, [1.0])
    recs = [Rec("SFU", "GLU", imm_a=FLT_MAX, desc=dict(A=V(0, 3072), B=V(3072, 3072), C=V(8192, 3072, ibcast=1),
                                                       O=V(16384, 3072, fmt="BF16")), tag="swiglu")]
    vector("CF-GLU", "QWEN", "glu_bf16_noclamp_route1", "SFU.GLU 3,072 a die: BF16 out, imm_a = FLT_MAX, C = 1.0 by "
           "ibcast", c, recs,
           mutants=[("clamp10", "the DS clamp 10.0 left on", lambda M, d, dies: setattr(d[0], "imm_a", f32u(10.0))),
                    ("fp32_out", "not rounded to BF16", lambda M, d, dies: setattr(d[0].desc["O"], "fmt", "FP32"))])
    c = Case(1, DS_CFG)
    c.vm_f32(0, 0, rng.standard_normal(2 * 2304).astype(F) * 8)
    c.vm_f32(0, 8192, [0.37])
    recs = [Rec("SFU", "GLU", imm_a=f32u(10.0), desc=dict(A=V(0, 2304), B=V(2304, 2304), C=V(8192, 2304, ibcast=1),
                                                          O=V(16384, 2304)), tag="swiglu")]
    vector("CF-GLU", "DS", "glu_clamp10_routew_fp32", "SFU.GLU with the DS clamp 10.0 and a route weight 0.37 by ibcast "
           "(FP32 out here; the DS FP8 publication is FUSED.QDQ_FP8 / the DS chain)", c, recs,
           mutants=[("no_clamp", "clamp disabled", lambda M, d, dies: setattr(d[0], "imm_a", FLT_MAX))])
    # CF-ROPE: Qwen permuted-weight 128-dim RoPE (adjacent pairs, b_half tables) on 10 heads
    c = Case(1, QW_CFG, pos=8191)
    xv = rng.standard_normal(10 * 128).astype(F)
    cos, sin = A.rope_tables(np.array([8191]), 128, 1e6)
    c.vm_f32(0, 0, xv)
    c.vm_f32(0, 4096, np.concatenate([cos[0], sin[0]]))
    recs = [Rec("SU", "VOP", sut=sut(m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q, c_pair=1, b_half=1, dst=I.DST_VM),
                desc=dict(A=V(0, 128, m=10, stride=128), B=V(4096, 64, m=10, stride=0),
                          D=V(4096 + 64, 64, m=10, stride=0),
                          O=V(8192, 128, m=10, stride=128)), tag="rope")]
    perm = A.rope_perm_index(128)
    c_un = copy.deepcopy(c)
    c_un.vm_f32(0, 0, xv.reshape(10, 128)[:, np.argsort(perm)].reshape(-1))      # unpermuted rows
    vector("CF-ROPE", "QWEN", "rope_qwen_permuted_128", "SU RoPE on rows already permuted offline (pairs (2t, 2t + 1) "
           "at angle t, c_pair = i XOR 1, cos / sin tables of 64 read through b_half), 8 q + 2 k heads, pos 8,191",
           c, recs, mutants=[("unpermuted", "the image keeps the checkpoint's split-half row order", (recs, c_un))])
    c = Case(1, DS_CFG, pos=1048575)
    xv = rng.standard_normal(512).astype(F)
    c.vm_f32(0, 0, xv)
    c.vm_f32(0, 1024, rng.uniform(-1, 1, 64).astype(F))
    recs = [Rec("SU", "VOP", sut=sut(m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q, c_pair=1, b_half=1, rnd=1, dst=I.DST_VM),
                desc=dict(A=V(448, 64), B=V(1024, 64), D=V(1024 + 32, 64), O=V(2048 + 448, 64)), tag="rope_tail")]
    vector("CF-ROPE", "DS", "rope_ds_tail64", "DS adjacent-pair RoPE on the last 64 of a 512 row, BF16 out", c, recs,
           mutants=[("pair_xor32", "pairs i, i + 32 (split-half)", lambda M, d, dies: setattr(
               d[0].desc["A"], "base", 449))])
    # CF-BCAST
    c = Case(1, QW_CFG)
    c.vm_f32(0, 0, rng.standard_normal(8 * 128).astype(F))
    c.vm_f32(0, 2048, rng.uniform(1, 2, 8).astype(F))
    recs = [Rec("SU", "VOP", sut=sut(m1=I.M1_DIVB, dst=I.DST_VM), desc=dict(
        A=V(0, 128, m=8, stride=128), B=V(2048, 128, m=8, stride=1, ibcast=1), O=V(4096, 128, m=8, stride=128)),
        tag="pv_normalize")]
    vector("CF-BCAST", "QWEN", "bcast_per_row_scalar", "MDESC ibcast: a per-row scalar (the softmax normaliser of 8 "
           "heads) read by every element of its row", c, recs,
           mutants=[("istride1", "ibcast ignored (inner stride 1)", lambda M, d, dies: setattr(d[0].desc["B"],
                                                                                               "ibcast", 0))])
    # CF-EMB: row 151,935 INT8 + BF16 scale, 4,128 B rows
    c = Case(1, QW_CFG, token=151935)
    emb = np.zeros(4128, dtype=np.uint8)                      # only row 151,935 of the EMBED region is materialised
    emb[:4096] = rng.integers(-128, 128, 4096).astype(np.int8).view(np.uint8)
    emb[:3] = np.array([-128, 127, 0], dtype=np.int8).view(np.uint8)
    emb[4096:4098] = np.array([0x3C23], dtype=np.uint16).view(np.uint8)
    c.hbm_bytes(0, (1 << 34) + 151935 * 4128, emb)
    recs = [Rec("DMA", "LOAD", desc=dict(A=H(1 << 34, 4096, fmt="INT8", dyn_sel=DYN["TOKEN"], dyn_mul=4128),
                                         O=V(0, 4096)), tag="embedding.codes"),
            Rec("DMA", "LOAD", desc=dict(A=H((1 << 34) + 4096, 1, fmt="BF16", dyn_sel=DYN["TOKEN"], dyn_mul=4128),
                                         O=V(8192, 1)), tag="embedding.scale"),
            Rec("SU", "VOP", sut=sut(m1=I.M1_AB, dst=I.DST_VM), desc=dict(A=V(0, 4096), B=V(8192, 4096, ibcast=1),
                                                                          O=V(0, 4096)), tag="embedding.dequant")]
    vector("CF-EMB", "QWEN", "emb_int8_row151935", "embedding of token 151,935: INT8 codes (incl. -128, 127, 0) x the "
           "row's BF16 scale, rows of 4,128 B at TOKEN x 4,128", c, recs,
           mutants=[("row_stride_4096", "row stride 4,096 (no scale / pad)", lambda M, d, dies: [
               setattr(d[k].desc["A"], "dyn_mul", 4096) for k in (0, 1)])])
    # CF-IDXD: expert fetch by id (SM.MATVEC with an indexed B over an I table), n from VM, out-of-range id
    c = Case(1, QW_CFG)
    E, R_, K = 8, 16, 64
    W8 = rng.integers(-128, 128, (E, R_, K)).astype(np.int8)
    c.hbm_bytes(0, 1 << 34, W8)
    c.vm_f32(0, 0, A.to_bf16(rng.standard_normal(K).astype(F)))
    c.vm_u32(0, 1024, [5, 2])
    recs = [Rec("CTL", "LOOP", param=2, tag="experts"),
            Rec("SM", "MATVEC", param=3, desc=dict(A=V(0, K), B=H(1 << 34, K, m=R_, stride=K, fmt="INT8", indexed=1,
                                                                   dyn_mul=R_ * K),
                                                   O=V(2048, R_, lstride=R_), I=V(1024, 2, fmt="U32")), tag="expert"),
            Rec("CTL", "ENDLOOP", tag="experts")]
    vector("CF-IDXD", "GENERIC", "idxd_expert_fetch_by_id", "SM.MATVEC fmt 3 with an indexed B (expert id = "
           "U32(VM[I + L])) in a 2-iteration CTL.LOOP: experts 5 then 2", c, recs,
           mutants=[("ignore_index", "the id term dropped (expert 0)", lambda M, d, dies: setattr(
               d[1].desc["B"], "indexed", 0))])
    c2 = copy.deepcopy(c)
    c2.vm_u32(0, 1024, [5, 9])
    vector("CF-IDXD", "GENERIC", "idxd_out_of_range_faults", "an indexed id past the weight region faults (status 3)",
           c2, recs, expect_status=3)
    c = Case(1, QW_CFG)
    c.hbm_bytes(0, 1 << 34, rng.standard_normal(64).astype(F))
    c.vm_u32(0, 1024, [0, 37])
    recs = [Rec("DMA", "LOAD", desc=dict(A=H(1 << 34, 0, n_sel=HGI.NSEL_FROM_VM), O=V(0, 0, n_sel=HGI.NSEL_FROM_VM),
                                         I=V(1024, 1, stride=1, fmt="U32")), tag="load_n_from_vm")]
    vector("CF-IDXD", "GENERIC", "idxd_n_from_vm", "n_sel = 63: n = U32(VM[I + I.stride + L]) = 37 elements", c, recs,
           mutants=[("static_n", "n_sel 63 ignored (n = 0 -> nothing moved)", lambda M, d, dies: [
               setattr(d[0].desc[k], "n_sel", 0) or setattr(d[0].desc[k], "n", 36) for k in ("A", "O")])])
    # CF-LOOP2: two-level loop with l1stride and L1
    c = Case(1, QW_CFG)
    c.vm_f32(0, 0, rng.standard_normal(4 * 3 * 16).astype(F))
    recs = [Rec("CTL", "LOOP", param=3, tag="L"),
            Rec("CTL", "LOOP", param=4 | (1 << 16), tag="L1"),
            Rec("SU", "VOP", sut=sut(m1=I.M1_AIMM, imm1=f32u(2.0), red=I.RED_SUM, dst=I.DST_VM), desc=dict(
                A=V(0, 16, lstride=64, l1stride=16), O=V(1024, 16, lstride=64, l1stride=16),
                R=V(4096, 1, lstride=4, l1stride=1)), tag="body"),
            Rec("CTL", "ENDLOOP", tag="L1"), Rec("CTL", "ENDLOOP", tag="L")]
    vector("CF-LOOP2", "GENERIC", "loop2_l1stride", "CTL.LOOP level 0 (3) around level 1 (4): base + L lstride + L1 "
           "l1stride on A, O and R", c, recs,
           mutants=[("l1_as_l", "level-1 counter driving lstride", lambda M, d, dies: setattr(
               d[2].desc["A"], "l1stride", 0))])
    # CF-CP: doorbell range, END range, absent unit
    for tok, pos, st in ((131071, 0, 0), (131072, 0, 0), (151935, 40959, 0), (151936, 0, 3), (0, 40960, 3)):
        c = Case(1, QW_CFG, pos=pos, token=tok)
        try:
            M = MC.Machine(c.build(), MC.UNITS)
            M.cfg.update(c.cfg)
            M.doorbell(tok, pos)
            got = 0
        except MC.Fault as e:
            got = e.status
        assert got == st
        VECTORS.append(dict(id=f"cp_doorbell_tok{tok}_pos{pos}", row="CF-CP", mode="QWEN",
                            what="doorbell range check against cp_vocab 151,936 / cp_ctx_max 40,960",
                            cfg=c.cfg, doorbell=dict(token=tok, pos=pos), expect=dict(status=st)))
    c = Case(1, DS_CFG, pos=(1 << 20) - 1, token=129279)
    vector("CF-CP", "DS", "cp_ds_pos_max", "DS reset: token 129,279 and position 2^20 - 1 accepted", c, [])
    c = Case(1, QW_CFG)
    c.vm_u32(0, 0, [151936])
    vector("CF-CP", "QWEN", "cp_end_token_range", "CTL.END token 151,936 >= cp_vocab: status 3", c,
           [Rec("CTL", "END", desc=dict(A=V(0, 1, fmt="U32")), tag="end")], expect_status=3)
    c = Case(1, QW_CFG)
    vector("CF-CP", "QWEN", "cp_absent_unit_simt", "a SIMT.RUN record on r25 (no SIMT unit) faults with status 3", c,
           [Rec("SIMT", "RUN", param=0, imm_a=1, tag="simt")], expect_status=3)


def cf0():
    out = []
    for name in ("ds_v41_flash", "qwen3_8b"):
        man, mb, md, words = HGI.d_build(name)
        cases = dict(ok=words)
        w = list(words); w[0] ^= 1; cases["bad_magic"] = w
        w = list(words); w[1] ^= 1; cases["bad_version"] = w
        w = list(words); w[40] ^= 1; cases["bad_crc"] = w
        for k, val in (("group_12", 12), ("group_16", 16)):
            w = list(words); w[46] = (w[46] & ~0xFF) | val; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); cases[k] = w
        w = list(words); w[44] |= 1; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); cases["reserved_bit"] = w
        w = list(words); w[40] = 1 << 18; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); cases["vocab_2p18"] = w
        for k, w in cases.items():
            out.append(dict(id=f"cfg_{name}_{k}", row="CF-0", mode="DS" if name.startswith("ds") else "QWEN",
                            what="CFG_COMMIT of the descriptor words", words=[f"{x:08x}" for x in w],
                            expect=dict(err=HGI.ERR[HGI.d_hw_check(w)], err_code=HGI.d_hw_check(w))))
        out.append(dict(id=f"cfg_{name}_busy", row="CF-0", mode="DS" if name.startswith("ds") else "QWEN",
                        what="CFG_COMMIT while a job runs", words=[f"{x:08x}" for x in words],
                        expect=dict(err="E_BUSY", err_code=4)))
    VECTORS.extend(out)


def cf_ehash():
    """CF-EHASH: the producer function and its values (IDX.EHASH is not modelled as a unit; the golden is
    hdc_golden_v41.EngramTables.hashes)."""
    try:
        import hdc_golden_v41 as GV
        import rtl_v41_fullshape_layer_campaign as LC         # the released DS-V4.1-Flash config and tokenizer
        c = json.loads(Path(LC.CONFIG).read_text())
        tok = GV.TOKENIZER
        GV.TOKENIZER = LC.HF / "tokenizer.json"
        try:
            et = GV.EngramTables(c, c["vocab_size"])
        finally:
            GV.TOKENIZER = tok
    except Exception as e:                                       # noqa: BLE001
        VECTORS.append(dict(id="ehash_unavailable", row="CF-EHASH", mode="DS", what=f"not generated: {e}"))
        return
    try:
        import w19_hbm_tp96_isa as W
        hist = list(json.loads(W.REF_RECORD.read_text())["token_history"])[-32:]
    except Exception:                                            # noqa: BLE001
        hist = list(range(1000, 1032))
    rows = []
    for t in range(1, len(hist) + 1):
        rows.append(dict(history_len=t, token=int(hist[t - 1]),
                         ids={str(lid): et.hashes(hist[:t], li).astype(np.int64).tolist()
                              for li, lid in enumerate(et.layer_ids)}))
    accept = dict(accepted_history=hist[:20], rejected_draft=hist[20:23],
                  ids_after_accept={str(lid): et.hashes(hist[:20], li).tolist() for li, lid in enumerate(et.layer_ids)})
    VECTORS.append(dict(
        id="ehash_ds_token_sequence", row="CF-EHASH", mode="DS",
        what="Engram row ids of every Engram layer for each prefix of a token sequence (O of IDX.EHASH, one id per "
             "head and n-gram order, order: n-gram 2..n, heads within); ACCEPT restores the history to the last "
             "accepted slot (ids after a rejected 3-token draft = ids of the accepted prefix)",
        producer="tools/hdc_golden_v41.py EngramTables.hashes (constants: primes [layer][ngram-1][head], offsets, "
                 "multipliers [layer][n] int64, token_map (compressed vocabulary), pad)",
        constants=dict(layer_ids=et.layer_ids, n=et.n, primes=et.primes.tolist(), offsets=et.offsets.tolist(),
                       multipliers=[[str(int(x)) for x in row] for row in et.multipliers], pad=et.pad,
                       token_map_sha256=hashlib.sha256(np.asarray(et.token_map, np.int64).tobytes()).hexdigest(),
                       token_map_len=int(len(et.token_map))),
        sequence=rows, accept=accept))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(20261009)
    cf0()
    cf_blocks(rng)
    cf_coll(rng)
    cf_topk(rng)
    cf_arg(rng)
    cf_qdq(rng)
    cf_att(rng)
    cf_ehash()
    a.out.mkdir(parents=True, exist_ok=True)
    idx = []
    for v in VECTORS:
        p = a.out / f"{v['row'].lower()}__{v['id']}.json"
        p.write_text(json.dumps(v, indent=1, default=int) + "\n")
        idx.append(dict(id=v["id"], row=v["row"], mode=v["mode"], file=p.name, what=v["what"],
                        status=v.get("expect", {}).get("status", v.get("expect", {}).get("err")),
                        mutants=[m["name"] for m in v.get("mutants", [])],
                        sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    src = {p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
        "hgi_sim/conformance.py", "hgi_sim/machine.py", "hgi_sim/records.py", "hgi_sim/lib.py",
        "hbm_generic_iface.py", "hdc_golden_v41.py")}
    (a.out / "index.json").write_text(json.dumps(dict(
        schema="opentallas.hgi_conformance_vectors.v1", spec="docs/HBM_GENERIC_INTERFACE.md section 8.4",
        encoding=f"HGI-1 {HGI.D_VERSION[0]}.{HGI.D_VERSION[1]} owner-approved (records: hbm_generic_iface D_UOP_FIELDS / "
                 "D_MDESC_FIELDS / D_SUT_LAYOUT / D_OPS)",
        modes=dict(DS="the DS reset / DS per-operation values (CF-1 equivalence side)",
                   QWEN="Qwen3-8B per-operation values", GENERIC="other models (generic interface)"),
        provisional=["IDX.TOPK param[12] = 1: ids in ascending id order (open gap G15; DS router / index order)"],
        not_covered=["CF-SFX (FUSED.SOFTMAX is not bound yet; the SU fallback is)", "CF-SM format 3 (hbm-forks owns "
                     "the fmt3 adapter; SM.MATVEC fmt 3 vectors: CF-IDXD and the Qwen token)",
                     "CF-SVC / CF-GDN / CF-PROG as timing or whole-program checks: see qwen / ds / gdn evidence"],
        vectors=idx, sources=src), indent=1) + "\n")
    print(f"{len(VECTORS)} vectors -> {a.out}")
    for row in sorted({v['row'] for v in VECTORS}):
        print(row, sum(v["row"] == row for v in VECTORS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
