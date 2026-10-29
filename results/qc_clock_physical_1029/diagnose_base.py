#!/usr/bin/env python3
import json,argparse
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--geometry',required=True);p.add_argument('--clock-seed',required=True);p.add_argument('--out',required=True);a=p.parse_args()
f=json.load(open(a.base))['failures'][0];x,y=f['base_xy_um'];g=json.load(open(a.geometry));D=g['dbu'];rows=[]
for scope,rr in [('signal',g['signal_shapes']),('obs',g['obstructions']),('nativePG',g['existing_supplies'])]:
 for r in rr:
  if scope=='signal':inst,pin,l,*b=r;owner=inst+'/'+pin
  else:owner,l,*b=r
  if l not in ['M6','M7']:continue
  x0,y0,x1,y1=[q/D for q in b]
  if x0<x+2 and x1>x-2 and y0<y+1.4 and y1>y-1.4:rows.append([scope,owner,l,x0,y0,x1,y1])
del g
for n,l,x0,y0,x1,y1 in json.load(open(a.clock_seed)):
 if l in ['M6','M7'] and x0<x+2 and x1>x-2 and y0<y+1.4 and y1>y-1.4:rows.append(['clock_base',n,l,x0,y0,x1,y1])
json.dump(dict(failure=f,rows=rows),open(a.out,'w'),indent=1);print(f);print(*rows,sep='\n')
