"""Price only the selected GUNIT CW IN leg72->73; never adopt source/dates."""
import argparse,copy,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
model=a.model_root/'tools/s81_dv/tokfunc/compose_tok_ds.py';spec=importlib.util.spec_from_file_location('cw_compose',model);C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
raw=subprocess.check_output(['git','-C',str(ROOT),'show','b19b88c9a78:physical/die_plan/s81/plan_h2_2249.json'])
plan=json.loads(raw);old=plan['latency']['lanes'];new=copy.deepcopy(old);lane='unit__seqhost__gunit'
owner=json.loads((HERE/'owner_lane_price.json').read_text());assert len(owner)==1 and owner[0]['lane']==lane
for k,v in owner[0]['old'].items():assert old[lane][k]==v,(k,v,old[lane][k])
new[lane].update(owner[0]['candidate'])
get=lambda lat,pat:{k:v['cycles']for k,v in lat.items()if re.fullmatch(pat,k)}
terms=lambda lat:C._lane_terms(lambda pat:get(lat,pat))
x,y=terms(old),terms(new);assert x==y
assert not any(lane in v['lanes']for v in x.values())
bind=json.loads((HERE/'cw_current_raw.json').read_text());b=bind['bus'];l=bind['landing']
assert b['width']==265 and b['planned_width']==267 and b['bound_stages']==72
assert sum(sum(hi-lo+1 for lo,hi in m['sink_bits'])for m in l['members'])==265
assert {m['bound_stages']for m in l['members']}=={72}
exposures=[]
for name in('A','B'):
 base=a.model_root/'results/token_pass/pipeline_native_s81_1021/inputs'/name
 cal=json.loads((base/'prog/calendar.json').read_text());manifest=json.loads((base/'manifest.json').read_text());words=[int(s,16)for s in(base/'prog/host_boot.memh').read_text().split()]
 timed=[r for r in cal['rows']if r['engine']==2]
 exposures.append(dict(programme=name,scope='actual historical native compiler bytes; not current source/date qualification',
   die_sha256=manifest['die_v_sha256'],GUNIT_timed_rows=len(timed),GUNIT_issue_slots=[r['issue']for r in timed],
   HOST_CSR14_CW_configuration_words=sum(((w>>1)&255)==0x14 for w in words),
   marginal_admission_per_affected_crossing_edges=1,wire_II_change=0))
# Actual current entry helper emits no GUNIT engine or CW CSR words.
entry_exposure=json.loads((HERE/'entry_CW_exposure.json').read_text())
assert entry_exposure['pages']==40 and entry_exposure['HOST_words']==16715 and entry_exposure['HOST_CSR14_words']==entry_exposure['GUNIT_timed_rows']==0
r=dict(scope='ONE_FORWARD_GUNIT_CW_R25_SOURCE_PRICE_NOT_ADOPTED',S81_source_event='117e37566c',canonical_plan_source='b19b88c9a78',canonical_plan_sha256=hashlib.sha256(raw).hexdigest(),
 lane=lane,current=old[lane],candidate=new[lane],changed_lanes=[lane],reverse_or_other_lanes_changed=[],
 actual_payload_bits=265,epoch_bit_separate=True,actual_wrapper_bus_width=266,declared_lane_capacity=267,
 exact_CW_mapping=l['members'],current_bound_target='u_gunit.u_l2.cw_*',current_target_age_from_seqhost_CW_output=72,candidate_target_age_from_seqhost_CW_output=73,
 selected_seqhost_command_to_CW_output_edges=3,current_native_issue_to_GUNIT_CW_input_edges=75,candidate_native_issue_to_GUNIT_CW_input_edges=76,
 marginal_CW_admission_edges=1,marginal_CW_admission_ps=833,marginal_wire_II_edges=0,
 physical_station=dict(kind='one IN station',payload_W=265,site_um=[1440.08,328.32]),
 composer_source_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),composer_terms_current=x,composer_terms_candidate=y,composer_CW_lane_consumed=False,
 composer_returned_delta_edges=0,rate_marginal_qualified=False,rate_delta_reason='CW is absent from this composer; unchanged terms are an omission, not proof of unchanged rate',
 carried_model_not_requalified=dict(MTP_tok_s=3655.3,AR_tok_s=1259.6),caller_exposures=exposures,
 current_entry_native_byte_counts=entry_exposure,current_entry_PW_HLOAD_GAIN_CW_exposure=dict(GUNIT_engine_rows=0,HOST_CSR14_words=0,actual_commands='3920TARGET5+80HLOAD+80GAIN use VN/VS only; KIT/END/MU use separate paths',admission_or_store_fence_delta_from_this_leg=0,qualification='component dependency exclusion only; entryboundc092 cohort not retagged to R25'),
 bootstrap_effect='every affected CW beat reaches Gunit1edge later; last-CW-ready may shift1 once per batch. No extra beat interval, no reverse/wholeS81/BOOT-span increment inferred.',
 timed_GUNIT_effect='if issuer dates unchanged, job admission and receiver-relative consumers gain1edge per affected dependency. Rebook precise Gunit data/calendar consumers; postedACK remains local issue+5.',
 current_physical_START_or_global_programme_dates_qualified=False,old_BoundDie_cohort_preserved=True,
 pending='S81 owner owns exact privateINsource/miter/bind/gates and approvedplan publication; no silent source/calendar adoption')
a.out.write_text(json.dumps(r,indent=2)+'\n');print('CW72to73 ADMIT75to76 actual265bits ENTRY_CW0 COMPOSER_UNCOVERED',exposures)
