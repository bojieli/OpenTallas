#!/usr/bin/env python3
"""Complete actual ODB LEF-pin reach census, including native boundary edges.
No absent boundary is assigned zero length. This is geometry, not timing.
"""
import argparse,collections,json
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--mapped',required=True);p.add_argument('--inventory',required=True);p.add_argument('--bindings',required=True);p.add_argument('--out',required=True);a=p.parse_args();d=odb.dbDatabase.create();odb.read_db(d,a.source);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron();mapped=json.load(open(a.mapped))['modules']['ot_die_start_stages'];inv=json.load(open(a.inventory));bd=json.load(open(a.bindings))['ports'];cells={c['inst']:c for c in inv['cells']};driver={};native={};arcs=[];bad=[];active=set();cache={}
def rect(i,pin):
 it=i.findITerm(pin);assert it,(i.getName(),pin);sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(i.getOrient())];x,y=i.getOrigin();rr=[]
 for mp in it.getMTerm().getMPins():
  for z in mp.getGeometry():
   if z.getTechLayer():
    xx=sorted([x+sx*z.xMin(),x+sx*z.xMax()]);yy=sorted([y+sy*z.yMin(),y+sy*z.yMax()]);rr.append([xx[0],yy[0],xx[1],yy[1]])
 assert rr,(i.getName(),pin);return[min(z[0] for z in rr),min(z[1] for z in rr),max(z[2] for z in rr),max(z[3] for z in rr)]
def dist(r,s):return max(abs(x-u)+abs(y-v) for x in(r[0],r[2]) for y in(r[1],r[3]) for u in(s[0],s[2]) for v in(s[1],s[3]))/D
for name,q in mapped['ports'].items():
 if bd[name]['role']=='clock':continue
 ee=bd[name].get('native_endpoints',[]);assert len(ee)==1,name;e=ee[0];i=b.findInst(e['inst']);assert i;it=i.findITerm(e['pin']);assert it.getNet().getName()==bd[name]['net'];native[name]=dict(inst=e['inst'],pin=e['pin'],rect=rect(i,e['pin']),direction=q['direction'],bit=q['bits'][0])
for n,c in cells.items():
 for pin,bits in c['connections'].items():
  if c['directions'][pin]=='output':
   for bit in bits:assert bit not in driver;driver[bit]=(n,pin)
for name,e in native.items():
 if e['direction']=='input':assert e['bit'] not in driver;driver[e['bit']]=('NATIVE',name)
def source(bit):
 if bit in cache:return cache[bit]
 assert bit not in active,('loop',bit);assert bit in driver,('unbound',bit);n,pin=driver[bit]
 if n=='NATIVE' or cells[n]['sequential']:return {(n,pin)}
 active.add(bit);s=set()
 for p,bb in cells[n]['connections'].items():
  if cells[n]['directions'][p]=='input':
   for bit2 in bb:s.update(source(bit2))
 active.remove(bit);cache[bit]=s;return s
def endbox(n,pin):
 if n=='NATIVE':return native[pin]['rect']
 i=b.findInst('start_provider/'+n);assert i,n;return rect(i,pin)
def arc(s,t,kind):
 n,pin=s;nn,pp=t;r=endbox(n,pin);q=endbox(nn,pp);h=dist(r,q);v=dict(src=n+'/'+pin,dst=nn+'/'+pp,um=h,kind=kind);arcs.append(v)
 if h>405+1e-9:bad.append(v)
for n,c in cells.items():
 if c['sequential']:
  for pin,bb in c['connections'].items():
   if c['directions'][pin]=='input' and pin!='CLK':
    for bit in bb:
     for s in source(bit):arc(s,(n,pin),'native_input' if s[0]=='NATIVE' else'internal')
for name,e in native.items():
 if e['direction']=='output':
  for s in source(e['bit']):arc(s,('NATIVE',name),'native_output')
arcs.sort(key=lambda q:-q['um']);report=dict(verdict='PASS' if not bad else'FAIL',source=a.source,registered_arcs=len(arcs),internal=sum(q['kind']=='internal' for q in arcs),native_inputs=sum(q['kind']=='native_input' for q in arcs),native_outputs=sum(q['kind']=='native_output' for q in arcs),native_ports=len(native),max_um=arcs[0]['um'],over405=len(bad),bad=bad,scope='Complete actual ODB LEF-pin geometry only, no routed timing/clock/PG claims');Path(a.out).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1));raise SystemExit(bool(bad))
