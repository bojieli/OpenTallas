#!/usr/bin/env python3
"""Routine C1 intake: verify immutable existing artifacts, then repair hold only."""
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / 'spec.json').read_text())
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''): h.update(b)
    return h.hexdigest()
def checked(path, expected):
    actual = sha(path)
    if actual != expected: raise RuntimeError(f'hash mismatch: {path}: {actual}')
    return {'path': str(path), 'sha256': actual}
p = argparse.ArgumentParser(); p.add_argument('--run', required=True); p.add_argument('--check-only', action='store_true'); a = p.parse_args()
run = Path(a.run); run.mkdir(parents=True, exist_ok=True)
base = Path(SPEC['route_base']); original = Path(SPEC['original_run']).parents[1]
checked(original / 'gate/terminal.json', SPEC['exact_terminal_sha256'])
gate = json.loads((original / 'gate/terminal.json').read_text())
assert gate['passed'] is True
binding = {}
for rel, expected in gate['source_pins'].items():
    binding[rel] = {s: checked(original / s / rel, expected) for s in ('src', 'bench_src_a1')}
mutant = original / 'neg_s3/neg_only.run.log'
assert 'wrong full73 receipt fabricated retirement' in mutant.read_text()
assert 'FATAL' in mutant.read_text()
checked(mutant, SPEC['mutant_run_sha256'])
checked(original / 'neg_s3/neg_only_tb.sv', SPEC['mutant_tb_sha256'])
artifacts = {'odb': checked(base / '6_final.odb', SPEC['odb_sha256']), 'spef': checked(base / '6_final.spef', SPEC['spef_sha256']), 'sdc': checked(SPEC['reference_sdc'], SPEC['sdc_sha256'])}
helpers = {rel: checked(HERE / 'flow' / rel, expected) for rel, expected in SPEC['helper_sha256'].items()}
receipt = {'source_commit': SPEC['source_commit'], 'helper_commit': SPEC['helper_commit'], 'source_binding': binding, 'artifacts': artifacts, 'helpers': helpers, 'exact_passed': True, 'genuine_mutant_log': {'path': str(mutant), 'sha256': sha(mutant)}}
(run / ('preflight.json' if a.check_only else 'route_preflight.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print('C1_IMMUTABLE_GATE_BOUND', flush=True)
if a.check_only: raise SystemExit(0)
seed = run / 'signoff_seed'; seed.mkdir(exist_ok=False)
shutil.copy2(SPEC['reference_sdc'], seed / '6_final.sdc')
os.link(base / '6_final.spef', seed / '6_final.spef')
env = os.environ.copy(); env.update(SPEC['env'])
cmd = ['bash', str(HERE / 'flow/tools/closure_loop/hold_eco.sh'), str(base), str(seed), str(run / 'eco'), 'ot_hbm_native_frame_station_rb']
rc = subprocess.call(cmd, cwd=HERE / 'flow', env=env)
result_path = run / 'eco/result.json'
if result_path.exists():
    result = json.loads(result_path.read_text())
    # The canonical ECO helper records final routed DRC count in result.json.
    metrics = {'detailedroute__route__drc_errors': result.get('drc'), 'provenance': {'path': str(result_path), 'sha256': sha(result_path), 'producer': 'current canonical hold_eco.sh; final Number of violations'}}
    (run / 'eco_drc_metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
(run / 'eco_exit.json').write_text(json.dumps({'returncode': rc, 'command': cmd, 'env': SPEC['env']}, indent=2) + '\n')
raise SystemExit(rc)
