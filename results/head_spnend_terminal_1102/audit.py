import odb,json
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,'/input/6_final.odb');b=db.getChip().getBlock()
c=json.load(open('/work/landing_contract.json'));decl={p['name']:p['source_clock_port']for p in c['pins']if p.get('kind')=='clock'and p.get('dir')=='out'}
def net(n):
 return None if n is None else dict(name=n.getName(),sigtype=str(n.getSigType()),special=n.isSpecial(),bterms=sorted(x.getName()for x in n.getBTerms()),iterm_count=len(n.getITerms()))
def trace(n):
 seen=set();steps=[]
 while n is not None and n.getId() not in seen:
  seen.add(n.getId());roots=[p.getName()for p in n.getBTerms()if str(p.getIoType())=='INPUT']
  if roots:return dict(roots=sorted(roots),steps=steps,status='INPUT_ROOT')
  ds=[p for p in n.getITerms()if p.isOutputSignal()]
  if len(ds)!=1:return dict(status='AMBIGUOUS_OR_UNDRIVEN',roots=[],steps=steps)
  i=ds[0].getInst();ins=[p for p in i.getITerms()if p.isInputSignal()]
  steps.append(dict(instance=i.getName(),master=i.getMaster().getName(),output=ds[0].getMTerm().getName(),net=n.getName()))
  if len(ins)!=1:return dict(status='NON_UNARY_DRIVER',roots=[],steps=steps)
  n=ins[0].getNet()
 return dict(status='NULL_OR_CYCLE',roots=[],steps=steps)
rows=[]
for port,source in decl.items():
 name='cland_fwd_'+port;i=b.findInst(name);assert i is not None,name
 A=i.findITerm('A').getNet();Y=i.findITerm('Y').getNet();src=b.findBTerm(source)
 rows.append(dict(port=port,instance=name,master=i.getMaster().getName(),location=list(i.getLocation()),orient=str(i.getOrient()),status=str(i.getPlacementStatus()),dont_touch=i.isDoNotTouch(),expected_source=source,expected_source_net=net(src.getNet())if src else None,A=net(A),Y=net(Y),A_trace=trace(A),output_on_Y=Y is not None and port in [p.getName()for p in Y.getBTerms()]))
out=dict(scope='Actual final ODB read-only7exports; no STA/repair/source or timing PASS',rows=rows,open_A=[r['port']for r in rows if r['A']is None])
Path('/work/ACTUAL_FINAL.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out))
