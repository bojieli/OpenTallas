#!/usr/bin/env python3
"""H-D4G 10-17: bus rows (driver inst.port, final non-relay sinks, bits, clock domain, relay stations) of a GENERATED
HBM die contract, with its relay chains collapsed.  Replaces the run9 dry-run rows the H-PLANSTUDY bus model read
(deleted with the d4f cancel): the d4g plan metrics run the same plan_study_1017 bus model on these rows for plan (b)
and plan d4g alike.
    d4g_bus_rows.py CONTRACT.json --out ROWS.json
"""
import collections, json, sys


def main():
    c = json.load(open(sys.argv[1]))
    out = sys.argv[sys.argv.index('--out') + 1]
    I = c['instances']
    rly = lambda n: I.get(n, {}).get('master', '').startswith(('hbfd_rly', 'hfd_stn'))
    nxt = collections.defaultdict(list)          # relay -> data successors (inst, port)
    starts = collections.defaultdict(list)       # (drv, port) -> [(inst, port, bits, clock)]
    for e in c['edges']:
        s, t = e['source'], e['sink']
        if rly(s[0]):
            if s[1].startswith('o'):
                nxt[s[0]].append((t[0], t[1]))
            continue
        if rly(t[0]) and t[1] != 'i':
            continue
        starts[(s[0], s[1])].append((t[0], t[1], (s[2], s[3]) if len(s) > 3 else (0, e['bits']), e.get('clock')))
    rows = []

    def reach(t):
        sinks, nst, st = set(), set(), [t]
        while st:
            x = st.pop()
            if rly(x):
                if x not in nst:
                    nst.add(x); st.extend(y for y, _ in nxt[x])
            else:
                sinks.add(x)
        return sinks, nst
    for (d, p), L in starts.items():
        # slices of one driver port that reach the same sink set form one bus; disjoint slices to different sinks
        # (PHY dram_rdata -> 32 PC leaves) are separate point-to-point buses, not a broadcast
        grp = collections.defaultdict(lambda: [set(), set(), None])
        for t, tp, sl, ck in L:
            sk, ns = reach(t)
            sk.discard(d)
            if not sk:
                continue
            g = grp[frozenset(sk)]
            g[0].update(range(sl[0], sl[1])); g[1] |= ns; g[2] = g[2] or ck
        # one slice reaching several sink sets through different relay chains: fold sets sharing bits
        for sk, (bits, ns, ck) in grp.items():
            rows.append(dict(driver=f'{d}.{p}', sinks=sorted(sk), bits=len(bits), domain=ck or 'stream', stations=len(ns),
                             cls='fork' if len(sk) > 1 else 'p2p'))
    json.dump(dict(schema='opentallas.hbm.d4g.bus_rows.v1', contract=sys.argv[1], rows=rows), open(out, 'w'))
    print(len(rows), 'rows;', sum(r['stations'] for r in rows), 'relay instances on rows;',
          collections.Counter(r['cls'] for r in rows))


if __name__ == '__main__':
    main()
