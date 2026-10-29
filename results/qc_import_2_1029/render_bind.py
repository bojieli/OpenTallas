#!/usr/bin/env python3
"""QC-IMPORT-2 GEOM render: provider cells + bound native boundaries (START outputs, local root reset, stage clocks)."""
import json, sys, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pl, g, stg, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), json.load(open(sys.argv[3])), sys.argv[4]
D = pl['dbu']; cells = pl['cells']
st = {s['id']: s for s in stg['stages']}
byport = {s['clock_port']: s for s in stg['stages']}
cen = collections.defaultdict(list)
for c in cells: cen[c['stage']].append(((c['bbox_dbu'][0]+c['bbox_dbu'][2])/2/D, (c['bbox_dbu'][1]+c['bbox_dbu'][3])/2/D))
mid = {k: (sum(x for x, _ in v)/len(v), sum(y for _, y in v)/len(v)) for k, v in cen.items()}
def c(r): return ((r[0]+r[2])/2, (r[1]+r[3])/2)
fig, ax = plt.subplots(1, 3, figsize=(21, 7.5))
a = ax[0]
for n, (m, r) in g['parts'].items(): a.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], facecolor='#eef1f4', edgecolor='#9aa6b0', lw=.3))
a.scatter([p[0] for v in cen.values() for p in v], [p[1] for v in cen.values() for p in v], s=.2, c='#1868b2', label='provider cells (%d)' % len(cells))
dist = []
for e in stg['die_outputs']:
    q = g['start'][e['net']]; s = mid[e['stage']]; t = c(q['xy']); dist.append((abs(s[0]-t[0])+abs(s[1]-t[1]), e['net'], e['stage']))
    a.plot([s[0], t[0]], [s[1], t[1]], '-', color='#dc8d27', lw=.4)
a.plot([], [], '-', color='#dc8d27', label='313 START out -> part cland_tstart_in')
rs = next(iter(g['reset'].values())); rxy = c(rs['xy'])
a.plot(*rxy, 'r*', ms=14, label='local root reset %s/%s' % (rs['inst'], rs['pin']))
b0 = mid['b0']; a.plot(*b0, 'k^', ms=9, label='root stage b0')
a.set(title='Bound source: provider cells + START/reset boundaries', xlabel='um', ylabel='um'); a.set_aspect('equal'); a.legend(fontsize=7, loc='lower left')
# panel 2: reset root zoom
a = ax[1]; x0, y0 = min(rxy[0], b0[0])-60, min(rxy[1], b0[1])-60; x1, y1 = max(rxy[0], b0[0])+60, max(rxy[1], b0[1])+60
for n, (m, r) in g['parts'].items():
    if r[0] < x1 and x0 < r[2] and r[1] < y1 and y0 < r[3]:
        a.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], facecolor='#eef1f4', edgecolor='#9aa6b0', lw=.6)); a.text(max(r[0], x0)+2, max(r[1], y0)+2, n, fontsize=7)
for cl in cells:
    x, y, X, Y = [v/D for v in cl['bbox_dbu']]
    if x < x1 and x0 < X and y < y1 and y0 < Y: a.add_patch(Rectangle((x, y), X-x, Y-y, facecolor='#1868b2' if cl['sequential'] else '#dc8d27', lw=0))
a.plot(*rxy, 'r*', ms=14); a.plot([rxy[0], b0[0]], [rxy[1], b0[1]], 'r--', lw=1)
hop = abs(rxy[0]-b0[0])+abs(rxy[1]-b0[1])
a.set(xlim=(x0, x1), ylim=(y0, y1), title='rst_raw_n -> %s (Manhattan pin->b0 centroid %.1f um)' % (rs['net'], hop), xlabel='um'); a.set_aspect('equal')
# panel 3: clock binding stub lengths + worst START bound
a = ax[2]; L = []
for p, q in g['clock'].items():
    s = byport[p]; t = c(q['xy']); m = mid[s['id']]; L.append(abs(m[0]-t[0])+abs(m[1]-t[1]))
dist.sort(reverse=True)
a.hist(L, bins=60, color='#1868b2', alpha=.8, label='stage centroid -> bound clock driver Y (3,266)')
a.hist([d for d, _, _ in dist], bins=60, color='#dc8d27', alpha=.6, label='START stage centroid -> cland_tstart_in (313)')
a.set(title='max clock %.1f um, max START %.1f um (%s)' % (max(L), dist[0][0], dist[0][1]), xlabel='Manhattan um (centroid, UNCHECKED vs routed)', ylabel='count'); a.legend(fontsize=7)
fig.suptitle('QC-IMPORT-2 preflight READY_FOR_REVIEW: 3,580/3,580 provider ports bound to native nets in source_bound.odb (60d6fc07). Not routed, no timing.')
fig.tight_layout(); fig.savefig(out, dpi=140)
print(json.dumps(dict(max_clock_centroid_um=max(L), max_start_centroid_um=dist[0][0], worst_start=dist[0][1:], reset_hop_um=hop)))
