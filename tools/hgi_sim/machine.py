"""hgi_sim: the HGI-1 v0.9 die simulator (docs/HBM_GENERIC_INTERFACE.md section 4), functional core.

Inputs are the artifacts the die consumes: the 64-word model descriptor (loaded through the config path with every
check and error code of section 1.4), the program image (encoded records, decoded here), each die's HBM image, and
doorbells.  Outputs: the completion, a per-record trace (unit, op, hashes of every operand and result buffer), the
HBM / VM write log, faults.

FUNCTIONAL MODEL.  Records execute in program order on every die of the group (SPMD; collectives join all dies at
the same record).  A unit op's arithmetic is the shared library (lib.py) and, for SU.VOP, Machine.su1's pipeline
(tools/hdc_program_v41.py) restated over HGI descriptors.  In-order program semantics is what the die computes iff the
program's `wait` masks, STREAM credits, collectives and FENCEs order every hazard; the timing model (timing.py)
checks exactly that and reports any record that would read a region before its producer retired (RACE).

Addressing (section 3.2): effective base = base + L * lstride + DYN[dyn_sel] * dyn_mul; n = DYN[n_sel] if n_sel;
element (o, i) at eb + o * stride + i * istride' (istride' = 1 when 0, 0 when 0xFFFF -- provisional reading G3).
VM addresses and strides are FP32 words; HBM addresses and outer strides are bytes, inner strides elements.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hbm_generic_iface as HGI  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

from . import lib as A  # noqa: E402
from .records import ISTRIDE_BCAST, MDesc, Rec, decode_program  # noqa: E402

F = np.float32
VM_WORDS = 1 << 18
IDX_DYN = 31                     # provisional C3b: dyn_sel code of an indexed descriptor
ESIZE = {"FP32": 4, "BF16": 2, "FP8E4M3": 1, "INT8": 1, "U32": 4, "UE8M0": 1, "FP4E2M1": 1}
_E4M3 = None


class Fault(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status          # completion status: 1 unit fault, 2 no result, 3 bad command / range


def e4m3_table():
    global _E4M3
    if _E4M3 is None:
        out = np.zeros(256, dtype=np.float64)
        for c in range(256):
            s, e, m = c >> 7, (c >> 3) & 15, c & 7
            if e == 15 and m == 7:
                v = np.nan
            elif e == 0:
                v = m / 8 * 2.0 ** -6
            else:
                v = (1 + m / 8) * 2.0 ** (e - 7)
            out[c] = -v if s else v
        _E4M3 = out.astype(F)
    return _E4M3


def fp8_encode(v):
    """FP32 values already on the E4M3 grid (to_fp8 output) -> bytes; +0 -> 0x00, -0 never occurs (canonical)."""
    t = e4m3_table()
    v = np.asarray(v, dtype=F).reshape(-1)
    order = np.argsort(t[:127])                       # positive codes 0..126 (0x7F is NaN)
    pos = np.abs(v)
    k = np.searchsorted(t[:127][order], pos)
    k = np.minimum(k, 126)
    codes = order[k].astype(np.uint8)
    if not np.array_equal(t[codes], pos):
        raise Fault(1, "FP8 store of a value off the E4M3 grid")
    return np.where((v < 0), codes | 0x80, codes).astype(np.uint8)


# ----------------------------------------------------------------------------------------------------------------
# memories
# ----------------------------------------------------------------------------------------------------------------
class Hbm:
    """A die's 40-bit HBM byte space as regions (base -> uint8 array); regions may be shared read-only between dies."""

    def __init__(self):
        self.regions: list[tuple[int, np.ndarray, str]] = []
        self.writes = 0

    def add(self, base, data, name=""):
        data = np.asarray(data).view(np.uint8).reshape(-1)
        if base % 32:
            raise ValueError(f"region {name} base not 32 B aligned")
        for b, d, n in self.regions:
            if base < b + d.size and b < base + data.size:
                raise ValueError(f"region {name} overlaps {n}")
        self.regions.append((base, data, name))
        self.regions.sort(key=lambda r: r[0])

    def find(self, addr, nbytes):
        for b, d, n in self.regions:
            if b <= addr and addr + nbytes <= b + d.size:
                return d, addr - b, n
        raise Fault(3, f"HBM access [{addr:#x}, +{nbytes}) outside every region")

    def view(self, addr, nbytes):
        d, off, _ = self.find(addr, nbytes)
        return d[off:off + nbytes]


class Die:
    def __init__(self, rank, hbm: Hbm):
        self.rank = rank
        self.vm = np.zeros(VM_WORDS, dtype=np.uint32)
        self.hbm = hbm
        self.dyn = [0] * 32


# ----------------------------------------------------------------------------------------------------------------
# the machine
# ----------------------------------------------------------------------------------------------------------------
class Machine:
    def __init__(self, dies, units=None):
        self.dies = dies
        self.cfg = dict(HGI.RESET)                 # active section-C values: reset = DS
        self.cfg_status = dict(loaded=False, err=0)
        self.trace = []
        self.units = units or {}
        self.busy = False

    # -- config path (section 1.2 - 1.4) ---------------------------------------------------------------------------
    def cfg_commit(self, words, busy=False):
        err = HGI.hw_check(list(words), busy=busy or self.busy)
        if err:
            self.cfg_status = dict(loaded=self.cfg_status["loaded"], err=err)
            return err
        md = HGI.unpack(list(words))
        for k in HGI.RESET:
            self.cfg[k] = md[k]
        self.cfg_status = dict(loaded=True, err=0)
        return 0

    # -- addressing ------------------------------------------------------------------------------------------------
    def eff(self, d: MDesc, die: Die, L):
        if d.dyn_sel == IDX_DYN:
            # C3b (provisional): an INDEXED descriptor; the dispatcher reads the U32 index at VM[lstride] and adds
            # index * dyn_mul to the base (the record cannot also use L * lstride)
            idx = int(die.vm[d.lstride])
            base = d.base + idx * d.dyn_mul
        else:
            base = d.base + L * d.lstride + die.dyn[d.dyn_sel] * d.dyn_mul
        n = die.dyn[d.n_sel] if d.n_sel else d.n
        ist = 0 if d.istride == ISTRIDE_BCAST else (d.istride or 1)
        return base, n, d.m, d.stride, ist

    def vm_addrs(self, d, die, L, no=None, ni=None):
        base, n, m, st, ist = self.eff(d, die, L)
        no = m if no is None else no
        ni = n if ni is None else ni
        o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
        a = (base + o * st + i * ist).reshape(-1)
        if a.size and (a.min() < 0 or a.max() >= VM_WORDS):
            raise Fault(3, "VM access out of range")
        return a

    def vm_read(self, d, die, L, no=None, ni=None):
        return die.vm[self.vm_addrs(d, die, L, no, ni)].view(F)

    def vm_write(self, d, die, L, vals, no=None, ni=None):
        a = self.vm_addrs(d, die, L, no, ni)
        die.vm[a] = np.asarray(vals, dtype=F).reshape(-1).view(np.uint32)

    def hbm_read(self, d, die, L, no=None, ni=None):
        """Elements of an HBM descriptor, decoded to FP32 (INT8 codes as their exact values)."""
        base, n, m, st, ist = self.eff(d, die, L)
        no = m if no is None else no
        ni = n if ni is None else ni
        es = ESIZE[d.fmt]
        rows = []
        for o in range(no):
            ra = base + o * st
            if ist == 1:
                raw = die.hbm.view(ra, ni * es)
            else:
                raw = np.concatenate([die.hbm.view(ra + i * ist * es, es) for i in range(ni)])
            rows.append(raw)
        raw = np.stack(rows) if rows else np.zeros((0, ni * es), dtype=np.uint8)
        return decode_fmt(raw, d.fmt).reshape(no, ni)

    def hbm_rows_raw(self, d, die, L):
        """[m, n] raw bytes of a contiguous-row HBM operand (weights): a strided view, no copy."""
        base, n, m, st, ist = self.eff(d, die, L)
        es = ESIZE[d.fmt]
        if ist != 1:
            raise Fault(3, "weight operand must be inner-contiguous")
        span = (m - 1) * st + n * es
        buf, off, _ = die.hbm.find(base, span)
        return np.lib.stride_tricks.as_strided(buf[off:], shape=(m, n * es), strides=(st, 1))

    def hbm_write(self, d, die, L, vals):
        base, n, m, st, ist = self.eff(d, die, L)
        es = ESIZE[d.fmt]
        v = np.asarray(vals, dtype=F).reshape(m, n)
        for o in range(m):
            raw = encode_fmt(v[o], d.fmt)
            if ist == 1:
                die.hbm.view(base + o * st, n * es)[:] = raw
            else:
                for i in range(n):
                    die.hbm.view(base + o * st + i * ist * es, es)[:] = raw[i * es:(i + 1) * es]
            die.hbm.writes += n * es

    def read(self, d, die, L, no=None, ni=None):
        if d.space == "VM":
            return self.vm_read(d, die, L, no, ni)
        if d.space == "HBM":
            return self.hbm_read(d, die, L, no, ni).reshape(-1)
        raise Fault(3, f"unsupported operand space {d.space}")

    # -- execution -------------------------------------------------------------------------------------------------
    def doorbell(self, token, pos, slot_count=1):
        if not 0 <= token < self.cfg["cp_vocab"] or not 0 <= pos < self.cfg["cp_ctx_max"]:
            raise Fault(3, "doorbell token / position out of range")
        for die in self.dies:
            die.dyn[:8] = [0, pos, pos + 1, token, 0, die.rank, 0, pos]

    def run(self, image: bytes, token, pos, hash_bufs=True):
        """Execute one doorbell: returns (completion token, trace)."""
        recs = decode_program(image)
        self.doorbell(token, pos)
        self.trace = []
        self.result = None
        pc, loop = 0, None
        L = 0
        while pc < len(recs):
            r = recs[pc]
            for die in self.dies:
                die.dyn[4] = L
            if not self.pred(r, L, loop):
                pc += 1
                continue
            if r.unit == "CTL":
                if r.op == "LOOP":
                    loop = dict(start=pc + 1, count=r.param)
                    L = 0
                    pc += 1
                    continue
                if r.op == "ENDLOOP":
                    if loop is None:
                        raise Fault(3, "ENDLOOP without LOOP")
                    L += 1
                    if L < loop["count"]:
                        pc = loop["start"]
                        continue
                    loop, L = None, 0
                    pc += 1
                    continue
                if r.op == "END":
                    toks = [int(self.read(r.desc["A"], die, L).view(np.uint32)[0]) for die in self.dies]
                    if len(set(toks)) != 1:
                        raise Fault(1, f"dies disagree on the token {toks}")
                    if toks[0] >= self.cfg["cp_vocab"]:
                        raise Fault(3, "END token >= cp_vocab")
                    self.trace.append(dict(pc=pc, L=L, unit="CTL", op="END", tag=r.tag))
                    self.result = toks[0]
                    return toks[0], self.trace
                pc += 1            # NOP / FENCE: ordering only (timing model)
                continue
            fn = self.units.get((r.unit, r.op))
            if fn is None:
                raise Fault(3, f"no unit model for {r.unit}.{r.op}")
            fn(self, r, L)
            ent = dict(pc=pc, L=L, unit=r.unit, op=r.op, tag=r.tag, family=r.family)
            if hash_bufs:
                ent["out"] = self.hash_out(r, L)
            self.trace.append(ent)
            pc += 1
        raise Fault(2, "program ended without END")

    def pred(self, r, L, loop):
        p = r.pred
        pos = self.dies[0].dyn[1]
        if p == "ALWAYS":
            return True
        if p == "POS0":
            return pos == 0
        if p == "NOT_POS0":
            return pos != 0
        return loop is not None and L == loop["count"] - 1

    def hash_out(self, r, L):
        h = hashlib.sha256()
        for k in ("O", "R"):
            d = r.desc.get(k)
            if d is None or d.space != "VM":
                continue
            for die in self.dies:
                try:
                    h.update(self.vm_read(d, die, L).tobytes())
                except Fault:
                    pass
        return h.hexdigest()[:16]


def decode_fmt(raw, fmt):
    raw = np.ascontiguousarray(raw)
    if fmt == "FP32" or fmt == "U32":
        return raw.view(np.uint32).view(F) if fmt == "FP32" else raw.view(np.uint32).astype(np.float64)
    if fmt == "BF16":
        return (raw.view(np.uint16).astype(np.uint32) << 16).view(F)
    if fmt == "INT8":
        return raw.view(np.int8).astype(F)
    if fmt == "FP8E4M3":
        return e4m3_table()[raw]
    raise Fault(3, f"fmt {fmt} not decodable here")


def encode_fmt(v, fmt):
    v = np.asarray(v, dtype=F)
    if fmt == "FP32":
        return v.view(np.uint8)
    if fmt == "BF16":
        return (A.to_bf16(v).view(np.uint32) >> 16).astype(np.uint16).view(np.uint8)
    if fmt == "FP8E4M3":
        return fp8_encode(A.to_fp8(v))
    raise Fault(3, f"store fmt {fmt} unsupported")


# ----------------------------------------------------------------------------------------------------------------
# unit models
# ----------------------------------------------------------------------------------------------------------------
def u_dma_load(M: Machine, r: Rec, L):
    for die in M.dies:
        a, o = r.desc["A"], r.desc["O"]
        vals = M.read(a, die, L)
        if a.fmt == "U32":
            die.vm[M.vm_addrs(o, die, L)] = vals.astype(np.uint32)
        else:
            M.vm_write(o, die, L, vals)


def u_dma_store(M: Machine, r: Rec, L):
    for die in M.dies:
        M.hbm_write(r.desc["O"], die, L, M.read(r.desc["A"], die, L))


def u_dma_fence(M, r, L):
    pass


def u_sm_matvec(M: Machine, r: Rec, L):
    fmt = r.param & 3
    a, b, o = r.desc["A"], r.desc["B"], r.desc["O"]
    want = {0: "BF16", 1: "FP8E4M3", 2: "FP4E2M1", 3: "INT8"}[fmt]
    if b.fmt != want:
        raise Fault(3, f"SM fmt {fmt} with a {b.fmt} weight descriptor")
    if fmt not in (0, 3):
        raise Fault(3, "block-dot SM formats run through the DS path")
    for die in M.dies:
        x = M.read(a, die, L)
        raw = M.hbm_rows_raw(b, die, L)
        w = raw.view(np.int8) if fmt == 3 else (np.ascontiguousarray(raw).view(np.uint16).astype(np.uint32) << 16).view(F)
        if w.shape[1] != x.size:
            raise Fault(3, f"SM K {w.shape[1]} != activation length {x.size}")
        M.vm_write(o, die, L, A.sm_int8(w, x))


def u_coll_all_reduce(M: Machine, r: Rec, L):
    g = M.cfg["coll_group_size"]
    dies = M.dies
    for s in range(0, len(dies), g):
        grp = dies[s:s + g]
        parts = [M.read(r.desc["A"], d, L) for d in grp]
        tot = A.pairwise(parts)
        for d in grp:
            M.vm_write(r.desc["O"], d, L, tot)


def u_argmax_local(M: Machine, r: Rec, L):
    for die in M.dies:
        v = M.read(r.desc["A"], die, L)
        j = A.argmax(v)
        a = M.vm_addrs(r.desc["O"], die, L, 1, 2)
        die.vm[a[0]] = np.asarray([v[j]], dtype=F).view(np.uint32)[0]
        die.vm[a[1]] = np.uint32(j)


def u_coll_argmax_merge(M: Machine, r: Rec, L):
    g, rows = M.cfg["coll_group_size"], M.cfg["coll_head_rows"]
    dies = M.dies
    for s in range(0, len(dies), g):
        grp = dies[s:s + g]
        vals, ids = [], []
        for k, d in enumerate(grp):
            a = M.vm_addrs(r.desc["A"], d, L, 1, 2)
            vals.append(d.vm[a[0]:a[0] + 1].view(F)[0])
            ids.append(int(d.vm[a[1]]) + (k * rows if rows else 0))
        order = np.lexsort((np.array(ids), -np.array(vals, dtype=np.float64)))
        tok = ids[order[0]]
        for d in grp:
            d.vm[M.vm_addrs(r.desc["O"], d, L, 1, 1)] = np.uint32(tok)


def u_row_norm(M: Machine, r: Rec, L):
    seg = r.param & 0xFF
    eps = np.uint32(r.imm_a).view(F)
    a, b, o = r.desc["A"], r.desc["B"], r.desc["O"]
    for die in M.dies:
        x = M.read(a, die, L)
        g = M.read(b, die, L)
        y = A.row_norm(x, g, eps, seg)
        if o.fmt == "BF16":
            y = A.to_bf16(y)
        M.vm_write(o, die, L, y)


def u_glu(M: Machine, r: Rec, L):
    c = M.cfg
    for die in M.dies:
        g, u = M.read(r.desc["A"], die, L), M.read(r.desc["B"], die, L)
        rw = None if c["glu_routew_off"] else M.read(r.desc["C"], die, L)[0]
        lim = None if c["glu_clamp_off"] else np.uint32(r.imm_a).view(F)
        y = A.glu(g, u, limit=lim, route_w=rw, out_bf16=bool(c["glu_out_bf16"]))
        if not c["glu_out_bf16"]:
            raise Fault(3, "FP8 GLU publication runs through the DS path")
        M.vm_write(r.desc["O"], die, L, y)


def u_att_qk(M: Machine, r: Rec, L):
    lanes = r.param & 0xF
    for die in M.dies:
        a, b, o = r.desc["A"], r.desc["B"], r.desc["O"]
        _, hd, _, _, _ = M.eff(a, die, L)
        q = M.vm_read(a, die, L, lanes, hd).reshape(lanes, hd)
        K = _rows(M, b, die, L, hd)
        for h in range(lanes):
            _write_row(M, o, die, L, h, A.att_qk(q[h], K))


def u_att_pv(M: Machine, r: Rec, L):
    lanes = r.param & 0xF
    for die in M.dies:
        a, b, o = r.desc["A"], r.desc["B"], r.desc["O"]
        _, hd, _, _, _ = M.eff(o, die, L)
        _, P, _, _, _ = M.eff(a, die, L)
        Vr = _rows(M, b, die, L, hd)
        if Vr.shape[0] != P:
            raise Fault(3, "PV: probability count != V rows")
        p = M.vm_read(a, die, L, lanes, P).reshape(lanes, P)
        for h in range(lanes):
            _write_row(M, o, die, L, h, A.att_pv(p[h], Vr))


def _rows(M, b, die, L, hd):
    """K / V rows: n_sel gives the row count (POS1); rows are `stride` bytes apart, hd elements each."""
    base, P, _, st, _ = M.eff(b, die, L)
    d2 = MDesc(space="HBM", fmt=b.fmt, base=base, n=hd, m=P, stride=st)
    return M.hbm_read(d2, die, 0)


def _write_row(M, o, die, L, h, vals):
    base, n, m, st, ist = M.eff(o, die, L)
    a = base + h * st + np.arange(len(vals)) * ist
    die.vm[a] = np.asarray(vals, dtype=F).view(np.uint32)


# -- SU.VOP: Machine.su1 over descriptors ------------------------------------------------------------------------
def u_su_vop(M: Machine, r: Rec, L):
    f = r.sut
    cfg = M.cfg
    for die in M.dies:
        a = r.desc["A"]
        _, ni, no, _, _ = M.eff(a, die, L)

        def src(k, s):
            d = r.desc.get(k)
            if d is None:
                return np.zeros(no * ni, dtype=F), None
            if d.space == "VM":
                if f["b_half"] and k in ("B", "D"):        # b / d inner index i >> 1 (adjacent-pair tables)
                    base, _, _, st, ist = M.eff(d, die, L)
                    o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
                    ad = (base + o * st + (i >> 1) * ist).reshape(-1)
                else:
                    ad = M.vm_addrs(d, die, L, no, ni)
                return die.vm[ad].view(F), ad
            return M.hbm_read(d, die, L, no, ni).reshape(-1), None
        av, ea = src("A", "a")
        bv, _ = src("B", "b")
        if f["c_pair"]:
            if ea is None:
                raise Fault(3, "c_pair needs a VM A operand")
            dims = 1 << cfg["rope_rot_log2"]
            part = ea ^ ((dims // 2) if cfg["rope_half"] else 1)
            cv = die.vm[part].view(F)
        else:
            cv, _ = src("C", "c")
        dv, _ = src("D", "d")
        imm1, imm2, imm3 = (np.uint32(f[k]).view(F) for k in ("imm1", "imm2", "imm3"))
        a_ = av
        if f["a_rnd"]:
            a_ = A.to_bf16(a_)
        if f["a_relu"]:
            a_ = np.maximum(a_, F(0)).astype(F)
        if f["a_min"]:
            a_ = np.minimum(a_, imm3).astype(F)
        c_ = cv
        if f["c_clip"]:
            c_ = np.clip(c_, -imm3, imm3).astype(F)
        with np.errstate(all="ignore"):
            p = {I.M1_BYP: lambda: a_, I.M1_AB: lambda: A.mul(a_, bv), I.M1_AA: lambda: A.mul(a_, a_),
                 I.M1_AIMM: lambda: A.mul(a_, imm1), I.M1_DIVB: lambda: A.div(a_, bv),
                 I.M1_DIVIMM: lambda: A.div(a_, imm1), I.M1_MAXB: lambda: np.maximum(a_, bv).astype(F)}[f["m1"]]()
            p = {I.M2_BYP: lambda: p, I.M2_C: lambda: A.mul(p, c_), I.M2_IMM: lambda: A.mul(p, imm1)}[f["m2"]]()
            i_idx = np.tile(np.arange(ni), no)
            if f["qm"] in (I.QM_ALT_NP, I.QM_ALT_PN):
                bit = ((i_idx >> (cfg["rope_rot_log2"] - 1)) & 1) if cfg["rope_half"] else (i_idx & 1)
            else:
                bit = i_idx & 1
            qd = {I.QM_OFF: None, I.QM_POS: dv, I.QM_NEG: A.neg(dv),
                  I.QM_ALT_NP: np.where(bit == 0, A.neg(dv), dv).astype(F),
                  I.QM_ALT_PN: np.where(bit == 0, dv, A.neg(dv)).astype(F)}[f["qm"]]
            q = None if qd is None else A.mul(c_, qd)
            rr = {I.AD_BYP: lambda: p, I.AD_Q: lambda: A.add(p, q), I.AD_C: lambda: A.add(p, c_),
                  I.AD_NEGB: lambda: A.add(p, A.neg(bv)), I.AD_IMM: lambda: A.add(p, imm2),
                  I.AD_D: lambda: A.add(p, dv)}[f["ad"]]()
            s = {I.SFU_NONE: lambda: rr, I.SFU_EXP: lambda: A.exp(rr), I.SFU_RSQRT: lambda: A.rsqrt(rr),
                 I.SFU_SQRT: lambda: A.sqrt(rr), I.SFU_SIGM: lambda: A.sigmoid(rr), I.SFU_SILU: lambda: A.silu(rr),
                 I.SFU_SPSQRT: lambda: A.sqrt(A.softplus(rr)),
                 I.SFU_EGATE: lambda: A.sigmoid(np.where(rr < 0, A.neg(A.sqrt(np.maximum(np.abs(rr), F(1e-6)).astype(F))),
                                                         A.sqrt(np.maximum(np.abs(rr), F(1e-6)).astype(F))).astype(F))
                 }.get(f["sfu"])
            if s is None:
                raise Fault(3, f"SU sfu {f['sfu']} not modelled for this program")
            s = s()
            t = {I.E1_BYP: lambda: s, I.E1_MULC: lambda: A.mul(s, c_), I.E1_ADDC: lambda: A.add(s, c_),
                 I.E1_MULIMM: lambda: A.mul(s, imm2), I.E1_ADDIMM: lambda: A.add(s, imm2)}[f["e1"]]()
            u = {I.E2_BYP: lambda: t, I.E2_MULB: lambda: A.mul(t, bv), I.E2_MULIMM: lambda: A.mul(t, imm1)}[f["e2"]]()
        out = np.asarray(u, dtype=F).reshape(-1)
        if not np.all(np.isfinite(out)):
            raise Fault(1, f"SU non-finite result ({r.tag})")
        if f["rnd"]:
            out = A.to_bf16(out)
        if f["red"]:
            v = A.mul(out, out) if f["red_sq"] else out
            segs = v.reshape(1, -1) if (f["red_whole"] or f["red_tree"]) else v.reshape(no, ni)
            if f["red"] == I.RED_SUM:
                vals = A.csum(segs)
            elif f["red"] == I.RED_MAX:
                vals = segs.max(axis=1).astype(F)
            else:
                raise Fault(3, "SU reduction kind")
            if f["red_rnd"]:
                vals = A.to_bf16(vals)
            rd = r.desc.get("R")
            if rd is None:
                raise Fault(3, "SU reduction without an R descriptor")
            _write_red(M, rd, die, L, vals)
        if f["dst"]:
            o = r.desc.get("O")
            M.vm_write(o, die, L, out, no, ni)


def _write_red(M, rd, die, L, vals):
    """Reduction k of the op goes to R.base + k * R.stride (stride 0 = 1)."""
    base, n, m, st, ist = M.eff(rd, die, L)
    a = base + np.arange(len(vals)) * (st or 1)
    die.vm[a] = np.asarray(vals, dtype=F).view(np.uint32)


UNITS = {("DMA", "LOAD"): u_dma_load, ("DMA", "STORE"): u_dma_store, ("DMA", "FENCE"): u_dma_fence,
         ("SM", "MATVEC"): u_sm_matvec, ("COLL", "ALL_REDUCE_SUM"): u_coll_all_reduce,
         ("ARGMAX", "LOCAL"): u_argmax_local, ("COLL", "ARGMAX_MERGE"): u_coll_argmax_merge,
         ("FUSED", "ROW_NORM"): u_row_norm, ("SFU", "GLU"): u_glu, ("ATT", "QK"): u_att_qk, ("ATT", "PV"): u_att_pv,
         ("SU", "VOP"): u_su_vop}
