#!/usr/bin/env python3
"""Exact source ports/pins for the eight-bank/eight-slot return candidate."""
from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
import die_port_bind as D
W=H=129.6
src=R/'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_return_bank8.sv'
mod=next(m for m in D.parse_modules(src.read_text(),str(src)) if m.name=='dsfd_vm_static_return_bank8')
env=mod.env({'DW':128,'LANE':0})
widths={n:dict(direction=d,bits=mod.width(n,env)) for n,(d,_) in mod.ports.items()}
faces={f:[] for f in 'NSEW'}
def add(face,name,lo,hi):
 faces[face].extend((name,i) for i in range(lo,hi))
add('N','i_data',0,512);add('E','i_data',512,1024)
for n in ['i_v','i_tag']:add('N',n,0,widths[n]['bits'])
for n in ['release_v','release_group','release_mask','prepare_v','prepare_group','prepare_mask']:add('E',n,0,widths[n]['bits'])
add('S','o_data',0,512);add('W','o_data',512,1024)
for n in ['o_v','o_group','fault']:add('S',n,0,widths[n]['bits'])
for n in ['ck','rst_n','peer_token','completion_token']:add('W',n,0,widths[n]['bits'])
pins={n:[] for n in widths};txt=['# SOURCE-EXACT candidate, no native timing or global reach claim.'];stats={}
for face,ordered in faces.items():
 layer='M5' if face in 'NS' else 'M4'
 sites=[]
 for k in range(2700):
  x=round(.012+.048*k,3)
  if x<2.16 or x>W-2.16:continue
  if layer=='M5' and .18<=x%5.4<=.74:continue
  if not sites or x-sites[-1]>=.144-1e-6:sites.append(x)
 assert len(sites)>=len(ordered),(face,len(sites),len(ordered))
 points=[sites[int((i+.5)*len(sites)/len(ordered))] for i in range(len(ordered))]
 for (name,bit),pos in zip(ordered,points):
  pins[name].append((bit,[face,layer,pos,.192]))
  port=name if widths[name]['bits']==1 else f'{name}[{bit}]'
  x,y=(pos,H if face=='N' else 0) if face in 'NS' else (W if face=='E' else 0,pos)
  sz='.024 .192' if layer=='M5' else '.192 .024'
  txt.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}} -force_to_die_boundary')
 stats[face]=dict(bits=len(ordered),layer=layer,min_spacing_um=round(min(b-a for a,b in zip(points,points[1:])),3),available_pg_free_sites=len(sites))
ports={n:dict(**widths[n],uniform=False,per_bit=[p for _,p in sorted(pp)]) for n,pp in pins.items()}
for n,pp in pins.items():assert [b for b,p in sorted(pp)]==list(range(widths[n]['bits'])),n
out=R/'physical/s81_vm_return_bank8_1015';out.mkdir(parents=True,exist_ok=True)
(out/'pins.tcl').write_text('\n'.join(txt)+'\n')
rep=dict(schema='opentallas.s81.assigned_pins.v1',master=mod.name,parameters=dict(DW=128,LANE=0),outline_um=[W,H],ports=ports,clock_entries={'stream':['ck']},reset_entries=['rst_n'],source=str(src.relative_to(R)),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),port_bits=sum(q['bits'] for q in widths.values()),checks=stats,scope='SOURCE_BOUND_NATIVE_CANDIDATE_NOT_PHYSICAL_CLOSURE',open=['route/CTS/TT/FF/DRC','all actual bank/lane/output peer wire lengths and aggregate cuts','parent releaseprepare clock and schedule integration'])
assert rep['port_bits']==2183,rep['port_bits']
(out/'pins.json').write_text(json.dumps(rep,indent=1)+'\n')
print(json.dumps(dict(port_bits=rep['port_bits'],checks=stats,source_sha256=rep['source_sha256'])))
