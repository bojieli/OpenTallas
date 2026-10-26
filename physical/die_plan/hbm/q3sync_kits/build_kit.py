#!/usr/bin/env python3
"""Build one physical q3 core kit from the qualified synchronous-reset closure.

Use the usual core-generator arguments after --, for example:
  build_kit.py --core edge --profile-dir SCRATCH -- --views VIEWS --view VIEW --out KITS

The plan module, canonical pin mapping, outlines and face-shell policy stay with the
ordinary core generator.  This selects the whole namespaced source closure, never
one sync top plus legacy helpers.  No physical run or geometry approval is implied.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
GEN_REL = 'tools/hbm_b2/q3sync/q3_sync_profile.py'
LIST_REL = 'tools/hbm_b2/q3sync/q3b.files'
TOPS = {
    'body': 'ot_hfd_coll_q3_body_core',
    'edge': 'ot_hfd_coll_q3_edge_core',
    'vm': 'ot_hfd_coll_q3_vm_core',
    'reduce': 'ot_hfd_coll_q2_reduce_core',
    'ring_ag': 'ot_hfd_coll_q2_ring_ag_core',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def materialize(core, profile_dir, root=REPO):
    """Generate and verify the pinned closure; return recipe, staging map, receipt."""
    root = Path(root).resolve()
    profile_dir = Path(profile_dir).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    census_path = profile_dir / 'census.json'
    subprocess.run([sys.executable, str(root / GEN_REL), '--root', str(root),
                    '--files', LIST_REL, '--out', str(profile_dir / 'rtl'),
                    '--census', str(census_path)], check=True)
    census = json.loads(census_path.read_text())
    if (census['status'] != 'PASS_GENERATED' or census['unclassified_total'] or
            census['unresolved_instantiations'] or not census['inputs_clean_at_commit']):
        raise SystemExit('NOT BUILT: q3sync source closure is incomplete or dirty')
    if census['modules_in_closure'] != 32:
        raise SystemExit('NOT BUILT: qualified q3sync cohort is exactly 32 modules')
    return recipe_from_census(core, census, profile_dir, root)


def recipe_from_census(core, census, profile_dir, root=REPO):
    """Keep source paths repo-relative while staging their generated profile bytes."""
    root, profile_dir = Path(root), Path(profile_dir)
    core_files = census['core_filelists'][core]
    wanted = set(core_files['files'])
    selected = [e for e in census['emitted'] if e['emitted'] in wanted]
    if {e['emitted'] for e in selected} != wanted:
        raise SystemExit('NOT BUILT: missing generated closure file')
    staged, sources = {}, []
    receipt = dict(name='q3sync', generator=GEN_REL, helper_list=LIST_REL,
                   source_commit=census['source_commit'], core=core,
                   modules_in_qualified_closure=32, data_cycle_delta=0,
                   reset='synchronous reset on existing reset pins; no reset logic removed',
                   source_files={}, generated_files={}, macros={})
    for item in selected:
        rel = item['source']
        p = Path(rel)
        if p.is_absolute() or '..' in p.parts:
            raise SystemExit('NOT BUILT: source path is not repository-relative')
        generated = profile_dir / 'rtl' / item['emitted']
        if not generated.is_file():
            raise SystemExit('NOT BUILT: generated source missing: ' + str(generated))
        sources.append(rel)
        staged[rel] = generated
        receipt['source_files'][rel] = sha(root / rel)
        receipt['generated_files'][rel] = sha(generated)
    for rel in core_files['macros']:
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise SystemExit('NOT BUILT: macro path is not repository-relative')
        sources.append(rel)
        receipt['macros'][rel] = sha(root / rel)
    top = TOPS[core]
    recipe = dict(files=sources, top=top, profile_top=top + '__q3sync', params={}, defines=[],
                  macros=[Path(p).stem for p in core_files['macros']],
                  source_commit=census['source_commit'], source='qualified q3sync closure')
    return recipe, staged, receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--core', required=True, choices=TOPS)
    ap.add_argument('--profile-dir', required=True)
    ap.add_argument('--diagnostic-plan', action='store_true',
                    help='allow an external scratch plan; not release evidence')
    ap.add_argument('core_args', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    args = a.core_args[1:] if a.core_args[:1] == ['--'] else a.core_args
    if '--view' not in args or '--views' not in args:
        ap.error('ordinary core-generator --view is required after --')
    view = args[args.index('--view') + 1]
    # Select a unique recipe key without mutating the shared recipe tables.
    if '--recipe-key' in args:
        ap.error('--recipe-key is supplied by this source profile')
    views_path = Path(args[args.index('--views') + 1]).resolve()
    views = json.loads(views_path.read_text())
    selected_view = next((v for v in views['view_list'] if v['view'] == view), None)
    allowed = {TOPS[a.core]}
    if a.core in ('reduce', 'ring_ag'):
        allowed.add('ot_hfd_coll_q2_hard_v8g__' + a.core)
    if selected_view is None or selected_view['module'] not in allowed:
        ap.error('selected plan view does not belong to the requested q3 core')
    plan_path = Path(views['plan'])
    if not plan_path.is_absolute():
        plan_path = views_path.parent / plan_path
    if not a.diagnostic_plan:
        for path in (views_path, plan_path.resolve()):
            if not path.is_relative_to(REPO):
                ap.error('external plan requires --diagnostic-plan: ' + str(path))
    recipe, staged, receipt = materialize(a.core, a.profile_dir)
    receipt['diagnostic_inputs'] = bool(a.diagnostic_plan)
    receipt['plan_module'] = selected_view['module']
    p = REPO / 'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
    sys.path.insert(0, str(p.parent))
    sys.path.insert(0, str(REPO / 'tools/die_plan'))
    spec = importlib.util.spec_from_file_location('q3sync_coregen', p)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    sys.argv = [str(p), *args, '--recipe-key', 'q3sync:' + view]
    gen.main(recipe_overrides={'q3sync:' + view: recipe}, source_overrides=staged,
             source_profile=receipt)


if __name__ == '__main__':
    main()
