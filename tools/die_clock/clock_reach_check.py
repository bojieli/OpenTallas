#!/usr/bin/env python3
"""QW-DIECLK3 10-19: reach check of a built die clock (tools/die_clock/build.py manifest.json).

Every clock net (one driver: a clock cell output or a tree root pin; its loads: clock cells and sink pins, from the
manifest parent map) is measured as its REACH = the largest Manhattan distance driver -> load (the unbuffered wire a
clock edge travels on that net; a merge buffer driving two opposite 200-um chains has reach 200, half-perimeter 400).
FAIL when any net's reach exceeds --limit-um (owner reach 405 um), or when the build recorded safe-tree violations
(regtree SAFE: segment > SEG_MAX, leaf beyond LEAF_REACH, no route within the safe over-block run).  The half-perimeter
(lower bound of the net's total wire) is reported beside it.  Placed-grid distance, not routed: a GRT detour is
checked downstream (die_repeaters long-wire report of the routed die).

Why: dv2f19g2 rA left 281 region-leaf nets n_dc_r*_L* > 1 mm unbuffered across CB16 columns (up to 2472 um, 9.8 ns);
die_repeaters skips clock pins, so nothing downstream ever repaired them.

  clock_reach_check.py MANIFEST [--limit-um 405] [--warn-um 220] [--out reach.json]
Prints one line 'QCLK_REACH PASS|FAIL ...'; exit 1 on FAIL.
"""
import argparse
from collections import Counter, defaultdict
import json
import sys


def nets_of(m):
    """[(driver, [loads], [(x, y), ...])] for every driver in the manifest parent map with known coordinates."""
    xy = {c[0]: (float(c[2]), float(c[3])) for c in m.get('cells', [])}
    for p, s in m.get('sinks', {}).items():
        xy[p] = (float(s['x']), float(s['y']))
    for t in m.get('trees', {}).values():
        if t.get('root') and t.get('root_xy'):
            xy.setdefault(t['root'], tuple(map(float, t['root_xy'])))
    # a local-root tree's root buffer input is an IDEAL regional entry (n_<rb>_spine, undriven: the GEN owes the
    # entry) unless a spine feeds it (then its parent is a spine cell): root pin -> root buffer is not a wire
    ideal = set((m.get('local_root_xy') or {}))
    kids = defaultdict(list)
    for ch, par in m.get('parent', {}).items():
        if par in ideal:
            continue
        kids[par].append(ch)
    out, unknown = [], 0
    for d, ch in kids.items():
        pts = [xy[x] for x in [d] + ch if x in xy]
        if d not in xy or len(pts) < 2:
            unknown += 1
            continue
        out.append((d, ch, pts))
    return out, unknown


def hpwl(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return max(xs) - min(xs) + max(ys) - min(ys)


def reach(pts):
    x0, y0 = pts[0]
    return max(abs(x - x0) + abs(y - y0) for x, y in pts[1:])


def check(m, limit=405.0, warn=220.0):
    nets, unknown = nets_of(m)
    rows = sorted(((round(reach(p), 1), d, len(ch), ch[0], round(hpwl(p), 1)) for d, ch, p in nets), reverse=True)
    over = [r for r in rows if r[0] > limit]
    warn_n = sum(1 for r in rows if r[0] > warn)
    vio = (m.get('safe_tree') or {}).get('violations', [])
    kinds = Counter(v.get('kind') for v in vio)
    by_type = Counter()
    for r in over:
        tail = r[1].rsplit('_', 1)[-1]
        by_type[''.join(ch for ch in tail if not ch.isdigit()) or tail] += 1
    ok = not over and not vio
    return dict(schema='opentallas.die_clock.reach.v1', verdict='PASS' if ok else 'FAIL', limit_um=limit, warn_um=warn,
                nets=len(rows), nets_without_xy=unknown, over_limit=len(over), over_warn=warn_n,
                max_um=rows[0][0] if rows else 0.0, over_by_driver_type=dict(by_type),
                hpwl_over_limit=sum(1 for r in rows if r[4] > limit), hpwl_max_um=max((r[4] for r in rows), default=0.0),
                safe_tree=bool(m.get('safe_tree')), safe_violations=dict(kinds),
                worst=[dict(um=r[0], driver=r[1], loads=r[2], first_load=r[3], hpwl_um=r[4]) for r in rows[:30]],
                violations_sample=vio[:30])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest')
    ap.add_argument('--limit-um', type=float, default=405.0)
    ap.add_argument('--warn-um', type=float, default=220.0)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    m = json.load(open(a.manifest))
    r = check(m, a.limit_um, a.warn_um)
    if a.out:
        json.dump(r, open(a.out, 'w'), indent=1)
    w = r['worst'][0] if r['worst'] else {}
    print('QCLK_REACH', r['verdict'], 'nets', r['nets'], f"over{int(a.limit_um)}", r['over_limit'],
          f"over{int(a.warn_um)}", r['over_warn'], 'max_um', r['max_um'], w.get('driver', ''),
          'by_type', json.dumps(r['over_by_driver_type']), 'hpwl_max_um', r['hpwl_max_um'], 'safe_tree', r['safe_tree'],
          'safe_violations', json.dumps(r['safe_violations']), 'no_xy', r['nets_without_xy'])
    return 0 if r['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
