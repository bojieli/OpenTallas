from pathlib import Path
import sys,json,re,copy
b=Path('/srv/opentallas-scratch2/claude/codex-fe3-control-0336');w=Path('/srv/opentallas-scratch2/claude/wt/codex-fe3-control-0336');sys.path.insert(0,str(w/'tools/die_plan'))
import clock_landings as C,count_align_bind as CAB,schema as S,gen_rtl as G
base=Path('/srv/opentallas-scratch2/claude/codex-collft-0336/plan');p=json.load((base/'plan_qc46.json').open());table=json.load((base/'sidecar_qc33.json').open());tn='sle_fe_v3';old=C.Landings(p,table,require_geometry=False)
model=json.load((b/'reader_phase1_minreach_corrected_rawregional_writer3.json').open());poses=model['results']['30']['positions'];q=copy.deepcopy(p);t=q['partition_types'][tn];clock=t.setdefault('clock',{});t['landing_relay_start_copy']=True
reader={bus:dict(stages=[dict(xy_um=poses['MODEL_reader_start_u_bound.u_cland_'+bus],raw_reset='cland_reset_cws3_i')]) for bus in old.by_type[tn]['inputs']}
writer={}
for bus in old.by_type[tn]['outputs']:
 oldname='u_bound.u_cland_fstart_'+bus+'/q$_SDFF_PN0_'
 writer[bus]=dict(stages=[dict(xy_um=poses[prefix+oldname],raw_reset='cland_reset_cws3_i') for prefix in ['MODEL_writer_bridge_','MODEL_writer_bridge2_']])
clock['landing_reader_start']=dict(depth=1,branches=reader,origin_rect_um=[29.984,667.44,34.304,671.76]);clock['landing_writer_start']=dict(depth=3,reuse_relay_origin=True,branches=writer)
raw=[]
for br in model['literal_raw_branches']:
 c=br['consumer']
 if c.startswith('u_bound.u_cland_rstart_rx/'):name='origin';roles=['origin']
 elif c.startswith('MODEL_reader_start_u_bound.u_cland_'):
  bus=c.split('MODEL_reader_start_u_bound.u_cland_')[1];name='reader_'+bus;roles=['reader:'+bus+':0']
 elif c.startswith('MODEL_writer_bridge2_') or c.startswith('MODEL_writer_bridge_'):
  second=c.startswith('MODEL_writer_bridge2_');bus=re.search(r'u_cland_fstart_(\w+)/',c)[1];i=int(second);name='writer_'+bus+'_'+str(i);roles=['writer:'+bus+':'+str(i)]+(['fstart:'+bus] if second else [])
 else:raise ValueError(c)
 stages=[]
 for st in br['stages']:
  orig=st['original'];m=re.search(r'u_rrl_(\d+)/',orig);net='rst_rl_'+m[1] if m else 'cland_reset_cws3_i'
  stages.append(dict(original=net,xy_um=poses[st['copy']]))
 raw.append(dict(name=name,base='rst_root_n',stages=stages,consumers=roles))
clock['landing_raw_branches']=raw
new=C.Landings(q,table,require_geometry=False);nr={r['port']:r for r in new.rows};phase=[]
for r in old.rows:
 if r['src']=='sl_E5_fe' or r['dst']=='sl_E5_fe':
  a=nr[r['port']];assert a['added_cycles']==r['added_cycles'];assert not a['start_tree_port'];phase.append(dict(port=r['port'],source=r['src'],destination=r['dst'],old_K=r['ring_k'],new_K=a['ring_k'],reader_phase=a.get('reader_start_depth',0),writer_phase=a.get('writer_start_depth',0),production_cycles_added=0))
out=b/'source_candidate';out.mkdir(exist_ok=True);(out/'plan.json').write_text(json.dumps(q,indent=2)+'\n');(out/'config.json').write_text(json.dumps(dict(type=tn,clock=clock,landing_relay_start_copy=True),indent=2)+'\n');(out/'per_port_phase.json').write_text(json.dumps(dict(rows=phase,cold_aggregate='UNKNOWN',source='actual shared CAB phase/K functions, not patched ties',straps=CAB.strap_ties(table['count_aligned'],q)),indent=2)+'\n')
# Actual plan/reset/CA/status generator, without rebinding the production arithmetic leaf.
P=S.Plan(p);epochs={(tn,x['name']):True for x in p['partition_types'][tn].get('buses',[])}
text=G.wrapper(P,tn,epochs,rtl_root=None);(out/'unlanded_plan_wrapper.sv').write_text(text)
a=old.type_rtl(tn,text);z=new.type_rtl(tn,text);(out/'baseline.sv').write_text(a);(out/'candidate.sv').write_text(z);(out/'placements.json').write_text(json.dumps(new.reset_placements[tn],indent=2)+'\n')
counts={k:len(re.findall(r'\bot_dp_'+pat+r'\s+u_cland_'+pref,z)) for k,pat,pref in [('raw','rrelay','raw_'),('reader','landing_relay','reader_start_'),('writer','landing_relay','writer_start_')]}
assert counts==dict(raw=60,reader=5,writer=6),counts;(out/'emitted_counts.json').write_text(json.dumps(dict(counts=counts,total_new_ff=sum(counts.values()),status='EMITTED_SOURCE_ONLY; native retained count and full mechanism proof still owed'),indent=2)+'\n');print('EMITTED',counts,'PHASES',phase)
