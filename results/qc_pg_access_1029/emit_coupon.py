#!/usr/bin/env python3
"""Emit a scoped physical ODB coupon from a reviewed PG construction plan."""
import json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--grid',required=True);p.add_argument('--odb',required=True);p.add_argument('--out',required=True);a=p.parse_args();base=Path(a.plan);o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
plan=json.load(open(base/'access_plan.json'));rects=json.load(open(base/'reserved_access.json'));pg=json.load(open(a.grid));D=plan['dbu'];assert plan['paths'] and not plan['failed'],'Cannot materialize incomplete probe'
# Actual canonical grid subset, including its real M8/M9 cross-layer connection.
selected=set();cross=[]
for q in plan['paths']:
 n=q['net'];x,y=q['m8'][2:];vs=[tuple(r) for r in pg if r[0]==n and r[1]=='M9' and round(r[2]*D)<=x<=round(r[4]*D) and round(r[3]*D)<=y<=round(r[5]*D)]
 assert vs
 v=vs[0];selected.add(v);hs=[tuple(r) for r in pg if r[0]==n and r[1]=='M8' and r[2]<=x/D<=r[4]];h=min(hs,key=lambda r:abs((r[3]+r[5])/2-y/D));selected.add(h)
 cross.append([n,'VIA89',round((v[2]+v[4])/2*D),round((h[3]+h[5])/2*D)])
lines=['read_db {'+a.odb+'}','set blk [ord::get_db_block]','set tech [[ord::get_db] getTech]']
for n in ['VDD','VSS']:
 lines += ['set pn [$blk findNet '+n+']','if {$pn == "NULL"} {set pn [odb::dbNet_create $blk '+n+']}', '$pn setSigType '+('POWER' if n=='VDD' else 'GROUND'),'$pn setSpecial','set sw_'+n+' [odb::dbSWire_create $pn FIXED]']
for n,ly,*r in rects+sorted(selected):
 xy=[round(v*D) for v in r];lines.append('odb::dbSBox_create $sw_'+n+' [$tech findLayer '+ly+'] '+' '.join(map(str,xy))+' STRIPE')
for n,vn,x,y in plan['vias_dbu']+cross:lines.append(f'odb::dbSBox_create $sw_{n} [$tech findVia {vn}] {x} {y} STRIPE')
for q in plan['paths']:
 for inst in q['members']:lines.append('[[$blk findInst {'+inst+'}] findITerm '+q['net']+'] connect [$blk findNet '+q['net']+']')
lines+=['write_db {'+str(o/'power_coupon.odb')+'}']
(o/'coupon.tcl').write_text('\n'.join(lines)+'\n');json.dump(dict(contacts=sum(len(q['members']) for q in plan['paths']),groups=len(plan['paths']),access_rectangles=len(rects),access_vias=len(plan['vias_dbu']),grid_rectangles=len(selected),grid_vias=len(cross),scope='Scoped coupon only; remaining contacts unconnected'),open(o/'coupon_scope.json','w'),indent=2)
