#!/usr/bin/env python3
"""Analytical child rectangles inside current KVC reservations; no mutation/adoption.
Consumes source-pinned pre-relay rectangle inventory. Existing native KVC masters
remain functional obligations; a containing placeholder is not a free macro slot.
"""
import argparse, hashlib, json, math
from pathlib import Path


def plan(inventory):
    rects = inventory['rectangles']
    eps = 1e-7
    parents = [r for r in rects if r['name'].startswith('lfifo_')]
    children = []
    for p in parents:
        engine_y = math.floor((p['y'] + (p['h'] - 2000.16)/2)/2.16 + eps)*2.16
        for suffix, y, h, master in [('engine', engine_y, 2000.16, 'qfd_emb_strip_bus92'),
                                    ('far', engine_y-1401.84, 1401.84, 'qfd_emb_far92')]:
            c = dict(name=p['name']+'_'+suffix, parent=p['name'], master=master,
                     x=p['x'], y=round(y, 6), w=92.016, h=h)
            if not (c['x'] >= p['x']-eps and c['y'] >= p['y']-eps and
                    c['x']+c['w'] <= p['x']+p['w']+eps and
                    c['y']+c['h'] <= p['y']+p['h']+eps):
                raise ValueError('candidate child escapes actual parent '+c['name'])
            collisions = []
            for other in rects:
                if other['name'] == p['name']:
                    continue
                if (min(c['x']+c['w'], other['x']+other['w']) > max(c['x'],other['x'])+eps
                        and min(c['y']+c['h'],other['y']+other['h']) > max(c['y'],other['y'])+eps):
                    collisions.append(other['name'])
            c['other_existing_rectangles_overlapped'] = collisions
            children.append(c)
    if len(parents) != 4:
        raise ValueError('four actual KVC parents required')
    for a in children:
        for b in children:
            if a['name'] >= b['name']:
                continue
            if (min(a['x']+a['w'],b['x']+b['w']) > max(a['x'],b['x'])+eps
                    and min(a['y']+a['h'],b['y']+b['h']) > max(a['y'],b['y'])+eps):
                raise ValueError('candidate child overlap')
    return dict(schema='opentallas.embedding_existing_strip_rectangle_plan.v1',
                status='ANALYTICAL_GEOMETRY_ONLY', die=inventory['die'], parents=parents,
                children=children, outline_addition_um=0,
                child_rectangles_mm2=sum(c['w']*c['h'] for c in children)/1e6,
                added_die_area_mm2=0,
                old_KVC_replaced=False, actual_ports_bound=False, physical_closed=False,
                headline_credit=0, source_removed_ROM=inventory.get('r21c', {}).get('removed'),
                obligations=['actual native KVC function/interfaces must survive replacement',
                             'real engine/far hardened views and actual pin/station binding',
                             'node/control/native KV/stations fit in the remaining real rectangles',
                             'actual die compaction/host/PLL sheet meets current <=~845 target',
                             'freed ROM rectangle cannot be numerically subtracted from die outline'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inventory', type=Path)
    ap.add_argument('out', type=Path)
    args = ap.parse_args()
    result = plan(json.loads(args.inventory.read_text()))
    result['inventory_sha256'] = hashlib.sha256(args.inventory.read_bytes()).hexdigest()
    result['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status':result['status'], 'parents':len(result['parents']),
                      'children':len(result['children']), 'die':result['die'],
                      'overlaps':[(c['name'],c['other_existing_rectangles_overlapped'])
                                  for c in result['children'] if c['other_existing_rectangles_overlapped']]}))

if __name__ == '__main__':
    main()
