"""Hold production kit waves until a completed reference canary shows NO-REGRESSION for the kit's flow.

Binding canary (COORD 10-26 05:10) = ANY completed released run of the reference die <= 24 h old, or the newest
completed one, whose flow equals the kit's; formerly only the NEWEST COMPLETED canary run of the reference die (canary.json whose
'src' equals canary_meta.json 'src_commit'); still-pending newer runs never mask it.
A releasing run binds a kit only when the kit's watched flow files equal the released canary's
(main's flow is not consulted: a kit runs on the flow it was generated from, AUTOPILOT-FIX 10-25 23:30).  A corrective kit names the reference failure by path (after the last '@').
Only runs of the die's CURRENT reference item (tools/flow_canary/canaries.json) count: after a reference switch the
old item's results neither bind nor hold (FLOW-CANARY 10-25: HBM rows kept binding the retired B2l calendar FAIL).
Reference die: cp1 -> s81; a qwen_kvsys hard-core kit (runner run_kit_kv.sh, or a kit dir holding one) ->
qwen_kvsys_core, the canary of that flow (gen_core_kit_kv.py), not the gen_phys type canary kv3_io_ft.
A completed run binds by its REGRESSION verdict vs the reference's recorded baseline (tools/flow_canary/baseline.py,
COORD CANARY GATING RULING 10-25 14:38), never by an absolute PASS of the reference design: NO-REGRESSION and INFO (the
run that set the baseline) release; REGRESSION and NO-BASELINE hold.
"""
import fnmatch
import importlib.util
import json
import os
import time
from pathlib import Path

RELEASE = ("NO-REGRESSION", "INFO")
# COORD RULING 2026-10-26 05:10 (CORES-KITS park (1), flow churn): a kit may route on ANY completed NO-REGRESSION
# canary of its reference die whose flow covers the kit's flow inputs, if that canary completed <= 24 h ago (the newest
# completed run stays eligible at any age, as before).  Newest-canary-only binding is dropped.  A completed canary of
# the kit's exact flow that is NOT released (REGRESSION / NO-BASELINE) still holds: evidence against that flow wins.
# AUTOPILOT_CANARY_NEWEST_ONLY=1 restores the old newest-only binding.
ANY_CANARY_MAX_AGE_S = 24 * 3600


def _baseline_mod(repo):
    for p in (Path(repo) / 'tools/flow_canary/baseline.py', Path(__file__).resolve().parent.parent / 'flow_canary/baseline.py'):
        if p.is_file():
            spec = importlib.util.spec_from_file_location('flow_canary_baseline', p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError('tools/flow_canary/baseline.py not found')


def regression(run, root, repo, seed=True):
    """(verdict, why) of one completed canary run vs its reference baseline; memoised on the run dict"""
    if 'reg' not in run:
        try:
            v = _baseline_mod(repo).verdict(run['run'], root, seed=seed)
            run['reg'] = (v['verdict'], v['why'])
        except Exception as e:                      # a broken verdict never releases rows
            run['reg'] = ('NO-BASELINE', 'regression verdict error ' + type(e).__name__ + ': ' + str(e))
    return run['reg']


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
        finished = None
        try:
            result = json.loads((p.parent / 'canary.json').read_text())
            if source and result.get('src') == source:
                verdict = result.get('verdict')
                finished = (p.parent / 'canary.json').stat().st_mtime
        except (OSError, ValueError, AttributeError):
            pass
        runs.append({'mtime': mtime, 'run': str(p.parent), 'src': source, 'verdict': verdict,
                     'done': verdict is not None, 'finished': finished,
                     'ref': source + '@' + str(p.parent / 'canary.json')})
    return sorted(runs, key=lambda r: (r['mtime'], r['run']))


def _flow_diff(run_git, repo, a, b, watch, spec=None, die=None):
    rc, paths, _ = run_git(['git', '-C', str(repo), 'diff', '--name-only', a, b], timeout=60)
    if rc:
        return None
    module_path = Path(__file__).resolve().parent.parent / "flow_canary/flow_watch.py"
    module_spec = importlib.util.spec_from_file_location("flow_canary_watch", module_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    changed = module.flow_paths(paths.splitlines(), spec or {"watch": watch}, die)
    if "tools/flow_canary/canaries.json" in changed and die:
        snapshots = []
        for revision in (a, b):
            status, content, _ = run_git(['git', '-C', str(repo), 'show',
                                          revision + ':tools/flow_canary/canaries.json'], timeout=60)
            try:
                snapshots.append(json.loads(content) if status == 0 else None)
            except ValueError:
                snapshots.append(None)
        if all(isinstance(s, dict) for s in snapshots) and not module.spec_flow_changed(*snapshots, die):
            changed.remove("tools/flow_canary/canaries.json")
    return changed


def _corrective(correction, runs, root, die, repo, seed):
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
    rv, _ = regression(r, root, repo, seed)
    if rv in RELEASE:
        return False, 'corrective canary ' + r['ref'] + ' is ' + rv + ' vs baseline; enqueue as a normal row'
    newer_ok = [x for x in runs if x['done'] and x['mtime'] > r['mtime'] and regression(x, root, repo, seed)[0] in RELEASE]
    if newer_ok:
        return False, ('a newer NO-REGRESSION canary exists (' + newer_ok[-1]['ref'] + ') than corrective canary '
                       + r['ref'] + '; enqueue as a normal row')
    return True, 'explicit corrective kit for ' + rv + ' canary ' + r['ref']


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


def assess(row, root, repo, run_git, seed=True):
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
        return _corrective(correction, runs, root, ref_die, repo, seed)
    if not completed:
        return False, ('newest reference canary pending: ' + newest['ref']
                       + '; reviewed corrective kit only: re-enqueue --canary-fix ' + newest['ref'])
    if not spec or 'watch' not in spec:
        return False, 'flow canary watch specification missing'
    watch = spec['watch']
    kit_source = row.get('src', '').rsplit('@', 1)[-1]
    if not kit_source:
        return False, 'queued kit source is missing'
    if os.environ.get('AUTOPILOT_CANARY_NEWEST_ONLY') == '1':
        return _bind_newest(completed[-1], kit_source, root, repo, run_git, seed, watch, spec, ref_die)
    return _bind_any(completed, kit_source, root, repo, run_git, seed, watch, spec, ref_die)


def _bind_any(completed, kit_source, root, repo, run_git, seed, watch, spec, ref_die, now=None):
    """COORD 10-26 05:10: newest first over the newest completed run + every completed run <= 24 h old; the first run
    whose flow equals the kit's flow decides (released -> route, else hold)."""
    now = time.time() if now is None else now
    newest = completed[-1]
    cands = [r for r in reversed(completed)
             if r is newest or (r.get('finished') and now - r['finished'] <= ANY_CANARY_MAX_AGE_S)]
    first_diff = None
    for r in cands:
        changed = _flow_diff(run_git, repo, r['src'], kit_source, watch, spec, ref_die)
        if changed is None:
            continue
        if changed:
            first_diff = first_diff or (r, changed)
            continue
        rv, rwhy = regression(r, root, repo, seed)
        if rv in RELEASE:
            age = '' if r is newest else ' (not the newest; completed <= 24 h ago, COORD 10-26 05:10)'
            return True, 'completed canary ' + rv + ' covers kit flow: ' + r['ref'] + age + ' (' + rwhy[:200] + ')'
        return False, ("completed reference canary of the kit's flow " + rv + ' vs baseline: ' + r['ref'] + ' ('
                       + rwhy[:300] + '); reviewed corrective kit only: re-enqueue --canary-fix ' + r['ref'])
    rv, rwhy = regression(newest, root, repo, seed)
    if rv not in RELEASE:
        return False, ('newest completed reference canary ' + rv + ' vs baseline: ' + newest['ref'] + ' (' + rwhy[:300]
                       + '); no completed canary <= 24 h old covers the kit flow; reviewed corrective kit only: '
                       're-enqueue --canary-fix ' + newest['ref'])
    if first_diff is None:
        return False, 'cannot compare queued kit flow source to released canary source'
    r, changed = first_diff
    return False, ('queued kit flow differs from released canary ' + newest['ref'] + ' and from every completed canary '
                   '<= 24 h old; regenerate from canaried flow: ' + ', '.join(changed[:4]) + ' (src ' + newest['src'] + ')')


def _bind_newest(bind, kit_source, root, repo, run_git, seed, watch, spec, ref_die):
    """pre-10-26 binding (AUTOPILOT_CANARY_NEWEST_ONLY=1): only the newest completed run binds"""
    rv, rwhy = regression(bind, root, repo, seed)
    if rv not in RELEASE:
        return False, ('newest completed reference canary ' + rv + ' vs baseline: ' + bind['ref'] + ' (' + rwhy[:300]
                       + '); reviewed corrective kit only: re-enqueue --canary-fix ' + bind['ref'])
    # AUTOPILOT-FIX 10-25 23:30: a row runs on the released canary's flow, judged by the KIT's own source.
    changed = _flow_diff(run_git, repo, bind['src'], kit_source, watch, spec, ref_die)
    if changed is None:
        return False, 'cannot compare queued kit flow source to released canary source'
    if changed:
        return False, ('queued kit flow differs from released canary ' + bind['ref'] + '; regenerate from canaried flow: '
                       + ', '.join(changed[:4]) + ' (src ' + bind['src'] + ')')
    return True, 'newest completed canary ' + rv + ' covers kit flow: ' + bind['ref'] + ' (' + rwhy[:200] + ')'
