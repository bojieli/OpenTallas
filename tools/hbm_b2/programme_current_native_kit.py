"""Selected SOURCE13 PAGE_AW1 r10 native intake; default physical release OFF."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = 'results/hbm_programme_native_intake_0450'
TOP = 'ot_hgi_sfu_programme_store_r10'
MASTER = 'ot_sram_1r1w_512x256_m1_r2c2'


def prepare(repo):
    r = repo/PACKET
    model = json.loads((r/'model.json').read_text())
    for f in model['files']:
        assert hashlib.sha256((repo/f['file']).read_bytes()).hexdigest() == f['sha256']
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    selected_top=(repo/model['files'][0]['file']).read_text()
    if not re.search(r'parameter integer PAGE_AW=1, AW=10\+PAGE_AW',selected_top):
        raise ValueError('exact selected native PAGE_AW1/AW11 default contract changed')
    # No override: exact selected source already defaults PAGE_AW1/AW11 and
    # rejects PAGE_AW!=1. Official explicit inventory forbids param overrides.
    recipe = dict(top=TOP, params={}, files=[f['file'] for f in model['files']],
                  source_commit=commit, read_at_commit=False, defines=[], macros=[MASTER],
                  macro_placement=[dict(inst=m['inst'],xy_um=m['origin_um'],orient='R0',macro=MASTER)
                                   for m in model['macros']],
                  source='Exact selected SOURCE13 r10+leaf+real512nativeSRAM; no historical pstore body/proof alias')
    top = model['files'][0]
    profile = dict(source_commit=commit,family='SOURCE13_SELECTED_PROGRAMME_R10_PAGE_AW1',
                   release_eligible=False,qualification='SOURCE_PROOF_ONLY_NATIVE_UNROUTED',
                   component_proof_reset_cycles=4,added_face_cycles=0,
                   selected_effective_params=dict(PAGE_AW=1,AW=11),
                   endpoint_contract=dict(kind='INTERNAL_CORE',parent_partition='DISABLED_B113_LOCAL_MOVE',
                                          partition_rule='R2_INTERNAL_TIMED_IN_PARTITION'),
                   clock_ports=['clk'],reset_ports=['rst_n'],
                   source_manifest={f['file']:f['sha256'] for f in model['files']},
                   source_caller='SOURCE13 NW_hub/NE_hub.u_u_sfup_Q_q1 PAGE_AW1; disabled move only',
                   source_readset=PACKET+'/model.json',pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',
                   port_inventory=dict(top=TOP,source_file=top['file'],source_sha256=top['sha256'],
                                       ports=[[p['name'],p['direction'],p['width']]for p in model['ports']]),
                   native_capacity=dict(macros=44,master=MASTER,memory_bits=5767168,external_face_shell=False),
                   physical_reset_phase='HELD: actual provider rst_n_t352/t350 versus B113 parent reset; no64/4phase credit',
                   START='Exact collar.io_start_v→IOvalid stripe2bit26→p_sv_q; component phase PASS only;66route held')
    return recipe,profile,json.loads((r/'views.json').read_text())


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT)
    p.add_argument('--profile-out',type=Path);p.add_argument('--prepare-only',action='store_true')
    a,args=p.parse_known_args();recipe,profile,views=prepare(a.repo)
    if a.profile_out:a.profile_out.write_text(json.dumps(dict(recipe=recipe,profile=profile),indent=2)+'\n')
    if a.prepare_only:return
    # Explicit fail-closed API prerequisite: old GEN must not silently stage64.
    helper=(a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py').read_text()
    if 'component_proof_reset_cycles' not in helper:
        raise SystemExit('fresh selected body requires reviewed explicit nonrelease component reset selector43b3032d3; old64 intake refused')
    for key,val in {'--face-shell':'off','--recipe-key':TOP,'--clock-pin-entry':'on',
                    '--core-macros':'auto','--core-insertion':'none'}.items():
        if key in args and args[args.index(key)+1]!=val:raise ValueError(key+' must be '+val)
        if key not in args:args.extend([key,val])
    if '--wrapper'in args:raise ValueError('source/provider wrappers not allowed')
    if '--views'not in args:args.extend(['--views',str(a.repo/PACKET/'views.json')])
    if '--view'not in args:args.extend(['--view',views['view_list'][0]['view']])
    path=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
    sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('programme_native_backend',path)
    backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
    sys.argv=[str(path),*args];backend.main(recipe_overrides={TOP:recipe},source_profile=profile)


if __name__=='__main__':main()
