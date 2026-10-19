import odb, json, collections, hashlib, os, gzip, csv
base='/work/results/asap7/opentallas_ot_hbm_svc_pc_ctrl_leaf_cfg_safe_legacy_asap7_ref_gate/base/'
path=base+'4_cts.odb'
db=odb.dbDatabase.create(); odb.read_db(db,path)
b=db.getChip().getBlock(); scale=b.getDbUnitsPerMicron()
insts=list(b.getInsts()); nets=list(b.getNets())
def ident(t): return t.getInst().getName()+'/'+t.getMTerm().getName()
def role(i):
 m=i.getMaster(); n=m.getName()
 return 'macro' if m.getType()=='BLOCK' else 'FF' if 'DFF' in n else 'tie' if 'TIE' in n else 'comb'
def trans(i):
 n=i.getMaster().getName()
 return n.startswith(('BUF','INV','HB2','HB4'))
def xy(t):
 v=t.getAvgXY()
 return [v[-2]/scale,v[-1]/scale]
def endpoint(t): return {'pin':ident(t),'role':role(t.getInst()),'master':t.getInst().getMaster().getName(),'xy':xy(t)}
def walk(n, seen=None):
 if seen is None: seen=set()
 if n is None or n.getId() in seen:return {}
 seen.add(n.getId()); out={}
 for t in n.getITerms():
  if t.getIoType() not in ('INPUT','INOUT'):continue
  i=t.getInst()
  if trans(i):
   for q in i.getITerms():
    if q.getIoType()=='OUTPUT':out.update(walk(q.getNet(),seen))
  else:out[ident(t)]=endpoint(t)
 for t in n.getBTerms():
  if t.getIoType()=='OUTPUT':out['PORT/'+t.getName()]={'pin':'PORT/'+t.getName(),'role':'port','master':'PORT'}
 return out
rows=[]; macros=[]
for i in insts:
 if role(i)=='macro':
  box=i.getBBox()
  macros.append({'inst':i.getName(),'master':i.getMaster().getName(),'bbox':[box.xMin()/scale,box.yMin()/scale,box.xMax()/scale,box.yMax()/scale], 'pins':[dict(endpoint(t),direction=t.getIoType(),net=t.getNet().getName() if t.getNet() else None) for t in i.getITerms()]})
 if trans(i):continue
 for t in i.getITerms():
  if t.getIoType()!='OUTPUT' or t.getNet() is None:continue
  ends=walk(t.getNet()); e=list(ends.values())
  isclock=bool(e) and all(x['pin'].rsplit('/',1)[-1].upper() in ('CLK','CK','RD_CLK','WR_CLK','RCLK','WCLK') for x in e)
  src=endpoint(t)
  reach=max((abs(src['xy'][0]-x['xy'][0])+abs(src['xy'][1]-x['xy'][1]) for x in e if 'xy'in x),default=0)
  rows.append(dict(src,fanout=len(e),clock=isclock,reach_um=reach,endpoints=e if len(e)>32 else []))
for t in b.getBTerms():
 if t.getIoType()!='INPUT' or t.getNet() is None:continue
 e=list(walk(t.getNet()).values())
 rows.append({'pin':'PORT/'+t.getName(),'role':'port','master':'PORT','fanout':len(e),'clock':bool(e) and all(x['pin'].rsplit('/',1)[-1].upper() in ('CLK','CK','RD_CLK','WR_CLK','RCLK','WCLK') for x in e),'endpoints':e if len(e)>32 else []})
nonclock=[r for r in rows if not r['clock']]
summary={'odb_sha256':hashlib.sha256(open(path,'rb').read()).hexdigest(),'instances':len(insts),'macro_count':len(macros),'masters':dict(collections.Counter(i.getMaster().getName() for i in insts)),'roots':len(rows),'nonclock_roots':len(nonclock),'unsafe_nonclock':sum(x['fanout']>32 for x in nonclock),'max_by_role':{r:max((x['fanout'] for x in nonclock if x['role']==r),default=0)for r in ('FF','comb','macro','tie','port')},'max_reach_um':max(x.get('reach_um',0) for x in nonclock)}
os.makedirs('/evidence/out',exist_ok=True)
summary['master_area_um2']={i.getMaster().getName():i.getMaster().getWidth()*i.getMaster().getHeight()/scale**2 for i in insts}
summary['physical_outline_um']=[b.getDieArea().xMin()/scale,b.getDieArea().yMin()/scale,b.getDieArea().xMax()/scale,b.getDieArea().yMax()/scale]
summary['clock_root_endpoints']={x['pin']:x['fanout'] for x in rows if x['clock']}
summary['reach_over405_roots']=sum(x.get('reach_um',0)>405 for x in nonclock)
json.dump([x for x in nonclock if x['fanout']>32],open('/evidence/out/unsafe_roots.json','w'),indent=2)
json.dump(sorted([x for x in nonclock if x.get('reach_um',0)>405],key=lambda x:-x.get('reach_um',0)),open('/evidence/out/reach_roots.json','w'),indent=2)
json.dump(summary,open('/evidence/out/summary.json','w'),indent=2)
json.dump(macros,open('/evidence/out/macros.json','w'),indent=2)
json.dump(sorted(rows,key=lambda x:-x['fanout']),open('/evidence/out/roots.json','w'),indent=2)
with gzip.open('/evidence/out/raw_cells.tsv.gz','wt') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['inst','master','role','x0_um','y0_um','x1_um','y1_um','orientation'])
 for i in insts:
  bb=i.getBBox();w.writerow([i.getName(),i.getMaster().getName(),role(i),bb.xMin()/scale,bb.yMin()/scale,bb.xMax()/scale,bb.yMax()/scale,i.getOrient()])
with gzip.open('/evidence/out/raw_pins.tsv.gz','wt') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['pin','master','direction','net','net_type','x_um','y_um'])
 for i in insts:
  for t in i.getITerms():
   n=t.getNet();w.writerow([ident(t),i.getMaster().getName(),t.getIoType(),n.getName() if n else '',n.getSigType() if n else '',*xy(t)])
 for t in b.getBTerms():
  n=t.getNet();w.writerow(['PORT/'+t.getName(),'PORT',t.getIoType(),n.getName() if n else '',n.getSigType() if n else '','',''])
print(json.dumps(summary,indent=2))
