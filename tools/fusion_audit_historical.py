#!/usr/bin/env python3
"""Check/replay the original FA model estimate using committed historical blobs.

Current product sources are deliberately not inputs. A retained audit record may
have a documented later pin-only edit; its numerical body must still equal the
original. Neither that edit nor this verifier certifies the current model.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'results/uarch/fusion_audit_historical_checkpoint.json'
RECORD = ROOT / 'results/uarch/fusion_audit.json'


def blob(commit, path):
    result = subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'Missing historical Git blob {commit}:{path}; fetch the refs listed in {CHECKPOINT.name}')
    return result.stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def body(record):
    return {k: v for k, v in record.items() if k != 'source_sha256'}


def verify(retained=None):
    cp = json.loads(CHECKPOINT.read_text())
    assert cp['schema'] == 'opentallas.fa.historical-checkpoint.v1'
    assert cp['adoption'] is False
    commit, path = cp['original_commit'], cp['record_path']
    raw = blob(commit, path)
    assert digest(raw) == cp['original_record_sha256']
    original = json.loads(raw)
    assert original['source_sha256'] == cp['original_source_sha256']
    for p, sha in cp['original_source_sha256'].items():
        assert digest(blob(commit, p)) == sha, p
    for p, sha in cp['replay_inputs_sha256'].items():
        assert digest(blob(commit, p)) == sha, p
    tree = subprocess.check_output(['git', 'rev-parse', f'{commit}:tools'], cwd=ROOT, text=True).strip()
    assert tree == cp['tools_tree_git_oid']
    tree = subprocess.check_output(['git', 'rev-parse', f'{commit}:src'], cwd=ROOT, text=True).strip()
    assert tree == cp['src_tree_git_oid']
    allowed_maps = [original['source_sha256']]
    for entry in cp['retained_pin_only_records']:
        raw = blob(entry['commit'], path)
        assert digest(raw) == entry['sha256']
        record = json.loads(raw)
        assert body(record) == body(original), 'historical numerical body changed'
        allowed_maps.append(record['source_sha256'])
    if retained is None:
        retained = json.loads(RECORD.read_text())
    assert body(retained) == body(original), 'retained record is not the historical audit'
    assert retained['source_sha256'] in allowed_maps, 'undocumented pin-map edit'
    # Prove each referenced commit is covered by the proposed publication roots.
    w11 = json.loads((ROOT / 'results/uarch/fusion_audit_w11_run_level.json').read_text())
    required_commits = {commit} | {x['commit'] for x in cp['retained_pin_only_records']}
    required_commits |= {x['commit'] for x in w11['git_sources']}
    assert set(cp['required_git_commits']) == required_commits, 'publication inventory drift'
    roots = [x['commit'] for x in cp['publication_roots']]
    for required in cp['required_git_commits']:
        assert any(subprocess.run(['git', 'merge-base', '--is-ancestor', required, root],
                                  cwd=ROOT, capture_output=True).returncode == 0 for root in roots), required
    return cp, original


def replay():
    cp, original = verify()
    # Export immutable source files into scratch. No checkout, current model
    # mutation, large physical job, or persistent write to historical evidence.
    paths = ['tools', 'src'] + [p for p in cp['replay_inputs_sha256'] if not p.startswith(('tools/', 'src/'))]
    archive = subprocess.check_output(['git', 'archive', cp['original_commit'], '--', *paths], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='fa-historical-') as tmp:
        tree = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar.getmembers():
                target = tree / member.name
                assert target.resolve().is_relative_to(tree)
                assert member.isdir() or member.isfile(), 'snapshot must contain regular files only'
            tar.extractall(tree)
        out = tree / 'replayed.json'
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL') if k in os.environ}
        env['PYTHONPATH'] = str(tree / 'src')
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        result = subprocess.run([sys.executable, 'tools/fusion_audit.py', '--out', str(out)],
                                cwd=tree, env=env, capture_output=True)
        if result.returncode:
            raise RuntimeError('Historical replay failed:\n' + result.stderr.decode())
        assert json.loads(out.read_text()) == original, 'historical replay differs from original record'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True)
    parser.add_argument('--record', type=Path, help='retained record to compare; defaults to this checkout')
    parser.add_argument('--replay', action='store_true', help='regenerate from the original Git snapshot')
    args = parser.parse_args()
    verify(json.loads(args.record.read_text()) if args.record else None)
    if args.replay:
        replay()
    print('PASS: original Git pins and historical numerical scope' + ('; isolated original replay' if args.replay else ''))


if __name__ == '__main__':
    main()
