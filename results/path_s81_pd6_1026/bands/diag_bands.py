#!/usr/bin/env python3
"""PATH-S81-PD6: diagnose clock-landing storage-band placement failures (read-only).
usage: diag_bands.py WT PLAN_PRE SIDE LANDED OUT_JSON [PNG_DIR]"""
import json, sys, math
wt, plan, sidep, landedp, outp = sys.argv[1:6]; pngd = sys.argv[6] if len(sys.argv) > 6 else None
sys.path.insert(0, wt + '/tools/die_plan')
import numpy as np, schema as S, reset_tree as RT, clock_landing_plan as CLP
raw = json.load(open(plan)); side = json.load(open(sidep)); tab = json.load(open(landedp))
col = side['collector']; res = []
widths = {}
P = S.Plan(raw, plan)
for r in tab['ports']:
    pr = next(p for p in raw['ports'] if p['id'] == r['port']) if False else None
pid = {p['id']: p for p in raw['ports']}
for r in tab['ports']:
    p = pid[r['port']]; tn = P.parts[r['dst']]['type']
    widths.setdefault((tn, p['dst']['bus']), int(r.get('width', p.get('width', 1))))
for f in col['placement_failures']:
    tn, bus = f['type'], f['bus']; t = json.loads(json.dumps(raw['partition_types'][tn]))
    info = col['types'][tn]; t['_cland_geom'] = info.get('bus_geometry', {})
    b = CLP._bus_geom(t, bus); w, h = t['outline_um']; lo, hi = b['window_um']
    width = widths.get((tn, bus), 0) + (2 if col.get('monitor') == 'dataflow' else 0)
    length = max(hi - lo, 8.64); rw = 64 * math.ceil((width + 1) / 64)
    area = (5*rw*.2916 + 4*rw*.0729 + 160*.2916)/.40; depth = math.ceil(max(8.64, area/length)/2.16)*2.16
    used = [bd['rect_um'] for k, bd in info['bands'].items() if bd.get('rect_um')]
    blk = RT.blockages(t)
    ft = []
    for slot in t.get('ft_slots', []):
        cell = slot.get('bit_site_cell_um', [1.404, .27])
        for st in slot.get('bit_sites_um', []):
            if st: ft.append([min(p[0] for p in st)-cell[0]/2, min(p[1] for p in st)-cell[1]/2, max(p[0] for p in st)+cell[0]/2, max(p[1] for p in st)+cell[1]/2])
        if not slot.get('bit_sites_um'): ft += [[x-2.16, y-2.16, x+2.16, y+2.16] for x, y in slot.get('regs_um', [])]
    px, py = CLP._bus_xy(t, bus); g = 2.16; nx, ny = int(w//g), int(h//g)
    def occ(obs):
        o = np.zeros((nx, ny), bool)
        for r in obs:
            i0, i1 = max(0, int(r[0]//g)), min(nx, int(math.ceil(r[2]/g))); j0, j1 = max(0, int(r[1]//g)), min(ny, int(math.ceil(r[3]/g)))
            if i1 > i0 and j1 > j0: o[i0:i1, j0:j1] = True
        m = 8; o[:m] = o[-m:] = True; o[:, :m] = o[:, -m:] = True
        return o
    X, Y = np.meshgrid((np.arange(nx)+.5)*g, (np.arange(ny)+.5)*g, indexing='ij')
    reach = (abs(X-px)+abs(Y-py)) <= 403
    def free(obs): return round(float(((~occ(obs)) & reach).sum()*g*g), 1)
    rec = dict(type=tn, bus=bus, face=b['face'], window=[lo, hi], pin=[round(px,2), round(py,2)], outline=[w, h],
               width=width, ring_width=rw, area_need_um2=round(area,1), depth=depth, length=round(length,2),
               n_macro_blk=len(blk), n_ft=len(ft), n_used=len(used),
               free_in_reach_no_obs=free([]), free_minus_macros=free(blk), free_minus_macros_ft=free(blk+ft),
               free_minus_all=free(blk+ft+used), hard=bool(t.get('hard')),
               instances=sorted(pn for pn, p in P.parts.items() if p['type'] == tn)[:4])
    res.append(rec); print(json.dumps(rec))
    if pngd:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
        fig, ax = plt.subplots(figsize=(7, 7*h/w if w > h else 7))
        ax.add_patch(Rectangle((0,0), w, h, fill=False))
        for r in blk: ax.add_patch(Rectangle((r[0],r[1]), r[2]-r[0], r[3]-r[1], color='grey', alpha=.6))
        for r in ft: ax.add_patch(Rectangle((r[0],r[1]), r[2]-r[0], r[3]-r[1], color='orange', alpha=.6))
        for r in used: ax.add_patch(Rectangle((r[0],r[1]), r[2]-r[0], r[3]-r[1], color='blue', alpha=.5))
        ax.plot([px],[py],'r*',ms=14)
        dd = np.array([[px-403,py],[px,py+403],[px+403,py],[px,py-403],[px-403,py]]); ax.plot(dd[:,0],dd[:,1],'r--',lw=.8)
        ax.set_xlim(0,w); ax.set_ylim(0,h); ax.set_aspect('equal'); ax.set_title(f"{tn} {bus} need {area:.0f}um2 free {rec['free_minus_all']}")
        fig.savefig(f"{pngd}/{tn}__{bus}.png", dpi=80); plt.close(fig)
json.dump(res, open(outp, 'w'), indent=1)
