"""Compose exact actual all-FF provider geometry and native reset source into ONE plan."""
import copy,json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251')
T=Path('/srv/opentallas-scratch2/claude/codex-provider-import-1029/proposal_qc_wave2_compact')
Q=Path('/srv/opentallas-scratch2/claude/codex-qc-1029/physical_event')
O=R/'native_source_candidate2';O.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'src_reset_contract/tools/die_plan'))
import schema as S,start_provider_plan as SP,landing_contract as LC
raw=json.load(open(Q/'plan_start_native_h800.json'))
stages=json.load(open(R/'reset_wave2/emitted/start_stages.json'))
ff=json.load(open(T/'stage_actual_ff_boxes.json'))['stages']
for st in stages['stages']:
 b=ff[st['id']]
 if b['all_ff_count']!=st['flops']:raise ValueError('actual FF census differs from source '+st['id'])
 st['emitted_ff_row_rect_um']=st['rect_um'];st['rect_um']=b['all_ff_bbox_um']
 st['geometry_source']='complete actual mapped FF bodies at legal proposal coordinates; not imported yet'
# All real boundary sinks are mapped from emitted actual dst_part, never region-name guesses.
ln=raw['clock']['landing_network']
ln['start_tree']=dict(form='die_start_stages',pins=dict(input='cland_tstart_in',output='cland_tstart_out'),
 source='fixed750 bounded-reset native-clock START source',
 uses=[dict(part=e['dst_part'],pin='cland_tstart_in',net=e['net']) for e in stages['die_outputs']],open=[])
for part in raw['partitions']:
 typ=raw['partition_types'][part['type']]
 if any(p['name']=='cland_tstart_out' for p in typ.get('clock',{}).get('landing_contract',{}).get('pins',[])):
  ln['start_tree']['open'].append(dict(part=part['name'],pin='cland_tstart_out'))
root_reset=json.load(open('/srv/opentallas-scratch2/claude/codex-qc-reset-infra-1029/provider_root_reset.json'))
rr=root_reset['candidates'][0]
ln['start_tree']['reset_source']=dict(port='rst_raw_n',part=rr['part'],pin=rr['pin'],net=rr['net'],xy_um=rr['xy_um'],
 source_part_release_cycles=rr['part_release_cycles'],hop_to_root_um=rr['hop_to_root_um'],phase_qualified=False,
 scope='existing whole-die synchronized neighbor-wavefront output; one local provider root input, not raw global star')
plan=SP.materialize(raw,stages)
P=S.Plan(plan,Q/'plan_start_native_h800.json')
result=SP.check(P,plan['clock']['landing_network']['start_tree']['provider'])
contract=LC.check(P)
(O/'plan.json').write_text(json.dumps(plan));(O/'actual_stages.json').write_text(json.dumps(stages))
(O/'provider_geometry.json').write_text(json.dumps(result,indent=1));(O/'landing_contract.json').write_text(json.dumps(contract,indent=1))
print(json.dumps(dict(provider=result,landing_errors=contract['errors'],scope='source/geometry candidate only; root phase, fresh source import and loaded clock remain required')),flush=True)
if result['errors'] or contract['errors']:raise SystemExit('physical source plan contract failed; candidate retained')
