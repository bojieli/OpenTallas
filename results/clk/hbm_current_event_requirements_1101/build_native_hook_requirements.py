from pathlib import Path
import json,sys,collections
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-contacts-1101/tools/die_plan')
import schema as S,gen_phys as G
r=Path(__file__).resolve().parent;p=S.Plan(S.load(r/'current_C11G_plan.json'));tree=json.load(open(r/'C12e_tree.json'));prior={(t['part'],t['tap']):t for t in tree['taps']};rows=[]
for side in ['NW','NE']:
 part=side+'_hub';pa=p.parts[part];tn=pa['type'];t=p.types[tn];pilot=json.load(open(r/'halo_regen'/f'{side}.json'));g=pilot['geom'];snap={n:[x,y]for n,x,y in G.core_tap_pins(p,tn)};owners={c['inst']:c for c in t['hard_cores']}
 for port,ux,uy,tp in S.core_taps(p,tn):
  owner=next((n for n in sorted(owners,key=len,reverse=True)if tp['name']==n or tp['name'].startswith(n+'.')),None);core=owners.get(owner,{})
  suffix=tp['name'][len(owner)+1:]if owner and tp['name'].startswith(owner+'.')else None
  key='K_'+port;early='L_X_'+port;topology='mesh_native_hook'if key in g['core_loads']else'early_tree_native_hook'
  assert topology=='mesh_native_hook'or early in pilot['cells'],(part,port)
  target=list(p.to_die(part,snap[port]));old=prior[(part,port)]['xy'];delta=round(sum(abs(a-b)for a,b in zip(target,old)),6)
  rows.append(dict(part=part,type=tn,port=port,topology=topology,planned_endpoint_name=tp['name'],owner_instance=owner,owner_module=core.get('module'),declared_child_clock_suffix=suffix,child_origin_um=core.get('origin_um'),child_outline_um=core.get('outline_um'),child_orient=core.get('orient','R0'),part_orient=pa['orient'],planned_pin_file=core.get('pins_file'),obs_max=core.get('obs_max'),current_unsnapped_type_target_um=[ux,uy],current_consumed_type_target_um=snap[port],current_consumed_global_target_um=target,prototype_old_tree_global_target_um=old,old_tree_target_delta_um=delta,prototype_mesh_node=g.get('tap_node',{}).get(key),early_source_driver=next((v['drv']for v in pilot['nets'].values()if v['kind']=='tree'and early in v['loads']),None),planned_internal_clock_ps={'TT':tp.get('insertion_ps'),'FF':tp.get('insertion_ff_ps')},planned_entry_is_not_native_view='NOT at the entry'in tp.get('note',''),current_native_view_contract_status='UNSUPPLIED',actual_native_pin_map=None,current_clock_source_node=None))
counts=collections.Counter((x['part'],x['topology'])for x in rows)
requirements=dict(scope='Exact current G hub child-clock source/view requirements; no old tree identity/phase adoption. E/G hardcores unchanged but old C12e target endpoints may differ.',current_plan_sha256='e0638225f8b38653671aa3a59d11023c566182278d7256359f8f5b221b34c492',counts={':'.join(k):v for k,v in counts.items()},native_contract_to_supply=['Exact current selected RTL source/parameters or immutable recipe, functional qualification and any outer shell cycles priced','Actual LEF master/outline plus typed Liberty TT+FF clock:true native input pin(s), capacitances, min/max internal clock path and related-pair contract','Actual native instance/pin mapping from planned owner/clock port; physical pin rectangle/layer at current child and partition orientations','If using planned in-core entry island, actual child source/LEF consumption of reservation and physical upper/lower-metal hookup; no center-island alias','One newly generated current clock graph node/net/cell/pin to this actual child pin; routed RCX connectivity and current TT/FF arrival/variation'],rows=rows,old_tree_endpoint_mismatches=[dict(part=x['part'],port=x['port'],owner=x['owner_instance'],delta_um=x['old_tree_target_delta_um'])for x in rows if x['old_tree_target_delta_um']>1e-6],release_qualified=False)
groups=collections.defaultdict(list)
for row in rows:
 groups[(row['owner_module'],tuple(round(v,6)for v in row['child_outline_um']),row['planned_pin_file'])].append(row)
requirements['contract_families']=[dict(module=module,outline_um=list(outline),planned_pin_file=pinfile,instances=[dict(part=row['part'],owner=row['owner_instance'],clock_port=row['port'])for row in members],status='UNSUPPLIED')for(module,outline,pinfile),members in sorted(groups.items())]
requirements['contract_family_count']=len(groups)
requirements['native_module_count']=len(set(x['owner_module']for x in rows))
(r/'current_G_native_hook_requirements.json').write_text(json.dumps(requirements,indent=2));print('counts',requirements['counts']);print('unresolvedowners',[x['planned_endpoint_name']for x in rows if not x['owner_instance']]);print('oldendpointmismatches',requirements['old_tree_endpoint_mismatches'])
