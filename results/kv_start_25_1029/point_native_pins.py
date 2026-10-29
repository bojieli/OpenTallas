#!/usr/bin/env python3
"""Site START/reset pins near the actual measured native entry, uniform by type.

This names physical endpoints; it does not turn an entry clock into an origin-FF
clock measurement. Origin/reset-export CK remains a declared local contract.
"""
import json,sys,math
from pathlib import Path
R=Path(sys.argv[1]);E=Path(sys.argv[2]);sys.path.insert(0,str(R/'source'))
import schema as S
p=json.load(open(E/'plan.json'));P=S.Plan(p)
taps={t['part']:t['xy_um'] for t in json.load(open(R/'inputs/proof/tap_arrivals_TT.json'))['taps'] if t['port'].endswith('__clk')}
by={};entries={}
for part,q in P.parts.items():
 x,y=[a-b for a,b in zip(taps[part],q['origin_um'])];w,h=P.ptype(part)['outline_um'];o=q.get('orient','R0')
 if o in ('MY','R180'):x=w-x
 if o in ('MX','R180'):y=h-y
 xy=[round(x,3),round(y,3)]
 if q['type'] in entries:assert entries[q['type']]==xy,(part,entries[q['type']],xy)
 entries[q['type']]=xy
roles={'cland_tstart_in':-1.728,'cland_tstart_out':-.864,'cland_raw_reset_out':.864}
for tn,t in p['partition_types'].items():
 cx,cy=entries[tn];w,h=t['outline_um'];taken=[]
 other=[q for q in t.get('clock',{}).get('landing_contract',{}).get('pins',[]) if q['name'] not in roles and q['layer']=='M7']
 for pin in t.get('clock',{}).get('landing_contract',{}).get('pins',[]):
  if pin['name'] not in roles:continue
  placed=None
  for n in range(20):
   dx=(0 if n==0 else math.ceil(n/2)*.128*(1 if n%2 else -1))
   xx=round((cx+dx-.032)/.064)*.064+.032;yy=round((cy+roles[pin['name']])/.27)*.27
   if not (.05<=xx<=w-.05 and .22<=yy<=h-.22):continue
   if any(abs(xx-q['xy_um'][0])<.081 and abs(yy-q['xy_um'][1])<.433 for q in other+taken):continue
   placed=[round(xx,4),round(yy,4)];break
  assert placed is not None,(tn,pin['name'],cx,cy)
  pin['xy_um']=placed;pin['layer']='M7';pin['native_entry_reference_um']=entries[tn];taken.append(pin)
  by.setdefault(tn,{})[pin['name']]=placed
# Keep the scalar CLOCK/RESET ABI exact for the native ASTK bit-vector declarations.
for t in p['partition_types'].values():
 for h in t.get('hard_cores',[]):
  if h['module']=='kv3_astk':h['pins_file']=str(R/'astk_index0.json')
(E/'plan_native_pins.json').write_text(json.dumps(p,indent=1))
ports=[]
sp=json.load(open(E/'sidecar.json'))['count_aligned']['start_pins']
for kind,events,key,pin,netkey in [('start_source',sp['die_inputs'],'src_part','cland_tstart_out','net'),('start_capture',sp['die_outputs'],'dst_part','cland_tstart_in','net'),('reset_source',sp.get('reset_inputs',[]),'src_part','cland_raw_reset_out','net')]:
 for e in events:
  part=e[key];typ=P.parts[part]['type'];local=by[typ][pin]
  ports.append(dict(role=kind,net=e[netkey],instance=part,master=P.ptype(part)['module'],pin=pin,xy_um=P.to_die(part,local),local_xy_um=local,
                    native_entry_clock=f't_{part}__clk',origin_ck_receipt='NOT RUN: physical origin/reset-export FF CK required; entry clock alone is insufficient'))
(E/'boundary_map.json').write_text(json.dumps(dict(qualification='PLAN terminals; actual sourceDB macro/FF receipts still required',ports=ports,type_pins=by),indent=1))
print(json.dumps(dict(types=len(by),boundary_ports=len(ports),max_pin_shift_from_native_um=max(sum(abs(a-b) for a,b in zip(v,entries[k])) for k,ps in by.items() for v in ps.values()),actual_ff_clock_qualified=False)))
