#!/usr/bin/env python3
"""Post-placement rebind of plan-built core-tree clock sinks to the nearest planned leaf (FLOW-GEN-2, GEOM-REVIEW-46).

A plan-built core tree (core_infra core_tree) binds every register clock pin to a named leaf from a trial-placement
census BEFORE global placement; GPL then moves the flops, and the leaf-complete tree skips TritonCTS, so a sink can end
up far from its own leaf (QC node a0k3: 79 sinks > 100 um, max 294.4; leaf-net HPWL max 450.7).

This is structure, not a timing tweak: after placement every MOVABLE sink is re-bound among the plan's REGISTER leaves
(same clock, same planned stage depth: core_infra.compile_slice asserts one depth for every leaf) so that each leaf
keeps EXACTLY its planned sink count (the plan's 12.8 d1 driver sizing and joint_nldm load balance stay valid) and the
total squared Manhattan sink->leaf distance is minimal (an exact transportation optimum: start from the planned
binding, cancel negative cycles of the leaf-to-leaf move graph until none is left).  No delay is read or measured;
the clock function of every sink is unchanged (same port, same buffer depth), so it is LEC-neutral.
Pinned sinks (zero-logic related pairs that must share a leaf) never move.

  core_leaf_rebind.py IN.tsv OUT.tsv
IN.tsv rows:   L <leaf> <x_um> <y_um>               (one per eligible leaf driver)
               S <id> <x_um> <y_um> <leaf> <pinned 0|1>  (id = the caller's sink index; names never parsed here)
OUT.tsv rows:  '# OT_CORE_LEAF_REBIND ...' summary (also printed), then M <id> <from_leaf> <to_leaf> per moved sink.
"""
import sys

import numpy as np


def _cost(sx, sy, lx, ly):
    return (np.abs(sx[:, None] - lx[None, :]) + np.abs(sy[:, None] - ly[None, :])) ** 2


def rebind(leaves, sinks, max_iter=200000):
    """leaves: [(name, x, y)], sinks: [(name, x, y, leaf, pinned)] -> (new leaf per sink (list), stats dict).
    Exact-count min sum d^2 assignment; deterministic (ties broken by index = input order)."""
    names = [l[0] for l in leaves]
    idx = {n: k for k, n in enumerate(names)}
    if len(idx) != len(names):
        raise ValueError("duplicate leaf")
    nL = len(names)
    lx = np.array([l[1] for l in leaves], float)
    ly = np.array([l[2] for l in leaves], float)
    cur = np.array([idx[s[3]] for s in sinks], int)
    mov = np.array([not int(s[4]) for s in sinks], bool)
    sx = np.array([s[1] for s in sinks], float)
    sy = np.array([s[2] for s in sinks], float)
    C = _cost(sx, sy, lx, ly)
    before = C[np.arange(len(sinks)), cur].copy()
    counts0 = np.bincount(cur, minlength=nL)
    INF = np.inf
    # W[u, v] = cheapest move of one movable sink from u to v; A[u, v] = that sink
    W = np.full((nL, nL), INF)
    A = np.full((nL, nL), -1, int)

    def row(u):
        m = np.nonzero((cur == u) & mov)[0]
        if not len(m):
            W[u, :] = INF; A[u, :] = -1; return
        D = C[m] - C[m, u][:, None]
        k = np.argmin(D, axis=0)
        W[u, :] = D[k, np.arange(nL)]
        A[u, :] = m[k]
        W[u, u] = INF

    for u in range(nL):
        row(u)
    it = cycles = moves = 0
    eps = 1e-9
    while it < max_iter:
        it += 1
        # Bellman-Ford from a virtual source (dist 0 everywhere)
        dist = np.zeros(nL); pred = np.full(nL, -1, int); last = -1
        for _ in range(nL):
            cand = dist[:, None] + W
            b = np.argmin(cand, axis=0)
            nd = cand[b, np.arange(nL)]
            upd = nd < dist - eps
            if not upd.any():
                last = -1; break
            dist[upd] = nd[upd]; pred[upd] = b[upd]
            last = int(np.nonzero(upd)[0][0])
        if last < 0:
            break
        v = last
        for _ in range(nL):
            v = pred[v]
        cyc = [v]; u = pred[v]
        while u != v:
            cyc.append(u); u = pred[u]
        cyc.reverse()                      # cyc[i] -> cyc[i+1] are edges pred -> node
        edges = [(cyc[i], cyc[(i + 1) % len(cyc)]) for i in range(len(cyc))]
        if sum(W[a, b] for a, b in edges) >= -eps:
            break
        ss = [A[a, b] for a, b in edges]
        if len(set(ss)) != len(ss):
            break                         # cannot happen (one sink per source leaf); fail safe
        for (a, b), s_ in zip(edges, ss):
            cur[s_] = b
        moves += len(edges); cycles += 1
        for a in {a for a, _ in edges}:
            row(a)
    counts1 = np.bincount(cur, minlength=nL)
    if not np.array_equal(counts0, counts1):
        raise RuntimeError("leaf counts changed")
    after = C[np.arange(len(sinks)), cur]
    moved = int(np.sum(cur != np.array([idx[s[3]] for s in sinks])))

    def q(a):
        d = np.sqrt(np.sort(a))
        return dict(p50=round(float(d[len(d) // 2]), 2), p90=round(float(d[int(0.9 * (len(d) - 1))]), 2),
                    max=round(float(d[-1]), 2), gt50=int(np.sum(d > 50)), gt100=int(np.sum(d > 100)))
    stats = dict(leaves=nL, sinks=len(sinks), pinned=int(np.sum(~mov)), moved=moved, cycles=cycles,
                 converged=bool(it < max_iter), before=q(before), after=q(after))
    return [names[k] for k in cur], stats


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if len(a) != 2:
        raise SystemExit(__doc__)
    leaves, sinks = [], []
    for line in open(a[0]):
        f = line.split()
        if not f:
            continue
        if f[0] == "L":
            leaves.append((f[1], float(f[2]), float(f[3])))
        elif f[0] == "S":
            sinks.append((f[1], float(f[2]), float(f[3]), f[4], int(f[5])))
    new, st = rebind(leaves, sinks)
    if not st["converged"]:
        raise SystemExit("OT_CORE_LEAF_REBIND not converged")
    summ = ("# OT_CORE_LEAF_REBIND leaves=%(leaves)d sinks=%(sinks)d pinned=%(pinned)d moved=%(moved)d cycles=%(cycles)d" % st
            + " before_p50/p90/max=%(p50)s/%(p90)s/%(max)s gt100=%(gt100)d" % st["before"]
            + " after_p50/p90/max=%(p50)s/%(p90)s/%(max)s gt100=%(gt100)d" % st["after"])
    with open(a[1], "w") as fh:
        fh.write(summ + "\n")
        for s_, n in zip(sinks, new):
            if n != s_[3]:
                fh.write(f"M {s_[0]} {s_[3]} {n}\n")
    print(summ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
