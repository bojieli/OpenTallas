#!/usr/bin/env python3
"""Price full native result storage in vacant physical SM sites; never admit it."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) + 1e-6 and min(a[3], b[3]) > max(a[1], b[1]) + 1e-6


def build(placement, provider):
    insts = {i['name']: i for i in placement['insts']}
    if provider['macro_count'] != 40 or provider['rows'] != 4096 or provider['row_bits'] != 256:
        raise ValueError('requires the actual full 4096-row provider')
    sw, sh, gap = 740.016, 501.12, 8.64
    mw, mh, halo = 130.896, 34.83, 2.16
    block_w, block_h = 4*sw+3*gap, 2*sh+gap
    slots, sites, conflicts = [], [], []
    keepouts = [(key, row['box_um']) for key in ('result_pin_bays', 'native_owner_bays',
                 'native_descriptor_bays', 'native_control_escape_bays', 'native_control_u_corridors')
                for row in placement.get(key, [])]
    for base in range(0, 32, 8):
        # Derive the empty site from actual occupied column/row coordinates, not
        # a nominal row-pitch formula (the south first-row gap differs).
        col, row = insts[f'sm{base+2}'], insts[f'sm{base+6}']
        if any(abs(insts[f'sm{base+k}'][a]-v)>1e-6
               for k in range(8) for a,v in [('w',3075.84),('h',1131.84)]):
            raise ValueError('actual SM dimensions changed; reprice the vacant site')
        x, y = col['x'], row['y']
        sites.append(dict(sm_group_start=base, box_um=[x,y,x+3075.84,y+1131.84]))
        # Lower/left aligned native grid, leaving all unused slack explicit.
        for k in range(8):
            sx, sy = x+(k%4)*(sw+gap), y+(k//4)*(sh+gap)
            box = [round(v,6) for v in (sx,sy,sx+sw,sy+sh)]
            macro_boxes=[]
            for mr in range(8):
                for mc in range(5):
                    mx=sx+halo+mc*(mw+2*halo)
                    my=sy+halo+mr*(mh+2*halo)
                    macro_boxes.append([round(v,6) for v in (mx,my,mx+mw,my+mh)])
            assert all(b[0]-halo>=sx-1e-6 and b[1]-halo>=sy-1e-6 and
                       b[2]+halo<=sx+sw+1e-6 and b[3]+halo<=sy+sh+1e-6 for b in macro_boxes)
            assert not any(overlap(a,b) for j,a in enumerate(macro_boxes) for b in macro_boxes[j+1:])
            hits=[i['name'] for i in insts.values() if overlap(box,i['box_um'])]
            reservations=[name for name,b in keepouts if overlap(box,b)]
            conflicts.extend(dict(store=f'result_store_sm{base+k}', instance=n) for n in hits)
            slots.append(dict(name=f'result_store_sm{base+k}', source_sm=f'sm{base+k}',
                box_um=box, macro_boxes_um=macro_boxes, existing_macro_conflicts=hits,
                existing_reservation_conflicts=reservations))
    assert len(slots)==32 and sum(len(s['macro_boxes_um']) for s in slots)==1280
    assert not any(overlap(a['box_um'],b['box_um']) for j,a in enumerate(slots) for b in slots[j+1:])
    return dict(schema='opentallas.hbm.result_store_reservation.v1', selected=False,
        status='MODEL_ONLY_RELOCATION_AND_TRANSPORT_UNQUALIFIED', compute_macs_per_cycle=0,
        replicas=32, site_shape_um=[3075.84,1131.84], store_shape_um=[sw,sh],
        grid_um=[.432,2.16], slots_per_site=8, populated_rectangle_um=[block_w,block_h],
        sites=sites, stores=slots, total_reservation_um2=32*sw*sh,
        macro_count=1280, macro_raw_area_um2=32*provider['macro_area_um2'],
        macro_halo_um=halo, macro_grid_pitch_um=[mw+2*halo,mh+2*halo],
        cell_budget_per_store_at_55pct_um2=sw*sh*.55,
        unmeasured_control_budget_per_store_um2=sw*sh*.55-provider['macro_area_um2'],
        macro_bank_read_mux_2to1_bits_per_store=provider['macro_read_mux_2to1_bit_cells'],
        capture_bits_per_cycle_per_store=269, capture_payload_bytes_per_cycle_per_store=32,
        capture_payload_bytes_per_cycle_all_stores=1024, macro_read_write_bytes_per_cycle_per_store=40,
        request_bits_per_store=312,response_bits_per_store=276,
        source_memory_fanout=dict(address=40,data=8),
        corridor_gap_um=gap, optimistic_3layer_tracks_per_gap=int(gap*(1/.048+1/.064+1/.080)),
        shared_track_admission=False,
        latency=dict(reservation_setup_cycles=64,capture_cycles=4096,
            capture_transport_cycles=None,drain_cycles=provider['drain_total_cycles'],
            publication='only after all exact installed-address writes and readbacks complete',
            note='No adopted rate: transport, arbitration, codec and installed-destination latency remain unbound.'),
        existing_macro_conflicts=conflicts,
        waypoint_relocations_required=sorted({c['instance'] for c in conflicts}),
        remaining_gates=['relocate named waypoints without deleting any existing network functionality',
            'rerun simultaneous control and protected-result station inventory with all 32 stores as obstacles',
            'bind actual SM capture pins to protected no-ready per-store transport; reserve all shared tracks',
            'map and place full control, SECDED, bitmap and 320-bit memory selection logic',
            'bind installed-address write/readback provider and finite arbitration',
            'actual clock entries, source power, SS setup and FF hold with 60/25ps uncertainty'],
        physical_admitted=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--placement',required=True);ap.add_argument('--provider',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();p=Path(a.placement);q=Path(a.provider)
    placement=json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
    result=build(placement,json.loads(q.read_text()))
    result['source_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (p,q,Path(__file__))}
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','total_reservation_um2','waypoint_relocations_required')}))


if __name__=='__main__':main()
