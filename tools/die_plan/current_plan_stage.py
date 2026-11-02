#!/usr/bin/env python3
"""Stage explicit current-plan DIE-CI inputs using the release-tree plan registry.

The legacy CI defaults name October-24 die_plan.json/B2l plans.  Do not guess new
paths: reuse release_tree_plan.py's plan/overlay/alias materializer.  This command
only stages source.  It never starts G2, STA, timers or a fleet job.

  current_plan_stage.py --repo REPO --rev SHA --registry ~/coord/tools/release_tree_plan.py \
      --dies qwen_compute,qwen_kvsys --out /scratch/current-ci

The output ci_static_argv.json is the existing die_ci.py run invocation, with
explicit --plan arguments and G2/STA disabled.  A later physical probe still needs
its exact source bundle and review-before-route approval.  Explicit --plan runs
retain die_ci.py's existing ad-hoc scope (no rack-system pass is implied).
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

SCHEMA = 'opentallas.current_plan_stage.v1'


def load_registry(path):
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location('_current_release_plan_registry', path)
    if spec is None or spec.loader is None:
        raise ValueError(f'cannot load plan registry {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ('PLANS', 'PIN_ALIASES', 'plan_archive_paths', 'materialize_plan',
                 'fetch_results_refs', 'materialize_pin_aliases'):
        if not hasattr(module, name):
            raise ValueError(f'plan registry lacks {name}')
    return module


def select_plans(registry, dies):
    selected = list(registry.PLANS)
    if dies:
        wanted = list(dict.fromkeys(dies.split(',')))
        known = {entry[0] for entry in selected}
        unknown = set(wanted) - known
        if unknown:
            raise ValueError('unknown current die(s): ' + ','.join(sorted(unknown)))
        selected = [entry for entry in selected if entry[0] in wanted]
    if not selected:
        raise ValueError('current plan registry selected no dies')
    return selected


def archive(repo, sha, paths, out):
    writer = subprocess.Popen(['git', '-C', str(repo), 'archive', sha, '--', *paths],
                              stdout=subprocess.PIPE)
    try:
        reader = subprocess.run(['tar', '-x', '-C', str(out)], stdin=writer.stdout)
    finally:
        writer.stdout.close()
    status = writer.wait()
    if status or reader.returncode:
        raise RuntimeError(f'current-plan archive failed: git={status} tar={reader.returncode}')


def stage(repo, rev, registry_path, out, dies=None, archive_fn=archive):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'output must be absent or empty (preserve existing inputs): {out}')
    registry_path = Path(registry_path).resolve()
    registry = load_registry(registry_path)
    selected = select_plans(registry, dies)
    sha = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--verify', rev + '^{commit}'],
                                  text=True).strip()
    registry.REPO = repo
    out.mkdir(parents=True, exist_ok=True)
    paths = registry.plan_archive_paths(selected)
    archive_fn(repo, sha, paths, out)
    plans = {}
    for name, plan_dir, src, overlays in selected:
        path = registry.materialize_plan(out, plan_dir, src, overlays)
        refs = registry.fetch_results_refs(out, path, rev=sha)
        aliases = registry.materialize_pin_aliases(path.parent, registry.PIN_ALIASES.get(name), rev=sha)
        # Missing/invalid materialized plans never create a usable manifest.
        json.loads(path.read_text())
        plans[name] = dict(path=str(path.relative_to(out)), source=src,
                           overlays=list(overlays), refs_fetched=refs, pin_aliases=aliases)
    argv = [sys.executable, str(out / 'tools/die_plan/die_ci.py'), 'run', '--repo', str(out),
            '--sha', sha, '--mode', 'manual', '--g2', 'none', '--sta', 'none', '--prev', 'none']
    for name, entry in plans.items():
        argv += ['--plan', f'{name}={out / entry["path"]}']
    record = dict(schema=SCHEMA, sha=sha, registry=str(registry_path),
                  registry_sha256=hashlib.sha256(registry_path.read_bytes()).hexdigest(),
                  plans=plans, scope='static current-plan inputs; G2/STA/rack systems NOT RUN',
                  ci_static_argv=argv)
    (out / 'current_plans.json').write_text(json.dumps(record, indent=2) + '\n')
    (out / 'ci_static_argv.json').write_text(json.dumps(argv, indent=2) + '\n')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--rev', required=True, help='explicit source commit/ref; pinned before extraction')
    parser.add_argument('--registry', required=True, help='existing coord tools/release_tree_plan.py')
    parser.add_argument('--dies', help='comma-separated current registry die keys (default all)')
    parser.add_argument('--out', required=True, help='new scratch output directory; existing data is never replaced')
    args = parser.parse_args(argv)
    try:
        result = stage(args.repo, args.rev, args.registry, args.out, args.dies)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'current-plan staging FAILED: {exc}\n')
    print(json.dumps({k: result[k] for k in ('sha', 'plans', 'scope')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
