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


regions=collections.defaultdict(list)
for a,b in edges:
 ia,oa=coords[a];ib,ob=coords[b]
 for an,bn,i,j,o,z in [(a,b,ia,ib,oa,ob),(b,a,ib,ia,ob,oa)]:
  if i is None:continue
  if j is None:box=[z[0]-o[0],z[1]-o[1],z[0]-o[0],z[1]-o[1]]
  elif bounds[j][1]-bounds[j][0]<10 and bounds[j+1][1]-bounds[j+1][0]<10:box=[bounds[j][0]+z[0]-o[0],bounds[j+1][0]+z[1]-o[1],bounds[j][1]+z[0]-o[0],bounds[j+1][1]+z[1]-o[1]]
  else:continue
  regions[nodes[an]['inst']].append((box,an,bn))
worst=[]
for inst,pts in regions.items():
 if len(pts)<2:continue
 best=max((max(a[0][0]-b[0][2],b[0][0]-a[0][2],0)+max(a[0][1]-b[0][3],b[0][1]-a[0][3],0),a,b) for a in pts for b in pts)
 if best[0]>810:worst.append({'instance':inst,'minimax_lower_bound_um':best[0]/2,'neighbours':best[1:]})
worst.sort(key=lambda z:-z['minimax_lower_bound_um']);(base/'anchor_neighbour_witness.json').write_text(json.dumps(worst,indent=2)+'\n');print('WITNESS count',len(worst),json.dumps(worst[:4]),flush=True)
