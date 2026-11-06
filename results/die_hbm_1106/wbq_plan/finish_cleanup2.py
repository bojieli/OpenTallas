import json,pathlib,collections,sys
r=pathlib.Path('/srv/opentallas-scratch2/claude/codex-hbm-wbq-plan');j=json.loads((r/'cleanup_candidate.json').read_text());led=json.loads((r/'cleanup_ledger.json').read_text())
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-hbm-1105/tools/die_plan');import schema
P=schema.Plan(j);uses=collections.Counter(p['type'] for p in j['partitions']);used=collections.defaultdict(set)
for p in j['ports']:
 for side in ['src','dst']:
  v=p[side]
  if v['part'] in P.parts:used[P.parts[v['part']]['type']].add(v['bus'])
removed=[]
for tn,t in j['partition_types'].items():
 if not uses[tn]:continue
 keep=[]
 for b in t.get('buses',[]):
  if b['name'] not in used[tn]:removed.append([tn,b])
  else:keep.append(b)
 if 'buses' in t:t['buses']=keep
led['obsolete_unreferenced_regular_buses']=removed
fixes={};portfix=[]
for p in j['ports']:
 ga=P.port_geom_from(p,'src');gb=P.port_geom_from(p,'dst')
 if not ga or not gb:continue
 if ga[3]==gb[3]:continue
 assert ga[:3]==gb[:3],(p['id'],ga,gb)
 ta=P.parts[p['src']['part']]['type'];tb=P.parts[p['dst']['part']]['type']
 # Preserve the shared hardened-type local ordering across R0/MY replicas.
 desired=gb[3] if uses[tb]>1 else ga[3]
 assert not (uses[ta]>1 and uses[tb]>1),(p['id'],ta,tb)
 if 'order' in p and p['order']!=desired:portfix.append([p['id'],p['order'],desired]);p['order']=desired
 for side,g in [('src',ga),('dst',gb)]:
  if g[3]==desired:continue
  ep=p[side];pn=ep['part'];bn=ep['bus'];tn=P.parts[pn]['type'];assert uses[tn]==1,(p['id'],tn)
  t=j['partition_types'][tn];local=P._type_geom(pn,bn);orient=P.parts[pn].get('orient','R0')
  flip=(local[0] in 'EW' and orient in ('MX','R180')) or (local[0] in 'NS' and orient in ('MY','R180'))
  order=('lsb_high' if desired=='lsb_low' else 'lsb_low') if flip else desired
  target=next((b for b in t.get('buses',[]) if b['name']==bn),None);field='order'
  if target is None:
   target=next(s for s in t.get('ft_slots',[]) if bn in (s['name']+'_i',s['name']+'_o'));field='in_order' if bn.endswith('_i') else 'out_order'
  key=(tn,bn,field);assert key not in fixes or fixes[key]['new']==order,key
  fixes[key]=dict(type=tn,bus=bn,field=field,old=target.get(field,target.get('order','lsb_low')),new=order,port=p['id'],reason='match peer physical bit order, preserving shared-type local order')
  target[field]=order
led['physical_order_repairs']=list(fixes.values());led['explicit_port_order_repairs']=portfix
lanes={l['id'] for l in j['lanes']};groups=[];oldgroups=[]
for g in j.get('latency_groups',[]):
 if g['name']=='L12m_word':
  assert g['lanes']==['L12m','L12ms'];g['lanes']=['L5037','L12ms'];g['note']+=' | C route renamed1980bit root->NEhub leg L12m toL5037; 1016bitL12ms unchanged'
 elif g['name']=='L6m_word':
  assert not set(g['lanes'])&lanes;oldgroups.append(g);continue
 groups.append(g)
j['latency_groups']=groups;led['obsolete_latency_groups']=oldgroups;led['lane_aliases']={'L12m':'L5037'}
(r/'cleanup_candidate_final.json').write_text(json.dumps(j)+'\n');(r/'cleanup_ledger_final.json').write_text(json.dumps(led,indent=1)+'\n')
print('remove regular',len(removed),'typeorder fields',len(fixes),'portorder',len(portfix),flush=True)
errs=schema.validate(j);print('schema',len(errs),errs[:30],flush=True);(r/'cleanup_final_errors.json').write_text(json.dumps(errs,indent=1)+'\n')
