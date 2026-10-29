#!/usr/bin/env python3
"""Two source-identical SPB congestion fixes: local PHY pin bundles vs tall endpoint FF banks.
Original M6 overflow195/pinaccess0 missed: source/RTL/clock/FF count unchanged.
Uses the owner-labelled modeled M6/M7 PHY abstract; no vendor-pin qualification.
"""
from pathlib import Path
import sys,re,json,math,copy
base,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
lef=(base/'macros.lef').read_text();tcl=(base/'probe.tcl').read_text()
ff={n:(float(x),float(y)) for n,x,y in re.findall(r'place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}',tcl) if n not in ('phy','ep')}
pat=r' PIN ((?:rx|tx|st)\[\d+\])\n(.*?) END \1'
phy=lef.split('MACRO EP_SPB_PROBE')[0];pp={}
for m in re.finditer(pat,phy,re.S):
 a=re.search(r'RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)',m[2]);x0,y0,x1,y1=map(float,a.groups());pp[m[1]]=((x0+x1)/2+103.68,(y0+y1)/2)
assert len(pp)==1026,len(pp)
def reach(poses,pins):
 vals=[]
 for b in range(514):
  pts=[pins[f'rx[{b}]'] if b<512 else pins[f'st[{b-512}]']]+[poses[f'rx_s{s}_b{b}'] for s in range(4)]
  vals += [abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(pts,pts[1:])]
 for b in range(512):
  pts=[poses[f'tx_s{s}_b{b}'] for s in range(4)]+[pins[f'tx[{b}]']]
  vals += [abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(pts,pts[1:])]
 return max(vals)
def writevariant(tag,poses,pins,newlef):
 td=out/tag;td.mkdir(exist_ok=True)
 new=tcl
 changed={n:v for n,v in poses.items() if v!=ff[n]}
 for n,(x,y) in changed.items():
  expr=r'set yy \[expr \{round\([\d.]+\*\$dbu\)\}\]\n(if \{!\[dict exists \$row_orient \$yy\]\} \{error "native bank off actual row: '+re.escape(n)+r'"\}\nplace_inst -name '+re.escape(n)+r' -location )\{[\d.]+ [\d.]+\}'
  new,cnt=re.subn(expr,lambda m:f'set yy [expr {{round({y:.6f}*$dbu)}}]\n'+m[1]+f'{{{x:.6f} {y:.6f}}}',new)
  assert cnt==1,(n,cnt)
 # Exact sites and bounding boxes; DFF width bound2.16 deliberately includes body.
 names=list(poses);bad=[]
 for n,(x,y) in poses.items():
  if abs(x/.054-round(x/.054))>1e-5 or abs(y/.27-round(y/.27))>1e-5:bad.append((n,'site'))
  if x<767.368 and x+2.16>40.04 and y<1113.64 and y+.27>0:bad.append((n,'PHY_PG'))
  if x<423.36 and x+2.16>181.44 and y<1486.08 and y+.27>1088.64:bad.append((n,'EP'))
 byrow={}
 for n,(x,y) in poses.items():byrow.setdefault(round(y,6),[]).append((x,n))
 for y,row in byrow.items():
  row.sort()
  for (a,n),(b,m) in zip(row,row[1:]):
   if b-a<2.16-1e-6:bad.append((n,'body_overlap',m))
 maxhop=reach(poses,pins)
 rep=dict(schema='hbm.spb_congestion_variant.v1',tag=tag,changed_FF=len(changed),changed_PHY_pins=sum(pins[n]!=pp[n] for n in pins),FF_count=len(poses),origin_anchor_max_hop_um=maxhop,body_PG_site_failures=bad,qualification='GEOMETRY_PREP_ONLY: exact OpenROAD D/Q pin-coordinate reach and G2 pending',source_change=0,added_cycles=0)
 (td/'macros.lef').write_text(newlef);(td/'probe.tcl').write_text(new);(td/'positions.json').write_text(json.dumps(poses));(td/'phy_pins.json').write_text(json.dumps(pins));(td/'review_input.json').write_text(json.dumps(rep,indent=1));print(tag,json.dumps(rep))
poses=copy.deepcopy(ff);pins=copy.deepcopy(pp)
def move_pin(m):
 name=m[1];kind=name[:2]
 if kind not in ('rx','tx'):return m[0]
 b=int(name.split('[')[1][:-1]);x=(4.0 if kind=='rx' else 497.696)+.192*b
 body=m[2];a=re.search(r'RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)',body);x0,y0,x1,y1=map(float,a.groups());w=x1-x0
 body=body[:a.start()]+f'RECT {x-w/2:.6f} {y0:.6f} {x+w/2:.6f} {y1:.6f}'+body[a.end():]
 pins[name]=(x+103.68,(y0+y1)/2)
 return ' PIN '+name+'\n'+body+' END '+name
newphy=re.sub(pat,move_pin,phy,flags=re.S);newlef=newphy+lef[len(phy):]
writevariant('A_pin_bundles',poses,pins,newlef)
poses=copy.deepcopy(ff)
for b in range(512):poses[f'tx_s3_b{b}']=(round(768.096+2.268*(b%2),6),round(641.52+.27*(b//2),6))
for b in range(514):poses[f'rx_s0_b{b}']=(round(4.536+2.268*(b%4),6),round(641.52+.27*(128-b//4),6))
writevariant('B_tall_banks',poses,pp,lef)
