import odb,json,math,re
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,'/work/run/results/asap7/hbc_ot_hgi_sfu_opsa_rest/base/3_place.odb')
b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
insts={i.getName().replace('\\',''):i for i in b.getInsts()}
def xy(i):
 x,y=i.getLocation();m=i.getMaster();return ((x+m.getWidth()/2)/u,(y+m.getHeight()/2)/u)
def seq(i):return 'DFF' in i.getMaster().getName() or i.getMaster().getName().startswith(('DLL','DHL'))
outs={}
for i in insts.values():
 outs[i.getName()]=[t.getNet() for t in i.getITerms() if t.getMTerm().getSigType()=='SIGNAL' and t.getMTerm().getIoType()=='OUTPUT' and t.getNet()]
adj={};caps={}
for n in b.getNets():
 if n.getSigType()!='SIGNAL':continue
 a=[];c=[]
 for t in n.getITerms():
  if t.getMTerm().getIoType()!='INPUT' or t.getMTerm().getSigType()!='SIGNAL':continue
  i=t.getInst()
  if seq(i):
   if t.getMTerm().getName()=='D':c.append(i.getName().replace('\\',''))
  else:a.extend(q.getName() for q in outs[i.getName()])
 adj[n.getName()]=a;caps[n.getName()]=c
rows=[]
for name,i in insts.items():
 if not name.startswith('u_hop_') or not seq(i):continue
 src=name.replace('u_hop_','u_bin_',1)
 if src not in insts:continue
 stack=[n.getName() for n in outs[i.getName()]];seen=set();cs=set()
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n);cs.update(caps.get(n,()));stack.extend(adj.get(n,()))
 h=xy(i);s=xy(insts[src]);cc=[dict(name=n,xy=xy(insts[n])) for n in sorted(cs)]
 worst=max((math.dist(h,c['xy']) for c in cc),default=0)
 rows.append(dict(hop=name,source=src,source_xy=s,hop_xy=h,captures=cc,face_hop_um=math.dist(s,h),hop_consumer_max_um=worst))
Path('/out/reach.json').write_text(json.dumps(rows,indent=1)+'\n')
print('HOP_REACH',len(rows),'face_over405',sum(r['face_hop_um']>405 for r in rows),'consumer_over405',sum(r['hop_consumer_max_um']>405 for r in rows),'max_face',max(r['face_hop_um'] for r in rows),'max_consumer',max(r['hop_consumer_max_um'] for r in rows),flush=True)
