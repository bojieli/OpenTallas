#!/usr/bin/env python3
"""Audit actual HBM connectivity against explicitly historical slots, never qualify it."""
import argparse, hashlib, json, math
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def distance(a,b):
    return max(0,a[2]-b[2]-b[4],b[2]-a[2]-a[4])+max(0,a[3]-b[3]-b[5],b[3]-a[3]-a[5])
def collisions(p, halo=0):
    out=[]
    for i,(n,a) in enumerate(p.items()):
        for m,b in list(p.items())[i+1:]:
            ox=min(a[2]+a[4],b[2]+b[4])-max(a[2],b[2]);oy=min(a[3]+a[5],b[3]+b[5])-max(a[3],b[3])
            if ox>-halo+1e-6 and oy>-halo+1e-6:out.append(dict(a=n,b=m,overlap_um=[round(ox,6),round(oy,6)]))
    return out

def audit(contract,legacy,sm):
    inst=contract['instances']; old=legacy['full_repack_candidate']['instances']; named=sorted(set(inst)&set(old))
    same=[n for n in named if inst[n]['master']==old[n][0]];changed=[n for n in named if n not in same]
    pairs=[];missing=[];connected={}
    for e in contract['known_actual_edges']:
        nodes=tuple(sorted([e['source'][0],e['sink'][0]]));g=connected.setdefault(nodes,dict(instances=list(nodes),known_signal_bits=0,known_edges=0,physical_pin_verified=False));g['known_signal_bits']+=e['bits'];g['known_edges']+=1
    for e in contract['known_actual_edges']:
        a,b=e['source'][0],e['sink'][0]
        if a not in old or b not in old:missing.append(e['name']);continue
        length=distance(old[a],old[b]);pairs.append(dict(name=e['name'],source=a,sink=b,bits=e['bits'],historical_box_distance_lower_bound_um=round(length,6),historical_bit_um_lower_bound=round(length*e['bits'],6),optimistic_490um_relay_lower_bound=max(0,math.ceil(length/490)-1),actual_pin_coordinates_present=False,masters_match=(a in same and b in same)))
    actual=json.loads(json.dumps(old));sm_names=[n for n,v in old.items() if v[1]=='sm' or n.startswith('sm') and n[2:].isdigit()]
    sw,sh=sm['frame_outline_um']
    for n in sm_names:actual[n][4:6]=[sw,sh]
    return dict(schema='opentallas.hbm_geometry.coverage.v1',qualification=False,status='SOURCE_GEOMETRY_GAPS_BLOCK_GLOBAL_OPTIMIZATION',coverage=dict(actual_instances=len(inst),actual_edges=len(contract['known_actual_edges']),legacy_name_matches=len(named),same_master_names=same,changed_master_names=changed,missing_slot_names=sorted(set(inst)-set(old)),edges_with_historical_slot_boxes=len(pairs),edges_missing_slot_boxes=len(missing),missing_edge_names=missing,actual_pin_verified_edges=0),top20_source_connected_pairs=sorted(connected.values(),key=lambda g:g['known_signal_bits'],reverse=True)[:20],top20_historical_lower_bounds=sorted(pairs,key=lambda e:e['historical_bit_um_lower_bound'],reverse=True)[:20],all_historical_edge_lower_bounds=pairs,sm_replacement=dict(count=len(sm_names),actual_component_outline_um=[sw,sh],actual_component_area_mm2=sw*sh/1e6,component_qualified=False,legacy_outline_um=old[sm_names[0]][4:6],collisions_after_replacement=collisions(actual),halo_20um_conflicts=collisions(actual,20),retained_all_non_sm=True),limits=['Legacy slots do not establish current master outlines or pins.','Rectangle distance is an optimistic bound, not routed wirelength.','SM replacement preserves each historical origin only to expose packing debt.','No new master, slot, orientation, clock, timing or performance qualification.','Graph is incomplete: unbound ports and omitted SM/SU/ATT native composition remain explicit.'])

def main():
    a=argparse.ArgumentParser();a.add_argument('--contract',required=True);a.add_argument('--legacy',required=True);a.add_argument('--sm',required=True);a.add_argument('--out',required=True);x=a.parse_args();r=audit(*[json.load(open(p)) for p in [x.contract,x.legacy,x.sm]]);r['input_sha256']={k:sha(getattr(x,k)) for k in ['contract','legacy','sm']};Path(x.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(coverage={k:v for k,v in r['coverage'].items() if isinstance(v,int)},sm_outline=r['sm_replacement']['actual_component_outline_um'],collision_count=len(r['sm_replacement']['collisions_after_replacement']))))
if __name__=='__main__':main()
