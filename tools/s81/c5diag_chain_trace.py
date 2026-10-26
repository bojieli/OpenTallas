#!/usr/bin/env python3
"""c5 diagnosis (2026-10-13): walk one bit of a relay chain through a placed die DEF and print every hop.
From <inst> <pin[bit]> follow the net to the next instance, leave it on its dq/do0/o pin of the same bit, until the
chain ends at an instance without such a pin.  Per hop: instance, master, placement, pin-to-pin Manhattan.
usage: c5diag_chain_trace.py <case dir> <net-name regex> <start inst> <start pin[bit]> [out.json]"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c5diag_congestion as M

case, rx, inst, pin = sys.argv[1:5]
size, pins = M.read_lefs(sorted(glob.glob(os.path.join(case, 'grt', '*.lef'))))
rx = re.compile(rx)
comp, nets, sec = {}, {}, None
for line in open(os.path.join(case, 'a_real', 'floorplan_placed.def')):
    if line.startswith('COMPONENTS'):
        sec = 'C'
    elif line.startswith('NETS'):
        sec = 'N'
    elif line.startswith('END NETS'):
        break
    elif sec == 'C':
        mt = re.match(r'\s*-\s+(\S+)\s+(\S+).*?(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\S+)', line)
        if mt:
            comp[mt.group(1)] = (mt.group(2), int(mt.group(3)) / 1000, int(mt.group(4)) / 1000, mt.group(5))
    elif sec == 'N':
        mt = re.match(r'\s*-\s+(\S+)', line)
        if mt and rx.search(mt.group(1)):
            cs = re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)', line.split('+')[0])
            for c in cs:
                nets[c] = (mt.group(1), cs)


def loc(i, p):
    mm, x, y, o = comp[i]
    w, h = size.get(mm, (0, 0))
    px, py, _ = pins.get(mm, {}).get(p, (w / 2, h / 2, '?'))
    if o == 'S':
        px, py = w - px, h - py
    elif o == 'FN':
        px = w - px
    elif o == 'FS':
        py = h - py
    return x + px, y + py


bit = pin[pin.index('['):] if '[' in pin else ''
rows, total = [], 0.0
cur = (inst, pin)
while cur in nets:
    name, cs = nets[cur]
    other = [c for c in cs if c != cur]
    if not other:
        break
    nx = other[0]
    (xa, ya), (xb, yb) = loc(*cur), loc(*nx)
    L = abs(xa - xb) + abs(ya - yb)
    total += L
    mm, x, y, o = comp[nx[0]]
    rows.append(dict(net=name, frm='%s.%s' % cur, to='%s.%s' % nx, master=mm, x=x, y=y, orient=o, from_pin=[round(xa, 1), round(ya, 1)],
                     to_pin=[round(xb, 1), round(yb, 1)], manh=round(L, 1), fanout=len(other)))
    nxt = next(((nx[0], q + bit) for q in ('dq', 'do0', 'o') if (nx[0], q + bit) in nets), None)
    if nxt is None:
        break
    cur = nxt
if rows:
    a, b = rows[0]['from_pin'], rows[-1]['to_pin']
    direct = abs(a[0] - b[0]) + abs(a[1] - b[1])
    rec = dict(case=os.path.abspath(case), start='%s.%s' % (inst, pin), end=rows[-1]['to'], hops=len(rows), path_manh_um=round(total, 1),
               direct_manh_um=round(direct, 1), detour=round(total / max(1.0, direct), 2), max_hop_um=max(r['manh'] for r in rows), rows=rows)
    print('OT_CHAIN %s -> %s hops %d path %.0f um direct %.0f um (x %.2f) max hop %.0f um' % (rec['start'], rec['end'], rec['hops'], total, direct,
                                                                                         rec['detour'], rec['max_hop_um']))
    for r in rows:
        print('  %-58s %-18s @%8.1f,%8.1f %-2s hop %6.1f' % (r['to'][-58:], r['master'], r['x'], r['y'], r['orient'], r['manh']))
    if len(sys.argv) > 5:
        json.dump(rec, open(sys.argv[5], 'w'), indent=1)
else:
    print('no net at', inst, pin)
