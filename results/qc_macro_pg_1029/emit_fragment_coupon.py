#!/usr/bin/env python3
"""Emit reviewed short-fragment M8-to-M9 bridges on a COPY of the term coupon."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--grid',required=True);p.add_argument('--odb',required=True);p.add_argument('--out',required=True);a=p.parse_args();p0=json.load(open(a.plan));assert not p0['failed'];D=p0['dbu'];pg=json.load(open(a.grid));o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
# Actual same-net canonical bottom rows serve as coupon connectivity anchors.
rows={n:min((tuple(round(v*D) for v in r) for nn,ly,*r in pg if nn==n and ly=='M8'),key=lambda r:r[1]) for n in ['VDD','VSS']};selected={(n,'M8',*r) for n,r in rows.items()};via89=set();contacts=[];newwires=[]
for q in p0['paths']:
 n=q['net'];r=q['m9_grid_dbu'];selected.add((n,'M9',*r));h=rows[n];via89.add((n,(r[0]+r[2])//2,(h[1]+h[3])//2));x,y=q['via78'];xx,yy=q['via89'];assert y==yy
 contacts.append(dict(inst=q['inst'],pin=q['pin'],shape=q['shape'],net=n,xy_dbu=[x,y],native_pin_dbu=q['native_pin_dbu'],metal_dbu={'M7':[x-16,y-27,x+16,y+27],'M8':[x-27,y-20,x+27,y+20]}));newwires.append((n,'M8',*q['m8_dbu']))
lines=['read_db {'+a.odb+'}','set blk [ord::get_db_block]','set tech [[ord::get_db] getTech]']
for n in ['VDD','VSS']:lines+=['set pn [$blk findNet '+n+']','if {$pn == "NULL"} {error {missing actual source supply}}','set sw_'+n+' [odb::dbSWire_create $pn FIXED]']
for n,ly,*r in sorted(selected)+newwires:lines.append('odb::dbSBox_create $sw_'+n+' [$tech findLayer '+ly+'] '+' '.join(map(str,r))+' STRIPE')
for n,x,y in sorted(via89):lines.append(f'odb::dbSBox_create $sw_{n} [$tech findVia VIA89] {x} {y} STRIPE')
for q in p0['paths']:
 n=q['net'];x,y=q['via78'];xx,yy=q['via89'];lines+=[f'odb::dbSBox_create $sw_{n} [$tech findVia VIA78] {x} {y} STRIPE',f'odb::dbSBox_create $sw_{n} [$tech findVia VIA89] {xx} {yy} STRIPE']
lines+=['write_db {'+str(o/'coupon.odb')+'}'];(o/'coupon.tcl').write_text('\n'.join(lines)+'\n');json.dump(dict(source=p0['source'],dbu=D,contacts=contacts,failed=[],scope='Short native PG fragment access coupon only; no IR or distributed PG closure'),open(o/'readback_plan.json','w'),separators=(',',':'));(o/'scope.json').write_text(json.dumps(dict(native_fragments=len(contacts),new_M8_bridges=len(newwires),new_VIA78=len(contacts),new_VIA89=len(contacts)+len(via89),scope='Native short-fragment access coupon only, no IR/distributedPG closure'),indent=2)+'\n')
