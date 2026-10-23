#!/usr/bin/env python3
"""l34 (FT-HBM 10-23): die relay hop <= HOP um (REACH-M89: one-cycle M8/M9 hop 1.0-1.2 mm on HBM; repeaters every
<= 450 um inside the hop, die_repeaters step on the M7-M9 RC).

Contract -> contract.  Relay / landing tiles (masters hbfd_rly_* / hbfd_lh* / hbfd_land*) form stage ROWS (instance
name minus the _l<k> tile suffix) linked by the contract edges.  Per lane DAG the planner keeps every head row, tail
row, fork / merge row and row without a planned site, and greedily the last row before the route length (Manhattan
between consecutive row site centroids, i.e. along the planned channel route) since the previous kept row would exceed
HOP.  A DROPPED tile is removed by edge composition: every edge leaving its output port (o / b / ck_o / eb) is
re-sourced, bit range by bit range, from the edges entering the paired input (i / a / ckf / ea).  The data path is
unchanged except for the removed register stages: each lane's latency = its kept stage count (static schedule),
written to l34_stage_counts.json.  Its other inputs (ck / rs / en) lose that sink; clock_resets / straps of dropped
tiles are removed.  Nothing else changes.

    l34_relay_hop.py IN_contract.json OUT_contract.json --hop 1000 [--hop-wide 1200 --wide-min-bits 600] --report DIR
"""
import argparse, collections, json, re, sys
from pathlib import Path

PAIRS = {'o': 'i', 'b': 'a', 'ck_o': 'ckf', 'eb': 'ea'}
RELAY_RE = re.compile(r'^hbfd_(rly|lh|land)')
SITE_RE = re.compile(r'site \(([-\d.]+), ([-\d.]+)\) um')


def row_of(n):
    return re.sub(r'_l\d+$', '', n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp', type=Path); ap.add_argument('out', type=Path)
    ap.add_argument('--hop', type=float, default=1000.0)
    ap.add_argument('--hop-wide', type=float, default=None, help='hop for rows whose tiles carry >= --wide-min-bits')
    ap.add_argument('--wide-min-bits', type=int, default=600)
    ap.add_argument('--report', type=Path, required=True)
    a = ap.parse_args()
    c = json.loads(a.inp.read_text())
    I, E = c['instances'], c['edges']
    tiles = {n for n, v in I.items() if RELAY_RE.match(v['master'])}
    site = {}
    for n in tiles:
        m = SITE_RE.search(I[n].get('note', ''))
        if m: site[n] = (float(m.group(1)), float(m.group(2)))
    rows = collections.defaultdict(list)
    for n in tiles: rows[row_of(n)].append(n)
    succ = collections.defaultdict(set); pred = collections.defaultdict(set)
    rbits = collections.Counter()
    for e in E:
        s, t = e['source'][0], e['sink'][0]
        if t in tiles and e['sink'][1] in ('i', 'a'): rbits[row_of(t)] += e['bits']
        if s in tiles and t in tiles and row_of(s) != row_of(t) and e['source'][1] in PAIRS:
            succ[row_of(s)].add(row_of(t)); pred[row_of(t)].add(row_of(s))
    def cent(r):
        p = [site[n] for n in rows[r] if n in site]
        return (sum(x for x, _ in p) / len(p), sum(y for _, y in p) / len(p)) if p else None
    CT = {r: cent(r) for r in rows}
    def d(r, s):
        p, q = CT[r], CT[s]
        return abs(p[0] - q[0]) + abs(p[1] - q[1])
    forced = {r for r in rows if len(succ[r]) != 1 or len(pred[r]) != 1 or CT[r] is None}
    indeg = {r: len(pred[r]) for r in rows}; order = [r for r in rows if indeg[r] == 0]; k = 0
    while k < len(order):
        r = order[k]; k += 1
        for s in succ[r]:
            indeg[s] -= 1
            if indeg[s] == 0: order.append(s)
    left = set(rows) - set(order); forced |= left; order += sorted(left)
    keep, acc = set(forced), {}
    for r in order:
        if r in forced: acc[r] = 0.0; continue
        (p,) = tuple(pred[r]); (s,) = tuple(succ[r])
        if CT[s] is None: keep.add(r); acc[r] = 0.0; continue
        hop = a.hop_wide if (a.hop_wide and rbits[r] >= a.wide_min_bits) else a.hop
        acc[r] = acc.get(p, 0.0) + d(p, r)
        if acc[r] + d(r, s) > hop: keep.add(r); acc[r] = 0.0
    drop_tiles = {n for r in rows if r not in keep for n in rows[r]}
    # ---- edge composition
    ins = collections.defaultdict(list); outs = collections.defaultdict(list)
    alive = {}
    for k_, e in enumerate(E):
        alive[k_] = e; ins[(e['sink'][0], e['sink'][1])].append(k_); outs[(e['source'][0], e['source'][1])].append(k_)
    nxt = len(E); undriven = 0; composed = 0; removed_side = 0
    def add(e):
        nonlocal nxt
        alive[nxt] = e; ins[(e['sink'][0], e['sink'][1])].append(nxt); outs[(e['source'][0], e['source'][1])].append(nxt); nxt += 1
    def kill(k_):
        alive.pop(k_, None)
    for t in sorted(drop_tiles):
        for po, pi in PAIRS.items():
            oe = [alive[k_] for k_ in outs.get((t, po), []) if k_ in alive]
            ie = [alive[k_] for k_ in ins.get((t, pi), []) if k_ in alive]
            for k_ in list(outs.get((t, po), [])): kill(k_)
            for e in oe:
                olo, ohi = e['source'][2], e['source'][3]; dlo = e['sink'][2]
                cov = 0
                for j, f in enumerate(ie):
                    tlo, thi = f['sink'][2], f['sink'][3]
                    lo, hi = max(olo, tlo), min(ohi, thi)
                    if lo >= hi: continue
                    slo = f['source'][2] + (lo - tlo)
                    ne = dict(e); ne['name'] = f"{e['name']}~{j}"; ne['bits'] = hi - lo
                    ne['source'] = [f['source'][0], f['source'][1], slo, slo + hi - lo]
                    ne['sink'] = [e['sink'][0], e['sink'][1], dlo + (lo - olo), dlo + (hi - olo)]
                    ne['basis'] = (e.get('basis') or '') + ' | l34 relay hop (dropped ' + t + ')'
                    add(ne); composed += 1; cov += hi - lo
                undriven += (ohi - olo) - cov
    # remove all remaining edges that touch dropped tiles (inputs incl. side pins)
    for k_, e in list(alive.items()):
        if e['sink'][0] in drop_tiles or e['source'][0] in drop_tiles:
            if e['source'][0] in drop_tiles:
                print('L34_DANGLING_OUT', e['name'], file=sys.stderr)
            alive.pop(k_); removed_side += 1
    c['edges'] = [alive[k_] for k_ in sorted(alive)]
    for n in drop_tiles: I.pop(n)
    for key in ('clock_resets', 'straps'):
        if key in c: c[key] = [x for x in c[key] if x.get('instance', x.get('inst')) not in drop_tiles]
    if isinstance(c.get('masters'), dict):
        cnt = collections.Counter(v['master'] for v in I.values())
        c['masters'] = {m: v for m, v in c['masters'].items() if cnt.get(m) or not RELAY_RE.match(m)}
    c.setdefault('notes', []).append({'layer': 'l34_relay_hop (FT-HBM 10-23)', 'hop_um': a.hop, 'hop_wide_um': a.hop_wide,
                                      'dropped_tiles': len(drop_tiles), 'kept_rows': len(keep), 'rows': len(rows)})
    if isinstance(c.get('summary'), dict): c['summary']['instances'] = len(I)
    a.out.write_text(json.dumps(c))
    # ---- stage counts per tail row (deepest chain), now vs kept
    dn, dk = {}, {}
    for r in order:
        ps = [p for p in pred[r] if p in dn]
        dn[r] = 1 + max((dn[p] for p in ps), default=0); dk[r] = (1 if r in keep else 0) + max((dk[p] for p in ps), default=0)
    hops = []
    for r in keep:
        for s in succ[r]:
            L, q = (d(r, s) if CT[r] and CT[s] else 0.0), s
            while q not in keep:
                (q2,) = tuple(succ[q]); L += d(q, q2) if CT[q] and CT[q2] else 0.0; q = q2
            hops.append(L)
    hops.sort()
    a.report.mkdir(parents=True, exist_ok=True)
    tails = [r for r in rows if not succ[r]]
    rep = dict(schema='opentallas.hbm.l34_relay_hop.v1', inp=str(a.inp), hop_um=a.hop, hop_wide_um=a.hop_wide, wide_min_bits=a.wide_min_bits,
               tiles=len(tiles), rows=len(rows), kept_rows=len(keep), forced_rows=len(forced), dropped_tiles=len(drop_tiles),
               composed_edges=composed, removed_edges=removed_side, undriven_bits=undriven, edges_out=len(c['edges']),
               stages_now=sum(dn[t] for t in tails), stages_kept=sum(dk[t] for t in tails),
               kept_hop_um=dict(median=hops[len(hops) // 2], p99=hops[int(.99 * len(hops))], max=hops[-1]) if hops else None)
    (a.report / 'l34_report.json').write_text(json.dumps(rep, indent=1))
    (a.report / 'l34_stage_counts.json').write_text(json.dumps({t: dict(now=dn[t], kept=dk[t]) for t in sorted(tails)}))
    print('L34_RELAY_HOP', json.dumps(rep))


if __name__ == '__main__':
    main()
