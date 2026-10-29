#!/usr/bin/env python3
"""DIE-QC-30 form (b1): die-local parent M7 clock stub for native M7 clock pins with no in-pin VIA78 landing.
For each failure of a native_landing_plan census, pick the nearest M8 row OUTSIDE the pin whose VIA78 M8 patch
(.192x.080) clears all M8 (canonical PG, reserved power, clock witnesses, the census's accepted landings) at the
census spacing, and whose M7 stub (pin width .032, from pin metal to the row incl. VIA78 M7 enclosure .027) clears
every other-net M7 shape (macro OBS/pins, reserved power M7) at M7 spacing .032. No PG change. Plan only."""
import argparse,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import die_clock_128 as C
p=argparse.ArgumentParser()
for n in ['census','clock-plan','pg','near-m7','out']:p.add_argument('--'+n,required=True)
p.add_argument('--reserved-power',action='append',default=[]);p.add_argument('--spacing',type=float,required=True)
p.add_argument('--stub-max',type=float,default=2.0);p.add_argument('--m7-space',type=float,default=.032)
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
cen=json.load(open(a.census));ix=C.MetalIndex(a.spacing)
for s in C.pg_shapes(json.load(open(a.pg))):ix.add(s)
m7=[]
for f in a.reserved_power:
  rows=json.load(open(f))
  for s in C.pg_shapes(rows):ix.add(s)
  m7+=[r for r in rows if r[1]=='M7']
for r in json.load(open(a.clock_plan))['records']:
  x,y=r['backbone_xy_um'][0],r['m8_witness_y_um'];ix.add(('M8',r['net'],'clock_access',y-.04,y+.04,x-.096,x+.096))
for r in cen['records']:
  x,y=r['entry_xy_um'];ix.add(('M8',r['net'],'access',y-.04,y+.04,x-.096,x+.096))
near=json.load(open(a.near_m7))
for inst,v in near.items():
  for kind in ('obs','sig','sup'):
    for r in v[kind]:
      if r[-5]=='M7':m7.append([f'{kind}:{r[0]}:{r[1] if kind!="obs" else ""}',*r[-5:]])
def m7_clear(net,inst,rect):
  x0,y0,x1,y1=rect;bad=[]
  for r in m7:
    if r[0]==net or r[0]==f'sig:{inst}:clk':continue
    rx0,ry0,rx1,ry1=r[2:6]
    if rx0<x1+a.m7_space-1e-6 and rx1>x0-a.m7_space+1e-6 and ry0<y1+a.m7_space-1e-6 and ry1>y0-a.m7_space+1e-6:bad.append(r)
  return bad
recs=[];fails=[]
for f in cen['failures']:
  x,ref=f['reference_xy_um'];x0,y0,x1,y1=f['rect_um'];hy=.027
  cand=[round(.04+k*.08,6) for k in range(math.floor((y0-a.stub_max-.04)/.08),math.ceil((y1+a.stub_max-.04)/.08)+1)]
  cand=sorted([y for y in cand if y-hy<y0-1e-6 or y+hy>y1+1e-6],key=lambda y:(max(y0-(y-hy),(y+hy)-y1),y))
  tried=[]
  for y in cand:
    patch=('M8',f['net'],'access',y-.04,y+.04,x-.096,x+.096);h=ix.hits(patch,first=True)
    stub=[x-.016,min(y0,y-hy),x+.016,max(y1,y+hy)]
    b=m7_clear(f['net'],f['inst'],stub) if not h else None
    tried.append(dict(row=y,m8=('clear' if not h else f'{h[0][1]} vs {ix.shapes[h[0][0]][:3]}'),m7=None if b is None else len(b)))
    if not h and not b:
      ix.add(patch)
      recs.append(dict(port=f['port'],inst=f['inst'],pin=f['pin'],net=f['net'],rect_um=f['rect_um'],entry_xy_um=[x,y],
        access_kind='parent M7 stub + VIA78',m7_stub_um=[round(v,4) for v in stub],stub_len_beyond_pin_um=round(max(y0-stub[1],stub[3]-y1),4),
        M8_patch_um=[.192,.08],spacing_um=a.spacing,rows_tried=tried));break
  else:fails.append(dict(f,rows_tried=tried))
st='PASS_GEOMETRY' if not fails else 'FAIL'
tot=len(cen['records'])+len(recs)
json.dump(dict(status=st,census_in=dict(landed=len(cen['records']),failed=len(cen['failures'])),stubs=recs,failures=fails,
  total_landed=tot,total_pins=len(cen['records'])+len(cen['failures']),physical_route=False),open(out/'phy_stub_plan.json','w'),indent=1)
print(st,'landed',tot,'of',len(cen['records'])+len(cen['failures']),'stubs',[(r['inst'],r['entry_xy_um'][1],r['stub_len_beyond_pin_um']) for r in recs])
