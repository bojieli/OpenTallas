#!/usr/bin/env python3
"""HBM-NEXT-ATT4 gate E1: does a KV-line-stationary UNION stream reproduce every lane's golden attention exactly?

Golden (tools/hdc_golden_v41.py Model.attention / Model.attend, two-pass softmax, blocks = [all rows]):
  a query's rows = its window rows OLDEST FIRST (ascending position) + its index selections SORTED ASCENDING
  (indexer(): sel = sorted(topk_lowest_index(...))); s = dots(q, kvm) * scale; m = max; e = exp(s - m);
  acc = dots(bf16(e), kvm.T) (p.v summed over the lane's own row list); den = reduce_rows(e) + exp(sink - m);
  o = bf16(acc / den).  Every sum runs over the query's OWN list order: chunk8 = csum (chunks of 8 list entries,
  sequential from +0, pairwise tree padded with +0), legacy = sequential (dots) / 8 interleaved partials (reduce_sum).

Union stream (the hardware being proposed): window positions of all lanes ascending, then the union of all lanes'
compressed selections ascending; each line carries a lane mask; lane l applies the line only if its mask bit is set and
keeps its OWN ordinal counter (chunk / partial boundaries, last chunk, padding are per lane).  Per-SM partition: each
lane's list is cut into the P=1 aligned runs of nrun chunks (rtl sm_attn_bench.plan); SM s streams the union range
covering all lanes' run s (boundary lines may go to two SMs) and publishes one node per lane; the cross-SM pairwise
merge per lane is the P=1 one.

  att4_e1_union.py synth --out R.json [--heads 8] [--ncomp 2048] [--sigma 0.3 ...] [--arith chunk8|legacy]
  att4_e1_union.py real  --out R.json [--prompt 170] [--verify 6] [--arith chunk8|legacy]   (reduced DS V4.1 checkpoint)
Negative controls (must MISMATCH): zins (unselected lines enter as +0 terms at union ordinals), rank (selections in
score-rank order, the lane-0 rank order), fixsm (fixed union-range SM split, chunks cut at the SM boundary).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402

F = np.float32
NSM = 32


def load_golden(arith):
    os.environ["HDC_V41_ARITH"] = arith
    import hdc_golden_v41 as V  # noqa: E402
    V.set_arith(arith)
    return V


def b32(a):
    return np.asarray(a, dtype=F).view(np.uint32)


# ---------------------------------------------------------------- golden core (verbatim Model.attend, one block)
def golden_core(V, q, kvm, scale, sink):
    s = V.mul(V.dots(q, kvm), scale)
    m = np.max(s, axis=1)
    e = V.exp(V.add(s, V.neg(m)[:, None]))
    acc = V.dots(V.to_bf16(e), kvm.T)
    den = V.reduce_rows(e)
    den = V.add(den, V.exp(V.add(sink, V.neg(m))))
    return acc, den, V.to_bf16(V.div(acc, den[:, None]))


# ---------------------------------------------------------------- streaming sums keyed by the lane's own ordinal
class StreamSum:
    """One lane's running sum over its OWN list ordinal o = 0, 1, ...  chunk8: csum (sequential chunk of 8 from +0,
    chunk sums kept, padded pairwise tree at the end); legacy 'seq': sequential from +0 (dots); legacy 'il8': 8
    interleaved partials by o % 8 then pairwise (reduce_sum)."""

    def __init__(self, V, kind, shape):
        self.V, self.kind, self.shape = V, kind, shape
        self.o = 0
        self.acc = np.zeros(shape, F)
        self.chunks = []
        self.part = [np.zeros(shape, F) for _ in range(8)]

    def push(self, y):
        V = self.V
        if self.kind == "chunk8":
            self.acc = V.add(self.acc if self.o % 8 else np.zeros(self.shape, F), y)
            if self.o % 8 == 7:
                self.chunks.append(self.acc)
        elif self.kind == "seq":
            self.acc = V.add(self.acc, y)
        else:
            self.part[self.o % 8] = V.add(self.part[self.o % 8], y)
        self.o += 1

    def chunk_sums(self):
        assert self.kind == "chunk8"
        return self.chunks + ([self.acc] if self.o % 8 else [])

    def total(self):
        V = self.V
        if self.kind == "seq":
            return self.acc
        if self.kind == "chunk8":
            return pairwise_pad(V, self.chunk_sums(), self.shape)
        p = list(self.part)
        while len(p) > 1:
            p = [V.add(p[i], p[i + 1]) for i in range(0, len(p), 2)]
        return p[0]


def pairwise_pad(V, nodes, shape):
    nodes = list(nodes) or [np.zeros(shape, F)]
    while len(nodes) & (len(nodes) - 1):
        nodes.append(np.zeros(shape, F))
    while len(nodes) > 1:
        nodes = [V.add(nodes[i], nodes[i + 1]) for i in range(0, len(nodes), 2)]
    return nodes[0]


# ---------------------------------------------------------------- the union stream
def build_union(lanes, order="asc"):
    """lanes: [dict(win=[positions asc], sel=[comp idx asc])] -> stream [(kind, idx, mask)].  order='rank' (negative
    control) puts the compressed union in lane 0's rank order (lane['rank']) then the rest ascending."""
    uw = sorted(set(p for ln in lanes for p in ln["win"]))
    uc = sorted(set(i for ln in lanes for i in ln["sel"]))
    if order == "rank":
        r0 = list(lanes[0]["rank"])
        uc = r0 + [i for i in uc if i not in set(r0)]
    ws = [set(ln["win"]) for ln in lanes]
    cs = [set(ln["sel"]) for ln in lanes]
    st = [("w", p, tuple(p in w for w in ws)) for p in uw]
    st += [("c", i, tuple(i in c for c in cs)) for i in uc]
    return st


def union_core(V, qs, stream, rowfn, scale, sinks, arith, zins=False, sm_plan=None):
    """Hardware-faithful emulation.  QK pass over the stream (lane-masked), per-lane softmax, PV + den pass over the
    stream with per-lane ordinals.  sm_plan: None (one SM) or 'aligned' / 'fixsm' (per-SM partition, chunk8 only)."""
    nl = len(qs)
    H = qs[0].shape[0]
    hd = qs[0].shape[1]
    # QK: scores land at the lane's own ordinal (zins: at the union ordinal, unselected lines contribute a 0 score
    # that is masked out of the max/exp by giving it e = +0 -- the 'zero insertion' variant)
    s = [[] for _ in range(nl)]
    for kind, idx, mask in stream:
        row = rowfn(kind, idx)
        for l in range(nl):
            if mask[l]:
                s[l].append(V.mul(V.dots(qs[l], row[None, :])[:, 0], scale))
            elif zins:
                s[l].append(None)
    outs = []
    sm_spans = None
    for l in range(nl):
        sl = np.stack([x for x in s[l] if x is not None], axis=1)
        m = np.max(sl, axis=1)
        e_sel = V.exp(V.add(sl, V.neg(m)[:, None]))
        if zins:
            e = np.zeros((H, len(s[l])), F)
            e[:, [i for i, x in enumerate(s[l]) if x is not None]] = e_sel
        else:
            e = e_sel
        p = V.to_bf16(e)
        outs.append(dict(m=m, e=e, p=p))
    pvk = "chunk8" if arith == "chunk8" else "seq"
    dk = "chunk8" if arith == "chunk8" else "il8"
    if sm_plan is None:
        pv = [StreamSum(V, pvk, (H, hd)) for _ in range(nl)]
        dn = [StreamSum(V, dk, (H,)) for _ in range(nl)]
        o = [0] * nl
        for kind, idx, mask in stream:
            row = rowfn(kind, idx)
            for l in range(nl):
                if mask[l] or zins:
                    pl = outs[l]["p"][:, o[l]]
                    pv[l].push(V.mul(pl[:, None], row[None, :]))
                    dn[l].push(outs[l]["e"][:, o[l]])
                    o[l] += 1
        accs = [x.total() for x in pv]
        dens = [x.total() for x in dn]
    else:
        assert arith == "chunk8"
        accs, dens, sm_spans = sm_partition(V, stream, rowfn, outs, nl, H, hd, sm_plan)
    res = []
    for l in range(nl):
        den = V.add(dens[l], V.exp(V.add(sinks, V.neg(outs[l]["m"]))))
        res.append((accs[l], den, V.to_bf16(V.div(accs[l], den[:, None]))))
    return res, sm_spans


def sm_partition(V, stream, rowfn, outs, nl, H, hd, plan):
    """Per-SM union streams.  'aligned': SM s covers, for every lane, the lane's P=1 aligned run s (ordinals
    [8 nrun s, 8 nrun (s+1))); its union range is the hull of those runs and its lane masks select only the run's lines.
    'fixsm': the union is cut into equal contiguous ranges, each SM restarts chunks at its range start (wrong)."""
    U = len(stream)
    lane_ord = []                    # per lane: union index of each ordinal
    for l in range(nl):
        lane_ord.append([u for u, (_, _, mk) in enumerate(stream) if mk[l]])
    T = [len(x) for x in lane_ord]
    nch = [-(-t // 8) for t in T]
    nrun = [1] * nl
    for l in range(nl):
        while -(-nch[l] // nrun[l]) > NSM:
            nrun[l] *= 2
    nsm = max(-(-nch[l] // nrun[l]) for l in range(nl))
    accs, dens, spans = [], [], []
    nodes = [[] for _ in range(nl)]
    dnodes = [[] for _ in range(nl)]
    if plan == "fixsm":
        bounds = [(U * s // nsm, U * (s + 1) // nsm) for s in range(nsm)]
    for s in range(nsm):
        if plan == "aligned":
            runs = []
            for l in range(nl):
                a, b = 8 * nrun[l] * s, min(T[l], 8 * nrun[l] * (s + 1))
                runs.append((lane_ord[l][a], lane_ord[l][b - 1]) if a < T[l] else None)
            lo = min(r[0] for r in runs if r)
            hi = max(r[1] for r in runs if r)
        else:
            lo, hi = bounds[s][0], bounds[s][1] - 1
            runs = [(lo, hi)] * nl
        need = [u for u in range(lo, hi + 1)
                if any(stream[u][2][l] and runs[l] and runs[l][0] <= u <= runs[l][1] for l in range(nl))]
        spans.append((len(need), sum((min(T[l], 8 * nrun[l] * (s + 1)) - 8 * nrun[l] * s) for l in range(nl)
                                     if 8 * nrun[l] * s < T[l])))
        pv = [StreamSum(V, "chunk8", (H, hd)) for _ in range(nl)]
        dn = [StreamSum(V, "chunk8", (H,)) for _ in range(nl)]
        for u in need:
            kind, idx, mask = stream[u]
            row = rowfn(kind, idx)
            for l in range(nl):
                if mask[l] and runs[l] and runs[l][0] <= u <= runs[l][1]:
                    o = lane_ord[l].index(u)
                    pv[l].push(V.mul(outs[l]["p"][:, o][:, None], row[None, :]))
                    dn[l].push(outs[l]["e"][:, o])
        for l in range(nl):
            nr = nrun[l]
            cs = pv[l].chunk_sums()
            ds = dn[l].chunk_sums()
            nodes[l].append(pairwise_pad(V, cs + [np.zeros((H, hd), F)] * (nr - len(cs)), (H, hd)) if cs
                            else np.zeros((H, hd), F))
            dnodes[l].append(pairwise_pad(V, ds + [np.zeros((H,), F)] * (nr - len(ds)), (H,)) if ds
                             else np.zeros((H,), F))
    for l in range(nl):
        accs.append(pairwise_pad(V, nodes[l], (H, hd)))
        dens.append(pairwise_pad(V, dnodes[l], (H,)))
    return accs, dens, spans


def sm_balance(stream, nl, nsm=NSM):
    """best of sm_balance1 over run sizes nrun, nrun/2, nrun/4 (smaller aligned runs = more nodes, same exactness)."""
    best = None
    for div in (1, 2, 4):
        r = sm_balance1(stream, nl, nsm, div)
        if best is None or r[0] < best[0]:
            best = r + (div,)
    return best


def sm_balance1(stream, nl, nsm=NSM, div=1):
    """Lines a SM streams when the (lane, aligned run) jobs are spread over all nsm SMs (exactness is the same as
    'aligned': each (lane, run) node is computed alone, only the SM that streams it changes).  A run index s whose
    lanes share >= 25% of their lines stays one grouped job (lines streamed once for the group); otherwise its lanes
    become separate jobs.  LPT onto nsm SMs; a SM's jobs run back to back.  -> (max lines, mean lines, jobs)"""
    lane_ord = [[u for u, (_, _, mk) in enumerate(stream) if mk[l]] for l in range(nl)]
    T = [len(x) for x in lane_ord]
    nrun = []
    for l in range(nl):
        nch, r = -(-T[l] // 8), 1
        while -(-nch // r) > NSM:
            r *= 2
        nrun.append(max(1, r // div))
    jobs = []
    for s in range(max(-(-(-(-T[l] // 8)) // nrun[l]) for l in range(nl))):
        runs = [set(lane_ord[l][8 * nrun[l] * s: 8 * nrun[l] * (s + 1)]) for l in range(nl)]
        tot, uni = sum(len(r) for r in runs), len(set().union(*runs))
        if tot and uni <= 0.75 * tot:
            jobs.append(uni)
        else:
            jobs += [len(r) for r in runs if r]
    load = [0] * nsm
    for j in sorted(jobs, reverse=True):
        load[load.index(min(load))] += j
    return max(load), round(sum(load) / nsm, 2), len(jobs)


def compare(golds, gots):
    """per lane: mismatching FP32 words of acc (p.v) + den + BF16 o (all three bit for bit)."""
    return [sum(int(np.sum(b32(gi) != b32(xi))) for gi, xi in zip(g, x)) for g, x in zip(golds, gots)]


# ---------------------------------------------------------------- synthetic full DS shape
def synth(a):
    V = load_golden(a.arith)
    rng = np.random.default_rng(a.seed)
    H, hd, W, K = a.heads, 512, 128, a.topk
    pos0 = a.ncomp * 4 + 1000
    nl = a.lanes
    win_rows = {p: V.qdq_fp8(rng.standard_normal(hd).astype(F) * F(rng.choice([0.05, 1.0, 4.0])))
                for p in range(pos0 - W + 1, pos0 + nl)}
    ckv = [V.qdq_fp4_e4m3(rng.standard_normal(hd).astype(F) * F(rng.choice([0.05, 1.0, 4.0])), 16)
           for _ in range(a.ncomp + nl)]
    sinks = rng.standard_normal(H).astype(F)
    scale = F(hd ** -0.5)

    def rowfn(kind, idx):
        return win_rows[idx] if kind == "w" else ckv[idx]

    out = dict(mode="synth", arith=a.arith, heads=H, hd=hd, window=W, topk=K, ncomp=a.ncomp, lanes=nl, seed=a.seed,
               cases=[])
    for sigma in a.sigma:
        base = rng.standard_normal(a.ncomp + nl)
        lanes = []
        for l in range(nl):
            pos = pos0 + l
            n = (pos + 1) // 4 - (pos0 + 1) // 4 + a.ncomp            # compressed rows visible to this lane
            if sigma < 0:      # disjoint lanes (multi-user stand-in: independent selections over disjoint ranges)
                sc = np.full(a.ncomp + nl, -np.inf)
                seg = (a.ncomp // nl)
                sc[l * seg:(l + 1) * seg] = rng.standard_normal(seg)
            else:
                sc = base + sigma * rng.standard_normal(a.ncomp + nl)
            sc = sc[:n]
            rank = [int(i) for i in V.topk_lowest_index(sc, min(K, n))]
            lanes.append(dict(win=list(range(pos - W + 1, pos + 1)), sel=sorted(rank), rank=rank,
                              q=V.to_bf16(rng.standard_normal((H, hd)).astype(F) * F(0.6))))
        golds = []
        for ln in lanes:
            kvm = np.stack([win_rows[p] for p in ln["win"]] + [ckv[i] for i in ln["sel"]])
            golds.append(golden_core(V, ln["q"], kvm, scale, sinks))
        qs = [ln["q"] for ln in lanes]
        st = build_union(lanes)
        U = len(st)
        sels = [set(ln["sel"]) for ln in lanes]
        ov = float(np.mean([len(sels[i] & sels[j]) / K for i in range(nl) for j in range(nl) if i < j]))
        case = dict(sigma=sigma, union_lines=U, lane_lines=[len(ln["win"]) + len(ln["sel"]) for ln in lanes],
                    mean_pair_topk_overlap=round(ov, 4))
        t0 = time.time()
        got, _ = union_core(V, qs, st, rowfn, scale, sinks, a.arith)
        case["union_mism"] = compare(golds, got)
        if a.arith == "chunk8":
            got, spans = union_core(V, qs, st, rowfn, scale, sinks, a.arith, sm_plan="aligned")
            case["sm_aligned_mism"] = compare(golds, got)
            case["sm_union_lines_max"] = max(x[0] for x in spans)
            case["sm_union_lines_mean"] = round(float(np.mean([x[0] for x in spans])), 2)
            case["sm_p1_lines_max"] = max(x[1] for x in spans)     # nl single-query runs back to back (P=1)
            case["sm_count"] = len(spans)
            bm, bmean, nj, dv = sm_balance(st, nl)
            case["sm32_balanced_lines_max"], case["sm32_balanced_lines_mean"], case["sm32_jobs"] = bm, bmean, nj
            case["sm32_run_div"] = dv
            case["sm32_ideal_lines"] = round(U / NSM, 1)
            case["model_upper_ratio_U4_U1"] = round((128 + nl - 1 + 512 * nl) / 640, 3)
            if not a.no_neg:
                got, _ = union_core(V, qs, st, rowfn, scale, sinks, a.arith, sm_plan="fixsm")
                case["neg_fixsm_mism"] = compare(golds, got)
        if not a.no_neg:
            got, _ = union_core(V, qs, st, rowfn, scale, sinks, a.arith, zins=True)
            case["neg_zins_mism"] = compare(golds, got)
            got, _ = union_core(V, qs, build_union(lanes, order="rank"), rowfn, scale, sinks, a.arith)
            case["neg_rank_mism"] = compare(golds, got)
        case["wall_s"] = round(time.time() - t0, 1)
        out["cases"].append(case)
        print(json.dumps(case), flush=True)
    return out


# ---------------------------------------------------------------- real: reduced DS V4.1 checkpoint, verify pass
def real(a):
    V = load_golden(a.arith)
    M = V.Model()
    rng = np.random.default_rng(a.seed)
    vocab = int(M.c["vocab_size"])
    cap = {}
    orig_attention, orig_attend = V.Model.attention, V.Model.attend

    def attention(self, L, x, pos, state, trace, ctx):
        cap["cur"] = None
        r = orig_attention(self, L, x, pos, state, trace, ctx)
        if cap.get("on"):
            n = len(state["win"][L])
            win = list(range(max(0, n - self.window), n))
            sel = list(ctx.get("sel", [])) if self.ratio[L] else []
            q, kvm, cs, out = cap["cur"]
            cap["rec"].append(dict(L=L, pos=pos, win=win, sel=sel, q=q, cs=cs, out=out, nkvm=len(kvm)))
        return r

    def attend(self, L, q, kvm, cs, blocks=None):
        out = orig_attend(self, L, q, kvm, cs, blocks)
        cap["cur"] = (q, kvm, cs, out)
        return out

    V.Model.attention, V.Model.attend = attention, attend
    state = M.new_state()
    toks = [int(t) for t in rng.integers(0, vocab, a.prompt + a.verify)]
    t0 = time.time()
    for p in range(a.prompt):
        M.decode_token(toks[p], p, state)
    cap["on"], cap["rec"] = True, []
    M.forward_positions(toks[a.prompt:], a.prompt, state)        # the layer-major verify pass (N = verify)
    cap["on"] = False
    t_run = time.time() - t0
    by_L = {}
    for r in cap["rec"]:
        by_L.setdefault(r["L"], []).append(r)
    res = dict(mode="real", arith=a.arith, prompt=a.prompt, verify=a.verify, layers=len(by_L), passes=[],
               golden_run_s=round(t_run, 1))
    tot_bad = tot_bad_full = 0
    for L, recs in sorted(by_L.items()):
        recs.sort(key=lambda r: r["pos"])
        src = M.kv_of.get(L)
        sink = M.lw(L, "attn.attn_sink")

        def rowfn(kind, idx, L=L, src=src):
            return state["win"][L][idx] if kind == "w" else state["ckv"][src][idx]

        for g0 in range(0, len(recs), a.lanes):
            grp = recs[g0:g0 + a.lanes]
            lanes = [dict(win=r["win"], sel=r["sel"], rank=r["sel"]) for r in grp]
            for ln, r in zip(lanes, grp):
                assert len(ln["win"]) + len(ln["sel"]) == r["nkvm"], (L, r["pos"])
            st = build_union(lanes)
            qs = [r["q"] for r in grp]
            got, _ = union_core(V, qs, st, rowfn, M.attn_scale, sink, a.arith)
            # golden's own output: post-core of Model.attend applied to the union o, against the captured attend out
            full_bad = 0
            for (_, _, o), r in zip(got, grp):
                o2 = V.rope_tail(o, r["cs"], inverse=True)
                og = o2.reshape(M.groups, -1)
                wa = M.lw(L, "attn.wo_a.weight").reshape(M.groups, M.o_rank, -1)
                z = np.stack([V.matvec_c(wa[gi], og[gi], V.WO_A_SPLIT) for gi in range(M.groups)])
                y = V.linear_q(M.lw(L, "attn.wo_b.weight"), V.to_bf16(z.reshape(-1)))
                full_bad += int(np.sum(b32(y) != b32(r["out"])))
            rec = dict(L=L, lanes=len(grp), union_lines=len(st), lane_lines=[len(x["win"]) + len(x["sel"]) for x in lanes],
                       sel_union=len(set(i for x in lanes for i in x["sel"])), sel_each=[len(x["sel"]) for x in lanes],
                       attend_out_mism=full_bad)
            if sm := (a.arith == "chunk8" and len(st) > 8 * NSM):
                got2, spans = union_core(V, qs, st, rowfn, M.attn_scale, sink, a.arith, sm_plan="aligned")
                rec["sm_aligned_mism"] = sum(compare(got, got2))
            tot_bad_full += full_bad
            res["passes"].append(rec)
        print(json.dumps(res["passes"][-1]), flush=True)
    res["attend_out_mism_total"] = tot_bad_full
    res["verdict"] = "PASS" if tot_bad_full == 0 and res["passes"] else "FAIL"
    return res


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("synth")
    s.add_argument("--heads", type=int, default=8)
    s.add_argument("--ncomp", type=int, default=2048)
    s.add_argument("--topk", type=int, default=512)
    s.add_argument("--lanes", type=int, default=4)
    s.add_argument("--sigma", type=float, nargs="+", default=[0.0, 0.15, 0.4, 1.0, -1])
    s.add_argument("--no-neg", action="store_true")
    r = sub.add_parser("real")
    r.add_argument("--prompt", type=int, default=170)
    r.add_argument("--verify", type=int, default=6)
    r.add_argument("--lanes", type=int, default=4)
    for p in (s, r):
        p.add_argument("--arith", choices=["chunk8", "legacy"], default="chunk8")
        p.add_argument("--seed", type=int, default=1019)
        p.add_argument("--out", required=True)
    a = ap.parse_args()
    out = synth(a) if a.cmd == "synth" else real(a)
    if a.cmd == "synth":
        ok = all(c["union_mism"] == [0] * a.lanes and c.get("sm_aligned_mism", [0] * a.lanes) == [0] * a.lanes
                 for c in out["cases"])
        neg = [k for c in out["cases"] for k in ("neg_zins_mism", "neg_rank_mism", "neg_fixsm_mism")
               if k in c and sum(c[k]) == 0 and c["sigma"] >= 0 and c["sigma"] != 0.0]
        out["negatives_that_passed"] = neg
        out["verdict"] = "PASS" if ok else "FAIL"
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(("PASS" if out["verdict"] == "PASS" else "FAIL") + " ATT4_E1 " + a.cmd + " " + a.arith)
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
