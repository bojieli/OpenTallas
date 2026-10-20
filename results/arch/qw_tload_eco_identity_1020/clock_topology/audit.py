from pathlib import Path
import sys,json,hashlib,odb
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
f=root/'eco_closed_0444/6_final.odb';before=hashlib.sha256(f.read_bytes()).hexdigest()
roles=json.loads((root/'eco_audit/6_final_eco/summary.json').read_text())['master_roles']
db=odb.dbDatabase.create();odb.read_db(db,str(f));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def loc(p):
 z=p.getBBox();return [(z.xMin()+z.xMax())/2/u,(z.yMin()+z.yMax())/2/u]
def chain(pin):
 ret=[];seen=set();err=[]
 while True:
  n=pin.getNet()
  if n is None:err.append('unconnected '+pin.getInst().getName()+'/'+pin.getMTerm().getName());break
  if n.getId()in seen:err.append('loop '+n.getName());break
  seen.add(n.getId());drivers=[x for x in n.getITerms()if str(x.getIoType())=='OUTPUT'];ports=[p.getName()for p in n.getBTerms()if str(p.getIoType())=='INPUT']
  if ports:
   ret.append({'root_input_ports':ports,'net':n.getName(),'sink_pin':pin.getInst().getName()+'/'+pin.getMTerm().getName(),'sink_xy_um':loc(pin)});break
  if len(drivers)!=1:err.append('driver_count '+str(len(drivers))+' '+n.getName());break
  d=drivers[0];i=d.getInst();m=i.getMaster().getName();r=roles.get(m,{})
  ret.append({'driver':i.getName()+'/'+d.getMTerm().getName(),'master':m,'function':r.get('pins',{}).get(d.getMTerm().getName(),{}).get('function'),'driver_xy_um':loc(d),'sink_xy_um':loc(pin),'endpoint_span_um':sum(abs(x-y)for x,y in zip(loc(d),loc(pin))),'sink_pin':pin.getInst().getName()+'/'+pin.getMTerm().getName(),'net':n.getName(),'physical_input_loads':sum(str(x.getIoType())=='INPUT'for x in n.getITerms())})
  if not r.get('unary'):err.append('nontransparent clock producer '+m);break
  ins=[p for p in i.getITerms()if str(p.getIoType())=='INPUT'and str(p.getSigType())not in ['POWER','GROUND']]
  if len(ins)!=1:err.append('input_count '+m);break
  pin=ins[0]
 return {'edges':ret,'errors':err,'depth':len(ret)-1,'endpoint_span_sum_um':sum(x.get('endpoint_span_um',0)for x in ret)}
r={}
for name in ['u_ot_pr_core.u_ld.m0','u_ot_pr_core.u_ld.m1','u_ot_pr_core.u_ld.m2','u_ot_pr_core.u_ld.m3']:
 i=b.findInst(name);assert i,name;pin=i.findITerm('clk');assert pin,name;r[name]=chain(pin)
a={'scope':'Readonly actual immutable CLOSED ECO ODB four-ROM clock paths. Every traversed producer classified from existing pinned Liberty Boolean unary function, no name filter. Endpoint spans are physical pin-centre Manhattan distances, not routed wire length or delay. No constraints/database writes.','odb_sha256':before,'after_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'paths':r}
(out/'clock_topology.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({k:{'depth':v['depth'],'endpoint_span_sum_um':v['endpoint_span_sum_um'],'errors':v['errors']}for k,v in r.items()},indent=2));assert a['after_sha256']==before
