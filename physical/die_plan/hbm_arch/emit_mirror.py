"""HBM-ARCH B2 router: NE = MY mirror of NW (COORD 10-23 review item 5), 3-layer endpoint faces where the M8/M9 ft
budget allows (item 1), margins face <= FACE_MAX, ft (transit + die-layer face pins) <= FT_MAX of the budget.

Primary lanes (src in NW, or src die-level and dst in NW) are routed; their mirror (partition NW_x <-> NE_x, die-level
partitions fixed) is emitted with the same slot / bus names in shared types, 'm'-suffixed names in die-level ones.
Die-level <-> die-level lanes are routed once and may only cross die-level partitions (keeps the tiles symmetric).
Windows: first-fit per shared segment; every allocation on a tile segment is mirrored onto its mirror segment, so the
two stay mirror images and the mirrored ports (bit order lsb_high on N/S faces) give one pin table per tile master."""
import collections, math
import schema as S

FACE_MAX = 0.75
FT_MAX = 0.80


def mir(n):
    return 'NE_' + n[3:] if n.startswith('NW_') else 'NW_' + n[3:] if n.startswith('NE_') else n


def single(n):
    return mir(n) == n


def window_sym(lo, n, lay, LAYERS, per_um):
    """window_for + mirror-equivariant pick: no layer with an odd pin count on an even usable-track count."""
    hi = S.window_for(lo, n, lay, LAYERS, per_um=per_um, track_max=0.6)
    nl = len(lay)
    need = [len(range(i, n, nl)) for i in range(nl)]
    for _ in range(400):
        if all(not (k % 2 == 1 and S.usable_tracks(LAYERS[ln], ln, lo, hi) % 2 == 0) for ln, k in zip(lay, need)):
            return round(hi, 4)
        hi += 0.016
    return round(hi, 4)


def emit_mirror(T, bundles, G, u, adjacency, shortest, plen, OPPF, HL, VL, LAYERS, FT_UM, LANE_MAX, DETOUR, REACH, reserve=None):
    P = T['parts']
    R, adj = adjacency(P)
    Wd = u(T['W'])
    hard = {n for n, p in P.items() if p['kind'] in ('sm', 'phy')}
    quadp = {n for n in P if not single(n)}
    l3 = T['V'].get('l3')
    errs, unrouted = [], []
    # ---- primary bundles
    items = []
    for (a, b, kd), w in bundles.items():
        mb = (mir(a), mir(b), kd)
        if mb == (a, b, kd):
            role = 'die'
        elif a.startswith('NW_') or (single(a) and b.startswith('NW_')):
            role = 'pri'
            if bundles.get(mb) != w:
                errs.append(f'asymmetric bundle {a}->{b} {w} vs mirror {bundles.get(mb)}')
        else:
            continue
        n = max(1, math.ceil(w / LANE_MAX))
        for j in range(n):
            items.append(((a, b, kd), w // n + (1 if j < w % n else 0), role))
    items.sort(key=lambda x: (-x[1], x[0]))

    def contact(n, m):
        f, lo, hi = adj[n][m]
        return hi - lo - 4.0

    def tdirs(fin, fout):
        if fin is None:
            return ()
        if fin in 'EW' and fout in 'EW':
            return ('H',)
        if fin in 'NS' and fout in 'NS':
            return ('V',)
        return ('H', 'V')

    def ext(n, d):
        x0, y0, x1, y1 = R[n]
        return (y1 - y0) if d == 'H' else (x1 - x0)

    fcap_um = (8.8 if l3 else 5.8) * FACE_MAX * 0.9
    pinl = collections.defaultdict(float)
    clk = collections.defaultdict(float, reserve or {})     # clock spine tracks (owner 10-23 MSCTS H-tree)

    hist = collections.defaultdict(float)     # PathFinder history cost of over-used resources

    def route_all():
        use = collections.defaultdict(float)
        tuse = collections.defaultdict(float)

        def ecost(n, m, fin=None, fout=None):
            k = tuple(sorted((n, m)))
            c = contact(n, m) * fcap_um
            x = use[k] / c if c > 0 else 9.0
            hc = hist[('e', k)]
            for d in tdirs(fin, fout):
                tc = FT_UM * ext(n, d) * FT_MAX - pinl[(n, d)] - clk[(n, d)]
                x = max(x, tuse[(n, d)] / tc if tc > 0 else 9.0)
                hc += hist[('t', n, d)]
            return 400.0 * x * x + (4000.0 if x > 0.85 else 0.0) + (40000.0 * (x - 1.0) if x > 1.0 else 0.0) + hc
        lanes = []
        for (a, b, kd), w, role in items:
            blk = hard | (quadp if role == 'die' else set())
            base = shortest(R, adj, P, a, b, blk)
            path = shortest(R, adj, P, a, b, blk, ecost)
            if path is None:
                path = base
            if path is None:
                unrouted.append((a, b, kd, w))
                continue
            paths = [path] + ([[mir(x) for x in path]] if role == 'pri' else [])
            for pth in paths:
                for x, y in zip(pth, pth[1:]):
                    if y not in adj[x]:
                        errs.append(f'mirror path broken {pth}')
                        break
                    use[tuple(sorted((x, y)))] += w + 1
                for h in range(1, len(pth) - 1):
                    fi = OPPF[adj[pth[h - 1]][pth[h]][0]]
                    fo = adj[pth[h]][pth[h + 1]][0]
                    for d in tdirs(fi, fo):
                        tuse[(pth[h], d)] += w
            lanes.append(dict(src=a, dst=b, kind=kd, width=int(w), path=path, role=role))
        return lanes, use, tuse

    for it in range(16):
        unrouted.clear()
        lanes, use, tuse = route_all()
        hov = 0
        for k, v in use.items():
            c = contact(*k) * fcap_um
            if v > c:
                hist[('e', k)] += 3000.0 * (v / c - 1.0) + 500.0; hov += 1
        for (n, d), v in tuse.items():
            tc = FT_UM * ext(n, d) * FT_MAX - pinl[(n, d)] - clk[(n, d)]
            if v > tc:
                hist[('t', n, d)] += 3000.0 * (v / max(tc, 1.0) - 1.0) + 500.0; hov += 1
        # endpoint layer choice per (lane, hop): on a segment whose 2-layer windows would pass FACE_MAX, the widest
        # endpoint ports move to 3 layers until the segment fits (fewest M8 / M9 endpoint pins: they cost ft budget)
        seg_hops = collections.defaultdict(list)
        for li, L in enumerate(lanes):
            pths = [L['path']] + ([[mir(x) for x in L['path']]] if L['role'] == 'pri' else [])
            for mi, pth in enumerate(pths):
                for h in range(len(pth) - 1):
                    seg_hops[tuple(sorted((pth[h], pth[h + 1])))].append((li, mi, h, 0 < h < len(pth) - 2, L['width'] + 1))
        need3 = set()
        for k, hops in seg_hops.items():
            c = max(contact(*k), 1.0)
            occ_ = sum(n / (8.8 if tr else 5.8) + 0.6 for _, _, _, tr, n in hops)
            for li, mi, h, tr, n in sorted(hops, key=lambda x: -x[4]):
                if occ_ <= FACE_MAX * 0.92 * c or not l3:
                    break
                if tr:
                    continue
                need3.add((li, h))
                occ_ -= n / 5.8 - n / 8.8
        pins3 = collections.defaultdict(float)
        for li, L in enumerate(lanes):
            pths = [L['path']] + ([[mir(x) for x in L['path']]] if L['role'] == 'pri' else [])
            for pth in pths:
                for h in range(len(pth) - 1):
                    if (li, h) not in need3 or 0 < h < len(pth) - 2:
                        continue
                    a, b = pth[h], pth[h + 1]
                    f = adj[a][b][0]
                    d = 'H' if f in 'EW' else 'V'
                    for p_ in ([a] if h == 0 else []) + ([b] if h == len(pth) - 2 else []):
                        pins3[(p_, d)] += (L['width'] + 1) / 3.0
        over = [(n, d) for (n, d) in set(tuse) | set(pins3)
                if (tuse[(n, d)] + pins3[(n, d)] + clk[(n, d)]) > FT_UM * ext(n, d) * FT_MAX + 1]
        if not over and not hov:
            break
        for k in over:
            pinl[k] = max(pinl[k], pins3[k]) * 1.05 + 50
    T['need3'] = need3
    # ---- windows, ports, slots
    occ = collections.defaultdict(list)       # seg key -> [(lo, hi)]

    def alloc(key, lo_s, hi_s, n, lay, per_um):
        starts = sorted({lo_s + 2.0} | {b + 0.48 for a, b in occ[key]})
        for st in starts:
            if st < lo_s + 2.0:
                continue
            hw = window_sym(st, n, lay, LAYERS, per_um)
            if all(not (a < hw and st < b) for a, b in occ[key]) and hw <= hi_s - 2.0:
                return round(st, 4), hw
        st = max([lo_s + 2.0] + [b + 0.48 for a, b in occ[key]])
        hw = window_sym(st, n, lay, LAYERS, per_um)
        errs.append(f'segment {key} overflow: needs up to {hw:.1f} > {hi_s - 2.0:.1f}')
        return round(st, 4), hw

    ports, lane_out = [], []
    buses = collections.defaultdict(dict)
    slots = collections.defaultdict(dict)
    fl = {'E': 'W', 'W': 'E', 'N': 'N', 'S': 'S'}
    for i, L in enumerate(lanes):
        path = L['path']
        prim_ports = []
        for mi, pth in enumerate([path] + ([[mir(x) for x in path]] if L['role'] == 'pri' else [])):
            sfx = 'm' if mi else ''
            lid = f'L{i}{sfx}'
            pids = []
            for h in range(len(pth) - 1):
                a, b = pth[h], pth[h + 1]
                face, lo, hi = adj[a][b]
                key = tuple(sorted((a, b)))
                transit = 0 < h < len(pth) - 2
                lay = HL if face in 'EW' else VL
                if not transit and (i, h) not in need3:
                    lay = lay[:2]
                per_um = 8.8 if len(lay) == 3 else 5.8
                n = L['width'] + 1
                order = 'lsb_low'
                mkey = tuple(sorted((mir(a), mir(b))))
                if mi == 0 or mkey == key:
                    st, hw = alloc(key, lo, hi, n, lay, per_um)
                    occ[key].append((st, hw))
                    if mkey != key:                     # keep the mirror segment a mirror image
                        occ[mkey].append((round(Wd - hw, 4), round(Wd - st, 4)) if face in 'NS' else (st, hw))
                    win = [st, hw]
                else:
                    pp = prim_ports[h]
                    a0, b0 = pp['window_um']
                    if face in 'NS':
                        win = [round(Wd - b0, 4), round(Wd - a0, 4)]
                        order = 'lsb_high' if pp.get('order', 'lsb_low') == 'lsb_low' else 'lsb_low'
                    else:
                        win = [a0, b0]
                        order = pp.get('order', 'lsb_low')
                # bus names: shared between mirror instances of a tile master; 'm' in die-level partitions
                def bn(part, base):
                    return base if not single(part) or not mi else base.replace(f'L{i}', f'L{i}m', 1)
                sb = bn(a, f'L{i}_o' if h == 0 else f'L{i}x{h}_o')
                db = bn(b, f'L{i}_i' if h == len(pth) - 2 else f'L{i}x{h + 1}_i')
                pid = f'{lid}_{h}'
                pr = dict(id=pid, src=dict(part=a, bus=sb), dst=dict(part=b, bus=db), width=L['width'], kind=L['kind'],
                          face=face, layers=list(lay), window_um=win)
                if order != 'lsb_low':
                    pr['order'] = order
                ports.append(pr)
                pids.append(pid)
                if mi == 0:
                    prim_ports.append(pr)
                if h == 0:
                    buses[a][sb] = dict(name=sb, dir='out', width=L['width'], kind=L['kind'])
                if h == len(pth) - 2:
                    buses[b][db] = dict(name=db, dir='in', width=L['width'], kind=L['kind'])
            for h in range(1, len(pth) - 1):
                p = pth[h]
                fin = OPPF[adj[pth[h - 1]][p][0]]
                fout = adj[p][pth[h + 1]][0]
                nm = f'L{i}x{h}' if not (single(p) and mi) else f'L{i}mx{h}'
                slots[p][nm] = dict(name=nm, in_face=fin, out_face=fout, width=L['width'], stations=1)
            lane_out.append(dict(id=lid, ports=pids, note=f'{pth[0]}->{pth[-1]} {L["kind"]}' + (' (mirror)' if mi else '')))
    # utilisation report: face occupancy from the windows, ft = transit + die-layer endpoint pins
    focc = []
    seen = set()
    for key, iv in occ.items():
        a, b = key
        if b not in adj[a]:
            continue
        c = contact(a, b) + 4.0
        focc.append((round(sum(y - x for x, y in iv) / c, 3), a, b))
    T['focc'] = sorted(focc, reverse=True)
    ftu = []
    for (n, d) in set(tuse) | set(pins3) | set(clk):
        ftu.append((round((tuse[(n, d)] + pins3[(n, d)] + clk[(n, d)]) / (FT_UM * ext(n, d)), 3), n, d, int(tuse[(n, d)]),
                    int(pins3[(n, d)]), int(clk[(n, d)])))
    T['ftu'] = sorted(ftu, reverse=True)
    T['util'] = sorted(((use[k] / max(contact(*k) * fcap_um / FACE_MAX, 1.0), k[0], k[1], int(use[k])) for k in use), reverse=True)
    T['tutil'] = [list(x) for x in T['ftu'][:25]]
    lanes_full = []
    for L in lanes:
        lanes_full.append(L)
    buses = {k: list(v.values()) for k, v in buses.items()}
    slots = {k: list(v.values()) for k, v in slots.items()}
    return lanes_full, ports, lane_out, buses, slots, errs, list(unrouted), R
