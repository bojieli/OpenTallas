#!/usr/bin/env python3
"""Assign actual static embedding return stations in the existing strip corridor.
Run after kv_die --reserve-static-memory; all endpoint/clock native views open.
"""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def build(plan):
    inst=json.loads((plan/'insts.json').read_text());by={x['name']:x for x in inst};homes=[];edges=[];collisions=[]
    w,h=64.8,172.8
    pins={}
    def add(port,n,face,lo,hi):
        for i in range(n):
            pos=.012+.048*round((lo+(hi-lo)*(i+.5)/n-.012)/.048)
            xy={'W':[0,pos],'E':[w,pos],'S':[pos,0],'N':[pos,h]}[face]
            pins[port if n==1 else f'{port}[{i}]']=dict(face=face,xy=xy,layer='M4' if face in 'WE' else 'M5')
    add('capture_record',298,'W',8,148);add('capture_v',1,'W',154,156)
    add('upi',299,'S',4,60);add('upo',299,'N',4,60)
    for port,lo in [('ck',8),('rst_n',16),('capture_slot',24),('transfer_slot',32),('fault',40)]:add(port,1,'E',lo,lo+2)
    for st in ('WS','WN','ES','EN'):
        land=by['land_'+st]
        for pc in range(32):
            base_y=land['y']+190.08+378*pc
            choices=[]
            for dx in range(10):
                x=land['x']+land['w']+4.32+21.6*dx if st[0]=='W' else land['x']-4.32-w-21.6*dx
                for dy in [0,21.6,-21.6,43.2,-43.2,64.8,-64.8,86.4,-86.4,108,-108]:
                    y=base_y+dy
                    if y<land['y'] or y+h>land['y']+land['h']:continue
                    if any(min(x+w,z['x']+z['w'])>max(x,z['x'])+1e-6 and min(y+h,z['y']+z['h'])>max(y,z['y'])+1e-6 for z in inst+homes):continue
                    if pc and abs(homes[-1]['x']-x)+abs(homes[-1]['y']+h-y)>500:continue
                    choices.append((abs(dy)+dx*21.6,x,y))
            assert choices,(st,pc)
            _,x,y=min(choices)
            d=dict(name=f'emb_return_{st}_{pc}',master='qkd_embedding_static_return_hop',x=round(x,3),y=round(y,3),w=w,h=h,orient='R0' if st[0]=='W' else 'MY',stack=st,physical_slot=pc,logical_pc=8*(pc%4)+(4,5,0,1,2,3,6,7)[pc//4],core_edges_to_strip_root=2*(32-pc))
            homes.append(d)
            if pc:
                prev=homes[-2]
                for bit in range(299):
                    # MY preserves y and reflects both stations identically.
                    a=pins[f'upo[{bit}]']['xy'];b=pins[f'upi[{bit}]']['xy']
                    distance=abs(prev['x']+a[0]-d['x']-b[0])+abs(prev['y']+a[1]-d['y']-b[1]);edges.append(distance)
    assert not collisions,collisions
    assert max(edges)<=500
    for face in 'WESN':
        v=sorted(p['xy'][1 if face in 'WE' else 0] for p in pins.values() if p['face']==face);assert all(b-a>=.096-1e-6 for a,b in zip(v,v[1:]))
    # Alternative source-free binary gather lower bound. These are lengths only,
    # not a substitute for actual tree RTL/pins/mapped-fit/clock contracts.
    leaves=[190.08+378*i+86.4 for i in range(32)];tree_wire=0;relay_edges=0;level=leaves
    while len(level)>1:
        nxt=[]
        for i in range(0,len(level),2):
            y=(level[i]+level[i+1])/2;nxt.append(y)
            for a in level[i:i+2]:tree_wire+=abs(y-a);relay_edges+=max(1,math.ceil(abs(y-a)/450))
        level=nxt
    tree_wire+=12141.312-level[0];relay_edges+=math.ceil((12141.312-level[0])/450)
    result=dict(schema='opentallas.embedding.static-return.geometry.v1',selected='32_PC_STATIC_COMPILED_INJECTION_STRIP',reason='Actual two-edge station source and existing short pin-aligned corridor; local compiled injections eliminate per-word POP roundtrip. No dynamic POP waiting or upstream priority.',status='OFFICIAL_STATION_HOME_PIN_RESERVATION; mapped fit/native clocks and endpoint integration OPEN',source='rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_hop.sv',clock_family='core',period_ps=833.334,station_outline=[w,h],pins=pins,homes=homes,overlap=collisions,segment_count=len(edges),worst_chain_bit_segment_um=round(max(edges),3),station_ff_census=1199,ff_census_scope='Source-owner conservative count, not mapped fit',fixed_ages='capture actual record at compiled capture slot; local transfer age2, each subsequent station +2. Root/gateway input pin capture and existing inter-stack gateway route are separate.',root_train='For root slots100..131, local transfer_slot[pc] occurs at desired_root_slot-2*(32-pc). Source actual record must be captured before that transfer; missing/overwrite/conflict faults without rescheduling.',compiler_open=['Actual persistent-controller es/er CDC and refresh timing','Actual static return endpoint capture producer','Source-bound station full32 train receipt','Per-child phi-R/launch/capture/reset/native TT/FF','Existing strip-root to gateway path source-bound ages','Embedding join/preload/SU end-to-end price'],alternative=dict(name='binary_gather_length_lower_bound_only',wire_um_per_stack=round(tree_wire,3),minimum_450um_link_segments=relay_edges,chain_wire_um_per_stack=round(31*(378-h),3),actual_source_pin_home_contract='MISSING; cannot certify a15edge root latency from logical depth'))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=build(a.plan);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');t=[]
    for name,d in r['pins'].items():
        x,y=d['xy'];size='.144 .024' if d['face'] in 'WE' else '.024 .144';t.append(f'place_pin -pin_name {{{name}}} -layer {d["layer"]} -location {{{x:.3f} {y:.3f}}} -pin_size {{{size}}}')
    a.out.with_suffix('.tcl').write_text('\n'.join(t)+'\n');print(json.dumps({k:r[k] for k in ('selected','segment_count','worst_chain_bit_segment_um','overlap','alternative')}))
