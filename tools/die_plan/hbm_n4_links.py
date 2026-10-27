#!/usr/bin/env python3
"""Prepare exact N4 link requirements; never turn a missing root into an alias.

This is a plan-preparation tool, not a G0 verdict or a plan mutator. Its output
keeps the original orphan records and lists the missing physical contracts.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def box(origin, size, halo=0):
    x, y = origin
    w, h = size
    return [x-halo, y-halo, x+w+halo, y+h+halo]


def intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def obstacles(t):
    """Conservative bounding boxes include actual FT bit cells, not centres only."""
    out = []
    for key in ('hard_cores', 'contents'):
        for item in t.get(key, []):
            if 'origin_um' in item and 'outline_um' in item:
                out.append((key+':'+item['inst'], box(item['origin_um'], item['outline_um'], 4.32)))
    for key in ('ft_slots', 'internal_stations'):
        for i, item in enumerate(t.get(key, [])):
            cell = item.get('bit_site_cell_um', [1.404, .27])
            for j, sites in enumerate(item.get('bit_sites_um', [])):
                if sites:
                    xs, ys = zip(*sites)
                    out.append((f'{key}:{i}:bank{j}', [min(xs)-cell[0]/2, min(ys)-cell[1]/2,
                                                            max(xs)+cell[0]/2, max(ys)+cell[1]/2]))
            for j, xy in enumerate(item.get('regs_um', [])):
                out.append((f'{key}:{i}:reg{j}', box(xy, [1.404, .27], 4.32)))
    w, h = t['outline_um']
    for i, band in enumerate(t.get('die_ft_bands', [])):
        lo, hi = band['span_um']
        out.append((f'die_ft_bands:{i}', [lo, 0, hi, h] if band['dir']=='NS' else [0, lo, w, hi]))
    for item in t.get('clock', {}).get('taps', []):
        out.append(('clock:'+item.get('name', '?'), box(item['xy'], [0, 0], 4.32)))
    return out


def root_lots(t, size=(345.6, 345.6), target_y=5231.52):
    obs = obstacles(t)
    w, h = t['outline_um']
    # Scan a legal manufacturing grid, closest to the two abutting N4 faces first.
    step = 8.64
    candidates = []
    for yi in range(math.ceil(4.32/step), math.floor((h-size[1]-4.32)/step)+1):
        y = round(yi*step, 6)
        for xi in range(1, math.floor((w-size[0]-4.32)/step)+1):
            x = round(xi*step, 6)
            rect = box([x,y], size, 4.32)
            if any(intersects(rect, r) for _, r in obs):
                continue
            score = abs(y+size[1]/2-target_y)+abs(x+size[0]/2-w/2)
            candidates.append((score, x, y))
    return [{'origin_um':[x,y], 'outline_um':list(size), 'halo_um':4.32,
             'area_status':'historical model assumption; not measured N4EXT1 implementation',
             'score_um':round(s,6)} for s,x,y in sorted(candidates)[:8]]


def wrapper_ports(manifest):
    expected = {'up_nw': ('input',271,'u_native.uq0'),
                'up_ne': ('input',271,'u_native.uq2'),
                'down_nw': ('output',173,'u_native.dq0'),
                'down_ne': ('output',173,'u_native.dq2')}
    if manifest['module'] != 'ot_hnx_fused_hub_n4ext' or manifest['added_cycles'] != 0:
        raise ValueError('unexpected root wrapper or source latency')
    for name,(direction,width,identity) in expected.items():
        if manifest['ports'][name] != [direction,width] or manifest['port_identity'][name] != identity:
            raise ValueError('wrapper changes actual N4 pairing or bit width')
    return manifest['proposed_new_plan_instance']


def prepare(plan, abi, pins, manifest=None):
    expected = {('NW',271,'uo','uq0'), ('NW',173,'dq0','dn'),
                ('NE',271,'uo','uq2'), ('NE',173,'dq2','dn')}
    seen = set()
    if abi['root_module'] != 'ot_hnx_fused_hub' or abi['root_parameters']['N4EXT'] != 1:
        raise ValueError('requires the actual N4EXT1 hub ABI')
    root = plan['partition_types']['root']
    root_parts = [p for p in plan['partitions'] if p['type']=='root']
    if len(root_parts)!=1:
        raise ValueError('requires exactly one actual root partition')
    rp = root_parts[0]
    by_name = {p['name']:p for p in plan['partitions']}
    pins_by_name = {p['name']:p for p in pins}
    links = []
    root_inst = wrapper_ports(manifest) if manifest else None
    for link in abi['native_links']:
        side, width = link['side'], link['width']
        src, dst = link['source']['port'], link['destination']['port']
        key = side,width,src,dst
        if key not in expected or key in seen:
            raise ValueError(f'duplicate or unexpected ABI link {key}')
        seen.add(key)
        bm=link['bit_map']
        if bm != dict(kind='identity',source_lsb=0,destination_lsb=0,count=width,stride=1):
            raise ValueError('bit map is not the exact identity contract')
        t=plan['partition_types'][link['partition_type']]
        original=t['internal_stations'][link['orphan_station_index']]
        if original != link['symbolic_anchor']:
            raise ValueError(f'{side} orphan source changed: refresh exact ABI first')
        h=by_name[side+'_hub']
        if h['orient'] not in ('R0','MY') or rp['orient']!='R0':
            raise ValueError('unexpected orientation: rederive abutment')
        edge_x = h['origin_um'][0]+(t['outline_um'][0] if h['orient']=='R0' else 0)
        required_root_x=rp['origin_um'][0]+(0 if side=='NW' else root['outline_um'][0])
        if abs(edge_x-required_root_x)>1e-6:
            raise ValueError('hub and root no longer abut')
        up=width==271
        root_port=('up_' if up else 'down_')+side.lower()
        root_leaf=root_inst+'.'+root_port if root_inst else None
        bus=f'mu_n4_{side.lower()}_'+('up' if up else 'down')
        # Separate windows: <=6 pins/um even under a combined-layer interpretation.
        center=3472.0 if up else 3536.0
        length=47.52 if up else 30.24
        window=[round(center-length/2,6),round(center+length/2,6)]
        root_window=[round(v+h['origin_um'][1]-rp['origin_um'][1],6) for v in window]
        hc=next(c for c in t['hard_cores'] if c['inst']=='u_mu_fused_n4')
        nodeport='uo' if up else 'dn'
        actual=[(hc['origin_um'][0]+pins_by_name[f'{nodeport}[{b}]']['x'],
                 hc['origin_um'][1]+pins_by_name[f'{nodeport}[{b}]']['y']) for b in range(width)]
        regs=original['regs_um']
        endpoint_station=regs[0] if up else regs[-1]
        max_hop=max(abs(x-endpoint_station[0])+abs(y-endpoint_station[1]) for x,y in actual)
        links.append(dict(id=bus, width=width, epoch=False,
            epoch_status='ABI already contains validity; native START/valid transport proof remains required',
            source=link['source'], destination=link['destination'], bit_map=bm,
            hub_bus=dict(name=bus,dir='out' if up else 'in',width=width,kind='data',
                leaf='u_mu_fused_n4.'+nodeport,face='E',window_um=window,layers=['M4','M6'],order='lsb_low'),
            root_bus=dict(name=bus,dir='in' if up else 'out',width=width,kind='data',
                leaf=root_leaf,face='W' if side=='NW' else 'E',window_um=root_window,layers=['M4','M6'],order='lsb_low'),
            port=dict(id=bus,src=dict(part=h['name'] if up else rp['name'],bus=bus),
                dst=dict(part=rp['name'] if up else h['name'],bus=bus),width=width,kind='data',epoch=False),
            original_orphan=original,
            actual_pin_to_original_station_max_manhattan_um=round(max_hop,6),
            hub_station_status='must regenerate per-bit <=405 and macro-avoiding paths from actual pins to new window',
            root_station_status='requires actual root pins and provider placement; no guessed stations',
            external_station_depth_unpriced=True))
    if seen!=expected:
        raise ValueError('missing ABI link')
    providers=[c for key in ('contents','hard_cores') for c in root.get(key,[])
               if c['module']==(manifest['module'] if manifest else abi['root_module'])]
    missing=['measured N4EXT1 root master and pin abstract', 'native root instance and exact control/job bindings',
             'root clock/reset/START delivery and release offsets', 'actual per-bit <=405um station sites and macro-avoiding routes',
             'link station latency in token compiler/model and R8 alignment', 'window occupancy/density and PG/clock geometry review']
    if not providers:
        missing.insert(0,'real central root content/hard-core lot (current plan has no provider)')
    return dict(schema='opentallas.hbm-n4-link-prep.v1',route_ready=False,qualification='PLAN PREPARATION ONLY',
        root_provider_found=bool(providers),root_parameters=abi['root_parameters'],
        root_all_ports=manifest['ports'] if manifest else abi['root_all_ports'],
        root_wrapper=manifest, proposed_new_root_instance=root_inst,total_link_bits=sum(l['width'] for l in links),
        source_hashes=abi['sources'],links=links,root_lot_candidates=root_lots(root),
        lot_exclusions='hard cores, contents, actual FT bit-cell bank bounds, relay sites, clock taps, full die FT bands; halo4.32',
        remaining=missing)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',required=True,type=Path)
    ap.add_argument('--abi',required=True,type=Path)
    ap.add_argument('--n4-pins',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--root-manifest',type=Path)
    a=ap.parse_args()
    result=prepare(json.loads(a.plan.read_text()),json.loads(a.abi.read_text()),json.loads(a.n4_pins.read_text()),
                   json.loads(a.root_manifest.read_text()) if a.root_manifest else None)
    result['input_sha256']={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in
                            [('plan',a.plan),('abi',a.abi),('n4_pins',a.n4_pins)]}
    if a.root_manifest:
        result['input_sha256']['root_manifest']=hashlib.sha256(a.root_manifest.read_bytes()).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('route_ready','root_provider_found','total_link_bits','root_lot_candidates')}))

if __name__=='__main__':
    main()
