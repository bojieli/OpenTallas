#!/usr/bin/env python3
"""Compact direct-leaf VM reservation with real closed views and explicit glue bays.
Does not establish physical or functional closure. Preserve the live group job.
"""
import json,sys,math,hashlib
from pathlib import Path

def overlap(a,b,gap=0):
    return a['x']<b['x']+b['w']+gap and b['x']<a['x']+a['w']+gap and a['y']<b['y']+b['h']+gap and b['y']<a['y']+a['h']+gap

def main():
    net,base,out=sys.argv[1:];d=json.loads(Path(net).read_text());p=json.loads(Path(base).read_text())
    old=[i for i in d['insts'] if i['n'] not in ('sp_vector_memory','sp_su64_sfu') and not i['m'].startswith(('qfd_rly','qkd_rly'))]
    x0,y0,W,H,gap=13288.32,17374.56,1123.2,1123.2,21.6
    cycle=[(0,0),(1,0),(2,0),(3,0),(3,1),(2,1),(1,1),(0,1)]
    origins={};children=[];fifo=[];helpers=[];regions=[]
    for k,(col,row) in enumerate(cycle):
        X,Y=round(x0+col*(W+gap),6),round(y0+row*(H+gap),6);origins[k]=[X,Y]
        regions.append(dict(n=f'vm_region_{k}',m='VM_RESERVATION_ONLY',x=X,y=Y,w=W,h=H))
        for bank in range(8):
            children.append(dict(n=f'vm_g{k}_ot_qfd_vm_bank_t_{bank}',m='ot_qfd_vm_bank_t',x=round(X+21.6+(bank%2)*239.76,6),
                y=round(Y+21.6+(bank//2)*205.2,6),w=218.16,h=183.6,orient='R0',region=k,logical_bank=8*k+bank,
                view='physical/ref_tile/qfd_vm_bank_t/views/ot_qfd_vm_bank_t',layer_cap='M5'))
        for bank in range(6):
            children.append(dict(n=f'vm_g{k}_ot_qfd_vm_su_t_{bank}',m='ot_qfd_vm_su_t',x=round(X+501.12+(bank%2)*257.04,6),
                y=round(Y+21.6+(bank//2)*257.04,6),w=235.44,h=235.44,orient='R0',region=k,
                operand=bank//2,logical_su_bank=2*k+bank%2,view='physical/ref_tile/qfd_vm_su_t/views/ot_qfd_vm_su_t',layer_cap='M5'))
        for n in range(4):
            fifo.append(dict(n=f'vm_g{k}_xfifo_{n}',m='ot_qfd_vm_xfifo32_t',x=round(X+21.6+(n%2)*300.24,6),
                y=round(Y+842.4+(n//2)*125.28,6),w=278.64,h=103.68,region=k,layer_cap='M5',clock_sinks_upper_bound=14176))
        # Placeholder all-six-stage helpers: four128-bit slices per bank. Their
        # cell area and matched transport depths MUST pass synthesis before use.
        sites=[(1015.2,21.6+i*86.4) for i in range(9)]
        sites += [(622.08+i*86.4,799.2) for i in range(5)]
        sites += [(622.08+i*86.4,885.6+j*86.4) for j in range(3) for i in range(6)]
        assert len(sites)==32
        for n,(x,y) in enumerate(sites):
            helpers.append(dict(n=f'vm_g{k}_rot_bank{n//4}_slice{n%4}',m='UNSIZED_ROTATION_BANK_HELPER',x=round(X+x,6),y=round(Y+y,6),
                w=64.8,h=64.8,region=k,logical_bank=8*k+n//4,slice_bits=[128*(n%4),128*(n%4)+127],layer_cap='M5',
                note='Candidate footprint only; resize/repack on measured cell area and route depths.'))
    su64=dict(n='sp_su64_sfu_reservation',m='UNSIZED_SU64_ACTUAL_LEAF_ENVELOPE',
        x=16424.64,y=19662.72,w=1991.52,h=2829.6,requested_leaf_area_mm2=5.04,
        reserved_area_mm2=1991.52*2829.6/1e6,status='Geometry reservation only; actual leaf decomposition and pin/cut/clock views required.')
    allblocks=children+fifo+helpers+[su64]
    overlaps=[(v['n'],u['n']) for j,v in enumerate(allblocks) for u in allblocks[:j]+old if overlap(v,u)]
    gaps=[(v['n'],u['n']) for j,v in enumerate(allblocks) for u in allblocks[:j] if overlap(v,u,20)]
    outside=[v['n'] for v in children+fifo+helpers if not any(r['x']<=v['x'] and r['y']<=v['y'] and v['x']+v['w']<=r['x']+r['w']+1e-6 and v['y']+v['h']<=r['y']+r['h']+1e-6 for r in regions)]
    assert not overlaps,(overlaps[:4]);assert not gaps,gaps[:4];assert not outside,outside
    # Remove stale scattered-layout graph/cut metadata before emitting this
    # independently placed candidate. Recompute transport on these coordinates.
    for key in ('regional_bays','glue_capacity_reservation','x_rotation_stages','x_rotation_links','minimum_engine_edges',
                'cuts','group_pin_plan','candidate_group_spec','pin_plan_status'):
        p.pop(key,None)
    p['status']='REGULAR_DIRECT_LEAF_GEOMETRY_CANDIDATE_ONLY'
    p['geometry_input']={'path':net,'sha256':hashlib.sha256(Path(net).read_bytes()).hexdigest(),'preserved_instances':len(old),'excluded_legacy_objects':['sp_vector_memory','sp_su64_sfu','qfd_rly*','qkd_rly*']}
    p['flattened_child_alternative'].update(children=children,region_origins=origins,regions=regions,
        eight_region_area_mm2=8*W*H/1e6,free_region_area_mm2=(8*W*H-sum(c['w']*c['h'] for c in children))/1e6)
    p['regular_placement']=dict(regions=regions,region_origins=origins,fifo_leaves=fifo,rotation_helper_placeholders=helpers,su64_reservation=su64,
        envelope_um=[4*W+3*gap,2*H+gap],x0_um=x0,y0_um=y0,closed_child_area_mm2=sum(c['w']*c['h'] for c in children)/1e6,
        fifo_area_mm2=sum(c['w']*c['h'] for c in fifo)/1e6,rotation_placeholder_area_mm2=sum(c['w']*c['h'] for c in helpers)/1e6,
        geometry=dict(hard_overlaps=0,peer_overlaps=0,outside=0,minimum_clearance_um=20,existing_closed_views_changed=0),
        assignment='Physical groups follow an eight-node cyclic snake; logical bank IDs and SU replica IDs unchanged.',
        gates=['Actual root area/depth <=64.8um placeholder, else repack','All VM interfaces plus original die demand in fine cuts',
               'Real pin/OBS views, clocks, <=500um seams, exact finite-credit benches and priced latency'])
    Path(out).write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps({k:v for k,v in p['regular_placement'].items() if k not in ('regions','region_origins','fifo_leaves','rotation_helper_placeholders','gates')}))
if __name__=='__main__':main()
