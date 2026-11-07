#!/usr/bin/env python3
"""Two-job compile_pipeline on the retained native A/B images with the l48un witness.

  qualify_pipeline.py REPO BUNDLE RUN OUT.json
Uses results/token_pass/pipeline_native_s81_1021 inputs and test bookings: real
native payloads, explicit TEST date books. The HEAD contract is the point here;
production holds stay as compile_pipeline reports them.
"""
import json
import shutil
import sys
from pathlib import Path

repo, bundle, run, out = (Path(a).resolve() for a in sys.argv[1:5])
sys.path[:0] = [str(repo / 'tools/s81_dv'), str(repo / 'tools/s81_dv/layer_prog')]
from layer_prog.pipeline_boot import compile_pipeline
from layer_prog.head_root_boot import PINS
from ks_descriptor import fixture_word

src = repo / 'results/token_pass/pipeline_native_s81_1021'
run.mkdir(parents=True, exist_ok=False)
for name in 'AB':
    shutil.copytree(src / 'inputs' / name, run / name)
shutil.copy(src / 'fixture_meta.json', run / 'fixture_meta.json')
shutil.copy(src / 'bookings.json', run / 'bookings.json')
calendar = json.loads((repo / 'results/token_pass/calendar_pipeline_s81_1021/calendar_rel241_G4_mtp.json').read_text())
(run / 'calendar.json').write_text(json.dumps(calendar))
book = json.loads((run / 'bookings.json').read_text())
meta = json.loads((run / 'fixture_meta.json').read_text())
(run / 'descriptor.memh').write_text(f'{fixture_word(meta, user=0):014x}\n')
book['head_root88_witness'] = dict(schema='opentallas.head.root88_source_selection.v1', bundle_root=str(bundle))
book['selected_HEAD_source_plan_sha256'] = PINS['source_plan.json']
result = compile_pipeline(calendar, book, run, run / 'emitted')
w = result['head_root_boot_contract']
causes = [g['cause'] for g in result['gaps']]
assert result['status'] == 'PARTIAL' and result['emitted'] == 2
assert w['plan_event'] == 'l48un' and w['n4_data_cycles_added_per_link'] == 1
assert 'HEAD_physical_START_HOST_PMA_authority_missing' in causes
assert not any(c.startswith('current_HEAD_ROOT88_source_witness_') for c in causes)
stale = dict(book, selected_HEAD_source_plan_sha256='655784af46096873ba3235578fbc045d24a567ec614aedc4ad16b4cb11e12d2f')
caught = compile_pipeline(calendar, stale, run, run / 'emitted_stale')
assert any(g['cause'] == 'HEAD_ROOT88_not_bound_to_selected_source_plan' for g in caught['gaps'])
summary = dict(verdict='PASS_TWO_JOB_PIPELINE_L48UN_WITNESS', scope='TEST date books on retained native A/B images',
               emitted=result['emitted'], status=result['status'], HEAD_boot=w,
               gap_causes=sorted(set(causes)), stale_selection_caught=True, full_token=False)
out.write_text(json.dumps(summary, indent=1) + '\n')
print(summary['verdict'], result['emitted'], result['status'], len(set(causes)), 'gap causes')
