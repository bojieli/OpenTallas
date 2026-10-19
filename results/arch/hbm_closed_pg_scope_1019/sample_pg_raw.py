import gzip,json,pathlib,re,os
import openroad as ord
import odb
p=pathlib.Path('/proof'); txt=(p/'report.tcldict').read_text()
samples={}
for m in re.finditer(r'\{instance (\S+) master (\S+) pin (\S+) role (POWER|GROUND) actual_net \{\}',txt):
 samples.setdefault(m[2],m[1])
del txt
tech=ord.Tech(); design=ord.Design(tech);design.readDb('/input.odb');b=design.getBlock()
rail={}
for n in b.getNets():
 if str(n.getSigType()) not in ('POWER','GROUND'):continue
 for sw in n.getSWires():
  for s in sw.getWires():
   if s.isVia() or s.getTechLayer().getName()!='M1':continue
   rail.setdefault(n.getName(),[]).append((s.xMin(),s.yMin(),s.xMax(),s.yMax()))
rows=list(b.getRows());out=[]
for master,name in samples.items():
 i=b.findInst(name);ox,oy=i.getOrigin();orient=str(i.getOrient()); bb=i.getBBox();pins=[]
 assert orient in ('R0','MX','MY','R180'),orient
 rowhits=[r.getName() for r in rows if r.getBBox().yMin()<=bb.yMin() and r.getBBox().yMax()>=bb.yMax() and r.getBBox().xMin()<=bb.xMin() and r.getBBox().xMax()>=bb.xMax()]
 for t in i.getITerms():
  mt=t.getMTerm();role=str(mt.getSigType())
  if role not in ('POWER','GROUND'):continue
  expected='VDD' if role=='POWER' else 'VSS';boxes=[]
  for mp in mt.getMPins():
   for z in mp.getGeometry():
    if z.isVia():continue
    xs=[ox+(-v if orient in ('MY','R180') else v) for v in (z.xMin(),z.xMax())];ys=[oy+(-v if orient in ('MX','R180') else v) for v in (z.yMin(),z.yMax())]
    q=(min(xs),min(ys),max(xs),max(ys));layer=z.getTechLayer().getName()
    hits=[r for r in rail.get(expected,[]) if layer=='M1' and min(r[2],q[2])>max(r[0],q[0]) and min(r[3],q[3])>max(r[1],q[1])]
    boxes.append({'layer':layer,'box':q,'same_role_M1_overlap':hits[:3],'overlap_count':len(hits)})
  pins.append({'pin':mt.getName(),'role':role,'actual_net':t.getNet().getName() if t.getNet() else None,'expected_net_from_native_rules':expected,'boxes':boxes})
 out.append({'master':master,'instance':name,'origin':[ox,oy],'orientation':orient,'bbox':[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()],'covering_rows':rowhits,'native_pins':pins})
(p/'sample_pg.json').write_text(json.dumps({'dbu_per_um':b.getDbUnitsPerMicron(),'scope':'one actual unbound representative per failed master; no conductor extraction','samples':out},indent=2)+'\n')
print('PG_SAMPLES',len(out))
