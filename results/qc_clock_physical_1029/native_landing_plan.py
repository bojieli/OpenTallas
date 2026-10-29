#!/usr/bin/env python3
"""Select actual native M7->M8 landings before clock-cell PG access.
Explicit spacing required. Out-of-pin growth numbers are diagnostic only.
"""
import argparse,json,math,sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import die_clock_128 as C
p=argparse.ArgumentParser()
for n in ['endpoints','clock-plan','pg','out']:p.add_argument('--'+n,required=True)
p.add_argument('--reserved-power',action='append',default=[]);p.add_argument('--spacing',type=float,required=True);p.add_argument('--probe-grow',type=float,default=0);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
e=json.load(open(a.endpoints));e=e.get('endpoints',e);ix=C.MetalIndex(a.spacing)
for s in C.pg_shapes(json.load(open(a.pg))):ix.add(s)
for file in a.reserved_power:
 for s in C.pg_shapes(json.load(open(file))):ix.add(s)
c=json.load(open(a.clock_plan));assert c['status']=='PASS_GEOMETRY' and not c['failures']
for r in c['records']:
 x,y=r['backbone_xy_um'][0],r['m8_witness_y_um'];ix.add(('M8',r['net'],'clock_access',y-.04,y+.04,x-.096,x+.096))
records=[];bad=[];reserved=[]
for port,ep in e.items():
 x,ref=ep.get('xy_um',ep.get('xy'));x0,y0,x1,y1=ep['rect_um'];hy=.027
 assert x-.016>=x0-1e-7 and x+.016<=x1+1e-7
 ys=sorted([round(.04+k*.08,6) for k in range(math.ceil((y0+hy-.04)/.08-1e-8),math.floor((y1-hy-.04)/.08+1e-8)+1)],key=lambda y:abs(y-ref))
 def clear(y):return not ix.hits(('M8',ep['net'],'access',y-.04,y+.04,x-.096,x+.096),first=True)
 found=next((y for y in ys if clear(y)),None)
 if found is None:
  r=dict(port=port,inst=ep['inst'],pin=ep['pin'],net=ep['net'],rect_um=ep['rect_um'],reference_xy_um=[x,ref],legal_in_pin_rows_um=ys)
  if a.probe_grow:
   extra=sorted([round(.04+k*.08,6) for k in range(math.ceil((ref-a.probe_grow-.04)/.08),math.floor((ref+a.probe_grow-.04)/.08)+1)],key=lambda y:abs(y-ref))
   new=next((y for y in extra if clear(y)),None)
   r['diagnostic_outside_pin_row_um']=new
   r['diagnostic_minimum_symmetric_pin_height_um']=None if new is None else round(2*(abs(new-(y0+y1)/2)+hy),6)
  bad.append(r);continue
 ix.add(('M8',ep['net'],'access',found-.04,found+.04,x-.096,x+.096))
 rec=dict(port=port,inst=ep['inst'],pin=ep['pin'],net=ep['net'],entry_xy_um=[x,found],rect_um=ep['rect_um'],M7_via_enclosed=True,M8_patch_um=[.192,.08],spacing_um=a.spacing);records.append(rec)
 # PG constructor adds40nm normal M8 clearance, so reserve the remainder.
 extra=max(0,a.spacing-.04);reserved.append([ep['net'],'M8',x-.096-extra,found-.04-extra,x+.096+extra,found+.04+extra])
status='FAIL' if bad else 'PASS_GEOMETRY';json.dump(dict(status=status,records=records,failures=bad,spacing_um=a.spacing,physical_route=False),open(out/'landing_plan.json','w'),indent=1);json.dump(reserved,open(out/'reserved.json','w'),separators=(',',':'));print(status,len(records),len(bad),'spacing',a.spacing,flush=True)
if bad:print('growth_probe_max_height',max((r.get('diagnostic_minimum_symmetric_pin_height_um') or 0 for r in bad)),flush=True)
