#!/usr/bin/env python3
"""HBM-PRICE5 (10-18) option (1) input: per-quadrant expert load of DeepSeek-V4.1 routed top-6 on the REAL routing capture
(v41router.py phase R1: main-model teacher-forced greedy continuations, 120 traces, 40 layers, top-6 of 384 per position;
/tmp/claude-review-20261003/mtp_q/router/router_full.pt, int16 [40, positions, 6]).

Only decode positions (index >= the prompt length L) are counted.  Expert -> quadrant maps (static, compile-time):
  mod4      q = e mod 4
  block     q = e // 96
  freq      per layer, greedy bin packing of expert selection counts measured on the EVEN traces (largest first into the
            lightest quadrant, 96 experts each), evaluated on the ODD traces (held out)
Per position: max_q (routed experts in quadrant q); MTP P = 6: max_q |union over the 6 positions t..t+5 in quadrant q|.

    python3 -m hgi_sim.ep_quadrant_stats_1018 --pt router_full.pt --out OUT.json
"""
import argparse, collections, json
import numpy as np


def maps(counts):
    nq, ne = 4, counts.shape[1]
    m = {"mod4": np.tile(np.arange(ne) % nq, (counts.shape[0], 1)),
         "block": np.tile(np.arange(ne) // (ne // nq), (counts.shape[0], 1))}
    fr = np.zeros_like(m["mod4"])
    for L in range(counts.shape[0]):
        load, size = [0] * nq, [0] * nq
        for e in np.argsort(-counts[L], kind="stable"):
            q = min((q for q in range(nq) if size[q] < ne // nq), key=lambda q: load[q])
            fr[L, e] = q; load[q] += counts[L, e]; size[q] += 1
    m["freq"] = fr
    return m


def stats(v):
    v = np.asarray(v)
    h = collections.Counter(int(x) for x in v)
    return dict(n=int(v.size), mean=round(float(v.mean()), 4), p50=float(np.percentile(v, 50)),
                p99=float(np.percentile(v, 99)), p999=float(np.percentile(v, 99.9)), max=int(v.max()),
                hist={str(k): h[k] for k in sorted(h)})


def main():
    import torch
    ap = argparse.ArgumentParser()
    ap.add_argument("--pt", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = torch.load(a.pt, weights_only=True, map_location="cpu")
    tr = [(t["router_idx"].numpy().astype(np.int64), int(t["L"])) for t in d]
    NL, NE = tr[0][0].shape[0], 384
    train = np.zeros((NL, NE), np.int64)
    for i, (x, L) in enumerate(tr):
        if i % 2 == 0:
            for l in range(NL):
                np.add.at(train[l], x[l, L:].ravel(), 1)
    M = maps(train)
    out = dict(schema="opentallas.hbm_price5.ep_quadrant_stats.v1", source=a.pt, traces=len(tr), layers=NL, topk=6,
               rule=__doc__, maps={})
    for name, mp_ in M.items():
        ar, mtp, arl = [], [], collections.defaultdict(list)
        for i, (x, L) in enumerate(tr):
            if name == "freq" and i % 2 == 0:
                continue                                    # held-out evaluation
            for l in range(NL):
                q = mp_[l][x[l, L:]]                         # [pos, 6]
                cnt = np.stack([(q == k).sum(1) for k in range(4)], 1)
                mx = cnt.max(1)
                ar.extend(mx.tolist()); arl[l].extend(mx.tolist())
                e = x[l, L:]
                for t in range(0, e.shape[0] - 5, 6):
                    u = set(e[t:t + 6].ravel().tolist())
                    uq = collections.Counter(int(mp_[l][k]) for k in u)
                    mtp.append(max(uq.values()))
        out["maps"][name] = dict(ar_max_routed_per_quadrant=stats(ar), mtp6_max_union_per_quadrant=stats(mtp),
                                 ar_mean_by_layer={str(l): round(float(np.mean(v)), 3) for l, v in arl.items()})
    # union size (P = 6) for reference with ds_mtp_verify.UNION 23.9
    us = []
    for x, L in tr:
        for l in range(NL):
            e = x[l, L:]
            us.extend(len(set(e[t:t + 6].ravel().tolist())) for t in range(0, e.shape[0] - 5, 6))
    out["mtp6_union_size"] = stats(us)
    # binomial reference: 6 balls uniform into 4 bins
    rng = np.random.default_rng(0)
    b = np.array([np.bincount(rng.integers(0, 4, 6), minlength=4).max() for _ in range(200000)])
    out["uniform_reference_ar"] = stats(b)
    json.dump(out, open(a.out, "w"), indent=1)
    for k, v in out["maps"].items():
        print(k, {kk: {x: v[kk][x] for x in ("mean", "p50", "p99", "max")} for kk in ("ar_max_routed_per_quadrant", "mtp6_max_union_per_quadrant")})
    print("union", {x: out["mtp6_union_size"][x] for x in ("mean", "p99", "max")}, "uniform", out["uniform_reference_ar"]["mean"])


if __name__ == "__main__":
    main()
