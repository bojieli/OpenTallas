#!/usr/bin/env python3
"""Prospective DMA-only service tile pin plans; never rewrite released views.

Use --out DIR to write additive records. These are reservations, not hardened
views: no route is admitted without measured area, legal die placement, RTL
relay instances, bandwidth proof and the normal timing/transaction gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOP = 380.0
PITCH = 0.192
HEIGHT = 240.0
PORTS = [('lane', 2160, 'output'), ('req', 51, 'input'),
         ('credit', 8, 'input'), ('ready', 1, 'output')]


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def edge_ports(width, reverse=False):
    """Two sparse horizontal layers, 1,110 traffic pins per face per layer."""
    ports = {}
    for face in ('W', 'E'):
        index = 0
        for bus, bits, direction in PORTS:
            pins = []
            for bit in range(bits):
                layer = ('M4', 'M6')[index % 2]
                y = round(8.064 + (index // 2) * PITCH, 4)
                x = 0 if face == 'W' else width - 0.192
                pins.append([f'{bus}_{face}[{bit}]', layer, round(x, 4), y,
                             round(x + 0.192, 4), round(y + 0.024, 4)])
                index += 1
            # A forwarding seam receives from W and transmits to E; req and
            # credit return in the opposite direction. Final joins select lanes.
            outface = 'W' if reverse else 'E'
            d = direction if face == outface else ('input' if direction == 'output' else 'output')
            ports[f'{bus}_{face}'] = dict(bits=bits, direction=d, face=face,
                                        dir_segments=[[0, bits, 'in' if d == 'input' else 'out']],
                                        layer='M4/M6', pins=pins)
        for name, y, direction in [('ck', HEIGHT / 2, 'input'), ('rst', 4.032, 'input')]:
            x = 0 if face == 'W' else width - 0.192
            ports[f'{name}_{face}'] = dict(bits=1, direction=direction, face=face, layer='M5',
                pins=[[f'{name}_{face}[0]', 'M5', round(x, 4), y, round(x+0.192, 4), y+0.024]])
    return ports


def validate_pins(ports, width):
    by = {}
    for p in ports.values():
        for q in p['pins']:
            assert 0 <= q[2] < q[4] <= width + 1e-6 and 0 <= q[3] < q[5] <= HEIGHT
            key = (p['face'], q[1])
            for other in by.setdefault(key, []):
                assert not overlap(q[2:6], other[2:6]), (q, other)
            by[key].append(q)
    return {f'{face}/{layer}': len(pins) for (face, layer), pins in by.items()}


def relay_path(points, cuts=()):
    """Explicit anchored endpoints, <=380um wires, and two captures per seam.

    Cuts apply only to service-local horizontal paths. Points supplied for
    front legs are a rectilinear proposal whose corridor occupancy is gated.
    """
    stages = [dict(xy_um=list(points[0]), role='source_pin_capture')]
    for start, end in zip(points, points[1:]):
        assert start[0] == end[0] or start[1] == end[1]
        boundaries = [start]
        if start[1] == end[1]:
            xs = sorted((x for x in cuts if min(start[0],end[0]) < x < max(start[0],end[0])),
                        reverse=end[0] < start[0])
            boundaries += [(x, start[1]) for x in xs]
        boundaries.append(end)
        for a, b in zip(boundaries, boundaries[1:]):
            distance = abs(b[0]-a[0])+abs(b[1]-a[1])
            n = max(1, math.ceil(distance/HOP))
            for i in range(1,n+1):
                xy = [round(a[j]+(b[j]-a[j])*i/n,4) for j in (0,1)]
                stages.append(dict(xy_um=xy, role='seam_output_pin' if b != end and i == n else 'relay'))
            if b != end:
                stages.append(dict(xy_um=list(b), role='seam_input_pin'))
    stages[-1]['role'] = 'destination_pin_capture'
    max_hop=max(abs(a['xy_um'][0]-b['xy_um'][0])+abs(a['xy_um'][1]-b['xy_um'][1])
                for a,b in zip(stages,stages[1:]))
    assert max_hop <= HOP + 0.001
    return dict(stages=stages, cycles=len(stages), max_wire_hop_um=round(max_hop,4),
                manhattan_um=sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:])))


def plan(root=ROOT, credits=64):
    import hbm_accel_die_fp as F
    svc=root/'physical/hbm_accel_die_views/svc'
    split=json.loads((svc/'split_psfc/split.json').read_text())
    geometry=json.loads((svc/'svc_geometry.json').read_text())
    die=F.build(F.R25GPH,geometry_only=True)
    insts=die['insts']
    loader=next(i for i in insts if i.master == 'hfd_loader')
    stacks={i.name[-2:]:i for i in insts if i.master in ['hfd_svc_'+s for s in ('SW','SE','NW','NE')]}
    result=dict(schema=1, status='PROSPECTIVE_DMA_ONLY_PHYSICAL_RESERVATION',
                source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [svc/'split_psfc/split.json',svc/'svc_geometry.json',root/'tools/hbm_accel_die_fp.py']},
                hop_um=HOP, pitch_um=PITCH, layers=['M4','M6'], lane_bits=2160,
                request_bits=51, credit_bits=8, ready_bits=1, edge_traffic_bits=2220,
                initial_credits=credits, loader=dict(name=loader.name,x_um=loader.x,y_um=loader.y,
                    w_um=loader.w,h_um=loader.h), families={}, stacks={}, route_admission=False,
                gates=['new tile RTL pins and relay instances match these records',
                       'measured cell area fits at <=60% utilization',
                       'resolve all proposed die placement/corridor conflicts',
                       'front endpoint physical pin allocation and clock-root lockups',
                       '>=90% bandwidth with composed actual credits/RTT',
                       'transaction exactness and in-context timing/DRC'])
    for family in ('SW','SE'):
        bands=split['parents']['hfd_svc_'+family]['bands']
        family_tiles=[]
        cuts=[]
        for j,band in enumerate(bands):
            b=split['bands'][band]
            old=json.loads((svc/'split_psfc'/band/'ports.json').read_text())
            width=old['w_um']
            ports=edge_ports(width, reverse=family == 'SE')
            count=validate_pins(ports,width)
            old_counts={}
            for p in old['ports'].values():
                if p.get('face') in ('W','E'):
                    for q in p['pins']:
                        key=p['face']+'/'+q[1];old_counts[key]=old_counts.get(key,0)+1
            pcids=[p for p,x in enumerate(geometry['hfd_svc_'+family]['pc_x'])
                   if b['x0_um'] <= x <= b['x0_um']+width]
            family_tiles.append(dict(master=f'hfd_svc_dma_{family}_s{j}',kind='svc_dma',
                x0_um=b['x0_um'],w_um=width,h_um=HEIGHT,ports=ports,
                face_pin_counts=count,existing_service_face_pin_counts=old_counts,pc_ids=pcids,
                storage_bits=8192*len(pcids),cell_area_um2=None,
                cell_area_capacity_um2=round(width*HEIGHT*0.60,3),
                implementation='separate DMA companion; no existing port moved or replaced',
                fit='PASS pin rectangles; HOLD measured cells/die placement/timing'))
            if j: cuts.append(b['x0_um'])
        pcs=geometry['hfd_svc_'+family]['pc_x']
        # Preserve the actual released expert descriptor position as the
        # prospective DMA front anchor rather than inventing an edge endpoint.
        e_pins=[]
        for band in bands:
            old=json.loads((svc/'split_psfc'/band/'ports.json').read_text())
            for name, mapping in split['parents']['hfd_svc_'+family]['port_map'][band].items():
                if mapping['parent_port']=='e':
                    e_pins += [((p[2]+p[4])/2+split['bands'][band]['x0_um'], (p[3]+p[5])/2)
                               for p in old['ports'][name]['pins']]
        assert e_pins, ('no actual descriptor pin anchor',family)
        front_x=sum(x for x,y in e_pins)/len(e_pins)
        lanes=[sum(pcs[4*k:4*k+4])/4 for k in range(8)]
        result['families'][family]=dict(tiles=family_tiles,cut_x_um=cuts,
            front_anchor='actual released e descriptor port x; new DMA pins still required',
            front_local_xy_um=[front_x,HEIGHT/2],lane_tile_local_xy_um=[[x,HEIGHT/2] for x in lanes],
            pc_to_lane=[relay_path([(x,HEIGHT/2),(lanes[p//4],HEIGHT/2)],cuts) for p,x in enumerate(pcs)],
            lane_to_front=[relay_path([(x,HEIGHT/2),(front_x,HEIGHT/2)],cuts) for x in lanes])
    for stack,i in stacks.items():
        fam='SW' if stack[1]=='W' else 'SE'
        f=result['families'][fam]
        # Reserve outside the service face; actual intersection checks below
        # retain conflicts rather than quietly moving the hardened neighbors.
        y=i.y-HEIGHT if stack[0]=='S' else i.y+i.h
        reservations=[]
        for tile in f['tiles']:
            box=[i.x+tile['x0_um'],y,i.x+tile['x0_um']+tile['w_um'],y+HEIGHT]
            conflicts=[n.name for n in insts if n.name!=i.name and overlap(box,[n.x,n.y,n.x+n.w,n.y+n.h])]
            reservations.append(dict(master=tile['master'],bbox_um=box,conflicting_instances=conflicts))
        target=(i.x+f['front_local_xy_um'][0],y+HEIGHT/2)
        launch=(loader.x if stack[1]=='W' else loader.x+loader.w,loader.y+loader.h/2)
        # Closest-side orthogonal front corridor is proposed explicitly. It
        # still needs track ownership, pin allocation and placement qualification.
        front=relay_path([launch,(target[0],launch[1]),target])
        internal=max(p['cycles'] for p in f['lane_to_front'])+max(p['cycles'] for p in f['pc_to_lane'])
        rtt=2*(front['cycles']+internal)+2
        result['stacks'][stack]=dict(reservations=reservations,front_leg=front,
            internal_one_way_cycles_bound=internal,composed_credit_rtt_cycles_bound=rtt,
            credit_utilization_upper_bound=min(1,credits/rtt),
            minimum_credits_for_90pct=math.ceil(.9*rtt),
            next_power_of_two_credit_depth=2**math.ceil(math.log2(rtt)),
            placement_fit=all(not r['conflicting_instances'] for r in reservations),
            front_corridor_fit='HOLD: endpoint pin and track allocation not measured')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--credits',type=int,default=64)
    args=parser.parse_args()
    result=plan(credits=args.credits)
    if args.out:
        args.out.mkdir(parents=True,exist_ok=True)
        for family in result['families'].values():
            for tile in family['tiles']:
                directory=args.out/tile['master'];directory.mkdir(exist_ok=True)
                (directory/'ports.json').write_text(json.dumps(tile,indent=2)+'\n')
                commands=[]
                for port in tile['ports'].values():
                    for pin in port['pins']:
                        commands.append('place_pin -pin_name {%s} -layer %s -location {%.4f %.4f} -pin_size {%.4f %.4f}'%
                            (pin[0],pin[1],(pin[2]+pin[4])/2,(pin[3]+pin[5])/2,pin[4]-pin[2],pin[5]-pin[3]))
                (directory/'io_place.tcl').write_text('\n'.join(commands)+'\n')
        (args.out/'dma_physical.json').write_text(json.dumps(result,indent=2)+'\n')
    summary={k:v for k,v in result.items() if k not in ('families','stacks')}
    summary['stacks']={s:{k:v for k,v in x.items() if k not in ('reservations','front_leg')} for s,x in result['stacks'].items()}
    for stack,x in result['stacks'].items():
        summary['stacks'][stack]['front_leg_cycles']=x['front_leg']['cycles']
        summary['stacks'][stack]['front_leg_um']=x['front_leg']['manhattan_um']
        summary['stacks'][stack]['placement_conflicts']=sorted(set(n for r in x['reservations'] for n in r['conflicting_instances']))
    summary['tiles_per_family']={f:len(x['tiles']) for f,x in result['families'].items()}
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
