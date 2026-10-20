#!/usr/bin/env python3
"""HBM-DIE9 10-20: structural relay channels for the d4g die by CHANNEL CUTS (LEAD7-HBM decision 10-20).

Why: the GEN2e4 r7 S7 lane rows failed on station CAPACITY, not pitch (HBM-DIE8): the routed stations of 44,093 rows
jam the SM frame-pair gaps (xq / xl stacks), the SM-row / middle-band edges (y ~9.0 / 22.7 mm) and the middle-band
spots around sfucore / su / pgp, where 572 um windows are 74 % covered by blocks and row demand is 1.17x the free
area.  A planner alone cannot create area there: the floorplan must carry reserved relay channels.

Model (geometry only; every block keeps its outline, orientation, pins and neighbours; the die grows):
  * the die is split into horizontal BANDS by the block centre y (stripe S = PHY/PC/SVG row, SM-S row, middle band,
    SM-N row, stripe N);
  * an X CUT (band, x, dx) opens a vertical channel of dx um at x inside one band: every block of that band whose
    centre is right of x moves right by dx (rigid: a block is never split; a slot inside a plan block moves with it);
    the total dx of every band is equal, so the die widens uniformly; a band with no cuts (the stripes: the PC row stays
    aligned to its PHY channel windows) moves by its 'shift';
  * a Y CUT (y, dy) opens a horizontal channel of dy um at y across the die (every block whose centre is above y moves
    up by dy);
  * moving blocks only ever separates two blocks (a block right of / above another never overtakes it), so no overlap
    can be created; the tool re-checks every pair and refuses the plan if one appears.
Points (relay homes in contract notes, clock-region sites, lanes) map by the same rule at the point itself.

    d4g_channel_cuts.py --spec SPEC.json --grants G.json --plan P.json --lanes L.json --region-map M.json --out DIR
writes DIR/{grants_d4g.json, compact.P.json, lanes.json, d4g_region_map.json, coord_map.json, report.json, plan.png}.
coord_map.json is the --coord-map input of die_case_v16.py (contract-note relay homes).  Reticle (26 x 33 mm,
>= 0.5 mm margin in W AND H) is enforced.
"""
import argparse, copy, json, math, sys
from pathlib import Path

ROT = ('R90', 'R270', 'MXR90', 'MYR90')


class CoordMap:
    """bands [{name, y0, y1, cuts: [[x, dx], ..], shift}], ycuts [[y, dy], ..] (all ORIGINAL coordinates)"""

    def __init__(self, spec):
        self.bands = spec['bands']; self.ycuts = sorted(spec.get('ycuts', []))
        tot = {b['name']: sum(dx for _, dx in b.get('cuts', [])) + b.get('shift', 0.0) for b in self.bands}
        self.dX = max(tot.values()); self.dY = sum(dy for _, dy in self.ycuts)
        # every band WITH cuts spans the full new width; a band without cuts (stripe) only moves by its shift (<= dX)
        bad = {b['name']: tot[b['name']] for b in self.bands
               if (b.get('cuts') and abs(tot[b['name']] - self.dX) > 1e-6) or tot[b['name']] > self.dX + 1e-6}
        if bad:
            raise SystemExit(f'CHANNEL_CUTS: band totals differ (die must widen uniformly): {tot}')

    def band(self, y):
        for b in self.bands:
            if b['y0'] <= y < b['y1']:
                return b
        return self.bands[0] if y < self.bands[0]['y0'] else self.bands[-1]

    def dxy(self, x, y):
        """shift (dx, dy) of a point / of a rigid block centred at (x, y)"""
        b = self.band(y)
        dx = b.get('shift', 0.0) + sum(d for cx, d in b.get('cuts', []) if cx < x)
        dy = sum(d for cy, d in self.ycuts if cy < y)
        return dx, dy

    def point(self, x, y):
        dx, dy = self.dxy(x, y)
        return x + dx, y + dy


def wh(slot):
    w, h = slot['outline']['w'], slot['outline']['h']
    return (h, w) if slot['origin'].get('orient', 'R0') in ROT else (w, h)


def overlaps(rs, tol=0.01):
    """pairs of overlapping rectangles [(name, x, y, w, h)] (sweep on x)"""
    rs = sorted(rs, key=lambda r: r[1]); out = []; act = []
    for r in rs:
        act = [q for q in act if q[1] + q[3] > r[1] + tol]
        for q in act:
            if q[2] < r[2] + r[4] - tol and r[2] < q[2] + q[4] - tol:
                out.append((q[0], r[0]))
        act.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--spec', '--grants', '--plan', '--lanes', '--region-map', '--out'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    spec = json.load(open(a.spec)); M = CoordMap(spec)
    G = json.load(open(a.grants)); P = json.load(open(a.plan)); L = json.load(open(a.lanes)); RM = json.load(open(a.region_map))
    W, H = G['floorplan']['die_um']
    G2, P2, L2, RM2 = copy.deepcopy(G), copy.deepcopy(P), copy.deepcopy(L), copy.deepcopy(RM)
    # plan blocks: rigid shift by their own centre
    pshift = {}
    for k, b in P2.items():
        if isinstance(b, dict) and 'x' in b:
            pshift[k] = M.dxy(b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
            b['x'] = round(b['x'] + pshift[k][0], 3); b['y'] = round(b['y'] + pshift[k][1], 3)
    pboxes = [(k, b['x'], b['y'], b['w'], b['h']) for k, b in P.items() if isinstance(b, dict) and 'x' in b]
    # grant slots: with the smallest plan block that contains the slot centre (slot moves with its plan region), else own centre
    rep = dict(slots_with_plan_block=0, slots_own_centre=0)
    for s in G2['slots']:
        if s.get('kind') == 'die':
            continue
        w, h = wh(s); cx, cy = s['origin']['x'] + w / 2, s['origin']['y'] + h / 2
        inside = [p for p in pboxes if p[1] <= cx <= p[1] + p[3] and p[2] <= cy <= p[2] + p[4]
                  and p[1] - 0.01 <= s['origin']['x'] and s['origin']['x'] + w <= p[1] + p[3] + 0.01
                  and p[2] - 0.01 <= s['origin']['y'] and s['origin']['y'] + h <= p[2] + p[4] + 0.01]
        if inside:
            k = min(inside, key=lambda p: p[3] * p[4])[0]; d = pshift[k]; rep['slots_with_plan_block'] += 1
        else:
            d = M.dxy(cx, cy); rep['slots_own_centre'] += 1
        s['origin']['x'] = round(s['origin']['x'] + d[0], 3); s['origin']['y'] = round(s['origin']['y'] + d[1], 3)
    W2, H2 = round(W + M.dX, 3), round(H + M.dY, 3)
    G2['floorplan']['die_um'] = [W2, H2]
    for s in G2['slots']:
        if s.get('kind') == 'die':
            s['outline']['w'], s['outline']['h'] = W2, H2
    G2['floorplan']['channel_cuts'] = dict(tool='tools/hbm_die_v16/d4g_channel_cuts.py', spec=spec, from_die_um=[W, H])
    # lanes: v = x of a vertical lane (middle-band rule), h = y of a horizontal lane
    mid = spec.get('lane_band_y', H / 2)
    for k, ln in L2.items():
        if 'v' in ln:
            ln['v'] = round(M.point(ln['v'], mid)[0], 3)
        if 'h' in ln:
            ln['h'] = round(ln['h'] + M.dxy(0.0, ln['h'])[1], 3)
    for d in (RM2.get('instances', {}), RM2.get('regions', {})):
        for k, v in d.items():
            if isinstance(v, dict) and 'site' in v:
                v['site'] = [round(c, 1) for c in M.point(*v['site'])]
    RM2['plan'] = str(Path(a.out) / 'compact.P.json')
    # overlap re-check (plan blocks among themselves; grant slots among themselves): only pairs NEW vs the input count
    def prs(PP):
        return [(k, b['x'], b['y'], b['w'], b['h']) for k, b in PP.items() if isinstance(b, dict) and 'x' in b]
    def srs(GG):
        return [(s['name'], s['origin']['x'], s['origin']['y']) + wh(s) for s in GG['slots'] if s.get('kind') != 'die']
    new_ov = {}
    for tag, before, after in (('plan', prs(P), prs(P2)), ('slots', srs(G), srs(G2)),
                               ('slot_vs_plan', [('P:' + r[0],) + r[1:] for r in prs(P)] + srs(G),
                                [('P:' + r[0],) + r[1:] for r in prs(P2)] + srs(G2))):
        b0 = set(map(frozenset, overlaps(before))); b1 = set(map(frozenset, overlaps(after)))
        new_ov[tag] = sorted(tuple(sorted(x)) for x in b1 - b0)
    import reticle
    ret = reticle.check_die(W2, H2)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rep.update(schema='opentallas.hbm.d4g_channel_cuts.v1', spec=spec, die_um=[W, H], new_die_um=[W2, H2],
               die_mm2=round(W * H / 1e6, 2), new_die_mm2=round(W2 * H2 / 1e6, 2), dX=M.dX, dY=M.dY, reticle=ret,
               new_overlaps=new_ov, verdict='PASS' if ret['ok'] and not any(new_ov.values()) else 'FAIL',
               rule='rigid block shifts by centre per band; slots move with their plan block; no block resized')
    json.dump(G2, open(out / 'grants_d4g.json', 'w'), indent=1)
    json.dump(P2, open(out / 'compact.P.json', 'w'), indent=1)
    json.dump(L2, open(out / 'lanes.json', 'w'), indent=1)
    json.dump(RM2, open(out / 'd4g_region_map.json', 'w'), indent=1)
    json.dump(dict(schema='opentallas.hbm.d4g_coord_map.v1', spec=spec), open(out / 'coord_map.json', 'w'), indent=1)
    json.dump(rep, open(out / 'report.json', 'w'), indent=1)
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, axs = plt.subplots(1, 2, figsize=(16, 13))
        for ax, PP, GG, (ww, hh), t in ((axs[0], P, G, (W, H), 'input'), (axs[1], P2, G2, (W2, H2), 'channel cuts')):
            ax.add_patch(Rectangle((0, 0), ww, hh, fill=False, lw=1.5))
            for k, x, y, w, h in prs(PP):
                ax.add_patch(Rectangle((x, y), w, h, fc='#f4b183' if k.startswith('sm_') else '#c9d9ef', ec='k', lw=0.3))
            for k, x, y, w, h in srs(GG):
                ax.add_patch(Rectangle((x, y), w, h, fc='none', ec='#2e7d32', lw=0.3))
            ax.set_xlim(0, max(W, W2)); ax.set_ylim(0, max(H, H2)); ax.set_aspect('equal')
            ax.set_title(f'{t}: {ww / 1e3:.2f} x {hh / 1e3:.2f} mm = {ww * hh / 1e6:.0f} mm2')
        if spec:
            for b in spec['bands']:
                for cx, dx in b.get('cuts', []):
                    x2 = M.point(cx, (b['y0'] + b['y1']) / 2)[0]
                    yy = [M.point(cx, b['y0'])[1], M.point(cx, min(b['y1'], H) - 1)[1]]
                    axs[1].fill_betweenx(yy, x2 - dx, x2, color='#ffeb3b', alpha=0.6, lw=0)
            for cy, dy in M.ycuts:
                y2 = cy + M.dxy(0, cy + 1e-3)[1]
                axs[1].fill_between([0, W2], y2 - dy, y2, color='#ffeb3b', alpha=0.6, lw=0)
        fig.tight_layout(); fig.savefig(out / 'plan.png', dpi=70)
    except Exception as e:  # noqa: BLE001
        print('PNG skipped', e)
    print('CHANNEL_CUTS', rep['verdict'], json.dumps({k: rep[k] for k in ('new_die_um', 'new_die_mm2', 'dX', 'dY', 'new_overlaps',
                                                                        'slots_with_plan_block', 'slots_own_centre')}))
    print('RETICLE', json.dumps(ret))
    sys.exit(0 if rep['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v15'))
    main()
