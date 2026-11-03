#!/usr/bin/env python3
"""Prepare one inactive token source event from immutable Git objects; never elaborate/build."""
from pathlib import Path
import json,subprocess,hashlib,copy,csv
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
FROZEN='39f754dda07e9746c4850ea0814d48d134a6cf2a'
ACCEPTED='9db068b5458b7a20a548ab165aabc8dc6c077a30'
MANIFEST='physical/die_plan/s81/bind/asbuilt_source39_candidate_1102.json'
CANON='physical/die_plan/s81/bind/asbuilt_b178_coll_h2_2249.json'

def raw(rev,p):return subprocess.check_output(['git','show',rev+':'+p],cwd=ROOT)
def obj(rev,p):return json.loads(raw(rev,p))
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,d):p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')

def main():
 base=obj('a01e4dfb0',MANIFEST);accepted=obj(ACCEPTED,CANON);candidate=copy.deepcopy(base)
 add=[dict(module=n,param='INSTANCE')for n in ['dsfd_bf_col','dsfd_bf_front_roots','ot_s81sl_xgt_xo','ot_s81sl_xg']]
 candidate['instance_path_params']+=add
 candidate['base']='../../../..';candidate['map_file']='inputs/map_b178.json'
 candidate['instance_path_params_note']+=' DISABLED TOKEN SOURCE EVENT: gated BF/current XS4/legacy XS namespace rules only. Legacy XS capture0, XS4 capture1. No hardware/source epoch/provider or mission qualification inferred. Frozen SOURCE39 tool/reset185/179 context required; separate canonical186 excluded.'
 candidate['note']+=' INACTIVE namespace successor. Requires explicit plan/clock source selection, fresh emitted parameters/readset and truthful ROM/programme input before launch.'
 candidate_path=ROOT/'physical/die_plan/s81/bind/asbuilt_token_namespace_source39_candidate_1102.json';candidate_path.parent.mkdir(parents=True,exist_ok=True);candidate_path.write_text(json.dumps(candidate,indent=1)+'\n')
 assert candidate['defines']==base['defines']==accepted['defines']
 for k in ['hard_params','substitute_inst','core_profile','files','prefer','slang_parameterized_blackboxes']:
  assert candidate[k]==base[k],k
 overlays={p:'b12d983ca'for p in ['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg.sv','physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_xg.sv']}
 overlays['tools/s81/verilator_hier_params.py']='6430864fb'
 explicit_child=['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv']
 paths=set(candidate['files']+candidate['prefer']+candidate['netlist']+candidate['hard_params']+candidate.get('dead_input_proofs',[])+explicit_child+list(overlays))
 paths.add(candidate['clock_landing_table']);paths.add(candidate['map_file'] if candidate['map_file'].startswith('physical/') else 'physical/die_plan/s81/bind/'+candidate['map_file'])
 profile=obj('b70e77239','results/rtl/s81_provider_obligations_0150/profile_current_join.json')
 tree=subprocess.check_output(['git','ls-tree','-r','--name-only',FROZEN],cwd=ROOT,text=True).splitlines();available=set(tree)
 native=[x['path']for x in profile['BF_profile_100']['rows']if x['path']in available]
 paths.update(native)
 paths.update(p for p in tree if p.startswith('tools/die_plan/')or p.startswith('tools/s81_dv/layer_prog/')or p in ['tools/die_port_bind.py','tools/s81_dv/current_source_assembly.py','tools/s81_dv/adopt_eng_split.py'])
 index=[]
 for p in sorted(paths):
  rev=overlays.get(p,FROZEN)
  if p in candidate.get('dead_input_proofs',[]):rev='4e1f2ec72'
  b=raw(rev,p);row=dict(path=p,revision=rev,sha256=sha(b),bytes=len(b),source_event_overlay=p in overlays)
  if p in available:
   old=raw(FROZEN,p);row['frozen_sha256']=sha(old);row['changed_from_frozen']=old!=b
  index.append(row)
 write('source_readset.json',dict(scope='Exact selected source assembly, retained native BF child closure and frozen compiler/bind tools; emitted bound/Verilator readset remains pending fresh approved emission',files=index,explicit_child_files=explicit_child,late_emitted_readset_qualified=False))
 defs=dict(defines=candidate['defines'],added=[],removed=[],count=len(candidate['defines']),DSFD_PQ_HAS_BF_X2='No new global define; actual selected component source has no use, original dsfd_sp_pq_n derives it locally from existing STATIC_X2')
 write('defines.json',defs)
 write('manifest_delta.json',dict(base_revision='a01e4dfb0',base_manifest=MANIFEST,base_sha256=sha(raw('a01e4dfb0',MANIFEST)),candidate=str(candidate_path.relative_to(ROOT)),candidate_sha256=sha(candidate_path.read_bytes()),INSTANCE_rules_added=add,all_hardware_parameters_substitutions_and_defines_unchanged=True,path_normalization=dict(base='private root dot to repository manifest ../../../..',map_file='repository-relative map path to manifest-relative inputs/map_b178.json'),legacy_XS_added_cycles=0,XS4_added_cycles=1,deadproof='results/token_pass/s81_dead_inputs_2148/proof_closing_source39_1101.json'))
 current=obj(ACCEPTED,'physical/die_plan/s81/lat/s81_latency.json');optional=obj('ef9559e12','physical/die_plan/s81/lat/s81_latency.json');assert current['lanes']==optional['lanes']and current['groups']==optional['groups']
 write('plan_clock_options.json',dict(selected=None,accepted=dict(revision=ACCEPTED,plan_digest=current['plan_digest'],latency_sha256=sha(raw(ACCEPTED,'physical/die_plan/s81/lat/s81_latency.json'))),inactive_SOURCE39=dict(lineage='4290c9c99',actual_plan_commit='a484b1428',actual_latency_commit='ef9559e12',actual_asbuilt_commit='a01e4dfb0',export_commit='617dd5502',proof_commit='4e1f2ec72',corrected_reset_proof='6604994a6',plan_digest=optional['plan_digest'],plan_path='physical/die_plan/s81/plan_h2_2249.json',plan_sha256=sha(raw('a484b1428','physical/die_plan/s81/plan_h2_2249.json')),four_clock_tap_moves=True,refreshed_dead_declarations=36,added_die_control_FFs_clock_reset_data_loads=6,source_wrapper_reset_context='SOURCE39 frozen185/179; not canonical physical186',lanes=len(optional['lanes']),all_complete_lane_records_and_groups_identical_to_accepted=True,mission_cycle_delta=0),launch_allowed=False))
 old=ROOT/'results/rtl/s81_successor_reuse_0402';exclude={'s81p_dsdv_slice_iq_C___05Ft1_9','s81p_dsdv_slice_kv512_C___05Ft1_3'}
 rows=list(csv.DictReader((old/'conditional_reuse.tsv').open(),delimiter='\t'));kept=[r for r in rows if r['class_key']not in exclude];assert len(kept)==148
 with(OUT/'conditional_reuse_148.tsv').open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(kept)
 write('cache_classes.json',dict(old_snapshot_completed=380,BF_namespace_dirty=216,XS4_namespace_source_dirty=14,legacy_XG_namespace_dirty=2,conditional_matched_archive_wrapper_candidates=len(kept),actual_reused=0,missing_service_archives_at_snapshot=15,no_inherited_cache_changed=True,optional_SOURCE39_control_changes='both changed column implementations already within216 dirty BF classes; fresh identity comparison still mandatory',reuse_requirements=['fresh emitted exact source and parameters/native defines/tool identity','same generated mangled class key','matched existing wrapper+archive protectlib hash pair','no old generated source copied over newly emitted source']))
 write('image_and_programme_inputs.json',dict(BF_images=dict(existing_host='intel1',existing_dir='/srv/opentallas-scratch2/claude/codex-ds-bf-selectors-2200/romdir_bf_candidate',regular=11100,BF=912,total_aliases=12012,native_field_count=72,source_gate='4ba6f3753'),XS_programmes=dict(required_selectors=16,XS4_selectors=14,legacy_selectors=2,required_prefixed_images=112,current_mission_images_available=0,existing_old_assets_scope='two partial u_s0S programmes only; no cloning authority',selected_component_images=7,selected_component_gate='b70e77239 phase106 only, independent partial/date gate',fullmission_qualified=False),BF_programmes=dict(default_descriptor_count0_phases=1800,selected_phase106_overlay='2ed5e1d18',real_phase106_source_native_gate='b70e77239',mission_availability_qualified=False),real_source_epoch_qualified=False,native_provider_qualified=False,physical_clock_sampling_qualified=False))
 write('SOURCE_EVENT.json',dict(schema='opentallas.inactive_token_source_event.v1',enabled=False,source_clock_selection=None,frozen_source=FROZEN,accepted_comparison=ACCEPTED,candidate_manifest=str(candidate_path.relative_to(ROOT)),source_overlays=overlays,current_XS4_sha256=sha(raw(FROZEN,'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv')),explicit_child_files=explicit_child,native_simulator_helper='tools/s81/verilator_hier_params.py',hierarchy_option_policy='Apply helper to each fresh generated library and final-top args in NEW output paths; preserve genuine type files; no -f recursion guesses. Do not alter inherited args/caches.',source_state_or_cycle_delta_from_namespace=0,plan_clock_options='plan_clock_options.json',image_input_contract='image_and_programme_inputs.json',readset='source_readset.json',cache_classes='cache_classes.json',fresh_emission_launched=False,frontend_backend_launched=False,provider_flags_changed=False,physical_epoch_qualified=False,fullmission_programme_qualified=False,ready_scope='One concrete inactive source/manifest/tool/cache/image event for root review; not a buildable mission until actual112 XS images/programme and source/clock selection are supplied'))
 print('PREPARED_INACTIVE_EVENT',len(index),'source/tool files;148 conditional archive pairs;112 missionXS images held')
if __name__=='__main__':main()
