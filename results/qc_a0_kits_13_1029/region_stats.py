#!/usr/bin/env python3
"""QC-A0-KITS-13 estimate helper: std-cell area/count per plan region from a geom.tsv (geom_dump.tcl format),
plus connectivity of the east-column cells and of the hard children (which macro each region talks to)."""
import sys, json, collections
path = sys.argv[1]
cells = {}; macros = {}; nets = []
for ln in open(path):
    f = ln.rstrip('\n').split('\t')
    if f[0] == 'C':
        cid, kind, master = f[1], f[2], f[3]
        x0, y0, x1, y1 = map(float, f[4:8])
        rec = (kind, master, x0, y0, x1, y1, f[8] if len(f) > 8 else '')
        cells[cid] = rec
        if kind == 'M':
            macros[cid] = rec
    elif f[0] == 'N':
        nets.append(f[1:])
def cen(r): return ((r[2]+r[4])/2, (r[3]+r[5])/2)
def area(r): return (r[4]-r[2])*(r[5]-r[3])
regions = {
 'east_col_upper (x>=388,y>=669.6)': (388.0, 669.6, 453.6, 1153.44),
 'upper_half_all (y>=658)': (4.32, 658.0, 453.6, 1153.44),
 'free_slot (142.152-257.5,673.9-814.3)': (142.152, 673.92, 257.5, 814.32),
 'central_street_lower (195.3-268.3,y<658)': (195.3, 4.32, 268.32, 658.0),
 'west_street_upper (x<16)': (4.32, 658.0, 15.98, 1153.44),
}
out = {}
for rn, (a, b, c, d) in regions.items():
    n = s = 0; ar = 0.0; mac = 0.0
    for cid, r in cells.items():
        x, y = cen(r)
        if a <= x < c and b <= y < d:
            if r[0] == 'M':
                mac += area(r); continue
            n += 1; ar += area(r); s += (r[0] == 'S')
    tot = (c-a)*(d-b)
    out[rn] = dict(cells=n, seq=s, std_area_um2=round(ar, 1), region_um2=round(tot, 1), macro_um2=round(mac, 1),
                   std_util_of_free=round(ar/max(tot-mac, 1e-9), 3))
# macro list
ml = []
for cid, r in macros.items():
    ml.append(dict(id=cid, master=r[1], x0=r[2], y0=r[3], x1=r[4], y1=r[5], name=r[6][-60:]))
out['macros'] = sorted(ml, key=lambda m: (m['master'], m['x0'], m['y0']))
# connectivity of east-column std cells: which macro(s) / regions are their net partners
a, b, c, d = regions['east_col_upper (x>=388,y>=669.6)']
inE = {cid for cid, r in cells.items() if r[0] != 'M' and a <= cen(r)[0] < c and b <= cen(r)[1] < d}
partner = collections.Counter(); pdist = collections.Counter()
for n in nets:
    ids = [t.rstrip('c')[1:] for t in n[1:] if t.startswith('i')]
    if not any(i in inE for i in ids): continue
    for i in ids:
        if i in inE or i not in cells: continue
        r = cells[i]
        if r[0] == 'M': partner[r[1] + '@%.0f,%.0f' % (r[2], r[3])] += 1
        else:
            x, y = cen(r)
            pdist['lower_half' if y < 658 else ('upper_x<142' if x < 142 else ('upper_142-268' if x < 268.32 else 'upper_268-388'))] += 1
out['east_col_partner_macro_pins'] = partner.most_common(20)
out['east_col_partner_cells_by_region'] = dict(pdist)
# nets touching each non-romleaf macro: count + partner centroid
mstat = {}
for mid, r in macros.items():
    if 'romleaf' in r[1]: continue
    cnt = 0; xs = []; ys = []
    for n in nets:
        ids = [t.rstrip('c')[1:] for t in n[1:] if t.startswith('i')]
        if mid not in ids: continue
        cnt += 1
        for i in ids:
            if i != mid and i in cells and cells[i][0] != 'M':
                x, y = cen(cells[i]); xs.append(x); ys.append(y)
    if xs:
        xs.sort(); ys.sort()
        mstat[r[1] + '@%.0f,%.0f' % (r[2], r[3])] = dict(nets=cnt, partner_cells=len(xs), x_med=round(xs[len(xs)//2], 1), y_med=round(ys[len(ys)//2], 1),
            x_p10=round(xs[len(xs)//10], 1), x_p90=round(xs[9*len(xs)//10], 1), y_p10=round(ys[len(ys)//10], 1), y_p90=round(ys[9*len(ys)//10], 1))
out['macro_partners'] = mstat
tot_std = sum(area(r) for r in cells.values() if r[0] != 'M')
out['total_std_area_um2'] = round(tot_std, 1); out['total_std_cells'] = sum(1 for r in cells.values() if r[0] != 'M')
json.dump(out, sys.stdout, indent=1)
