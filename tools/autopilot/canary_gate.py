"""Hold production kit waves until the newest reference canary passes the current flow.
An explicitly identified corrective kit may run to repair that exact reference failure.
"""
import fnmatch
import json
from pathlib import Path


def assess(row, root, repo, run_git):
    if row.get('mode') == 'adopt':
        return True, 'existing run: observation only'
    reference_die = {'cp1': 's81'}.get(row['die'], row['die'])
    candidates = []
    for p in Path(root).glob('*/canary_meta.json'):
        try:
            meta = json.loads(p.read_text())
            if meta['spec']['die'] == reference_die:
                candidates.append((p.stat().st_mtime_ns, str(p.parent), meta))
        except (OSError, ValueError, KeyError):
            continue
    if not candidates:
        return False, 'no reference canary for die ' + reference_die + '; register a reviewed reference canary first'
    _, run, meta = max(candidates)
    result = Path(run) / 'canary.json'
    source = meta.get('src_commit', '')
    exact = source + '@' + str(result)
    remedy = '; reviewed corrective kit only: re-enqueue --canary-fix ' + exact
    correction = row.get('canary_fix')
    if correction:
        if correction == exact and source:
            return True, 'explicit corrective kit for ' + exact
        return False, 'corrective reference must equal newest canary ' + exact
    try:
        verdict = json.loads(result.read_text())
    except (OSError, ValueError):
        return False, 'newest reference canary pending: ' + exact + remedy
    if verdict.get('verdict') != 'PASS' or verdict.get('src') != source:
        return False, 'newest reference canary failed/unbound: ' + exact + remedy
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
        return False, 'flow changed since newest PASS: ' + ', '.join(changed[:4]) + remedy
    return True, 'newest PASS covers current flow: ' + exact
