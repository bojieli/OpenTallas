#!/usr/bin/env python3
"""Plan native M7 macro supply VIA78 contacts inside same-net die M8 stripes.
No added bridge or pin metal, and no obstruction exemption outside actual pin.
All input/output conductor coordinates are integer DBU. No IR qualification.
"""
import argparse,bisect,collections,json
from pathlib import Path

def inside(a,b):return b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--grid',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 inv=json.load(open(a.inventory));D=inv['dbu'];grid=json.load(open(a.grid));via=inv['vias']['VIA78'];enc={ly:r for ly,*r in via if ly in ['M7','M8']};assert set(enc)=={'M7','M8'}
 rows=collections.defaultdict(list)
 for net,ly,*r in grid:
  if ly=='M8':rows[net].append(tuple(round(v*D) for v in r))
 for rr in rows.values():rr.sort(key=lambda r:r[1])
 ys={n:[r[1] for r in rr] for n,rr in rows.items()};contacts=[];failed=[];terms=[];why=collections.Counter()
 for m in inv['macros']:
  for term in m['pins']:
   net='VDD' if term['kind']=='POWER' else 'VSS';rr=rows.get(net,[]);yidx=ys.get(net,[]);start=len(contacts)
   for si,(ly,*pin) in enumerate(term['shapes_dbu']):
    if ly!='M7':failed.append(dict(inst=m['inst'],pin=term['pin'],shape=si,reason='unsupported_layer',rect_dbu=pin));continue
    # VIA78 bottom enclosure must be wholly inside this native PG rectangle.
    lo=pin[1]-enc['M7'][1];hi=pin[3]-enc['M7'][3];xx=(pin[0]+pin[2])//2
    xlo=pin[0]-enc['M7'][0];xhi=pin[2]-enc['M7'][2]
    if xlo>xhi or lo>hi:raise ValueError('native pin cannot enclose VIA78')
    candidates=rr[max(0,bisect.bisect_left(yidx,lo-1000)):bisect.bisect_right(yidx,hi+1000)]
    valid=[]
    for stripe in candidates:
     yylo=max(lo,stripe[1]-enc['M8'][1]);yyhi=min(hi,stripe[3]-enc['M8'][3]);ax=max(xlo,stripe[0]-enc['M8'][0]);bx=min(xhi,stripe[2]-enc['M8'][2])
     if yylo<=yyhi and ax<=bx:
      y=max(yylo,min((pin[1]+pin[3])//2,yyhi));x=max(ax,min(xx,bx));valid.append((abs(2*y-pin[1]-pin[3]),x,y,stripe))
    if not valid:
     failed.append(dict(inst=m['inst'],pin=term['pin'],shape=si,reason='no_enclosed_same_net_M8_crossing',rect_dbu=pin));why['no_enclosed_same_net_M8_crossing']+=1;continue
    _,x,y,stripe=min(valid);metal={l:[x+r[0],y+r[1],x+r[2],y+r[3]] for l,r in enc.items()}
    assert inside(metal['M7'],pin) and inside(metal['M8'],stripe)
    contacts.append(dict(inst=m['inst'],pin=term['pin'],shape=si,net=net,via='VIA78',xy_dbu=[x,y],native_pin_dbu=pin,grid_rect_dbu=stripe,metal_dbu=metal))
   terms.append(dict(inst=m['inst'],pin=term['pin'],net=net,existing_bound_net=term['net'],contacts=len(contacts)-start,pin_shapes=len(term['shapes_dbu'])))
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 json.dump(dict(source=inv['source'],dbu=D,contacts=contacts,failed=failed,terms=terms),open(out/'join_plan.json','w'),separators=(',',':'))
 summary=dict(macros=len(inv['macros']),terms=len(terms),terms_with_direct_contacts=sum(t['contacts']>0 for t in terms),pin_shapes=sum(t['pin_shapes'] for t in terms),direct_contacts=len(contacts),unresolved_shapes=len(failed),reasons=dict(why),added_wire_rectangles=0,verdict='CANDIDATE_PENDING_OBSTACLE_CHECK')
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
