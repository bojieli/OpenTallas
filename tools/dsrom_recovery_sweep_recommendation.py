"""Matched three-owner sweep recommendation; never adopts incomplete service."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/dsrom_recovery_20261004/sweep_recommendation'
def build():
 paths=['results/rtl/dsrom_recovery_20261004/composition.json',
 'results/rtl/dsrom_recovery_20261004/levers/draft_sweep.json',
 'results/rtl/dsrom_recovery_20261004/field_spine_sensitivity.json',
 'results/rtl/dsrom_recovery_20261004/expert_placement_sweep/summary.json',
 'results/rtl/dsrom_expert_transport_20261005/measurement.json',
 'results/rtl/dsrom_expert_transport_20261005/native_raw32/measurement.json',
 'results/rtl/dsrom_recovery_20261004/draft/rlinks.json']
 base,draft,sensitivity,place,packed,raw,links=[json.loads((ROOT/p).read_text()) for p in paths]
 assert base['AR_us']==620.078 and base['MTP']['MTP_tok_s']==4462.1
 assert all(x['verdict']=='PASS_ENDPOINT_PAYLOAD_ONLY' for x in (packed,raw))
 hops=[('field_input_raw32',raw['hops']['native_field_input']),
       ('GU_output_raw32',packed['hops']['w2_input']),
       ('W2_input_raw32',raw['hops']['native_w2_input'])]
 transport={n:dict(payload_B=v['payload_B'],cycles=v['total_cycles'],us=v['total_cycles']/1200,
                   vendor_and_wire_already_included=True,loaded_service_qualified=False,
                   scope='Exact payload-size endpoint case only; semantic producer/consumer/context not measured') for n,v in hops}
 rows=[]
 for layer in place['layers']:
  for case in layer['summary']:
   rows.append(dict(layer=layer['layer'],groups=case['groups'],field_only_us=case['best_field_only_us'],
    canonical_field_only_us=layer['canonical_field_node_barrier_sum_us'],
    maximum_new_exposed_service_budget_to_beat_field_calendar_us=layer['canonical_field_node_barrier_sum_us']-case['best_field_only_us'],
    added_dies=case['added_dies'],added_die_body_mm2=case['added_die_body_mm2'],
    scoped_dominance=case['field_only_dominated_by'],complete_chain_us=None))
 return dict(schema='opentallas.recovery-three-sweep-recommendation.v1',
  inputs_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
  baseline=dict(AR_us=base['AR_us'],MTP={k:base['MTP'][k] for k in ('II_us','verify_us','draft_us','step_us','MTP_tok_s','tau')},physical_qualified=False),
  draft_cases=[{k:v[k] for k in ('name','draft_us','MTP_tok_s','added_dies','added_die_mm2')} for v in draft['variants'] if v['draft_us'] is not None],
  draft_decision='Keep EP5 reference for minimum latency; EP2/EP3 reduce area but slow this matched case. DP1 alone analytically dominates EP1 (+0 vs+4 dies,9.189us faster); both physically unqualified. Do not independently add sweep percentages.',
  hot_only_decision='Timing/packing NULL; frequency census cannot decide adoption.',
  phase_sensitivity=dict(source=paths[2],candidate_not_baseline=True,points=[dict(extra_edges=v['extra_stream_cycles_per_phase'],AR_us=v['AR_us'],MTP_tok_s=v['MTP']['MTP_tok_s']) for v in sensitivity['points']],
   decision='Up to8 phase edges costs3.120us inside historical PQ candidate projection; budget necessary spine repair, not a measured gain. Claude structural hold unchanged.'),
  raw32_idle_endpoint_terms=transport,packed_references_conditional_only=True,
  placement_cases=rows,
  recommendation='Discard fresh1-group L3 (same field calendar plus dies); fresh1-group L20 is slower even before links. Eliminate4/5 as field-only dominated by3. Only2/3/6 survive field-calendar screen; no whole-chain selection or all40 extrapolation.',
  promising_candidate_missing_measurement='One selected actual six-expert owner context must measure raw32 field-input broadcast/fanout, GU returns, native SU/quant and W2 dispatch, final return/ordered combine with real finite endpoint credits and surviving VM write visibility. Match exact group placement, full phase/address/context, all four rank slices, start through dependent consumer-ready; retain endpoint area/loaded clock/PG/route costs. Idle endpoint sums cannot replace this accepted service calendar.',
  additional_draft_missing_measurement=draft['unbound'],
  adoption=False,combined_candidate_AR_us=None,combined_candidate_MTP=None,
  full_die_hold=['Claude redesigned spine RTL+route','PQ verdict','hubPG0.088 IR fix'])
if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'model.json').write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
