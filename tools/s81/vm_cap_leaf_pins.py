#!/usr/bin/env python3
"""Generous exact-source capleaf IO/clock slot-change request, not die adoption."""
import argparse,hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import die_port_bind as D
from vm_scatter_lane_pins import sites

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--capl',type=Path,required=True);p.add_argument('--system',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();module=next(m for m in D.parse_modules(a.source.read_text(),str(a.source)) if m.name=='dsfd_vm_static_cap_leaf');env=module.env({'E':8});widths={n:dict(bits=module.width(n,env),direction=d) for n,(d,_) in module.ports.items()};expected={'ck':1,'rn':1,'gid':4,'f_c':832,'flush':1,'o_v':1,'o_row':14,'o_m':16,'o_d':512,'flt':5};assert {n:v['bits'] for n,v in widths.items()}==expected
 W,H=172.8,259.2;pins={n:[] for n in widths};table=[]
 for face,fields in [('N',[('f_c',832)]),('S',[('o_v',1),('o_row',14),('o_m',16),('o_d',512),('flt',5)])]:
  ordered=[(n,i) for n,w in fields for i in range(w)]
  for (n,i),pos in zip(ordered,sites(len(ordered))):pins[n].append((i,face,'M5',pos));table.append((n,i,face,'M5',pos))
 ordered=[('ck',0),('rn',0)]+[('gid',i) for i in range(4)]+[('flush',0)]
 for k,(n,i) in enumerate(ordered):
  pos=round(.012+.048*round((H/2+(k-3)*.192-.012)/.048),3);pins[n].append((i,'W','M4',pos));table.append((n,i,'W','M4',pos))
 assert len(table)==1387 and len(set((f,l,p) for n,i,f,l,p in table))==1387
 checks={}
 for face,span in [('N',W),('S',W),('W',H)]:
  vals=sorted(p for n,i,f,l,p in table if f==face);spacing=min(b-a for a,b in zip(vals,vals[1:]));assert spacing>=.096-1e-6;checks[face]=dict(bits=len(vals),min_spacing_um=round(spacing,6),raw048_track_share=len(vals)/(span/.048),native096_slot_share=len(vals)/(span/.096),PG_exclusion=('M5 phase5.4um forbidden .18..74; 2.16umcornerkeepout' if face!='W' else 'Control M4nativegrid; actualnativePG review required'))
 assigned=dict(schema='opentallas.s81.assigned_pins.v1',master=module.name,parameters={'E':8},outline_um=[W,H],ports={n:dict(**widths[n],uniform=False,per_bit=[[f,L,pos,.192] for _,f,L,pos in sorted(pp)]) for n,pp in pins.items()},port_bits=len(table),clock_entries={'serial_capture':['ck']},clock_period_ps=1111.111111,reset_entries=['rn'],reset_contract='rn is synchronous released serial reset from actual parent; not independent asynchronous reset tree',source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),transitive_capl_sha256=hashlib.sha256(a.capl.read_bytes()).hexdigest(),face_checks=checks,status='REQUESTED_GENEROUS_NATIVE_LEAF_CONTRACT_NOT_DIE_ADOPTED',open=['ActualnativeIO/PG/CTS/TTsetup/FFhold/DRC0','Fullparentcap/status/flushroots and16x34 phase/epochdelivery','Allproducer/outputglobaltrafficcuts and registeredflightages'])
 text=['# Actual source E8 capleaf slot-change candidate:172.8x259.2um, one serial0.9GHz ck root.']
 for n,i,f,L,pos in table:
  name=n if expected[n]==1 else f'{n}[{i}]';x,y=(pos,H if f=='N' else 0) if f in 'NS' else (0,pos);size='.024 .192' if L=='M5' else '.192 .024';text.append(f'place_pin -pin_name {{{name}}} -layer {L} -location {{{x:.3f} {y:.3f}}} -pin_size {{{size}}} -force_to_die_boundary')
 system=json.loads(a.system.read_text());B=next(o for o in system['options'] if o['name'].startswith('B_'));leaves=[];overlaps=[]
 for g in range(16):
  x,y=15703.2+194.4*(g%4),17729.28+280.8*(g//4);b=dict(name=f'VM_cap{g}',logical_gid=g,xy_um=[x,y],outline_um=[W,H],orientation='R0',master=module.name,source_roots=list(range(8*g,8*g+8)),clock_root_request=f'cap_{g}_serial_ck',clock_port='ck')
  for other in B['nodes']+B['fixed']+leaves:
   xx,yy=other['xy_um'];ww,hh=other['outline_um']
   if x<xx+ww and x+W>xx and y<yy+hh and y+H>yy:overlaps.append([b['name'],other['name']])
  leaves.append(b)
 assert not overlaps,overlaps
 slot=dict(status='B_SYSTEM_SLOT_CHANGE_REQUEST_READY_FOR_NATIVE_LEAF_MEASUREMENT',basis='Actual current B470placedreal leaves, source-bound328core+150edge;8readblocks remainunplaced',system_sha256=hashlib.sha256(a.system.read_bytes()).hexdigest(),reservation_xywh_um=[15703.2,17729.28,756,1101.6],lane_pitch_um=[194.4,280.8],interleaf_channel_um=[21.6,21.6],leaves=leaves,coarse_body_overlaps=overlaps,producer_separate='sp_capture remains x13942.8..15670.776,y17837.28..18398.856; t_vm13376 feeds cap16; actualproducer pin binding pending',boundary_bits=dict(input_f_c=13312,additional_parent_status=64,output_per_leaf=548,leaf_clock_roots=16),cut_scope='Only actualleaf face capacity proven below; no claimed allboundarycut<=.60 without clock/PG/phase/throughtraffic',open=['16actualx34 native footprints remainadditional, not merged withupstreamcapture','Parent scalarclock alias is not physical rootdelivery;598rootbind owns sourceplumbing','Uniformregisteredinput/outputdistribution andcompilerages notyetpriced'])
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'dsfd_vm_static_cap_leaf.json').write_text(json.dumps(assigned,indent=1)+'\n');(a.out/'dsfd_vm_static_cap_leaf.tcl').write_text('\n'.join(text)+'\n');(a.out/'slot_request.json').write_text(json.dumps(slot,indent=1)+'\n');print(json.dumps(dict(port_bits=len(table),face_checks=checks,overlaps=overlaps,source_sha256=assigned['source_sha256'],capl_sha256=assigned['transitive_capl_sha256']),indent=1))
if __name__=='__main__':main()
