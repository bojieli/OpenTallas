"""Hold production kit waves until a completed reference canary PASSes the kit's flow.

Binding canary = the NEWEST COMPLETED canary run of the reference die (canary.json whose
'src' equals canary_meta.json 'src_commit'); still-pending newer runs never mask it.
A PASS binds a kit only when the kit's watched flow files equal the PASS canary's, and
main's watched flow is either the PASS canary's or already covered by a newer (pending)
canary run.  A corrective kit names the reference failure by path (after the last '@').
"""
import fnmatch
import json
from pathlib import Path


def _runs(root, die):
    runs = []
    for p in Path(root).glob('*/canary_meta.json'):
        try:
            meta = json.loads(p.read_text())
            if meta['spec']['die'] != die:
                continue
            mtime = p.stat().st_mtime_ns
        except (OSError, ValueError, KeyError, TypeError):
            continue
        source = meta.get('src_commit', '')
        verdict = None
        try:
            result = json.loads((p.parent / 'canary.json').read_text())
            if source and result.get('src') == source:
                verdict = result.get('verdict')
        except (OSError, ValueError, AttributeError):
            pass
        runs.append({'mtime': mtime, 'run': str(p.parent), 'src': source, 'verdict': verdict,
                     'done': verdict is not None,
                     'ref': source + '@' + str(p.parent / 'canary.json')})
    return sorted(runs, key=lambda r: (r['mtime'], r['run']))


def _flow_diff(run_git, repo, a, b, watch):
    rc, paths, _ = run_git(['git', '-C', str(repo), 'diff', '--name-only', a, b], timeout=60)
    if rc:
        return None
    return [p for p in paths.splitlines() if any(fnmatch.fnmatch(p, w) for w in watch)]


def _corrective(correction, runs, root, die):
    named = correction.rsplit('@', 1)[-1].strip()
    run_dir = Path(named).parent if Path(named).name == 'canary.json' else Path(named)
    try:
        key = str(run_dir.resolve())
    except OSError:
        key = str(run_dir)
    match = [r for r in runs if str(Path(r['run']).resolve()) == key]
    if not match:
        meta = run_dir / 'canary_meta.json'
        if meta.is_file():
            try:
                other = json.loads(meta.read_text())['spec']['die']
            except (OSError, ValueError, KeyError, TypeError):
                other = '?'
            return False, ('corrective canary ' + named + ' belongs to die ' + str(other) + ', not reference die '
                           + die + '; enqueue as a normal row')
        return False, 'corrective canary unknown: ' + named + ' is not a canary run under ' + str(root)
    r = match[0]
    if not r['done']:
        if r is runs[-1]:
            return True, 'explicit corrective kit for newest (pending) canary ' + r['ref']
        return False, 'corrective canary ' + r['ref'] + ' is pending but not the newest run; name the newest canary'
    if r['verdict'] == 'PASS':
        return False, 'corrective canary ' + r['ref'] + ' PASSed; enqueue as a normal row'
    newer_pass = [x for x in runs if x['done'] and x['verdict'] == 'PASS' and x['mtime'] > r['mtime']]
    if newer_pass:
        return False, ('a newer PASS canary exists (' + newer_pass[-1]['ref'] + ') than corrective canary '
                       + r['ref'] + '; enqueue as a normal row')
    return True, 'explicit corrective kit for failed canary ' + r['ref']


def assess(row, root, repo, run_git):
    if row.get('mode') == 'adopt':
        return True, 'existing run: observation only'
    reference_die = {'cp1': 's81'}.get(row['die'], row['die'])
    runs = _runs(root, reference_die)
    if not runs:
        return False, 'no reference canary for die ' + reference_die + '; register a reviewed reference canary first'
    newest = runs[-1]
    completed = [r for r in runs if r['done']]
    correction = row.get('canary_fix')
    if correction:
        return _corrective(correction, runs, root, reference_die)
    if not completed:
        return False, ('newest reference canary pending: ' + newest['ref']
                       + '; reviewed corrective kit only: re-enqueue --canary-fix ' + newest['ref'])
    bind = completed[-1]
    if bind['verdict'] != 'PASS':
        return False, ('newest completed reference canary failed: ' + bind['ref']
                       + '; reviewed corrective kit only: re-enqueue --canary-fix ' + bind['ref'])
    try:
        spec = json.loads((Path(repo) / 'tools/flow_canary/canaries.json').read_text())
        watch = spec['watch']
    except (OSError, ValueError, KeyError):
        return False, 'flow canary watch specification missing'
    # main's watched flow is covered when a newer pending run already canaries it;
    # otherwise main must still carry the PASS canary's flow.
    covered = False
    if newest is not bind and newest['src']:
        covered = _flow_diff(run_git, repo, newest['src'], 'main', watch) == []
    if not covered:
        changed = _flow_diff(run_git, repo, bind['src'], 'main', watch)
        if changed is None:
            return False, 'cannot compare canary flow source to current main'
        if changed:
            return False, ('flow changed since newest PASS ' + bind['ref'] + ': ' + ', '.join(changed[:4])
                           + '; no canary run on main\'s flow yet (trigger the flow canary)')
    kit_source = row.get('src', '').rsplit('@', 1)[-1]
    if not kit_source:
        return False, 'queued kit source is missing'
    changed = _flow_diff(run_git, repo, bind['src'], kit_source, watch)
    if changed is None:
        return False, 'cannot compare queued kit flow source to PASS canary source'
    if changed:
        return False, ('queued kit flow differs from PASS canary ' + bind['ref'] + '; regenerate from canaried flow: '
                       + ', '.join(changed[:4]) + ' (src ' + bind['src'] + ')')
    return True, 'newest completed PASS covers kit flow: ' + bind['ref']
