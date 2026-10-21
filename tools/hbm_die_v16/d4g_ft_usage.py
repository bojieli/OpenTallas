#!/usr/bin/env python3
"""HBM-DIE13 10-20: which die feedthrough channels (d4g_ft_grid.py, die_case_v16 --carve-reserved all) a GEN case uses.

    d4g_ft_usage.py MANIFEST.json [--out ft_usage.json]

For every placed instance whose master carves feedthrough channels (manifest carved_feedthrough, slot-local, mirrored
like relay_router), count the die relay / lane / landing tiles (hbfd_* masters, rly*/rf* instances) whose centre lies in
one of its channels.  A master whose channels carry relays GENUINELY needs the internal feedthrough (tile redesign: the
real tile must reserve the channel); a master whose channels stay empty can drop them (wires route around).
"""
import argparse
import json
from collections import defaultdict


def rects(v, chans):
    o = v.get('o', 'R0')
    for c in chans:
        (x0, x1), (y0, y1) = c['x_um'], c['y_um']
        if o in ('MY', 'R180'):
            x0, x1 = v['w'] - x1, v['w'] - x0
        if o in ('MX', 'R180'):
            y0, y1 = v['h'] - y1, v['h'] - y0
        yield c.get('kind', ''), (v['x'] + x0, v['y'] + y0, v['x'] + x1, v['y'] + y1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('manifest'); ap.add_argument('--out')
    a = ap.parse_args()
    m = json.load(open(a.manifest)); pl = m['placement']; carved = m.get('carved_feedthrough') or {}
    is_relay = lambda n, v: v['m'].startswith('hbfd') or n.startswith(('rly', 'rf'))  # noqa: E731
    rs = []
    for n, v in pl.items():
        for kind, r in rects(v, carved.get(v['m'], [])):
            rs.append((n, v['m'], kind, r))
    # bin index (500 um)
    B = 500.0; idx = defaultdict(list)
    for i, (_, _, _, r) in enumerate(rs):
        for bx in range(int(r[0] // B), int(r[2] // B) + 1):
            for by in range(int(r[1] // B), int(r[3] // B) + 1):
                idx[(bx, by)].append(i)
    per_inst = defaultdict(lambda: dict(master=None, relays=0, columns_used=set(), rows_used=set()))
    for n, v in pl.items():
        if not is_relay(n, v):
            continue
        cx, cy = v['x'] + v['w'] / 2, v['y'] + v['h'] / 2
        for i in idx.get((int(cx // B), int(cy // B)), ()):
            p, mm, kind, r = rs[i]
            if r[0] <= cx <= r[2] and r[1] <= cy <= r[3]:
                d = per_inst[p]; d['master'] = mm; d['relays'] += 1
                (d['columns_used'] if 'column' in kind else d['rows_used']).add(r)
                break
    by_master = defaultdict(lambda: dict(instances=0, instances_used=0, relays=0))
    for n, v in pl.items():
        if carved.get(v['m']):
            by_master[v['m']]['instances'] += 1
    for p, d in per_inst.items():
        b = by_master[d['master']]; b['instances_used'] += 1; b['relays'] += d['relays']
    rep = dict(schema='opentallas.hbm.d4g_ft_usage.v1', manifest=a.manifest, carved_masters=len(carved), channels=len(rs),
               by_master=dict(sorted(by_master.items(), key=lambda t: -t[1]['relays'])),
               per_instance={p: dict(master=d['master'], relays=d['relays'], columns_used=len(d['columns_used']),
                                     rows_used=len(d['rows_used'])) for p, d in per_inst.items()})
    if a.out:
        json.dump(rep, open(a.out, 'w'), indent=1)
    used = sum(1 for b in by_master.values() if b['relays'])
    print(f"FT_USAGE carved_masters {len(carved)} channels {len(rs)} masters_with_relays {used} "
          f"relays_in_channels {sum(b['relays'] for b in by_master.values())}")
    for mm, b in rep['by_master'].items():
        print(f"  FT {mm[:56]:56s} inst {b['instances']:3d} used {b['instances_used']:3d} relays {b['relays']}")


if __name__ == '__main__':
    main()
