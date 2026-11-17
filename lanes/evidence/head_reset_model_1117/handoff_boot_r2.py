from pathlib import Path
import json,sys,hashlib
L=Path('/srv/opentallas-scratch2/claude/head-die-r');O=L/'reset_feasibility_r4_1117';f=L/'prep21z20NF15c/prep/source_plan.json';P=json.load(f.open());sys.path.insert(0,str(L/'nf15e_e7/code/tools/die_plan'));import schema as S,reset_tree as RT
relocated=[]
for tn,t in P['partition_types'].items():
 nd=t.get('clock',{}).get('native_domains',{})
 if nd.get('census_file') and not Path(nd['census_file']).exists():
  q=f.parent/'native_domains'/Path(nd['census_file']).name
  assert q.exists(),q
  cj=json.load(q.open());assert cj.get('source_odb_sha256')==nd.get('source_odb_sha256'),(tn,'census source identity')
  relocated.append(dict(type=tn,old=nd['census_file'],new=str(q),file_sha256=hashlib.sha256(q.read_bytes()).hexdigest()));nd['census_file']=str(q)
w=RT.wf_plan(S.Plan(P,str(f)));rows=json.load((O/'reverse_phase_clockfork_provisional.json').open())['rows'];added={x['part'] for x in rows};parents={p:r['parent'] for p,r in w['parts'].items()};memo={}
def delta(p):
 if p not in memo:memo[p]=(delta(parents[p]) if parents[p] else 0)+int(p in added)
 return memo[p]
for p in parents:delta(p)
oldmax=max(r['release'] for r in w['parts'].values());newmax=max(r['release']+memo[p] for p,r in w['parts'].items());ca=json.load((L/'prep21z20NF15c/prep/source_sidecar.json').open())['count_aligned'];base=ca['root_settle_cycles'];maxdelta=max(memo.values());changes=[dict(part=p,type=w['parts'][p]['type'],old_release_cycles=w['parts'][p]['release'],new_release_cycles=w['parts'][p]['release']+memo[p],delta_cycles=memo[p],entry_handoff_added=p in added) for p in sorted(parents) if memo[p]]
r=dict(schema='opentallas.reset_handoff_boot_price.v1',status='MODEL_ONLY_REQUIRES_SOURCE_DEPTH_GATE',scope='13 receiver phase-class clones only, each adds1 synchronous pin entry handoff stage for reset AND START. Existing raw/run relay topology andcountdepth retained. Old NF15c graph; fresh NF15e reprice required.',relocated_census=relocated,source_plan_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),local_handoff_instances=sorted(added),old_wavefront_max_release=oldmax,new_wavefront_max_release=newmax,max_path_added_boot_cycles=maxdelta,changed_parts=len(changes),old_ca_root_settle_cycles=base,proposed_ca_root_settle_cycles=base+maxdelta,root_settle_policy='Increase by max extra raw-wavefront path cost, preserving every old relative boot clearance even if the root raw provider also moves later; no reduced hold/reset obligation.',explicit_start_offsets='Reset AND START use same wavefront: compiler per-part mission-admission offsets increase by listed delta. Root must not issue arithmetic before updated release/calendar.',count_aligned_J_K='Conditional: origin sample clocks and forward START physical path unchanged => J and origin differences unchanged after common rootsettle delay; recompute actual post-fork source/destination phase interval and run ordinary count-align gate. A boundary crossing/changed J requires new K/depth/strap rows, never assume old K.',added_arithmetic_cycles=0,added_reset_start_ff=26,shared_phasefork_buf4=390,added_area_um2=13*(30*.10206+2*.2916),changes=changes)
(O/'handoff_boot_price_provisional_r2.json').write_text(json.dumps(r,indent=1)+'\n');print({k:r[k] for k in ['old_wavefront_max_release','new_wavefront_max_release','max_path_added_boot_cycles','changed_parts','old_ca_root_settle_cycles','proposed_ca_root_settle_cycles','added_reset_start_ff','shared_phasefork_buf4','added_area_um2']})
