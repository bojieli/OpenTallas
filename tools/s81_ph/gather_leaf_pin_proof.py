#!/usr/bin/env python3
"""Bind preserved S8 CTS pin rectangles to the v18 die assignment and real RTL bits."""
import gzip,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'results/rtl/s81_ph_20261006/gather/pins_v18'
def write(n,x):
 data=(json.dumps(x,indent=1)+'\n').encode()
 if n.endswith('.gz'): (P/n).write_bytes(gzip.compress(data,mtime=0))
 else:(P/n).write_bytes(data)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
parent=json.loads((P/'parent_assignment.json').read_text())
w,h=parent['outline_um']
def pp(port,bit):
 face,layer,t,_=parent['ports'][port]['per_bit'][bit]
 return [layer,0 if face=='W' else w if face=='E' else t,0 if face=='S' else h if face=='N' else t]
masters={};fail=[]
for kind in ('rw','re'):
 dump=json.loads((P/f'dsfd_gth_{kind}.gate_dump.json').read_text()); pins={}
 for name,net,typ,direction,rects in dump['bterms']:
  if typ in ('POWER','GROUND'):continue
  assert len(rects)==1
  layer,rect=rects[0]; x=(rect[0]+rect[2])/2;y=(rect[1]+rect[3])/2
  face='W' if rect[0]==0 else 'E' if rect[2]==190.08 else 'S' if rect[1]==0 else 'N' if rect[3]==164.16 else '?'
  pins[name]={'point':[layer,round(x,6),round(y,6)],'face':face,'rect':rect,'direction':direction}
  coord=y if face in ('W','E') else x
  if abs((coord-.012)/.048-round((coord-.012)/.048))>1e-5:fail.append(['pin_lattice',kind,name,coord])
  for item in dump['pdn_edge']:
   if len(item)<4 or item[1]!=layer:continue
   pg=item[3]
   if max(rect[0],pg[0])<min(rect[2],pg[2]) and max(rect[1],pg[1])<min(rect[3],pg[3]):fail.append(['PG_overlap',kind,name,item])
 expected={'ck':1,'rs':1,'rso':1,'li':1104,'lo':828,'ci':636,'co':848,'fi':2,'fo':2}
 names={name if count==1 else f'{name}[{i}]' for name,count in expected.items() for i in range(count)}
 assert set(pins)==names,(kind,set(pins)^names)
 masters[kind]=pins
 write(f'dsfd_gth_{kind}.pins.json',{'schema':'opentallas.s81.gather_leaf_pins.v1','status':'PROPOSED_FOR_DIE_ACCEPTANCE','outline_um':[190.08,164.16],'orientation':'R0','source_iop_sha256':sha(P/f'dsfd_gth_{kind}.cts_iop.tcl'),'source_odb_dump_sha256':sha(P/f'dsfd_gth_{kind}.gate_dump.json'),'pins':pins,'pg_layer':'M5','parent_straps':'M6','signal_layer_cap':'M5'})
rtl=ROOT/'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv'
lanes={int(a)//69:(b,int(c)) for a,b,c in re.findall(r'assign ln\[(\d+) \+: 69\] = (r[WE]\d)\[(\d+) \+: 69\]',rtl.read_text())}
assert len(lanes)==128
instances=[];links=[]
def ep(g,k,pin):
 kind='rw' if g<4 else 're';x=12.96+216*g;y=61.632+184.32*k
 layer,px,py=masters[kind][pin]['point']
 return {'instance':f'g_c[{g}].g_k[{k}].g_{"w" if g<4 else "e"}.u_l','port':pin,'point':[layer,round(x+px,6),round(y+py,6)]}
def link(kind,a,b):
 A=a['point'];B=b['point'];links.append({'kind':kind,'a':a,'b':b,'manhattan_um':round(abs(A[1]-B[1])+abs(A[2]-B[2]),6)})
def boundary(p,b):return {'instance':'PARENT','port':f'{p}[{b}]','point':pp(p,b)}
for g in range(8):
 for k in range(4):
  x=12.96+216*g;y=61.632+184.32*k
  assert abs(x/.432-round(x/.432))<1e-5
  assert abs(x/.288-round(x/.288))<1e-5 and abs(y/.576-round(y/.576))<1e-5
  assert x+190.08<=w and y+164.16<=h
  instances.append({'g':g,'k':k,'origin_um':[x,y],'orientation':'R0','master':f'dsfd_gth_{"rw" if g<4 else "re"}','clock':f'ck_l[{4*g+k}]','clock_pin':ep(g,k,'ck'),'reset_pin':ep(g,k,'rs'),'status_pins':[ep(g,k,'fo[0]'),ep(g,k,'fo[1]')]})
  link('clock_entry',boundary('ck_l',4*g+k),ep(g,k,'ck'))
  if g in (0,7):
   groups=[0,16,32,48] if g==0 else [112,96,80,64]
   for q,base in enumerate(groups):
    for s in range(4):
     p,start=lanes[base+4*k+s]
     for bit in range(69):link('outer_lane',boundary(p,start+bit),ep(g,k,f'li[{276*q+69*s+bit}]'))
  elif g in (1,2,3,4,5,6):
   prev=g-1 if g<4 else g+1
   for bit in range(828):link('lane_seam',ep(prev,k,f'lo[{bit}]'),ep(g,k,f'li[{bit}]'))
  if k<3:
   for bit in range(636):link('chain_seam',ep(g,k+1,f'co[{bit}]'),ep(g,k,f'ci[{bit}]'))
   for bit in range(2):link('status_seam',ep(g,k+1,f'fo[{bit}]'),ep(g,k,f'fi[{bit}]'))
   link('reset_seam',ep(g,k+1,'rso'),ep(g,k,'rs'))
  else:pass # ci/fi tied zero; rs is driven by rc via the separately owned control strip
  if k==0:
   for bit in range(848):link('capture_boundary',ep(g,k,f'co[{bit}]'),boundary('t_capture',848*g+bit))
# Last-column lo is unused; internal li[1103:828] are tied zero. Top ci/fi are zero.
bindings=[]
for g in range(8):
 for k in range(4):
  kind='rw' if g<4 else 're'
  for pin in masters[kind]:
   base=pin.split('[')[0]; bit=int(pin.split('[')[1][:-1]) if '[' in pin else 0
   usage='linked'
   if base=='li' and g not in (0,7) and bit>=828:usage='constant_zero'
   if base in ('ci','fi') and k==3:usage='constant_zero'
   if base=='lo' and g in (3,4):usage='unused_output'
   if base=='co' and k>0 and bit>=636:usage='unused_output'
   if base=='rso' and k==0:usage='unused_output'
   if base=='rs' and k==3:usage=f'control_strip_rc[{g}]'
   if base=='fo' and k==0:usage=f'control_strip_cs[{2*g+bit}]'
   bindings.append({**ep(g,k,pin),'usage':usage})
assert len(bindings)==32*3423
write('whole_leaf_port_bindings.json.gz',bindings)
write('leaf_instances.json',instances);write('bit_links.json.gz',links)
summary={kind:{'count':sum(x['kind']==kind for x in links),'max_manhattan_um':max(x['manhattan_um'] for x in links if x['kind']==kind)} for kind in sorted({x['kind'] for x in links})}
write('proof.json',{'schema':'opentallas.s81.gather_leaf_pin_proof.v1','status':'PROPOSED_FOR_DIE_ACCEPTANCE' if not fail else 'FAIL','parent_assignment_sha256':sha(P/'parent_assignment.json'),'rtl_sha256':sha(rtl),'leaf_pins':{'rw':len(masters['rw']),'re':len(masters['re'])},'instances':32,'orientation':'R0','origin_lattice_um':{'x':.432,'y':.576},'pin_lattice_pitch_um':.048,'pin_lattice_offset_um':.012,'pg_rectangles_source':'preserved actual IOP ODB dump; route/LEF PG access remains required','failures':fail,'links':summary,'owed':['actual routed slew/clock/internal timing/TT+FF+DRC and child_lint','timing-aware per-bit hop reach from actual routed views; capture max100.458um exceeds100um pin-stage heuristic; actualpair/reach/hold still required','control strip rc/cs/tst/f_vm/f_cd/tc binding','f_vm[511:160] remain declared but unused in current RTL; parent bypass treatment belongs to die/control owner','clock phi-R_i compensation from actual routed insertion.json','native81/optional120 whole-operation PFABI binding']})
print(json.dumps({'failures':fail,'links':summary},indent=1))
