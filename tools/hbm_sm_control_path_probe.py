#!/usr/bin/env python3
"""Candidate owner/descriptor flight geometry; never a routed timing claim.

Both endpoints are exterior centres beside planned logical WEST bay faces.
Every bay remains an obstruction, including the source and destination bays.
Actual owner/adapter BPins and simultaneous dual-copy station packing are gates.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from hbm_relay_channel_model import channel_path


def portal(box, orient, clearance):
    if orient not in ('R0', 'MX', 'MY', 'R180'):
        raise ValueError('unsupported bay orientation')
    return (box[2] + clearance if orient in ('MY', 'R180') else box[0] - clearance,
            (box[1] + box[3]) / 2)


def price_path(path, max_segment_um=300):
    if max_segment_um <= 0:
        raise ValueError('positive segment budget required')
    lengths = []
    for a, b in zip(path, path[1:]):
        if a[0] != b[0] and a[1] != b[1]:
            raise ValueError('nonrectilinear flight')
        lengths.append(abs(a[0]-b[0]) + abs(a[1]-b[1]))
    if not lengths or min(lengths) <= 0:
        raise ValueError('nonempty nonzero links required')
    links = sum(math.ceil(length / max_segment_um) for length in lengths)
    # Capture at both portals, with a register at each bend and subdivision.
    stages = links + 1
    return dict(path_length_um=sum(lengths), registered_links=links,
                forward_register_stages=stages, reverse_register_stages=stages,
                descriptor_bridge_HOPS=stages,
                earliest_consumed_ack_edges=2*stages+2,
                dual_copy_forward_bits_per_stage=114,
                dual_copy_reverse_bits_per_stage=6,
                flight_register_bits=120*stages,
                descriptor_bridge_total_register_bits=120*stages+239,
                destination_fifo_register_bits=232,
                destination_fifo_depth_per_copy=2,
                fifo_sizing_contract='one parent descriptor pending; ACK only after actual consumption',
                hop_scope='constructive path; each bend registered; not minimum-hop optimization')


def probe(data, clearance=12.16, max_segment_um=300):
    by = {i['name']:i for i in data['insts']}
    obstacles = [(i['name'], i.get('box_um', [i['x'],i['y'],i['x']+i['w'],i['y']+i['h']]))
                 for i in data['insts']]
    for key in ('native_owner_bays','native_descriptor_bays','result_pin_bays'):
        obstacles += [(key+':'+b['sm'],b['box_um']) for b in data[key]]
    owners = {b['sm']:b['box_um'] for b in data['native_owner_bays']}
    adapters = {b['sm']:b['box_um'] for b in data['native_descriptor_bays']}
    if set(owners) != set(adapters):
        raise ValueError('owner/adapter identity mismatch')
    rows = []
    for sm, box in owners.items():
        source, sink = portal(box,by[sm]['orient'],clearance), portal(adapters[sm],by[sm]['orient'],clearance)
        row = dict(sm=sm, orientation=by[sm]['orient'],source_portal_um=source,sink_portal_um=sink)
        row['portal_obstacles'] = {
            side:[name for name,(x0,y0,x1,y1) in obstacles
                  if x0-clearance < p[0] < x1+clearance and y0-clearance < p[1] < y1+clearance]
            for side,p in [('source',source),('sink',sink)]}
        try:
            path = channel_path(source,sink,[b for _,b in obstacles],(data['geo']['W'],data['geo']['H']),clearance)
            row.update(path_um=path,reverse_path_um=list(reversed(path)),**price_path(path,max_segment_um))
        except ValueError as exc:
            row['failure'] = str(exc)
        rows.append(row)
    return dict(schema='opentallas.hbm_sm_control_path_probe.v1',
        status='candidate geometry only; not adopted',
        assumed_station_shape_um=[20,20], clearance_um=clearance,
        max_link_design_um=max_segment_um,forward_physical_bits=114,reverse_physical_bits=6,
        obstacle_count=len(obstacles), owner_bay_count=len(owners),adapter_bay_count=len(adapters),
        successful_paths=sum('failure' not in r for r in rows),rows=rows,
        gates=['actual owner/adapter flight BPins and <=100um final reach',
               'dual protected-copy simultaneous station placement and routing',
               'shared result/control/clock/PDN track capacity',
               'full-width exact RTL and negative controls at selected HOPS',
               'routed SS setup >=15ps / FF hold >=15ps under real interface budgets',
               'descriptor traversals and consumption stalls composed in token latency model'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    out=probe(json.loads(args.geometry.read_text()))
    sources=[args.geometry,Path(__file__),Path(__file__).with_name('hbm_relay_channel_model.py')]
    out['sources']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'successful_paths':out['successful_paths'],'failures':[(r['sm'],r['portal_obstacles'],r['failure']) for r in out['rows'] if 'failure' in r]}))

if __name__=='__main__':main()
