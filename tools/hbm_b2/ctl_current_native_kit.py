#!/usr/bin/env python3
"""Exact selected CTL component intake; no historical die-reset receipt."""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PACKET='results/hbm_ctl_native_intake_0440'
TOP='ot_hgi_sfu_core_split3__ctl'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(repo):
 p=repo/PACKET;r=json.loads((p/'readset.json').read_text());v=json.loads((p/'views.json').read_text());provider=json.loads((p/'provider.json').read_text())
 for row in r['files']:
  if digest(repo/row['file'])!=row['sha256']:raise ValueError('selected CTL closure changed')
 for k,f in [('pins_sha256','CTL_pins.json'),('plan_sha256','GEN_plan.json'),('planned_core_macros_sha256','core_macros.json')]:
  if digest(p/f)!=r[k]:raise ValueError('reviewed CTL inventory changed: '+f)
 if len(json.loads((p/'CTL_pins.json').read_text()))!=11810:raise ValueError('exact11810ABI required')
 commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 recipe=dict(top=TOP,params={},files=[x['file']for x in r['files']],source_commit=commit,read_at_commit=False,defines=[],macros=[],source='Exact selected SOURCE13 CTL+native VM static bridge+native reset relay, no provider alias')
 profile=dict(source_commit=commit,family='SOURCE13_CURRENT_NATIVE_CTL_COMPONENT',release_eligible=False,qualification='COMPONENT_SOURCEPROOF_ONLY_UNROUTED',component_proof_reset_cycles=4,conditional_formal_reset_edges=4,added_face_cycles=0,endpoint_contract=dict(kind='INTERNAL_CORE',parent_partition='q_b113*',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION'),clock_ports=['clk'],reset_ports=['rst_n'],pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',source_manifest={x['file']:x['sha256']for x in r['files']},source_readset=PACKET+'/readset.json',source_caller='SOURCE13 B113 u_u_sfucore_Q_ctl',port_inventory=dict(top=TOP,source_file=r['files'][0]['file'],source_sha256=r['files'][0]['sha256'],ports=[[x['name'],x['direction'],x['width']]for x in provider['ports']]),native_capacity=dict(macros={},external_face_shell=False),physical_reset_phase='HELD: exact wrapper t22, native SYNC2/TREE1 REGIONS4 reset relay, parent66START and source clock not qualified',START='Opaque exact1742 command source/event remains unjoined; no dummySTART')
 return recipe,profile,v

def main():
 a=argparse.ArgumentParser();a.add_argument('--repo',type=Path,default=ROOT);a.add_argument('--prepare-only',action='store_true');a.add_argument('--profile-out',type=Path);a,args=a.parse_known_args();recipe,profile,v=prepare(a.repo)
 if a.profile_out:a.profile_out.write_text(json.dumps(dict(recipe=recipe,profile=profile),indent=2)+'\n')
 if a.prepare_only:return
 path=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
 if 'component_proof_reset_cycles'not in path.read_text():raise ValueError('Requires reviewed explicit nonrelease component-reset selector; refusing legacy die64 receipt')
 fixed={'--face-shell':'off','--recipe-key':TOP,'--clock-pin-entry':'on','--core-macros':'auto','--core-insertion':'none'}
 for k,val in fixed.items():
  if k in args and args[args.index(k)+1]!=val:raise ValueError(k+' must be '+val)
  if k not in args:args.extend([k,val])
 if '--wrapper'in args:raise ValueError('No external source/capture wrapper allowed')
 if '--views'not in args:args.extend(['--views',str(a.repo/PACKET/'views.json')])
 if '--view'not in args:args.extend(['--view',v['view_list'][0]['view']])
 sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('ctl_native_backend',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);sys.argv=[str(path),*args];mod.main(recipe_overrides={TOP:recipe},source_profile=profile)
if __name__=='__main__':main()
