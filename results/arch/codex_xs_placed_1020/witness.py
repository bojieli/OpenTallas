import odb,os,json,collections
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();d=json.loads(Path(os.environ['SEQUENTIAL_RAW']).read_text());edges=collections.defaultdict(list);terminal={}
for i in b.getInsts():
 master=i.getMaster().getName();seq='DFF' in master.upper() or 'SRAM' in master.upper();ins=[];outs=[]
 for t in i.getITerms():
  n=t.getNet()
  if not n or str(n.getSigType()) in ('POWER','GROUND','CLOCK'):continue
  name=i.getName()+'/'+t.getMTerm().getName();terminal[name]=n.getId()
  if str(t.getIoType())=='INPUT':ins.append((n.getId(),name))
  elif str(t.getIoType())=='OUTPUT':outs.append((n.getId(),name))
 if not seq:
  for a,ap in ins:
   for z,zp in outs:edges[a].append((z,ap,zp,master))
out=[]
for row in d['top'][:3]:
 start=terminal[row['source'][2]];target=terminal[row['sink'][2]];q=collections.deque([start]);prev={start:None}
 while q and target not in prev:
  n=q.popleft()
  for z,ap,zp,m in edges[n]:
   if z not in prev:prev[z]=(n,ap,zp,m);q.append(z)
 path=[];cur=target
 if cur in prev:
  while prev[cur] is not None:
   n,ap,zp,m=prev[cur];path.append(dict(input=ap,output=zp,master=m));cur=n
  path.reverse()
 out.append(dict(**row,found=target in prev,combinational_cells=path))
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(out,indent=2)+'\n');print([(x['um'],x['found'],len(x['combinational_cells'])) for x in out])
