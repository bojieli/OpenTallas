import odb, json, os, hashlib, collections, pathlib
path=os.environ['PG_ODB']; out=os.environ['PG_OUT']
db=odb.dbDatabase.create(); odb.read_db(db,path); b=db.getChip().getBlock()
rows=[]; masters={}; bad=[]; counts=collections.Counter()
for inst in b.getInsts():
 m=inst.getMaster(); terms={t.getMTerm().getName():t for t in inst.getITerms()}
 for mt in m.getMTerms():
  typ=str(mt.getSigType()); pn=mt.getName()
  if typ not in ('POWER','GROUND'):
   if pn.upper() in ('VDD','VSS','VCC','GND','VPWR','VGND'): counts['named_pg_without_native_type']+=1
   continue
  t=terms.get(pn); net=t.getNet() if t else None
  expected='VDD' if typ=='POWER' else 'VSS'
  actual=net.getName() if net else None; nt=str(net.getSigType()) if net else None
  status='PASS' if actual==expected and nt==typ else ('UNBOUND' if net is None else 'WRONG_NET')
  row=[inst.getName(),m.getName(),str(m.getType()),pn,typ,actual,nt,expected,status]
  rows.append(row); counts[status]+=1
  if status!='PASS': bad.append(row)
  masters[m.getName()]=[str(m.getType()),[[x.getName(),str(x.getSigType())] for x in m.getMTerms()]]
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
pathlib.Path(out+'.json').write_text(json.dumps(dict(odb=path,odb_sha256=sha(path),instances=len(b.getInsts()),counts=dict(counts),masters=masters,failures=bad,nets=[[n.getName(),str(n.getSigType()),len(n.getITerms())] for n in b.getNets() if str(n.getSigType()) in ('POWER','GROUND')]),indent=2)+'\n')
with open(out+'.tsv','w') as f:
 f.write('instance\tmaster\tmaster_type\tpin\tpg_type\tactual_net\tnet_type\texpected_net\tstatus\n')
 for r in rows:f.write('\t'.join(str(x) for x in r)+'\n')
print('PG_AUDIT',out,dict(counts))

import re,gzip
# Native final GRT database; every endpoint retained, including reset/ties/macros.
trans=lambda i: bool(re.match(r'^(BUF|INV|HB)[x0-9_]',i.getMaster().getName(),re.I))
clock=lambda t: str(t.getSigType())=='CLOCK' or t.getMTerm().getName().upper() in ('CLK','CK','CP','GCLK','CLKN','CLKB')
role=lambda i: ('macro' if i.getMaster().isBlock() else ('ff' if re.search('DFF|SDFF',i.getMaster().getName(),re.I) else ('tie' if re.search('TIE|LOGIC[01]',i.getMaster().getName(),re.I) else 'comb')))
def loc(t):
 try:
  a=t.getAvgXY();return (a[-2]/b.getDbUnitsPerMicron(),a[-1]/b.getDbUnitsPerMicron()) if a[0] else None
 except Exception:return None
def bloc(t):
 boxes=[q for bp in t.getBPins() for q in bp.getBoxes()]
 if not boxes:return None
 q=boxes[0];return ((q.xMin()+q.xMax())/2/b.getDbUnitsPerMicron(),(q.yMin()+q.yMax())/2/b.getDbUnitsPerMicron())
roots=[]; endpoints=[]; excludes=collections.Counter(); reach=[]; unknown=[]
for n in b.getNets():
 ds=[t for t in n.getITerms() if str(t.getIoType())=='OUTPUT' and str(t.getSigType()) not in ('POWER','GROUND')]
 bs=[t for t in n.getBTerms() if str(t.getIoType())=='INPUT']
 if len(ds)==1:
  d=ds[0];i=d.getInst()
  if trans(i):continue
  name=i.getName()+'/'+d.getMTerm().getName();kind=role(i);xy=loc(d)
 elif not ds and len(bs)==1:
  name='port:'+bs[0].getName();kind='input';xy=bloc(bs[0])
 else:
  if ds or bs:unknown.append([n.getName(),len(ds),len(bs)])
  continue
 seen=set(); sinks={}; todo=[n]
 while todo:
  nn=todo.pop()
  if nn.getId() in seen:continue
  seen.add(nn.getId())
  for t in nn.getBTerms():
   if str(t.getIoType())=='OUTPUT':sinks['port:'+t.getName()]=('output',bloc(t),None)
  for t in nn.getITerms():
   if str(t.getSigType()) in ('POWER','GROUND') or str(t.getIoType()) not in ('INPUT','INOUT'):continue
   if clock(t):excludes[t.getInst().getMaster().getName()+'/'+t.getMTerm().getName()]+=1;continue
   i=t.getInst()
   if trans(i):
    todo.extend(x.getNet() for x in i.getITerms() if str(x.getIoType())=='OUTPUT' and x.getNet())
   else:sinks[i.getName()+'/'+t.getMTerm().getName()]=(role(i),loc(t),t.getMTerm().getName())
 counts=collections.Counter(v[0] for v in sinks.values());worst=0
 for sn,(sk,sxy,pn) in sinks.items():
  dist=abs(xy[0]-sxy[0])+abs(xy[1]-sxy[1]) if xy and sxy else None
  if dist is not None:worst=max(worst,dist)
  endpoints.append([name,kind,sn,sk,pn,dist])
  if dist is not None and dist>405:reach.append([name,sn,dist])
 roots.append([name,kind,len(sinks),dict(counts),worst])
with gzip.open(out+'_all_roots.json.gz','wt') as f:json.dump(roots,f)
with gzip.open(out+'_all_endpoints.json.gz','wt') as f:json.dump(endpoints,f)
summary=dict(odb_sha256=sha(path),roots=len(roots),endpoints=len(endpoints),unsafe=[r for r in roots if r[2]>32],maximum=max((r[2] for r in roots),default=0),clock_pin_exclusions=dict(excludes),ambiguous_roots=unknown,reach_over405=reach,transparent_masters=sorted(set(i.getMaster().getName() for i in b.getInsts() if trans(i))),reach_definition='Manhattan logical root output pin to real endpoint pin through BUF/INV; physical XY, clock terminals excluded',clock_exclusion_definition='native CLOCK plus exact conventional clock pin names; validate against exported native Liberty')
pathlib.Path(out+'_census.json').write_text(json.dumps(summary,indent=2)+'\n')
print('FINAL_NATIVE_CENSUS',len(roots),len(summary['unsafe']),summary['maximum'],'reach405',len(reach))
