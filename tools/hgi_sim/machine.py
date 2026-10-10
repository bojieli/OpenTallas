"""hgi_sim: the HGI-1 die simulator (docs/HBM_GENERIC_INTERFACE.md section 8.1), functional core.

Inputs are the artifacts the die consumes: the 64-word model descriptor (loaded through the config path with every
check and error code of section 5.7), the program image (encoded records, decoded here), each die's HBM image, and
doorbells.  Outputs: the completion, a per-record trace (unit, op, hashes of every operand and result buffer), the
HBM / VM write log, faults.

FUNCTIONAL MODEL.  Records execute in program order on every die of the group (SPMD; collectives join all dies at
the same record).  A unit op's arithmetic is the shared library (lib.py) and, for SU.VOP, Machine.su1's pipeline
(tools/hdc_program_v41.py) restated over HGI descriptors.  In-order program semantics is what the die computes iff the
program's `wait` masks, STREAM credits, collectives and FENCEs order every hazard; the timing model (timing.py)
checks exactly that and reports any record that would read a region before its producer retired (RACE).

Addressing (section 3.3): effective base = base + L * lstride + L1 * l1stride + X * dyn_mul, X = DYN[dyn_sel], or
U32(VM[I + L]) for an indexed descriptor; n = DYN[n_sel] if n_sel (63: row 1 of the I table); element (o, i) at
eb + o * stride + i * istride' (istride' = 1 when 0, and 0 when ibcast).
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
from .records import MDesc, Rec, decode_program  # noqa: E402

F = np.float32
VM_WORDS = 1 << 18
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
        self.streams = {}            # STREAM id -> FIFO of pushed element vectors (credit-ordered producer -> consumer)
        self.stream_seen = {}        # STREAM id -> the last vector pushed (simulator-side visibility for checkers)


# STREAM ids by wiring (spec 2.4: fixed by the die's wiring).  PROVISIONAL table (hbm-sim -> hgi-takeover): a STREAM
# descriptor's base is the stream id; the producer's O and the consumer's A must name the wired pair.
STREAM_WIRING = {0: ("SM", "SU"),           # SM results into the SU lane registers
                 1: ("SU", "ARGMAX"),       # SU reduction output into the argmax unit (hb_su_red_mtp_am)
                 2: ("SM", "ARGMAX")}       # the LM-head matvec into the argmax unit


# ----------------------------------------------------------------------------------------------------------------
# the machine
# ----------------------------------------------------------------------------------------------------------------
D_STATIC = [n for n in HGI.D_RESET]


def d_unpack(words):
    md = {}
    for name, w, lsb, width, *_ in HGI.D_MD_FIELDS:
        if width > 32:
            md[name] = sum(words[w + k] << (32 * k) for k in range(width // 32))
        else:
            md[name] = (words[w] >> lsb) & ((1 << width) - 1)
    return md


class Machine:
    def __init__(self, dies, units=None):
        self.dies = dies
        self.cfg = dict(HGI.D_RESET)               # the three static fields; reset = DS
        self.cfg_status = dict(loaded=False, err=0)
        self.trace = []
        self.units = units or {}
        self.busy = False
        self.cur = None                            # the record being executed (its I operand serves indexed descriptors)
        self.die_recs = None                       # rank -> that die's record (per-die images, G11), set per record

    def rec_of(self, die, r):
        """The record die `die` executes at this program step (per-die images of identical structure)."""
        return self.die_recs[die.rank] if self.die_recs else r

    def groups(self):
        g = self.cfg["coll_group_size"]
        return [self.dies[s:s + g] for s in range(0, len(self.dies), g)]

    # -- config path (spec 5.5 - 5.7) ------------------------------------------------------------------------------
    def cfg_commit(self, words, busy=False):
        err = HGI.d_hw_check(list(words), busy=busy or self.busy)
        if err:
            self.cfg_status = dict(loaded=self.cfg_status["loaded"], err=err)
            return err
        md = d_unpack(list(words))
        for k in D_STATIC:
            self.cfg[k] = md[k]
        self.cfg_status = dict(loaded=True, err=0)
        return 0

    # -- addressing (spec 3.3, 6.4) --------------------------------------------------------------------------------
    def _plain_base(self, d, die, L):
        return d.base + L * d.lstride + die.dyn[8] * d.l1stride + die.dyn[d.dyn_sel] * d.dyn_mul

    def eff(self, d: MDesc, die: Die, L):
        if d.indexed or d.n_sel == HGI.NSEL_FROM_VM:
            cur = self.rec_of(die, self.cur) if self.cur is not None else None
            idesc = cur.desc.get("I") if cur is not None else None
            if idesc is None:
                raise Fault(3, "indexed descriptor without an I operand")
            ib = self._plain_base(idesc, die, L)
        if d.indexed:
            idx = int(die.vm[ib + L])
            base = d.base + L * d.lstride + die.dyn[8] * d.l1stride + idx * d.dyn_mul
        else:
            base = self._plain_base(d, die, L)
        if d.n_sel == HGI.NSEL_FROM_VM:
            n = int(die.vm[ib + idesc.stride + L])
        else:
            n = die.dyn[d.n_sel] if d.n_sel else d.n
        ist = 0 if d.ibcast else (d.istride or 1)
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

    def stream_push(self, d, die, vals):
        sid = d.base
        if sid not in STREAM_WIRING or self.cur is None or STREAM_WIRING[sid][0] != self.cur.unit:
            raise Fault(3, f"STREAM {sid}: not a wired output of unit {getattr(self.cur, 'unit', None)}")
        v = np.asarray(vals, dtype=F).reshape(-1).copy()
        die.streams[sid] = np.concatenate([die.streams.get(sid, np.zeros(0, F)), v])   # an element FIFO
        die.stream_seen[sid] = v

    def stream_pop(self, d, die, n):
        sid = d.base
        if sid not in STREAM_WIRING or self.cur is None or STREAM_WIRING[sid][1] != self.cur.unit:
            raise Fault(3, f"STREAM {sid}: not a wired input of unit {getattr(self.cur, 'unit', None)}")
        q = die.streams.get(sid, np.zeros(0, F))
        if q.size < n:
            raise Fault(3, f"STREAM {sid}: consumer reads {n} elements, {q.size} queued (underrun)")
        die.streams[sid] = q[n:]
        return q[:n]

    def vm_write(self, d, die, L, vals, no=None, ni=None):
        if d.space == "STREAM":
            return self.stream_push(d, die, vals)
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
        if d.space == "STREAM":
            _, n, m, _, _ = self.eff(d, die, L)
            return self.stream_pop(d, die, (no if no is not None else m) * (ni if ni is not None else n))
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
            die.dyn[:16] = [0, pos, pos + 1, token, 0, die.rank, 0, pos, 0, 0, 0, 0, 0, 0, 0, pos + 1]

    def run(self, image: bytes, token, pos, hash_bufs=True, hook=None, recs=None):
        """Execute one doorbell: returns (completion token, trace).  Loops: two levels (CTL.LOOP param [16])."""
        recs = recs if recs is not None else decode_program(image)
        self.doorbell(token, pos)
        self.trace = []
        self.result = None
        pc = 0
        loops = []                                    # stack of dict(start, count, level, i)
        while pc < len(recs):
            r = recs[pc]
            L = next((x["i"] for x in reversed(loops) if x["level"] == 0), 0)
            L1 = next((x["i"] for x in reversed(loops) if x["level"] == 1), 0)
            for die in self.dies:
                die.dyn[4], die.dyn[8] = L, L1
            if not self.pred(r, loops):
                pc += 1
                continue
            if r.unit == "CTL":
                if r.op == "LOOP":
                    loops.append(dict(start=pc + 1, count=r.param & 0xFFFF, level=(r.param >> 16) & 1, i=0))
                    pc += 1
                    continue
                if r.op == "ENDLOOP":
                    if not loops:
                        raise Fault(3, "ENDLOOP without LOOP")
                    lp = loops[-1]
                    lp["i"] += 1
                    if lp["i"] < lp["count"]:
                        pc = lp["start"]
                        continue
                    loops.pop()
                    pc += 1
                    continue
                if r.op == "END":
                    self.cur = r
                    toks = [int(self.read(r.desc["A"], die, L).view(np.uint32)[0]) for die in self.dies]
                    if len(set(toks)) != 1:
                        raise Fault(1, f"dies disagree on the token {toks}")
                    if toks[0] >= self.cfg["cp_vocab"]:
                        raise Fault(3, "END token >= cp_vocab")
                    self.trace.append(dict(pc=pc, L=L, unit="CTL", op="END", tag=r.tag))
                    self.result = toks[0]
                    return toks[0], self.trace
                if r.op == "TOKX":
                    # PROPOSED (SPEC_GAP Q-MTP-1): A[0] = k (U32, 1 <= k <= ncol), A[1..k] = the committed tokens;
                    # the CP emits k completion beats {token A[i], pos + i - 1} before END.
                    self.cur = r
                    outs = []
                    for die in self.dies:
                        a0 = self.vm_addrs(r.desc["A"], die, L, 1, 1)[0]
                        k = int(die.vm[a0])
                        if not 1 <= k <= r.desc["A"].n - 1:
                            raise Fault(3, f"TOKX count {k} outside 1..{r.desc['A'].n - 1}")
                        outs.append([int(t) for t in die.vm[a0 + 1:a0 + 1 + k]])
                    if any(o != outs[0] for o in outs):
                        raise Fault(1, "dies disagree on the committed tokens")
                    if any(t >= self.cfg["cp_vocab"] for t in outs[0]):
                        raise Fault(3, "TOKX token >= cp_vocab")
                    self.tokx = outs[0]
                    self.trace.append(dict(pc=pc, L=L, unit="CTL", op="TOKX", tag=r.tag, k=len(outs[0])))
                    pc += 1
                    continue
                pc += 1            # NOP / FENCE: ordering only (timing model)
                continue
            fn = self.units.get((r.unit, r.op))
            if fn is None:
                raise Fault(3, f"no unit {r.unit}.{r.op} on this die")
            self.cur = r
            fn(self, r, L)
            ent = dict(pc=pc, L=L, L1=L1, unit=r.unit, op=r.op, tag=r.tag, family=r.family)
            if hash_bufs:
                ent["out"] = self.hash_out(r, L)
            self.trace.append(ent)
            if hook:
                hook(self, r, L)
            pc += 1
        raise Fault(2, "program ended without END")

    def pred(self, r, loops):
        p = r.pred
        pos = self.dies[0].dyn[1]
        if p == "ALWAYS":
            return True
        if p == "POS0":
            return pos == 0
        if p == "NOT_POS0":
            return pos != 0
        return bool(loops) and loops[-1]["i"] == loops[-1]["count"] - 1

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
    if fmt in ("FP32", "U32"):                  # U32: the word moves unchanged (ids, counts)
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
    P = ((r.param >> 2) & 7) + 1                  # [4:2] positions - 1: one weight read serves P slots (spec 6.7)
    for die in M.dies:
        raw = M.hbm_rows_raw(b, die, L)
        w = raw.view(np.int8) if fmt == 3 else (np.ascontiguousarray(raw).view(np.uint16).astype(np.uint32) << 16).view(F)
        if P == 1:
            x = M.read(a, die, L)
            if w.shape[1] != x.size:
                raise Fault(3, f"SM K {w.shape[1]} != activation length {x.size}")
            M.vm_write(o, die, L, A.sm_int8(w, x))
            continue
        # P slots: A and O carry one row per slot (m = P); each slot's result is the single-slot arithmetic
        _, an, am, _, _ = M.eff(a, die, L)
        _, on, om, _, _ = M.eff(o, die, L)
        if am != P or om != P or an != w.shape[1]:
            raise Fault(3, f"SM P={P}: A/O rows ({am}, {om}) or K {an} != weights K {w.shape[1]}")
        xs = M.read(a, die, L).reshape(P, an)
        M.vm_write(o, die, L, np.stack([A.sm_int8(w, xs[k]) for k in range(P)]))


def u_coll_all_reduce(M: Machine, r: Rec, L):
    for grp in M.groups():
        if len(grp) not in (1, 2, 4, 8):
            raise Fault(3, f"E_RANGE: ALL_REDUCE_SUM over a group of {len(grp)} (legal 1, 2, 4, 8; G = 96 reduces "
                           "as GROUP_REDUCE_MCAST s = 8, GX11)")
        tot = A.pairwise([M.read(M.rec_of(d, r).desc["A"], d, L) for d in grp])
        for d in grp:
            M.vm_write(M.rec_of(d, r).desc["O"], d, L, tot)


def u_argmax_local(M: Machine, r: Rec, L):
    for die in M.dies:
        v = M.read(r.desc["A"], die, L)
        j = A.argmax(v)
        a = M.vm_addrs(r.desc["O"], die, L, 1, 2)
        die.vm[a[0]] = np.asarray([v[j]], dtype=F).view(np.uint32)[0]
        die.vm[a[1]] = np.uint32(j + die.rank * r.imm_a)           # global id = local + RANK * imm_a


def u_coll_argmax_merge(M: Machine, r: Rec, L):
    for grp in M.groups():
        vals, ids = [], []
        for k, d in enumerate(grp):
            a = M.vm_addrs(M.rec_of(d, r).desc["A"], d, L, 1, 2)
            vals.append(d.vm[a[0]:a[0] + 1].view(F)[0])
            ids.append(int(d.vm[a[1]]))                              # ids are global (ARGMAX.LOCAL imm_a)
        order = np.lexsort((np.array(ids), -np.array(vals, dtype=np.float64)))
        tok = ids[order[0]]
        for d in grp:
            d.vm[M.vm_addrs(M.rec_of(d, r).desc["O"], d, L, 1, 1)] = np.uint32(tok)


def u_row_norm(M: Machine, r: Rec, L):
    seg = (r.param >> 6) & 0xFF                                     # [5:0] d_units, [13:6] seg
    eps = np.uint32(r.imm_a).view(F)
    a, b, o = r.desc["A"], r.desc["B"], r.desc["O"]
    for die in M.dies:
        x = M.read(a, die, L)
        g = M.read(b, die, L)
        if g.size != (seg or x.size) or (seg and x.size % seg):
            raise Fault(3, "ROW_NORM: gain length != segment (or row) width")
        y = A.row_norm(x, g, eps, seg)
        if o.fmt == "BF16":
            y = A.to_bf16(y)
        M.vm_write(o, die, L, y)


def u_glu(M: Machine, r: Rec, L):
    """SFU.GLU: per-op settings only: imm_a = clamp limit (FLT_MAX disables), C = route weight (1.0 + ibcast
    disables), output format = O.fmt."""
    lim = np.uint32(r.imm_a).view(F)
    for die in M.dies:
        g, u = M.read(r.desc["A"], die, L), M.read(r.desc["B"], die, L)
        rw = M.read(r.desc["C"], die, L)
        u = np.clip(u, -lim, lim).astype(F)
        g = np.minimum(g, lim).astype(F)
        y = A.mul(rw, A.mul(A.div(g, A.add(A.exp(A.mul(g, F(-1.0))), F(1.0))), u))
        if r.desc["O"].fmt == "BF16":
            y = A.to_bf16(y)
        elif r.desc["O"].fmt != "FP32":
            raise Fault(3, "GLU output format")
        M.vm_write(r.desc["O"], die, L, y)


def u_att_qk(M: Machine, r: Rec, L):
    lanes = (r.param & 0xF) or 16                  # [3:0] head lanes; 0 encodes 16 (HGI-1.1 clarification)
    for die in M.dies:
        a, o = r.desc["A"], r.desc["O"]
        _, hd, _, _, _ = M.eff(a, die, L)
        q = M.vm_read(a, die, L, lanes, hd).reshape(lanes, hd)
        K = att_rows(M, r, die, L, hd)
        for h in range(lanes):
            _write_row(M, o, die, L, h, A.att_qk(q[h], K))


def u_att_pv(M: Machine, r: Rec, L):
    lanes = (r.param & 0xF) or 16                  # [3:0] head lanes; 0 encodes 16 (HGI-1.1 clarification)
    for die in M.dies:
        a, o = r.desc["A"], r.desc["O"]
        _, hd, _, _, _ = M.eff(o, die, L)
        _, P, _, _, _ = M.eff(a, die, L)
        Vr = att_rows(M, r, die, L, hd)
        if Vr.shape[0] != P:
            raise Fault(3, "PV: probability count != V rows")
        p = M.vm_read(a, die, L, lanes, P).reshape(lanes, P)
        for h in range(lanes):
            _write_row(M, o, die, L, h, A.att_pv(p[h], Vr))


def att_rows(M, r, die, L, hd):
    """The ATT row list (spec 6.7): B's n rows (n_sel POS1 / POS_SLOT1 = the mask), oldest first; with param[8] ring,
    B is a ring of B.m slots (a power of two) read from slot (POS1 - n) mod B.m, wrapping; then C's n rows."""
    b = r.desc["B"]
    base, n, m, st, _ = M.eff(b, die, L)
    if (r.param >> 8) & 1:
        if m < 1 or m & (m - 1) or n > m:
            raise Fault(3, "ATT ring: B.m must be a power of two >= n")
        first = (die.dyn[2] - n) % m
        slots = (first + np.arange(n)) % m
        ring = M.hbm_read(MDesc(space="HBM", fmt=b.fmt, base=base, n=hd, m=m, stride=st), die, 0)
        rows = [ring[slots]]
    else:
        rows = [M.hbm_read(MDesc(space="HBM", fmt=b.fmt, base=base, n=hd, m=n, stride=st), die, 0)]
    c = r.desc.get("C")
    if c is not None:
        cb, cn, _, cst, _ = M.eff(c, die, L)
        rows.append(M.hbm_read(MDesc(space="HBM", fmt=c.fmt, base=cb, n=hd, m=cn, stride=cst), die, 0))
    return np.concatenate(rows) if len(rows) > 1 else rows[0]


def _write_row(M, o, die, L, h, vals):
    base, n, m, st, ist = M.eff(o, die, L)
    a = base + h * st + np.arange(len(vals)) * ist
    die.vm[a] = np.asarray(vals, dtype=F).view(np.uint32)


# -- IDX.TOPK, COLL gather / reduce / row gather, DMA.KVWB_DS, FUSED.QDQ (spec 6.7) ----------------------------------
TOPK_ASC = 1 << 12              # G15 (spec c80ed5d7c): param[12] order = 1 -> ids in ascending id order, k <= 8 only


def topk_ids(v, k, asc=False):
    """k ids of the largest values, ties to the lowest index, in descending-score order (asc: ascending id)."""
    v = np.asarray(v, dtype=np.float64)
    if np.isnan(v).any():
        raise Fault(1, "TOPK: NaN score")
    ids = np.lexsort((np.arange(len(v)), -v))[:k]
    return np.sort(ids) if asc else ids


def u_idx_topk(M: Machine, r: Rec, L):
    k = r.param & 0xFFF
    if not 1 <= k <= 2048:
        raise Fault(3, "TOPK k outside 1..2048")
    if r.param & TOPK_ASC and k > 8:
        raise Fault(3, "E_RANGE: TOPK order = 1 (ascending id) is legal for k <= 8 only (G15)")
    for die in M.dies:
        a = r.desc["A"]
        _, n, m, _, _ = M.eff(a, die, L)
        if k > n:
            raise Fault(3, "TOPK k > n")
        v = M.read(a, die, L).reshape(m, n)
        o, rr = r.desc["O"], r.desc.get("R")
        ob, _, _, ost, oist = M.eff(o, die, L)
        for row in range(m):
            ids = topk_ids(v[row], k, bool(r.param & TOPK_ASC))
            die.vm[ob + row * ost + np.arange(k) * oist] = ids.astype(np.uint32)
            if rr is not None:
                rb, _, _, rst, rist = M.eff(rr, die, L)
                die.vm[rb + row * rst + np.arange(k) * rist] = v[row][ids].astype(F).view(np.uint32)


# -- IDX.INDEX (G18): one DS indexer frame; COLL.TOPK_MERGE from VM -------------------------------------------------
INDEX_BLOCK = 8                  # keys are sharded by rank in blocks of 8 (the candidate block)


def index_owned(rank, n, G):
    """Global ids of the keys < n owned by `rank` of a G-rank group (blocks of INDEX_BLOCK, round robin), and the
    owned blocks."""
    blocks = np.arange(rank, -(-n // INDEX_BLOCK), G)
    idx = (blocks[:, None] * INDEX_BLOCK + np.arange(INDEX_BLOCK)[None, :]).reshape(-1)
    return idx[idx < n], blocks


def u_idx_index(M: Machine, r: Rec, L):
    """IDX.INDEX: param [11:0] k, [12] cand_en, [13] keep_en; imm_a = n keys, imm_b = layer.  A = post-RoPE query
    (ih heads x ihd, FP32), B = scaled head weights (ih BF16 values in FP32 words), C = keep table (keep_en: row 0
    block ids U32, row 1 values FP32; listed blocks with value > -inf are kept, G18a), O = local top-k ids (ascending),
    R = their values (FP32), D = candidate table (cand_en: row 0 block ids, row 1 block maxima; D.n candidates).
    The keys are the indexer engine's key store (M.index_keys(die, layer, ids) -> FP4-grid key rows).  Arithmetic:
    hdc_golden_v41 (the shipped indexer): FP4 query quantiser, block-dot scores, relu x weight, row reduce, BF16."""
    import hdc_golden_v41 as GV
    k, cand_en, keep_en = r.param & 0xFFF, (r.param >> 12) & 1, (r.param >> 13) & 1
    n, layer = r.imm_a, r.imm_b
    G_ = M.cfg["coll_group_size"]
    if True:
        for die in M.dies:                              # (run per die or per group: the rank is the die's)
            q_ = die.rank % G_
            rd = M.rec_of(die, r)
            ih = rd.desc["B"].n
            q = M.read(rd.desc["A"], die, L).astype(F).reshape(ih, -1)
            w = M.read(rd.desc["B"], die, L).astype(F)
            qf = np.stack([GV.qdq_fp4_e8m0(q[h]) for h in range(ih)])
            idx, blocks = index_owned(q_, n, G_)
            keys = M.index_keys(die, layer, idx)
            score = A.to_bf16(GV.dots_q4(qf, keys))
            terms = A.to_bf16(A.mul(np.maximum(score, F(0)), w[:, None]))
            v = A.to_bf16(GV.reduce_rows(terms.T, cls="idx")).astype(np.float64)
            if cand_en:
                bs = np.full(len(blocks), -np.inf)
                np.maximum.at(bs, np.searchsorted(blocks, idx // INDEX_BLOCK), v)
                bs[blocks == (n - 1) // INDEX_BLOCK] = np.inf          # the newest block is pinned
                d = rd.desc["D"]
                db, dn, _, dst, _ = M.eff(d, die, L)
                kc = min(dn, len(blocks))
                order = np.lexsort((blocks, -bs))[:kc]
                if kc != dn:
                    raise Fault(3, f"INDEX D.n {dn} > owned blocks {len(blocks)}")
                die.vm[db:db + kc] = blocks[order].astype(np.uint32)
                die.vm[db + dst:db + dst + kc] = bs[order].astype(F).view(np.uint32)
            if keep_en:
                c = rd.desc["C"]
                cb, cn, _, cst, _ = M.eff(c, die, L)
                ids, vals = die.vm[cb:cb + cn].astype(np.int64), die.vm[cb + cst:cb + cst + cn].view(F)
                kept = set(int(b_) for b_, x in zip(ids, vals) if x > -np.inf)
                keep = np.array([int(i) // INDEX_BLOCK in kept for i in idx], dtype=bool)
                v = np.where(keep, v, -np.inf)
            die.index_last = (idx, v.copy())                     # (checker's view of the scores, after the mask)
            kk = min(k, len(idx))
            sel = np.lexsort((idx, -v))[:kk]
            o = rd.desc["O"]
            ob, on, _, _, _ = M.eff(o, die, L)
            if on != kk:
                raise Fault(3, f"INDEX O.n {on} != local top-k {kk}")
            order = sel[np.argsort(idx[sel], kind="stable")]           # ids in ascending id order
            die.vm[ob:ob + on] = idx[order].astype(np.uint32)
            if "R" in rd.desc:
                M.vm_write(rd.desc["R"], die, L, v[order].astype(F))


def u_coll_topk_merge(M: Machine, r: Rec, L):
    """COLL.TOPK_MERGE (G18): from VM, A = local values, B = their ids (n each, per die); the group's top imm_a by
    descending value, ties to the lowest id; O = the ids in ascending id order, R (optional) = their values.  The
    contributions move through the collective's exact gather (bypass) path."""
    for grp in M.groups():
        vs, ids = [], []
        for d in grp:
            rd = M.rec_of(d, r)
            vs.append(M.read(rd.desc["A"], d, L).astype(np.float64))
            b0, n_, _, _, _ = M.eff(rd.desc["B"], d, L)
            ids.append(d.vm[b0:b0 + n_].astype(np.int64))
        v, i = np.concatenate(vs), np.concatenate(ids)
        if np.isnan(v).any():
            raise Fault(1, "TOPK_MERGE: NaN value")
        top = np.lexsort((i, -v))[:r.imm_a]
        top = top[np.argsort(i[top], kind="stable")]
        for d in grp:
            rd = M.rec_of(d, r)
            ob, on, _, _, _ = M.eff(rd.desc["O"], d, L)
            if on != len(top):
                raise Fault(3, f"TOPK_MERGE O.n {on} != {len(top)}")
            d.vm[ob:ob + on] = i[top].astype(np.uint32)
            if "R" in rd.desc:
                M.vm_write(rd.desc["R"], d, L, v[top].astype(F))


def u_coll_all_gather(M: Machine, r: Rec, L):
    """Even-split segments (G9): rank q of a G-rank group contributes A[floor(q n / G), floor((q + 1) n / G))."""
    for grp in M.groups():
        G = len(grp)
        n = M.rec_of(grp[0], r).desc["A"].n
        full = np.zeros(n, dtype=np.uint32)
        for q, d in enumerate(grp):
            lo, hi = q * n // G, (q + 1) * n // G
            full[lo:hi] = d.vm[M.vm_addrs(M.rec_of(d, r).desc["A"], d, L)][lo:hi]
        for d in grp:
            d.vm[M.vm_addrs(M.rec_of(d, r).desc["O"], d, L)] = full


def u_coll_group_reduce_mcast(M: Machine, r: Rec, L):
    """Each aligned sub-group of s ranks reduces A (rank-order pairwise tree); every rank of the group receives all
    sub-groups' results in sub-group order in O (format O.fmt) (G10)."""
    s = r.param & 0xFF
    for grp in M.groups():
        G = len(grp)
        if s not in (2, 4, 8) or G % s:
            raise Fault(3, "GROUP_REDUCE_MCAST sub-group size")
        res = []
        for q in range(G // s):
            sub = grp[q * s:(q + 1) * s]
            res.append(A.pairwise([M.vm_read(M.rec_of(d, r).desc["A"], d, L) for d in sub]))
        out = np.concatenate(res).astype(F)
        for d in grp:
            o = M.rec_of(d, r).desc["O"]
            if M.eff(o, d, L)[1] * o.m != out.size:
                raise Fault(3, "GROUP_REDUCE_MCAST: O does not hold (G / s) sub-group results")
            v = A.to_bf16(out) if o.fmt == "BF16" else out
            M.vm_write(o, d, L, v)


def u_coll_row_gather(M: Machine, r: Rec, L):
    """COLL.ROW_GATHER (G14): I = selected row ids (U32); row i is owned by rank (i div B) mod G and stored there at
    local row (i div (B G)) B + i mod B of A (this die's row store); ranks 0 .. imm_b - 1 receive the rows in list
    order in O.  An unwritten (NaN) row faults."""
    B = r.param & 0xFF
    for grp in M.groups():
        G = len(grp)
        d0 = grp[0]
        i_d = M.rec_of(d0, r).desc["I"]
        ib, n_i, _, _, iist = M.eff(i_d, d0, L)
        k = r.imm_a or n_i
        ids = d0.vm[ib + np.arange(k) * iist].astype(np.int64)
        # bypass gather (hgi-die-gaps round 4): each owner reads its rows in list order, padded to the group's
        # maximum owned count, then one exact gather pass; the counts are recorded for the timing model
        owned = np.bincount((ids // B) % G, minlength=G)
        getattr(M, "row_gather_stats", []).append(dict(tag=r.tag, k=int(k), G=G, max_owned=int(owned.max()),
                                                       mean_owned=round(float(owned.mean()), 3)))
        rows = []
        for i in ids:
            owner = grp[(i // B) % G]
            a = M.rec_of(owner, r).desc["A"]
            ab, an, _, ast, _ = M.eff(a, owner, L)
            local = (i // (B * G)) * B + i % B
            rows.append(M.hbm_read(MDesc(space="HBM", fmt=a.fmt, base=ab + local * ast, n=an), owner, 0)[0]
                        if a.space == "HBM" else M.vm_read(MDesc(space="VM", base=ab + local * ast, n=an), owner, 0))
        rows = np.stack(rows).astype(F) if rows else np.zeros((0, 1), F)
        if np.isnan(rows).any():
            raise Fault(1, "ROW_GATHER: an unwritten row")
        for q, d in enumerate(grp):
            if q >= r.imm_b:
                continue
            o = M.rec_of(d, r).desc["O"]
            ob, on, _, ost, _ = M.eff(o, d, L)
            for j in range(len(rows)):
                if o.space == "HBM":
                    M.hbm_write(MDesc(space="HBM", fmt=o.fmt, base=ob + j * ost, n=on), d, 0, rows[j])
                else:
                    M.vm_write(MDesc(space="VM", base=ob + j * ost, n=on), d, 0, rows[j])


def u_dma_kvwb_ds(M: Machine, r: Rec, L):
    """DMA.KVWB_DS: the DS window-ring write-back: A (one row) into ring O (O.m slots, O.stride apart) at slot
    POS mod O.m."""
    for die in M.dies:
        o = r.desc["O"]
        ob, on, om, ost, _ = M.eff(o, die, L)
        slot = die.dyn[1] % om
        M.hbm_write(MDesc(space="HBM", fmt=o.fmt, base=ob + slot * ost, n=on), die, 0, M.read(r.desc["A"], die, L))


def _golden_v41():
    import hdc_golden_v41 as GV
    return GV


def u_fused_qdq(M: Machine, r: Rec, L):
    """FUSED.QDQ_*: quantise each block and dequantise it again, exactly as the DS activation quantiser
    (hdc_golden_v41.qdq_fp8 / qdq_fp4_e8m0 / qdq_fp4_e4m3)."""
    GV = _golden_v41()
    if r.op == "QDQ_FP4_E4M3" and (r.param & 0xFF) != 16:
        raise Fault(3, "QDQ_FP4_E4M3 block size other than 16 is not defined (CF-QDQ)")
    f = {"QDQ_FP8": GV.qdq_fp8, "QDQ_FP4_E8M0": GV.qdq_fp4_e8m0,
         "QDQ_FP4_E4M3": lambda x: GV.qdq_fp4_e4m3(x, r.param & 0xFF)}[r.op]
    for die in M.dies:
        M.vm_write(r.desc["O"], die, L, np.asarray(f(M.read(r.desc["A"], die, L)), dtype=F))


# -- SU.VOP: Machine.su1 over descriptors ------------------------------------------------------------------------
def u_su_vop(M: Machine, r: Rec, L):
    f = r.sut
    for die in M.dies:
        a = r.desc["A"]
        _, ni, no, _, _ = M.eff(a, die, L)

        def src(k, s):
            d = r.desc.get(k)
            if d is None:
                return np.zeros(no * ni, dtype=F), None
            if d.space == "STREAM":
                return M.read(d, die, L, no, ni), None
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
            part = ea ^ 1                                   # c_pair: always i XOR 1 (pairing is in the weights)
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
                bit = i_idx & 1
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
         ("IDX", "INDEX"): u_idx_index, ("COLL", "TOPK_MERGE"): u_coll_topk_merge,
         ("ARGMAX", "LOCAL"): u_argmax_local, ("COLL", "ARGMAX_MERGE"): u_coll_argmax_merge,
         ("FUSED", "ROW_NORM"): u_row_norm, ("SFU", "GLU"): u_glu, ("ATT", "QK"): u_att_qk, ("ATT", "PV"): u_att_pv,
         ("SU", "VOP"): u_su_vop, ("IDX", "TOPK"): u_idx_topk, ("COLL", "ALL_GATHER"): u_coll_all_gather,
         ("COLL", "GROUP_REDUCE_MCAST"): u_coll_group_reduce_mcast, ("COLL", "ROW_GATHER"): u_coll_row_gather,
         ("DMA", "KVWB_DS"): u_dma_kvwb_ds, ("FUSED", "QDQ_FP8"): u_fused_qdq, ("FUSED", "QDQ_FP4_E8M0"): u_fused_qdq,
         ("FUSED", "QDQ_FP4_E4M3"): u_fused_qdq}
