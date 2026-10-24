#!/usr/bin/env python3
"""HBM-ARCH: plan comparison metrics (d4g vs concepts) from a die_plan.json + its G0C report.
    python3 metrics.py NAME PLAN.json G0C_REPORT.json [...]  -> JSON rows on stdout"""
import collections, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'die_plan'))
import check as CK, schema as S

rows = []
args = sys.argv[1:]
for i in range(0, len(args), 3):
    name, pp, rp = args[i:i + 3]
    raw = json.load(open(pp)); P = S.Plan(raw)
    r = json.load(open(rp))
    W, H = raw['die']['outline_um']
    bits = bitmm = 0.0; hopmax = 0.0; stations = 0
    for lid in P.lanes:
        pts, regs, xs = CK.lane_geometry(P, lid)
        w = P.ports[P.lanes[lid]['ports'][0]]['width']
        L = CK.plen(pts)
        bits += w; bitmm += w * L / 1000.0
        hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(regs, regs[1:])]
        hopmax = max([hopmax] + hops)
        stations += sum(x['stations'] for x in xs)
    err = collections.Counter(f['check'] for f in r['findings'] if f['level'] == 'ERROR')
    fb = r['summary'].get('xdie', {}) if isinstance(r['summary'], dict) else {}
    cells = [t.get('cells', 0) for t in raw['partition_types'].values()]
    core_cells = [c.get('cells', 0) for t in raw['partition_types'].values() for c in t.get('contents', [])]
    rows.append(dict(name=name, die_um=[round(W), round(H)], die_mm2=round(W * H / 1e6, 1), partitions=len(raw['partitions']),
                     types=len(raw['partition_types']), lanes=len(P.lanes), lane_bits=int(bits),
                     bits_per_mm2=round(bits / (W * H / 1e6)), bit_mm=round(bitmm), mean_mm_per_bit=round(bitmm / bits, 2),
                     max_hop_um=round(hopmax), max_hop_over_reach=round(hopmax / 1001.0, 3), ft_stations=stations,
                     worst_cut=r['summary'].get('worst_cut'), worst_seg=r['summary'].get('worst_segment'),
                     max_content_cells=max(core_cells) if core_cells else None,
                     g0c_errors=dict(err)))
print(json.dumps(rows, indent=1))
