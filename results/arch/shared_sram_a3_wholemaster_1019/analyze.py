import json,re,collections,hashlib,gzip
from pathlib import Path
P=Path(__file__).resolve().parent;N=P/'native';inv=json.loads(gzip.decompress((P/'inventory.json.gz').read_bytes()))
def markers(path):
 out=[]
 for chunk in path.read_text().split('violation type: ')[1:]:
  mt=re.search(r'bbox = \(([-.\d]+), ([-.\d]+)\) - \(([-.\d]+), ([-.\d]+)\) on Layer (\S+)',chunk);assert mt
  out.append(dict(type=chunk.splitlines()[0],nets=re.findall(r'net:(\S+)',chunk.splitlines()[1]),bbox_nm=[round(float(v)*1000)for v in mt.groups()[:4]],layer=mt.group(5)))
 return out
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])and min(a[3],b[3])>max(a[1],b[1])
res={'status':'NATIVE_COVERED_RULE_FULLMASTER_RESULT_ONLY','geometry_commit':'c634d1540','model_sha256':hashlib.sha256((P/'input/model.json').read_bytes()).hexdigest(),'families':{},'controls':[]}
for fam in ['qwen','sc2']:
 d=N/fam;full=markers(d/'all_markers.rpt');roi=markers(d/'roi_00.rpt');assert full==roi
 nets=[]
 for f in sorted(d.glob('odb_net_*.json')):
  n=json.loads(f.read_text());assert n['exact_box_multiset']and set(n['wire_type'])=={'ROUTED'}and n['sig_type']=='SIGNAL';boxes=n['actual_boxes'];edges={i:set()for i in range(len(boxes))}
  for i,(la,a)in enumerate(boxes):
   for j,(lb,b)in enumerate(boxes[i+1:],i+1):
    ok=la==lb and overlap(a,b)
    if (la=='V4'and lb in ['M4','M5'])or(lb=='V4'and la in ['M4','M5']):
     cut=a if la=='V4'else b;metal=b if la=='V4'else a;ok=metal[0]<=cut[0]and metal[1]<=cut[1]and metal[2]>=cut[2]and metal[3]>=cut[3]
    if ok:edges[i].add(j);edges[j].add(i)
  unseen=set(edges);components=[]
  while unseen:
   todo=[unseen.pop()];part=set(todo)
   while todo:
    for j in edges[todo.pop()]-part:part.add(j);unseen.discard(j);todo.append(j)
   components.append(sorted(part))
  if n['source_net']not in ['VDD','VSS']:assert len(components)==1
  nets.append(dict(source_net=n['source_net'],actual_box_count=len(boxes),component_count=len(components),components=components))
 (d/'independent_native_connectivity.json').write_text(json.dumps(nets,indent=2)+'\n')
 expected=inv['families'][fam];assert len(nets)==expected['counts']['signal_nets']+2
 res['families'][fam]=dict(global_markers=full,global_marker_count=len(full),global_types=dict(collections.Counter(x['type']for x in full)),full_outline_roi_equal_global=True,native_net_count=len(nets),all_actual_signal_components_one=True,PG_components={n['source_net']:n['component_count']for n in nets if n['source_net']in ['VDD','VSS']},exact_native_box_count=sum(n['actual_box_count']for n in nets),OBS_retained_reservations=expected['conditional_OBS'],native_resource=(d/'resources.time').read_text())
for i,c in enumerate(inv['original_controls']):
 mm=markers(N/'controls'/f'roi_{i:02d}.rpt');res['controls'].append(dict(name=c['name'],markers=mm,types=dict(collections.Counter(x['type']for x in mm)),model_components=len(c['independent_geometry_components'])))
assert res['controls'][0]['types']=={}
assert res['controls'][1]['types']=={'Rect Only':2}
assert res['controls'][2]['types']=={'Lef58EolKeepOut':2,'Metal Spacing':1}
assert res['controls'][3]['types']=={'Lef58EolKeepOut':6,'Metal Spacing':1,'Lef58SpacingEndOfLine':1,'Min Area':1}
assert res['controls'][3]['model_components']==2
res['controls_global_markers']=markers(N/'controls/all_markers.rpt');assert len(res['controls_global_markers'])==14
im=json.loads((N/'image_inspect.json').read_text())[0];assert im['Id']=='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29';assert(N/'binary_sha256.txt').read_text().split()[0]=='21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846'
res['provenance']={'host':(N/'host.txt').read_text().strip(),'observed_at':(N/'observed_at.txt').read_text().strip(),'image_Id':im['Id'],'RepoDigests':im['RepoDigests'],'binary':(N/'binary_sha256.txt').read_text().strip(),'disk':(N/'disk.bytes').read_text().strip()}
res['HOLD']=['Native non-ORTH WIDTHTABLE import/binding and track coverage gaps.','All 121 own PG/OBS intersections remain unresolved; no AP or PG continuity.','PG disconnected, SIGNAL visibility diagnostic only; no fed supply or core/contact implementation.','No transistor-grid, source phase/reset/K/first-use, timing/RC, B/C or production-view qualification.']
(P/'analysis.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:{a:b for a,b in v.items()if a in ['global_marker_count','global_types','native_net_count','PG_components','exact_native_box_count']}for k,v in res['families'].items()},indent=2));print(res['provenance'])
