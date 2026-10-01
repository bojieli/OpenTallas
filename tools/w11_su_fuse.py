#!/usr/bin/env python3
"""SU OPERATOR FUSION (W11; AGENTS.md "Operator fusion", user decision 2026-10-01): dependent stream-unit ops
chain through LANE REGISTERS instead of a vector-memory round trip.

MECHANISM.  Every lane of ot_hdc_v41x_vec holds a lane register file (KR, `KR_DEPTH` 32-bit entries).  An op
whose element results feed a later op element for element writes them, besides (or instead of) the vector
memory, into its lanes' KR at entry `kr_wb + v` (v: the op's vector index; each lane holds one element of a
vector).  A consumer op reads stream X (A, B, C, D: bit of `kr_r`) from KR entry `kr_rb + v` in place of the
vector memory.  Legal only when the two ops lay element e onto the SAME lane in the SAME vector (same layout:
counts, slot size, packing, vector width; no gather, no pair read, no half stream) -- checked here on the
unit's own layout (tools/rtl_hdc_v41x_vec_campaign.layout, the controller's mirror) at every position the
program can run at.  A reduction's scalar result is not an element stream: it stays a vector-memory result read
by the broadcast path, so reductions end a chain unless the next op takes only the scalar.

ISA (tools/hdc_isa_v41.py FUSE_FIELDS, appended after every existing field of both profiles, so no existing
offset moves):  kr_w (1) write the op's elements to KR at kr_wb (KR_AW bits);  kr_r (4: A, B, C, D) read those
streams from KR at kr_rb (KR_AW bits);  kr_lw (1) run the op at the SFU lanes' width (a light op inside a chain
with SFU ops: element e must sit on the same lane, and the SFU classes are M wide).  All zero: today's program.

THE PASS (`fuse`).  Over the scheduled program, in issue order:
  1. element-level def-use on the vector memory: every stream op's element reads and writes are exact (DYN
     resolved at each sampled position); other units' reads and writes are taken at region granularity;
  2. an edge P -> C on stream X when every element C reads on X was last written by P's element write, with the
     same (vector, lane) placement, the same predicate, no other writer in between, at every sampled position;
  3. write-back: P keeps its vector-memory write (dst VM) iff some read of what it wrote is not served by an
     edge (another unit, a broadcast / gathered / misaligned read, a cross-lane consumer, or live-out at the
     program's end); otherwise dst becomes NONE (the reduction, if any, still runs);
  4. KR allocation: P's value occupies nv(P) consecutive entries from P to its last consumer (first fit; a
     consumer that is its producer's last reader may write in place); a value that does not fit is not fused.
`fuse(..., on=False)` returns the program unchanged (the fallback).

Run:  python3 tools/w11_su_fuse.py [--shape shipped|reduced] [--out results/rtl/w11_su_fuse_stats.json]
"""
from __future__ import annotations

import argparse
import bisect
import collections
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I                           # noqa: E402
import rtl_hdc_v41x_vec_campaign as C             # noqa: E402

KR_DEPTH = I.KR_DEPTH
# C_rotate (tools/w11_vm_options.py price_C("rotate"), results/uarch/w11_vm_options.json on claude/w11-crot):
# the operand read and the element write each cross 16 register stages between the central VM strip and a lane
ROT_READ, ROT_WRITE = 16, 16


# ---- fields -------------------------------------------------------------------------------------------------
def bench_op(f, D):
    """An ISA stream op with its DYN selections resolved by D(sel) -> the campaign's (bench) field dict."""
    d = lambda k: D(f.get(k, 0))                                     # noqa: E731
    g = C.op_defaults()
    g.update(nout=f.get("su_nout", 0) + d("su_d_nout"), nin=f.get("su_nin", 0) + d("su_d_nin"))
    for s in "abcd":
        g[f"{s}src"], g[f"{s}base"] = f.get(f"{s}_src", 0), f.get(f"{s}_base", 0) + d(f"{s}_d")
        g[f"{s}so"], g[f"{s}si"] = f.get(f"{s}_so", 0), f.get(f"{s}_si", 0)
    for a, b in (("aibase", "a_ibase"), ("aind", "a_ind"), ("bhalf", "b_half"), ("cpair", "c_pair"),
                 ("arnd", "a_rnd"), ("arelu", "a_relu"), ("amin", "a_min"), ("cclip", "c_clip"), ("m1", "m1"),
                 ("m2", "m2"), ("qm", "qm"), ("ad", "ad"), ("sfu", "sfu"), ("e1", "e1"), ("e2", "e2"),
                 ("rnd", "rnd"), ("dst", "dst"), ("oso", "o_so"), ("osi", "o_si"), ("red", "red"),
                 ("redsq", "red_sq"), ("redwhole", "red_whole"), ("redtree", "red_tree"),
                 ("redrnd", "red_rnd"), ("rbase", "r_base"), ("rso", "r_so"), ("imm1", "imm1"), ("imm2", "imm2"),
                 ("imm3", "imm3"), ("krw", "kr_w"), ("krwb", "kr_wb"), ("krr", "kr_r"), ("krrb", "kr_rb"),
                 ("krlw", "kr_lw")):
        g[a] = f.get(b, 0)
    if g["dst"] == I.DST_KVT:
        g.update(obase=f.get("o_base", 0), orow=d("o_d"))
    else:
        g.update(obase=f.get("o_base", 0) + d("o_d"))
    return g


def placement(g, N, M):
    """Per element (flattened o * ni + i of the op's own order): its vector index and lane.  The unit's layout
    (ot_hdc_v41x_vec set-up; tools/rtl_hdc_v41x_vec_campaign.layout), with the lane kept.  kr_lw: the SFU width."""
    lay = C.layout(g, N, M)
    no, ni = g["nout"], g["nin"]
    ls, nsh, packed = lay["ls"], lay["nsh"], lay["packed"]
    flat = lay["flat"]
    no_f, ni_f = (1, no * ni) if flat else (no, ni)
    S, nslot = 1 << ls, 1 << nsh
    use = 1 << (ls + nsh)
    vec = np.full(no * ni, -1, dtype=np.int64)
    lane = np.full(no * ni, -1, dtype=np.int64)
    o_v = i_v = 0
    v = 0
    lanes = np.arange(use)
    d_o, d_i = lanes >> ls, lanes & (S - 1)
    while True:
        oo, ii = o_v + d_o, i_v + d_i
        live = (oo < no_f) & (ii < ni_f)
        e = (ii[live] if flat else oo[live] * ni + ii[live])
        vec[e] = v
        lane[e] = lanes[live]
        wrap = packed or (i_v + S >= ni_f)
        last = wrap and (o_v + nslot >= no_f)
        v += 1
        if last:
            break
        if wrap:
            o_v, i_v = o_v + nslot, 0
        else:
            i_v += S
    assert (vec >= 0).all()
    return vec, lane, lay


def used_streams(g):
    """The operand streams the op's arithmetic consumes (the unit fetches all four; an unused one is ignored)."""
    u = {"a"}
    if g["m1"] in (I.M1_AB, I.M1_DIVB, I.M1_MAXB) or g["ad"] == I.AD_NEGB or g["e2"] == I.E2_MULB:
        u.add("b")
    if g["m2"] == I.M2_C or g["qm"] != I.QM_OFF or g["ad"] == I.AD_C or g["e1"] in (I.E1_MULC, I.E1_ADDC):
        u.add("c")
    if g["qm"] != I.QM_OFF or g["ad"] == I.AD_D:
        u.add("d")
    return u


def stream_addrs(g):
    """Exact vector-memory element addresses of the streams the op uses: {stream: array or None (not
    element-exact)}, output array or None."""
    no, ni = g["nout"], g["nin"]
    out = {}
    used = used_streams(g)
    for s in "abcd":
        if g[f"{s}src"] != I.SRC_VM or s not in used:
            continue
        if s == "a" and g["aind"]:
            out[s] = None
        elif s == "c" and g["cpair"]:
            out[s] = ("pair", C.addrs(g, "a", no, ni) ^ 1) if not g["aind"] else None
        else:
            out[s] = C.addrs(g, s, no, ni)
    w = C.out_addrs(g) if g["dst"] == I.DST_VM else None
    return out, w


def result_addrs(g):
    if not g["red"]:
        return np.zeros(0, dtype=np.int64)
    no = g["nout"]
    n = 1 if (g["redwhole"] or g["redtree"]) else no
    return g["rbase"] + np.arange(n, dtype=np.int64) * g["rso"]


# ---- the pass core: ISA-generic -----------------------------------------------------------------------------
# A backend turns each instruction into a View; the core sees only views.  W12b's Qwen SU (ot_hdc_vstream) uses
# the same core with its own backend.
class View:
    """What the pass reads of one instruction.  su: an element-wise unit op the pass may fuse; for one:
    n elements, nv vectors, vec / lane per element (the unit's placement), pred (an issue predicate that must
    match along an edge), streams {name: exact memory addresses per element, or None (gathered, pair, any read
    not element-exact: read at region granularity, never fused)}, out (element write addresses or None),
    res (other exact writes, e.g. reduction results), bad (the unit cannot run it: a legality fault).
    Any instruction: reads / writes (region names, for the units the pass does not see element by element)."""
    __slots__ = ("su", "skip", "n", "nv", "vw", "vec", "lane", "pred", "streams", "out", "res", "reads", "writes",
                 "tag", "bad", "nvs")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def analyse(views, regions):
    """Fusible edges {(P, C, stream): elements} over views in issue order; rejects counted by reason."""
    su = [k for k, v in enumerate(views) if v.su and not v.skip]
    parts = [np.zeros(0, dtype=np.int64)]
    for k in su:
        v = views[k]
        parts += [a for a in v.streams.values() if a is not None] + ([v.out] if v.out is not None else []) + [v.res]
    U = np.unique(np.concatenate(parts))
    ru = regions.ids(U)                               # region id of every address
    lwk = np.full(len(U), -1, dtype=np.int64)         # last element writer (op), -1 none / not an element write
    lwe = np.zeros(len(U), dtype=np.int64)
    blocked = {}                                      # region id -> last op writing it at region level
    edges, reject = {}, collections.Counter()
    src_of = {}                                       # (consumer, stream) -> producers whose writes it reads
    for k, v in enumerate(views):
        if not v.su:
            for r in v.writes:
                blocked[regions.id(r)] = k
            continue
        if v.skip:
            continue
        for s, a in v.streams.items():
            if a is None:
                reject["gather_pair_or_region_read"] += 1
                continue
            ix = np.searchsorted(U, a)
            pk = lwk[ix]
            if (pk < 0).all():
                continue
            src_of[(k, s)] = set(np.unique(pk[pk >= 0]).tolist())
            if (pk < 0).any():
                reject["partly_older_or_result"] += 1
                continue
            ks = np.unique(pk)
            if len(ks) != 1:
                reject["several_producers"] += 1
                continue
            p = int(ks[0])
            pv = views[p]
            rids = np.unique(ru[ix])
            if any(blocked.get(int(r), -1) > p for r in rids):
                reject["other_unit_wrote_between"] += 1
                continue
            if pv.pred != v.pred:
                reject["predicate"] += 1
                continue
            ep = lwe[ix]
            if not (np.array_equal(pv.vec[ep], v.vec) and np.array_equal(pv.lane[ep], v.lane)):
                reject["placement_same_width" if pv.vw == v.vw else "placement_width"] += 1
                continue
            edges[(p, k, s)] = len(a)
        if len(v.res):
            lwk[np.searchsorted(U, v.res)] = -1
        if v.out is not None:
            ix = np.searchsorted(U, v.out)
            lwk[ix] = k
            lwe[ix] = np.arange(len(v.out))
    # a KR consumer may read nothing of its KR producer through memory: its early credit leads the landing
    for (p, c, s) in list(edges):
        if any(p in src for (c2, s2), src in src_of.items() if c2 == c and (p, c, s2) not in edges):
            edges.pop((p, c, s))
            reject["producer_also_read_from_memory"] += 1
    return edges, reject


def write_backs(views, edges, regions):
    """Producers that must keep their memory write: some read of what they wrote is not served by an edge
    (another unit's region read, a non-element-exact read, a stream not fused), or it is live at the end."""
    su = [k for k, v in enumerate(views) if v.su and not v.skip]
    parts = [np.zeros(0, dtype=np.int64)]
    for k in su:
        v = views[k]
        parts += [a for a in v.streams.values() if a is not None] + ([v.out] if v.out is not None else []) + [v.res]
    U = np.unique(np.concatenate(parts))
    ru = regions.ids(U)
    pend = np.full(len(U), -1, dtype=np.int64)
    fused = collections.defaultdict(set)
    for (p, c, s) in edges:
        fused[c].add(s)
    need = set()

    def region_read(rid):
        m = (ru == rid) & (pend >= 0)
        need.update(np.unique(pend[m]).tolist())
    for k, v in enumerate(views):
        if not v.su or v.skip:
            for r in v.reads:
                region_read(regions.id(r))
            if not v.su:
                for r in v.writes:
                    pend[ru == regions.id(r)] = -1
            continue
        for s, a in v.streams.items():
            if s in fused[k]:
                continue
            if a is None:
                for r in v.reads:
                    region_read(regions.id(r))
                continue
            q = pend[np.searchsorted(U, a)]
            need.update(np.unique(q[q >= 0]).tolist())
        if len(v.res):
            pend[np.searchsorted(U, v.res)] = -1
        if v.out is not None:
            pend[np.searchsorted(U, v.out)] = k
    need.update(np.unique(pend[pend >= 0]).tolist())          # live out of the program
    return need


def allocate(views, edges, depth):
    """First-fit KR ranges over issue order.  A value lives from its producer to its last consumer; a consumer
    that is the last reader of its input may take the same entries (it reads entry b + v before it writes it).
    Returns ({"w": producer -> base, "r": consumer -> base, "peak": entries}, kept edges)."""
    cons = collections.defaultdict(set)
    for (p, c, s) in edges:
        cons[p].add(c)
    last = {p: max(cs) for p, cs in cons.items()}
    live, w = {}, {}
    peak = 0
    for k in range(len(views)):
        for p in [p for p, x in live.items() if x[2] < k]:
            live.pop(p)
        if k not in cons:
            continue
        nv = views[k].nv
        used = sorted((b, b + n) for q, (b, n, l) in live.items() if l != k)
        cand = 0
        for lo, hi in used:
            if cand + nv <= lo:
                break
            cand = max(cand, hi)
        if cand + nv <= depth:
            live[k] = (cand, nv, last[k])
            w[k] = cand
            peak = max(peak, max(b + n for b, n, _ in live.values()))
    kept = {e for e in edges if e[0] in w}
    r = {c: w[p] for (p, c, s) in kept}
    return dict(w=w, r=r, peak=peak), kept


def form_chains(views_per_pos, regions, depth):
    """The pass over views at every sampled position: edges legal at all of them (same vector counts), one KR
    producer per consumer, allocated; producers' write-backs.  Returns (edges, alloc, need, rejects)."""
    per = [analyse(vs, regions) for vs in views_per_pos]
    common = set(per[0][0])
    for e, _ in per[1:]:
        common &= set(e)
    common = {e for e in common if all(vs[e[0]].nv == views_per_pos[0][e[0]].nv and
                                       vs[e[1]].nv == views_per_pos[0][e[1]].nv for vs in views_per_pos)}
    byc = collections.defaultdict(set)
    for (p, c, s) in common:
        byc[c].add(p)
    # one KR read base per consumer: a consumer reading two producers keeps the older one in memory
    common = {e for e in common if e[0] == max(byc[e[1]])}
    alloc, kept = allocate(views_per_pos[0], common, depth)
    edges = {e: per[0][0][e] for e in kept}
    need = set()
    for vs in views_per_pos:
        need |= write_backs(vs, edges, regions)
    return edges, alloc, need, per[0][1]


# ---- the V4.1 backend ----------------------------------------------------------------------------------------
class Regions:
    def __init__(self, vmap):
        items = sorted(vmap.items(), key=lambda kv: kv[1])
        self.names = [n for n, _ in items]
        self.bases = np.array([b for _, b in items], dtype=np.int64)
        self.idx = {n: i for i, n in enumerate(self.names)}

    def id(self, name):
        return self.idx.get(name, -1 - (hash(name) & 0xFFFF))      # a region outside the VM (KV, ...)

    def ids(self, addrs):
        return np.searchsorted(self.bases, addrs, side="right") - 1


def v41_views(prog, D, N, M, lw_ops=frozenset()):
    out = []
    for k, (f, reads, writes, tag) in enumerate(prog):
        if f["unit"] != I.UNIT_SU or max(1, f.get("mx_m", 0)) > 1:
            out.append(View(su=False, reads=set(reads), writes=set(writes), tag=tag))
            continue
        g = bench_op(f, D)
        if g["nout"] == 0 or g["nin"] == 0:
            out.append(View(su=True, skip=True, reads=set(reads), writes=set(writes), tag=tag, nv=0))
            continue
        if k in lw_ops:
            g["krlw"] = 1
        vec, lane, lay = placement(g, N, M)
        sa, w = stream_addrs(g)
        streams = {s: (None if (a is None or isinstance(a, tuple)) else a) for s, a in sa.items()}
        out.append(View(su=True, skip=False, n=g["nout"] * g["nin"], nv=lay["nv"], vw=lay["vw"], vec=vec,
                        lane=lane, pred=f.get("pred", 0), streams=streams, out=w, res=result_addrs(g),
                        reads=set(reads), writes=set(writes), tag=tag, bad=lay["bad"]))
    return out


def bench_views(ops, N, M, lw_ops=frozenset()):
    """Views of bench ops (tools/rtl_hdc_v41x_vec_campaign field dicts, DYN already resolved): every op is a
    stream op over one memory region."""
    out = []
    for k, g in enumerate(ops):
        g = dict(g)
        if k in lw_ops:
            g["krlw"] = 1
        vec, lane, lay = placement(g, N, M)
        sa, w = stream_addrs(g)
        streams = {s: (None if (a is None or isinstance(a, tuple)) else a) for s, a in sa.items()}
        out.append(View(su=True, skip=False, n=g["nout"] * g["nin"], nv=lay["nv"], vw=lay["vw"], vec=vec,
                        lane=lane, pred=0, streams=streams, out=w, res=result_addrs(g), reads={"VM"},
                        writes={"VM"}, tag=f"op{k}", bad=lay["bad"]))
    return out


def fuse_bench(ops, N, M, depth=KR_DEPTH, lw=True):
    """The pass on a bench program (the campaign's fused programs).  Returns (fused ops, report)."""
    regions = Regions({"VM": 0})
    lw_ops = frozenset()
    if lw:
        vs = bench_views(ops, N, M)
        trial = frozenset(k for k, v in enumerate(vs) if v.vw == N and -(-v.n // M) - v.nv < ROT_READ + ROT_WRITE)
        e0, _ = analyse(vs, regions)
        e1, _ = analyse(bench_views(ops, N, M, trial), regions)
        lw_ops = frozenset(x for (p, c, s) in set(e1) - set(e0) for x in (p, c) if x in trial)
    vs = bench_views(ops, N, M, lw_ops)
    edges, alloc, need, reject = form_chains([vs], regions, depth)
    kr_r = collections.defaultdict(int)
    for (p, c, s) in edges:
        kr_r[c] |= {"a": 1, "b": 2, "c": 4, "d": 8}[s]
    out = []
    for k, g in enumerate(ops):
        g = dict(g)
        if k in alloc["w"]:
            g["krw"], g["krwb"] = 1, alloc["w"][k]
            if k not in need:
                g["dst"] = I.DST_NONE
        if k in kr_r:
            g["krr"], g["krrb"] = kr_r[k], alloc["r"][k]
        if k in lw_ops and (k in alloc["w"] or k in kr_r):
            g["krlw"] = 1
        out.append(g)
    return out, dict(edges=len(edges), producers=len(alloc["w"]), elided=sum(1 for p in alloc["w"] if p not in need),
                     lw=len([k for k in lw_ops if k in alloc["w"] or k in kr_r]), peak=alloc["peak"],
                     rejects=dict(reject))


def fuse(prog, Ds, N, M, regions, depth=KR_DEPTH, on=True, lw=False, strict=False):
    """The V4.1 pass.  prog: [(f, reads, writes, tag)] in issue order; Ds: DYN resolvers of the positions it must
    be legal at.  Returns (program, report); on=False returns the program unchanged."""
    if not on:
        return prog, dict(on=False)
    vps = [v41_views(prog, D, N, M) for D in Ds]
    bad = sorted({(k, v.tag) for vs in vps for k, v in enumerate(vs) if v.su and not v.skip and v.bad})
    if bad and strict:
        raise ValueError(f"SU legality (N={N}, M={M}): ops the unit refuses: {bad[:10]}")
    lw_ops = frozenset()
    if lw:
        lw_ops = choose_lw(prog, Ds, N, M, regions)
        vps = [v41_views(prog, D, N, M, lw_ops) for D in Ds]
    edges, alloc, need, reject = form_chains(vps, regions, depth)
    kr_r = collections.defaultdict(int)
    for (p, c, s) in edges:
        kr_r[c] |= {"a": 1, "b": 2, "c": 4, "d": 8}[s]
    out = []
    for k, (f, reads, writes, tag) in enumerate(prog):
        f = dict(f)
        if k in alloc["w"]:
            f["kr_w"], f["kr_wb"] = 1, alloc["w"][k]
            if k not in need:
                f["dst"] = I.DST_NONE
                for x in ("o_base", "o_so", "o_si", "o_d"):
                    f[x] = 0
        if k in kr_r:
            f["kr_r"], f["kr_rb"] = kr_r[k], alloc["r"][k]
        if k in lw_ops and (k in alloc["w"] or k in kr_r):
            f["kr_lw"] = 1
        out.append((f, reads, writes, tag))
    rep = report(prog, vps[0], edges, need, alloc, N, M)
    rep["rejects"] = dict(reject)
    rep["legality_faults"] = [dict(pc=k, tag=t) for k, t in bad]
    rep["kr_lw_ops"] = sorted(k for k in lw_ops if k in alloc["w"] or k in kr_r)
    return out, rep


def choose_lw(prog, Ds, N, M, regions):
    """Light ops worth laying at the SFU width: they sit next to an SFU-class op in a dependence the width alone
    breaks, and the vectors the narrower layout adds cost less than the round trip saved."""
    vs = v41_views(prog, Ds[0], N, M)
    trial = frozenset(k for k, v in enumerate(vs) if v.su and not v.skip and v.vw == N and
                      -(-v.n // M) - v.nv < ROT_READ + ROT_WRITE)
    vt = v41_views(prog, Ds[0], N, M, trial)
    e0, _ = analyse(vs, regions)
    e1, _ = analyse(vt, regions)
    gained = set(e1) - set(e0)
    return frozenset(x for (p, c, s) in gained for x in (p, c) if x in trial)


# ---- statistics -------------------------------------------------------------------------------------------
CATS = (("hc_pre", "hc_pre"), ("hc_post", "hc_post"), ("attn_norm", "rmsnorm"), ("ffn_norm", "rmsnorm"),
        ("head", "rmsnorm"), ("hc_attn", "hc_mix"), ("hc_ffn", "hc_mix"), ("engram", "engram"),
        ("compressor", "compressor"), ("indexer", "indexer"), ("attention", "attention"), ("moe", "moe"),
        ("embed", "embed"))


def category(tag):
    for key, cat in CATS:
        if key in tag:
            return cat
    return tag.split(".")[-1]


def report(prog, views, edges, need, alloc, N, M):
    """Chains (connected components of the edge graph), traffic avoided, per category."""
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x
    for (p, c, s) in edges:
        a, b = find(p), find(c)
        if a != b:
            parent[max(a, b)] = min(a, b)
    comp = collections.defaultdict(set)
    for (p, c, s) in edges:
        comp[find(p)].update((p, c))
    chains = []
    for root, ops in sorted(comp.items()):
        ops = sorted(ops)
        es = [(p, c, s) for (p, c, s) in edges if p in ops]
        rd = sum(edges[e] for e in es)
        wr = sum(views[p].n for p in ops if p in alloc["w"] and p not in need)
        # the chain's dependent depth: the longest path of edges (each a serial producer -> consumer hop)
        lp = {}
        for k in ops:
            lp[k] = max([lp[p] + 1 for (p, c, s) in es if c == k] + [0])
        chains.append(dict(ops=ops, length=len(ops), edges=len(es), path_edges=max(lp.values()), tag=prog[ops[0]][3],
                           category=category(prog[ops[0]][3]), vm_elem_reads_avoided=rd, vm_elem_writes_avoided=wr,
                           vectors=[views[k].nv for k in ops], streams=sorted(f"{p}->{c}:{s}" for p, c, s in es)))
    su = [v for v in views if v.su and not v.skip]
    su_reads = sum(len(a) for v in su for a in v.streams.values() if a is not None)
    su_writes = sum(len(v.out) for v in su if v.out is not None)
    by_cat = collections.defaultdict(lambda: dict(chains=0, ops_fused=0, edges=0, reads_avoided=0,
                                                  writes_avoided=0, max_len=0))
    for c in chains:
        b = by_cat[c["category"]]
        b["chains"] += 1
        b["ops_fused"] += c["length"]
        b["edges"] += c["edges"]
        b["reads_avoided"] += c["vm_elem_reads_avoided"]
        b["writes_avoided"] += c["vm_elem_writes_avoided"]
        b["max_len"] = max(b["max_len"], c["length"])
        b["path_edges"] = b.get("path_edges", 0) + c["path_edges"]
    hist = collections.Counter(c["length"] for c in chains)
    # per op class: ops in chains, chain heads (no KR read: they start from memory) and tails (no KR write)
    readers = {c for _, c, _ in edges}
    writers = {p for p, _, _ in edges}
    by_class = collections.defaultdict(lambda: dict(ops=0, heads=0, tails=0, middles=0, reads_avoided=0,
                                                    writes_avoided=0))
    for c in chains:
        for k in c["ops"]:
            f = prog[k][0]
            cls = op_class(f)
            b = by_class[cls]
            b["ops"] += 1
            b["heads" if k not in readers else "tails" if k not in writers else "middles"] += 1
            b["reads_avoided"] += sum(n for (p, c2, s), n in edges.items() if c2 == k)
            if k in alloc["w"] and k not in need:
                b["writes_avoided"] += views[k].n
    return dict(N=N, M=M, su_ops=sum(1 for v in views if v.su), su_ops_active=len(su), edges=len(edges),
                consumer_ops=len({c for _, c, _ in edges}), chains=len(chains),
                ops_in_chains=sum(c["length"] for c in chains),
                chain_length_hist={str(k): v for k, v in sorted(hist.items())},
                producers_writing_vm_still=sum(1 for p in alloc["w"] if p in need),
                producers_vm_write_elided=sum(1 for p in alloc["w"] if p not in need),
                vm_elem_reads_total=su_reads, vm_elem_reads_avoided=sum(edges.values()),
                vm_elem_writes_total=su_writes, vm_elem_writes_avoided=sum(c["vm_elem_writes_avoided"] for c in chains),
                path_edges=sum(c["path_edges"] for c in chains),
                cycles_saved_c_rotate_upper=sum(c["path_edges"] for c in chains) * (ROT_READ + ROT_WRITE),
                kr_peak_entries=alloc["peak"], by_category=dict(by_cat), by_op_class=dict(by_class),
                chain_heads=len(writers - readers), chain_tails=len(readers - writers), chains_detail=chains)


def op_class(f):
    """light / sfu (exp, sigmoid, SiLU) / divide / scalar (lane-0 side pipe), + '+red' when it reduces."""
    sfu = f.get("sfu", 0)
    c = ("scalar" if sfu in (I.SFU_RSQRT, I.SFU_SQRT, I.SFU_SPSQRT, I.SFU_EGATE) else
         "sfu" if sfu else "divide" if f.get("m1", 0) in (I.M1_DIVB, I.M1_DIVIMM) else "light")
    return c + ("+red" if f.get("red", 0) else "")


def stats_su_ops(prog):
    return sum(1 for f, *_ in prog if f["unit"] == I.UNIT_SU)


# ---- program sources ---------------------------------------------------------------------------------------
def shipped_program():
    import hdc_replay_v41 as R
    lay = R.ShapeLayout(R.SHIPPED)
    old = I.SU_LANES
    I.SU_LANES = 8
    try:
        b = R.ShapeBuilder(lay, True)
        sched = b.build()
    finally:
        I.SU_LANES = old
    prog = [(f, f["_reads"], f["_writes"], f["_tag"]) for f in sched]
    ivals = lambda pos: I.dyn_values(0, pos)                          # noqa: E731

    def mk(pos):
        dv, iv = R.dyn_values(R.SHIPPED, pos), ivals(pos)
        return lambda sel: (iv[sel] if isinstance(sel, int) else R.resolve(sel, dv))
    return prog, mk, Regions(lay.vm.map)


def reduced_program():
    import hdc_golden_v41 as V
    import hdc_program_v41 as P
    model = V.Model()
    lay = P.Layout(model)
    b = P.Builder(lay)
    sched = b.build()
    prog = [(f, r, w, t) for f, (_, r, w, t) in zip(sched, b.prog)]
    assert len(sched) == len(b.prog)

    def mk(pos):
        dv = I.dyn_values(0, pos)
        return lambda sel: dv[sel]
    return prog, mk, Regions(lay.vm.map), lay, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", default="shipped", choices=("shipped", "reduced"))
    ap.add_argument("--N", type=int, default=0)
    ap.add_argument("--M", type=int, default=0)
    ap.add_argument("--depth", type=int, default=KR_DEPTH)
    ap.add_argument("--lw", action="store_true")
    ap.add_argument("--positions", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--depths", default="", help="a depth curve (comma list); --depth is the full depth")
    a = ap.parse_args()
    if a.shape == "shipped":
        prog, mk, regions = shipped_program()
        N, M = a.N or 1024, a.M or 256
        pos = [int(x) for x in a.positions.split(",")] if a.positions else [0, 1, 7, 127, 128, 4095, 65535, 1048575]
    else:
        prog, mk, regions, _, _ = reduced_program()
        N, M = a.N or 16, a.M or 8
        pos = [int(x) for x in a.positions.split(",")] if a.positions else [0, 1, 2, 3, 7, 8, 15, 16, 31, 33, 64, 127]
    Ds = [mk(p) for p in pos]
    if a.depths:
        rec = sweep(prog, Ds, N, M, regions, [int(x) for x in a.depths.split(",")], a.depth, a.lw)
        rec.update(shape=a.shape, positions=pos, inputs=pins())
        print(json.dumps({k: v for k, v in rec.items() if k != "at_depth"}, indent=1))
        if a.out:
            Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
        return
    _, rep = fuse(prog, Ds, N, M, regions, depth=a.depth, lw=a.lw)
    rep["positions"] = pos
    det = rep.pop("chains_detail")
    print(json.dumps(rep, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(dict(rep, chains_detail=det), indent=1) + "\n")


# per fused hop on a chain's dependent path, under C_rotate (results/uarch/w11_vm_options.json C_rotate, claude/w11-crot):
# the consumer skips the operand read (16 stages) and the producer's element write (16) -- its control broadcast
# (5) stays; at root's fixed 42 cycles per SU op the hop saves 42 - 5 = 37
SAVE_PER_HOP = dict(c_rotate_class_stages=ROT_READ + ROT_WRITE, c_rotate_fixed_42_per_op=42 - 5)
SU_PERIOD_NS = 1.111                      # the serial domain (AGENTS.md clock domains)
# lane register file area, ASAP7 (estimate before the route): a D flop per bit at the hardened lane's 0.295 um2,
# plus a read multiplexer of depth - 1 two-input muxes per bit at 0.087 um2 and the write enables
FLOP_UM2, MUX2_UM2 = 0.295, 0.087


def kr_area_um2(depth):
    return round(32 * depth * FLOP_UM2 + 32 * (depth - 1) * MUX2_UM2 + depth * 0.5, 1)


def sweep(prog, Ds, N, M, regions, depths, full_depth, lw):
    """The depth curve: the pass at each KR depth (a value that does not fit stays in the vector memory)."""
    lw_ops = choose_lw(prog, Ds, N, M, regions) if lw else frozenset()
    vps = [v41_views(prog, D, N, M, lw_ops) for D in Ds]
    rows, at = [], {}
    for d in sorted(set(depths) | {full_depth}):
        edges, alloc, need, reject = form_chains(vps, regions, d)
        rep = report(prog, vps[0], edges, need, alloc, N, M)
        rep["rejects"] = dict(reject)
        det = rep.pop("chains_detail")
        rows.append(dict(depth=d, edges=rep["edges"], chains=rep["chains"], ops_in_chains=rep["ops_in_chains"],
                         path_edges=rep["path_edges"], vm_elem_reads_avoided=rep["vm_elem_reads_avoided"],
                         vm_elem_writes_avoided=rep["vm_elem_writes_avoided"], kr_peak_entries=rep["kr_peak_entries"],
                         cycles_saved_per_token={k: rep["path_edges"] * v for k, v in SAVE_PER_HOP.items()},
                         kr_bits_per_lane=32 * d, kr_area_um2_per_lane_estimate=kr_area_um2(d)))
        at[d] = dict(rep, chains=[dict(ops=c["ops"], length=c["length"], path_edges=c["path_edges"],
                                       category=c["category"], tag=c["tag"]) for c in det])
    full = rows[-1]
    for r in rows:
        r["fraction_of_peak_edges"] = round(r["edges"] / max(1, full["edges"]), 4)
        r["fraction_of_peak_reads_avoided"] = round(r["vm_elem_reads_avoided"] / max(1, full["vm_elem_reads_avoided"]), 4)
        r["fraction_of_peak_writes_avoided"] = round(r["vm_elem_writes_avoided"] / max(1, full["vm_elem_writes_avoided"]), 4)
        r["fraction_of_peak_cycles"] = round(r["path_edges"] / max(1, full["path_edges"]), 4)
    return dict(schema="opentallas.w11.su_fuse_stats/1", N=N, M=M, lw=lw, kr_lw_ops=len(lw_ops),
                save_per_hop_cycles=SAVE_PER_HOP, su_period_ns=SU_PERIOD_NS, depth_curve=rows,
                at_depth={str(k): v for k, v in at.items()})


def pins():
    files = ["tools/w11_su_fuse.py", "tools/hdc_isa_v41.py", "tools/hdc_program_v41.py", "tools/hdc_replay_v41.py",
             "tools/rtl_hdc_v41x_vec_campaign.py"]
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":
    main()
