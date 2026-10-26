#!/usr/bin/env python3
"""H-NETLIST/D4F-RELAY 10-17: re-home the fixed-depth SU RF (rfr_*) and SFU (sfr_*) relay chains on the H-DIE routed
station grid WITHOUT changing their stage count (the compiler's 36-stage RF ring / 11-stage SFU legs stay exact).

For every chain head-driver -> t0 -> ... -> t(K-1) -> tail-sink of the LAYER=none contract: the obstacle-aware relay
router (H-DIE relay_router.py, same grid / reach / root keepouts as the station list) plans the direct driver-pin ->
sink-pin route; it needs d stations at the reach.  d <= K: the K tiles take the d routed station homes in path order and
the K - d spare stages sit at the same routed homes (spread evenly: a co-located stage adds no wire hop), so every hop
of the chain is a routed hop <= reach and the latency is unchanged.  d > K is reported (the chain cannot meet the reach
at its fixed depth).  Output: a revision layer with key 'rehome' (full_die_v16.py) and a report.
    su_chain_rehome_d4f.py --case CASE --case-contract C --contract BASE.json.gz --hdie-src SRC --root-keepouts K
        [--reach 405] [--route-grid 10] --out-layer L.json --report R.json
"""
import argparse, collections, gzip, json, math, re, sys
from pathlib import Path

CHAIN = re.compile(r'^(rfr|sfr)_')


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def chains_of(c):
    I = c['instances']; rel = {n for n in I if CHAIN.match(n)}
    pred, succ = collections.defaultdict(set), collections.defaultdict(set)
    for e in c['edges']:
        s, d = e['source'][0], e['sink'][0]
        if d in rel:
            pred[d].add(s)
        if s in rel:
            succ[s].add(d)
    out = {}
    for h in sorted(n for n in rel if not (pred[n] & rel)):
        ch = [h]; x = h
        while succ[x] & rel:
            nx = succ[x] & rel
            assert len(nx) == 1, (x, nx)
            x = nx.pop(); ch.append(x)
        hd, tl = pred[ch[0]], succ[ch[-1]]
        assert len(hd) == 1 and len(tl) == 1, (h, hd, tl)
        out[h] = dict(head=next(iter(hd)), tail=next(iter(tl)), tiles=ch)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--case', '--case-contract', '--contract', '--hdie-src', '--root-keepouts', '--out-layer', '--report'):
        ap.add_argument(k, required=True)
    ap.add_argument('--reach', type=float, default=405.0); ap.add_argument('--route-grid', type=float, default=10.0)
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.hdie_src) / 'tools/hbm_die_v15'))
    import die_relay_pass as RP, relay_router as RR
    base = load(a.contract); I = base['instances']
    chains = chains_of(base)
    case = Path(a.case); man = json.loads((case / 'manifest.json').read_text())
    pl, nets, directions, _ = RP.load_case(case, load(a.case_contract))
    # pin points: head driver pins on nets that reach tile 0; tail sink pins on nets driven by the last tile
    hp, tp = collections.defaultdict(list), collections.defaultdict(list)
    first = {v['tiles'][0]: k for k, v in chains.items()}; last = {v['tiles'][-1]: k for k, v in chains.items()}
    for n, ends in nets.items():
        drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
        if len(drv) != 1:
            continue
        d = drv[0]
        for l in ends:
            if l is d:
                continue
            if l[0] in first and chains[first[l[0]]]['head'] == d[0]:
                hp[first[l[0]]].append(d[2])
            if d[0] in last and chains[last[d[0]]]['tail'] == l[0]:
                tp[last[d[0]]].append(l[2])
    cen = lambda pts: (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    router = RR.Router(man['placement'], man['die_um'], a.reach, G=a.route_grid, carved=man.get('carved_feedthrough'),
                       keepouts=[s_['keepout'] for s_ in json.load(open(a.root_keepouts))['sites']])
    rehome, rep, problems = {}, [], []
    for k, ch in chains.items():
        if not hp[k] or not tp[k]:
            problems.append(f'{k}: no head/tail pins in the case ({len(hp[k])}/{len(tp[k])})'); continue
        root, sink = cen(hp[k]), cen(tp[k])
        W = int(re.match(r'hbfd_rly_(\d+)_', I[ch['tiles'][0]]['master']).group(1))
        rsl, rtail, depth, viol = RR.plan_bus(router, [root, sink], [-1, 0], a.reach, W, [ch['tail']])
        K, d = len(ch['tiles']), depth[0]
        path = [s for s in rsl]            # p2p: one branch, stations in depth order
        path.sort(key=lambda s: s['depth'])
        if d > K:
            problems.append(f'{k}: routed depth {d} > fixed chain depth {K} at reach {a.reach}')
        if viol:
            problems.append(f'{k}: router hop violations {viol}')
        # K tiles over the d routed homes (d == 0: the sink's nearest free point); spares spread evenly
        homes = [(s['x'], s['y'], s['master'].rsplit('_', 1)[1]) for s in path] or \
                [(*[round(v, 1) for v in router.nearest_free(sink)], I[ch['tiles'][0]]['master'].rsplit('_', 1)[1])]
        m_ = len(homes)
        slot = [min(m_ - 1, (j * m_) // K) for j in range(K)] if K >= m_ else list(range(K))
        hops = []
        prev = root
        for j, t in enumerate(ch['tiles']):
            x, y, fl = homes[slot[j]]
            rehome[t] = dict(home=[x, y], master=re.sub(r'_[A-Z]{2}$', f'_{fl}', I[t]['master']),
                             why=f'chain {k} stage {j}/{K} on routed station {slot[j]}/{d} (reach {a.reach})')
            hops.append(abs(x - prev[0]) + abs(y - prev[1])); prev = (x, y)
        hops.append(abs(sink[0] - prev[0]) + abs(sink[1] - prev[1]))
        rep.append(dict(chain=k, head=ch['head'], tail=ch['tail'], stages=K, routed_depth=d, spare_stages=max(0, K - d),
                        max_routed_hop_um=max([s['hop_um'] for s in path] + [0]), max_manhattan_hop_um=round(max(hops), 1),
                        route_um=round(sum(s['hop_um'] for s in path), 1)))
    spec = dict(region='su_chain_rehome_d4f', author='Claude H-NETLIST/D4F-RELAY 1017', instances=[], edges=[], clocks=[],
                straps=[], gaps=[], rehome=rehome, notes=__doc__.split('\n\n')[1])
    Path(a.out_layer).write_text(json.dumps(spec, indent=1) + '\n')
    Path(a.report).write_text(json.dumps(dict(schema='opentallas.hbm.su_chain_rehome.v1', reach_um=a.reach, chains=rep,
                                              problems=problems), indent=1) + '\n')
    for r in rep:
        print(r['chain'], r['stages'], 'routed', r['routed_depth'], 'max hop', r['max_routed_hop_um'], 'route', r['route_um'])
    print('CHAINS', len(rep), 'tiles', len(rehome), 'problems', len(problems), problems[:6])


if __name__ == '__main__':
    main()
