#!/usr/bin/env python3
"""H-D4G3b 10-18: d4g regional clock root sites (opentallas.die_clock.root_sites.v1) from the d4g region map -- one root
per region at the region's planned site, keepout +-HALF um (station-free box for relay_lanes / relay_layer).  Replaces
d4f_root_sites_r5 (d4f geometry) for the d4g relay layer.  With --manifest, a region whose site falls inside a placed
block is reported (the root must sit in a channel; die_case_v16 regional trees start at the same site).
    d4g_root_sites.py --region-map results/arch/hbm_die_d4g/d4g_region_map.json [--manifest M.json] --out R.json"""
import argparse, json

ap = argparse.ArgumentParser(); ap.add_argument('--region-map', required=True); ap.add_argument('--manifest')
ap.add_argument('--half', type=float, default=30.0); ap.add_argument('--out', required=True)
a = ap.parse_args()
M = json.load(open(a.region_map)); H = a.half
pl = json.load(open(a.manifest))['placement'] if a.manifest else {}
sites, inside = [], []
for r, v in sorted(M['regions'].items()):
    x, y = v['site']
    sites.append(dict(region=r, x=x, y=y, moved_um=0.0, planned=[x, y], keepout=[x - H, y - H, x + H, y + H],
                      note='d4g region site (d4g_region_map)'))
    for n, p in pl.items():
        if p['x'] < x < p['x'] + p['w'] and p['y'] < y < p['y'] + p['h']:
            inside.append([r, n]); break
json.dump(dict(schema='opentallas.die_clock.root_sites.v1', die='hbm_d4g', plan=M.get('plan'),
               rule='one root per d4g clock region at its region-map site; keepout +-%g um' % H, sites=sites,
               failed=[], inside_blocks=inside), open(a.out, 'w'), indent=1)
print('ROOT_SITES', len(sites), 'inside_blocks', len(inside))
