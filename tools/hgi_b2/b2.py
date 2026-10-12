"""B2 compiler pass: per-quadrant VM placement, per-cluster record split and the bit-exact check, for the HBM die with
four clusters and a distributed VM (results/arch/hbm_b2_1012/SPEC.md, results/arch/hbm_die_phy_study_1012/STUDY.md).

HGI-1 is unchanged: a record still names one logical VM (262,144 words).  This pass decides, for the program the
compiler emitted, where every logical word lives and which cluster computes what:

  placement   every touched logical word is LOCAL q (slice q only) or MIRROR (the same copy in every slice's mirror
              window).  A word that a split record needs on more than one cluster (an SM activation, a scalar
              broadcast, a reduction result) is MIRROR; a word only one cluster reads or writes is LOCAL to it.  Words
              only the central ring clients touch are spread over the slices in 256-word blocks.
              The slice holds LOCAL_W local words + MIRROR_W mirror words (STUDY: 65,536 + mirror, 98,304 total).
  map         the address -> slice map the command processor uses: runs of equal class in logical order, each packed
              contiguously in its region (local q at phys 0.., mirror at phys LOCAL_W..); segment table
              [lo, len, cls, phys].  Per executed record and cluster the exporter also emits the physical
              sub-descriptor (base, n, m, stride, istride), which must be 2-D affine in physical space.
  split       SM.MATVEC   ESPLIT: output rows (= weight rows) split 4 ways, balanced; A whole (MIRROR); weight rows
                          of cluster q are the ones its HBM stack must hold.  MoE expert slots are SM records, so every
                          expert's rows split over all 4 clusters by construction; expert outputs that a later record
                          needs whole are MIRROR (the gather is the mirror-write broadcast of each quarter).
              ATT.QK/PV   ESPLIT over KV positions (each cluster's quarter of the context from its own stack);
                          QK has no reduction across positions; PV's sum over positions is a CHAIN.
              SU.VOP      RSPLIT (rows) or ESPLIT (elements); a reduction across the split is a CHAIN.
              SFU.GLU     RSPLIT / ESPLIT, elementwise.
              others      CENTRAL ring clients (FUSED, COLL, IDX, HC, ARGMAX, DMA, SIMT): read and write any slice.
  chain       a reduction split across clusters is combined cluster 0 -> 1 -> 2 -> 3 carrying the golden csum8
              binary-counter state (hgi_b2.reduce): bit-exact for any split.  MAX is order-free.  The result is MIRROR.

The check (pass 2) runs every split record once per cluster with every word the cluster may NOT read (not LOCAL q,
not MIRROR, not an I/n_sel word the command processor resolves) perturbed, and requires (a) every output word the
cluster owns to equal the golden run bit for bit, (b) every chained reduction's per-cluster input block to equal the
golden block and the chained combine to equal the golden reduction bit for bit, (c) every per-cluster operand to be
placement-legal and physically affine.  A record that breaks (a)-(c) is refused (PlacementError).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

import numpy as np

from hgi_sim import machine as MC
from hgi_sim import lib as A
from hgi_b2 import reduce as RD

NQ = 4
VMW = MC.VM_WORDS
LOCAL_W = 65536
MIRROR_W = 32768
SLICE_W = LOCAL_W + MIRROR_W
MIR = NQ
SPLIT_UNITS = {"SM", "SU", "SFU", "ATT"}
F = np.float32


class PlacementError(Exception):
    pass


def rng(n, q):
    return q * n // NQ, (q + 1) * n // NQ


def ga(base, st, ist, rows, cols):
    o, i = np.meshgrid(np.asarray(rows, np.int64), np.asarray(cols, np.int64), indexing="ij")
    return (base + o * st + i * ist).reshape(-1)


# ------------------------------------------------------------------------------------------------ per-record split
class Split:
    """How one executed record (on one die) splits over the clusters.
    ops: [(name, role, kind, per)]: role in/out/red; kind grid (per[q] = addresses cluster q touches) / whole (per =
    the addresses every cluster reads) / hbm (per[q] = (rows, bytes)) / stream."""

    def __init__(self, mode, grid=(0, 0), chain=None):
        self.mode, self.grid, self.chain = mode, grid, chain
        self.ops = []
        self.part = {}              # q -> (rows range, cols range) of the grid
        self.red_cols = {}          # chain: q -> [c0, c1) on the reduced axis of every hooked reduction
        self.sub = {}               # (name, q) -> logical sub-descriptor [base, n, m, st, ist]


def _cp_words(M, r, die, L):
    """VM words the command processor reads to resolve operands (I base / n_sel / index words): never perturbed."""
    out = []
    i_ = r.desc.get("I")
    if i_ is not None and i_.space == "VM":
        try:
            out.append(M.vm_addrs(i_, die, L))
        except MC.Fault:
            pass
        ib = M._plain_base(i_, die, L)
        out.append(np.array([ib + L, ib + i_.stride + L], np.int64))
    return np.concatenate(out) if out else np.zeros(0, np.int64)


def split_of(M, r, die, L):
    u = r.unit
    if u not in SPLIT_UNITS:
        return Split("CENTRAL")
    E = lambda nm: M.eff(r.desc[nm], die, L)          # noqa: E731
    if u == "SM":
        o = r.desc["O"]
        ob, on, om, ost, oist = E("O")
        s = Split("ESPLIT", (om, on))
        for q in range(NQ):
            s.part[q] = ((0, om), rng(on, q))
        if o.space == "VM":
            s.ops.append(("O", "out", "grid", {q: ga(ob, ost, oist, range(om), range(*rng(on, q))) for q in range(NQ)}))
        else:
            s.ops.append(("O", "out", "stream", None))
        if r.desc["A"].space == "VM":
            s.ops.append(("A", "in", "whole", M.vm_addrs(r.desc["A"], die, L)))
        bb, bn, bm, bst, _ = E("B")
        s.ops.append(("B", "in", "hbm", {q: (rng(bm, q), (rng(bm, q)[1] - rng(bm, q)[0]) * bst) for q in range(NQ)}))
        for q in range(NQ):
            c0, c1 = rng(on, q)
            s.sub[("O", q)] = [ob + c0 * oist, c1 - c0, om, ost, oist]
            s.sub[("B", q)] = [bb + rng(bm, q)[0] * bst, bn, rng(bm, q)[1] - rng(bm, q)[0], bst, 0]
        return s
    if u == "ATT":
        lanes = (r.param & 0xF) or 16
        bb, bn, bm, bst, _ = E("B")
        P = bn + (E("C")[1] if r.desc.get("C") is not None else 0)
        ab, an, am, ast, aist = E("A")
        ob, on, om, ost, oist = E("O")
        if r.op == "QK":
            s = Split("ESPLIT", (lanes, P))
            s.ops.append(("A", "in", "whole", ga(ab, ast, aist, range(lanes), range(an))))
            s.ops.append(("O", "out", "grid", {q: ga(ob, ost, oist, range(lanes), range(*rng(P, q))) for q in range(NQ)}))
            for q in range(NQ):
                c0, c1 = rng(P, q)
                s.sub[("O", q)] = [ob + c0 * oist, c1 - c0, lanes, ost, oist]
        else:
            s = Split("ESPLIT", (lanes, P), chain="SUM")
            s.ops.append(("A", "in", "grid", {q: ga(ab, ast, aist, range(lanes), range(*rng(P, q))) for q in range(NQ)}))
            s.ops.append(("O", "red", "whole", ga(ob, ost, oist, range(lanes), range(on))))
            for q in range(NQ):
                c0, c1 = rng(P, q)
                s.sub[("A", q)] = [ab + c0 * aist, c1 - c0, lanes, ast, aist]
                s.red_cols[q] = (c0, c1)
        for q in range(NQ):
            s.part[q] = ((0, lanes), rng(P, q))
        s.ops.append(("B", "in", "hbm", {q: (rng(P, q), 0) for q in range(NQ)}))
        return s
    if u == "SFU":
        ob, on, om, ost, oist = E("O")
        mode = "RSPLIT" if om >= NQ else "ESPLIT"
        s = Split(mode, (om, on))
        for q in range(NQ):
            s.part[q] = (rng(om, q), (0, on)) if mode == "RSPLIT" else ((0, om), rng(on, q))
        for nm in ("A", "B", "O"):
            b, n, m, st, ist = E(nm)
            if (m, n) == (om, on):
                per = {q: ga(b, st, ist, range(*s.part[q][0]), range(*s.part[q][1])) for q in range(NQ)}
                s.ops.append((nm, "out" if nm == "O" else "in", "grid", per))
                for q in range(NQ):
                    (r0, _), (c0, c1) = s.part[q]
                    s.sub[(nm, q)] = [b + r0 * st + c0 * ist, c1 - c0, s.part[q][0][1] - r0, st, ist]
            else:
                s.ops.append((nm, "in", "whole", M.vm_addrs(r.desc[nm], die, L)))
        if r.desc.get("C") is not None and r.desc["C"].space == "VM":
            s.ops.append(("C", "in", "whole", M.vm_addrs(r.desc["C"], die, L)))
        return s
    # SU.VOP
    f = r.sut
    _, ni, no, _, _ = E("A")
    red, whole = int(f["red"]), bool(f["red_whole"] or f["red_tree"])
    chain = None
    if red and whole:
        mode = "RSPLIT" if no > 1 else "ESPLIT"
        chain = "SUM" if red == MC.I.RED_SUM else "MAX"
    elif red:
        if ni >= NQ * 64 or no < NQ:
            mode, chain = "ESPLIT", ("SUM" if red == MC.I.RED_SUM else "MAX")
        else:
            mode = "RSPLIT"
    else:
        mode = "RSPLIT" if no >= NQ else "ESPLIT"
    s = Split(mode, (no, ni), chain)
    for q in range(NQ):
        s.part[q] = (rng(no, q), (0, ni)) if mode == "RSPLIT" else ((0, no), rng(ni, q))
        if chain:
            (r0, r1), (c0, c1) = s.part[q]
            s.red_cols[q] = (r0 * ni, r1 * ni) if (whole and mode == "RSPLIT") else (c0, c1)
    a_per = None
    for nm in ("A", "B", "C", "D", "O"):
        d = r.desc.get(nm)
        if d is None or d.space != "VM" or (nm == "O" and not f["dst"]):
            if d is not None and d.space == "STREAM":
                s.ops.append((nm, "out" if nm == "O" else "in", "stream", None))
            continue
        b, _, _, st, ist = E(nm)
        half = bool(f["b_half"]) and nm in ("B", "D")
        per = {}
        for q in range(NQ):
            (r0, r1), (c0, c1) = s.part[q]
            cols = (np.arange(c0, c1) >> 1) if half else np.arange(c0, c1)
            per[q] = ga(b, st, ist, range(r0, r1), cols)
            if half:
                nh = (((c1 - 1) >> 1) - (c0 >> 1) + 1) if c1 > c0 else 0
                s.sub[(nm, q)] = [b + r0 * st + (c0 >> 1) * ist, nh, r1 - r0, st, ist]
            else:
                s.sub[(nm, q)] = [b + r0 * st + c0 * ist, c1 - c0, r1 - r0, st, ist]
        if nm == "A":
            a_per = per
        s.ops.append((nm, "out" if nm == "O" else "in", "grid", per))
    if f["c_pair"] and a_per is not None:
        s.ops.append(("C", "in", "grid", {q: a_per[q] ^ 1 for q in range(NQ)}))
    if red:
        rb, _, _, rst, _ = E("R")
        nred = 1 if whole else no
        ra = rb + np.arange(nred) * (rst or 1)
        if chain:
            s.ops.append(("R", "red", "whole", ra))
        else:
            s.ops.append(("R", "out", "grid", {q: ra[slice(*s.part[q][0])] for q in range(NQ)}))
    return s


# ------------------------------------------------------------------------------------------------ pass 1: demands
class Collect:
    """Pass 1: run the golden program, record which clusters need every VM word."""

    def __init__(self):
        self.need = np.zeros(VMW, np.uint8)       # bit q: cluster q reads / writes it in a split record
        self.central = np.zeros(VMW, bool)        # a central ring client reads / writes it
        self.modes = Counter()
        self.subs = set()                         # per-cluster VM sub-operands (one physical descriptor each)

    def _central(self, M, r, die, L):
        for nm, d in r.desc.items():
            if d.space == "VM":
                try:
                    a = M.vm_addrs(d, die, L)
                    self.central[a[(a >= 0) & (a < VMW)]] = True
                except MC.Fault:
                    pass

    def wrap(self, key, fn):
        def run(M, r, L):
            dies, cur = M.dies, M.cur
            try:
                if r.unit not in SPLIT_UNITS:
                    for die in dies:
                        M.dies, M.cur = [die], M.rec_of(die, r)
                        self._central(M, M.cur, die, L)
                    self.modes[(r.unit, "CENTRAL")] += 1
                else:
                    for die in dies:
                        M.dies, M.cur = [die], M.rec_of(die, r)
                        s = split_of(M, M.cur, die, L)
                        self.modes[(r.unit, s.mode + ("+" + s.chain if s.chain else ""))] += 1
                        for (nm, q), t in s.sub.items():
                            if nm != "B" and t[1] > 0 and t[2] > 0:
                                self.subs.add(tuple(int(x) for x in t))
                        for nm, role, kind, per in s.ops:
                            if kind == "grid":
                                for q in range(NQ):
                                    self.need[per[q]] |= np.uint8(1 << q)
                            elif kind == "whole":
                                self.need[per] |= np.uint8(0xF)
            finally:
                M.dies, M.cur = dies, cur
            return fn(M, r, L)
        return run

    def placement(self):
        cls = np.full(VMW, -1, np.int8)
        pc = np.zeros(VMW, np.int64)
        nb = self.need
        cnt = ((nb >> 0) & 1) + ((nb >> 1) & 1) + ((nb >> 2) & 1) + ((nb >> 3) & 1)
        cls[cnt >= 2] = MIR
        for q in range(NQ):
            cls[(cnt == 1) & (((nb >> q) & 1) == 1)] = q
        only_c = (cnt == 0) & self.central
        w = np.nonzero(only_c)[0]
        cls[w] = (w // 256) % NQ
        # closure: a cluster's sub-operand is ONE physical descriptor, so it must sit in one region: promote a mixed one
        # to MIRROR until stable
        self.promoted = 0
        for _ in range(16):
            ch = 0
            for b, n, m, st, ist in self.subs:
                la = ga(b, st, ist, range(m), range(n))
                la = la[(la >= 0) & (la < VMW)]
                c = cls[la]
                if c.size and not np.all(c == c[0]):
                    ch += int(np.sum(c != MIR))
                    cls[la] = MIR
            self.promoted += ch
            if not ch:
                break
        return Placement(cls)


# ------------------------------------------------------------------------------------------------ the map
class Placement:
    def __init__(self, cls):
        self.cls = cls
        self.phys = np.full(VMW, -1, np.int64)
        use = {}
        for c in range(NQ + 1):
            w = np.nonzero(cls == c)[0]
            base = LOCAL_W if c == MIR else 0
            self.phys[w] = base + np.arange(len(w))
            use[c] = len(w)
        self.use = use
        segs = []
        t = np.nonzero(cls >= 0)[0]
        if len(t):
            brk = np.nonzero((np.diff(t) != 1) | (np.diff(cls[t]) != 0))[0]
            starts = np.concatenate([[0], brk + 1])
            ends = np.concatenate([brk + 1, [len(t)]])
            for s0, e0 in zip(starts, ends):
                lo = int(t[s0])
                segs.append([lo, int(e0 - s0), int(cls[lo]), int(self.phys[lo])])
        self.segs = segs

    def capacity(self):
        loc = [self.use[q] for q in range(NQ)]
        return dict(local_words=loc, mirror_words=self.use[MIR], local_cap=LOCAL_W, mirror_cap=MIRROR_W,
                    slice_words=[x + self.use[MIR] for x in loc], slice_cap=SLICE_W,
                    fits=bool(max(loc) <= LOCAL_W and self.use[MIR] <= MIRROR_W),
                    fits_slice=bool(max(loc) + self.use[MIR] <= SLICE_W), segments=len(self.segs))

    def table(self):
        return dict(schema="opentallas.hgi_b2.placement.v1", nq=NQ, vm_words=VMW, local_w=LOCAL_W, mirror_w=MIRROR_W,
                    mirror_phys_base=LOCAL_W, cls_codes={"0..3": "LOCAL slice q", "4": "MIRROR (every slice)"},
                    segments_fields=["logical_lo", "len", "cls", "phys_lo"], segments=self.segs,
                    capacity=self.capacity())

    def slice_image(self, vm, q):
        img = np.zeros(SLICE_W, np.uint32)
        for c in (q, MIR):
            w = np.nonzero(self.cls == c)[0]
            img[self.phys[w]] = vm[w]
        return img

    def avail(self, q):
        return (self.cls == q) | (self.cls == MIR)


def affine(ph, rows, cols):
    """physical addresses on a rows x cols grid -> (base, st, ist) if 2-D affine else None."""
    if ph.size == 0:
        return (0, 0, 0)
    g = ph.reshape(rows, cols)
    st = int(g[1, 0] - g[0, 0]) if rows > 1 else 0
    ist = int(g[0, 1] - g[0, 0]) if cols > 1 else 0
    want = g[0, 0] + np.arange(rows)[:, None] * st + np.arange(cols)[None, :] * ist
    return (int(g[0, 0]), st, ist) if np.array_equal(g, want) else None


# ------------------------------------------------------------------------------------------------ pass 2: check
class Check:
    """Pass 2: placement asserts + masked per-cluster execution + chain proof, on every die; per-record B2 dispatch."""

    def __init__(self, pl: Placement, die0, seed=12, refuse=True, mutant=None):
        """mutant (the check's own teeth; each must FAIL): stale_mirror = a cluster sees no mirror copy (the
        mirror-write broadcast / collective broadcast never arrived); chain_naive = per-cluster csums combined by a
        pairwise tree instead of the carried golden counter state."""
        self.pl, self.die0, self.refuse, self.mutant = pl, die0, refuse, mutant
        self.rng = np.random.default_rng(seed)
        self.avail = [pl.avail(q) for q in range(NQ)]
        self.viol = []
        self.stats = Counter()
        self.ring = Counter()
        self.recs = []              # rank 0, one per executed dispatched record (Capture order)
        self.hbm_q = np.zeros(NQ, np.int64)

    def fail(self, msg):
        self.viol.append(msg)
        self.stats["violations"] += 1
        if self.refuse and len(self.viol) == 1:
            pass                    # collect all, raise at the end (finish)

    def _poison(self, vm, q, keep):
        p = vm.copy()
        bad = (self.pl.cls != q) if self.mutant == "stale_mirror" else ~self.avail[q]
        bad[keep[(keep >= 0) & (keep < VMW)]] = False
        idx = np.nonzero(bad)[0]
        x = self.rng.integers(0, 1 << 32, idx.size, dtype=np.uint64).astype(np.uint32)
        p[idx] ^= (x & np.uint32(0x07070707)) | np.uint32(0x01010101)
        return p

    def _static(self, s, tag, rank):
        cls = self.pl.cls
        for nm, role, kind, per in s.ops:
            if kind == "grid":
                for q in range(NQ):
                    a = per[q]
                    if a.size and not np.all(self.avail[q][a]):
                        self.fail(f"rank {rank} {tag} {nm}: cluster {q} touches {int((~self.avail[q][a]).sum())} words "
                                  f"outside slice {q} / mirror")
            elif kind == "whole" and per.size and not np.all(cls[per] == MIR):
                self.fail(f"rank {rank} {tag} {nm}: whole operand ({role}) not MIRROR ({int((cls[per] != MIR).sum())} words)")

    def _phys_sub(self, s, rank):
        """physical per-cluster descriptors; refuse a non-affine one"""
        out = {}
        for (nm, q), (b, n, m, st, ist) in s.sub.items():
            if nm == "B":
                out[f"{nm}{q}"] = dict(hbm=[int(b), int(n), int(m), int(st), int(ist)])
                continue
            if n <= 0 or m <= 0:
                continue
            la = ga(b, st, ist, range(m), range(n))
            if la.min() < 0 or la.max() >= VMW:
                continue
            ph = self.pl.phys[la]
            cl = self.pl.cls[la]
            af = affine(ph, m, n)
            region = int(cl[0])
            if af is None or region < 0 or not np.all(cl == region):
                self.fail(f"rank {rank} {s.tag} {nm}: cluster {q} sub-operand not affine in slice space")
                continue
            out[f"{nm}{q}"] = dict(logical=[int(b), int(n), int(m), int(st), int(ist)], region=region,
                                   phys=[af[0], int(n), int(m), af[1], af[2]])
        return out

    def wrap(self, key, fn):
        def run(M, r, L):
            dies, cur = M.dies, M.cur
            hook_prev = MC.RED_HOOK
            try:
                if r.unit not in SPLIT_UNITS:
                    self._central_ring(M, r, dies, L)
                    M.dies, M.cur = dies, cur
                    return fn(M, r, L)
                for die in dies:
                    M.dies, M.cur = [die], M.rec_of(die, r)
                    self._one(M, M.cur, die, L, fn)
            finally:
                MC.RED_HOOK = hook_prev
                M.dies, M.cur = dies, cur
        return run

    def _central_ring(self, M, r, dies, L):
        for die in dies:
            if die.rank != 0:
                continue
            M.dies, M.cur = [die], M.rec_of(die, r)
            rd = wr = 0
            for nm, d in M.cur.desc.items():
                if d.space != "VM":
                    continue
                try:
                    a = M.vm_addrs(d, die, L)
                except MC.Fault:
                    continue
                a = a[(a >= 0) & (a < VMW)]
                if nm in ("O", "R", "D") and r.unit != "SU":
                    wr += int(np.sum(np.where(self.pl.cls[a] == MIR, NQ, 1)))
                else:
                    rd += a.size
            self.ring["central_read"] += rd
            self.ring["central_write"] += wr
            self.recs.append(dict(unit=r.unit, op=r.op, tag=getattr(M.cur, "tag", ""), L=int(L), mode="CENTRAL",
                                  ring_read=rd, ring_write=wr))

    def _one(self, M, r, die, L, fn):
        rank = die.rank
        s = split_of(M, r, die, L)
        s.tag = f"{r.unit}.{r.op}[{getattr(r, 'tag', '')}]@L{L}"
        self._static(s, s.tag, rank)
        sub = self._phys_sub(s, rank)
        keep = _cp_words(M, r, die, L)
        pre = die.vm.copy()
        st_pre = ({k: v.copy() for k, v in die.streams.items()}, dict(die.stream_seen)) if hasattr(die, "streams") else None
        posts, reds = [], []
        for q in range(NQ):
            die.vm[:] = self._poison(pre, q, keep)
            if st_pre is not None:
                die.streams, die.stream_seen = {k: v.copy() for k, v in st_pre[0].items()}, dict(st_pre[1])
            cap = []
            MC.RED_HOOK = lambda kind, op, t, cap=cap: cap.append((kind, op, np.asarray(t, F).copy()))
            try:
                fn(M, r, L)
                posts.append(die.vm.copy())
            except MC.Fault as ex:
                self.fail(f"rank {rank} {s.tag}: cluster {q} masked run faults ({ex})")
                posts.append(None)
            MC.RED_HOOK = None
            reds.append(cap)
        die.vm[:] = pre
        if st_pre is not None:
            die.streams, die.stream_seen = {k: v.copy() for k, v in st_pre[0].items()}, dict(st_pre[1])
        gcap = []
        MC.RED_HOOK = lambda kind, op, t: gcap.append((kind, op, np.asarray(t, F).copy()))
        fn(M, r, L)                                         # the golden execution (the state the run continues from)
        MC.RED_HOOK = None
        # (a) owned outputs bit-exact
        nout = 0
        for nm, role, kind, per in s.ops:
            if role != "out" or kind != "grid":
                continue
            for q in range(NQ):
                a = per[q]
                if posts[q] is None or not a.size:
                    continue
                bad = int(np.sum(posts[q][a] != die.vm[a]))
                nout += a.size
                if bad:
                    self.fail(f"rank {rank} {s.tag} {nm}: cluster {q} computes {bad}/{a.size} owned words wrong "
                              f"from its slice + mirror")
        # (b) chained reductions
        hop = 0
        if s.chain:
            if any(len(c) != len(gcap) for c in reds):
                self.fail(f"rank {rank} {s.tag}: reduction count differs between masked and golden runs")
            for j, (kind, op, G) in enumerate(gcap):
                parts = []
                for q in range(NQ):
                    c0, c1 = s.red_cols[q]
                    Q = reds[q][j][2] if j < len(reds[q]) else None
                    if Q is None or Q.shape != G.shape or not np.array_equal(Q[:, c0:c1].view(np.uint32),
                                                                             G[:, c0:c1].view(np.uint32)):
                        self.fail(f"rank {rank} {s.tag}: cluster {q} reduction block {j} not computable locally")
                    parts.append(G[:, c0:c1] if Q is None else Q[:, c0:c1])
                if s.chain == "SUM":
                    got, h = RD.chain(parts)
                    if self.mutant == "chain_naive":
                        got = A.pairwise([A.csum(p_) for p_ in parts if p_.shape[1]])
                    want = A.csum(G)
                else:
                    nz = [p for p in parts if p.shape[1]]
                    got, h = np.maximum.reduce([p.max(axis=1) for p in nz]).astype(F), G.shape[0]
                    want = G.max(axis=1).astype(F)
                hop = max(hop, h)
                if not np.array_equal(np.asarray(got, F).reshape(-1).view(np.uint32),
                                      np.asarray(want, F).reshape(-1).view(np.uint32)):
                    self.fail(f"rank {rank} {s.tag}: chained {s.chain} {j} != golden order")
                self.stats["chain_reductions"] += 1
        self.stats["split_records"] += 1
        self.stats["owned_words_checked"] += nout
        if die.rank == 0:
            mb = 0
            for nm, role, kind, per in s.ops:
                if role == "out" and kind == "grid":
                    for q in range(NQ):
                        mb += int(np.sum(self.pl.cls[per[q]] == MIR)) * (NQ - 1)
                elif role == "red":
                    mb += int(per.size) * (NQ - 1)
            self.ring["mirror_broadcast"] += mb
            self.ring["chain_state"] += hop * (NQ - 1)
            work = {q: int((s.part[q][0][1] - s.part[q][0][0]) * (s.part[q][1][1] - s.part[q][1][0]))
                    for q in range(NQ)} if s.part else {}
            for nm, role, kind, per in s.ops:
                if kind == "hbm":
                    for q in range(NQ):
                        self.hbm_q[q] += per[q][1]
            self.recs.append(dict(unit=r.unit, op=r.op, tag=getattr(r, "tag", ""), L=int(L), mode=s.mode,
                                  chain=s.chain, grid=list(map(int, s.grid)), work=work, sub=sub,
                                  mirror_broadcast=mb, chain_hop_words=hop))

    def finish(self):
        return dict(violations=len(self.viol), first_violations=self.viol[:40], stats=dict(self.stats),
                    ring_words=dict(self.ring), hbm_weight_bytes_per_cluster=[int(x) for x in self.hbm_q])


def write(out, pl, chk, collect, vm0, vm_final, meta_extra):
    out.mkdir(parents=True, exist_ok=True)
    for q in range(NQ):
        (out / f"vm0_s{q}.bin").write_bytes(pl.slice_image(vm0, q).astype("<u4").tobytes())
        (out / f"vm_final_s{q}.bin").write_bytes(pl.slice_image(vm_final, q).astype("<u4").tobytes())
    (out / "placement.json").write_text(json.dumps(pl.table(), default=int) + "\n")
    (out / "records_b2.json").write_text(json.dumps(chk.recs, default=int) + "\n")
    v = chk.finish()
    split_work = defaultdict(lambda: [0] * NQ)
    for e in chk.recs:
        for q, w in (e.get("work") or {}).items():
            split_work[e["unit"]][int(q)] += w
    verdict = dict(schema="opentallas.hgi_b2.verdict.v1", **meta_extra, capacity=pl.capacity(),
                   modes={f"{k[0]}:{k[1]}": n for k, n in sorted(collect.modes.items())},
                   work_per_cluster=dict(split_work), **v,
                   exact=bool(v["violations"] == 0))
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=int) + "\n")
    return verdict
