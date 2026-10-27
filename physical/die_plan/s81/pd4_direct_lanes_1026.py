#!/usr/bin/env python3
"""PATH-S81-PD4: replace the PHY-fit ft_phy feedthrough chains with direct lanes (B5 style).

Input: the PD2 B2 candidate plan (PHY-fit rects, published PHY sizes) + the routed-GRT0 B5 plan.
For every lane the PHY-fit tool re-routed (ports '*__phy1026_*'), all ft_phy slots and their ports are
removed and the lane is re-routed over abutting partitions with:
  * the B5 route preferred hop by hop (B5 = GRT0 reference);
  * NO transit through svc_* partitions unless B5 itself transited that svc for that lane
    (svc row seams carried the 2.24M g0fix overflow, PATH-S81-PD3);
  * SerDes lk_* partitions allowed as transits again (B5 ft in lk = 19,494 bits) but only through
    their core strip: E/W windows clipped to the strip outside the published PHY macro keepout,
    stations later placed off the keepout (published PHY sizes unchanged);
  * per-seam load model: bits / tracks (seam span x sum 1/pitch on the two face layers) -- a hop whose
    seam would exceed --seam-max is refused, above --seam-soft it is penalised;
  * phy_hbm never a transit, frame fW/fE transits only in their end rows (as the PHY-fit tool) x4 cost.
Window allocation and slot/port emission follow apply_phyfit_routes_1026.py (same face rules, same
station count formula) so downstream station placement / G0 / G0C tools apply unchanged.
"""
import argparse, collections, copy, heapq, json, math, re, sys
from pathlib import Path

OPP = dict(N='S', S='N', E='W', W='E')


def edge(a, b):
    if abs(a[2]-b[0]) < 1e-3: return 'E', [max(a[1], b[1]), min(a[3], b[3])]
    if abs(b[2]-a[0]) < 1e-3: return 'W', [max(a[1], b[1]), min(a[3], b[3])]
    if abs(a[3]-b[1]) < 1e-3: return 'N', [max(a[0], b[0]), min(a[2], b[2])]
    if abs(b[3]-a[1]) < 1e-3: return 'S', [max(a[0], b[0]), min(a[2], b[2])]
    raise ValueError('non-abutting')


def local_geom(part, rect, face, window):
    orient = part.get('orient', 'R0'); fx = orient in ('MY', 'R180'); fy = orient in ('MX', 'R180')
    w, h = rect[2]-rect[0], rect[3]-rect[1]
    lf = OPP[face] if (face in 'EW' and fx) or (face in 'NS' and fy) else face
    base = rect[0] if face in 'NS' else rect[1]; extent = w if face in 'NS' else h
    flip = fx if face in 'NS' else fy
    win = [extent-(v-base) if flip else v-base for v in window]
    return lf, sorted(round(v, 6) for v in win), 'lsb_high' if flip else 'lsb_low'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path); ap.add_argument('--plan', required=True, type=Path)
    ap.add_argument('--b5', required=True, type=Path); ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--report', required=True, type=Path)
    ap.add_argument('--prefix', default='ft_dl'); ap.add_argument('--b5-bonus', type=float, default=0.6)
    ap.add_argument('--seam-soft', type=float, default=0.45); ap.add_argument('--seam-max', type=float, default=0.55)
    ap.add_argument('--bits-per-um', type=float, default=4.6)
    a = ap.parse_args()
    sys.path.insert(0, str(a.root)); from tools.die_plan import schema as S
    raw = json.loads(a.plan.read_text()); b5 = json.loads(a.b5.read_text())
    model = S.Plan(raw, a.plan); ports = model.ports; layers = model.layers
    parts = {p['name']: p for p in raw['partitions']}; types = raw['partition_types']
    rect = {}
    for n, p in parts.items():
        w, h = types[p['type']]['outline_um']; o = p['origin_um']; rect[n] = [o[0], o[1], o[0]+w, o[1]+h]
    # --- lanes to re-route: every lane carrying a PHY-fit port
    lanes = {l['id']: l for l in raw['lanes']}
    affected = sorted(l for l, v in lanes.items() if any('__phy1026_' in pid for pid in v['ports']))
    b5ports = {p['id']: p for p in b5['ports']}; b5lanes = {l['id']: l for l in b5['lanes']}
    b5route = {}
    for lid in affected:
        ps = [b5ports[x] for x in b5lanes[lid]['ports']]
        b5route[lid] = [ps[0]['src']['part']]+[p['dst']['part'] for p in ps]
    b5edges = {lid: {frozenset(e) for e in zip(r, r[1:])} for lid, r in b5route.items()}
    removed = {pid for lid in affected for pid in lanes[lid]['ports']}
    endpoint = {}
    for lid in affected:
        pids = lanes[lid]['ports']; endpoint[lid] = (copy.deepcopy(ports[pids[0]]['src']), copy.deepcopy(ports[pids[-1]]['dst']),
                                                     ports[pids[0]]['width'], ports[pids[0]].get('kind', 'data'))
    # --- strip every old ft_phy slot (all of them belong to the affected lanes)
    old_phy = collections.Counter(); old_phy_bits = 0
    for n, p in parts.items():
        t = types[p['type']]; keep = []
        for s in t.get('ft_slots', []):
            if s['name'].startswith('ft_phy'): old_phy[n] += 1; old_phy_bits += s['width']
            else: keep.append(s)
        t['ft_slots'] = keep
    for n, p in parts.items():      # bus entries of removed slots
        t = types[p['type']]
        t['buses'] = [b for b in t.get('buses', []) if not re.match(r'ft_phy\d+_[io]$', b['name'])]
    # --- lk strip: allowed E/W face interval (die coords) outside the PHY keepout
    allowed = {}
    for n, p in parts.items():
        if not n.startswith('lk_'): continue
        t = types[p['type']]; ko = t['clock'].get('keepouts_um', [])
        w, h = t['outline_um']; fy = p.get('orient', 'R0') in ('MX', 'R180')
        ylo, yhi = 0.0, h
        for k in ko:            # keepout spans full width -> strip is the complement in y (type frame)
            if k[1] <= 1e-3: ylo = max(ylo, k[3])
            else: yhi = min(yhi, k[1])
        y0, y1 = (h-yhi, h-ylo) if fy else (ylo, yhi)
        r = rect[n]; iv = (r[1]+y0+8.64, r[1]+y1-8.64)
        allowed[(n, 'E')] = allowed[(n, 'W')] = iv
    def face_layers(fa): return ['M7', 'M5'] if fa in 'NS' else ['M6', 'M4']
    def tracks_per_um(fa): return sum(1.0/layers[L]['pitch_um'] for L in face_layers(fa) if L in layers)
    occupied = collections.defaultdict(list); seam_bits = collections.Counter()
    for p in ports.values():
        if p['id'] in removed: continue
        fa = p['face']; lo, hi = sorted(p['window_um'])
        occupied[(p['src']['part'], fa)].append((lo-2, hi+2)); occupied[(p['dst']['part'], OPP[fa])].append((lo-2, hi+2))
        seam_bits[frozenset((p['src']['part'], p['dst']['part']))] += p['width']
    seam_span = {}
    neighbours = {n: [] for n in rect}; names = sorted(rect)
    # spatial bucketing to avoid O(n^2) over 398 partitions (cheap anyway)
    for i, na in enumerate(names):
        for nb in names[i+1:]:
            try: fa, span = edge(rect[na], rect[nb])
            except ValueError: continue
            if span[1]-span[0] > 12:
                neighbours[na].append((nb, fa)); neighbours[nb].append((na, OPP[fa]))
                seam_span[frozenset((na, nb))] = (fa, span)
    def seam_ratio(na, nb, extra=0):
        fa, span = seam_span[frozenset((na, nb))]
        return (seam_bits[frozenset((na, nb))]+extra)/max(1e-9, (span[1]-span[0])*tracks_per_um(fa))
    def allocate(na, nb, width, commit=True):
        fa, (lo, hi) = edge(rect[na], rect[nb])
        for key in ((na, fa), (nb, OPP[fa])):
            if key in allowed: lo, hi = max(lo, allowed[key][0]), min(hi, allowed[key][1])
        length = max(17.28, (width+1)/a.bits_per_um)
        intervals = sorted(occupied[(na, fa)]+occupied[(nb, OPP[fa])]); at = lo+6.144
        for left, right in intervals:
            if right <= at: continue
            if left-at >= length+2: break
            at = max(at, right)
        if at+length > hi-6.144: raise ValueError(f'WINDOW_EXHAUSTED {na}/{fa}|{nb} {width}')
        win = [round(at, 6), round(at+length, 6)]
        if commit:
            occupied[(na, fa)].append((at-2, at+length+2)); occupied[(nb, OPP[fa])].append((at-2, at+length+2))
            seam_bits[frozenset((na, nb))] += width
        return fa, win
    FRAME_ROW = lambda n: rect[n][1] <= 103.68+1226.88+.01 or rect[n][3] >= 103.68+19*1226.88-.01
    def select_path(lid, src, dst, width):
        heap = [(0.0, src, '')]; dist = {(src, ''): 0.0}; prev = {}; end = None
        okb5 = set(b5route[lid])
        while heap:
            cost, n, inface = heapq.heappop(heap); state = (n, inface)
            if cost != dist[state]: continue
            if n == dst: end = state; break
            for nxt, face in neighbours[n]:
                if face == inface: continue
                if nxt != dst:
                    if nxt == 'phy_hbm': continue
                    if nxt.startswith('svc_') and nxt not in okb5: continue
                    if nxt.startswith(('fW', 'fE')) and not FRAME_ROW(nxt): continue
                r = seam_ratio(n, nxt, width)
                if r > a.seam_max: continue
                try: allocate(n, nxt, width, False)
                except ValueError: continue
                ar, br = rect[n], rect[nxt]
                step = abs((ar[0]+ar[2]-br[0]-br[2])/2)+abs((ar[1]+ar[3]-br[1]-br[3])/2)
                m = 4.0 if (n.startswith(('fW', 'fE')) or nxt.startswith(('fW', 'fE'))) else 1.0
                if frozenset((n, nxt)) in b5edges[lid]: m *= a.b5_bonus
                if r > a.seam_soft: m *= 1+10*(r-a.seam_soft)
                nc = cost+step*m; ns = (nxt, OPP[face])
                if nc < dist.get(ns, math.inf): dist[ns] = nc; prev[ns] = state; heapq.heappush(heap, (nc, *ns))
        if end is None: raise ValueError(f'NO_ROUTE {lid} {src}->{dst} w{width}')
        path = [end[0]]
        while end != (src, ''): end = prev[end]; path.append(end[0])
        return path[::-1]
    slot_counts = collections.Counter(); newports = []; newslots = collections.defaultdict(list); rows = []
    for lid in sorted(affected, key=lambda z: (-endpoint[z][2], z)):
        source, dest, width, kind = endpoint[lid]
        path = select_path(lid, source['part'], dest['part'], width)
        nm = {}
        for n in path[1:-1]:
            nm[n] = a.prefix+str(slot_counts[n]); slot_counts[n] += 1
        edges = []
        for i, (na, nb) in enumerate(zip(path, path[1:])):
            fa, win = allocate(na, nb, width)
            src = source if i == 0 else dict(part=na, bus=nm[na]+'_o'); dst = dest if i == len(path)-2 else dict(part=nb, bus=nm[nb]+'_i')
            L = face_layers(fa)
            p = dict(id=f'{lid}__pd4_{i}', src=src, dst=dst, width=width, kind=kind, face=fa, layers=L, window_um=win, order='lsb_low')
            newports.append(p); edges.append(p)
            for ep, wf in ((src, fa), (dst, OPP[fa])):
                t = types[parts[ep['part']]['type']]; lf, lwin, order = local_geom(parts[ep['part']], rect[ep['part']], wf, win)
                bus = next((b for b in t.get('buses', []) if b['name'] == ep['bus']), None)
                if bus is not None: bus.update(face=lf, window_um=lwin, layers=L, order=order)
        for i, n in enumerate(path[1:-1], 1):
            inc, out = edges[i-1], edges[i]; fin = OPP[inc['face']]; fout = out['face']
            if fin == fout: raise ValueError(f'SAME_FACE_TRANSIT {lid} {n}')
            lf, wi, order = local_geom(parts[n], rect[n], fin, inc['window_um']); lo, wo, _ = local_geom(parts[n], rect[n], fout, out['window_um'])
            t = types[parts[n]['type']]; w, h = t['outline_um']
            pt = lambda f, wv: {'N': (sum(wv)/2, h), 'S': (sum(wv)/2, 0), 'W': (0, sum(wv)/2), 'E': (w, sum(wv)/2)}[f]
            aa, bb = pt(lf, wi), pt(lo, wo); d = abs(aa[0]-bb[0])+abs(aa[1]-bb[1])
            cnt = max(1, math.ceil((d+max(wi[1]-wi[0], wo[1]-wo[0]))/(405*.98)))
            slot = dict(name=nm[n], in_face=lf, out_face=lo, width=width, stations=cnt, in_window_um=wi, out_window_um=wo, order=order)
            t['ft_slots'].append(slot); newslots[parts[n]['type']].append(slot['name'])
        lanes[lid]['ports'] = [p['id'] for p in edges]
        bm = sum(abs((rect[x][0]+rect[x][2]-rect[y][0]-rect[y][2])/2)+abs((rect[x][1]+rect[x][3]-rect[y][1]-rect[y][3])/2) for x, y in zip(path, path[1:]))
        rows.append(dict(lane=lid, width=width, parts=path, transits=len(path)-2, b5_transits=len(b5route[lid])-2,
                         b5_same=path == b5route[lid], ft_bits=width*(len(path)-2), centre_mm=round(bm/1000, 3),
                         svc_transits=[n for n in path[1:-1] if n.startswith('svc_')], lk_transits=[n for n in path[1:-1] if n.startswith('lk_')]))
    raw['ports'] = [p for p in raw['ports'] if p['id'] not in removed]+newports
    # one type per instance holds; refuse a shared type receiving instance-specific slots
    tcount = collections.Counter(p['type'] for p in raw['partitions'])
    shared = sorted(tn for tn in newslots if tcount[tn] > 1)
    if shared: raise ValueError(f'new slots on shared types {shared}')
    # per-seam report over the whole plan (all ports)
    seam = []
    for k, b in seam_bits.items():
        if k not in seam_span: continue
        na, nb = sorted(k); fa, span = seam_span[k]; tr = (span[1]-span[0])*tracks_per_um(fa)
        seam.append(dict(a=na, b=nb, face=fa, bits=b, tracks=round(tr), ratio=round(b/tr, 4)))
    seam.sort(key=lambda r: -r['ratio'])
    newbits = sum(r['ft_bits'] for r in rows)
    rep = dict(status='PD4 DIRECT-LANE PLAN (stations/G0/G0C pending)', lanes=len(rows), new_slots=dict(newslots),
               old_ft_phy=dict(slots=sum(old_phy.values()), bits=old_phy_bits, parts=len(old_phy)),
               new_ft=dict(slots=sum(len(v) for v in newslots.values()), bits=newbits, parts=len(newslots)),
               b5_equiv_ft_bits=sum(endpoint[l][2]*(len(b5route[l])-2) for l in affected),
               same_as_b5=sum(r['b5_same'] for r in rows), svc_transit_lanes=[r['lane'] for r in rows if r['svc_transits']],
               lk_ft_bits=sum(r['width']*len(r['lk_transits']) for r in rows),
               seam_max=seam[:15], seams_over=dict(soft=sum(r['ratio'] > a.seam_soft for r in seam), max=sum(r['ratio'] > a.seam_max for r in seam)),
               routes=rows, params=vars(a) | {'root': str(a.root), 'plan': str(a.plan), 'b5': str(a.b5), 'out': str(a.out), 'report': str(a.report)})
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(raw, separators=(',', ':'))+'\n')
    a.report.write_text(json.dumps(rep, indent=1)+'\n')
    print(json.dumps({k: rep[k] for k in ('lanes', 'old_ft_phy', 'new_ft', 'b5_equiv_ft_bits', 'same_as_b5', 'svc_transit_lanes', 'lk_ft_bits', 'seams_over')}, indent=1))
    print('seam top', seam[:5])


if __name__ == '__main__':
    main()
