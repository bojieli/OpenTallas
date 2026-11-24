#!/usr/bin/env python3
"""Qualify the W6 witness in head_root_boot and compile the HEAD schedule on it (HEAD-R18 11-24).

  qualify.py REPO BUNDLE OLD_BUNDLE OUT_DIR
BUNDLE from make_bundle.py; OLD_BUNDLE the previous (l48uo, 11-07) bundle, which must now be rejected.
"""
import copy
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

repo, bundle, old, out = (Path(a).resolve() for a in sys.argv[1:5])
sys.path[:0] = [str(repo / 'tools/s81_dv'), str(repo / 'tools/s81_dv/layer_prog'), str(repo / 'tools/s81_head'),
                str(repo / 'tools/die_plan')]
from layer_prog.head_root_boot import PINS, N4_LINK_ADDED_CYCLES, pipeline_guard
import regen_schedule_constants as R

selection = dict(schema='opentallas.head.root88_source_selection.v1', bundle_root=str(bundle))
book = dict(head_root88_witness=selection, selected_HEAD_source_plan_sha256=PINS['source_plan.json'])
witness, gaps = pipeline_guard(book, '.')
assert witness['root_settle_cycles'] == 88 and witness['added_steady_cycles'] == 0
assert witness['n4_link_added_cycles'] == N4_LINK_ADDED_CYCLES
assert [g['cause'] for g in gaps] == ['HEAD_physical_START_HOST_PMA_authority_missing']

controls = {}
assert pipeline_guard({}, '.')[1][0]['cause'] == 'current_HEAD_ROOT88_source_witness_missing'
controls['missing_witness'] = 'rejected'
for tag, sha in (('10_30', '655784af46096873ba3235578fbc045d24a567ec614aedc4ad16b4cb11e12d2f'),
                 ('l48uo', 'f140216c876ba3186afdf3271f0f9b3ceadf63df95b5e0416a06af6dffcb54f6')):
    bad = copy.deepcopy(book); bad['selected_HEAD_source_plan_sha256'] = sha
    assert any(g['cause'] == 'HEAD_ROOT88_not_bound_to_selected_source_plan' for g in pipeline_guard(bad, '.')[1])
    controls[tag + '_plan_selected'] = 'rejected'
bad = copy.deepcopy(book); bad['head_root88_witness']['bundle_root'] = str(old)
w, g = pipeline_guard(bad, '.')
assert w is None and g[0]['cause'] == 'current_HEAD_ROOT88_source_witness_unqualified'
controls['l48uo_bundle'] = 'rejected: ' + g[0]['detail']
for date in (None, 113, 365, 5851):
    bad = copy.deepcopy(book); bad['actual_physical_START_cycle'] = date
    assert pipeline_guard(bad, '.')[0]['global_booking_qualified'] is False and pipeline_guard(bad, '.')[1]
controls['caller_START_date'] = 'still blocked; no physical event inferred'


def mutated(edit):
    with tempfile.TemporaryDirectory(prefix='l48uo_guard_') as d:
        p = Path(d)
        for f in bundle.iterdir():
            shutil.copy(f, p / f.name)
        edit(p)
        bad = copy.deepcopy(book); bad['head_root88_witness']['bundle_root'] = str(p)
        return pipeline_guard(bad, '.')


def drop_n4(p):
    s = json.loads((p / 'source_sidecar.json').read_text())
    next(r for r in s['ports'] if r['port'] == 'coll_WN2_u__3')['added_cycles'] = 3
    (p / 'source_sidecar.json').write_text(json.dumps(s))


def stale_settle(p):
    s = json.loads((p / 'source_sidecar.json').read_text())
    s['count_aligned']['root_settle_cycles'] = 74
    (p / 'source_sidecar.json').write_text(json.dumps(s))


def collector_without_lep0N_w(p):
    s = json.loads((p / 'source_sidecar.json').read_text())
    s['collector']['parts'].pop('lep0N_w')
    (p / 'source_sidecar.json').write_text(json.dumps(s))


E1BR = os.environ.get('OT_HEAD_E1BR_PROVIDER')  # optional: the 11-22 provider_e1br dir (pre-W6 re-site)


def start_tree_e1br(p):
    for n in ('start_stages.json', 'start_stages.sv'):
        (p / n).write_bytes(gzip.open(Path(E1BR) / (n + '.gz')).read())


MUTANTS = [('sidecar_without_n4', drop_n4), ('stale_settle_74', stale_settle),
           ('collector_without_lep0N_w', collector_without_lep0N_w)] + ([('start_tree_e1br', start_tree_e1br)] if E1BR else [])
for name, edit in MUTANTS:
    w, g = mutated(edit)
    assert w is None
    controls[name] = 'rejected: ' + g[0]['detail']

# The schedule: l48uo alone, then l48uo with sidecar 90d006.
raw = json.loads((bundle / 'source_plan.json').read_text())
side = json.loads((bundle / 'source_sidecar.json').read_text())
before = R.generate(raw)
after = R.generate(raw, None, side)
out.mkdir(parents=True, exist_ok=True)
plan_lanes = {k: v['cycles'] for k, v in before['lanes'].items()}
n4_lanes = {r['lane'] for r in side['ports'] if r['port'] in N4_LINK_ADDED_CYCLES}
n4_only = R.head_transport({k: v + (k in n4_lanes) for k, v in plan_lanes.items()})['total_cycles']
stale_lanes = {r['lane'] for r in after['sidecar_rows_below_sched_lat']}
summary = dict(verdict='PASS_W6_WITNESS_AND_SCHEDULE', witness=witness, production_gaps=gaps, controls_caught=controls,
               selected_source=dict(schema=selection['schema'], bundle='make_bundle.py output'),
               schedule=dict(plan_only_transport=before['transport']['total_cycles'],
                             n4_links_only_transport=n4_only,
                             sidecar_rows_below_sched_lat=after['sidecar_rows_below_sched_lat'],
                             with_sidecar_transport=after['transport']['total_cycles'],
                             spine=after['transport']['spine']['cycles'], spine_slice=after['transport']['spine']['slice'],
                             spine_side=after['transport']['spine']['side'], gather_worst=after['transport']['gather_worst'],
                             formula=after['transport']['formula'], landed_sidecar_extra=after['landed_sidecar_extra'],
                             delta=R.delta(before, after)),
               physical_START_qualified=False, full_token=False)
(out / 'qualification.json').write_text(json.dumps(summary, indent=1) + '\n')
(out / 'head_w6_schedule.json').write_text(json.dumps(
    dict(after, lanes={k: v for k, v in after['lanes'].items() if k.startswith('coll_')}), indent=1) + '\n')
(out / 'head_w6_sched_pkg.sv').write_text(R.sv(after))
print(summary['verdict'], json.dumps(summary['schedule']['delta']), after['transport']['total_cycles'], len(controls), 'controls')
