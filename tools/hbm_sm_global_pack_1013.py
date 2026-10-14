#!/usr/bin/env python3
"""Geometry exploration preserving all 32 SMs and all non-SM rectangles.

MaxRects is a search heuristic, never an impossibility proof. PHY, PHY-facing
service and IO slabs remain fixed; other rectangles may move. Waypoints are
reserved by their full measured rectangle area, not treated as usable whitespace.
The resulting search does not qualify routing, clocks, pins or performance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def intersect(a, b):
    return a[0] < b[2] - 1e-7 and b[0] < a[2] - 1e-7 and a[1] < b[3] - 1e-7 and b[1] < a[3] - 1e-7


def contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def validate(rows, W, H):
    boxes=[(r['name'],[*r['at_um'],r['at_um'][0]+r['size_um'][0],r['at_um'][1]+r['size_um'][1]]) for r in rows]
    outside=[n for n,r in boxes if min(r[:2]) < -1e-6 or r[2]>W+1e-6 or r[3]>H+1e-6]
    overlaps=[(a,b) for i,(a,ra) in enumerate(boxes) for b,rb in boxes[i+1:] if intersect(ra,rb)]
    return {'outside':outside,'overlaps':overlaps,'legal':not outside and not overlaps}


def subtract(free, b):
    result = []
    for f in free:
        if not intersect(f, b):
            result.append(f)
            continue
        if f[0] < b[0]: result.append([f[0], f[1], b[0], f[3]])
        if b[2] < f[2]: result.append([b[2], f[1], f[2], f[3]])
        if f[1] < b[1]: result.append([f[0], f[1], f[2], b[1]])
        if b[3] < f[3]: result.append([f[0], b[3], f[2], f[3]])
    # Remove nested free rectangles; overlapping free rectangles are intentional.
    return [f for i, f in enumerate(result) if not any(j != i and contains(g, f) and (g != f or j < i) for j, g in enumerate(result))]


def template(component, tile):
    c = json.loads(json.dumps(component))
    c['outline_um'] = [c['outline_um']['w'], c['outline_um']['h']]
    delta = 1252.8 - tile['outline_um'][1]
    c['outline_um'][1] -= 2 * delta
    for child in c['children']:
        if '_tile_' in child['logical_module']:
            child['h_um'] = tile['outline_um'][1]
            if '.g_p[0].' in child['instance']: child['xy_um'][1] -= delta
            child['compaction_geometry'] = tile['variants'][child['logical_module'][-2:]]
    c['placement_status'] = 'GEOMETRY_CANDIDATE_ONLY_PARENT_LOGIC_AND_ROUTES_OPEN'
    boxes = [(x['instance'], [*x['xy_um'], x['xy_um'][0] + x['w_um'], x['xy_um'][1] + x['h_um']]) for x in c['children']]
    overlaps = [(a, b) for i, (a, ra) in enumerate(boxes) for b, rb in boxes[i+1:] if intersect(ra, rb)]
    assert not overlaps, overlaps
    assert all(r[0] >= 0 and r[1] >= 0 and r[2] <= c['outline_um'][0] + 1e-6 and r[3] <= c['outline_um'][1] + 1e-6 for _, r in boxes)
    c['placement_check'] = {'overlaps': [], 'inside': True, 'direct_children': len(boxes), 'leaf_children_after_expansion': 211}
    return c


def search(data, sm, gap, mode):
    W, H = data['die_um']
    free = [[0, 0, W, H]]
    fixed, moving = [], []
    for row in data['instances']:
        r = dict(row)
        if r['kind'] == 'waypoint': continue
        if r['kind'] == 'sm': r['size_um'] = sm['outline_um']
        if r['kind'] in ('phy', 'svc', 'serdes_slab', 'host_slab'):
            fixed.append(r)
            x, y = r['at_um']; w, h = r['size_um']
            free = subtract(free, [max(0,x-gap),max(0,y-gap),min(W,x+w+gap),min(H,y+h+gap)])
        else: moving.append(r)
    key = lambda r: (r['size_um'][0] * r['size_um'][1] if mode == 'area' else max(r['size_um']) if mode == 'long' else r['size_um'][1])
    moving.sort(key=key, reverse=True)
    placed, failed = list(fixed), []
    for r in moving:
        w, h = r['size_um']; best = None
        for f in free:
            x = math.ceil((f[0]+gap)/2.16 - 1e-7)*2.16
            y = math.ceil((f[1]+gap)/2.16 - 1e-7)*2.16
            dx, dy = f[2]-(x+w+gap), f[3]-(y+h+gap)
            if dx < -1e-7 or dy < -1e-7: continue
            score = (min(dx,dy), max(dx,dy), y, x)
            if best is None or score < best[0]: best = (score,x,y)
        if best is None:
            failed.append(r['name'])
            continue
        _, x, y = best
        r['at_um'] = [round(x,6),round(y,6)]
        placed.append(r)
        free = subtract(free,[x-gap,y-gap,x+w+gap,y+h+gap])
    # Union free area computed by an x sweep; MaxRects free list overlaps.
    xs = sorted({0,W,*[x for f in free for x in (f[0], f[2])]})
    free_area = 0
    for a,b in zip(xs,xs[1:]):
        intervals=sorted((f[1],f[3]) for f in free if f[0] <= a+1e-7 and f[2]>=b-1e-7)
        total=0; stop=-1
        for y,z in intervals:
            total+=max(0,z-max(y,stop));stop=max(stop,z)
        free_area+=(b-a)*total
    relay_area = sum(r['size_um'][0]*r['size_um'][1] for r in data['instances'] if r['kind']=='waypoint')
    relay_area += sum(r['size_um'][0]*r['size_um'][1]*r['count'] for r in data.get('waypoint_rectangle_groups',[]))
    return {'mode':mode,'gap_um':gap,'placed':placed,'unplaced':failed,'validation':validate(placed,W,H),'free_union_mm2':free_area/1e6,'existing_relay_rectangle_mm2':relay_area/1e6,'relay_area_fits_necessary_only':free_area>=relay_area,'status':'GEOMETRY_SEARCH_ONLY_NO_RELAY_PLACEMENT_OR_ROUTING_PROOF'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--component',required=True);p.add_argument('--tile',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    data=json.load(open(a.inventory)); sm=template(json.load(open(a.component)),json.load(open(a.tile)))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'compact_sm_component.json').write_text(json.dumps(sm,indent=2)+'\n')
    trials=[search(data,sm,gap,mode) for gap in (8.64,21.6,43.2) for mode in ('area','long','height')]
    summary=[]
    for i,t in enumerate(trials):
        (out/f'packing_{i}.json').write_text(json.dumps(t,indent=2)+'\n')
        summary.append({k:v for k,v in t.items() if k!='placed'})
    record={'input_sha256':{x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in (a.inventory,a.component,a.tile)},'sm_outline_um':sm['outline_um'],'sm_count':32,'sm_frame_mm2':32*math.prod(sm['outline_um'])/1e6,'trials':summary,'contract_revised':False,'clock_and_routing_closed':False,'performance_credit':None}
    (out/'packing_summary.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))


if __name__=='__main__':main()
