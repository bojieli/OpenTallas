#!/usr/bin/env python3
"""Default-off regional StoreA component source intake. No parent adoption."""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PACKET=Path('results/hbm_storeA_regional_write_0900')
MODULE='ot_hnx_sfu_store_a_regional4_captured'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(repo):
 r=repo/PACKET;readset=json.loads((r/'native_readset.json').read_text());views=json.loads((r/'views.json').read_text())
 for item in readset['files']:
  if sha(repo/item['file'])!=item['sha256']:raise ValueError('source readset changed: '+item['file'])
 for f,key in [('native_pins.json','pins_sha256'),('GEN_plan.json','plan_sha256'),('core_macros.json','core_macros_sha256')]:
  if sha(r/f)!=readset[key]:raise ValueError('source intake model changed: '+f)
 pins=json.loads((r/'native_pins.json').read_text());assert len(pins)==5986
 commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 mac=json.loads((r/'core_macros.json').read_text())['cores'][MODULE]['macros'];assert len(mac)==32
 recipe=dict(top=MODULE,params={},files=[i['file']for i in readset['files']],defines=[],read_at_commit=False,source_commit=commit,macros=['ot_sram_1r1w_256x256_m2_r2c2'],macro_placement=[dict(inst=m['name'],macro=m['master'],xy_um=m['rect_um'][:2],orient=m['orient'])for m in mac],source='Disabled source-native32SRAM StoreA plus4same-edge regional capture copies; no current-parent or physical adoption')
 profile=dict(source_commit=commit,family='STOREA_REGIONAL4_SOURCE_PROPOSAL',release_eligible=False,qualification='SOURCE_PROOF_ONLY',component_proof_reset_cycles=4,added_face_cycles=0,clock_ports=['store0_clk','store0_clk[0]'],reset_ports=['store0_rst_n','capture_ctl_reset_n','capture_meta_reset_n'],endpoint_contract=dict(kind='INTERNAL_CORE',parent_partition='UNADOPTED_B113_SOURCE_EVENT',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION'),pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',source_manifest={i['file']:i['sha256']for i in readset['files']},native_capacity=dict(macros={'ot_sram_1r1w_256x256_m2_r2c2':32},external_face_shell=False),physical_reset_phase='UNQUALIFIED:actual native store reset and distinct selected n6/t22 capture reset inputs; component4 is not die qualification',physical_clock_phase='UNQUALIFIED:actual11714FFcontext+32SRAM needs current native clock/PG/source joins',parent_exactness='smallest capture/writer mechanisms plus separate wholecaller/nativeproof gates, no old component proof transfer')
 return recipe,profile,views

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--prepare-only',action='store_true');p.add_argument('--profile-out',type=Path);a,args=p.parse_known_args();recipe,profile,views=prepare(a.repo)
 if '--wrapper'in args:raise ValueError('no external face shell')
 for key,value in [('--face-shell','off'),('--recipe-key',MODULE),('--clock-pin-entry','on'),('--core-macros','auto'),('--core-insertion','none')]:
  if key in args and args[args.index(key)+1]!=value:raise ValueError('fixed '+key)
  if key not in args:args.extend([key,value])
 if '--views'not in args:args.extend(['--views',str(a.repo/PACKET/'views.json')])
 if '--view'not in args:args.extend(['--view',views['view_list'][0]['view']])
 if a.profile_out:a.profile_out.write_text(json.dumps(dict(recipe=recipe,profile=profile),indent=1)+'\n')
 if a.prepare_only:return
 path=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('storeA_regional_source_backend',path);backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend);sys.argv=[str(path),*args];backend.main(recipe_overrides={MODULE:recipe},source_profile=profile)
if __name__=='__main__':main()
