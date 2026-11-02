#!/usr/bin/env python3
"""One selected SOURCE13 native StoreA GEN/source-proof intake; no face shell."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MODULE='ot_hnx_sfu_store_a__da81d76763c9'
PACKET='results/hbm_storeA_sourceproof_intake_0030'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(repo):
 r=repo/PACKET;readset=json.loads((r/'readset.json').read_text());V=json.loads((r/'views.json').read_text());cap=json.loads((r/'storeA_GEN_capsule.json').read_text())
 for row in readset['files']:
  if digest(repo/row['file'])!=row['sha256']:raise ValueError('selected native input changed:'+row['file'])
 if V['plan_sha256']!=digest(r/'GEN_plan.json')or readset['pins_sha256']!=digest(r/'StoreA_pins.json'):raise ValueError('native plan/pins changed')
 if len(json.loads((r/'StoreA_pins.json').read_text()))!=6040:raise ValueError('native6040ABI required')
 commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 recipe=dict(top=MODULE,params={},files=[x['file']for x in readset['files']],source_commit=commit,read_at_commit=False,defines=[],macros=['ot_sram_1r1w_256x256_m2_r2c2'],macro_placement=[dict(inst=m['inst'],xy_um=m['origin_um'],orient='R0',macro=m['master'])for m in cap['macro_candidates']],source='Exact selected SOURCE13 native StoreA and two native generic children; real same-name32SRAM binding, no provider alias')
 abi=json.loads((repo/'results/hbm_l730_native_event_0015/providers/providers.json').read_text());ports=next(x['ports']for x in abi if x['module']==MODULE);source=readset['files'][2]
 source=next(x for x in readset['files']if x['file'].endswith(MODULE+'.sv'))
 profile=dict(source_commit=commit,family='SOURCE13_CURRENT_NATIVE_STOREA',release_eligible=False,qualification='NATIVE_SOURCEPROOF_INTAKE_UNROUTED',added_face_cycles=0,endpoint_contract=dict(kind='INTERNAL_CORE',parent_partition='q_b113*',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION'),clock_ports=['store0_clk'],reset_ports=['store0_rst_n'],source_manifest={x['file']:x['sha256']for x in readset['files']},source_caller='SOURCE13 B113 u_u_sfucore_Q_opstore_a',source_readset=PACKET+'/readset.json',pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',port_inventory=dict(top=MODULE,source_file=source['file'],source_sha256=source['sha256'],ports=[[p['name'],p['direction'],p['width']]for p in ports]),native_capacity=dict(macros=readset['native_capacity'],external_face_shell=False),conditional_formal_reset_edges=4,physical_reset_phase='NOT_QUALIFIED: actual wrappert22→native3edge→store; no inherited64/native4physicalreceipt',START='Opaque native command1742 producer join remainsheld; no dummySTART')
 return recipe,profile,V

def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--profile-out',type=Path);p.add_argument('--prepare-only',action='store_true');a,args=p.parse_known_args();recipe,profile,V=prepare(a.repo)
 forced={'--face-shell':'off','--recipe-key':MODULE,'--clock-pin-entry':'on','--core-macros':'auto','--core-insertion':'none'}
 for key,value in forced.items():
  if key in args and args[args.index(key)+1]!=value:raise ValueError(key+' must be '+value)
  if key not in args:args.extend([key,value])
 if '--wrapper'in args:raise ValueError('external source/provider wrappers are not allowed')
 if '--views'not in args:args.extend(['--views',str(a.repo/PACKET/'views.json')])
 if '--view'not in args:args.extend(['--view',V['view_list'][0]['view']])
 if a.profile_out:a.profile_out.write_text(json.dumps(dict(recipe=recipe,profile=profile),indent=2)+'\n')
 if a.prepare_only:return
 path=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('storeA_native_backend',path);backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend);sys.argv=[str(path),*args];backend.main(recipe_overrides={MODULE:recipe},source_profile=profile)
if __name__=='__main__':main()
