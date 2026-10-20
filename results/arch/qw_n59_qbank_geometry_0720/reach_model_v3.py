import json,gzip,sys,re,collections,hashlib,time
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.optimize import linprog
base=Path(sys.argv[1]);mode=sys.argv[2];graph=base/'stage_graph_v2.json.gz';g=json.load(gzip.open(graph,'rt'));m=json.load(open(base/'provider_model.json'));nodes=g['endpoint_nodes'];insts=g['instances'];edges=g['edges'];W,H=m['proposal']['outline_um'];positions={p['writer']:p for p in m['proposal']['placements']};macroW=m['macro']['width_um'];qsplit={k for k in insts if 'qrow_a' in k};newnodes={};newedges=[]
def writer(name):
 z=re.search(r'g_writer\\?\[(\d+)\\?\]',name);return int(z[1]) if z else None

def duplicate(n,side):
 key=n+'@'+side
 if key not in newnodes:
  nd=dict(nodes[n]);nd['inst']+='@'+side;newnodes[key]=nd
 return key
if mode.startswith('split_input'):
 for a,b in edges:
  aa=[a];bb=[b]
  if nodes[a]['inst'] in qsplit:aa=[duplicate(a,s) for s in ['L','R']]
  if nodes[b]['inst'] in qsplit:
   w=writer(nodes[a]['inst']);sides=['L' if w<4 else 'R'] if w is not None else ['L','R'];bb=[duplicate(b,s) for s in sides]
  if nodes[a]['kind']=='port' and nodes[a]['direction']=='INPUT' and nodes[a]['pin'] not in ['rst_n','ck']:
   k='EXTRA_INPUT/'+nodes[a]['pin'];nd=dict(nodes[a]);nd.update(inst=k,kind='new_input_seq');newnodes[k]=nd;aa=[k]
  for x in aa:
   for y in bb:newedges.append([x,y])
 for k,n in list(newnodes.items()):
  if n['kind']=='new_input_seq':newedges.append(['PORT/'+n['pin'],k])
 edges=newedges;nodes.update(newnodes)
used={n for e in edges for n in e};seqinst=sorted({nodes[n]['inst'] for n in used if nodes[n]['kind']=='seq'});idx={k:2*i for i,k in enumerate(seqinst)};ridx=2*len(idx);nv=ridx+1;coords={};bounds=[(0,W),(0,H)]*len(idx)+[(0,None)]
for n in used:
 nd=nodes[n];kind=nd['kind'];i=nd['inst'];pin=nd['pin']
 if kind=='seq':
  orig=i.split('@')[0];b=insts[orig]['bbox'];off=[nd['point'][0]-(b[0]+b[2])/2,nd['point'][1]-(b[1]+b[3])/2];coords[n]=(idx[i],off)
 elif kind=='macro':
  wi=writer(i);p=positions[wi];x,y=m['macro']['pins'][pin]['point'];x=macroW-x if p['orient']=='MY' else x;coords[n]=(None,[p['origin'][0]+x,p['origin'][1]+y])
 elif kind in ['port','new_input_seq']:
  x,y=nd['point'];x+=(W-518.4)/2;y=H if y>194.4 else 0
  if kind=='new_input_seq':y=4.32
  coords[n]=(None,[x,y])
 else:raise ValueError(kind)
# Literal source boundary capture/launch FFs stay adjacent to physical pads unless a new input stage is inserted.
for a,b in edges:
 na,nb=nodes[a],nodes[b]
 if na['kind']=='port' and nb['kind']=='seq' and na['pin']!='rst_n':
  xy=coords[a][1];i=idx[nb['inst']]
  for d,maxi in [(0,W),(1,H)]:bounds[i+d]=(max(0,xy[d]-4.32),min(maxi,xy[d]+4.32))
 if na['kind']=='seq' and nb['kind']=='port':
  xy=coords[b][1];i=idx[na['inst']]
  for d,maxi in [(0,W),(1,H)]:bounds[i+d]=(max(0,xy[d]-4.32),min(maxi,xy[d]+4.32))
row=[];col=[];val=[];rhs=[]
for a,b in edges:
 ia,oa=coords[a];ib,ob=coords[b]
 for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
  ri=len(rhs);rhs.append(-sx*(oa[0]-ob[0])-sy*(oa[1]-ob[1]))
  for ii,ss in [(ia,1),(ib,-1)]:
   if ii is not None:row.extend([ri,ri]);col.extend([ii,ii+1]);val.extend([sx*ss,sy*ss])
  row.append(ri);col.append(ridx);val.append(-1)
A=coo_matrix((val,(row,col)),shape=(len(rhs),nv)).tocsr();cost=np.zeros(nv);cost[-1]=0 if mode.endswith('405') else 1
if mode.endswith('405'):bounds[-1]=(405,405)
print('LP',mode,'edges',len(edges),'seq',len(idx),'rows',len(rhs),'nnz',A.nnz,flush=True)
t=time.time();res=linprog(cost,A_ub=A,b_ub=np.array(rhs),bounds=bounds,method='highs',options={'time_limit':300});print('LPresult',res.status,res.message,'seconds',time.time()-t,flush=True)
out={'schema':'opentallas.qbank.full_stage_necessary_reach_model.v1','mode':mode,'status':'MODEL_ONLY_HOLD','source_graph_sha256':hashlib.sha256(graph.read_bytes()).hexdigest(),'source_role_errors':g['role_errors'],'original_graph_edges':len(g['edges']),'modeled_edges':len(edges),'seq_instances':len(idx),'qrow_a_original_instances':len(qsplit),'extra_input_instances':sum(n['kind']=='new_input_seq' for n in newnodes.values()),'solver_status':res.status,'solver_message':res.message,'scope':'Continuous FF centres, actual fixed macro/pad pins and full actualLib Boolean-closure stage root edges. Necessary endpoint span ONLY; no packing/legal rows/route length/cell timing/clock/PG/native32/source semantics qualification. New topology proposal is not source implemented or proven.'}
if res.x is not None:
 witness={k:res.x[i:i+2].tolist() for k,i in idx.items()};dist=[]
 for a,b in edges:
  def pt(n):
   i,o=coords[n];return o if i is None else [res.x[i]+o[0],res.x[i+1]+o[1]]
  x,y=pt(a),pt(b);d=abs(x[0]-y[0])+abs(x[1]-y[1]);dist.append((d,a,b))
 out.update(minimax_endpoint_L1_um=float(res.x[-1]),maximum_recomputed=max(dist),stage_endpoint_violations_gt405=int(sum(z[0]>405.000001 for z in dist)),coordinates=witness)
(base/('reach_'+mode+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='coordinates'}),flush=True)
