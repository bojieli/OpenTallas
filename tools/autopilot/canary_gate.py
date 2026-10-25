"""Hold production kit waves until a completed reference canary PASSes the kit's flow.

Binding canary = the NEWEST COMPLETED canary run of the reference die (canary.json whose
'src' equals canary_meta.json 'src_commit'); still-pending newer runs never mask it.
A PASS binds a kit only when the kit's watched flow files equal the PASS canary's, and
main's watched flow is either the PASS canary's or already covered by a newer (pending)
canary run.  A corrective kit names the reference failure by path (after the last '@').
Only runs of the die's CURRENT reference item (tools/flow_canary/canaries.json) count: after a reference switch the
old item's results neither bind nor hold (FLOW-CANARY 10-25: HBM rows kept binding the retired B2l calendar FAIL).
Reference die: cp1 -> s81; a qwen_kvsys hard-core kit (runner run_kit_kv.sh, or a kit dir holding one) ->
qwen_kvsys_core, the canary of that flow (gen_core_kit_kv.py), not the gen_phys type canary kv3_io_ft.
"""
import fnmatch
import json
from pathlib import Path


def _runs(root, die, item=None):
    runs = []
    for p in Path(root).glob('*/canary_meta.json'):
        try:
            meta = json.loads(p.read_text())
            if meta['spec']['die'] != die:
                continue
            if item and meta['spec'].get('item', item) != item:
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


def _kv_core_kit(row):
    if Path(row.get('runner') or '').name == 'run_kit_kv.sh':
        return True
    path = (row.get('kit') or '').split(':', 1)[-1]
    try:
        return bool(path) and (Path(path) / 'run_kit_kv.sh').is_file()
    except OSError:
        return False


def reference_die(row):
    die = row['die']
    if die == 'qwen_kvsys' and _kv_core_kit(row):
        return 'qwen_kvsys_core'
    return {'cp1': 's81'}.get(die, die)


def assess(row, root, repo, run_git):
    if row.get('mode') == 'adopt':
        return True, 'existing run: observation only'
    ref_die = reference_die(row)
    try:
        spec = json.loads((Path(repo) / 'tools/flow_canary/canaries.json').read_text())
    except (OSError, ValueError):
        spec = None
    item = None
    if spec:
        item = next((c.get('item') for c in spec.get('canaries', []) if c.get('die') == ref_die), None)
    runs = _runs(root, ref_die, item)
    if not runs:
        return False, ('no reference canary for die ' + ref_die + (' item ' + item if item else '')
                       + '; register a reviewed reference canary first')
    newest = runs[-1]
    completed = [r for r in runs if r['done']]
    correction = row.get('canary_fix')
    if correction:
        return _corrective(correction, runs, root, ref_die)
    if not completed:
        return False, ('newest reference canary pending: ' + newest['ref']
                       + '; reviewed corrective kit only: re-enqueue --canary-fix ' + newest['ref'])
    bind = completed[-1]
    if bind['verdict'] != 'PASS':
        return False, ('newest completed reference canary failed: ' + bind['ref']
                       + '; reviewed corrective kit only: re-enqueue --canary-fix ' + bind['ref'])
    if not spec or 'watch' not in spec:
        return False, 'flow canary watch specification missing'
    watch = spec['watch']
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
