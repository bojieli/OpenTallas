#!/usr/bin/env python3
"""Generate the exact HCOL half masters with their existing registered boundary.

The generic external face shell changes the h0->h1 accumulator phase by two
edges. This qualified source profile preserves the original zero-cycle split;
normal face, clock, geometry, LEC and timing gates still apply to every kit.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def value(args, flag):
    if flag not in args or args.index(flag) + 1 >= len(args):
        raise SystemExit(f'{flag} required')
    return args[args.index(flag) + 1]


def force(args, flag, expected):
    if flag in args and value(args, flag) != expected:
        raise SystemExit(f'{flag} must be {expected} for the registered HCOL source profile')
    if flag not in args:
        args.extend([flag, expected])


def validate_clock_contract(plan_dir, module, pins):
    required = {'clk_pair[0]', 'clk_pair[1]'}
    clocks = {p['name']: p for p in pins if p['name'].startswith('clk_pair')}
    if set(clocks) != required:
        raise ValueError('HCOL requires both unchanged scalar clk_pair pins')
    entries = json.loads((plan_dir / 'clock_entries.json').read_text())
    found = [entry for core_entries in entries.values() for entry in core_entries.values()
             if entry.get('module') == module]
    if not found:
        raise ValueError('HCOL plan has no per-instance clock entries')
    for entry in found:
        if entry.get('port') is not None or set(entry.get('merged_clock_ports', [])) != required:
            raise ValueError('HCOL requires explicit merged metadata for both preserved clock ports')
        cx, cy = entry['xy_um']
        if any(abs(p['y'] - cy) > 0.001 or abs(p['x'] - cx) > 0.1 for p in clocks.values()):
            raise ValueError('HCOL actual scalar clock pins are not at the declared common entry')
        if len({(p['x'], p['y']) for p in clocks.values()}) != 2:
            raise ValueError('HCOL scalar clock pins require distinct physical windows')
    return dict(ports=sorted(required), instances=len(found), no_bus_collapse=True)


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--diagnostic-plan', action='store_true')
    opts, rest = ap.parse_known_args()
    repo = opts.repo.resolve()
    views_path = Path(value(rest, '--views')).resolve()
    views = json.loads(views_path.read_text())
    view = next((v for v in views['view_list'] if v['view'] == value(rest, '--view')), None)
    if view is None:
        raise SystemExit('view is absent from the requested inventory')
    mod = view['module']
    allowed = {'ot_hbm_idx_score_hcol_h0': 0, 'ot_hbm_idx_score_hcol_h1': 1}
    if mod not in allowed:
        raise SystemExit(f'{mod} is not a canonical HCOL half master')
    half = allowed[mod]
    plan_file = Path(views['plan'])
    if not plan_file.is_absolute():
        plan_file = (views_path.parent / plan_file).resolve()
    plan_dir = plan_file.parent
    pins = json.loads((plan_dir / view['pins_file']).read_text())
    try:
        clock_check = validate_clock_contract(plan_dir, mod, pins)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    harden = repo / 'physical/die_plan/hbm/cores/harden'
    candidates = [v for v in json.loads((harden / 'recipes_split.json').read_text()).values()
                  if isinstance(v, dict) and v.get('functional_type') == f'score_hcol_h{half}']
    if not candidates:
        raise SystemExit('exact split source recipe missing')
    recipe = dict(candidates[0])
    shape = lambda r: (r['top'], r['files'], r.get('params', {}), r.get('macros', []))
    if any(shape(r) != shape(recipe) for r in candidates):
        raise SystemExit('ambiguous HCOL source variants in the split recipe inventory')
    if recipe['top'] != 'ot_hidx_score_hcol' or recipe['params'] != {'HALF': half, 'MUT': 0}:
        raise SystemExit('unexpected HCOL arithmetic parameter contract')
    if view.get('canonical_type'):
        raise SystemExit('use a canonical family view with identity pin buses, not a legacy per-piece cut map')
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    recipe.update(source_commit=commit, read_at_commit=True)
    for flag, expected in [('--face-shell', 'off'), ('--sigmax', 'M5'), ('--recipe-key', mod)]:
        force(rest, flag, expected)
    if '--core-insertion' not in rest:
        rest.extend(['--core-insertion', 'none'])
    profile = dict(source_commit=commit, family='HCOL_REGISTERED_NATIVE', added_face_cycles=0,
                   endpoint_contract=dict(kind='INTERNAL_CORE', partition_rule='R2_INTERNAL_TIMED_IN_PARTITION',
                                          source='rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv'),
                   qualification='UNROUTED_CANDIDATE', clock_ports=['clk_pair', 'clk_pair[0]', 'clk_pair[1]'],
                   reset_ports=['rst_col'], source_parameters=recipe['params'],
                   clock_contract=dict(preserved_ports=['clk_pair[0]', 'clk_pair[1]'],
                                       domain='one 833 ps die clock; explicit plan merged_clock_ports required',
                                       no_bus_collapse=True, plan_check=clock_check),
                   phase_edges=dict(key_to_cs_out=68 if half == 0 else 104,
                                    cs_in_to_cs_out=None if half == 0 else 36,
                                    generic_external_shell_forbidden=True))
    if opts.diagnostic_plan:
        profile['diagnostic_inputs'] = True
    generator = repo / 'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
    spec = importlib.util.spec_from_file_location('hcol_shared_kit', generator)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    sys.argv = [str(generator), *rest]
    gen.main(recipe_overrides={mod: recipe}, source_profile=profile)


if __name__ == '__main__':
    main()
