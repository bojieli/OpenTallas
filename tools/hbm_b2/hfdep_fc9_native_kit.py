#!/usr/bin/env python3
"""Additive compact-fault FC9 HFDEP source-only native4 intake; no external face shell."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from vms_current_native_kit import digest, force, values, load_backend
ROOT = Path(__file__).resolve().parents[2]
MODULE = 'hfd_ep_static_fc9'
READSET = 'results/hbm_hfdep_native_0250/fc9/intake/readset.json'

def prepare(repo, view, views):
    readset = json.loads((repo / READSET).read_text())
    inventory = json.loads(views.read_text())
    if view != readset['view'] or inventory['plan_sha256'] != readset['plan_sha256']:
        raise ValueError('exact static SOURCE13 intake plan required')
    for row in readset['files']:
        if digest(repo / row['file']) != row['sha256']:
            raise ValueError('selected source changed: ' + row['file'])
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    recipe = dict(top=MODULE, params=readset['parameters'], files=[r['file'] for r in readset['files']],
                  defines=[], macros=['ot_sram_1r1w_64x512_m1_r2c2'], read_at_commit=False,
                  source_commit=commit, source='Additive FC9 selected-source projection; no old physical provider or parent adoption')
    profile = dict(source_commit=commit, family='HFDEP_FC9_NATIVE4_SOURCE_ONLY',
                   release_eligible=False, qualification='SOURCE_PROOF_ONLY', added_face_cycles=0,
                   component_proof_reset_cycles=4, clock_ports=['clk'], reset_ports=['rst_n'],
                   source_manifest={r['file']:r['sha256'] for r in readset['files']}, source_readset=READSET,
                   endpoint_contract=dict(kind='INTERNAL_CORE', parent_partition='UNJOINED_SOURCE_ONLY',
                                          partition_rule='R2_INTERNAL_TIMED_IN_PARTITION'),
                   pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',
                   native_capacity=dict(macros={'ot_sram_1r1w_64x512_m1_r2c2':4}, external_face_shell=False))
    return recipe, profile

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=ROOT)
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--profile-out',type=Path)
    a,forwarded=p.parse_known_args(argv)
    for key in ['--views','--view']:
        if len(set(values(forwarded,key)))!=1: raise ValueError('one '+key+' required')
    if values(forwarded,'--wrapper'): raise ValueError('no outside wrapper')
    for key,value in [('--face-shell','off'),('--recipe-key',MODULE),('--clock-pin-entry','on'),
                      ('--core-macros','auto'),('--core-insertion','none'),('--single-root-taps','off')]:
        force(forwarded,key,value)
    recipe,profile=prepare(a.repo,values(forwarded,'--view')[0],Path(values(forwarded,'--views')[0]))
    if a.profile_out:a.profile_out.write_text(json.dumps(dict(recipe=recipe,profile=profile),indent=1)+'\n')
    if a.prepare_only:return
    backend=load_backend(a.repo)
    sys.argv=[str(a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'),*forwarded]
    backend.main(recipe_overrides={MODULE:recipe},source_profile=profile)
if __name__=='__main__':main()
