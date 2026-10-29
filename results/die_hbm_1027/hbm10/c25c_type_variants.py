"""Explicit physical type variants for real bound content differences; no binder/check waiver.
usage: c25c_type_variants.py SRC_DIR OUT_DIR bind_report.json bind_latency.json
Outputs an overlay: apply all generated files to a complete plan tree before regeneration.
"""
import copy,json,sys
from pathlib import Path
D,O,R,L=map(Path,sys.argv[1:5]);O.mkdir(parents=True,exist_ok=True)
P=json.load(open(D/'die_plan.json'));R=json.load(open(R));L=json.load(open(L))['buses']
parts={p['name']:p for p in P['partitions']};newmap={};clones={};changes=[]
for row in R['type_splits']:
 old=row['type'];assert old in P['partition_types'],old
 for i,group in enumerate(row['variants']):
  assert all(parts[p]['type']==old for p in group),(old,group,'source plan no longer matches binding groups')
  if not i:continue
  new=old+'__physical_v'+str(i)
  assert new not in P['partition_types'],new
  t=copy.deepcopy(P['partition_types'][old]);t['module']+='__physical_v'+str(i)
  t['note']=t.get('note','')+' | Explicit actual bound-content variant; same leaf masters/geometry, independent wrapper G3.'
  # No wrapper views are valid under the new module identity.
  for k in ('lef','lib','libs','gds','def','netlist','sdc','signed','signoff'):t.pop(k,None)
  P['partition_types'][new]=t;clones[new]=old
  for part in group:parts[part]['type']=new;newmap[part]=new
  changes.append({'old_type':old,'new_type':new,'instances':group,'reason':row['detail'],'hardcore_interfaces_changed':False})
# Type-keyed indices keep both variants; per-instance indices and hard-master keys remain intact.
def clone_indices(obj,path,log):
 if isinstance(obj,dict):
  for k,v in list(obj.items()):clone_indices(v,path+'/'+k,log)
  for new,old in clones.items():
   if old in obj and new not in obj:
    obj[new]=copy.deepcopy(obj[old]);log.append(path+'/'+new)
 elif isinstance(obj,list):
  for i,v in enumerate(obj):clone_indices(v,path+'/'+str(i),log)
index_changes=[]
for k,v in P.items():
 if k not in ('partition_types','partitions'):clone_indices(v,k,index_changes)
(O/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n')
sidecars=[]
for f in D.glob('*.json'):
 if f.name=='die_plan.json':continue
 try:q=json.load(open(f))
 except (ValueError,OSError):continue
 log=[];clone_indices(q,f.name,log)
 if log:(O/f.name).write_text(json.dumps(q,indent=1)+'\n');sidecars.append({'file':f.name,'indices':log})
# Reconstruct every failed FT signature from existing actual-width latency and unchanged lane paths.
ports={p['id']:p for p in P['ports']};lanes={l['id']:l for l in P['lanes']};ft={}
for l in L:
 if not l['lane']:continue
 hp=[ports[i] for i in lanes[l['lane']]['ports']]
 for a,b in zip(hp,hp[1:]):ft.setdefault(a['dst']['part'],[]).append([a['dst']['bus'],b['src']['bus'],l['width']])
report={'status':'READY plan overlay, explicit variants; requires one coherent GEN/reset/clock regeneration and fresh strict binding',
 'variant_count':len(clones),'changes':changes,'instance_type_map':newmap,'type_keyed_indices':index_changes,'sidecars':sidecars,
 'ft_signatures':{p:sorted(ft.get(p,[])) for row in R['type_splits'] for g in row['variants'] for p in g},
 'rtl_cycles_changed':0,'leaf_interfaces_changed':False,'check_waiver':False,
 'note':'FT mismatches are actual width/presence differences, not bit permutation. No unused capacity is silently instantiated or erased.'}
(O/'type_variants_report.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({'variants':len(clones),'sidecars':[x['file'] for x in sidecars],'instance_type_map':newmap},indent=1))
