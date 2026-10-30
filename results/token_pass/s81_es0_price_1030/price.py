"""One S81 ES0 unlandedFT repair: forward coll lane57->58, reverse57 unchanged.
No plan/RTL mutation; use current event3 canonical plan and actual composer
maxima. Report the exact directed calendar delta separately from coarse model.
"""
import copy,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools/s81_dv/tokfunc')]
import compose_tok_ds as C
raw=subprocess.check_output(['git','-C',str(ROOT),'show','b19b88c9a78:physical/die_plan/s81/plan_h2_2249.json'])
sha=hashlib.sha256(raw).hexdigest();assert sha.startswith('39aa595f5bd3'),sha
p=json.loads(raw);old=p['latency']['lanes'];new=copy.deepcopy(old)
fwd='coll__s_7S_LP__lk_ES1';rev='coll__lk_ES1__s_7S_LP'
assert old[fwd]['cycles']==old[rev]['cycles']==57
new[fwd]['cycles']=58;new[fwd]['stations']+=1;new[fwd]['natural']+=1
get=lambda lat,pat:{k:v['cycles']for k,v in lat.items()if re.fullmatch(pat,k)}
terms=lambda lat:C._lane_terms(lambda pat:get(lat,pat))
a,b=terms(old),terms(new);assert a==b
cols=get(old,r'coll__.*');top=max(cols,key=cols.get)
r=dict(scope='ONE_DIRECTED_S81_ES0_REPAIR_PRICE_NOT_ADOPTED',source_plan_commit='b19b88c9a78',source_plan_sha256=sha,forward_lane=fwd,reverse_lane=rev,current_forward=old[fwd],candidate_forward=new[fwd],current_reverse=old[rev],candidate_reverse=new[rev],changed_lane_count=1,exact_forward_calendar_added_cycles=1,exact_reverse_calendar_added_cycles=0,wire_initiation_interval_changed=False,per_occurrence_forward_added_ps=833,current_circuit_max_coll_lane=top,current_circuit_max_coll_cycles=cols[top],candidate_circuit_max_coll_cycles=max(get(new,r'coll__.*').values()),composer_terms_current=a,composer_terms_candidate=b,composer_marginal_added_cycles=0,composer_marginal_tok_s_change=0,model_rows_carried_not_requalified=dict(MTP_tok_s=3655.3,AR_tok_s=1259.6),physical_START_or_token_qualified=False,source_rationale='ES0 eightflops leave seven r2r intervals min411um>405; candidate nineflops/eight intervals max399.251um with existing190um PHYshore detour',compiler_action='regenerate exact lane forward latency parameter and dependent TX/RX/calendar dates once in approved plan event; do not add1 to all S81 lanes or reverse direction',scope_limit='max-based composer does not prove exact ES1-specific schedule unchanged; every dependent directed crossing accrues1edge, actual occurrence count/critical-path binding must come from programme')
Path(sys.argv[1]).write_text(json.dumps(r,indent=2)+'\n');print({k:v['cycles']for k,v in a.items()});print('FORWARD57to58 REVERSE57 maxcoll',cols[top],'COMPOSER_DELTA0')
