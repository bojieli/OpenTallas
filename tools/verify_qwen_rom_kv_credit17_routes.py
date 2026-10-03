#!/usr/bin/env python3
"""Independent arithmetic/track replay. Does not import the constructor."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT='results/uarch/qwen_rom_kv_credit17_routes_20261003/model-r1.json'


def require(ok,message):
    if not ok:raise ValueError(message)


def verify(m,root=ROOT):
    c=m['credit17_route_cuts'];parent_path=root/'results/uarch/qwen_rom_kv_credit17_physical_20261003/model-r4.json'
    require(hashlib.sha256(parent_path.read_bytes()).hexdigest()==c['source_model_sha256'],'parent pin')
    parent=json.loads(parent_path.read_text())
    path=root/'results/uarch/qwen_rom_mapped_root_pg_context_20261002/inputs'
    lef=(path/'tech.lef').read_text();tracks=(path/'make_tracks.tcl').read_text();tech={}
    for name in ['M6','M8','M9']:
        body=re.search(r'^LAYER '+name+r'\n(.*?)^END '+name+r'$',lef,re.M|re.S)[1]
        direction=re.search(r'DIRECTION\s+(\w+)',body)[1]
        row=re.search(r'make_tracks '+name+r' -x_offset (\S+) -x_pitch (\S+) -y_offset (\S+) -y_pitch (\S+)',tracks)
        tech[name]={'direction':direction,'pitch':float(row[2 if direction=='VERTICAL' else 4]),'offset':float(row[1 if direction=='VERTICAL' else 3])}
    require(tech==c['layer_geometry'],'technology binding')
    def signal_centers(lo,hi,name):
        t=tech[name];a=math.ceil((lo-t['offset'])/t['pitch']);b=math.ceil((hi-t['offset'])/t['pitch'])
        return [t['offset']+i*t['pitch'] for i in range(a+1,b,2)]
    fill=control=0
    require(len(c['channel_bands'])==7,'seven bands')
    for b in c['channel_bands']:
        r=b['rectangle_um'];actual=[]
        for layer in ['M6','M8']:
            actual += [(layer,y) for y in signal_centers(r[1],r[3],layer)]
        used=[]
        for role,count in [('fill',1048),('shared_control',91),('clock',64),('reset_ACK',64),('spare',93)]:
            rows=b['allocated_tracks'][role];require(len(rows)==count,'channel role width')
            used += [(x['layer'],x['coordinate_um']) for x in rows]
        require(len(actual)==b['signal_capacity']==1360,'actual band capacity')
        require(len(set(used))==1360 and set(used)==set(actual),'exclusive channel tracks')
        fill+=1048;control+=91
    require(fill+control==c['fill_control_tracks']==7973,'fill/control aggregate')
    #Shoreline tracks pay two actual PHY pin slots and128clock/reset wires.
    families={'request':455,'command':1356,'owned_receipt':3736,'reverse':3232}
    require(c['source_family_bits_per_stack']==families,'typed source families')
    require(4*sum(families.values())+7336+804==c['source_boundary_bits']==43256,'full boundary conservation')
    require(c['untyped_parent_boundary_bits']==804,'untyped reservation preserved')
    for s,old in zip(c['shoreline_trunks'],parent['shoreline_cuts']):
        xs=signal_centers(*old['band_x_um'],'M9');used=[]
        for slot in s['stack_allocations']:
            require([f['bits'] for f in slot['families']]==[455,1356,3736,3232,201,229],'stack family widths')
            for f in slot['families']:
                require(len(f['x_centers_um'])==f['bits'],'shore family tracks')
                used+=f['x_centers_um']
        require(len(s['clock_reset_ACK_x_centers_um'])==128,'shore control reservation')
        used+=s['clock_reset_ACK_x_centers_um']
        require(len(xs)==s['signal_capacity'] and len(used)==s['demand']==18546,'shore cut')
        require(len(set(used))==len(used) and set(used)<=set(xs),'shore exclusive tracks')
    for t in c['field_delivery_trunks']:
        r=t['rectangle_um'];xs=signal_centers(r[0],r[2],'M9');used=[]
        require(t['demand']==4*(1048+91+64+64)==5068,'delivery demand')
        require(t['signal_capacity']==len(xs)>=t['demand'],'delivery capacity')
        expected={(lane,role):n for lane in ([0,2,4,6] if t['side']==0 else [1,3,5,6])
            for role,n in [('fill',1048),('shared_control',91),('clock',64),('reset_ACK',64)]}
        require(len(t['allocations'])==len(expected),'all delivery families')
        seen=set()
        for a in t['allocations']:
            key=(a['lane'],a['role']);require(key not in seen and key in expected,'delivery family ownership')
            require(len(a['x_centers_um'])==expected[key],'delivery family width');seen.add(key)
            used+=a['x_centers_um']
        require(len(set(used))==len(used)==5068 and set(used)<=set(xs),'delivery exclusive tracks')
        for old in parent['shoreline_cuts']:
            lo,hi=old['band_x_um'];require(r[2]<=lo or r[0]>=hi,'M9 trunks must be disjoint')
    count=0;wire=0
    for r in c['field_delivery_routes']:
        band=next(b for b in c['channel_bands'] if b['name']==f"KV_FILL_CHANNEL_{r['lane']}")
        trunk=c['field_delivery_trunks'][r['side']];rect=trunk['rectangle_um'];center=(rect[0]+rect[2])/2
        slot=parent['controller_slots'][r['side']]['rectangle_um']
        length=abs((slot[0]+slot[2])/2-center)+abs(slot[3]-band['rectangle_um'][1]-48.384)
        require(abs(length-r['length_um'])<1e-8,'finite endpoint length')
        stages=math.ceil(length/128);require(stages==r['segments_per_bit'],'128um segments')
        require(r['buffers']==r['bits']*(stages+1),'per-bit buffer census')
        count+=r['buffers'];wire+=r['bits']*(length+16)
    require(count==c['field_delivery_buffer_reservation'],'route buffer total')
    require(abs(wire-c['field_delivery_wire_um'])<.1,'wire total')
    prices=parent['credit17']['cell_prices_um2']
    upgrade=parent['route_buffer_reservation']*(prices['selected_BUF8']-prices['BUF4'])/1e6
    delta=upgrade+count*prices['selected_BUF8']/1e6
    require(abs(delta-c['delta_mm2'])<1e-12,'area delta')
    require(abs(m['known_composed_area_mm2']-parent['known_composed_area_mm2']-delta)<1e-10,'composed area')
    require(abs(m['remaining_area_before_unknown_placements_mm2']-(815-m['known_composed_area_mm2']))<1e-10,'remaining area')
    phylef=(root/'physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.lef').read_text()
    for pin in c['actual_PHY_clock_reset_pins']:
        body=re.search(r'  PIN '+pin['pin']+r'\n(.*?)  END '+pin['pin'],phylef,re.S)[1]
        actual_layer=re.search(r'LAYER (\w+)',body)[1]
        actual_rect=[float(v) for v in re.search(r'RECT ([\d. ]+) ;',body)[1].split()]
        require(pin['layer']==actual_layer=='M5' and pin['rectangle_um']==actual_rect,'actual PHY M5 pins')
    require(m['actual_sustained_PHY_Bps'] is None,'no ideal PHY claim')
    require(not any(m[k] for k in ['source_map_admission','PnR','actual_contextual_SSFF','default_enabled','complete_route_allocation']),'no admission')
    require(not m['credit17']['candidate_replayed'] and not m['credit17']['capacity_admitted'],'no capacity prediction')
    return dict(checks='PASS_TRACK_AND_COST_REPLAY_ONLY',hardware_admission='FAIL',
        fill_control_tracks=7973,boundary_bits=43256,untyped_boundary_bits=804,
        field_delivery_buffers=count,route_delta_mm2=delta,
        remaining_before_unknowns_mm2=m['remaining_area_before_unknown_placements_mm2'],
        actual_sustained_PHY_Bps=None)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',default=DEFAULT);args=parser.parse_args()
    print(json.dumps(verify(json.loads((ROOT/args.model).read_text())),indent=2,sort_keys=True))
