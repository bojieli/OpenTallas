#!/usr/bin/env python3
"""Source-bound43.2square first-stage record-capture pins, E/W output variants."""
import argparse,hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import die_port_bind as D
FIELDS=[('v',1),('we',1),('row',14),('mask',4),('data',128),('tag',8)];W=H=43.2

def tracks(n,layer):
 vv=[]
 for k in range(1000):
  v=round(.012+.048*k,3)
  if v<2.16 or v>41.04 or layer=='M5' and .18<=v%5.4<=.74:continue
  if not vv or v-vv[-1]>=.096-1e-6:vv.append(v)
 assert len(vv)>=n
 return [vv[int((i+.5)*len(vv)/n)] for i in range(n)]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 m=next(x for x in D.parse_modules(a.source.read_text(),str(a.source)) if x.name=='dsfd_vm_static_write_capture128');env=m.env({})
 actual={n:(d,m.width(n,env)) for n,(d,_) in m.ports.items()};expected={prefix+n:(direction,w) for prefix,direction in [('i_','input'),('o_','output')] for n,w in FIELDS};expected.update(ck=('input',1),rst_n=('input',1));assert actual==expected
 a.out.mkdir(parents=True,exist_ok=True)
 for side in ['E','W']:
  ports={};txt=['# Actual156bit first-stage record;43.2square; source-pinned pin option only']
  for prefix,face,L in [('i_','N','M5'),('o_',side,'M4')]:
   ordered=[(prefix+n,i,w) for n,w in FIELDS for i in range(w)]
   for (n,i,w),p in zip(ordered,tracks(156,L)):
    ports.setdefault(n,dict(bits=w,direction=actual[n][0],uniform=False,per_bit=[]))['per_bit'].append([face,L,p,.192])
    label=n if w==1 else f'{n}[{i}]';x,y=(p,H) if face=='N' else (W if face=='E' else 0,p)
    txt.append(f'place_pin -pin_name {{{label}}} -layer {L} -location {{{x:.3f} {y:.3f}}} -pin_size {{'+('.024 .192' if L=='M5' else '.192 .024')+'} -force_to_die_boundary')
  control='W' if side=='E' else 'E'
  for n,pos in [('ck',21.132),('rst_n',22.044)]:
   ports[n]=dict(bits=1,direction='input',uniform=False,per_bit=[[control,'M4',pos,.192]])
   txt.append(f'place_pin -pin_name {{{n}}} -layer M4 -location {{{0 if control=="W" else W:.3f} {pos:.3f}}} -pin_size {{.192 .024}} -force_to_die_boundary')
  d=dict(schema='opentallas.s81.assigned_pins.v1',master=m.name,case='first_existing_scatter_stage_output_'+side,outline_um=[W,H],ports=ports,clock_entries={'stream':['ck']},reset_entries=['rst_n'],source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),port_bits=314,scope='SOURCE_BOUND_PIN_OPTION_NOT_NATIVE_CLOSURE',requirements=['ActualCKroot/phi-R/TT/FF/DRC andnativepinbudget','All156rawrecordbits remain actual RTL; routing is not qualified','Actualallincidentpinreach andaggregatecuts withq8dispatch/storage/output placements'])
  name='dsfd_vm_static_write_capture128_'+side
  (a.out/(name+'.json')).write_text(json.dumps(d,indent=1)+'\n');(a.out/(name+'.tcl')).write_text('\n'.join(txt)+'\n')
 print(json.dumps(dict(master=m.name,port_bits=314,source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),variants=['E','W'])))
if __name__=='__main__':main()
