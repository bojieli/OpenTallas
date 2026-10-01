"""Explicit Ram role replacement plus channel-aware integer-origin repack.

Model records only: never remove any source file, process, or checkpoint.
"""
import bisect
import collections
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
raw=(ROOT/'sensitivity_192_homes.json').read_bytes();old=json.loads(raw)
pin=old['source_pin']['commit'];path=old['source_pin']['path']
src=subprocess.check_output(['git','show',pin+':'+path]);fp=json.loads(src);g=fp['geometry']
allowed={'ROM_MAC.expert','ROM_MAC.dense_QE','ROM_MAC.ME','ENGRAM.spill'}
removed=[r for r in fp['instances'] if r[5] in allowed]
assert all(r[1]=='ot_rom_8192x274_m8' for r in removed)
retained=[r for r in fp['instances'] if r[5] not in allowed]
removed_soft=[r for r in fp['soft_regions'] if r[1]=='ROM_MAC_strip']
retained_soft=[r for r in fp['soft_regions'] if r[1]!='ROM_MAC_strip']
cx0,cy0,cx1,cy1=g['core'];hx,hy,hw,hh=g['hub'];halo=g['hub_halo_um']
ox=hx+hw+halo;oy=cy0
px=old['grid_size_um'][0]/64;py=old['grid_size_um'][1]/128
xvoids=sorted(set((r[2],r[2]+r[4]) for r in fp['channel_rects'] if r[1]=='vertical_hbm_corridor' and r[2]>=ox))
yvoids=sorted(set((r[3],r[3]+r[5]) for r in fp['channel_rects'] if r[1]=='horizontal_spine'))
# Preserve every source constant ROM. Four intersect this right strip;
# reserve their entire y bands across the grid, including source pin halo.
yvoids=sorted(set(yvoids+[(r[3]-g['pin_halo_um'],r[3]+119.34+g['pin_halo_um']) for r in retained if r[5]=='VM.CONSTANT_HE' and r[2]+125.712>ox]))
def slots(start,count,pitch,voids):
    out=[];cur=start
    for _ in range(count):
        while True:
            hits=[b for a,b in voids if cur<b and a<cur+pitch]
            if not hits:break
            cur=max(hits)
        out.append(cur);cur+=pitch
    return out
xs=slots(ox,64,px,xvoids);ys=slots(oy,128,py,yvoids)
assert xs[-1]+px<=cx1 and ys[-1]+py<=cy1
def overlap(a,b):
    x,y,w,h=a;xx,yy,ww,hh=b
    return x<xx+ww and xx<x+w and y<yy+hh and yy<y+h
sizes={};lef_pins={}
for master in sorted({r[1] for r in retained}):
    if master=='ASSUMED_serdes_112g_lane':sizes[master]=(400.,1000.)
    elif master=='ASSUMED_ucie_a_x64':sizes[master]=(388.8,1043.)
    else:
        p=f'physical/asap7_memory_macros/{master}/{master}.lef';b=subprocess.check_output(['git','show',pin+':'+p]);m=re.search(rb'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',b);assert m
        sizes[master]=tuple(float(v) for v in m.groups());lef_pins[master]=dict(path=p,sha256=hashlib.sha256(b).hexdigest())
obstacles=[]
for name,master,x,y,orient,group in retained:
    w,h=sizes[master]
    if orient in ('R90','R270'):w,h=h,w
    obstacles.append((name,'hard:'+group,x,y,w,h))
obstacles += [(r[0],'soft:'+r[1],*r[2:]) for r in retained_soft]
obstacles += [(r[0],'channel:'+r[1],*r[2:]) for r in fp['channel_rects']]
def xy(local):
    return (sum(((local>>(11-2*k))&1)<<(5-k) for k in range(6)),sum(((local>>(12-2*k))&1)<<(6-k) for k in range(7)))
bad=collections.Counter();examples=[]
# Check every reserved cell, stronger than checking only the predictive LEF
# macro inside each cell. This includes cell routing gaps and density reserve.
for x in xs:
    for y in ys:
        for name,kind,xx,yy,w,h in obstacles:
            if overlap((x,y,px,py),(xx,yy,w,h)):
                bad[kind]+=1
                if len(examples)<8:examples.append(dict(cell_origin=[x,y],obstacle=name,kind=kind))
digest=hashlib.sha256()
for h in old['homes']:
    for local in range(h['actual_macros']):
        x,y=xy(local);mx,my=xs[x]+8,ys[y]+8
        assert mx>=cx0 and my>=cy0 and mx+125.28<=cx1 and my+62.91<=cy1
        digest.update(f"{h['home_id']},{h['macro_start']+local},{local},{mx:.9f},{my:.9f}\n".encode())
# The unchanged full-width tree cannot assume an unreserved corridor.
spine=next(c for c in fp['channels']['channels'] if c['channel']=='spine_0')
vcorr=next(c for c in fp['channels']['channels'] if c['channel']=='vcorr_s1')
newtracks=341
out=dict(schema='opentallas.engram.192-home-role-repack.v1',source_floorplan_pin=old['source_pin'],
    source_LEF_pins=lef_pins,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    supersedes_previous_role_pin='f67dbe0b59cbf9890ceac153743db04eab4e961e; latest owner keeps constants, previous role screen preserved',
    role_owner_decision='Ram latest: retain ALL VM.CONSTANT_HE. Dedicated ENGRAM_TABLE_SERVICE192 homes; replace historical ROM payload plus corresponding MAC strips only. Keep current hub, allSRAM/HBM/PHY/IO/service and channels. Operators remain separately priced elsewhere; this does not claim capacity or payload removal.',
    exact_replaced_historical_instances=removed,exact_replaced_historical_soft_regions=removed_soft,
    replaced_hard_count=len(removed),replaced_soft_count=len(removed_soft),
    all_retained_hard_count=len(retained),all_retained_soft_count=len(retained_soft),all_retained_channel_count=len(fp['channel_rects']),
    retained_obstacles_hash=hashlib.sha256((json.dumps(obstacles,separators=(',',':'))+'\n').encode()).hexdigest(),
    coordinate_construction=dict(x_slot_origins_um=xs,y_slot_origins_um=ys,cell_pitch_um=[px,py],
        skipped_vertical_hbm_ranges_um=xvoids,skipped_horizontal_spine_ranges_um=yvoids,
        cell_maximum_point_um=[xs[-1]+px,ys[-1]+py],actual_macro_orientation='R0',macro_origins='(x_slot+8,y_slot+8)',
        all1500067_actual_macro_origin_tuple_SHA256=digest.hexdigest(),no_macro_copy_replication=True),
    all8192_reserved_cell_retained_obstacle_pair_conflicts=dict(bad),conflict_examples=examples,
    legal_source_obstacle_rectangle_screen_pass=not bad,
    route_screen=dict(new_request_response_credit_tracks_per_edge=newtracks,
        existing_spine_tracks=spine['tracks'],existing_spine_demand=spine['demand_wires'],
        remaining_spine_tracks=spine['tracks']-spine['demand_wires'],
        over_by_tracks=newtracks-(spine['tracks']-spine['demand_wires']),
        existing_HBM_corridor_tracks=vcorr['tracks'],existing_HBM_corridor_demand=vcorr['demand_wires'],
        remaining_HBM_corridor_tracks=vcorr['tracks']-vcorr['demand_wires'],
        verdict='FAIL_SINGLE_FULLWIDTH_TREE_EDGE_ON_EXISTING_RESERVED_SPINE_LAYER_SET',
        caveat='Necessary additive cut allocation for one edge, not a routed global proof. Different layers or narrower/serialized response need explicit source capacity and latency/FF/mux/power repricing; no extra layers or free overlap assumed.'),
    CTS_PHY_selector_control_area_placement=False,
    selector_latency_note='Nonuniform origins change tree edge lengths; prior104cycle row and prior typed192 CTS budget are not automatically valid for this repack. Price a source-bound new tree and root-to-PHY path before admission.',
    model_writes_only_no_source_retirement=True,L1_generated_source=None,checkpoint_reads=0,RTL_or_PnR_runs=False,
    physical_admission=False,full_token_rate=None)
target=ROOT/'sensitivity_192_role_repack_constants_retained.json';assert not target.exists()
target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),removed_hard=len(removed),removed_soft=len(removed_soft),maxpoint=out['coordinate_construction']['cell_maximum_point_um'],conflicts=dict(bad),spine_remaining=out['route_screen']['remaining_spine_tracks'])))
