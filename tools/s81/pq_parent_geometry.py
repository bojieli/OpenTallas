#!/usr/bin/env python3
"""Bind production PQ partitions to the current mixed221 S81 die geometry.

Candidate only. Existing routed views, field source and generator stay immutable.
Reservations precede route-station placement, so old channels cannot be silently
occupied. Real SRAM/ROM abstracts are placed within the core reservation. Root,
RWB and control outlines remain estimated until their own hardened views exist.
"""
import argparse
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s81_fulldie as F

BASIS='results/uarch/dsrom_s81_mixed_geometry_20261007/mixed221_layer1_plan.json'
DESIGN='results/uarch/dsrom_s81_pq_fullshape_design_20261007/design.json'
ROOT_ROW=164.16
ROOT_SIZE=(132.192,133.92)
CORE_HEIGHT=449.28
SRAM='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
ROM='physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef'


def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def box(i):return (i['x'],i['y'],i['x']+i['w'],i['y']+i['h'])
def overlaps(a,b):return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6


def check_boxes(items,within):
    outside=[i['name']for i in items if any((box(i)[0]<within[0]-1e-6,box(i)[1]<within[1]-1e-6,
                                            box(i)[2]>within[2]+1e-6,box(i)[3]>within[3]+1e-6))]
    collisions=[(a['name'],b['name'])for n,a in enumerate(items)for b in items[n+1:]if overlaps(box(a),box(b))]
    return dict(PASS=not(outside or collisions),outside=outside,overlaps=collisions)


def core_children(core):
    """Concrete36 SRAM +3 ROM layout; retain separate control reservation."""
    s,r=F.real_lef(SRAM),F.real_lef(ROM)
    children=[]
    for n in range(36):
        row,col=divmod(n,9)
        children.append(dict(name=(f'bb_replica{n//8}_bank{n%8}'if n<32 else f'qb_bank{n-32}'),
            master=s['name'],x=core.x+20.304+col*116.64,y=core.y+20.304+row*64.8,
            w=s['w'],h=s['h'],domain='stream_1p2',role='SRAM',source=SRAM,source_sha256=sha(SRAM)))
    for n,name in enumerate(('phase_even','phase_odd','stream')):
        children.append(dict(name=name,master=r['name'],x=core.x+1140.48+n*60.48,
            y=core.y+349.92,w=r['w'],h=r['h'],domain='stream_1p2',role='ROM',
            source=ROM,source_sha256=sha(ROM)))
    children.append(dict(name='pq_ctl_reservation',master='unhardened_pq_ctl',x=core.x+1123.2,
        y=core.y+17.28,w=570.24,h=311.04,domain='stream_1p2',role='control_estimate'))
    check=check_boxes(children,core.box())
    if not check['PASS']:raise ValueError(check)
    return dict(children=children,legality=check,
        SRAM_macros=36,ROM_macros=3,macro_pin_geometry_source='actual LEF; block-face pins not yet hardened',
        control_slot_um2=570.24*311.04,control_required_um2_est=108654.2,
        parity_bits_priced_not_implemented=14208,macro_RTL_instance_binding_complete=False)


def bind_before_routes(m,old_channels):
    """Called before existing bus/station placement, including hop-planning pass."""
    cap=m['hub']['capture']
    core=F.Inst('sp_pq_core','s81_pq_core_reservation',cap.x,cap.y,cap.w,CORE_HEIGHT,
                kind='pq_core_reservation',region='spine',domain='stream_1p2')
    cap.y+=CORE_HEIGHT+F.SPINE_GAP
    cap.h-=CORE_HEIGHT+F.SPINE_GAP
    if cap.h<=0:raise ValueError('capture reservation was not enlarged before stack planning')
    m['insts'].append(core);m['hub']['pq_core']=core
    roots=[]
    for rid,f in m['frames'].items():
        y0=m['geo']['ch_y'][f['tier']]+old_channels[f['tier']]-51.84
        x0=f['x']+2*F.LANE_W
        root=F.Inst(f'pq_root_{rid}','s81_pq_root_r128_reservation',x0+4.32,y0+15.12,*ROOT_SIZE,
                    kind='pq_root_reservation',region=f'pq_root_row_{rid}',domain=f'column_{rid}')
        m['insts'].append(root)
        stations=[]
        for side,dy in [('S',2.16),('N',153.36)]:
            st=F.Inst(f'pq_root_{rid}_pin_{side}','s81_pq_root_station_reservation',x0+4.32,y0+dy,
                       ROOT_SIZE[0],8.64,kind='pq_pin_station_reservation',region=f'pq_root_row_{rid}',domain=f'column_{rid}')
            m['insts'].append(st);stations.append(st.d())
        rect=[x0,y0,x0+F.NS_W+F.RSC_W,y0+ROOT_ROW]
        m['regions'].append(dict(name=f'pq_root_row_{rid}',kind='pq_reserved',rect=rect))
        roots.append(dict(region=rid,tier=f['tier'],half=f['half'],col=f['col'],
            root=root.d(),stations=stations,reserved_rect=rect,clock_source=f'cf{rid}.co',reset_source=f'cf{rid}.rs',
            physical_root_pins_pending=True,native_raw_bits=66,native_result_bits=69,
            proposed_face_bits=dict(tree=67,result=71),extra_valid_busy_fault_and_parity_contract_pending=True))
    m['pq_bindings']=dict(roots=roots,core=core.d(),core_children=core_children(core))


def bind_rwb_children(m):
    """RWB replaces return ownership inside gather; do not double count its slot."""
    ga=m['hub']['gather'];children=[];routes=[]
    for side in 'WE':
        for t,n in enumerate(F.TIER_COLS8):
            x=ga.x+17.28 if side=='W'else ga.x+ga.w-17.28-103.68
            y=ga.y+17.28+t*125.28
            it=dict(name=f'pq_rwb_{side}{t}',master=f's81_pq_rwb_{n}_reservation',x=x,y=y,
                    w=103.68,h=103.68,domain='stream_1p2',regions=n)
            children.append(it)
            routes.append(dict(instance=it['name'],input_end=f'hr_{side}{t}',
                region_ids=[int(r)for r,f in m['frames'].items()if f['half']==side and f['tier']==t],
                root_result_payload_bits_per_region=69,transport_lane_bits_per_region=71,
                cfg_replica_bits=458,VM_write_bits=n*52,rowcount_bits=16,
                input_pin_station_required=True,VM_ratio_CDC_required=True))
    legality=check_boxes(children,ga.box())
    if not legality['PASS']:raise ValueError(legality)
    return dict(parent_instance=ga.name,children=children,bindings=routes,legality=legality,
        occupies_existing_parent_reservation=True,parent_functional_repartition_not_yet_implemented=True,
        remaining_parent_area_um2=ga.w*ga.h-sum(i['w']*i['h']for i in children))


def build():
    basis=json.loads((ROOT/BASIS).read_text());design=json.loads((ROOT/DESIGN).read_text())
    if (design['problem']['PHW'],design['problem']['SAW'],design['problem']['KMAX'])!=(9,11,6144):
        raise ValueError('production source dimensions changed')
    args=F.die_options(argparse.ArgumentParser()).parse_args(basis['run_options'].split())
    F.apply_options(args)
    old_channels=[F.chh(t)for t in range(7)]
    F.CHS=tuple(h+(ROOT_ROW if t<6 else 0)for t,h in enumerate(old_channels))
    # Expand capture's stack allocation, then split it BEFORE endpoints and
    # routing stations are placed; its original useful area is retained.
    old_capture=F.HUB_MM2['capture']
    cw=F.dn((F.SPINE_W8-F.VCH8)/2,F.GX)
    F.HUB_MM2['capture']=old_capture+(CORE_HEIGHT+F.SPINE_GAP)*cw/1e6
    original=F.buses_r8
    def buses(m):
        bind_before_routes(m,old_channels)
        original(m)
        for rid in m['frames']:
            names=[f'pq_root_{rid}',f'pq_root_{rid}_pin_S',f'pq_root_{rid}_pin_N']
            for bid,cls,bits,endpoints in m['buses']:
                if bid==f'ck_col_{rid}':endpoints.extend((n,'clk')for n in names)
                if bid==f'rs_col_{rid}':endpoints.extend((n,'rst_n')for n in names)
        m['pq_bindings']['rwb']=bind_rwb_children(m)
    F.buses_r8=buses
    try:
        m=F.build_r8()
        for bid,cls,bits,endpoints in m['buses']:
            if bid=='clk_stream':endpoints.append(('sp_pq_core','clk'))
            if bid=='rst_stream':endpoints.append(('sp_pq_core','rst_n'))
        F.finalize_r8(m)
        m['pq_bindings']['actual_clock_nets']=[dict(net=bid,driver=endpoints[0],
            receivers=[p for p in endpoints[1:] if p[0].startswith('pq_root_') or p[0]=='sp_pq_core'])
            for bid,cls,bits,endpoints in m['buses'] if cls in ('clock','reset','col_clock','col_reset')
            and any(p[0].startswith('pq_root_') or p[0]=='sp_pq_core' for p in endpoints[1:])]
        if sum(len(n['receivers'])for n in m['pq_bindings']['actual_clock_nets'])!=128*3*2+2:
            raise ValueError('missing root/station/core clock or reset binding')
        legality=F.legality(m)
        if legality['overlaps']or legality['outside']:raise ValueError(legality)
        plan=F.plan_record_r8(m)
    finally:
        F.buses_r8=original;F.HUB_MM2['capture']=old_capture
    record=dict(schema='opentallas.s81.production-pq-geometry.v1',
        source_sha256={p:sha(p)for p in [BASIS,DESIGN,'tools/dsrom_s81_fulldie.py','tools/s81/pq_parent_geometry.py',SRAM,ROM]},
        base_options=basis['run_options'],root_row_added_um=ROOT_ROW,channels_um=list(F.CHS),
        die_um=list(F.DIE),pairs=F.PAIRS,BF_pairs=F.BF_PAIRS,root_replicas=128,
        field_slots=F.SLOTS8,field_frame_height_um=F.column_height(),
        production_parameters=dict(R=128,PQ=1,PHW=9,SAW=11,KMAX=6144),
        native_broadcast_bits=1633,planned_union_lane_bits=1085,
        union_lane_RTL_and_widened_transport_implemented=False,
        baseline_field_round_trip_cycles=basis['field_round_trip_cycles'],
        candidate_legacy_transport_field_round_trip_cycles=plan['field_round_trip_cycles'],
        legacy_transport_latency_is_not_production_PQ_latency=True,
        legality=legality,bindings=m['pq_bindings'],
        clock_reservations=dict(core='stream_1p2',RWB='stream_1p2',roots='own cfN column clock',VM='serial_0p9',
            setup_uncertainty_ps=60,hold_uncertainty_ps=25,stream_period_ps=833.3333333333334),
        reservation_area_um2=dict(roots=128*ROOT_SIZE[0]*ROOT_SIZE[1],
            root_stations=128*2*ROOT_SIZE[0]*8.64,core=m['hub']['pq_core'].w*CORE_HEIGHT,
            RWB_children_within_existing_gather=sum(i['w']*i['h']for i in m['pq_bindings']['rwb']['children'])),
        remaining=['source-matched hard root/control/RWB views and actual protected endpoint pins',
                   'union lane RTL, expanded FIFO/station views and capacity qualification',
                   'actual VM request-response and sustained write credit protocol',
                   'complete contextual SS/FF/DRC/IR and composed production latency'],
        physical_route_admitted=False,physical_adopted=False)
    return record,dict(instances=[i.d()for i in m['insts']],regions=m['regions'],
                       frames=m['frames'],hub={k:v.d()for k,v in m['hub'].items()})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    record,geo=build()
    (a.out/'binding.json').write_text(json.dumps(record,indent=2)+'\n')
    (a.out/'geometry.json.gz').write_bytes(gzip.compress(json.dumps(geo).encode(),mtime=0))
    print(json.dumps({k:record[k]for k in ['pairs','BF_pairs','root_replicas','field_slots','legality']}))


if __name__=='__main__':main()
