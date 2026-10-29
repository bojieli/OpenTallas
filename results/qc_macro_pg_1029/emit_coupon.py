#!/usr/bin/env python3
"""Materialize only reviewed native-contact coupon, with real canonical stripes."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--grid',required=True);p.add_argument('--odb',required=True);p.add_argument('--out',required=True);a=p.parse_args();x=json.load(open(a.plan));assert not x['failed'];out=Path(a.out);out.mkdir(parents=True,exist_ok=True);D=x['dbu'];grid=json.load(open(a.grid));selected=set();cross=set()
for c in x['contacts']:
 n=c['net'];h=tuple(c['grid_rect_dbu']);selected.add((n,'M8',*h));xx,yy=c['xy_dbu'];v=min((r for nn,ly,*r in grid if nn==n and ly=='M9'),key=lambda r:abs((r[0]+r[2])*D/2-xx));v=tuple(round(q*D) for q in v);selected.add((n,'M9',*v));vx=(v[0]+v[2])//2;vy=(h[1]+h[3])//2
 # VIA89's actual square40nm pads are enclosed by canonical stripes.
 assert h[0]<=vx-20 and vx+20<=h[2] and v[1]<=vy-20 and vy+20<=v[3]
 cross.add((n,'VIA89',vx,vy))
lines=['read_db {'+a.odb+'}','set blk [ord::get_db_block]','set tech [[ord::get_db] getTech]']
for n,st in [('VDD','POWER'),('VSS','GROUND')]:lines+=['set pn [$blk findNet '+n+']','if {$pn == "NULL"} {set pn [odb::dbNet_create $blk '+n+']}', '$pn setSigType '+st,'$pn setSpecial','set sw_'+n+' [odb::dbSWire_create $pn FIXED]']
for n,ly,*r in sorted(selected):lines.append('odb::dbSBox_create $sw_'+n+' [$tech findLayer '+ly+'] '+' '.join(map(str,r))+' STRIPE')
for n,vn,xx,yy in sorted(cross):lines.append(f'odb::dbSBox_create $sw_{n} [$tech findVia {vn}] {xx} {yy} STRIPE')
for c in x['contacts']:
 n=c['net'];xx,yy=c['xy_dbu'];lines.append(f'odb::dbSBox_create $sw_{n} [$tech findVia VIA78] {xx} {yy} STRIPE');lines.append('[[$blk findInst {'+c['inst']+'}] findITerm {'+c['pin']+'}] connect [$blk findNet '+n+']')
lines+=['write_db {'+str(out/'coupon.odb')+'}'];(out/'coupon.tcl').write_text('\n'.join(lines)+'\n');(out/'scope.json').write_text(json.dumps(dict(terms=len(x['contacts']),macro_contacts=len(x['contacts']),canonical_grid_rectangles=len(selected),canonical_via89=len(cross),new_via78=len(x['contacts']),scope='Connectivity coupon only; not IR, die PG or per-fragment closure'),indent=2)+'\n')
