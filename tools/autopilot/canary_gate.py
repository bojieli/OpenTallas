"""Hold production kit waves until the newest reference canary passes the current flow.
An explicitly identified corrective kit may run to repair that exact reference failure.
"""
import fnmatch
import json
from pathlib import Path


def assess(row, root, repo, run_git):
    if row.get('mode') == 'adopt':
        return True, 'existing run: observation only'
    candidates = []
    for p in Path(root).glob('*/canary_meta.json'):
        try:
            meta = json.loads(p.read_text())
            if meta['spec']['die'] == row['die']:
                candidates.append((p.stat().st_mtime_ns, str(p.parent), meta))
        except (OSError, ValueError, KeyError):
            continue
    if not candidates:
        return False, 'no reference canary for this die'
    _, run, meta = max(candidates)
    result = Path(run) / 'canary.json'
    source = meta.get('src_commit', '')
    exact = source + '@' + str(result)
    correction = row.get('canary_fix')
    if correction:
        if correction == exact and source:
            return True, 'explicit corrective kit for ' + exact
        return False, 'corrective reference must equal newest canary ' + exact
    try:
        verdict = json.loads(result.read_text())
    except (OSError, ValueError):
        return False, 'newest reference canary pending: ' + exact
    if verdict.get('verdict') != 'PASS' or verdict.get('src') != source:
        return False, 'newest reference canary failed/unbound: ' + exact
    try:
        spec = json.loads((Path(repo) / 'tools/flow_canary/canaries.json').read_text())
        watch = spec['watch']
    except (OSError, ValueError, KeyError):
        return False, 'flow canary watch specification missing'
    rc, paths, _ = run_git(['git', '-C', str(repo), 'diff', '--name-only', source, 'main'], timeout=60)
    if rc:
        return False, 'cannot compare canary flow source to current main'
    changed = [p for p in paths.splitlines() if any(fnmatch.fnmatch(p, w) for w in watch)]
    if changed:
        return False, 'flow changed since newest PASS: ' + ', '.join(changed[:4])
    return True, 'newest PASS covers current flow: ' + exact
