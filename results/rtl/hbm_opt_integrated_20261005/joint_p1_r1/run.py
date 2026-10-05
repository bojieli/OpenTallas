#!/usr/bin/env python3
"""One production PQ/XMAP build; run retained P1 fixtures, never generate inputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

JOB = Path(sys.argv[1]).resolve()
SOURCE = JOB / 'source'
DRIVER = SOURCE / 'tools/dshbm_sm_xmap_seq.py'
PRODUCTION = SOURCE / 'rtl/hbm_accel/sm/pq_production_20261005'
WORK = JOB / 'work'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (JOB / name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def main():
    identity = json.loads((JOB / 'rawls-joint-source-identity.json').read_text())
    pins = {name: sha(SOURCE / name) for name in identity['source_paths']}
    save('selected_sources.json', pins)
    save('source_context.json', dict(**identity, measurement_flags={
        'ENABLE': 1, 'PQ_ENABLE': 1, 'XMAP': 1, 'HAZ': 1, 'G1ASB': 0},
        clock_scope='1ns simulation only; no loaded SS/FF admission or headline frequency'))
    # Keep an independently clean selected-source snapshot. This content commit
    # is not represented as the original full-main revision named above.
    subprocess.run(['git', 'init', '-q', str(SOURCE)], check=True)
    subprocess.run(['git', '-C', str(SOURCE), 'add', '--', *pins], check=True)
    subprocess.run(['git', '-C', str(SOURCE), '-c', 'gc.auto=0',
                    '-c', 'user.name=Rawls', '-c', 'user.email=rawls@localhost',
                    'commit', '-qm', 'Selected unchanged main source for PQ/XMAP joint gate'], check=True)
    save('snapshot_content_commit.json', {
        'snapshot_content_commit': subprocess.check_output(
            ['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip(),
        'full_main_source_commit': identity['source_main_commit']})
    results = {}
    for name, negative in [('stress', False), ('ar_l20', False), ('wg', False),
                           ('other', False), ('stress', True)]:
        fixture = JOB / 'fixtures' / f'{name}_haz1_g0'
        key = name + ('_negative_fp4' if negative else '')
        argv = [sys.executable, str(DRIVER), 'run', '--production-dir', str(PRODUCTION),
                '--work', str(WORK), '--xmap', '1', '--active', '1', '--jobs', '16',
                '--fixture', str(fixture)]
        if negative:
            argv.append('--negative-fp4')
        save(key + '_command.json', argv)
        with (JOB / (key + '_driver.log')).open('x') as log:
            process = subprocess.Popen(argv, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT)
            save(key + '_running.json', {'pid': process.pid})
            rc = process.wait()
        save(key + '_exit.json', {'exit': rc})
        record = WORK / ('negative' if negative else 'pq') / 'a1' / fixture.name / 'result.json'
        measured = json.loads(record.read_text()) if record.is_file() else None
        results[key] = dict(exit=rc, result=measured)
        if rc:
            save('terminal.json', dict(status='fail', first_blocker=key,
                results=results, source_stable=all(sha(SOURCE / p) == h for p, h in pins.items())))
            return rc
    passed = all(r['result'] and r['result']['accepted'] for r in results.values())
    stable = all(sha(SOURCE / p) == h for p, h in pins.items())
    save('terminal.json', dict(status='pass' if passed and stable else 'fail',
        results=results, source_stable=stable, one_compiled_executable=True,
        generated_numeric_inputs=False, P6_pending=True, full_token_measured=False,
        SS_FF_admitted=False, composed_model_owner='Maxwell'))
    return 0 if passed and stable else 1


try:
    exit_code = main()
except Exception:
    with (JOB / 'launcher_failure.txt').open('x') as f:
        traceback.print_exc(file=f)
    exit_code = 1
    if not (JOB / 'terminal.json').exists():
        save('terminal.json', {'status': 'fail', 'first_blocker': 'launcher exception'})
(JOB / 'runtime.exit').write_text(str(exit_code) + '\n')
sys.exit(exit_code)
