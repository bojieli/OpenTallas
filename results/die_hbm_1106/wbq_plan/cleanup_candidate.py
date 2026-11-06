import json,pathlib,collections,sys
r=pathlib.Path('/srv/opentallas-scratch2/claude/codex-hbm-wbq-plan');j=json.loads((r/'base/die_plan.json').read_text());led={}
for v in j['partition_types'].values():
 for s in v.get('ft_slots',[]):
  if s['in_face']==s['out_face']:s['turnaround']=True
# Restore exact six NE-side root endpoints from the pre-composition NE route, identical root origin/outline.
names={b['name'] for b in j['partition_types']['root']['buses']};add=json.loads((r/'codex_root_ne_buses.json').read_text());assert not names.intersection(b['name'] for b in add)
j['partition_types']['root']['buses']+=add;led['restored_root_buses']=add
laneports={p for l in j['lanes'] for p in l['ports']};dead=[p for p in j['ports'] if p['id'] not in laneports];assert {p['id'] for p in dead}=={'L114m_0','L114m_1','L114m_2','L114m_3'}
j['ports']=[p for p in j['ports'] if p['id'] in laneports];led['obsolete_orphan_ports']=dead
types={p['name']:p['type'] for p in j['partitions']};used=collections.defaultdict(set)
for p in j['ports']:
 for k in ['src','dst']:
  if p[k]['part'] in types:used[types[p[k]['part']]].add(p[k]['bus'])
removed=[]
for tn,t in j['partition_types'].items():
 ss=[]
 for s in t.get('ft_slots',[]):
  if not ({s['name']+'_i',s['name']+'_o'}&used[tn]):removed.append([tn,s])
  else:ss.append(s)
 if 'ft_slots' in t:t['ft_slots']=ss
led['obsolete_unused_ft_slots']=removed
j['partition_types']['PHY_NC']['buses']=[b for b in j['partition_types']['PHY_NC'].get('buses',[]) if b['name']!='L114m_o']
(r/'cleanup_candidate.json').write_text(json.dumps(j)+'\n');(r/'cleanup_ledger.json').write_text(json.dumps(led,indent=1)+'\n')
print('restored6rootbuses,removed4orphanports,removedFT',len(removed),flush=True)
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-hbm-1105/tools/die_plan');import schema
errs=schema.validate(j);print('schema',len(errs),errs[:40],flush=True)
(r/'cleanup_schema_errors.json').write_text(json.dumps(errs,indent=1)+'\n')
