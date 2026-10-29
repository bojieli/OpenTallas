#!/usr/bin/env python3
"""DIE-QC-30 form (b2) what-if: notch the canonical M8 strap over each failing PHY clock pin (gap = patch .192 + 2x spacing),
re-run the in-pin landing census for those pins on the notched grid, and check each strap remainder still meets >=1
same-net M9 stripe (VIA89 site). Plan only; adoption needs an opt-in flag in the shared PG generator (ROOT-MERGE)."""
import argparse,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import die_clock_128 as C
p=argparse.ArgumentParser()
for n in ['census','clock-plan','pg','out']:p.add_argument('--'+n,required=True)
p.add_argument('--reserved-power',action='append',default=[]);p.add_argument('--spacing',type=float,required=True)
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
cen=json.load(open(a.census));pg=json.load(open(a.pg));half=.096+a.spacing
notches=[];new=list(pg)
for f in cen['failures']:
  x,ref=f['reference_xy_um']
  hit=[r for r in new if r[1]=='M8' and r[3]<=ref<=r[5] and r[2]<=x<=r[4]]
  for r in hit:
    new.remove(r);L=[r[0],'M8',r[2],r[3],x-half,r[5]];R=[r[0],'M8',x+half,r[3],r[4],r[5]]
    new+= [L,R]
    m9=[s for s in pg if s[1]=='M9' and s[0]==r[0]]
    feed=lambda seg:sorted([round((s[2]+s[4])/2,3) for s in m9 if s[2]<seg[4] and s[4]>seg[2] and s[3]<=seg[3] and s[5]>=seg[5]],key=lambda v:abs(v-x))[:1]
    notches.append(dict(port=f['port'],net=r[0],strap_y=[r[3],r[5]],gap_x=[round(x-half,4),round(x+half,4)],gap_um=round(2*half,4),
      left_feed_m9_x=feed(L),right_feed_m9_x=feed(R)))
json.dump(new,open(out/'pg_rects_notched.json','w'))
ix=C.MetalIndex(a.spacing)
for s in C.pg_shapes(new):ix.add(s)
for fn in a.reserved_power:
  for s in C.pg_shapes(json.load(open(fn))):ix.add(s)
for r in json.load(open(a.clock_plan))['records']:
  x,y=r['backbone_xy_um'][0],r['m8_witness_y_um'];ix.add(('M8',r['net'],'clock_access',y-.04,y+.04,x-.096,x+.096))
for r in cen['records']:
  x,y=r['entry_xy_um'];ix.add(('M8',r['net'],'access',y-.04,y+.04,x-.096,x+.096))
recs=[];fails=[]
for f in cen['failures']:
  x=f['reference_xy_um'][0];y=next((y for y in f['legal_in_pin_rows_um'] if not ix.hits(('M8',f['net'],'access',y-.04,y+.04,x-.096,x+.096),first=True)),None)
  if y is None:fails.append(f);continue
  ix.add(('M8',f['net'],'access',y-.04,y+.04,x-.096,x+.096));recs.append(dict(port=f['port'],entry_xy_um=[x,y]))
ok=not fails and all(n['left_feed_m9_x'] and n['right_feed_m9_x'] for n in notches)
json.dump(dict(status='PASS_GEOMETRY' if ok else 'FAIL',notches=notches,landings=recs,failures=fails,total_landed=len(cen['records'])+len(recs),
  total_pins=len(cen['records'])+len(cen['failures']),ir='UNCHECKED (strap remainders fed by nearest M9; no IR run)',physical_route=False),open(out/'phy_notch_plan.json','w'),indent=1)
print('PASS_GEOMETRY' if ok else 'FAIL','landed',len(cen['records'])+len(recs),'notches',[(n['port'],n['gap_um'],n['left_feed_m9_x'],n['right_feed_m9_x']) for n in notches])
