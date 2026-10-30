#!/usr/bin/env python3
import copy,json,sys,tempfile
from pathlib import Path
from layer_prog.head_root_boot import PINS,read_witness,pipeline_guard
base=Path('/srv/opentallas-scratch2/claude/codex-head-event-1030')
selection=dict(schema='opentallas.head.root88_source_selection.v1',metadata_root=str(base/'meta_legal88'),emitted_root=str(base/'src25legal88_native'))
b=dict(head_root88_witness=selection,selected_HEAD_source_plan_sha256=PINS['metadata/source_plan.json'])
w,g=pipeline_guard(b,'.')
assert w['root_settle_cycles']==88 and w['delta_boot_cycles']==14 and w['added_steady_cycles']==0
assert len(g)==1 and g[0]['cause']=='HEAD_physical_START_HOST_PMA_authority_missing'
controls={}
assert pipeline_guard({},'.')[1][0]['cause']=='current_HEAD_ROOT88_source_witness_missing';controls['missing_witness']='rejected'
bad=copy.deepcopy(b);bad['selected_HEAD_source_plan_sha256']='0'*64
assert any(p['cause']=='HEAD_ROOT88_not_bound_to_selected_source_plan'for p in pipeline_guard(bad,'.')[1]);controls['wrong_selected_source']='rejected'
for date in [None,110,382,5861]:
 bad=copy.deepcopy(b);bad['actual_physical_START_cycle']=date
 assert pipeline_guard(bad,'.')[0]['global_booking_qualified']is False and pipeline_guard(bad,'.')[1]
controls['missing_or_timeout_derived_START']='all blocked; no physical event inferred'
with tempfile.TemporaryDirectory(prefix='root88_guard_')as d:
 p=Path(d)
 for key in PINS:
  if key.startswith('metadata/'):
   name=key.split('/',1)[1];(p/name).write_bytes((base/'meta_legal88'/name).read_bytes())
 for stale in [64,74]:
  r=json.loads((base/'meta_legal88/source_sidecar.json').read_text());r['count_aligned']['root_settle_cycles']=stale
  (p/'source_sidecar.json').write_text(json.dumps(r))
  bad=copy.deepcopy(b);bad['head_root88_witness']['metadata_root']=str(p)
  assert pipeline_guard(bad,'.')[0]is None;controls['stale_settle_'+str(stale)]='rejected actual source identity mismatch'
result=dict(verdict='PASS_CURRENT_SOURCE_WITNESS_GUARD',actual_witness=w,production_gaps=g,controls_caught=controls,
    selected_source=selection,physical_START_qualified=False,full_token=False)
Path(sys.argv[1]).write_text(json.dumps(result,indent=1)+'\n');print(result['verdict'],len(controls),'controls',w['delta_boot_cycles'],'bootcycles',len(g),'globalholds')
