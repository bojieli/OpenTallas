#!/usr/bin/env python3
"""HBM-MTP / MTP-STATS (10-18): P-lane sharing statistics for the next HBM die variant, from REAL captures.

Inputs (real DeepSeek-V4.1-Flash runs, released checkpoint, 2026-10-03, tools/v41_dspark_onpolicy):
  --router  router_full.pt   v41router.py phase R1: main-model teacher-forced pass over 120 greedy traces
                             (prompt + greedy continuation), every MoE gate's top-6 of 384 per position, int16 [40, n, 6]
  --drafts  drafts.json      v41draft.py: the real DSpark drafter's 5 drafts at every generated position (greedy mode)

(a) MoE expert union over P lanes, per layer, per verify cycle / lane group:
  cont      P consecutive positions of the trace (greedy continuation windows), P = 1..8      [real, proxy for verify]
  verify    actual DSpark acceptance walk (gamma = P-1, block truncated as acc_qualified.greedy_prompt), lanes =
            pending + P-1 drafts.  Lanes 0..a (a = accepted drafts) are the trace's own inputs at the trace's prefix,
            so their routing is EXACT.  Lanes a+1..P-1 carry rejected/after-reject draft tokens whose routing was not
            captured; three estimators are reported for them:
              v_cont    the trace's own continuation routing at those indices (the held 23.9 proxy, optimistic)
              v_decor   routing of a random other decode position of the same trace (decorrelated, realistic-high)
              v_upper   strict upper bound: every unknown lane adds 6 new experts (cap 384)
            plus v_known_lanes: the union over the exact lanes only (strict lower bound).
  indep     P independent users: P distinct traces, one random decode position each (mixed workloads, and
            same-workload groups)
  Per-expert lane histogram: for each expert in a union, how many of the P lanes route to it.
(b) is structural (no indexer capture exists); see README.
"""
import argparse, collections, hashlib, json
import numpy as np

NE, K, G = 384, 6, 5


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dist(v):
    v = np.asarray(v, float)
    return dict(n=int(v.size), mean=round(float(v.mean()), 3), p50=float(np.percentile(v, 50)),
                p90=float(np.percentile(v, 90)), p99=float(np.percentile(v, 99)), max=float(v.max()))


class Acc:
    """per-layer union sizes + lane-count histogram for one (mode, P)."""

    def __init__(s, NL, P):
        s.u = [[] for _ in range(NL)]
        s.h = np.zeros(P + 1, np.int64)
        s.P = P

    def add(s, rows):                       # rows: [NL, P, 6] expert ids (or list of per-layer lane lists)
        for l, lanes in enumerate(rows):
            c = collections.Counter(int(e) for ln in lanes for e in ln)
            s.u[l].append(len(c))
            for n in c.values():
                s.h[min(n, s.P)] += 1

    def addn(s, l, n):
        s.u[l].append(n)

    def out(s, per_layer=True):
        allv = [x for v in s.u for x in v]
        if not allv:
            return None
        o = dict(pooled=dist(allv))
        if per_layer:
            pl = [dist(v) for v in s.u]
            o["per_layer"] = {k: [d[k] for d in pl] for k in ("mean", "p50", "p90", "max")}
            o["layer_mean_range"] = [min(o["per_layer"]["mean"]), max(o["per_layer"]["mean"])]
        if s.h.sum():
            tot = s.h[1:].sum()
            o["lane_hist"] = {str(i): int(s.h[i]) for i in range(1, s.P + 1)}
            o["lane_hist_frac"] = {str(i): round(float(s.h[i]) / tot, 4) for i in range(1, s.P + 1)}
            o["mean_lanes_per_union_expert"] = round(float((np.arange(s.P + 1) * s.h).sum()) / tot, 3)
        return o


def main():
    import torch
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", required=True)
    ap.add_argument("--drafts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--indep-samples", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=20261018)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    R = torch.load(a.router, weights_only=False, map_location="cpu")
    D = {t["item"]["prompt_id"]: t for t in json.load(open(a.drafts)) if t.get("mode") == "greedy"}
    tr = []
    for x in R:
        it = x["item"] if isinstance(x["item"], dict) else eval(x["item"])  # noqa: S307 (own capture file)
        d = D[it["prompt_id"]]
        assert list(d["tokens"]) == list(x["tokens"])
        tr.append(dict(id=it["prompt_id"], wl=d["item"]["workload"], L=int(x["L"]), toks=list(x["tokens"]),
                       idx=x["router_idx"].numpy().astype(np.int64), drafts={int(p): v for p, v in d["drafts"].items()}))
    NL = tr[0]["idx"].shape[0]
    Ps = (1, 2, 4, 6, 8)
    res = dict(cont={}, verify={}, indep_mixed={}, indep_same_workload={})

    # ---- (a)(i) continuation windows
    for P in range(1, 9):
        A = Acc(NL, P)
        for t in tr:
            x, L, n = t["idx"], t["L"], t["idx"].shape[1]
            for i in range(L, n - P + 1):
                A.add(x[:, i:i + P])
        res["cont"][str(P)] = A.out(per_layer=P in Ps)

    # ---- (a)(i) actual DSpark verify walk, gamma = P-1 (P <= 6)
    tau = {}
    for P in (2, 3, 4, 5, 6):
        g = P - 1
        est = {k: Acc(NL, P) for k in ("v_known_lanes", "v_cont", "v_decor")}
        up = Acc(NL, P)
        acc_hist = np.zeros(g + 1, np.int64)
        cyc = com = 0
        for t in tr:
            x, toks, L, n = t["idx"], t["toks"], t["L"], t["idx"].shape[1]
            acc = {}
            for p, d in t["drafts"].items():
                if p + 1 + G > n - 1:
                    continue
                k = 0
                while k < G and d[k] == toks[p + 2 + k]:
                    k += 1
                acc[p] = min(k, g)
            p = L
            while p in acc:
                ac = acc[p]
                cyc += 1; com += ac + 1; acc_hist[ac] += 1
                known = x[:, p + 1:p + 2 + ac]                       # exact lanes
                unk_n = P - 1 - ac
                est["v_known_lanes"].add(known)
                est["v_cont"].add(x[:, p + 1:p + 1 + P])
                if unk_n:
                    js = rng.integers(L, n, unk_n)
                    est["v_decor"].add(np.concatenate([known, x[:, js]], axis=1))
                else:
                    est["v_decor"].add(known)
                for l in range(NL):
                    kn = len(set(known[l].ravel().tolist()))
                    up.addn(l, min(NE, kn + K * unk_n))
                p += ac + 1
        o = {k: v.out(per_layer=P in Ps) for k, v in est.items()}
        o["v_upper"] = up.out(per_layer=P in Ps)
        o["cycles"] = int(cyc)
        o["tau"] = round(com / cyc, 4)
        o["accepted_hist"] = acc_hist.tolist()
        o["mean_unknown_lanes"] = round(float(((g - np.arange(g + 1)) * acc_hist).sum() / cyc), 3)
        res["verify"][str(P)] = o
        tau[str(P - 1)] = o["tau"]

    # ---- (a)(ii) independent users
    by_wl = collections.defaultdict(list)
    for i, t in enumerate(tr):
        by_wl[t["wl"]].append(i)
    wls = sorted(by_wl)
    for mode in ("indep_mixed", "indep_same_workload"):
        for P in Ps[1:]:
            A = Acc(NL, P)
            for s in range(a.indep_samples):
                pool = list(range(len(tr))) if mode == "indep_mixed" else by_wl[wls[s % len(wls)]]
                us = rng.choice(pool, P, replace=False)
                lanes = []
                for u in us:
                    t = tr[u]
                    lanes.append(t["idx"][:, rng.integers(t["L"], t["idx"].shape[1])])
                A.add(np.stack(lanes, axis=1))
            res[mode][str(P)] = A.out()

    # uniform-random reference (independent top-6 of 384 per lane)
    unif = {str(P): round(NE * (1 - (1 - K / NE) ** P), 3) for P in range(1, 9)}

    ctx = [t["idx"].shape[1] for t in tr]
    out = dict(
        schema="opentallas.hbm_mtp_next_1018.mtp_stats_moe.v1",
        model=dict(name="DeepSeek-V4.1-Flash", n_layers=NL, n_routed_experts=NE, top_k=K, n_shared_experts=1,
                   dspark_block=G, config="compiler/models/deepseek-v4.1-flash/inference_config.json"),
        sources={a.router: sha(a.router), a.drafts: sha(a.drafts)},
        traces=len(tr), workloads={w: len(v) for w, v in by_wl.items()},
        decode_positions=int(sum(t["idx"].shape[1] - t["L"] for t in tr)),
        context_tokens=dict(min=min(ctx), p50=float(np.median(ctx)), max=max(ctx)),
        tau_greedy_walk_by_gamma=tau, uniform_random_union=unif, seed=a.seed, rule=__doc__, **res)
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
