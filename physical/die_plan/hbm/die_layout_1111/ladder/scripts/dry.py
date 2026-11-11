import json, sys, math, collections
sys.path.insert(0, sys.argv[2])
sys.path.insert(0, sys.argv[4] if len(sys.argv) > 4 else '.')
import schema as S
import lgeom as G
import runs as RU

raw = json.load(open(sys.argv[1]))
P = S.Plan(raw)
spec = json.load(open(sys.argv[3]))
lat = raw['latency']['lanes']
RR = RU.runs(P, S)
dem = collections.defaultdict(lambda: [0, []])
bad, up = [], []
nfail = 0
for side in ('NE', 'NW'):
    R = G.rects(side, spec[side])
    for r in [x for x in RR if x['side'] == side]:
        if r['start'][0] == 'bank':
            sb = r['start'][1]
            x0, y0, x1, y1 = R[sb]
            sp = ((x0 + x1) / 2, (y0 + y1) / 2)
        else:
            _, part, nf, win, pid = r['start']
            sp = RU.win_point(P, part, nf, win)
            sb = RU.entry_bank(R, nf, win, sp)
        if r['end'][0] == 'bank':
            eb = r['end'][1]
            x0, y0, x1, y1 = R[eb]
            ep = ((x0 + x1) / 2, (y0 + y1) / 2)
        else:
            _, part, nf, win, pid = r['end']
            ep = RU.win_point(P, part, nf, win)
            eb = RU.entry_bank(R, nf, win, ep)
        if sb is None or eb is None:
            bad.append((r['lane'], 'straddle', r['start'][:2], r['end'][:2]))
            continue
        res = G.route(R, sb, sp, eb, ep)
        if res is None:
            bad.append((r['lane'], 'noroute'))
            continue
        cost, path, pts = res
        for a, b in zip(path, path[1:]):
            e = tuple(sorted((a, b)))
            dem[e][0] += r['width'] + 1
            dem[e][1].append(r['lane'])
        # station estimate per crossed bank (not the end banks of a lane)
        allp = [sp] + pts + [ep]
        st = 0
        for i, b in enumerate(path):
            is_end = (i == 0 and r['start'][0] == 'bank') or (i == len(path) - 1 and r['end'][0] == 'bank')
            if is_end:
                continue
            L = G.man(allp[i], allp[i + 1])
            st += max(1, math.ceil(L / 405.0 - 1e-9))
        r.update(path=path, est_st=st)
# per lane: old stations in bank runs vs new
by = collections.defaultdict(list)
for r in RR:
    by[r['lane']].append(r)
for lid, rs in by.items():
    if any('path' not in r for r in rs):
        continue
    oldst = 0
    for part, slot, _, _ in P.lane_crossings(lid):
        if any(part in r['run'] for r in rs) and slot:
            s = P.slot(part, slot)
            oldst += int(s.get('stations', 1))
    newst = sum(r['est_st'] for r in rs)
    if newst > oldst:
        up.append((lid, rs[0]['width'], oldst, newst, ' / '.join('>'.join(r['path']) for r in rs)))
print('runs', len(RR), 'bad', len(bad))
for b in bad:
    print('  BAD', b)
print('edge demand (bits incl epoch) vs capacity at 6/um (2 layers) and 12/um (4 layers):')
for side in ('NE', 'NW'):
    R = G.rects(side, spec[side])
    for e, (bits, ls) in sorted(dem.items()):
        if not e[0].startswith(side):
            continue
        f, lo, hi, line = G.shared_edge(R[e[0]], R[e[1]])
        L = hi - lo
        need2 = bits / 6.0
        print(f'  {e[0]}|{e[1][3:]} {f} len {L:7.1f} bits {bits:6d} need2 {need2:7.1f} need4 {bits/12:7.1f} '
              f'{"OK2" if need2 + 4*len(ls) < L - 2 else ("OK4" if bits/12 + 4*len(ls) < L - 2 else "OVER")} lanes {len(ls)}')
for e,(bits,ls) in sorted(dem.items()):
    if False:
        print('USERS',e, [(l, next(r['width'] for r in RR if r['lane']==l), next('>'.join(r['path']) for r in RR if r['lane']==l and 'path' in r)) for l in ls])
print('latency up (est):', len(up), 'bits', sum(u[1] for u in up))
for u in sorted(up, key=lambda z: -z[1])[:40]:
    print('  UP', *u)
