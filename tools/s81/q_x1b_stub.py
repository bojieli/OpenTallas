#!/usr/bin/env python3
"""s81-gen 2026-10-10: B-pin STUB of the qs5f q-element abstract (coordinator option B; real route
dsrom-qelem-qs5f-x1b-e82a88082 by cont-takeover).  The x1 port pins (S face, x 233.1-284.2 um in the routed qs5f view)
are moved, unchanged in order / pitch / layer / shape, to the S-face east end (element x 400.08-505.44, centred), so the
die-level x1 bank stands over the slot station instead of the packed cfg ROM row.  Everything else is the qs5f view.
For die generation / lint only until the routed x1b view lands.
    q_x1b_stub.py [--src physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz] [--out physical/s81_die_views/q_elem_qs5f_x1b_stub/q_elem.lef.gz]"""
import argparse, gzip, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
LO, HI, DB = 400.08, 505.44, 0.048


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default='physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz')
    ap.add_argument('--out', default='physical/s81_die_views/q_elem_qs5f_x1b_stub/q_elem.lef.gz')
    a = ap.parse_args()
    import os
    os.environ['OT_S81_Q_LEF'] = a.src
    import dsrom_s81_fulldie as F
    rq = F.real_lef(a.src)
    x1 = set(F.real_ports_r8()[rq['name']]['x1'])
    xs = [rq['pins'][n][1] for n in x1]
    x0, x1max = min(r[0] for r in xs), max(r[2] for r in xs)
    assert all(abs(r[1]) < 1e-6 for r in xs), 'x1 pins expected on the S face'
    assert x1max - x0 <= HI - LO, (x0, x1max)
    dx = round(((LO + HI) / 2 - (x0 + x1max) / 2) / DB) * DB
    # nothing else may sit on the S face inside the new span
    clash = [n for n, (ly, r) in rq['pins'].items() if n not in x1 and r[1] < 1e-6 and r[2] > x0 + dx and r[0] < x1max + dx]
    assert not clash, ('S-face pins inside the x1 target span', clash[:8])
    txt = gzip.open(ROOT / a.src, 'rt').read().split('\n')
    out, cur = [], None
    for ln in txt:
        mm = re.match(r'\s*PIN (\S+)', ln)
        if mm:
            cur = mm.group(1)
        elif re.match(r'\s*END (\S+)', ln) and cur and ln.strip() == f'END {cur}':
            cur = None
        if cur in x1 and re.match(r'\s*RECT ', ln):
            v = ln.split()
            i = v.index('RECT')
            nums = [float(t) for t in v[i + 1:i + 5]]
            nums[0] += dx
            nums[2] += dx
            ln = re.sub(r'RECT .*;', 'RECT ' + ' '.join(f'{t:.3f}' for t in nums) + ' ;', ln)
        out.append(ln)
    p = ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, 'wt') as f:
        f.write('\n'.join(out))
    (p.parent / 'SOURCE.txt').write_text(
        f'B-pin STUB (s81-gen 2026-10-10, tools/s81/q_x1b_stub.py): {a.src} with the {len(x1)} x1 pins shifted by '
        f'{dx:+.3f} um along the S face ({x0:.3f}-{x1max:.3f} -> {x0 + dx:.3f}-{x1max + dx:.3f}; target {LO}-{HI}).\n'
        'NOT a routed view: die generation / lint only until dsrom-qelem-qs5f-x1b-e82a88082 (cont-takeover) closes.\n')
    print(dict(pins=len(x1), dx=round(dx, 3), new=(round(x0 + dx, 3), round(x1max + dx, 3))))


if __name__ == '__main__':
    main()
