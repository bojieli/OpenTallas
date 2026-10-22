#!/usr/bin/env python3
"""Re-fold fetched STG evidence locally; a remote legacy PASS is not a gate."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def unavailable(stage, label, reason):
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=True)
    result = stage / 'result.json'
    if result.exists():
        raw = result.read_bytes()
        (stage / f'original_result.{hashlib.sha256(raw).hexdigest()}.json').write_bytes(raw)
    result.write_text(json.dumps(dict(stage=label, verdict='INCOMPLETE',
        grade='DIAG (required collection evidence unavailable)', failures=[reason],
        source_identity_qualified=False, delivery_timing_qualified=False), indent=1) + '\n')


def normalize(stage):
    stage = Path(stage).resolve()
    raw = (stage / 'result.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    original = stage / f'original_result.{digest}.json'
    if original.exists():
        assert original.read_bytes() == raw
    else:
        original.write_bytes(raw)
    missing = []
    try:
        legacy = json.loads(raw)
        required = {'runlist.txt'}
        required.update(f'fx/L{layer}_fixture.json' for layer in range(36))
        for cfg, record in legacy.get('configs', {}).items():
            required.update(f'{cfg}/runs/{name}/bench.out' for name in record.get('stages', {}))
        for cfg in ('rel', 'pos', 'mut'):
            required.update(f'{cfg}/{name}' for name in (
                'vtb.sha256', 'vflags.txt', 'build/slice_calibrate.out',
                'build/calibrate.out', 'cal_mat/calibrate.out'))
        missing = sorted(name for name in required if not (stage / name).is_file())
        run = subprocess.run([sys.executable, str(Path(__file__).with_name('stage_stg.collect.py')),
                              str(stage.parent), stage.name], capture_output=True, text=True)
        (stage / 'normalization.log').write_text(run.stdout + run.stderr)
        if run.returncode not in (0, 1) or not run.stdout.startswith('STG '):
            raise ValueError('local collector could not fold fetched evidence: ' + run.stderr[-500:])
        result = json.loads((stage / 'result.json').read_text())
        if not all(key in result for key in ('numeric_case_summary', 'unknown_delivery_cases',
                                             'calibration_gate', 'delivery_timing_qualified')):
            raise ValueError('local collector lacks required calibration/delivery normalization schema')
        result['src_commit'] = legacy.get('src_commit')
    except (ValueError, OSError, KeyError, AttributeError, TypeError) as error:
        result = dict(stage=stage.name, verdict='INCOMPLETE', failures=[str(error)],
                      delivery_timing_qualified=False)
        missing.append('complete parsable local evidence')
    if missing:
        result['verdict'] = 'INCOMPLETE'
        result['delivery_timing_qualified'] = False
    # This collector does not inspect executable/source binding. The separately
    # published original-build receipt remains authoritative for that scope.
    result['grade'] = 'DIAG (local evidence fold; binary/source binding requires its separate build receipt)'
    result['source_identity_qualified'] = False
    result['collection_normalization'] = dict(
        raw_result=original.name, raw_result_sha256=digest,
        missing_evidence=missing, remote_result_unchanged=True,
        corrected_calibration_substituted=False)
    (stage / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(dict(verdict=result['verdict'],
                          numeric_case_summary=result.get('numeric_case_summary'),
                          unknown_delivery_cases=len(result.get('unknown_delivery_cases', [])),
                          missing_evidence=missing)))


if __name__ == '__main__':
    if sys.argv[1] == '--unavailable':
        unavailable(*sys.argv[2:5])
    else:
        normalize(sys.argv[1])
