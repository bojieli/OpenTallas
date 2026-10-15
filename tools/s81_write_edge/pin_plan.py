#!/usr/bin/env python3
"""Generate actual per-bit pin candidates for static VM write leaves.
Candidates require native CTS, face-pin lint, extracted STA and actual global
registered connectivity. No parent geometry/adoption is claimed by this tool.
"""
import hashlib,json,math,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
import die_port_bind as D
PITCH=.096

def bits(name,start,width,total):
 return [name if total==1 else f'{name}[{i}]' for i in range(start,start+width)]
def plan(top,source,params,box,faces,name=None):
 m=next(m for m in D.parse_modules(source.read_text(),str(source)) if m.name==top);env=m.env(params)
 ports={n:dict(direction=d,width=m.width(n,env)) for n,(d,_) in m.ports.items()}
 expected={b for n,p in ports.items() for b in bits(n,0,p['width'],p['width'])}
 flat=sum(faces.values(),[]);assert len(flat)==len(set(flat)) and set(flat)==expected,(top,len(flat),len(expected),expected-set(flat))
 pins=[];w,h=box;counts={}
 for face,names in faces.items():
  length=w if face in 'NS' else h;cap=int(round(length/PITCH));counts[face]=dict(bits=len(names),full_track_capacity=cap,fraction=len(names)/cap)
  assert len(names)<=.60*cap,(top,face,counts[face])
  start=math.floor((length-(len(names)-1)*PITCH)/2/PITCH)*PITCH
  for i,n in enumerate(names):
   q=round(start+i*PITCH,6);xy=[q,h-.042] if face=='N' else [q,.042] if face=='S' else [.042,q] if face=='W' else [w-.042,q]
   pins.append(dict(name=n,face=face,layer='M3' if face in 'NS' else 'M4',xy_um=xy))
 name=name or top
 out=R/'physical/s81_vm_write_edge_1015';out.mkdir(parents=True,exist_ok=True)
 d=dict(schema='opentallas.s81.vm-write-leaf-pins.v1',name=name,master=top,parameters=params,source=str(source.relative_to(R)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),outline_um=box,pitch_um=PITCH,ports=ports,total_port_bits=len(flat),face_capacity=counts,pins=pins,status='CANDIDATE_ACTUAL_BITS_NOT_NATIVE_VIEW_OR_GLOBAL_REACH_QUALIFIED')
 (out/(name+'.json')).write_text(json.dumps(d,indent=1)+'\n')
 (out/(name+'.tcl')).write_text('# Actual-source pin candidate; not an adopted die slot.\n'+''.join('place_pin -pin_name {'+p['name']+'} -layer '+p['layer']+' -location {'+' '.join(f'{v:.6f}' for v in p['xy_um'])+'} -force_to_die_boundary\n' for p in pins))
 return {k:v for k,v in d.items() if k!='pins'}
def main():
 base=R/'rtl/dsrom_sys/s81_ph/vm';rows=[]
 faces={f:[] for f in 'NSEW'}
 for c in range(53):
  f='N' if c<27 else 'S'
  for n,v in [('i_v',1),('i_row',14),('i_mask',4),('i_data',128),('i_tag',8),('i_capture_lane',2),('i_storage_slot',2)]:faces[f]+=bits(n,c*v,v,53*v)
 for b in range(8):
  f='E' if b<4 else 'W'
  for lane in range(3):
   for n,v in [('o_v',1),('o_slot',2),('o_row',14),('o_mask',4),('o_data',128),('o_tag',8)]:faces[f]+=bits(n,(3*b+lane)*v,v,24*v)
 faces['N']+=['ck','rst_n'];faces['E']+=['fault']
 rows.append(plan('dsfd_vm_static_wdispatch128',base/'dsfd_vm_static_wdispatch128.sv',dict(NSRC=53,NBANK=8,BANK_BASE=0),[734.4,345.6],faces))
 for orientation in ['east','west']:
  faces={f:[] for f in 'NSEW'};capture='W' if orientation=='east' else 'E';out='E' if orientation=='east' else 'W'
  for lane in range(3):
   for n,v in [('capture_v',1),('capture_slot',2),('capture_row',14),('capture_mask',4),('capture_data',128),('capture_tag',8)]:faces[capture]+=bits(n,lane*v,v,3*v)
  for n,v in [('o_v',1),('o_row',14),('o_mask',4),('o_data',128),('o_tag',8),('fault',1)]:faces[out]+=bits(n,0,v,v)
  faces['S']=['ck','rst_n','drain_v','drain_slot[0]','drain_slot[1]']
  rows.append(plan('dsfd_vm_static_wstage128',base/'dsfd_vm_static_wstage128.sv',dict(DEPTH=3),[86.4,86.4],faces,'dsfd_vm_static_wstage128_'+orientation))
 faces={f:[] for f in 'NSEW'}
 for n,v in [('i_v',53),('i_row',742),('i_tag',424)]:faces['N']+=bits(n,0,v,v)
 for n,v in [('o_v',53),('o_row',742),('o_tag',424),('o_epoch',3)]:faces['S']+=bits(n,0,v,v)
 faces['W']=['ck','rst_n']
 rows.append(plan('dsfd_vm_static_w0_header',base/'dsfd_vm_static_w0.sv',dict(NSRC=53),[216,86.4],faces))
 faces={f:[] for f in 'NSEW'}
 faces['N']=bits('i_data',0,6784,6784);faces['S']=bits('o_data',0,6784,6784)
 faces['W']=bits('i_mask',0,212,212);faces['E']=bits('o_mask',0,212,212)+['ck','rst_n']+bits('o_epoch',0,3,3)
 rows.append(plan('dsfd_vm_static_w0_payload',base/'dsfd_vm_static_w0.sv',dict(NSRC=53),[1166.4,86.4],faces))
 faces={f:[] for f in 'NSEW'}
 for n,v in [('pv',53),('pr',742),('header_epoch',3),('payload_epoch',12)]:faces['N']+=bits(n,0,v,v)
 faces['W']=bits('cap_v',0,96,96)+['ck_control','rst_n']
 for n,v in [('lane',106),('lv',53),('dr_v',32),('dr_s',64),('own',3)]:faces['S']+=bits(n,0,v,v)
 rows.append(plan('dsfd_vm_static_wcontrol',base/'dsfd_vm_static_wcontrol.sv',dict(NSRC=53),[216,86.4],faces))
 # Exact dispatch->storage native pin correspondence in one wires-only group.
 pp=R/'physical/s81_vm_write_edge_1015';disp=json.loads((pp/'dsfd_vm_static_wdispatch128.json').read_text());dp={p['name']:p['xy_um'] for p in disp['pins']};edges=[]
 # dispatch x108.0; west storage x0; east storage x864.0;21.6um channels.
 for bank in range(8):
  east=bank<4;sp=json.loads((pp/('dsfd_vm_static_wstage128_'+('east' if east else 'west')+'.json')).read_text());sp={p['name']:p['xy_um'] for p in sp['pins']}
  ox=864.0 if east else 0;oy=86.4*(bank%4)
  for lane in range(3):
   for on,inn,width in [('o_v','capture_v',1),('o_slot','capture_slot',2),('o_row','capture_row',14),('o_mask','capture_mask',4),('o_data','capture_data',128),('o_tag','capture_tag',8)]:
    for bit in range(width):
     dn=f'{on}[{(3*bank+lane)*width+bit}]';sn=f'{inn}[{lane*width+bit}]';a=dp[dn];b=sp[sn];length=abs(a[0]+108.0-b[0]-ox)+abs(a[1]-b[1]-oy)
     edges.append(dict(bank=bank,dispatch_pin=dn,stage_pin=sn,manhattan_um=round(length,6)))
 rootplan=dict(total_roots=150,control=dict(count=1,port='ck_control'),header=dict(count=1,port='ck_header'),payload=dict(count=4,port='ck_payload[3:0]'),dispatch=dict(count=16,port='ck_dispatch[4*slice+quarter]'),stage=dict(count=128,port='ck_stage[32*slice+bank]'),reset='Each actual leaf owns local two-flop reset release from rst_n. Clock periods/phases must be delivered independently from each measured insertion; no shared parent flops hidden.',edge_ages='W0 P, dispatch P+1/P+2, storage P+3, scatter sample P+4+lane; root split adds no stage',qualification='All scalar core clock ties are functional simulation only. Actual150root CTS/TTFF/DRC0/face-pin/reset ownership and native IO budgets remain OPEN.')
 result=dict(schema='opentallas.s81.vm-write-edge-plan.v1',status='SOURCE_BOUND_CANDIDATE_WITH_LOCAL_BIT_REACH_ONLY',leaf_specs=rows,clock_ownership=rootplan,group=dict(outline_um=[950.4,345.6],dispatch_xy_um=[108.0,0],stage_xy_um=[[864.0 if b<4 else 0,86.4*(b%4)] for b in range(8)],dispatch_to_stage_bit_count=len(edges),max_manhattan_um=max(e['manhattan_um'] for e in edges),over500=sum(e['manhattan_um']>500 for e in edges)),open=['Native mapped leaf CTS/TTFF/DRC0 and output drain mux IO budget','Actual group to native scatter/bank paths; uniform real relay stages/calendar if over500','Global53source bus distribution,150individualclockdelivery/reset/PG and fullcanonical geometry','W0/control lane function physical mapping and timing; no ready/backpressure'],edges=edges)
 (pp/'plan.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['edges','leaf_specs']},indent=2))
if __name__=='__main__':main()
