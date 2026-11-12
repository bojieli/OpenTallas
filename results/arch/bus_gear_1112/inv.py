#!/usr/bin/env python3
"""BUS-GEAR-1 crossing inventory: per die, the widest crossings by window pin density,
per type/face pin totals, and per type ft bits.  Read-only on plan JSON."""
import json, gzip, sys, collections, os

def load(p):
    return json.load(gzip.open(p) if p.endswith('.gz') else open(p))

def wlen(w):
    return abs(w[1] - w[0]) if w else None

out_rows, face_rows, ft_rows = [], [], []
for die, path in [a.split('=', 1) for a in sys.argv[1:]]:
    d = load(path)
    parts = d['partitions']
    if isinstance(parts, dict):
        parts = [dict(name=k, **v) for k, v in parts.items()]
    ptype = {p['name']: p['type'] for p in parts}
    nrep = collections.Counter(ptype.values())
    types = d['partition_types']
    lanes = {}
    for ln in d.get('lanes', []):
        for pid in ln['ports']:
            lanes[pid] = ln
    # crossings: dedupe by (src type, src bus, dst type, dst bus)
    seen = {}
    portface = {}
    for pt in d['ports']:
        if pt.get('kind') in ('clock', 'reset'):
            continue
        st, dt = ptype.get(pt['src']['part'], '?'), ptype.get(pt['dst']['part'], '?')
        w = pt['width']
        segs = pt.get('segments')
        L = sum(wlen(s['window_um']) for s in segs) if segs else wlen(pt.get('window_um'))
        dens = (w / L) if L else None
        key = (st, pt['src']['bus'], dt, pt['dst']['bus'])
        ln = lanes.get(pt['id'], {})
        r = seen.get(key)
        opp = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
        if pt.get('face'):
            portface[(st, pt['src']['bus'])] = (pt['face'], w)
            portface[(dt, pt['dst']['bus'])] = (opp[pt['face']], w)
        if r is None:
            seen[key] = dict(die=die, port=pt['id'], src_type=st, src_bus=pt['src']['bus'], dst_type=dt,
                             dst_bus=pt['dst']['bus'], width=w, face=pt.get('face'), layers=','.join(pt.get('layers', [])),
                             win_um=round(L, 2) if L else None, pins_per_um=round(dens, 2) if dens else None,
                             n=1, beats=ln.get('beats'), lane=ln.get('id'), cycles=ln.get('fixed_cycles'))
        else:
            r['n'] += 1
    # type faces: from the type's own bus table when present (pins per face), else from ports
    for tn, t in types.items():
        ol = t.get('outline_um') or [0, 0]
        W, H = (ol[0], ol[1]) if len(ol) == 2 else (ol[2] - ol[0], ol[3] - ol[1])
        fp = collections.defaultdict(int)
        for b in (t.get('buses') or []):
            if isinstance(b, dict) and b.get('face') and b.get('width'):
                fp[b['face']] += int(b['width'])
        src = 'buses'
        if not fp:
            src = 'ports'
            for (tt, bus), (f, w) in portface.items():
                if tt == tn: fp[f] += w
        ftp = collections.defaultdict(int)
        for s_ in (t.get('ft_slots') or []):
            ftp[s_.get('in_face')] += int(s_.get('width', 0)); ftp[s_.get('out_face')] += int(s_.get('width', 0))
        for f in set(fp) | set(k for k in ftp if k):
            n = fp.get(f, 0)
            flen = W if f in 'NS' else H
            tot = n + ftp.get(f, 0)
            face_rows.append(dict(die=die, type=tn, face=f, bus_pins=n, ft_pins=ftp.get(f, 0), pins=tot,
                                  face_um=round(flen, 1), pins_per_um=round(tot / flen, 2) if flen else None,
                                  reps=nrep.get(tn, 0), src=src, hard=bool(t.get('hard'))))
        ftb = 0; nft = 0; ftmax = 0
        for s in (t.get('ft_slots') or []):
            ftb += int(s.get('width', 0)); nft += 1; ftmax = max(ftmax, int(s.get('width', 0)))
        if ftb:
            ft_rows.append(dict(die=die, type=tn, ft_bits=ftb, ft_slots=nft, ft_max_slot=ftmax,
                                outline=f'{W:.0f}x{H:.0f}', reps=nrep.get(tn, 0)))
    out_rows += list(seen.values())

o = os.environ.get('OUT', '.')
def dump(name, rows):
    if not rows: return
    ks = list(rows[0].keys())
    with open(os.path.join(o, name), 'w') as f:
        f.write('\t'.join(ks) + '\n')
        for r in rows:
            f.write('\t'.join('' if r.get(k) is None else str(r.get(k)) for k in ks) + '\n')
dump('crossings.tsv', sorted(out_rows, key=lambda r: -(r['width'])))
dump('faces.tsv', sorted(face_rows, key=lambda r: -(r['pins_per_um'] or 0)))
dump('ft.tsv', sorted(ft_rows, key=lambda r: -r['ft_bits']))
print(len(out_rows), len(face_rows), len(ft_rows))
