#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v: core clock regions (OWNER 11-03: one clock entry per <= 5k sinks; DIE-HBM-61/CLOCK).
    python3 mk_clkreg.py PLAN_DIR GEOMCOLL.json [--keep MOD ...]  -> PLAN_DIR/core_clock_regions.json
Per hard-core module with N > 5000 clock sinks (d44o AUTO-GEOM clock_sinks): n = ceil(N/5000) regional clock entries on an
r x c grid of the core outline (r*c >= n, tiles closest to square), entry = tile centre on the 4.32 lattice, moved to the
nearest lattice point >= 4.32 um off every macro (12.8a); the plan centre entry (clock_entries.json) stays the root pin
that feeds the regional entries (kit/gen support: DIE-HBM-61/CLOCK).  Kept (signed) modules are listed, never changed."""
import json, math, sys
from pathlib import Path
pd = Path(sys.argv[1]); G = json.load(open(sys.argv[2]))
keep = set(sys.argv[sys.argv.index('--keep') + 1:]) if '--keep' in sys.argv else set()
P = json.loads((pd / 'die_plan.json').read_text()); CM = json.loads((pd / 'core_macros.json').read_text())['cores']
Q, LIM = 4.32, 5000
mods = {}
for tn, t in P['partition_types'].items():
    for h in t.get('hard_cores') or []:
        mods.setdefault(h['module'], dict(outline=h['outline_um'], inst=0))['inst'] += 1
out, nodata = {}, []
for m, d in sorted(mods.items()):
    g = (G.get(m) or {}).get('metrics') or {}
    N = g.get('clock_sinks')
    if N is None: nodata.append(m); continue
    if N <= LIM: continue
    W, H = d['outline']; n = math.ceil(N / LIM)
    best = None
    for r in range(1, n + 1):
        c = math.ceil(n / r); sc = (r * c - n, abs(math.log((W / c) / (H / r))))
        if best is None or sc < best[0]: best = (sc, r, c)
    _, r, c = best
    mac = (CM.get(m) or {}).get('macros') or []
    def free(x, y): return all(not (a - Q < x < b + Q and e - Q < y < f + Q) for a, e, b, f in (q['rect_um'] for q in mac))
    ents = []
    for i in range(r):
        for j in range(c):
            if len(ents) >= n: break
            x, y = W * (j + .5) / c, H * (i + .5) / r
            cand = sorted(((round(round(x / Q) * Q + dx * Q, 3), round(round(y / Q) * Q + dy * Q, 3)) for dx in range(-30, 31) for dy in range(-30, 31)),
                          key=lambda p: abs(p[0] - x) + abs(p[1] - y))
            p = next((p for p in cand if Q <= p[0] <= W - Q and Q <= p[1] <= H - Q and free(*p)), None)
            if p is None:      # part 2: region centre window all macro -> nearest free lattice point in the core (CLOCK 11-03: 1 unsited)
                cand = sorted(((round(a * Q, 3), round(b * Q, 3)) for a in range(1, int(W / Q)) for b in range(1, int(H / Q))),
                              key=lambda p: abs(p[0] - x) + abs(p[1] - y))
                p = next((p for p in cand if free(*p)), None)
            ents.append(dict(xy_um=list(p) if p else None, region_um=[round(W * j / c, 3), round(H * i / r, 3), round(W * (j + 1) / c, 3), round(H * (i + 1) / r, 3)]))
    out[m] = dict(sinks=N, entries=n, grid=[r, c], outline_um=[W, H], instances=d['inst'], kept_signed=m in keep,
                  sinks_per_entry=math.ceil(N / n), regional_entries=ents)
rep = dict(schema='opentallas.hbm_core_clock_regions.v1', rule='one clock entry per <= 5000 sinks (OWNER 11-03)',
           source='d44o AUTO-GEOM clock_sinks (latest attempt)', modules=out, no_sink_data=nodata,
           totals=dict(modules=len(out), entries=sum(v['entries'] for v in out.values()),
                       slots=sum(v['instances'] for v in out.values()), kept_signed=sorted(m for m in out if m in keep)))
(pd / 'core_clock_regions.json').write_text(json.dumps(rep, indent=1))
print(json.dumps(rep['totals']), 'no data', len(nodata))
