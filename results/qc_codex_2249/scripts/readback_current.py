#!/usr/bin/env python3
"""Read complete imported cell bodies, PG contacts and registered reach from actual ODB."""
import argparse,json,collections,hashlib
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--cells',required=True);p.add_argument('--out',required=True);a=p.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron();inv=json.load(open(a.cells));provider={q['inst']:q for q in inv['cells']};seq={n for n,q in provider.items() if q['sequential']}
def rect(i,z):
 sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(i.getOrient())];x,y=i.getOrigin();xx=sorted([x+sx*z.xMin(),x+sx*z.xMax()]);yy=sorted([y+sy*z.yMin(),y+sy*z.yMax()]);return [xx[0],yy[0],xx[1],yy[1]]
def box(it):
 rr=[rect(it.getInst(),z) for p in it.getMTerm().getMPins() for z in p.getGeometry() if z.getTechLayer() and z.getTechLayer().getRoutingLevel()>0];assert rr;return [min(q[0] for q in rr),min(q[1] for q in rr),max(q[2] for q in rr),max(q[3] for q in rr)]
def dist(r,s):return max(abs(x-u)+abs(y-v) for x in [r[0],r[2]] for y in [r[1],r[3]] for u in [s[0],s[2]] for v in [s[1],s[3]])/D
terms=[];nativeclk=[];actual=[]
for i in b.getInsts():
 n=i.getName();clock=i.getMaster().getName().startswith('CKINVDCx16_')
 if not clock and n not in provider:continue
 if n in provider:
  q=provider[n];bb=i.getBBox();assert q['bbox_dbu']==[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()];actual.append(n)
 for it in i.getITerms():
  if str(it.getMTerm().getSigType()) not in ['POWER','GROUND']:continue
  ss=[[z.getTechLayer().getName(),*rect(i,z)] for mp in it.getMTerm().getMPins() for z in mp.getGeometry() if z.getTechLayer() and z.getTechLayer().getRoutingLevel()>0]
  terms.append(dict(inst=n,pin=it.getMTerm().getName(),master=i.getMaster().getName(),orient=str(i.getOrient()),shapes_dbu=ss,connected_net=it.getNet().getName() if it.getNet() else None))
assert len(actual)==len(provider) and len(terms)==2*(len(provider)+sum(i.getMaster().getName().startswith("CKINVDCx16_") and i.getName() not in provider for i in b.getInsts())),(len(actual),len(terms))
json.dump(dict(dbu=D,terms=terms),open(o/'power_terms.json','w'),separators=(',',':'))
cache={};active=set()
def sources(net):
 name=net.getName()
 if name in cache:return cache[name]
 assert name not in active,'combinational loop '+name
 active.add(name);out=[]
 for it in net.getITerms():
  if str(it.getMTerm().getIoType())!='OUTPUT':continue
  i=it.getInst();n=i.getName()
  if n in seq or n not in provider:out.append((n,it.getMTerm().getName(),box(it)))
  else:
   for ip in i.getITerms():
    if str(ip.getMTerm().getIoType())=='INPUT' and str(ip.getMTerm().getSigType()) not in ['POWER','GROUND'] and ip.getNet():out.extend(sources(ip.getNet()))
 for bt in net.getBTerms():
  if str(bt.getIoType())=='INPUT':
   rr=[[z.xMin(),z.yMin(),z.xMax(),z.yMax()] for bp in bt.getBPins() for z in bp.getBoxes()];assert rr;out.append(('BTERM',bt.getName(),[min(r[0] for r in rr),min(r[1] for r in rr),max(r[2] for r in rr),max(r[3] for r in rr)]))
 active.remove(name);out=list({(n,p,tuple(bb)):(n,p,bb) for n,p,bb in out}.values());cache[name]=out;return out
arcs=[];undriven=[]
for n in sorted(seq):
 i=b.findInst(n)
 for it in i.getITerms():
  if str(it.getMTerm().getIoType())!='INPUT' or str(it.getMTerm().getSigType()) in ['POWER','GROUND','CLOCK'] or it.getMTerm().getName()=='CLK':continue
  net=it.getNet();ss=sources(net) if net else []
  if not ss:undriven.append([n,it.getMTerm().getName()]);continue
  for sn,sp,sb in ss:arcs.append(dict(src=sn,src_pin=sp,dst=n,dst_pin=it.getMTerm().getName(),um=dist(sb,box(it)),scope='provider' if sn in provider else 'native_boundary'))
# Include provider outputs captured at native partition START input pins.
for net in b.getNets():
 drivers=[it for it in net.getITerms() if it.getInst().getName() in seq and str(it.getMTerm().getIoType())=='OUTPUT']
 if not drivers:continue
 for it in net.getITerms():
  if it.getInst().getName() in provider or str(it.getMTerm().getIoType())!='INPUT':continue
  for dr in drivers:arcs.append(dict(src=dr.getInst().getName(),src_pin=dr.getMTerm().getName(),dst=it.getInst().getName(),dst_pin=it.getMTerm().getName(),um=dist(box(dr),box(it)),scope='native_capture_boundary'))
arcs.sort(key=lambda q:-q['um']);over=[q for q in arcs if q['um']>405+1e-9];summary=dict(source_odb_sha256=hashlib.sha256(Path(a.odb).read_bytes()).hexdigest(),actual_provider_cells=len(actual),power_contacts=len(terms),registered_arcs=len(arcs),max_um=arcs[0]['um'],over405=len(over),undriven_inputs=len(undriven),boundary_arcs=sum(q['scope']!='provider' for q in arcs),verdict='ACTUAL_REACH_PASS' if not over and not undriven else 'ACTUAL_REACH_FAIL')
json.dump(dict(summary=summary,arcs=arcs,undriven=undriven),open(o/'reach.json','w'),separators=(',',':'));json.dump(summary,open(o/'summary.json','w'),indent=2);print(json.dumps(summary,indent=2),flush=True)
