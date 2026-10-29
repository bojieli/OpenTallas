#!/usr/bin/env python3
"""HEAD-KITS-10 ft A trial (plan COPY only, not a die plan change): face-anchor the last ft stage at the out pin.

For each ft slot of the listed types: k' = max(k, ceil(Lmax/reach)+1) so every inner hop L/(k'-1) <= reach with
station 0 at the in face (kit input pass) and station k'-1 at the out pin (R2 out pin->reg <= 30).
  --mode v1 : bit_sites_um (FIRM per-bit lower-left sites, row/site legal, collision-free per type)
  --mode v2 : regs_um (one point per station; face_flops.tcl spiral-packs the bits around it)
Pins come from the type's generated kit pins.json (same plan pin tables).
usage: ftface.py PLAN_IN PLAN_OUT KITS_DIR --mode v1|v2 --types a,b [--reach 405]
"""
import argparse, json, math, sys
ap = argparse.ArgumentParser()
ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('kits')
ap.add_argument('--mode', choices=('v1', 'v2'), required=True)
ap.add_argument('--types', required=True)
ap.add_argument('--reach', type=float, default=405.0)
ap.add_argument('--with-regs', action='store_true')
ap.add_argument('--margin', type=float, default=4.0, help='um below reach for the inner hop budget (snap slack)')
a = ap.parse_args()
P = json.load(open(a.plan))
SW, RH, C0 = 0.054, 0.27, 4.32
CW, CH = 2.16, 0.27          # per-bit envelope: DFFHQNx1 (1.08) + room for its INV/port buffer
def zroute(ax, ay, bx, by, fin, fout):
    if abs(ax-bx) < 1 or abs(ay-by) < 1: return [(ax, ay), (bx, by)]
    if (fin in 'EW') != (fout in 'EW'):
        return [(ax, ay), (bx, ay), (bx, by)] if fin in 'EW' else [(ax, ay), (ax, by), (bx, by)]
    if fin in 'EW':
        xm = (ax+bx)/2; return [(ax, ay), (xm, ay), (xm, by), (bx, by)]
    ym = (ay+by)/2; return [(ax, ay), (ax, ym), (bx, ym), (bx, by)]
def plen(p): return sum(abs(p[i][0]-p[i+1][0])+abs(p[i][1]-p[i+1][1]) for i in range(len(p)-1))
def at(p, t):
    for i in range(len(p)-1):
        d = abs(p[i][0]-p[i+1][0])+abs(p[i][1]-p[i+1][1])
        if t <= d:
            f = 0 if d == 0 else t/d
            return (p[i][0]+f*(p[i+1][0]-p[i][0]), p[i][1]+f*(p[i+1][1]-p[i][1]))
        t -= d
    return p[-1]
rep = []
for tn in a.types.split(','):
    T = P['partition_types'][tn]
    W, H = T['outline_um']; x1, y1 = W-C0, H-C0
    ncol = int((x1-C0-CW)/CW)+1; nrow = int((y1-C0)/RH)
    pins = json.load(open(f"{a.kits}/{tn}/pins.json"))
    PIN = {(p['bus'], p['bit']): (p['x'], p['y']) for p in pins}
    occ = set()
    # keep-out: kit input pass face flops (cols 0..3 inward, rows +-2 around every input pin) so FIRM sites never overlap
    def cell(x, y):
        return (min(max(int(round((x-C0)/CW)), 0), ncol-1), min(max(int(round((y-C0)/RH)), 0), nrow-1))
    for (b, i), (x, y) in PIN.items():
        if not b.endswith('_i'): continue
        c, r = cell(min(max(x, C0), x1-CW), min(max(y, C0), y1-RH))
        for dc in range(-3, 4):
            for dr in range(-2, 3): occ.add((c+dc, r+dr))
    def put(x, y):
        c0, r0 = cell(min(max(x-CW/2, C0), x1-CW), min(max(y-RH/2, C0), y1-RH))
        for rad in range(400):
            for dr in range(-rad, rad+1):
                for dc in {rad-abs(dr), abs(dr)-rad}:
                    c, r = c0+dc, r0+dr
                    if 0 <= c < ncol and 0 <= r < nrow and (c, r) not in occ:
                        occ.add((c, r)); return (round(C0+c*CW, 4), round(C0+r*RH, 4))
        raise SystemExit(f'no site {tn} {x} {y}')
    for s in T['ft_slots']:
        n, k, fi, fo, w = s['name'], s['stations'], s['in_face'], s['out_face'], s['width']
        routes = []
        for b in range(w+1):
            ax, ay = PIN[(n+'_i', b)]; bx, by = PIN[(n+'_o', b)]
            routes.append(zroute(ax, ay, bx, by, fi, fo))
        Lmax = max(plen(r) for r in routes)
        k2 = max(k, math.ceil(Lmax/(a.reach-a.margin))+1)
        s['stations'] = k2
        s.pop('regs_um', None); s.pop('bit_sites_um', None); s.pop('bit_site_cell_um', None)
        if a.mode == 'v1':
            st = []
            for j in range(1, k2):
                st.append([list(put(*at(r, plen(r)*j/(k2-1)))) for r in routes])
            s['bit_sites_um'] = st; s['bit_site_cell_um'] = [CW, CH]
            if a.with_regs:   # station-level points too, so gen's clock tap planner sees the new station columns
                r0 = routes[w//2]; L0 = plen(r0)
                s['regs_um'] = [[round(v, 3) for v in at(r0, L0*j/(k2-1))] for j in range(k2)]
            # per-bit hop check (lower-left + half envelope vs pins), Manhattan
            def ctr(xy): return (xy[0]+0.54, xy[1]+RH/2)
            hops = []; pr = []
            for b, r in enumerate(routes):
                seq = [r[0]] + [ctr(st[j][b]) for j in range(k2-1)]
                hops += [abs(seq[i][0]-seq[i+1][0])+abs(seq[i][1]-seq[i+1][1]) for i in range(len(seq)-1)]
                last = ctr(st[-1][b]); pr.append(abs(last[0]-r[-1][0])+abs(last[1]-r[-1][1]))
            pr.sort()
            rep.append(dict(type=tn, slot=n, k=k, k_new=k2, L_max=round(Lmax, 1), hop_max=round(max(hops), 1),
                            out_pinreg_p90=round(pr[int(.9*(len(pr)-1))], 1), out_pinreg_max=round(pr[-1], 1)))
        else:
            r0 = routes[w//2]; L = plen(r0)
            s['regs_um'] = [list(map(lambda v: round(v, 3), at(r0, L*j/(k2-1)))) for j in range(k2)]
            # pull the last point 1 um inside the core so the spiral starts at the face column
            lx, ly = s['regs_um'][-1]; s['regs_um'][-1] = [min(max(lx, C0+1), x1-CW-1), min(max(ly, C0+1), y1-1)]
            rep.append(dict(type=tn, slot=n, k=k, k_new=k2, L_max=round(Lmax, 1), hop_mid=round(L/(k2-1), 1)))
    T['note'] = T.get('note', '') + f' | HEAD-KITS-10 TRIAL ft A {a.mode}: last stage face-anchored at the out pin, stations k->k\' (plan copy only)'
json.dump(P, open(a.out, 'w'), indent=1)
for r in rep: print(json.dumps(r))
