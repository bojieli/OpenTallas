"""Background flow-canary admission (METHODOLOGY12.14f).

Pending, absent and different-source references are advisory. An actual
REGRESSION matching the kit flow blocks until a newer matching measured release.
Kit source/watch integrity and corrective-reference identity still fail closed.
Geometry, preflight, formal and timing gates remain outside this module.
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
        except Exception as e:                      # evaluation errors remain distinct from an absent baseline
            run['reg'] = ('NO-BASELINE', 'regression verdict error ' + type(e).__name__ + ': ' + str(e))
    return run['reg']


def _runs(root, die, item=None):
    runs = []
    for p in Path(root).glob('*/canary_meta.json'):
        try:
            meta = json.loads(p.read_text())
            if meta['spec']['die'] != die:
                continue
            # FLOW-SHARED-6 2026-10-27: candidate-branch A/B runs (source under flow-canary/ab/) are not reference
            # canaries of any main flow: HBM kits were held by the f9d9190f1 A/B run as 'newest completed reference'.
            if '/flow-canary/ab/' in str(meta.get('src', '')):
                continue
            # FLOW-SHARED-9 2026-10-27 (COORD 19:36 (3)): canaries run from immutable commits only -- a run whose source is
            # a mutable lane worktree (not a flow-canary/sources/<sha> snapshot) never binds or holds kits.
            src = str(meta.get('src', '') or '')
            if src and '/flow-canary/sources/' not in src:
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


def _corrective(correction, runs, root, die, repo, seed, validate_only=False):
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
    if validate_only:
        return True, 'corrective reference recorded: ' + r['ref']
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
    # Historical queue rows use the same KV alias accepted by per-die flow tags.
    # Canonicalise before deciding whether the core or partition flow applies.
    die = {'kv': 'qwen_kvsys'}.get(row['die'], row['die'])
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
    if not spec or 'watch' not in spec:
        return False, 'flow canary watch specification missing'
    kit_source = row.get('src', '').rsplit('@', 1)[-1]
    if not kit_source:
        return False, 'queued kit source is missing'
    correction = row.get('canary_fix')
    if correction:
        valid, why = _corrective(correction, runs, root, ref_die, repo, seed, validate_only=True)
        if not valid:
            return False, why
    completed = [r for r in runs if r['done']]
    if not completed:
        return True, ('background canary advisory: reference pending' if runs else
                      'background canary advisory: no reference result')
    return _bind_any(completed, kit_source, root, repo, run_git, seed, spec['watch'], spec, ref_die)


def _bind_any(completed, kit_source, root, repo, run_git, seed, watch, spec, ref_die, now=None):
    """METHODOLOGY12.14f: background references block only on an actual matching regression.

    Latest matching measured verdict wins. Unknown/no-baseline results do not
    erase an older measured regression; source changes are advisory until tested.
    Corrective annotations cannot override a regression of the same flow.
    """
    for r in reversed(completed):
        changed = _flow_diff(run_git, repo, r['src'], kit_source, watch, spec, ref_die)
        if changed is None:
            return False, 'source integrity error: cannot compare kit flow with canary ' + r['ref']
        if changed:
            continue
        rv, rwhy = regression(r, root, repo, seed)
        if rv in RELEASE:
            return True, 'completed canary ' + rv + ' covers kit flow: ' + r['ref'] + ' (' + rwhy[:200] + ')'
        if rv == 'NO-BASELINE' and rwhy.startswith('regression verdict error'):
            return False, 'matching canary evaluation error: ' + rwhy
        if rv == 'REGRESSION':
            return False, ('matching reference canary REGRESSION: ' + r['ref'] + ' (' + rwhy[:300] + ')')
    return True, 'background canary advisory: no measured regression of this kit flow'


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
