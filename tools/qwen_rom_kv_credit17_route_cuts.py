#!/usr/bin/env python3
"""One exact-track continuation of the fixed 17-credit KV7 allocation.

No source placement, extracted route, ideal PHY or service replay admission.
"""
import copy
import math
import re
from pathlib import Path
import qwen_rom_kv_credit17_physical as P
R=P.R
OUT=Path('results/uarch/qwen_rom_kv_credit17_routes_20261003')
TECH=Path('results/uarch/qwen_rom_mapped_root_pg_context_20261002/inputs/tech.lef')
TRACKS=TECH.parent/'make_tracks.tcl'


def centers(lo,hi,pitch,offset):
    return [offset+i*pitch for i in range(math.ceil((lo-offset)/pitch),math.ceil((hi-offset)/pitch))]


def layers():
    text=(R.ROOT/TECH).read_text();tracks=(R.ROOT/TRACKS).read_text();d={}
    for name in ['M6','M8','M9']:
        body=re.search(r'^LAYER '+name+r'\n(.*?)^END '+name+r'$',text,re.M|re.S)[1]
        direction=re.search(r'DIRECTION\s+(\w+)',body)[1]
        row=re.search(r'make_tracks '+name+r' -x_offset (\S+) -x_pitch (\S+) -y_offset (\S+) -y_pitch (\S+)',tracks)
        d[name]=dict(pitch=float(row[2 if direction=='VERTICAL' else 4]),offset=float(row[1 if direction=='VERTICAL' else 3]),direction=direction)
    return d


def price():
    parent=R.obj(P.OUT/'model-r4.json');m=copy.deepcopy(parent);tech=layers()
    bands=[]
    for row in parent['dedicated_fill_channels']:
        rect=row['rectangle_um'];available=[]
        for name in ['M6','M8']:
            assert tech[name]['direction']=='HORIZONTAL'
            raw=centers(rect[1],rect[3],tech[name]['pitch'],tech[name]['offset'])
            available.extend(dict(layer=name,coordinate_um=y) for y in raw[1::2])
        assert len(available)>=1360
        cursor=0;alloc={}
        for role,n in [('fill',1048),('shared_control',91),('clock',64),('reset_ACK',64),('spare',93)]:
            alloc[role]=available[cursor:cursor+n];cursor+=n
        bands.append(dict(name=row['name'],rectangle_um=rect,signal_capacity=len(available),
            allocated_tracks=alloc,PG_and_other_share='at least half of physical centers excluded',
            ownership_against_existing_routes_proven=False,pin_and_via_access_proven=False))
    #Four lane feeds per half: three local lanes plus the split lane6. These
    #cannot borrow the nearly full shoreline M9 trunks.
    demand=4*(1048+91+64+64)
    width=(demand+1)*2*tech['M9']['pitch']
    roots=[];route_buffers=0;route_wire=0;routes=[]
    for side in range(2):
        center=1700 if side==0 else parent['die']['width_um']-1700
        xs=centers(center-width/2,center+width/2,tech['M9']['pitch'],tech['M9']['offset'])[1::2]
        assert len(xs)>=demand
        lanes=[0,2,4,6] if side==0 else [1,3,5,6]
        trunk=dict(name=f'KV_FIELD_DELIVERY_M9_{side}',side=side,
            rectangle_um=[center-width/2,833.49,center+width/2,32131.89],
            signal_capacity=len(xs),demand=demand,lanes=lanes,layer='M9',allocations=[])
        i=0
        for lane in lanes:
            band=next(b for b in bands if b['name']==f'KV_FILL_CHANNEL_{lane}')
            #Source controller slots live in last row. Count the full worst
            #finite controller-slot-to-band span; no ideal boundary path.
            slot=parent['controller_slots'][side]
            source=[(slot['rectangle_um'][0]+slot['rectangle_um'][2])/2,slot['rectangle_um'][3]]
            landing=[center,band['rectangle_um'][1]+48.384]
            length=sum(abs(a-b) for a,b in zip(source,landing))
            segments=math.ceil(length/128)
            for role,n in [('fill',1048),('shared_control',91),('clock',64),('reset_ACK',64)]:
                trunk['allocations'].append(dict(lane=lane,role=role,x_centers_um=xs[i:i+n]));i+=n
                count=n*(segments+1);route_buffers+=count;route_wire+=n*(length+16)
                routes.append(dict(side=side,lane=lane,role=role,bits=n,length_um=length,
                    maximum_segment_um=128,segments_per_bit=segments,buffers=count,
                    source_pin_binding_complete=False,clock_reset_feed_timing_qualified=False))
        for shore in parent['shoreline_cuts']:
            a,b=shore['band_x_um']
            assert trunk['rectangle_um'][2]<=a or trunk['rectangle_um'][0]>=b
        roots.append(trunk)
    #Replace the original PHY/controller BUF4 lower bound with paid BUF8.
    #All previously charged cells stay charged once; only size delta is added.
    old=parent['route_buffer_reservation'];price=parent['credit17']['cell_prices_um2']
    existing_upgrade=old*(price['selected_BUF8']-price['BUF4'])/1e6
    extra=route_buffers*price['selected_BUF8']/1e6
    delta=existing_upgrade+extra
    source_families=dict(request=455,command=4*339,owned_receipt=8*467,reverse=8*404)
    typed=sum(source_families.values());untyped=43256-(4*typed+7*1048)
    assert untyped==804
    #Reserve the804 handoff bits without pretending their endpoint families
    #are known. Each stack's8980 bits remains below9209 abstract pin slots.
    shores=[]
    for oldshore in parent['shoreline_cuts']:
        lo,hi=oldshore['band_x_um'];raw=centers(lo,hi,tech['M9']['pitch'],tech['M9']['offset'])
        xs=raw[1::2];assert len(xs)>=18546
        slots=[];i=0
        for stack in [oldshore['side'],oldshore['side']+2]:
            families=[]
            for name,n in list(source_families.items())+[('untyped_parent_boundary',201),('unused_PHY_pin_allowance',229)]:
                families.append(dict(family=name,bits=n,x_centers_um=xs[i:i+n]));i+=n
            slots.append(dict(stack=stack,families=families,source_to_actual_PHY_pin_mapping_complete=False))
        control=xs[i:i+128];i+=128
        shores.append(dict(side=oldshore['side'],signal_capacity=len(xs),demand=i,
            stack_allocations=slots,clock_reset_ACK_x_centers_um=control,source_family_routes_proven=False))
    lef=(R.ROOT/'physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.lef').read_text()
    pinrows=[]
    for name in ['clk','rst_n']:
        body=re.search(r'  PIN '+name+r'\n(.*?)  END '+name,lef,re.S)[1]
        pinrows.append(dict(pin=name,layer=re.search(r'LAYER (\w+)',body)[1],
            rectangle_um=[float(v) for v in re.search(r'RECT ([\d. ]+) ;',body)[1].split()]))
    m['schema']='QROM_CREDIT17_EXACT_TRACK_ROUTE_CUT_R1'
    m['credit17_route_cuts']=dict(source_model_sha256=R.sha(P.OUT/'model-r4.json'),
        layer_geometry=tech,channel_bands=bands,field_delivery_trunks=roots,shoreline_trunks=shores,
        source_family_bits_per_stack=source_families,untyped_parent_boundary_bits=804,
        fill_control_tracks=7973,source_boundary_bits=43256,
        field_delivery_routes=routes,field_delivery_buffer_reservation=route_buffers,
        field_delivery_wire_um=route_wire,field_delivery_buffer_area_mm2=extra,
        original_PHY_controller_buffers_upgraded=old,PHY_controller_drive_upgrade_mm2=existing_upgrade,
        delta_mm2=delta,actual_PHY_clock_reset_pins=pinrows,
        historical_M4_clock_label_corrected=True,root_routes_and_CTS_qualified=False,
        PHY_macro_claim='licensed-IP placement/connection abstract with assumed timing and footprint',
        source_command_paths_to_PHY_interface_instantiated=False,
        all_original_failures_preserved=True)
    m['known_composed_area_mm2']+=delta;m['remaining_area_before_unknown_placements_mm2']-=delta
    m['new_route_cells_location_scope']='distributed field/shoreline route reservations; not all packed into controller slots'
    m['admission_failures']+=['804 parent boundary bits lack typed source endpoints',
        'M9 delivery/shoreline and M6/M8 bands lack exclusive PG/via/hold/source pin ownership',
        'field/shoreline root clock-reset balancing and actual transport stage replay incomplete']
    m['status']='FAIL_G0_EXACT_TRACK_RESERVATIONS_NOT_ROUTED_OR_SERVICE_ADMITTED'
    return m


if __name__=='__main__':
    p=R.ROOT/OUT/'model-r1.json'
    if p.exists():raise ValueError('preserve verdict')
    p.parent.mkdir(parents=True,exist_ok=True)
    P.C.Q.M.write(p,price())
