#!/usr/bin/env python3
"""SU RF write-relay routes on the die plan (H-DIE r2 2026-10-15, for H-ELEM-A ot_hbm_su_rf_route / H-ELEM-B RF_RELAY).

16 point-to-point routes core q -> core d (41 b each: red_sv/red_tag/red_x at the source core, rf_wv/rf_wa/rf_wd at the
destination core).  Paths avoid every hard frame wider than the reach (SM frames, IDX scorers): band -> inner channel
(vertical moves only in the 0.6 mm channels) -> the scorer relay row of the die half (horizontal crossings of the centre
column) -> channel -> band.  Relay homes every <= REACH um along the path; RF_RELAY = max stages over the 16 routes
(equal-latency static schedule; the q -> q route is padded to the same depth in RTL).

    su_rf_route_pins.py --plan DIR [--reach 480] [--out DIR/su_rf_route_pins.json]
"""
import argparse, json, math
from pathlib import Path

QS = ['SW', 'SE', 'NW', 'NE']
BITS = 41


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True); ap.add_argument('--reach', type=float, default=480.0); ap.add_argument('--out')
    a = ap.parse_args()
    P = json.loads((Path(a.plan) / 'compact.P.json').read_text())
    core = {q: P[f'sucore_{q}'] for q in QS}
    hub = {q: P[f'vmh_{q}'] for q in QS}
    s0, s1, s2, s3 = (P[f'idx_s{i}'] for i in range(4))
    row = {'S': (s0['y'] + s0['h'] + s1['y']) / 2, 'N': (s3['y'] + s3['h'] + s2['y']) / 2}
    chx = {'W': (hub['SW']['x'] + hub['SW']['w'] + s0['x']) / 2, 'E': (s0['x'] + s0['w'] + hub['SE']['x']) / 2}
    side = lambda q: 'W' if q[1] == 'W' else 'E'
    half = lambda q: 'S' if q[0] == 'S' else 'N'
    face_x = lambda q: core[q]['x'] + core[q]['w'] if side(q) == 'W' else core[q]['x']   # channel-facing face

    def pin(q, k):           # k: route slot 0..3 on this face, staggered 12 um around the half's relay row
        y = row[half(q)] + (k - 1.5) * 12.0
        assert core[q]['y'] <= y <= core[q]['y'] + core[q]['h'], (q, y)
        return [round(face_x(q), 3), round(y, 3)]

    routes = []
    for q in QS:
        for d in QS:
            src, dst = pin(q, QS.index(d)), pin(d, QS.index(q))
            if q == d:
                pts = [src, dst]
            else:
                pts = [src, [chx[side(q)], src[1]]]
                if half(q) != half(d):
                    pts.append([chx[side(q)], row[half(d)]])
                if side(q) != side(d):
                    pts.append([chx[side(d)], row[half(d)]])
                pts += [[chx[side(d)], dst[1]], dst]
            L = sum(abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
            n = max(0, math.ceil(L / a.reach) - 1)
            homes, acc, seg = [], 0.0, 0
            # relay homes at equal spacing L/(n+1) along the path
            sp = L / (n + 1) if n else L
            for i in range(len(pts) - 1):
                (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                ln = abs(x1 - x0) + abs(y1 - y0)
                while ln > 0 and len(homes) < n and acc + ln >= sp * (len(homes) + 1) - 1e-6:
                    t = (sp * (len(homes) + 1) - acc) / ln
                    homes.append([round(x0 + (x1 - x0) * t, 1), round(y0 + (y1 - y0) * t, 1)])
                acc += ln
            routes.append(dict(src=q, dst=d, bits=BITS, src_pin=dict(block=f'sucore_{q}', ports='red_sv/red_tag/red_x', xy=src,
                               face='E' if side(q) == 'W' else 'W'), dst_pin=dict(block=f'sucore_{d}', ports='rf_wv/rf_wa/rf_wd', xy=dst,
                               face='E' if side(d) == 'W' else 'W'), path=pts, length_um=round(L, 1), stages_at_reach=n, relay_homes=homes))
    rf = max(r['stages_at_reach'] for r in routes)
    out = dict(schema='opentallas.hbm_die_v15.su_rf_route_pins.v1', plan=str(a.plan), reach_um=a.reach, RF_RELAY=rf,
               relay_rows=row, channel_x=chx, rule=__doc__.strip().splitlines()[2:6], routes=routes,
               relay_flops=sum(BITS * rf for r in routes), note='every route padded to RF_RELAY stages (static equal latency)')
    o = Path(a.out or Path(a.plan) / 'su_rf_route_pins.json'); o.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(RF_RELAY=rf, lengths={f"{r['src']}>{r['dst']}": r['length_um'] for r in routes}, relay_flops=out['relay_flops'], out=str(o))))


if __name__ == '__main__':
    main()
