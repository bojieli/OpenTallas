"""B2 compiler pass: per-quadrant VM placement, per-cluster record split and the bit-exact check, for the HBM die with
four clusters and a distributed VM (results/arch/hbm_b2_1012/SPEC.md, results/arch/hbm_die_phy_study_1012/STUDY.md).

HGI-1 is unchanged: a record still names one logical VM (262,144 words).  This pass decides, for the program the
compiler emitted, where every logical word lives and which cluster computes what:

  placement   every touched logical word is LOCAL q (slice q only) or MIRROR (the same copy in every slice's mirror
              window).  A word that a split record needs on more than one cluster (an SM activation, a scalar
              broadcast, a reduction result) is MIRROR; a word only one cluster reads or writes is LOCAL to it.  Words
              only the central ring clients touch is LOCAL to the home cluster of the first central record that
              touches it (home = the cluster holding most of that record's already-LOCAL words, else the least loaded
              slice), so a central client's private operands never cross the ring.
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
              DMA group   NATIVE: a member of a native dispatch group (header parameter bit 0, hgi_b2.mtp_swap: the
                          MTP column swap) is cluster q's own linear record (q = its HBM stack): its VM operand is
                          needed by cluster q and is ONE physical descriptor there (LOCAL q or MIRROR); it never
                          rides the ring.  Refused if any of its words is LOCAL to another cluster.
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
from hgi_b2 import mtp_swap as MS

NQ = 4
VMW = MC.VM_WORDS
LOCAL_W = 65536
MIRROR_W = 32768
SLICE_W = LOCAL_W + MIRROR_W
# SPEC.md v0.5 (main 87eead465) address map, PARAMETERS (RTL / compiler / sim agree); decode by RANGE, never by a bit:
#   addr < REPL_BASE -> slice addr[17:16]; [REPL_BASE, +REPL_W) -> local mirror; [HCAP_BASE, +HCAP_W) -> HC aperture
REPL_BASE = 262144
REPL_W = MIRROR_W
HCAP_BASE = 294912          # v0.5: HC weight aperture moved up from HGI-1's 262,144 (overlapped REPL)
HCAP_W = MC.VM_AP           # 65,536; the simulator's logical aperture is [VM_WORDS, VM_WORDS + VM_AP)
SPEC_WORDS = HCAP_BASE + HCAP_W   # 360,448: the die VM image / simulated address space
assert REPL_BASE + REPL_W <= HCAP_BASE and NQ * LOCAL_W <= REPL_BASE
MIR = NQ
SPLIT_UNITS = {"SM", "SU", "SFU", "ATT"}
VEC_HOME = 0                # the vector home cluster: small vector records run there, on operands LOCAL to it


REPLX_MAX_IN = 16384        # REPLX operands (all MIRROR) at most this many words
SPLIT_MIN = 3072            # a vector producer splits only if its quarter covers the hop: N / 4 / 64 >= 12 cycles


def out_words(M, r, die, L):
    """number of VM words the record writes (O, or SU.VOP's R when it has no O)"""
    try:
        if r.unit == "SU" and not r.sut["dst"]:
            _, n, m, _, _ = M.eff(r.desc["R"], die, L) if int(r.sut["red"]) else (0, 0, 0, 0, 0)
        else:
            _, n, m, _, _ = M.eff(r.desc["O"], die, L)
    except (MC.Fault, KeyError):
        return 0
    return n * m


def replx(M, r, die, L):
    """REPLX: a small vector record (SU.VOP / SFU / FUSED.ROW_NORM writing < SPLIT_MIN words) runs WHOLE on every
    cluster from MIRROR operands, each cluster writing its own mirror copy of the result: no ring, no broadcast, no
    chain (a reduction is recomputed in the golden order, bit-exact by construction).  A split would leave each
    cluster a local lead of N/4/64 < 12 cycles (exposed), a single home would expose the full hop on 3 clusters
    (Qwen L0 measured 12 x ~10 records)"""
    if r.unit not in ("SU", "SFU") and not osplit(r):
        return False
    n = out_words(M, r, die, L)
    if not 0 < n < SPLIT_MIN:
        return False
    rd = 0                                  # every operand goes MIRROR: only small operands (a softmax.max over a
    for nm, d in r.desc.items():            # [heads x positions] buffer stays a chained ESPLIT)
        if d is not None and d.space == "VM" and nm != "O":
            try:
                _, a_n, a_m, _, _ = M.eff(d, die, L)
            except MC.Fault:
                return False
            rd += a_n * a_m
    return rd <= REPLX_MAX_IN


def osplit(r):
    """FUSED.ROW_NORM of a long vector runs on every cluster (OSPLIT): the whole input is MIRROR, each cluster
    recomputes the row statistic in the golden order (bit-exact by construction, no chain) and writes only its quarter
    of the output (local lead N/4/64 >= 12 cycles covers the mirror stream of the other three quarters)"""
    return (r.unit, r.op) == ("FUSED", "ROW_NORM")


def central(M, r, die, L):
    return not (r.unit in SPLIT_UNITS or osplit(r))


F = np.float32

# ring / broadcast cost model: the verification harness's (tools/hgi_e2e/b2.py on el1012-b2verif), same constants;
# results/arch/hbm_b2_1012/b2_params.json (from SPEC.md) overrides key by key when it exists
RING = dict(ring_link_bits=2048, ring_hop_cycles=16, bcast_bits=1024, bcast_hops=2,
            budget_cycles_per_layer=dict(ds=290, qwen=93), source="provisional (PHY study STUDY.md)")


def ring_params():
    import os
    from pathlib import Path
    f = Path(os.environ.get("HGI_B2_PARAMS", Path(__file__).resolve().parents[2] / "results/arch/hbm_b2_1012/b2_params.json"))
    out = dict(RING)
    if f.exists():
        out.update({k: v for k, v in json.loads(f.read_text()).items() if k in RING})
        out["source"] = str(f)
    return out


def _hops(a, b):
    d = abs(a - b)
    return min(d, NQ - d)


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
    if central(M, r, die, L):
        return Split("CENTRAL")
    E = lambda nm: M.eff(r.desc[nm], die, L)          # noqa: E731
    if replx(M, r, die, L):
        s = Split("REPLX", (1, out_words(M, r, die, L)))
        outs = {"O"} if not (u == "SU" and not r.sut["dst"]) else set()
        if u == "SU" and int(r.sut["red"]):
            outs.add("R")
        for nm, d in r.desc.items():
            if d is None or d.space != "VM":
                continue
            a_ = M.vm_addrs(d, die, L)
            if nm in outs:
                s.ops.append((nm, "out", "grid", {q: a_ for q in range(NQ)}))
            if nm not in outs:
                s.ops.append((nm, "in", "whole", a_))
            elif u == "SU" and nm == "O":           # MIRROR assertion only: SU.VOP never READS O (machine.u_su_vop),
                s.ops.append((nm, "own", "whole", a_))   # so liveness must see a pure write (was "in": every REPLX
                                                    # output became live-in, DS L14 34,420 mirror words held from -1)
        for q in range(NQ):
            s.part[q] = ((0, 1), (0, s.grid[1]))
        return s
    if osplit(r):
        ob, on, om, ost, oist = E("O")
        rows = om >= NQ
        s = Split("OSPLIT", (om, on))
        for q in range(NQ):
            s.part[q] = (rng(om, q), (0, on)) if rows else ((0, om), rng(on, q))
        s.ops.append(("A", "in", "whole", M.vm_addrs(r.desc["A"], die, L)))
        s.ops.append(("O", "out", "grid", {q: ga(ob, ost, oist, range(*s.part[q][0]), range(*s.part[q][1]))
                                           for q in range(NQ)}))
        bb, bn, bm, bst, bist = E("B")
        s.ops.append(("B", "in", "hbm", {q: (rng(bn, q), (rng(bn, q)[1] - rng(bn, q)[0]) * 2) for q in range(NQ)}))
        for q in range(NQ):
            (r0, r1), (c0, c1) = s.part[q]
            s.sub[("O", q)] = [ob + r0 * ost + c0 * oist, c1 - c0, r1 - r0, ost, oist]
        return s
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
    elif red and no == NQ:
        mode = "RSPLIT"                 # one row per cluster (the DS HC residual's 4 streams): a row reduction stays on
                                        # its cluster in golden order, and the partition matches the elementwise ops below
    elif red:
        if ni >= NQ * 64 or no < NQ:
            mode, chain = "ESPLIT", ("SUM" if red == MC.I.RED_SUM else "MAX")
        else:
            mode = "RSPLIT"
    else:
        # elementwise: any partition is exact, so follow the long axis -- a [heads x positions] softmax buffer splits by
        # POSITION like its QK producer / ESPLIT reductions / PV consumer (a head split here made every P word needed by
        # two clusters: 65,536 MIRROR words at Qwen P8191, 2.3x the REPL window)
        # ROWS == CLUSTERS (the DS HC residual, 4 streams x hidden): one row per cluster, so the residual, its engram
        # mixes and their row reductions (RSPLIT above) share ONE partition and the residual stays LOCAL (a column
        # split here against the row-split reductions made all 20,480 residual words MIRROR at L14)
        mode = "RSPLIT" if no == NQ else "ESPLIT" if ni >= NQ * 64 else ("RSPLIT" if no >= NQ else "ESPLIT")
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

    def __init__(self, mutant=None):
        """mutant alias_dead (the alias proof's teeth): every word's lifetime collapsed to its first touch, so the
        allocator reuses words that are still live; the rank-0 alias proof must refuse it"""
        self.mutant = mutant
        # PER DIE (rank): every HBM die is its own VM address space with its own cmdproc slice map, and an SPMD
        # program's rank-dependent bases (EP slot rows, per-rank expert columns) touch different words on every die.
        # The union over the 96 ranks counted every rank's private rows against ONE die's mirror (DS L2: 125,091 /
        # 32,768); the per-die maps are what each die loads.
        self.rk = {}
        self.modes = Counter()
        self.t = 0                  # record clock (program order), shared by every die
        self.trace = []             # rank 0: (touched words, values before, values after) per record: the alias proof
        self.vm0 = None             # rank 0 VM before the first record
        self.outside = []           # rank 0: records that changed VM words outside their tracked operands

    def _r(self, rank):
        if rank not in self.rk:
            self.rk[rank] = dict(need=np.zeros(VMW, np.uint8),   # bit q: cluster q reads / writes it in a split record
                                 central=np.zeros(VMW, bool),    # a central ring client reads / writes it
                                 subs=set(),                     # per-cluster VM sub-operands (one descriptor each)
                                 crecs=[],                       # the VM words of every central record, program order
                                 # liveness (record clock): first / last touch, first touch a pure write, last touch
                                 # writes, ever written
                                 first=np.full(VMW, np.iinfo(np.int32).max, np.int32), last=np.full(VMW, -1, np.int32),
                                 fw=np.zeros(VMW, bool), lw=np.zeros(VMW, bool), wr=np.zeros(VMW, bool))
        return self.rk[rank]

    def _touch(self, D, rd, wr):
        """liveness: this record (clock self.t) reads rd and writes wr (logical VM words)"""
        rd = np.unique(rd[(rd >= 0) & (rd < VMW)]) if len(rd) else np.zeros(0, np.int64)
        wr = np.unique(wr[(wr >= 0) & (wr < VMW)]) if len(wr) else np.zeros(0, np.int64)
        a = np.union1d(rd, wr)
        if not a.size:
            return a, np.zeros(0, bool)
        isw = np.isin(a, wr)
        new = D["first"][a] > self.t
        D["first"][a[new]] = self.t
        D["fw"][a[new]] = isw[new] & ~np.isin(a[new], rd)
        D["last"][a] = self.t
        D["lw"][a] = isw
        D["wr"][wr] = True
        return a, np.isin(a, rd)

    def _central(self, M, r, die, L, seg=None):
        """seg = (q, G): the die's index in its collective group: COLL.ALL_GATHER reads only its own even-split segment
        A[q n / G, (q + 1) n / G) (machine.u_coll_all_gather); the rest of A (in place = O) is a pure write.  Counting
        all of A as read made every gathered buffer live-in from -1 (DS L14: expert intermediate 15,960, eg_kv 9,974,
        iq, qa, y, yf ... mirror words held through the whole layer)"""
        xs, rd, wr = [], [], []
        gq = MS.group_cluster(r)
        if gq is not None:                      # NATIVE: cluster gq's own record; its VM operand is one sub-descriptor
            D = self._r(die.rank)
            for nm, d in r.desc.items():
                if d.space == "VM":
                    a = M.vm_addrs(d, die, L)
                    D["need"][a] |= np.uint8(1 << gq)
                    D["subs"].add(tuple(int(x) for x in M.eff(d, die, L)))
                    (wr if nm == "O" else rd).append(a)
            cat = lambda xs_: np.concatenate(xs_) if xs_ else np.zeros(0, np.int64)   # noqa: E731
            return self._touch(D, cat(rd), cat(wr))
        for nm, d in r.desc.items():
            if d.space == "VM":
                try:
                    a = M.vm_addrs(d, die, L)
                    if seg is not None and nm == "A" and (r.unit, r.op) == ("COLL", "ALL_GATHER"):
                        q, G = seg
                        a = a[q * a.size // G:(q + 1) * a.size // G]
                    a = a[(a >= 0) & (a < VMW)]
                    self._r(die.rank)["central"][a] = True
                    xs.append(a)
                    (wr if nm in ("O", "R") else rd).append(a)      # a central client's O / R: written (the alias
                except MC.Fault:                                    # proof refuses it if one is also read)
                    pass
        rd.append(_cp_words(M, r, die, L))
        if xs:
            self._r(die.rank)["crecs"].append(np.unique(np.concatenate(xs)))
        cat = lambda xs_: np.concatenate(xs_) if xs_ else np.zeros(0, np.int64)   # noqa: E731
        return self._touch(self._r(die.rank), cat(rd), cat(wr))

    def wrap(self, key, fn):
        def run(M, r, L):
            dies, cur = M.dies, M.cur
            t0 = None
            try:
                if central(M, M.rec_of(dies[0], r), dies[0], L):
                    g = max(1, int(M.cfg.get("coll_group_size") or len(dies)))
                    for k, die in enumerate(dies):
                        M.dies, M.cur = [die], M.rec_of(die, r)
                        a = self._central(M, M.cur, die, L, seg=(k % g, min(g, len(dies))))
                        if die.rank == 0:
                            t0 = (die, a)
                    self.modes[(r.unit, "NATIVE" if MS.group_cluster(M.rec_of(dies[0], r)) is not None else
                                "CENTRAL" if r.unit not in SPLIT_UNITS else "HOME")] += 1
                else:
                    for die in dies:
                        M.dies, M.cur = [die], M.rec_of(die, r)
                        s = split_of(M, M.cur, die, L)
                        if die.rank == 0:
                            self.modes[(r.unit, s.mode + ("+" + s.chain if s.chain else ""))] += 1
                        D = self._r(die.rank)
                        for (nm, q), t in s.sub.items():
                            if nm != "B" and t[1] > 0 and t[2] > 0:
                                D["subs"].add(tuple(int(x) for x in t))
                        rd, wr = [_cp_words(M, M.cur, die, L)], []
                        for nm, role, kind, per in s.ops:
                            if kind == "grid":
                                for q in range(NQ):
                                    D["need"][per[q]] |= np.uint8(1 << q)
                                    (rd if role == "in" else wr).append(np.asarray(per[q], np.int64))
                            elif kind == "whole":
                                D["need"][per] |= np.uint8(0xF)
                                (rd if role == "in" else wr).append(np.asarray(per, np.int64))
                        a = self._touch(D, np.concatenate(rd), np.concatenate(wr) if wr else np.zeros(0, np.int64))
                        if die.rank == 0:
                            t0 = (die, a)
            finally:
                M.dies, M.cur = dies, cur
            if t0 is None:
                d0 = next((d for d in dies if d.rank == 0), None)
                t0 = (d0, (np.zeros(0, np.int64), np.zeros(0, bool))) if d0 is not None else None
            if t0 is not None:
                die0, a = t0
                full = die0.vm[:VMW].copy()
                if self.vm0 is None:
                    self.vm0 = full.copy()
                a, rm = a
                before = full[a]
            out = fn(M, r, L)
            if t0 is not None:
                now = die0.vm[:VMW]
                extra = np.setdiff1d(np.nonzero(now != full)[0], a)
                if extra.size:
                    self.outside.append(f"alias proof: {r.unit}.{r.op} changed {extra.size} VM words outside its "
                                        f"tracked operands (first {int(extra[0])})")
                self.trace.append((a, rm, before, now[a].copy()))
                self.vm_final = now.copy()
            self.t += 1
            return out
        return run

    def placement(self):
        """one Placement per die (rank); PlacementSet.of(rank)"""
        self.promoted = 0
        ps = PlacementSet({rk: self._placement(D) for rk, D in sorted(self.rk.items())} or {0: self._placement(self._r(0))})
        ps.proof = self.proof(ps.of(0))
        return ps

    def _placement(self, D):
        cls = np.full(VMW, -1, np.int8)
        nb = D["need"]
        cnt = ((nb >> 0) & 1) + ((nb >> 1) & 1) + ((nb >> 2) & 1) + ((nb >> 3) & 1)
        cls[cnt >= 2] = MIR
        for q in range(NQ):
            cls[(cnt == 1) & (((nb >> q) & 1) == 1)] = q
        only_c = (cnt == 0) & D["central"]
        load = np.array([int(np.sum(cls == q)) for q in range(NQ)], np.int64)
        for a in D["crecs"]:                     # central-private words: LOCAL to the record's home cluster
            fresh = a[only_c[a] & (cls[a] < 0)]
            if not fresh.size:
                continue
            c = cls[a]
            votes = np.bincount(c[(c >= 0) & (c < NQ)].astype(np.int64), minlength=NQ)
            order = sorted(range(NQ), key=lambda q: (q != VEC_HOME, -votes[q], load[q], q))
            h = next((q for q in order if load[q] + fresh.size <= LOCAL_W), order[0])
            cls[fresh] = h
            load[h] += fresh.size
        w = np.nonzero(only_c & (cls < 0))[0]    # (none left: every die records its own central records)
        cls[w] = (w // 256) % NQ
        # closure: a cluster's sub-operand is ONE physical descriptor, so it must sit in one region: promote a mixed one
        # to MIRROR until stable
        for _ in range(16):
            ch = 0
            for b, n, m, st, ist in D["subs"]:
                la = ga(b, st, ist, range(m), range(n))
                la = la[(la >= 0) & (la < VMW)]
                c = cls[la]
                if c.size and not np.all(c == c[0]):
                    ch += int(np.sum(c != MIR))
                    cls[la] = MIR
            self.promoted += ch
            if not ch:
                break
        end = np.iinfo(np.int32).max
        touched = cls >= 0
        live_in = touched & ~D["fw"]                             # first touch reads it: in the VM image at entry
        live_out = touched & (D["lw"] | ~D["wr"])                # last touch writes it, or never written (persistent)
        s_w = np.where(live_in, -1, D["first"]).astype(np.int64)
        e_w = np.where(live_out, end, D["last"]).astype(np.int64)
        if self.mutant == "alias_dead":
            e_w = np.maximum(s_w, D["first"]).astype(np.int64)
        return Placement(cls, *allocate(cls, D["subs"], s_w, e_w), live_in=live_in, live_out=live_out)

    def proof(self, pl):
        """rank 0 alias proof (value level): replay every record on the PHYSICAL slices (a word aliased with a dead
        one shares its physical address): each record must see, on every word it touches, the value the logical run
        saw, and every live-out word must end with the logical final value.  Returns violation strings."""
        if self.vm0 is None:
            return []
        out = list(self.outside[:5])
        sa = np.where(pl.cls == MIR, REPL_BASE + pl.phys - LOCAL_W, pl.cls.astype(np.int64) * LOCAL_W + pl.phys)
        ph = np.zeros(SPEC_WORDS, np.uint32)
        li = np.nonzero(pl.live_in)[0]
        if np.unique(sa[li]).size != li.size:
            out.append(f"alias proof: {li.size - np.unique(sa[li]).size} live-in words share a physical word")
        ph[sa[li]] = self.vm0[li]
        own = np.full(SPEC_WORDS, -1, np.int64)                 # the logical word last written to each physical word
        own[sa[li]] = li
        D0 = self._r(0)
        bad = 0
        for i, (a, rm, before, after) in enumerate(self.trace):
            k = pl.cls[a] >= 0
            a_, b_ = a[k], before[k]
            m = (ph[sa[a_]] != b_) & rm[k]                     # only what the record READS must be intact
            if m.any():
                bad += 1
                if bad <= 3:
                    w0 = int(a_[m][0])
                    o = int(own[sa[w0]])
                    lv = lambda x: (int(D0["first"][x]), int(D0["last"][x]), bool(pl.live_in[x]), bool(pl.live_out[x]))  # noqa: E731
                    out.append(f"alias proof: record #{i} reads {int(m.sum())} words whose physical copy was "
                               f"clobbered (first logical {w0} life {lv(w0)}, physical owner {o} life "
                               f"{lv(o) if o >= 0 else None})")
            ph[sa[a_]] = after[k]
            own[sa[a_]] = a_
        lo = np.nonzero(pl.live_out)[0]
        m = ph[sa[lo]] != self.vm_final[lo]
        if m.any():
            out.append(f"alias proof: {int(m.sum())} live-out words end with a wrong physical value")
        if bad > 3:
            out.append(f"alias proof: {bad} records in all read a clobbered word")
        return out


# ------------------------------------------------------------------------------------------------ the map
class PlacementSet:
    """per-die placements (rank -> Placement). The exported vector is rank 0's die: its images / table / slice map are
    rank 0's; capacity must fit on EVERY die."""

    def __init__(self, by_rank):
        self.by_rank = by_rank
        self.r0 = by_rank[min(by_rank)]
        self.cls, self.phys = self.r0.cls, self.r0.phys

    def of(self, rank):
        return self.by_rank.get(rank, self.r0)

    def capacity(self):
        caps = {rk: p.capacity() for rk, p in self.by_rank.items()}
        worst_m = max(caps, key=lambda rk: caps[rk]["mirror_words"])
        worst_l = max(caps, key=lambda rk: max(caps[rk]["local_words"]))
        c = dict(self.r0.capacity())
        c.update(dies=len(caps), fits=all(x["fits"] for x in caps.values()),
                 fits_slice=all(x["fits_slice"] for x in caps.values()),
                 worst_mirror=dict(rank=worst_m, words=caps[worst_m]["mirror_words"]),
                 worst_local=dict(rank=worst_l, words=max(caps[worst_l]["local_words"])),
                 note="local_words / mirror_words = rank 0 (the exported die); fits = every die")
        return c

    def table(self):
        t = self.r0.table()
        t["per_die"] = "rank 0 shown; every die has its own map (SPMD rank-dependent bases)"
        return t

    def slice_image(self, vm, q, live=None):
        return self.r0.slice_image(vm, q, live)

    def spec_image(self, vm, live=None):
        return self.r0.spec_image(vm, live)

    def save(self, f):
        rks = sorted(self.by_rank)
        P = [self.by_rank[r] for r in rks]
        ex = json.dumps(dict(ext=[{str(k): v for k, v in p.use.items()} for p in P],
                             peak=[{str(k): v for k, v in p.peak.items()} for p in P], proof=getattr(self, "proof", [])))
        np.savez_compressed(f, ranks=np.array(rks), cls=np.stack([p.cls for p in P]), phys=np.stack([p.phys for p in P]),
                            live_in=np.stack([p.live_in for p in P]), live_out=np.stack([p.live_out for p in P]),
                            extra=np.array(ex))

    @staticmethod
    def load(f):
        z = np.load(f)
        if "phys" not in z:
            return PlacementSet({int(r): Placement(c) for r, c in zip(z["ranks"], z["cls"])})
        ex = json.loads(str(z["extra"]))
        dk = lambda d: {int(k): v for k, v in d.items()}   # noqa: E731
        ps = PlacementSet({int(r): Placement(c, ph, dk(e), dk(pk), li, lo) for r, c, ph, li, lo, e, pk in
                           zip(z["ranks"], z["cls"], z["phys"], z["live_in"], z["live_out"], ex["ext"], ex["peak"])})
        ps.proof = ex["proof"]
        return ps


def packed(cls):
    """every class's words packed in logical order (no reuse): the layout the affine check was written against"""
    pp = np.full(VMW, -1, np.int64)
    for c in range(NQ + 1):
        w = np.nonzero(cls == c)[0]
        pp[w] = np.arange(len(w))
    return pp


def allocate(cls, subs, s_w, e_w):
    """LIVENESS-based physical allocation per region (local q, mirror).  Blocks: the packed layout's intervals covered
    by one cluster sub-descriptor are merged (a block moves as a whole, a translation, so every per-cluster descriptor
    stays 2-D affine); words no descriptor covers (central-only) form runs of equal lifetime.  A block lives
    [min start, max end] on the record clock (start -1 = live-in, end int32 max = live-out); blocks whose lifetimes
    are disjoint share physical words (first fit by offset, in start order).  Returns (phys, extent per class,
    peak live words per class)."""
    pp = packed(cls)
    phys = np.full(VMW, -1, np.int64)
    ext, peak = {}, {}
    END = np.iinfo(np.int32).max
    for c in range(NQ + 1):
        w = np.nonzero(cls == c)[0]
        n = w.size
        ext[c] = peak[c] = 0
        if not n:
            continue
        cov = np.zeros(n + 1, np.int64)              # interval cover on the packed axis (difference array)
        for b, nn, m, st, ist in subs:
            la = ga(b, st, ist, range(m), range(nn))
            la = la[(la >= 0) & (la < VMW)]
            if not la.size or cls[la[0]] != c:
                continue
            lo, hi = int(pp[la].min()), int(pp[la].max())
            if hi > lo:
                cov[lo + 1] += 1                     # words lo+1..hi continue lo's block
                cov[hi + 1] -= 1
        join = np.cumsum(cov)[:n] > 0
        sw, ew = s_w[w], e_w[w]
        diff = np.ones(n, bool)
        diff[1:] = (sw[1:] != sw[:-1]) | (ew[1:] != ew[:-1])
        newblk = ~join & diff                        # an uncovered word continues a run of equal lifetime
        newblk[0] = True
        bid = np.cumsum(newblk) - 1
        nb = int(bid[-1]) + 1
        bs = np.full(nb, np.iinfo(np.int64).max, np.int64)
        be = np.full(nb, np.iinfo(np.int64).min, np.int64)
        np.minimum.at(bs, bid, sw)
        np.maximum.at(be, bid, ew)
        blo = np.nonzero(newblk)[0]
        bsz = np.diff(np.concatenate([blo, [n]]))
        best = None                                  # first fit in several orders; keep the smallest extent
        for key in (lambda i: (bs[i], -bsz[i]), lambda i: (-bsz[i], bs[i]),
                    lambda i: (-(min(be[i], 1 << 40) - bs[i]) * bsz[i], bs[i]), lambda i: (-be[i], -bsz[i])):
            placed = []                              # (off, size, start, end)
            off_of = np.zeros(nb, np.int64)
            for i in sorted(range(nb), key=key):
                s0, e0, z = bs[i], be[i], int(bsz[i])
                busy = sorted((o, o + zz) for o, zz, ss, ee in placed if not (ee < s0 or e0 < ss))
                off = 0
                for o, oe in busy:
                    if off + z <= o:
                        break
                    off = max(off, oe)
                placed.append((off, z, s0, e0))
                off_of[i] = off
            x = max(o + z for o, z, _, _ in placed)
            if best is None or x < best[0]:
                best = (x, placed, off_of)
        _, placed, off_of = best
        phys[w] = (LOCAL_W if c == MIR else 0) + off_of[bid] + (np.arange(n) - blo[bid])
        ext[c] = int(max(o + z for o, z, _, _ in placed))
        ev = [(int(ss), z) for _, z, ss, _ in placed] + [(int(ee) + 1 if ee < END else 1 << 62, -z)
                                                          for _, z, _, ee in placed]
        cur = 0
        for _, dz in sorted(ev):
            cur += dz
            peak[c] = max(peak[c], cur)
    return phys, ext, peak


class Placement:
    def __init__(self, cls, phys=None, ext=None, peak=None, live_in=None, live_out=None):
        self.cls = cls
        if phys is None:                             # no liveness: packed, no reuse
            phys = packed(cls) + np.where(cls == MIR, LOCAL_W, 0)
            phys[cls < 0] = -1
            ext = {c: int(np.sum(cls == c)) for c in range(NQ + 1)}
        self.phys = phys
        self.use = ext
        self.peak = peak or ext
        self.words = {c: int(np.sum(cls == c)) for c in range(NQ + 1)}
        self.live_in = live_in if live_in is not None else cls >= 0
        self.live_out = live_out if live_out is not None else cls >= 0
        segs = []
        t = np.nonzero(cls >= 0)[0]
        if len(t):
            brk = np.nonzero((np.diff(t) != 1) | (np.diff(cls[t]) != 0) | (np.diff(phys[t]) != 1))[0]
            starts = np.concatenate([[0], brk + 1])
            ends = np.concatenate([brk + 1, [len(t)]])
            for s0, e0 in zip(starts, ends):
                lo = int(t[s0])
                c, ph = int(cls[lo]), int(self.phys[lo])
                segs.append([lo, int(e0 - s0), c, ph, spec_addr(c, ph)])
        self.segs = segs

    def capacity(self):
        loc = [self.use[q] for q in range(NQ)]
        return dict(local_words=loc, mirror_words=self.use[MIR], local_cap=LOCAL_W, mirror_cap=MIRROR_W,
                    allocation="liveness (record clock; blocks keep every cluster descriptor affine)",
                    logical_local_words=[self.words[q] for q in range(NQ)], logical_mirror_words=self.words[MIR],
                    peak_live_local=[self.peak[q] for q in range(NQ)], peak_live_mirror=self.peak[MIR],
                    slice_words=[x + self.use[MIR] for x in loc], slice_cap=SLICE_W,
                    fits=bool(max(loc) <= LOCAL_W and self.use[MIR] <= MIRROR_W),
                    fits_slice=bool(max(loc) + self.use[MIR] <= SLICE_W), segments=len(self.segs))

    def table(self):
        return dict(schema="opentallas.hgi_b2.placement.v1", nq=NQ, vm_words=VMW, local_w=LOCAL_W, mirror_w=MIRROR_W,
                    mirror_phys_base=LOCAL_W, cls_codes={"0..3": "LOCAL slice q", "4": "MIRROR (every slice)"},
                    segments_fields=["logical_lo", "len", "cls", "phys_lo", "spec_addr_lo"],
                    spec="results/arch/hbm_b2_1012/SPEC.md v0.5: range decode; slice = addr[17:16] below REPL_BASE",
                    repl_base=REPL_BASE, repl_w=REPL_W, hcap_base=HCAP_BASE, hcap_w=HCAP_W, spec_words=SPEC_WORDS, segments=self.segs,
                    capacity=self.capacity())

    def slice_image(self, vm, q, live=None):
        """live: the words resident at that moment (live_in for the entry image, live_out for the final one); aliased
        words share a physical word, so only the resident one is written"""
        live = self.cls >= 0 if live is None else live
        img = np.zeros(SLICE_W, np.uint32)
        for c in (q, MIR):
            w = np.nonzero((self.cls == c) & live)[0]
            img[self.phys[w]] = vm[w]
        return img

    def spec_image(self, vm, live=None):
        """the whole die VM in SPEC.md v0.5 addresses (SPEC_WORDS = 360,448): slice q LOCAL at q * LOCAL_W + phys, the
        REPL window (one copy; every slice's mirror holds it) at REPL_BASE + phys - LOCAL_W, and the HC weight aperture
        (logical [VM_WORDS, VM_WORDS + VM_AP) when the image carries it) relocated to HCAP_BASE"""
        img = np.zeros(SPEC_WORDS, np.uint32)
        w = np.nonzero((self.cls >= 0) & (self.cls >= 0 if live is None else live))[0]
        img[[spec_addr(int(c), int(p)) for c, p in zip(self.cls[w], self.phys[w])]] = vm[w]
        ap = vm[VMW:VMW + HCAP_W]
        img[HCAP_BASE:HCAP_BASE + ap.size] = ap
        return img

    def avail(self, q):
        return (self.cls == q) | (self.cls == MIR)


def spec_addr(c, ph):
    """SPEC.md v0.5 word address of physical word ph of region c: slice q (q * LOCAL_W + ph); the REPL window (mirror)
    at REPL_BASE + (ph - LOCAL_W)"""
    return REPL_BASE + ph - LOCAL_W if c == MIR else c * LOCAL_W + ph


def spec_of_logical_aperture(a):
    """an HC-aperture logical address (simulator [VM_WORDS, VM_WORDS + VM_AP)) -> its SPEC v0.5 address"""
    assert VMW <= a < VMW + HCAP_W
    return HCAP_BASE + (a - VMW)


def decode(addr):
    """SPEC v0.5 range decode -> ("slice", q, offset) | ("repl", offset) | ("hcap", offset); a hole faults"""
    if 0 <= addr < REPL_BASE:
        return ("slice", addr >> 16 & 3, addr & 0xFFFF)
    if REPL_BASE <= addr < REPL_BASE + REPL_W:
        return ("repl", addr - REPL_BASE)
    if HCAP_BASE <= addr < HCAP_BASE + HCAP_W:
        return ("hcap", addr - HCAP_BASE)
    raise ValueError(f"SPEC v0.5 address {addr} decodes to no region (fault)")


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

    def __init__(self, pl, die0, seed=12, refuse=True, mutant=None):
        """mutant (the check's own teeth; each must FAIL): stale_mirror = a cluster sees no mirror copy (the
        mirror-write broadcast / collective broadcast never arrived); chain_naive = per-cluster csums combined by a
        pairwise tree instead of the carried golden counter state."""
        self.pls = pl if isinstance(pl, PlacementSet) else PlacementSet({0: pl})
        self.die0, self.refuse, self.mutant = die0, refuse, mutant
        self.rng = np.random.default_rng(seed)
        self._av = {}
        self._use(0)
        self.viol = []
        self.stats = Counter()
        self.ring = Counter()
        self.recs = []              # rank 0, one per executed dispatched record (Capture order)
        self.hbm_q = np.zeros(NQ, np.int64)
        self.P = ring_params()

    def _use(self, rank):
        """switch to this die's placement"""
        self.pl = self.pls.of(rank)
        k = id(self.pl)
        if k not in self._av:
            self._av[k] = [self.pl.avail(q) for q in range(NQ)]
        self.avail = self._av[k]

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
                                   phys=[af[0], int(n), int(m), af[1], af[2]],
                                   spec=[int(spec_addr(region, af[0])), int(n), int(m), af[1], af[2]])
        return out

    def wrap(self, key, fn):
        def run(M, r, L):
            dies, cur = M.dies, M.cur
            hook_prev = MC.RED_HOOK
            try:
                if central(M, M.rec_of(dies[0], r), dies[0], L):
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
            self._use(0)
            M.dies, M.cur = [die], M.rec_of(die, r)
            gq = MS.group_cluster(M.cur)
            if gq is not None:
                self._native(M, M.cur, die, L, gq)
                continue
            rd = wr = 0
            ops = []
            for nm, d in M.cur.desc.items():
                if d.space != "VM":
                    continue
                try:
                    a = M.vm_addrs(d, die, L)
                except MC.Fault:
                    continue
                a = a[(a >= 0) & (a < VMW)]
                ops.append((nm in (("O", "R") if r.unit == "SU" else ("O", "R", "D")), self.pl.cls[a]))
            allc = np.concatenate([c for _, c in ops]) if ops else np.zeros(0, np.int8)
            v = np.bincount(allc[(allc >= 0) & (allc < NQ)].astype(np.int64), minlength=NQ)
            home = VEC_HOME if r.unit in SPLIT_UNITS else (int(np.argmax(v)) if v.any() else VEC_HOME)
            wq = sorted(set(int(x) for w_, c in ops if w_ for x in c[(c >= 0) & (c < NQ)]))
            nmir = sum(int(np.sum(c == MIR)) for w_, c in ops if w_)
            if r.unit == "DMA" and r.op == "LOAD" and (len(wq) > 1 or nmir):
                # SPEC 1 DMA: the loader is per quadrant (lq_<q> ends at slice q): each cluster's loader writes its
                # own slice's words, and a REPL word is loaded by every quadrant from its own stack (the constant is
                # replicated per stack: a few KB a layer), so neither is a ring write nor a mirror broadcast
                self.ring["dma_repl_load"] += nmir
                self.recs.append(dict(unit=r.unit, op=r.op, tag=getattr(M.cur, "tag", ""), L=int(L), mode="QSPLIT",
                                      cluster=list(range(NQ)) if nmir else wq, ring_read=0, ring_write=0,
                                      mirror_write=0, repl_load=nmir, **self._cycles(Counter(), 0, 0)))
                continue
            pair, bc = Counter(), 0
            for is_w, c in ops:
                for q in range(NQ):
                    n = int(np.sum(c == q))
                    if q != home and n:
                        pair[(home, q) if is_w else (q, home)] += n
                if is_w:
                    bc += int(np.sum(c == MIR))
                    wr += int(np.sum((c >= 0) & (c != home)))
                else:
                    rd += int(np.sum((c >= 0) & (c < NQ) & (c != home)))
            cyc = self._cycles(pair, bc, 0)
            self.ring["central_remote_read"] += rd
            self.ring["central_remote_write"] += wr
            self.ring["central_mirror_write"] += bc
            self.recs.append(dict(unit=r.unit, op=r.op, tag=getattr(M.cur, "tag", ""), L=int(L),
                                  mode="HOME" if r.unit in SPLIT_UNITS else "CENTRAL",
                                  cluster=home, ring_read=rd, ring_write=wr, mirror_write=bc, **cyc))

    def _native(self, M, r, die, L, q):
        """a native dispatch-group member: every VM word in cluster q's slice (LOCAL q or MIRROR), one affine physical
        descriptor in one region; no ring word.  A LOAD into MIRROR words is the mirror-write broadcast of that
        cluster's part (the other three slices' copies), as for any mirror write."""
        tag = f"{r.unit}.{r.op}[{getattr(r, 'tag', '')}]@L{L}"
        sub, bc = {}, 0
        for nm, d in r.desc.items():
            if d.space != "VM":
                continue
            b, n, m, st, ist = (int(x) for x in M.eff(d, die, L))
            la = ga(b, st, ist, range(m), range(n))
            if la.min() < 0 or la.max() >= VMW:
                self.fail(f"rank {die.rank} {tag} {nm}: native group operand outside the VM")
                continue
            cl, ph = self.pl.cls[la], self.pl.phys[la]
            if not np.all(self.avail[q][la]):
                self.fail(f"rank {die.rank} {tag} {nm}: native member of cluster {q} touches "
                          f"{int((~self.avail[q][la]).sum())} words outside slice {q} / mirror")
                continue
            af = affine(ph, m, n)
            region = int(cl[0])
            if af is None or not np.all(cl == region):
                self.fail(f"rank {die.rank} {tag} {nm}: cluster {q} native operand not affine in slice space")
                continue
            if nm == "O":
                bc += int(np.sum(cl == MIR))
            sub[f"{nm}{q}"] = dict(logical=[b, n, m, st, ist], region=region, phys=[af[0], n, m, af[1], af[2]],
                                   spec=[int(spec_addr(region, af[0])), n, m, af[1], af[2]])
        self.ring["native_group_words"] += sum(v["logical"][1] * v["logical"][2] for v in sub.values())
        self.ring["central_mirror_write"] += bc
        self.recs.append(dict(unit=r.unit, op=r.op, tag=getattr(r, "tag", ""), L=int(L), mode="NATIVE", cluster=q,
                              group_last=bool(r.param & MS.GLAST), sub=sub, ring_read=0, ring_write=0,
                              mirror_write=bc, **self._cycles(Counter(), bc, 0)))

    def _cycles(self, pair, bcast, chain_hop):
        """the harness's per-record cost: ring = slowest (src, dst) pair, broadcast tree, plus the chained-reduction
        state carried cluster 0 -> 1 -> 2 -> 3 (NQ - 1 sequential one-hop transfers)"""
        P = self.P
        wpl, wpb, hc = P["ring_link_bits"] // 32, P["bcast_bits"] // 32, P["ring_hop_cycles"]
        ring = max((hc * _hops(s_, d_) + -(-w // wpl) for (s_, d_), w in pair.items() if w), default=0)
        bc = (hc * P["bcast_hops"] + -(-bcast // wpb)) if bcast else 0
        ch = (NQ - 1) * (hc + -(-chain_hop // wpl)) if chain_hop else 0
        return dict(ring_cycles=int(ring), bcast_cycles=int(bc), chain_cycles=int(ch), cycles=int(ring + bc + ch))

    def _one(self, M, r, die, L, fn):
        rank = die.rank
        self._use(rank)
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
                if role == "out" and kind == "grid" and s.mode != "REPLX":   # REPLX: every cluster writes its own copy
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
            cyc = self._cycles({}, mb // (NQ - 1), hop)
            self.recs.append(dict(unit=r.unit, op=r.op, tag=getattr(r, "tag", ""), L=int(L), mode=s.mode,
                                  cluster=[q for q in range(NQ) if work.get(q, 0)] or [0],
                                  chain=s.chain, grid=list(map(int, s.grid)), work=work, sub=sub,
                                  mirror_broadcast=mb, chain_hop_words=hop, **cyc))

    def ring_report(self, model):
        """measured exposed ring cycles per layer (sum over the rank-0 records, the harness's convention) vs budget"""
        per_l = defaultdict(lambda: dict(cycles=0, ring=0, bcast=0, chain=0, records=0))
        by = defaultdict(lambda: dict(records=0, cycles=0))
        for e in self.recs:
            x = per_l[e["L"]]
            x["cycles"] += e["cycles"]
            x["ring"] += e["ring_cycles"]
            x["bcast"] += e["bcast_cycles"]
            x["chain"] += e["chain_cycles"]
            x["records"] += 1
            b = by[f"{e['unit']}.{e['op']}"]
            b["records"] += 1
            b["cycles"] += e["cycles"]
        key = "qwen" if "qwen" in str(model).lower() else "ds"
        bud = self.P["budget_cycles_per_layer"][key]
        lay = {int(k): v for k, v in sorted(per_l.items()) if k >= 0} or {int(k): v for k, v in per_l.items()}
        return dict(params_source=self.P["source"], budget_cycles_per_layer=bud, per_layer=lay,
                    max_layer_cycles=max((v["cycles"] for v in lay.values()), default=0),
                    within_budget=all(v["cycles"] <= bud for v in lay.values()),
                    by_op=dict(sorted(by.items(), key=lambda kv: -kv[1]["cycles"])[:12]))

    def finish(self):
        return dict(violations=len(self.viol), first_violations=self.viol[:40], stats=dict(self.stats),
                    ring_words=dict(self.ring), hbm_weight_bytes_per_cluster=[int(x) for x in self.hbm_q])


def write(out, pl, chk, collect, vm0, vm_final, meta_extra):
    out.mkdir(parents=True, exist_ok=True)
    cap = pl.capacity()
    for q in range(NQ if cap["fits"] else 0):   # an over-capacity placement has no slice image: refused below
        (out / f"vm0_s{q}.bin").write_bytes(pl.slice_image(vm0, q, pl.r0.live_in).astype("<u4").tobytes())
        (out / f"vm_final_s{q}.bin").write_bytes(pl.slice_image(vm_final, q, pl.r0.live_out).astype("<u4").tobytes())
    if cap["fits"]:                             # SPEC 2a die image: what the native die TB / cmdproc address map loads
        (out / "vm0_spec.bin").write_bytes(pl.spec_image(vm0, pl.r0.live_in).astype("<u4").tobytes())
        (out / "vm_final_spec.bin").write_bytes(pl.spec_image(vm_final, pl.r0.live_out).astype("<u4").tobytes())
    (out / "placement.json").write_text(json.dumps(pl.table(), default=int) + "\n")
    sl = np.where(pl.cls == MIR, -1, np.where(pl.cls < 0, -2, pl.cls)).astype(np.int8)
    np.save(out / "slice.npy", sl)          # per logical VM word: slice 0..3, -1 = mirror, -2 = untouched
    (out / "records_b2.json").write_text(json.dumps(chk.recs, default=int) + "\n")
    v = chk.finish()
    for msg in getattr(pl, "proof", []) or []:   # rank 0 alias proof (pass 1): physical reuse must not change a value
        v["violations"] += 1
        v["first_violations"].insert(0, msg)
    if not cap["fits"]:
        v["violations"] += 1
        v["first_violations"].insert(0, f"capacity: local {cap['local_words']} / {LOCAL_W}, mirror {cap['mirror_words']} / "
                                        f"{MIRROR_W} on rank 0; worst die mirror {cap.get('worst_mirror')}, local {cap.get('worst_local')}")
    split_work = defaultdict(lambda: [0] * NQ)
    for e in chk.recs:
        for q, w in (e.get("work") or {}).items():
            split_work[e["unit"]][int(q)] += w
    verdict = dict(schema="opentallas.hgi_b2.verdict.v1", **meta_extra, capacity=cap,
                   modes={f"{k[0]}:{k[1]}": n for k, n in sorted(collect.modes.items())},
                   work_per_cluster=dict(split_work), ring_cycles=chk.ring_report(meta_extra.get("model")), **v,
                   exact=bool(v["violations"] == 0))
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=int) + "\n")
    return verdict
