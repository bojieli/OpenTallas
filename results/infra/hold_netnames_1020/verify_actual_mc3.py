import odb,hashlib,json,collections
from pathlib import Path
p=Path('/w')
def canonical(file,properties=False):
 db=odb.dbDatabase.create();odb.read_db(db,str(file));b=db.getChip().getBlock()
 ports=sorted((x.getName(),str(x.getIoType())) for x in b.getBTerms())
 cells={i.getName():i.getMaster().getName() for i in b.getInsts()}
 edges=[];prop={};empty=0
 for n in b.getNets():
  terms=sorted([('B',t.getName()) for t in n.getBTerms()]+[('I',t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()])
  if not terms:empty+=1;continue
  edges.append(terms)
  if properties:prop[json.dumps(terms)]=dict(sigtype=str(n.getSigType()),special=n.isSpecial(),dont_touch=n.isDoNotTouch())
 rec=dict(ports=ports,cells=cells,edges=sorted(edges))
 if properties:
  rec['net_properties']=prop
  rec['cell_properties']={i.getName():dict(orient=str(i.getOrient()),status=str(i.getPlacementStatus()),location=list(i.getLocation()),dont_touch=i.isDoNotTouch()) for i in b.getInsts()}
 return rec
old=canonical(p/'preflight/iohold.odb',True);new=canonical(p/'preflight_fixed/iohold.odb',True)
fixed=canonical(p/'preflight_fixed/iohold.odb');rt=canonical(p/'preflight_fixed/roundtrip.odb')
report=dict(scope='Exact native names, complete BTerm/ITerm hyperedges, masters, properties; no behavioral cell model.',old_fixed_identical_except_netnames=old==new,fixed_roundtrip_exact_topology=fixed==rt,ports=len(fixed['ports']),cells=len(fixed['cells']),native_edges=len(fixed['edges']))
if fixed!=rt:
 for k in fixed:
  if fixed[k]!=rt[k]:
   if isinstance(fixed[k],dict):report[k+'_missing']=sorted(set(fixed[k])-set(rt[k]))[:8];report[k+'_extra']=sorted(set(rt[k])-set(fixed[k]))[:8]
   elif isinstance(fixed[k],list):
    aa={json.dumps(x) for x in fixed[k]};bb={json.dumps(x) for x in rt[k]};report[k+'_missing']=sorted(aa-bb)[:8];report[k+'_extra']=sorted(bb-aa)[:8]
report['old_odb_sha256']=hashlib.sha256((p/'preflight/iohold.odb').read_bytes()).hexdigest();report['fixed_odb_sha256']=hashlib.sha256((p/'preflight_fixed/iohold.odb').read_bytes()).hexdigest()
(p/'preflight_fixed/graph_comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert old==new;assert fixed==rt
