#!/usr/bin/env python3
"""Exact rectangular-obstacle RF route witness using centre-facing qcore pins.

Production port ABI: red_rf_v, red_tag[7:0], red_x -> destination q's
rf_wv[source], rf_wa[8*source+:8], rf_wd[32*source+:32]. Forty-one bits.
This is geometric evidence only: actual relay masters, clocks and routing remain
required before adoption. It never substitutes a 500um rule for measured reach.
"""
import argparse
import json
import math
from pathlib import Path

QS = ['SW', 'SE', 'NW', 'NE']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    a = ap.parse_args()
    d = Path(a.plan)
    p = json.loads((d / 'compact.P.json').read_text())
    south = max(p[f'vmh_{q}']['y'] + p[f'vmh_{q}']['h'] for q in ['SW', 'SE']) + 20
    north = min(p[f'vmh_{q}']['y'] for q in ['NW', 'NE']) - 20
    xw = (p['vmh_SW']['x'] + p['vmh_SW']['w'] + p['idx_s0']['x']) / 2
    xe = (p['idx_s0']['x'] + p['idx_s0']['w'] + p['vmh_SE']['x']) / 2
    # cross corridors: mid-gap between idx_s1 and the lowest centre-column block above it, and between the highest
    # block below idx_s3 and idx_s3 (= the idx_q gaps when only the IDX glue row sits there; a centre hc_eng moves them)
    s1t, s3b = p['idx_s1']['y'] + p['idx_s1']['h'], p['idx_s3']['y']
    x0c, x1c = p['idx_s1']['x'], p['idx_s1']['x'] + p['idx_s1']['w']
    mid = [b for b in p.values() if b['x'] < x1c and b['x'] + b['w'] > x0c and b['y'] >= s1t - 1e-6 and b['y'] + b['h'] <= s3b + 1e-6]
    cross = (s1t + min(b['y'] for b in mid)) / 2
    cross_n = (max(b['y'] + b['h'] for b in mid) + s3b) / 2

    def pin(q, index):
        b = p[f'sucore_{q}']
        return [round(b['x'] + b['w']/2 + index * 12, 3),
                round(b['y'] + b['h'] if q.startswith('S') else b['y'], 3)]

    def hits(a, b, own):
        bad = []
        for n, r in p.items():
            if n in own:
                continue
            x0, x1, y0, y1 = r['x'], r['x']+r['w'], r['y'], r['y']+r['h']
            if abs(a[0]-b[0]) < 1e-6:
                hit = x0 < a[0] < x1 and max(min(a[1],b[1]), y0) < min(max(a[1],b[1]), y1)-1e-6
            else:
                hit = y0 < a[1] < y1 and max(min(a[0],b[0]), x0) < min(max(a[0],b[0]), x1)-1e-6
            if hit:
                bad.append(n)
        return bad

    routes = []
    for q in QS:
        for dst in QS:
            s, t = pin(q, -3), pin(dst, QS.index(q)-1)
            ys, yt = (south if q.startswith('S') else north), (south if dst.startswith('S') else north)
            xs, xt = (xw if q.endswith('W') else xe), (xw if dst.endswith('W') else xe)
            if q == dst:
                pts = [s, t]
            else:
                pts = [s, [s[0], ys], [xs, ys]]
                if xs != xt:
                    row = cross_n if q.startswith('N') and dst.startswith('N') else cross
                    pts += [[xs, row], [xt, row]]
                pts += [[xt, yt], [t[0], yt], t]
            pts = [[round(x,3),round(y,3)] for x,y in pts]
            pts = [v for k,v in enumerate(pts) if not k or v != pts[k-1]]
            length = sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(pts,pts[1:]))
            stages = max(0, math.ceil(length/480)-1)
            failures = [(i,n) for i,(a,b) in enumerate(zip(pts,pts[1:]))
                        for n in hits(a,b,{f'sucore_{q}',f'sucore_{dst}'})]
            homes = []
            step = length/(stages+1)
            used = 0
            for a,b in zip(pts,pts[1:]):
                segment = abs(b[0]-a[0])+abs(b[1]-a[1])
                while segment and len(homes)<stages and used+segment >= (len(homes)+1)*step-1e-7:
                    f = ((len(homes)+1)*step-used)/segment
                    homes.append([round(a[0]+f*(b[0]-a[0]),3),round(a[1]+f*(b[1]-a[1]),3)])
                used += segment
            routes.append(dict(source=q,destination=dst,bits=41,path=pts,length_um=round(length,3),
                               stages=stages,hop_um=round(step,3),relay_homes=homes,hard_crossings=failures))
    out = dict(schema='opentallas.hbm.rf_centre.v1',qualification='GEOMETRY_ONLY_NO_NATIVE_OR_ROUTE_VIEW',
               source_port='red_rf_v,red_tag[7:0],red_x',destination_port='rf_wv[q],rf_wa[8q+:8],rf_wd[32q+:32]',
               RF_RELAY_required=max(x['stages'] for x in routes), RF_RELAY_production=36,
               obstacles_clear=not any(x['hard_crossings'] for x in routes),
               corridors=dict(south=south,north=north,west=xw,east=xe,cross=cross,cross_north=cross_n), routes=routes,
               open=['source-bound exact per-bit qcore pin grant','relay cell footprints and cut','measured clock compensation/reach','TT/FF/DRC0','compiler padding and native reproof'])
    (d/'rf_centre_routes.json').write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:out[k] for k in ['RF_RELAY_required','RF_RELAY_production','obstacles_clear','corridors']}))
    print([(x['source'],x['destination'],x['stages'],x['hard_crossings']) for x in routes])


if __name__ == '__main__':
    main()
