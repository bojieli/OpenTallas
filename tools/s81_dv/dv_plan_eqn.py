#!/usr/bin/env python3
"""TOK-S81-GAPS/G8R (10-18): EQUAL STATION COUNT per multi-lane bundle (gaps.json G8 residual).

A bundle = plan links <stem>_l<i> into ONE receiver block (dv_land_pilot.lane_bundles).  The receiver consumes the
bundle's lanes in one cycle (rstop line beat, seqhost host word, frame crs4 4 x 276 column word), so every lane must
land at ONE age ceil(N/2) + K + 1.  G8 equalised the age with the landing strap K; where the landing window does not
fit the raised K (hf_7N: l0 at K 29 is outside the D 8 window at FF; the 24 x_frame bundles: crs4 D 4) the station
count N itself must be equal.  This tool pads the shorter lanes of such a bundle with relay stations:

  a new station is a half-cycle relay placed at the midpoint of the lane's LONGEST straight inter-station piece
  (so no hop gets longer and the reach rule holds); the plan's 'sp' (station points), 'h' (hop segments, split at
  the new point) and 's' (stage count) are rewritten.  Physical arrival at the receiver changes by one station cell
  (forwarded clock and data move together), not by T/2; the logical age moves by the half-cycle.

  dv_plan_eqn.py --plan results/arch/s81_dv_1016/p4l/plan.json --land-in results/arch/s81_dv_1016/landing/p4l2 \
      --out-plan results/arch/s81_dv_1016/p4m --out-land results/arch/s81_dv_1016/landing/p4m_in \
      [--bundles hf_7N x_f_*] [--cell-ps 60]
  -> <out-plan>/plan.json + eqn.json (per padded lane: N before/after, inserted point, longest piece um)
  -> <out-land>/land_plan.json = the land plan with stages = new N and s1 shifted by -cell_ps per added station
     (s1_source 'estimated: STA owed'); run dv_land_pilot.py agebundle --plan-in <out-land> next.
Only bundles whose lane ages are unequal at K = E (or which the user names) are padded.
"""
import argparse, fnmatch, json, math, re, shutil
from pathlib import Path


def lane_bundles(links):
    grp = {}
    for l in links:
        m = re.fullmatch(r'(.+)_l(\d+)', l['i'])
        if m:
            grp.setdefault((m.group(1), l['e'][1][0]), []).append(l)
    return {k: v for k, v in grp.items() if len(v) > 1}


def pad_one(l):
    """insert one station at the midpoint of the longest straight inter-station piece of plan link l"""
    (_, _, x0, y0, _), (_, _, x1, y1, _) = l['e']
    pts = [tuple(p) for p in l['sp']]
    # Include wire turns when selecting an interval: consecutive stations can straddle a turn.
    # Work in path arc length so the inserted point retains source-to-receiver station order.
    best, offset = None, 0.0
    station_dist = []
    for h in l['h']:
        ax, ay, bx, by, _ = h
        length = abs(bx - ax) + abs(by - ay)
        cuts = [0.0, length]
        for px, py in pts:
            if ((ax == bx == px and min(ay, by) <= py <= max(ay, by)) or
                    (ay == by == py and min(ax, bx) <= px <= max(ax, bx))):
                distance = abs(px - ax) + abs(py - ay)
                cuts.append(distance)
                station_dist.append(offset + distance)
        cuts = sorted(set(cuts))
        for lo, hi in zip(cuts, cuts[1:]):
            d = hi - lo
            if best is None or d > best[0]:
                fraction = ((lo + hi) / 2) / length if length else 0
                best = (d, offset + (lo + hi) / 2,
                        (round(ax + fraction * (bx - ax), 3), round(ay + fraction * (by - ay), 3)))
        offset += length
    if best is None or best[0] <= 0:
        raise ValueError(f'{l["i"]}: no positive wire segment for a station')
    d, distance, mp = best
    k = sum(value < distance for value in set(station_dist))
    pts.insert(k, mp)
    # split the hop segment containing mp
    hs = []
    done = False
    for h in l['h']:
        hx1, hy1, hx2, hy2, b = h
        on = (not done) and ((hx1 == hx2 == mp[0] and min(hy1, hy2) < mp[1] < max(hy1, hy2)) or
                             (hy1 == hy2 == mp[1] and min(hx1, hx2) < mp[0] < max(hx1, hx2)))
        if on:
            hs += [[hx1, hy1, mp[0], mp[1], b], [mp[0], mp[1], hx2, hy2, b]]
            done = True
        else:
            hs.append(h)
    if not done:
        raise SystemExit(f'dv_plan_eqn: {l["i"]} midpoint {mp} is on no hop segment')
    l['sp'] = [list(p) for p in pts]
    l['h'] = hs
    l['s'] = len(pts)
    return dict(point=list(mp), piece_um=round(d, 1), piece_after_um=round(d / 2, 1), at_index=k)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True, type=Path)
    ap.add_argument('--land-in', required=True, type=Path)
    ap.add_argument('--out-plan', required=True, type=Path)
    ap.add_argument('--out-land', required=True, type=Path)
    ap.add_argument('--bundles', nargs='*', default=None, help='bundle stems (fnmatch); default every unequal-N bundle '
                    'whose age differs at K = E')
    ap.add_argument('--cell-ps', type=float, default=60.0, help='arrival cost of one added relay station (estimate)')
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    land = json.load(open(a.land_in / 'land_plan.json'))
    lrow = {r['link']: r for r in land['links']}
    blocks = plan['blocks']
    rec = []
    for (stem, dst), lanes in sorted(lane_bundles(plan['links']).items(), key=lambda kv: kv[0]):
        Ns = [len(l.get('sp', [])) for l in lanes]
        if len(set(Ns)) == 1 or min(Ns) == 0:
            continue
        if a.bundles is not None and not any(fnmatch.fnmatch(stem, p) for p in a.bundles):
            continue
        # unequal age at the plan K (= E)?  only the ceil(N/2) term can differ when E is shared
        ages = [math.ceil(n / 2) + (lrow.get(l['i'].replace('-', '_'), {}).get('E') or 0) for n, l in zip(Ns, lanes)]
        if a.bundles is None and len(set(ages)) == 1:
            continue
        nmax = max(Ns)
        for l, n in zip(lanes, Ns):
            while len(l['sp']) < nmax:
                ins = pad_one(l)
                nm = l['i'].replace('-', '_')
                r = lrow.get(nm)
                if r is not None:
                    r['stages'] = l['s']
                    r['s1'] = {c: (round(v - a.cell_ps, 1) if v is not None else None) for c, v in r['s1'].items()}
                    r['s1_source'] = f'TOK-S81-GAPS/G8R estimate: STA s1 - {a.cell_ps} ps per added station (die STA owed)'
                    r['eqn_added'] = r.get('eqn_added', 0) + 1
                rec.append(dict(bundle=stem, dst=blocks[dst]['name'], link=l['i'], N_before=n, N_after=l['s'], **ins))
    a.out_plan.mkdir(parents=True, exist_ok=True)
    a.out_land.mkdir(parents=True, exist_ok=True)
    (a.out_plan / 'plan.json').write_text(json.dumps(plan) + '\n')
    (a.out_plan / 'eqn.json').write_text(json.dumps(dict(
        schema='opentallas.s81_dv.plan_eqn.v1', tool='tools/s81_dv/dv_plan_eqn.py', source_plan=str(a.plan),
        rule='pad the shorter lanes of a multi-lane bundle with half-cycle relay stations at the midpoint of their '
             'longest straight inter-station piece until every lane has the bundle max N',
        padded_lanes=len({r['link'] for r in rec}), added_stations=len(rec),
        bundles=sorted({r['bundle'] for r in rec}), rows=rec), indent=1) + '\n')
    land['source_plan_eqn'] = str(a.out_plan / 'plan.json')
    (a.out_land / 'land_plan.json').write_text(json.dumps(land, indent=1) + '\n')
    if (a.land_in / 'landing.sdc').exists():
        shutil.copy(a.land_in / 'landing.sdc', a.out_land / 'landing.sdc')
    print(f'dv_plan_eqn: {len(rec)} stations added on {len({r["link"] for r in rec})} lanes of '
          f'{len({r["bundle"] for r in rec})} bundles -> {a.out_plan / "plan.json"}, {a.out_land / "land_plan.json"}')


if __name__ == '__main__':
    main()
