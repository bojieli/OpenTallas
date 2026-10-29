import sys,json,copy,hashlib
from pathlib import Path
w=Path('/srv/opentallas-scratch/claude/wt/codex-tokens-hbm-ready-1028');sys.path.insert(0,str(w/'tools/hbm_next'))
import bound_from_plan as B
import four_role_calendar as C
pf=Path('/srv/opentallas-scratch/claude/codex-hbm-token-1028/c25c_candidate1a/die_plan.json');raw=pf.read_bytes();plan=json.loads(raw);sha=hashlib.sha256(raw).hexdigest();commit='abe1936f353f83ffc73175ee0d3652712a50f1e3'
sidep='/srv/opentallas-scratch/claude/wt/codex-hbm-1028/results/die_hbm_1027/hbm10/c25c_candidate1a/c25c_side.json';side=json.load(open(sidep));rtl=json.load(open(w/'results/tok_hbm_6_1028/rtl_constants_hwi5.json'))
legs,missing=B.build(plan,commit,rtl,B.side_legs(side,sidep,sha));assert not missing,missing
bound=dict(source_plan_commit=commit,plan_sha256=sha,legs_exclude_tree_nodes=True,legs=legs,rtl=rtl,missing=[])
raw_host=bound['legs'].pop('host_to_provider')
bound.update(missing=['host_to_provider regional CAK extra UNKNOWN; source LOADcapture31 is not a qualified clock-aligned leg'],deferred_host_to_provider=raw_host,qualification='MISSING_CLOCK_EXTRA',host_clock_extra_cycles=None)
jobs=json.load(open('/srv/opentallas-scratch/claude/codex-hbm-token-1028/recovered_jobs_a122/jobs.json'));service=json.load(open(w/'results/tok_hbm_2_1028/service_segments.json'))
strict,problems=C.compile_calendar(jobs,bound,service,schedule_rgap=True);assert strict is None and any('host_to_provider' in m for m in problems)
raw_bound=copy.deepcopy(bound);raw_bound['legs']['host_to_provider']=raw_host
cal,diagnostic_problems=C.compile_calendar(jobs,raw_bound,service,schedule_rgap=True);assert cal and not diagnostic_problems,diagnostic_problems
cal.pop('start_authority',None)
for key in ('provider_start_cycle','provider_preload_complete_cycle','provider_cfg_commit_cycle'):cal.pop(key,None)
cal['scope']='RAW_SOURCE_ONLY; NO CLOCK EXTRA OR START AUTHORITY'
cal['schema']='opentallas.hbm.raw_source_calendar_diagnostic.v1'
price=dict(schema='opentallas.hbm.c25c_source_price.v1',qualification='RAW_SOURCE_ONLY',plan_commit=commit,plan_sha256=sha,image_sha256=jobs['image_sha256'],regional_clock_extra_cycles=None,qualified_calendar_missing=problems,source_host_load_capture31=raw_host,
 station_legs={k:v['cycles'] for k,v in legs.items()},diagnostic_root_config=cal['root_config'],records=len(cal['records']),pre_records=sum(r['op']!='HC_POST' for r in cal['records']),rgap_values=sorted(set(r.get('rgap_override',{}).get('value',0) for r in cal['records'] if r['op']!='HC_POST')),added_service_cycles=sum(r.get('rgap_override',{}).get('added_service_cycles',0) for r in cal['records']),
 note='No START authority or qualified calendar emitted; actual source closure and regional clock extra remain required. Per-record FUSED component price only, no full token price. HC NQ2 non-FUSED reduction price is separate.')
o=w/'results/tok_hbm_codex_1028/c25c_candidate1a'
for n,d in [('bound.MISSING.json',bound),('raw_source_diagnostic.json',cal),('price.json',price)]: (o/n).write_text(json.dumps(d,indent=1)+'\n')
print(json.dumps(price,indent=1)[:3500])
