"""Explicit collect-only lint recovery; original route helpers and inputs stay immutable."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def eligible(j):
    if (j.get('status') != 'NEEDS_HUMAN' or j.get('stage_key') != 'collect'
            or not j.get('spec', {}).get('ref_tile') or j.get('export_lint_recovery')
            or not j.get('freeze_helper_overlay') or not j.get('route_overlay_plan')):
        raise ValueError('requires frozen ref_tile collect failure without an earlier recovery')
    events = ' '.join(j.get('events', []))
    if 'route done (rc=0)' not in events or '-> CLOSED' not in events:
        raise ValueError('route did not finish and pass the physical verdict')
    if j.get('failed_checks') or (j.get('metrics', {}).get('drc') != 0):
        raise ValueError('physical checks are not clean')
    metrics = j['metrics']
    if (metrics.get('errors') or metrics.get('ss_ps', -1) < 0 or metrics.get('ff_ps', -1) < 0):
        raise ValueError('routed setup/hold are not passing')
    if not any('child_lint FAIL (b) pg:' in c.get('tail', '') for c in j.get('crashes', [])):
        raise ValueError('no recorded PG lint collection failure')


def verify(manifest):
    for path, expected in manifest['hashes'].items():
        if digest(path) != expected:
            raise ValueError(f'export recovery immutable input changed: {path}')


def prepare(request):
    j = request['job']
    eligible(j)
    run = Path(j['run'])
    base = list((Path(j['metrics']['orfs_dir']) / 'results/asap7').glob('*/base'))
    if len(base) != 1:
        raise ValueError('expected one physical route base')
    hashes = {}
    for ext in ('odb', 'sdc', 'spef'):
        p = base[0] / ('6_final.' + ext)
        if not p.is_file() or not p.stat().st_size:
            raise ValueError('missing routed ' + ext)
        hashes[str(p)] = digest(p)
    for row in j['route_overlay_plan']['files']:
        p = run / 'cl' / Path(row['path']).name
        if digest(p) != row['sha256']:
            raise ValueError('original frozen helper changed: ' + str(p))
        hashes[str(p)] = row['sha256']
    # Capture the actual completed verdict, including all measured post-SDC inputs.
    for p in list((run / 'cl').glob('routed_ioref*')) + [Path(x) for x in j['metrics'].get('corner_sta', [])]:
        if p.is_file():
            hashes[str(p)] = digest(p)
    for rel in j['metrics'].get('post_sdc', []) + j['metrics'].get('setup_post_sdc', []):
        p = run / 'src' / rel
        hashes[str(p)] = digest(p)
    data = base64.b64decode(request['helper_b64'], validate=True)
    if hashlib.sha256(data).hexdigest() != request['helper_sha256']:
        raise ValueError('recovery helper hash mismatch')
    dest = run / 'cl/export-lint-recovery'
    dest.mkdir()  # exclusive, never overwrite a prior attempt
    helper = dest / 'child_lint.py'
    helper.write_bytes(data)
    hashes[str(helper)] = digest(helper)
    guard = dest / 'verify.py'
    guard.write_bytes(Path(__file__).read_bytes() if __file__ != '<stdin>' else base64.b64decode(request['guard_b64']))
    hashes[str(guard)] = digest(guard)
    shutil.copytree(run / 'record', dest / 'original_record')
    (dest / 'original_job.json').write_text(json.dumps(j, indent=1) + '\n')
    for p in [dest / 'original_job.json', *sorted((dest / 'original_record').rglob('*'))]:
        if p.is_file():
            hashes[str(p)] = digest(p)
    manifest = dict(job=j['name'], original_commit=j['commit_full'],
                    helper_commit=request['helper_commit'], hashes=hashes)
    verify(manifest)
    path = dest / 'inputs.json'
    path.write_text(json.dumps(manifest, indent=1) + '\n')
    return dict(directory=str(dest), manifest_sha256=digest(path), guard_sha256=digest(guard), helper_sha256=digest(helper),
                helper_commit=request['helper_commit'])


def stage_script(recovery, source):
    import shlex
    q = shlex.quote
    d = Path(recovery['directory'])
    # Verify the manifest itself before executing the pinned guard. The guard is also hashed inside it.
    pre = (f"printf '%s  %s\\n' {q(recovery['manifest_sha256'])} {q(str(d / 'inputs.json'))} | sha256sum -c - >/dev/null || exit 91\n"
           f"printf '%s  %s\\n' {q(recovery['guard_sha256'])} {q(str(d / 'verify.py'))} | sha256sum -c - >/dev/null || exit 91\n"
           f"python3 {q(str(d / 'verify.py'))} verify {q(str(d / 'inputs.json'))} || exit 91\n")
    return pre + f"cp {q(str(d / 'child_lint.py'))} {q(str(Path(source) / 'tools/hier_contract/child_lint.py'))} || exit 91\n", pre


if __name__ == '__main__':
    if sys.argv[1] == 'verify':
        verify(json.loads(Path(sys.argv[2]).read_text()))
    elif sys.argv[1] == 'prepare':
        print(json.dumps(prepare(json.loads(sys.argv[2]))))
