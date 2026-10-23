#!/usr/bin/env python3
"""FT-HBM die what-if: relay hop <= HOP um along the CURRENT lane routes (REACH-M89: one-cycle M8/M9 hop 1.0-1.2 mm on HBM).

Reads chains_<case>.json (chains_from_die_v.py: every hbfd_* relay/landing tile, its in/out bus nets, its relay neighbours)
and keeps, per lane DAG, the head and tail rows, every fork/merge row, and greedily the last row before the accumulated
route length from the previous kept row would exceed HOP.  Every other row is DROPPED: in the ODB each dropped tile's
output nets are merged into its input nets (register removed, logic otherwise unchanged; latency = kept stages).
Outputs drop list (Tcl-friendly) + per-path stage counts (now / kept) for the static schedule.

    decimate_plan.py chains.json --hop 1000 --out DIR
"""
import argparse, collections, json, math, re
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('chains', type=Path)
ap.add_argument('--hop', type=float, default=1000.0)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
C = json.loads(a.chains.read_text())
def row(i): return re.sub(r'_l\d+$', '', i)
rows = collections.defaultdict(list)
for i in C: rows[row(i)].append(i)
succ = collections.defaultdict(set); pred = collections.defaultdict(set)
for i, r in C.items():
    for j in r['dn']:
        if row(j) != row(i): succ[row(i)].add(row(j)); pred[row(j)].add(row(i))
def cent(r):
    xs = [C[i]['xy'] for i in rows[r] if C[i]['xy']]
    return (sum(p[0] + p[2] / 2 for p in xs) / len(xs), sum(p[1] + p[3] / 2 for p in xs) / len(xs)) if xs else None
CT = {r: cent(r) for r in rows}
def d(r, s):
    p, q = CT[r], CT[s]
    return abs(p[0] - q[0]) + abs(p[1] - q[1]) if p and q else 0.0
forced = {r for r in rows if len(succ[r]) != 1 or len(pred[r]) != 1 or CT[r] is None}
# topological order (cycles are not expected; any row left over is forced)
indeg = {r: len(pred[r]) for r in rows}; order = [r for r in rows if indeg[r] == 0]; k = 0
while k < len(order):
    r = order[k]; k += 1
    for s in succ[r]:
        indeg[s] -= 1
        if indeg[s] == 0: order.append(s)
left = set(rows) - set(order); forced |= left; order += sorted(left)
keep = set(forced); acc = {}
for r in order:
    if r in forced:
        acc[r] = 0.0; continue
    (p,) = tuple(pred[r]); (s,) = tuple(succ[r])
    acc[r] = acc.get(p, 0.0) + d(p, r)
    if acc[r] + d(r, s) > a.hop:
        keep.add(r); acc[r] = 0.0
drop = [r for r in rows if r not in keep]
# per-path stage counts: depth (rows) now vs kept rows on the deepest path to each tail
dn, dk = {}, {}
for r in order:
    ps = [p for p in pred[r] if p in dn]
    dn[r] = 1 + max((dn[p] for p in ps), default=0)
    dk[r] = (1 if r in keep else 0) + max((dk[p] for p in ps), default=0)
tails = [r for r in rows if not succ[r]]
paths = []
for t in tails:
    dst = collections.Counter(); [dst.update(C[i]['dst']) for i in rows[t]]
    paths.append(dict(tail=t, dst=dst.most_common(1)[0][0] if dst else None, stages_now=dn[t], stages_kept=dk[t]))
a.out.mkdir(parents=True, exist_ok=True)
tiles = sorted(i for r in drop for i in rows[r])
(a.out / 'drop_tiles.txt').write_text('\n'.join(tiles) + '\n')
hops = []
for r in keep:
    for s in succ[r]:
        # walk to the next kept row
        L, q = d(r, s), s
        while q not in keep:
            (q2,) = tuple(succ[q]); L += d(q, q2); q = q2
        hops.append(L)
hops.sort()
rep = dict(hop_um=a.hop, rows=len(rows), kept_rows=len(keep), dropped_rows=len(drop), tiles=len(C), dropped_tiles=len(tiles),
           forced_rows=len(forced), stages_now=sum(p['stages_now'] for p in paths), stages_kept=sum(p['stages_kept'] for p in paths),
           kept_hop_um=dict(median=hops[len(hops) // 2], p90=hops[int(.9 * len(hops))], p99=hops[int(.99 * len(hops))], max=hops[-1],
                            over_hop=sum(h > a.hop for h in hops)))
(a.out / 'decimate_report.json').write_text(json.dumps(dict(rep, paths=paths), indent=0))
print(json.dumps(rep))
