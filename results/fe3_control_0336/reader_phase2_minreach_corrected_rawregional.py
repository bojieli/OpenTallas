from pathlib import Path
from collections import defaultdict,deque
import sys,json,re,math
sys.path.insert(0,"/srv/opentallas-scratch2/claude/codex-fe3-control-0336/vendor")
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
b=Path('/srv/opentallas-scratch2/claude/codex-fe3-control-0336');sys.path.insert(0,str(b));import geom_rules as G
D=G.Design(b/'input/geom.tsv');byname={c[6]:k for k,c in D.cells.items()};model=json.load(open(b/'input/read_split_model.json'));moved={}
for n,xy in model['moved'].items():
 if ('u_bound.u_bin_x_st_b_i/' in n or ('/u_ring.dch' in n and '.u_dsel/y' in n)):
  k=byname[n];c=list(D.cells[k]);cx,cy=G.ctr(c);dx=xy[0]-cx;dy=xy[1]-cy;c[2]+=dx;c[4]+=dx;c[3]+=dy;c[5]+=dy;D.cells[k]=tuple(c);moved[n]=xy
original=json.load(open(b/'input/capture_census.json'))
origin=next(k for k,c in D.cells.items() if c[0]=='S' and c[6].startswith('u_bound.u_cland_rstart_rx/'))
controls={byname[cap] for dist,src,cap in original['census'] if src.startswith('u_bound.u_cland_rstart_rx/') and cap.startswith('u_bound.u_cland_') and 'u_cland_fstart_' not in cap}
seq={k for k,c in D.cells.items() if c[0]=='S'};succ=defaultdict(set);pred=defaultdict(set)
for cid,nets in D.drives.items():
 for net in nets:
  for end in D.nets[net][2]:
   if end[0]=='i' and not end[2]:succ[cid].add(end[1]);pred[end[1]].add(cid)
def nearest(start,edges):
 q=list(edges[start]);seen=set();out=set()
 while q:
  k=q.pop()
  if k in seen:continue
  seen.add(k)
  if k in seq:out.add(k)
  elif D.cells[k][0] in 'BLK':q.extend(edges[k])
 return out
controls={q for q in nearest(origin,succ) if D.cells[q][6].startswith("u_bound.u_cland_") and "u_cland_fstart_" not in D.cells[q][6]}
rawold=next(k for k,c in D.cells.items() if c[0]=='S' and c[6].startswith('u_bound.u_cland_rst_cws3_i/'))
rawpath=[];at=rawold
while True:
 q=nearest(at,pred)
 if len(q)!=1:raise RuntimeError('raw reset equation has multiple seq parents; exact clone model must expand it')
 parent=next(iter(q));rawpath.append(parent)
 if not D.cells[parent][6].startswith('u_bound.u_rrl_'):break
 at=parent
rawbase=rawpath[-1];rrpath=list(reversed(rawpath[:-1]));rawmeta=[];ghostmeta={};adj={}
for k in [origin]+sorted(controls):adj[k]=[nearest(k,pred),nearest(k,succ)]
def ghost(proto,name,role):
 k=max(D.cells)+1;c=list(D.cells[proto]);c[6]=name;D.cells[k]=tuple(c);adj[k]=[set(),set()];ghostmeta[k]=dict(name=name,role=role);return k
reader={};reader_first=[]
for prefix in sorted({D.cells[k][6].split('/')[0] for k in controls}):
 r=ghost(origin,'MODEL_reader_start_'+prefix,'reader BOOT +1');reader[prefix]=r;f=ghost(origin,'MODEL_reader_first_'+prefix,'reader BOOT +2 first stage');reader_first.append(f);adj[f][0].add(origin);adj[origin][1].add(f);adj[r][0].add(f);adj[f][1].add(r)
 for k in controls:
  if D.cells[k][6].split('/')[0]!=prefix:continue
  adj[k][0].discard(origin);adj[k][0].add(r);adj[origin][1].discard(k);adj[r][1].add(k)
faces=[k for k,c in D.cells.items() if c[0]=='S' and c[6].startswith('u_bound.u_cland_fstart_')]
writers=[]
for f in faces:
 q=ghost(origin,'MODEL_writer_bridge_'+D.cells[f][6],'writer BOOT +2 via existing origin q +onebridge+existingface');writers.append((q,f));adj[origin][1].discard(f);adj[q][0].add(origin);adj[origin][1].add(q);adj[q][1].add(f)
# All new raw branches are exact same-depth copies from the SAME fixed ancestor.
consumers=[origin]+reader_first+list(reader.values())+[q for q,f in writers]
for consumer in consumers:
 prev=rawbase;copies=[]
 for old in rrpath+[rawold]:
  q=ghost(old,'MODEL_raw_for_'+str(consumer)+'_same_'+D.cells[old][6],'same-depth raw tree clone; zero additional boot phase')
  adj[q][0].add(prev)
  if prev in adj:adj[prev][1].add(q)
  copies.append(dict(original=D.cells[old][6],copy=D.cells[q][6],D_original=D.cells[prev][6] if prev==rawbase else copies[-1]['original'],depth_from_fixed_base=len(copies)+1));prev=q
 adj[consumer][0].discard(rawold);adj[consumer][0].add(prev);adj[prev][1].add(consumer)
 for bridge,face in writers:
  if bridge==consumer:adj[prev][1].add(face)
 if consumer in reader.values():
  prefix=next(p for p,r in reader.items() if r==consumer)
  for k in controls:
   if D.cells[k][6].split('/')[0]==prefix and rawold in adj[k][0]:
    adj[k][0].discard(rawold);adj[k][0].add(prev);adj[prev][1].add(k)
 rawmeta.append(dict(consumer=D.cells[consumer][6],fixed_base=D.cells[rawbase][6],stages=copies))
audit=dict(status='PRELIMINARY design graph; no RTL',writer_edges=[dict(old_origin_face_removed=f not in adj[origin][1],origin_bridge=q in adj[origin][1] and origin in adj[q][0],bridge_face=f in adj[q][1],face=D.cells[f][6]) for q,f in writers],reader_edges=[dict(control=D.cells[k][6],old_origin_removed=origin not in adj[k][0],regional_reader_present=reader[D.cells[k][6].split('/')[0]] in adj[k][0],old_raw_retained=rawold in adj[k][0]) for k in controls],literal_raw_branches=rawmeta)
assert all(a['old_origin_face_removed'] and a['origin_bridge'] and a['bridge_face'] for a in audit['writer_edges'])
assert all(a['old_origin_removed'] and a['regional_reader_present'] for a in audit['reader_edges'])
(b/'reader_phase2_minreach_corrected_rawregional_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
variables=list(adj);ix={k:j for j,k in enumerate(variables)};fixed={k:set() for k in variables};pairs=set()
for k,(before,after) in adj.items():
 for q in before|after:
  if q==k:continue
  if q in ix:pairs.add(tuple(sorted((k,q))))
  else:fixed[k].add(q)
pin=None
for line in (b/'input/geom.tsv').read_text().replace('\\t','\t').splitlines():
 a=line.split('\t')
 if a[0]=='P' and a[2].startswith('cland_rstart_in'):pin=list(map(float,a[6:8]));break
assert pin
core=D.extra['core'];N=len(variables);results={}
for rad in [30]:
 rows=[];rhs=[];bounds=[];cert=[]
 for k in variables:
  j=ix[k];points=[(q,G.ctr(D.cells[q])) for q in fixed[k]];us=[(q,sum(pt)) for q,pt in points];vs=[(q,pt[0]-pt[1]) for q,pt in points]
  loU=-1e6;hiU=1e6;loV=-1e6;hiV=1e6
  for axis,values in [(0,us),(1,vs)]:
   for _,value in values:
    for sign in [-1,1]:rows.append({2*j+axis:sign,4*N:-1});rhs.append(sign*value)
  if k==origin:loU=max(loU,sum(pin)-rad);hiU=min(hiU,sum(pin)+rad);loV=max(loV,pin[0]-pin[1]-rad);hiV=min(hiV,pin[0]-pin[1]+rad)
  if loU>hiU or loV>hiV:cert.append(dict(cell=D.cells[k][6],u=[loU,hiU],v=[loV,hiV],fixed_sources=[D.cells[q][6] for q in fixed[k]]))
  bounds.extend([(loU,hiU),(loV,hiV)])
  c=D.cells[k];hw=(c[4]-c[2])/2;hh=(c[5]-c[3])/2
  for a,d,z in [(1,1,2*(core[2]-hw)),(-1,-1,-2*(core[0]+hw)),(1,-1,2*(core[3]-hh)),(-1,1,-2*(core[1]+hh))]:rows.append({2*j:a,2*j+1:d});rhs.append(z)
 for a,z in pairs:
  for axis in [0,1]:
   for sign in [-1,1]:rows.append({2*ix[a]+axis:sign,2*ix[z]+axis:-sign,4*N:-1});rhs.append(0)
 for k in variables:
  x,y=G.ctr(D.cells[k]);j=ix[k]
  for axis,value in [(0,x+y),(1,x-y)]:
   for sign in [-1,1]:rows.append({2*j+axis:sign,2*N+2*j+axis:-1});rhs.append(sign*value)
 bounds += [(0,None)]*(2*N+1)
 if cert:results[str(rad)]=dict(success=False,status='LOCAL_FIXED_CONE_INFEASIBLE',certificates=cert);continue
 A=lil_matrix((len(rows),4*N+1))
 for ri,row in enumerate(rows):
  for col,v in row.items():A[ri,col]=v
 obj=np.r_[np.zeros(4*N),1]
 r=linprog(obj,A_ub=A.tocsr(),b_ub=np.array(rhs),bounds=bounds,method='highs',options={'time_limit':45})
 out=dict(success=bool(r.success),status=str(r.message))
 if r.success:
  poses={D.cells[k][6]:[(r.x[2*ix[k]]+r.x[2*ix[k]+1])/2,(r.x[2*ix[k]]-r.x[2*ix[k]+1])/2] for k in variables};out['positions']=poses;out['origin']=poses[D.cells[origin][6]];out['max_in_out_cone_distance']=max(sum(abs(x-y) for x,y in zip(poses[D.cells[k][6]],poses[D.cells[q][6]] if q in ix else G.ctr(D.cells[q]))) for k in variables for q in fixed[k]|set().union(*adj[k]) if q!=k);out['objective']=float(r.fun);out['critical_edges']=sorted([dict(source=D.cells[k][6],sink=D.cells[q][6],distance=sum(abs(x-y) for x,y in zip(poses[D.cells[k][6]],poses[D.cells[q][6]] if q in ix else G.ctr(D.cells[q])))) for k in variables for q in fixed[k]|set().union(*adj[k]) if q!=k],key=lambda z:-z['distance'])[:30]
 results[str(rad)]=out
(b/'reader_phase2_minreach_corrected_rawregional.json').write_text(json.dumps(dict(scope='analytic full-control L1 minimum max-register-reach, reader+2, origin pinradius30; no rows/sites/overlap/clock/STA clearance',data_only_moves=len(moved),reader_controls=len(controls),new_reader_relays=len(reader)+len(reader_first),new_writer_bridges=len(writers),new_raw_copy_flops=sum(len(r['stages']) for r in rawmeta),literal_raw_branches=rawmeta,variables=N,results=results),indent=2)+'\n')
print('COUNTS',len(controls),len(reader),len(writers),sum(len(r['stages']) for r in rawmeta),'BASE',D.cells[rawbase][6],G.ctr(D.cells[rawbase]))
for rad,r in results.items():print('PIN',rad,'SAT',r['success'],'STATUS',r['status'],'MAX',r.get('max_in_out_cone_distance'),'ORIGIN',r.get('origin'))
