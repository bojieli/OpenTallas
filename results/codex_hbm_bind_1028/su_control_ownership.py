"""Propose exact-once SU residual ownership from actual bit endpoint weights.
Usage: su_control_ownership.py PLAN ASBUILT MANIFEST OUT_DIR
Source topology proposal only. Physical capacity, added routes/cycles and adoption
remain open. Combinational primitives stay whole; supported FFs may fracture by
original Q/D index using the already-qualified primitive_splits mechanism.
"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys
import numpy as np
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind as B
plan,src,manifest,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
a=json.loads(manifest.read_text());p=json.loads(plan.read_text());p['asbuilt']=a
b=B.Binder(p,json.loads(src.read_text()),plan.parent,a['base']);b.map_cells();F=b.F
control=lambda pn: bool(re.fullmatch(r'(clk.*|clock.*|ck(_.*)?|rst.*|reset.*|arst.*|srst.*)',pn.lower()))
clocknets={n for c in F.cells for pn,bs in c.ports.items() if control(pn) for n in bs if isinstance(n,int)}
drivers=collections.defaultdict(list);loads=collections.defaultdict(list)
for i,c in enumerate(F.cells):
 for pn,bs in c.ports.items():
  if control(pn):continue
  tab=drivers if b.G.dirs[i].get(pn)=='output' else loads
  for bit,n in enumerate(bs):
   if isinstance(n,int) and n not in clocknets:tab[n].append((i,pn,bit))
clusters=collections.defaultdict(list)
for i,c in enumerate(F.cells):
 if i not in b.cpart and re.match(r'^su_(NW|NE)[0-3]\.',c.path):clusters[c.path.split('.')[0]].append(i)
whole={};bitowners={};records=[];fractures=[];all_touched=set()
for pre,ids in sorted(clusters.items()):
 parts=sorted({part for i,part in b.cpart.items() if F.cells[i].path.startswith(pre+'.')})
 assert len(parts)==2,(pre,parts)
 ix={i:j for j,i in enumerate(ids)};N=len(ids);edges=collections.Counter();anchor=np.zeros((N,2));ext=collections.defaultdict(set)
 touched={n for i in ids for pn,bs in F.cells[i].ports.items() if not control(pn) for n in bs if isinstance(n,int) and n not in clocknets};all_touched.update(touched)
 for n in touched:
  for si,sp,sb in drivers[n]:
   for di,dp,db in loads[n]:
    if si==di:continue
    x=ix.get(si);y=ix.get(di)
    if x is not None and y is not None:
     edges[(x,y)]+=1;edges[(y,x)]+=1
    elif x is not None and di in b.cpart:
     z=b.cpart[di]
     if z in parts:anchor[x,parts.index(z)]+=1
     else:ext[z].add(n)
    elif y is not None and si in b.cpart:
     z=b.cpart[si]
     if z in parts:anchor[y,parts.index(z)]+=1
     else:ext[z].add(n)
 er=np.array([e[0] for e in edges],dtype=np.int64);ec=np.array([e[1] for e in edges],dtype=np.int64);ew=np.array(list(edges.values()),dtype=float)
 degree=anchor.sum(axis=1)+np.bincount(er,weights=ew,minlength=N);safe=np.where(degree>0,degree,1)
 score=np.full(N,.5);convergence=None
 for iteration in range(192):
  update=(anchor[:,1]+np.bincount(er,weights=ew*score[ec],minlength=N))/safe
  update=np.where(degree>0,update,.5);update=.5*score+.5*update
  delta=float(np.max(np.abs(update-score)));score=update
  if delta<1e-9:convergence=iteration+1;break
 for i,j in ix.items():whole[i]=parts[int(score[j]>.5)]
 ties=0;ffrows=[]
 def neighbor_owner(ci):return whole.get(ci,b.cpart.get(ci))
 for i in ids:
  c=F.cells[i]
  if c.ytype not in ('$dff','$adff'):continue
  assert len(c.ports['D'])==len(c.ports['Q'])
  owners=[];votes=[]
  for k,(dn,qn) in enumerate(zip(c.ports['D'],c.ports['Q'])):
   v=collections.Counter()
   for ci,_,_ in loads.get(qn,[]):
    z=neighbor_owner(ci)
    if ci!=i and z in parts:v[z]+=1
   for ci,_,_ in drivers.get(dn,[]):
    z=neighbor_owner(ci)
    if ci!=i and z in parts:v[z]+=1
   best=max(v.values(),default=0);choices=[z for z in parts if v[z]==best]
   if len(choices)==1:z=choices[0]
   else:z=whole[i];ties+=1
   owners.append(z);votes.append(dict(v))
  bitowners[i]=owners
  by=collections.defaultdict(list)
  for k,z in enumerate(owners):by[z].append(k)
  if len(by)>1:fractures.append(dict(member=c.path,fragments=[dict(path=c.path+'.__controller_'+z,bits=ks,partition=z) for z,ks in sorted(by.items())]))
  ffrows.append(dict(path=c.path,module=c.module,width=len(owners),owner_bits=dict(by),endpoint_votes=votes))
 counts={z:dict(nonfractured_cells=0,sequential_fragments=0,known_primitive_q_bits=0,retained_leaf_cells=[]) for z in parts}
 for i in ids:
  c=F.cells[i]
  if i in bitowners:
   for z,n in collections.Counter(bitowners[i]).items():counts[z]['sequential_fragments']+=1;counts[z]['known_primitive_q_bits']+=n
  else:
   counts[whole[i]]['nonfractured_cells']+=1
   if c.kind!='glue':counts[whole[i]]['retained_leaf_cells'].append(dict(path=c.path,module=c.module,parameters=c.params,internal_state='UNELABORATED_REQUIRED_BEFORE_DENSITY'))
 records.append(dict(source_root=pre,parts=parts,unmapped_cells=N,whole_cell_owners={F.cells[i].path:whole[i] for i in ids if i not in bitowners},ff_bit_owners=ffrows,per_part=counts,external_ingress_or_egress_bits={z:len(ns) for z,ns in ext.items()},solver=dict(method='bit-weighted endpoint harmonic vote; fixed native cut anchors; whole combinational primitives',iterations=iteration+1,converged_iterations=convergence,last_delta=delta,tied_ff_bits=ties,unconnected_cells=int(sum(degree==0))),primary_counterfactual=parts[0]))
# Fracture proposals refer to current residual FF indices. Translate through any
# existing original-vector fragment before producing a composable source packet.
composition=json.loads(Path(a['compose']).read_text());oldspec=copy.deepcopy(composition.get('primitive_splits',[]));byfrag={f['path']:(s,f) for s in oldspec for f in s['fragments']}
for row in fractures:
 old=byfrag.get(row['member'])
 if old:
  s,f=old;original=f['bits'];s['fragments'].remove(f)
  s['fragments'] += [dict(path=g['path'],bits=[original[k] for k in g['bits']]) for g in row['fragments']]
 else:oldspec.append(dict(member=row['member'],fragments=[{k:g[k] for k in ('path','bits')}for g in row['fragments']]))
composition['primitive_splits']=oldspec
(out/'compose_proposal.json').write_text(json.dumps(composition,separators=(',',':'))+'\n')
maprows={}
for rec in records:
 for path,z in rec['whole_cell_owners'].items():maprows[path]=[z,'u_su_controller.'+hashlib.sha256(path.encode()).hexdigest()[:16]]
 for ff in rec['ff_bit_owners']:
  for z,ks in ff['owner_bits'].items():
   path=ff['path'] if len(ff['owner_bits'])==1 else ff['path']+'.__controller_'+z
   maprows[path]=[z,'u_su_controller.'+hashlib.sha256(path.encode()).hexdigest()[:16]]
# Source crossing demand on nets incident to these residual cells. No wire delay
# or zero-cycle physical implementation is inferred.
def owners(i,pn,k,counterfactual=False):
 if i in b.cpart:return {b.cpart[i]}
 if i not in whole:return set()
 if counterfactual:
  pre=F.cells[i].path.split('.')[0];return {next(r['primary_counterfactual'] for r in records if r['source_root']==pre)}
 if i in bitowners:
  if pn in ('D','Q'):return {bitowners[i][k]}
  return set(bitowners[i])
 return {whole[i]}
def crossing(cf):
 groups=collections.defaultdict(dict)
 for n in all_touched:
  for si,sp,sb in drivers[n]:
   for di,dp,db in loads[n]:
    for z in owners(si,sp,sb,cf):
     for y in owners(di,dp,db,cf):
      if z!=y:groups[(z,y)].setdefault(n,dict(driver=F.cells[si].path,port=sp,bit=sb))
 return [dict(src=z,dst=y,bits=len(ns),drivers=[dict(global_net=n,**d)for n,d in sorted(ns.items())])for (z,y),ns in sorted(groups.items())]
receipt=dict(schema='opentallas.hbm.su_control_ownership_proposal.v1',source_json=str(src),manifest=str(manifest),status='PROPOSAL_ONLY_NO_PHYSICAL_CAPACITY_OR_CYCLE_ADOPTION',excluded='Clock/reset nets and pins; source outside SU roots not assigned.',unmapped_before=b.n_unmapped,assigned_original_su_cells=len(whole),other_unmapped_cells=b.n_unmapped-len(whole),records=records,needed_ff_fractures=fractures,source_map=dict(parts=maprows),incident_crossings=crossing(False),central_counterfactual_crossings=crossing(True),cycles='PENDING actual route/landing/token price',note='Every original SU residual cell is owned once; each FF Q/D bit exactly once. Mixed vectors require existing exact primitive_splits. Ties/solver uncertainty explicit; tied/unconnected homes are estimates requiring plan-owner choice. Qbits count visible primitives ONLY; retained leaf state/macros require source body census before density. No comb primitive duplication or semantic edit.')
(out/'ownership.json').write_text(json.dumps(receipt,separators=(',',':'))+'\n')
(out/'summary.json').write_text(json.dumps({k:v for k,v in receipt.items() if k not in ('records','source_map','needed_ff_fractures','incident_crossings','central_counterfactual_crossings')}|dict(per_source=[dict(source_root=r['source_root'],per_part=r['per_part'],solver=r['solver'])for r in records],ff_fractures=len(fractures),incident_crossing_bits=sum(x['bits']for x in receipt['incident_crossings']),central_counterfactual_bits=sum(x['bits']for x in receipt['central_counterfactual_crossings'])),indent=2)+'\n')
print('SU ownership proposal',len(whole),'cells',len(fractures),'mixed FFvectors; otherunmapped',receipt['other_unmapped_cells'],flush=True)
