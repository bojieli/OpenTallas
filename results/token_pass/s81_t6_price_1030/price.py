"""Two exact T6 FT4->5 branches; retain prior fixed flags and all other lanes."""
import argparse,copy,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
H=Path(__file__).resolve().parent;R=H.parents[2]
spec=importlib.util.spec_from_file_location('C',a.model_root/'tools/s81_dv/tokfunc/compose_tok_ds.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
raw=subprocess.check_output(['git','-C',str(R),'show','b19b88c9a78:physical/die_plan/s81/plan_h2_2249.json']);plan=json.loads(raw);old=plan['latency']['lanes'];new=copy.deepcopy(old)
for lane in('x_W2_out','x_W2_in'):
 new[lane]['cycles']+=1;new[lane]['stations']+=1;new[lane]['natural']+=1
assert (old['x_W2_out']['fixed'],new['x_W2_out']['fixed'],old['x_W2_in']['fixed'],new['x_W2_in']['fixed'])==(1,1,0,0)
get=lambda lat,pat:{k:v['cycles']for k,v in lat.items()if re.fullmatch(pat,k)}
A=C._lane_terms(lambda pat:get(old,pat));B=C._lane_terms(lambda pat:get(new,pat));assert A==B
rounds=[]
for group,base in[('in',1),('out',4)]:
 for k in range(3):
  pos=base+k;lane='x_W2_'+group;xo=sum(old[f'xo_W2_{group}_{suffix}']['cycles']for suffix in('a','b')[:k])
  fi=sorted(get(old,rf'fi_W2_p{pos}_r\d r\d'.replace(' ','')).values(),reverse=True)[:C.FRAME_FI_HOPS]
  rt=old[f'rt_W2_{group}_{k}']['cycles'];before=old[lane]['cycles']+xo+sum(fi)+rt
  rounds.append(dict(group=group,frame_position=pos,affected_lane=lane,current_round_edges=before,candidate_round_edges=before+1,forward_added_edges=1,return_lane=f'rt_W2_{group}_{k}',return_added_edges=0))
current_raw=json.loads((H/'t6_current_raw.json').read_text())
assert {r['lane']:r['bound_stages']for r in current_raw}=={'x_W2_out':59,'x_W2_in':24}
r=dict(scope='ONE_T6_INSTANCE_TWO_EXACT_FT_BRANCHES_NOT_ADOPTED',source_plan_commit='b19b88c9a78',source_plan_sha256=hashlib.sha256(raw).hexdigest(),
 physical_type='slice_station__t6__cl54a9ceeb',physical_instance='s_0S_x07',candidate_reason='4FF across1442.88um cannot meet broad30um endpoint admission; private5FF stage adds1 per declared FT',
 affected_lanes={k:dict(current=old[k],candidate=new[k],added_cycles=1,payload_bits=1104,epoch_bits=1)for k in('x_W2_out','x_W2_in')},
 changed_lanes=[k for k in old if old[k]!=new[k]],extra_FF=2210,extra_FF_formula='2*(1104payload+1epoch)',fixed_flags_preserved=dict(x_W2_out=1,x_W2_in=0),
 reverse_or_return_lane_changes=[],wire_II_change=0,per_occurrence_added_ps=833,
 actual_raw_bound=current_raw,affected_W2_field_rounds=rounds,
 composer_terms_current=A,composer_terms_candidate=B,composer_global_field_max=152,
 composer_dominating_lanes=A['field_round']['lanes'],composer_delta_edges=0,
 composer_reason='Both x_W2 branches are considered by field-round scan; exact W2 rounds gain1 but global E3/out/p6 maximum152 remains larger. This is scoped max domination, unlike omittedCW.',
 local_calendar_effect='Inputbranchuse+1 andoutputbranchuse+1, each independently. A trulyserialpathusingboth gains2; modelround usesone branch, so no automatic2/wholeoperation.',
 entry_dependency='PW/HLOAD/GAIN are VN/VS ring→XR→VP/VN, no 1104b matrix-band x_W2 crossing. Pinnedc092entry fences not retagged to newplan.',
 model_rates_carried_not_requalified=dict(MTP_tok_s=3655.3,AR_tok_s=1259.6),actual_token_rate_delta_qualified=False,
 candidate_global_START_or_programme_dates_qualified=False,source_RTL_or_plan_adopted=False,
 compiler_followup='Afterapprovedsource/gates publish, update only these two field input-arrival/calendar terms and all exposedW2consumers; preserveoutfixed1/infixed0 andunchangedreturns. No allT6/wholeS81+1.')
a.out.write_text(json.dumps(r,indent=2)+'\n');print('T6 out59to60 fixed1; in24to25 fixed0; FF+2210; max152unchanged; W2rounds',rounds)
