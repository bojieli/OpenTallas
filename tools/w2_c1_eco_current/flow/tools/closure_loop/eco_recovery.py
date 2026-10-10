#!/usr/bin/env python3
"""Immutable preflight/launch guards for explicitly requested missing-overlay ECO recovery."""
import hashlib
import json
from pathlib import Path
import shutil
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(manifest):
    for path, expected in manifest['hashes'].items():
        if digest(path) != expected:
            raise ValueError(f'recovery input/evidence changed: {path}')


def prepare(request):
    j = request['job']
    run = Path(j['run'])
    route = Path(j['eco']['ob'])
    measured = json.loads(Path(j['metrics']['corner_sta'][0]).read_text())
    failed = run / 'cl/eco'
    if json.loads((failed / 'result.json').read_text()) != j['eco']['result']:
        raise ValueError('failed ECO differs from recorded result')
    if (run / 'cl/hold_eco.a1.rc').read_text().strip() != '0':
        raise ValueError('original ECO did not complete normally')
    if list(route.glob('*.pre_eco')) or list(failed.glob('**/*.pre_eco')):
        raise ValueError('ECO installation/backup already exists')
    hashes = {}
    for ext, expected in request['original_hashes'].items():
        path = route / f'6_final.{ext}'
        if digest(path) != expected or measured['setup_ss'][f'{ext}_sha256'] != expected:
            raise ValueError(f'original {ext} is not the pinned signoff input')
        hashes[str(path)] = expected
    if measured['setup_ss']['worst_slack_ps'] != 190.49 or measured['hold_ff']['worst_slack_ps'] != -70.99:
        raise ValueError('original signoff metrics changed')
    if measured.get('post_sdc') != request['post_sdc_hashes']:
        raise ValueError('measured overlays changed')
    for path, expected in request['post_sdc_hashes'].items():
        hashes[str(run / 'src' / path)] = expected
    # Original reports, failed candidate, helpers and wrapper remain immutable too.
    for path in [Path(j['metrics']['corner_sta'][0]), route / '5_2_route.odb', route / '6_final.v',
                 run / 'cl/hold_eco.a1.sh', run / 'cl/hold_eco.a1.rc', *sorted(failed.rglob('*'))]:
        if path.is_file():
            hashes[str(path)] = digest(path)
    manifest = dict(hashes=hashes, source_commit=j['commit_full'], job=j['name'])
    verify(manifest)
    dest = run / 'cl/eco-overlay-recovery-a2'
    dest.mkdir()  # exclusive: no resetting/replacing a prior attempt
    for name in ('hold_eco.sh', 'hold_eco.tcl'):
        shutil.copyfile(run / 'cl' / name, dest / ('original_' + name))
    (dest / 'original_state.json').write_text(json.dumps(j, indent=1) + '\n')
    (dest / 'inputs.json').write_text(json.dumps(manifest, indent=1) + '\n')
    return dict(directory=str(dest), out=str(dest / 'candidate'), guard=str(dest / 'inputs.json'),
                manifest_sha256=digest(dest / 'inputs.json'))


if __name__ == '__main__':
    if sys.argv[1] == 'verify':
        verify(json.loads(Path(sys.argv[2]).read_text()))
    elif sys.argv[1] == 'prepare':
        print(json.dumps(prepare(json.loads(sys.argv[2]))))
    else:
        raise SystemExit('expected prepare or verify')
