#!/usr/bin/env python3
"""Additive regional HCOL565 native4 component source intake; no parent activation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from vms_current_native_kit import force, values, load_backend
ROOT = Path(__file__).resolve().parents[2]
BASE = Path('results/hbm_query_native_event_0135/hcol565_native_intake')

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare(repo, view, views_path):
    readset = json.loads((repo / BASE / 'READSET_PREP.json').read_text())
    inv = json.loads(views_path.read_text())
    row = next(v for v in inv['view_list'] if v['view'] == view)
    if row['module'] not in ['ot_hbm_idx_score_hcol_regional_head5_h0', 'ot_hbm_idx_score_hcol_regional_head5_h1']:
        raise ValueError('exact additive HCOL565 half required')
    plan = views_path.parent / inv['plan']
    pins_path = views_path.parent / row['pins_file']
    if digest(plan) != inv['plan_sha256'] or digest(pins_path) != row['pins_sha256']:
        raise ValueError('component plan or native pin model changed')
    pins = json.loads(pins_path.read_text())
    half = int(row['module'][-1])
    if len(pins) != 2290 + 33 * half or len({(p['bus'], p['bit']) for p in pins}) != len(pins):
        raise ValueError('true h0/h1 ABI required')
    clocks = [p for p in pins if p['bus'] == 'clk_pair']
    if sorted(p['bit'] for p in clocks) != [0, 1] or len({(p['x'], p['y']) for p in clocks}) != 2:
        raise ValueError('both actual clock port windows must survive')
    for item in readset['files']:
        if digest(repo / item['file']) != item['sha256']:
            raise ValueError('selected source changed: ' + item['file'])
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    params = dict(MUT=0, DELIVERED_RESET=1)
    recipe = dict(top=row['module'], params=params, files=[r['file'] for r in readset['files']],
                  defines=[], macros=[], read_at_commit=False, source_commit=commit,
                  source='Exact selected SOURCE13 math/reset definitions; explicit additive regional/head5 source projection')
    profile = dict(source_commit=commit, family='HCOL565_CURRENT_NATIVE4_SOURCE_ONLY',
                   release_eligible=False, qualification='SOURCE_PROOF_ONLY', added_face_cycles=0,
                   component_proof_reset_cycles=4, clock_ports=['clk_pair', 'clk_pair[0]', 'clk_pair[1]'],
                   reset_ports=['rst_col'], source_parameters=params,
                   source_manifest={r['file']: r['sha256'] for r in readset['files']},
                   endpoint_contract=dict(kind='INTERNAL_CORE', parent_partition='UNJOINED_SOURCE_ONLY',
                                          partition_rule='R2_INTERNAL_TIMED_IN_PARTITION'),
                   pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',
                   native_capacity=dict(macros={}, external_face_shell=False),
                   clock_contract=dict(preserved_ports=['clk_pair[0]', 'clk_pair[1]'],
                                       common_entry_reference_only=True, no_parent_clock_adoption=True),
                   reset_contract=dict(kind='DIE_DELIVERED_SYNCHRONOUS', local_release_edges=3,
                                       local_assert_edges=3, local_false_paths=False,
                                       bootstrap_component_native4=True, source_reset_DRST=0, regional_reset_copies=1),
                   phase_edges=dict(key_to_cs_out=68 if half == 0 else 104, added_edges=0,
                                    status='UNCHANGED_SOURCE_STRUCTURE_NOT_NEW_TIMING_MEASUREMENT'))
    return row['module'], recipe, profile

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=ROOT)
    p.add_argument('--prepare-only', action='store_true')
    p.add_argument('--profile-out', type=Path)
    args, forwarded = p.parse_known_args()
    for key in ['--views', '--view']:
        if len(set(values(forwarded, key))) != 1:
            raise ValueError('one ' + key + ' required')
    if values(forwarded, '--wrapper'):
        raise ValueError('no external wrapper')
    mod, recipe, profile = prepare(args.repo, values(forwarded, '--view')[0], Path(values(forwarded, '--views')[0]))
    for key, value in [('--face-shell', 'off'), ('--recipe-key', mod), ('--clock-pin-entry', 'on'),
                       ('--core-macros', 'auto'), ('--core-insertion', 'none'), ('--single-root-taps', 'off')]:
        force(forwarded, key, value)
    if args.profile_out:
        args.profile_out.write_text(json.dumps(dict(recipe=recipe, profile=profile), indent=1) + '\n')
    if args.prepare_only:
        return
    backend = load_backend(args.repo)
    sys.argv = [str(args.repo / 'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'), *forwarded]
    backend.main(recipe_overrides={mod: recipe}, source_profile=profile)

if __name__ == '__main__':
    main()
