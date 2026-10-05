#!/usr/bin/env python3
"""OPERATOR-FUSION BUILD of tools/hdc_program_v41.py (W11; tools/w11_su_fuse.py, AGENTS.md dataflow level 1).

    HDC_V41_SU_FUSE=N,M,depth python3 tools/hdc_program_v41_fuse.py [hdc_program_v41.py's arguments]

hdc_program_v41.py (pinned by committed records) is unchanged; this module extends it in-process:
* the ISA gets the fusion fields (tools/hdc_isa_v41_fuse.install: appended, no existing offset moves);
* Builder.build runs the chain-forming pass (w11_su_fuse.fuse) over the builder's entries BEFORE scheduling, for
  a vector unit of N light / M SFU lanes with `depth` lane registers (HDC_V41_SU_FUSE; unset: no pass, the
  program is the original's);
* schedule() lets a lane-register consumer of the previous stream op chase it vector by vector (su_chase = 1)
  instead of draining the stream unit (the fused unit's adapter, ot_hdc_v41x_su_adapt_kr.sv, chases such a
  consumer per vector; its KR credit requires every older op landed);
* Machine.su1 keeps the lane registers exactly as the unit does (indexed by (vector, lane) of the unit's
  placement), so a compiler error -- an overlapping range, a misplaced element -- shows as a wrong value.
Everything else (images, the ISA model's check against the golden) is hdc_program_v41's own.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdc_isa_v41_fuse as IF   # noqa: E402

IF.install()
import hdc_program_v41 as P     # noqa: E402
from hdc_program_v41 import *   # noqa: E402,F401,F403  (the copied functions below use its names)
from hdc_program_v41 import CHASE  # noqa: E402

FUSE_ENV = "HDC_V41_SU_FUSE"
FUSE_POSITIONS = (0, 1, 2, 3, 7, 8, 15, 16, 17, 31, 32, 33, 63, 64, 65, 127)
_lay = [None]                   # the layout of the Builder being built


def fuse_geom():
    v = os.environ.get(FUSE_ENV, "")
    if not v:
        return None
    N, M, d = (int(x) for x in v.split(","))
    return N, M, d


def fuse_entries(entries, lay, geom=None):
    """The fusion pass over the builder's (f, reads, writes, tag) entries.  Region read / write sets are unchanged
    (a value kept in lane registers still counts as its region)."""
    geom = geom or fuse_geom()
    if not geom or lay is None or lay.mtp:
        return entries
    import w11_su_fuse as FU
    N, M, d = geom
    Ds = [(lambda dv: (lambda sel: dv[sel]))(I.dyn_values(0, p)) for p in FUSE_POSITIONS]
    out, rep_ = FU.fuse(entries, Ds, N, M, FU.Regions(lay.vm.map), depth=d, lw=True)
    fuse_entries.report = rep_
    return out


_orig_build = P.Builder.build


def build(self, *a, **kw):
    _lay[0] = self.lay
    try:
        return _orig_build(self, *a, **kw)
    finally:
        _lay[0] = None


def schedule(prog, chain=False):
    """hdc_program_v41.schedule with the fusion pass first (fuse_entries) and a lane-register consumer of the previous
    stream op chased per vector; its original docstring follows."""
    prog = fuse_entries(prog, _lay[0]) if not chain else prog
    """Wait masks: an instruction waits for every unit holding an in-flight
    instruction it conflicts with.  On ANOTHER unit a conflict is any overlap (it
    reads what that unit writes, or writes what it reads or writes).  On its OWN
    unit only a read of what the unit writes conflicts: a unit starts an op after
    the previous op's last element has been read, and writes in issue order --
    the stream unit because a class change drains it and a class fixes the depth
    (its reducer writes later, so a write over a reducer's output still waits),
    the matrix engine when consecutive ops share the split and weight source
    (the result latency).  A unit executes in order, so waiting for it to drain
    covers all its older work.  The quantised engine and the auxiliary unit are
    SEQUENTIAL (an op is accepted only once the previous one has written
    everything), so once an op that is never skipped has issued on one of them,
    every older op there is complete: its conflicts are forgotten.

    chain=True (the MTP programs): a stream op of another CLASS than the
    previous one is accepted only once the unit has drained (ot_hdc_v41_stream
    `ready`), so element writes before a class change are never waited on;
    within a same-class run a read of an earlier op's writes CHASES the whole
    run (chain_distance) when every writer involved is static -- the multi-slot
    programs place the slots' copies of an op side by side, so a slot's
    producer sits several ops back."""
    out = []
    su_chain, su_chain_w = [], []                   # same-class stream ops since the last drain / class change
    su_sig_w = {}                                   # stream-unit copy signature -> regions written since a drain
    rd = {u: set() for u in I.UNITS}
    wr = {u: set() for u in I.UNITS}
    rw = {u: set() for u in I.UNITS}              # reducer outputs (stream unit)
    last = {}
    last_su = None                                  # the previous stream op (chase source)
    sequential = (I.UNIT_QE, I.UNIT_XU)
    for f, reads, writes, tag in prog:
        f = dict(f)
        wait = f.get("wait", 0)
        own = f["unit"]
        red = set(f.pop("_redw", ()))
        chase = 0
        cls_change = own == I.UNIT_SU and last_su is not None and su_class(f) != su_class(last_su)
        if chain and cls_change:
            su_chain, su_chain_w = [], []
        for u in I.UNITS:
            if u == own:
                c = reads & wr[u]
                if u == I.UNIT_SU and c and f.get("kr_r", 0) and last_su is not None and last_su.get("kr_w", 0) \
                        and last_su.get("kr_wb", 0) == f.get("kr_rb", 0) and not (reads & rw[u]) and not chain \
                        and max(1, f.get("mx_m", 0)) == 1 and max(1, last_su.get("mx_m", 0)) == 1:
                    # operator fusion: a lane-register consumer of the previous stream op chases it vector by
                    # vector; the unit's KR credit requires every older op landed (its memory reads), and the
                    # pass never lets it read its KR producer through memory (ot_hdc_v41x_su_adapt kr_prev)
                    chase = 1
                    c = set()
                elif u == I.UNIT_SU and c and CHASE and chain:
                    if cls_change:
                        c = reads & rw[u]          # the element pipeline drains; a reducer may still write
                    elif not (reads & rw[u]):
                        live = reads & set().union(set(), *su_chain_w)
                        if not live:
                            c = set()              # its writers precede a drain or a class change
                        elif su_static(f):
                            relevant = [g for g, w in zip(su_chain, su_chain_w) if w & reads]
                            if all(su_static(g) for g, _ in relevant):
                                chase = chain_distance(su_chain, f)
                                c = set()
                elif u == I.UNIT_SU and c and CHASE and not (reads & rw[u]) and su_static(f) and last_su \
                        and su_static(last_su) and su_class(f) == su_class(last_su) and \
                        su_sig(f) == su_sig(last_su) and \
                        not (reads & set().union(set(), *(w for s, w in su_sig_w.items() if s != su_sig(f)))):
                    # a copy's chase counts only its own vectors: never across copies
                    chase = chase_distance(last_su, f)
                    c = set()                      # chase the previous stream op instead of draining
                if u == I.UNIT_SU:
                    c = c or (writes & rw[u])
                if u == I.UNIT_ME and last.get(u) != (f.get("me_split", 0), f.get("me_wsrc", 0)):
                    c = c or (writes & wr[u])
            else:
                c = (reads & wr[u]) or (writes & (rd[u] | wr[u]))
            if c:
                wait |= 1 << (u - 1)
        for u in I.UNITS:
            if wait >> (u - 1) & 1:
                rd[u], wr[u], rw[u] = set(), set(), set()
        f["wait"] = wait
        if wait >> (I.UNIT_SU - 1) & 1:
            su_sig_w = {}
        if own == I.UNIT_SU:
            f["su_chase"] = chase if not (wait >> (I.UNIT_SU - 1) & 1) else 0
            last_su = f
            su_sig_w.setdefault(su_sig(f), set()).update(writes)
            if chain:
                if wait >> (I.UNIT_SU - 1) & 1:
                    su_chain, su_chain_w = [], []
                su_chain.append((f, su_nvec(f)))
                su_chain_w.append(set(writes))
        elif chain and wait >> (I.UNIT_SU - 1) & 1:
            su_chain, su_chain_w = [], []
        if own in sequential and never_skipped(f):
            rd[own], wr[own] = set(), set()
        if own in rd:
            rd[own] |= reads
            wr[own] |= writes
            rw[own] |= red
            if own == I.UNIT_ME:
                last[own] = (f.get("me_split", 0), f.get("me_wsrc", 0))
        f["_tag"] = tag
        out.append(f)
    return out


# -- ISA-level simulator ------------------------------------------------------------------


class _K:
    kr_geom = None

    def kr_place(self, f, no, ni):
        """(vector, lane) of each element of a fused op on the unit kr_geom: KR is indexed by them, exactly as
        the hardware is, so a compiler error (overlapping ranges, a misplaced element) shows as a wrong value."""
        import w11_su_fuse as FU
        if self.kr_geom is None and fuse_geom():
            self.kr_geom = fuse_geom()[:2]
        if self.kr_geom is None:
            raise ValueError("a fused stream op (kr_w / kr_r) needs Machine.kr_geom = (N, M) or HDC_V41_SU_FUSE")
        N, M = self.kr_geom
        if not hasattr(self, "kr"):
            self.kr = np.full((IF.KR_DEPTH, N), np.nan, dtype=F)
        g = FU.bench_op(f, lambda sel: self.dyn[sel])
        g.update(nout=no, nin=ni)
        vec, lane, _ = FU.placement(g, N, M)
        return vec, lane

    def su1(self, f):
        d = self.dyn
        no = f["su_nout"] + d[f["su_d_nout"]]
        ni = f["su_nin"] + d[f["su_d_nin"]]
        if no == 0 or ni == 0:
            return
        idx = None
        if f["a_ind"]:
            cnt = ni if f["a_ind"] == I.IND_I else no
            idx = to_u32(self.vm[f["a_ibase"]:f["a_ibase"] + cnt]).astype(np.int64)
        ea = self.addr(f, "a", no, ni, idx)
        a = self.fetch(f, "a", ea)
        b = self.fetch(f, "b", self.addr(f, "b", no, ni))
        ec = ea ^ 1 if f["c_pair"] else self.addr(f, "c", no, ni)
        c = self.fetch(f, "c", ec)
        dd = self.fetch(f, "d", self.addr(f, "d", no, ni))
        krp = None
        if f.get("kr_r", 0) or f.get("kr_w", 0):
            krp = self.kr_place(f, no, ni)
            if f.get("kr_r", 0):
                kv_ = self.kr[f["kr_rb"] + krp[0], krp[1]]
                rk = f["kr_r"]
                a = kv_.copy() if rk & 1 else a
                b = kv_.copy() if rk & 2 else b
                c = kv_.copy() if rk & 4 else c
                dd = kv_.copy() if rk & 8 else dd
        imm1, imm2, imm3 = (u32f(f[k]) for k in ("imm1", "imm2", "imm3"))
        if f["a_rnd"]:
            a = G.to_bf16(a)
        if f["a_relu"]:
            a = np.maximum(a, F(0)).astype(F)
        if f["a_min"]:
            a = np.minimum(a, imm3).astype(F)
        if f["c_clip"]:
            c = np.clip(c, -imm3, imm3).astype(F)
        p = {I.M1_BYP: lambda: a, I.M1_AB: lambda: G.mul(a, b), I.M1_AA: lambda: G.mul(a, a),
             I.M1_AIMM: lambda: G.mul(a, imm1), I.M1_DIVB: lambda: V.div(a, b), I.M1_DIVIMM: lambda: V.div(a, imm1),
             I.M1_MAXB: lambda: np.maximum(a, b).astype(F)}[f["m1"]]()
        p = {I.M2_BYP: lambda: p, I.M2_C: lambda: G.mul(p, c), I.M2_IMM: lambda: G.mul(p, imm1)}[f["m2"]]()
        par = np.tile(np.arange(ni) & 1, no)
        qd = {I.QM_OFF: None, I.QM_POS: dd, I.QM_NEG: G.neg(dd),
              I.QM_ALT_NP: np.where(par == 0, G.neg(dd), dd).astype(F),
              I.QM_ALT_PN: np.where(par == 0, dd, G.neg(dd)).astype(F)}[f["qm"]]
        q = None if qd is None else G.mul(c, qd)
        r = {I.AD_BYP: lambda: p, I.AD_Q: lambda: G.add(p, q), I.AD_C: lambda: G.add(p, c),
             I.AD_NEGB: lambda: G.add(p, G.neg(b)), I.AD_IMM: lambda: G.add(p, imm2),
             I.AD_D: lambda: G.add(p, dd)}[f["ad"]]()

        def egate(x):
            mag = V.sqrt(np.maximum(np.abs(x), F(1e-6)).astype(F))
            return V.sigmoid(np.where(x < 0, G.neg(mag), mag).astype(F))

        s = {I.SFU_NONE: lambda: r, I.SFU_EXP: lambda: G.exp(r), I.SFU_RSQRT: lambda: G.rsqrt(r),
             I.SFU_SQRT: lambda: V.sqrt(r), I.SFU_SIGM: lambda: V.sigmoid(r), I.SFU_SILU: lambda: V.silu(r),
             I.SFU_SPSQRT: lambda: V.sqrt(V.softplus(r)), I.SFU_EGATE: lambda: egate(r)}[f["sfu"]]()
        t = {I.E1_BYP: lambda: s, I.E1_MULC: lambda: G.mul(s, c), I.E1_ADDC: lambda: G.add(s, c),
             I.E1_MULIMM: lambda: G.mul(s, imm2), I.E1_ADDIMM: lambda: G.add(s, imm2)}[f["e1"]]()
        u = {I.E2_BYP: lambda: t, I.E2_MULB: lambda: G.mul(t, b), I.E2_MULIMM: lambda: G.mul(t, imm1)}[f["e2"]]()
        out = np.asarray(u, dtype=F).reshape(-1)
        if f["rnd"]:
            out = G.to_bf16(out)
        if f["red"] and f["red_tree"]:
            v = G.mul(out, out) if f["red_sq"] else out
            x = V.csum(v) if V.chunked("su") else \
                V.split_sum_parts([G.reduce_sum(sg) for sg in v.reshape(no, ni)])
            if f["red_rnd"]:
                x = G.to_bf16(x)
            self.vm[f["r_base"]] = x
        elif f["red"]:
            v = G.mul(out, out) if f["red_sq"] else out
            segs = v.reshape(1, -1) if f["red_whole"] else v.reshape(no, ni)
            vals = []
            for sg in segs:
                if f["red"] == I.RED_SUM:
                    vals.append(V.csum(sg) if V.chunked("idx" if "indexer" in f.get("_tag", "") else "su")
                                else G.reduce_sum(sg))
                elif f["red"] == I.RED_MAX:
                    vals.append(np.max(sg))
                else:
                    acc = F(0)
                    for x in sg:
                        acc = G.add(acc, x)
                    vals.append(acc)
            vals = np.asarray(vals, dtype=F)
            if f["red_rnd"]:
                vals = G.to_bf16(vals)
            for k, x in enumerate(vals):
                self.vm[f["r_base"] + k * f["r_so"]] = x
        if f.get("kr_w", 0):
            self.kr[f["kr_wb"] + krp[0], krp[1]] = out
        if f["dst"]:
            if f["dst"] == I.DST_KVT:
                o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
                row = self.dyn[f["o_d"]] + o
                ed = (f["o_base"] + (row >> 4) * (HD * W) + i * W + (row & 15)).reshape(-1)
            else:
                ed = self.addr(f, "o", no, ni)
            if f["dst"] == I.DST_VM:
                self.vm[ed] = out
            else:
                self.kv[ed] = G.to_bf16(out)

    # -- quantised engine ----------------------------------------------------------------------


P.schedule = schedule
P.Builder.build = build
P.Machine.kr_geom = None
P.Machine.kr_place = _K.kr_place
P.Machine.su1 = _K.su1
P.fuse_entries, P.fuse_geom = fuse_entries, fuse_geom


if __name__ == "__main__":
    sys.exit(P.main())
