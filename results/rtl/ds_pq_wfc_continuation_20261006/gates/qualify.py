#!/usr/bin/env python3
"""Qualify two existing terminals; pure record parsing, no tools or reruns."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(name):
    return json.loads((ROOT / name).read_text())

def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')

def text_hash(file):
    assert hashlib.sha256(file['text'].encode()).hexdigest() == file['sha256'], file['path']

w = read('wfc_terminal.json')
files = {f['relative']: f for f in w['files']}
for f in files.values():
    if 'text' in f:
        text_hash(f)

def one(suffix):
    matches = [f for p, f in files.items() if p.endswith(suffix)]
    assert len(matches) == 1, suffix
    return matches[0]

sta = json.loads(files['wf_sta.json']['text'])
drv = json.loads(files['wf_drv.json']['text'])
case = json.loads(files['case.json']['text'])
route = json.loads(one('5_2_route.json')['text'])
metrics = json.loads(one('6_report.json')['text'])
assert 'flow_rc=0' in files['status']['text'] and 'sta_rc=0' in files['status']['text']
assert 'period 833 ' in files['signoff.sdc']['text']
for name, sha in sta['artifacts_sha256'].items():
    assert one(name)['sha256'] == sha, name
for c in ('SS', 'FF'):
    assert sta['corners'][c]['done'] and sta['corners'][c]['exit'] == 0
    assert drv[c]['done'] and all(v == 0 for v in drv[c]['violators'].values())
for mode in ('incontext', 'reg2reg', 'region'):
    ss, ff = (sta['corners'][c][mode] for c in ('SS', 'FF'))
    assert ss['setup_wns_ps'] >= 15 and ff['hold_wns_ps'] >= 15
    assert ss['hold_wns_ps'] >= 0 and ff['setup_wns_ps'] >= 0
    assert all(c[k] == 0 for c in (ss, ff) for k in ('failing_setup', 'failing_hold'))
for key in ('detailedroute__route__drc_errors', 'detailedroute__antenna__violating__nets',
            'detailedroute__antenna__violating__pins', 'detailedroute__flow__errors__count'):
    assert route[key] == 0
assert one('5_route_drc.rpt')['bytes'] == 0
assert '[INFO ANT-0002] Found 0 net violations.' in one('5_2_route.log')['text']
assert '[INFO ANT-0001] Found 0 pin violations.' in one('5_2_route.log')['text']
assert metrics['finish__flow__errors__count'] == 0
exact = read('wfc_stage_exact.json')
assert next(f['sha256'] for f in exact if f['path'].endswith('.sv')) == case['ctrl_sha256']
for f in exact:
    if 'text' not in f:
        continue
    text_hash(f)
    if f['path'].endswith('run.log'):
        if '/r11_neg_' in f['path']:
            assert 'rc 1' in f['text'] and ('EQUIV FAIL' in f['text'] or 'LINK_REG FAIL' in f['text'])
        else:
            assert 'rc 0' in f['text'] and 'EQUIV PASS' in f['text']
            assert 'out=940000/940000' in f['text'] and 'starts=20000/20000' in f['text']
    if f['path'].endswith('args.txt'):
        assert '-GSOURCE=0' in f['text'] and '-GMAXU=866' in f['text'] and '-GUSERS=866' in f['text']
        assert '-DOT_WFC_LINK_SEL=1' in f['text'] and '-DOT_WFC_VM_REG=1' in f['text']
export = [{k: v for k, v in f.items() if k != 'text'} for f in files.values()
          if '/6_final.' in f['relative']]
dump('wfc_stage_qualified.json', {
    'schema': 'opentallas.ds_pq_wfc.stage_qualification.v1',
    'verdict': 'PASS_FULL_SHAPE_COMPONENT_REGION_CONTEXT',
    'accepted_15_15_region': True,
    'host': w['host'], 'case_path': w['root'], 'case': case,
    'signoff_period_ps': 833,
    'period_note': 'Existing signoff is 833 ps, slightly stricter than 833.333; not relaxed or rerun.',
    'setup_uncertainty_ps': 60, 'hold_uncertainty_ps': 25,
    'region_io_hold_uncertainty_ps': 50,
    'io_contract': 'Propagated extracted clock: 150 ps stage-link skew, 90 ps intra-region skew; 20% period IO allowance.',
    'timing': {c: {m: sta['corners'][c][m] for m in ('incontext', 'reg2reg', 'region')} for c in ('SS', 'FF')},
    'insertion_ps': {c: sta['corners'][c]['insertion_ps'] for c in ('SS', 'FF')},
    'drc_errors': 0, 'antenna_violating_nets': 0, 'antenna_violating_pins': 0,
    'electrical_checks': drv,
    'exact_stage_streams': {'positive_seeds': 2, 'flits_per_seed': 940000, 'starts_per_seed': 20000,
                            'negative_controls_caught': ['link', 'upos', 'vmrd']},
    'physical_metrics': {k: v for k, v in metrics.items() if k.startswith('finish__design__')},
    'retained_artifact_export': export,
    'export_kind': 'Verified remote final artifact paths and SHA256 manifest; bulk DB/DEF/GDS/SPEF/netlist remain on EPYC1.',
    'scope': 'Full-shape SOURCE=0 stage, MAXU=866, extracted SS/FF under the approved region boundary contract. No assembled-die closure or whole-controller-source closure claim.',
    'reroutes': 0, 'verification_tool_runs': 0,
})

qfiles = {f['relative']: f for f in read('qs2_terminal.json')['files']}
for f in qfiles.values():
    text_hash(f)
q = json.loads(qfiles['exact_qs2/qx_qs2.json']['text'])
checks = read('qs2_source_checks.json')
assert len(checks) == 37 and all(c['match'] for c in checks)
assert read('qs2_route_source_hashes.json') == q['source_sha256']
assert q['verdict'] == 'PASS' and not q['sources_dirty']
assert read('qs2_committed_evidence.json') == q
assert len(q['runs']) == 7
for run in q['runs']:
    log = qfiles[f"exact_qs2/{run['name']}_seed{run['seed']}.log"]
    assert log['sha256'] == run['log_sha256']
    if run['name'].startswith('neg_'):
        assert run['returncode'] != 0 and run['caught']
        assert 'divergence' in log['text'] or 'mismatch' in log['text']
    else:
        assert run['returncode'] == 0 and 'PASS QP=' in log['text']
for name, cmd in q['build_commands'].items():
    assert '+define+QX_QS=2' in cmd and '+define+QX_QM=5' in cmd
l20 = read('qs2_l20.json')
for f in l20['files']:
    text_hash(f)
build = json.loads(next(f['text'] for f in l20['files'] if f['path'].endswith('build.json')))
common = set(build['source_sha256']) & set(q['source_sha256'])
assert all(build['source_sha256'][p] == q['source_sha256'][p] for p in common)
assert '`define OT_PAIR_PQ_QS 2' in next(f['text'] for f in l20['files'] if f['path'].endswith('qelem_defines.sv'))
assert 'comb rc=0\nDONE' in next(f['text'] for f in l20['files'] if f['path'].endswith('comb_qs2.log'))
assert len(l20['runs']) == 3648
for item in l20['runs']:
    v = item['result']
    assert v['pass_'] and v['mismatched'] == 0 and v['extra'] == 0 and v['node']['fault'] == 0
phase = sum('#p' in x['result']['group'] for x in l20['runs'])
assert phase == 2752

dump('qs2_qualified.json', {
    'schema': 'opentallas.ds_pq_wfc.qs2_exact_qualification.v1',
    'verdict': 'PASS_SOURCE_MATCHED_QS2_EXACT_AND_NEGATIVES',
    'route_source_commit': 'd44b98796bc261e7b8a594741beb246dd7e5085d',
    'bench_reported_commit': q['git_commit'],
    'committed_terminal_evidence': '1dd2bf2f4',
    'committed_terminal_match': 'Harvested exact-gate JSON is byte-identical to qx10qs2.json at 1dd2bf2f4.',
    'cycle_cost_record': '1dd2bf2f4 reports all 3648 PQ1 L20 runs cycle-identical to QS1; this harvest does not re-run QS1.',
    'source_identity_basis': 'All 37 recorded RTL/bench/driver hashes match central d44b98796 and remote EPYC2 Z29c source; remote bench commit ID is not locally available.',
    'exact_gate': {'positive_runs': 5, 'negative_runs': 2, 'total_compared_cycles': q['total_compared_cycles'],
                   'QM': 5, 'QS': 2, 'PQ': 0, 'scope': 'Full q-element mechanism vs pinned reference; sequence comparison, four seeds plus sparse NaN.'},
    'pq1_l20': {'phase_runs': phase, 'node_runs': 3648-phase, 'failed': 0, 'rows_mismatched': 0,
                'rows_extra': 0, 'common_exact_source_pins': len(common),
                'spine_sha256': build['source_sha256']['rtl/v41die/ot_v41_spine_pqc_w17w10.sv'],
                'scope': 'Existing full-shape L20 PQ=1 field fixture; spine pin differs from active v13b, so this is not qualification of the combined current v13b+QS2 build.'},
    'physical_adoption': False, 'physical_status': 'Existing Z29c run preserved; this record qualifies exactness only.',
    'new_benches': 0, 'qs1_evidence_used': False,
})
print('PASS WFC full-shape component: DRC/antenna/SSFF/region/exact and final-artifact hashes')
print('PASS QS2: 37 source pins, 5 positives, 2 caught negatives, PQ1 L20 3648/3648')
