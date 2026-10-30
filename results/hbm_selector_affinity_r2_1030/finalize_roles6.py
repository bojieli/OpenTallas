#!/usr/bin/env python3
"""Apply complete consumer-role model to fresh, never-run placement kits."""
import sys,json,shutil,subprocess,importlib.util
from pathlib import Path
repo,R=map(Path,sys.argv[1:3]);H=repo/'physical/die_plan/hbm_arch_cores';sys.path.insert(0,str(H))
sp=importlib.util.spec_from_file_location('role_gen',H/'gen_core_kit_hbm.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G)
ks=sorted((R/'kits').glob('*-roles6_*'));assert len(ks)==2
model=Path(sys.argv[3]) if len(sys.argv)>3 else R/'model6_disjoint';revision=sys.argv[4] if len(sys.argv)>4 else 'v3';s=json.load(open(model/'summary.json'))
assert not s['macro_halo_island_collisions'] and s['min_same_column_macro_channel_um']>=10.8
assert s['station_box_bound_gt405']==0 and s['direct_same_quarter_sram_rd_to_wd_bound_um']<=405
assert not s.get('region_overlap_pairs',[])
for K in ks:
 assert not (K/'run').exists(),'kit already run: do not mutate it'
 for name in ['macro_placement.tcl','core_infra_plan.json','pins.json','plan_pins.json']:
  assert (K/name).read_bytes()==(ks[0]/name).read_bytes(),f'{name} differs across variants'
 dst=K/('role_model_'+revision)
 if dst.exists():
  assert (K/'selector_roles_data.tcl').read_bytes()==(model/'selector_roles_data.tcl').read_bytes()
  subprocess.run([sys.executable,str(repo/'tools/die_plan/kit_preflight.py'),'--contract','--plan-dir','/srv/opentallas-scratch2/claude/die-hbm-32/plan/d32q','--out',str(K/f'preflight_candidate_{revision}.json'),str(K)],check=True)
  print('ROLES6_G1_READY_FOR_LOOK',K,flush=True);continue
 shutil.copytree(model,dst)
 shutil.copy2(model/'selector_roles_data.tcl',K/'selector_roles_data.tcl')
 shutil.copy2(R/'selector_roles_guide.tcl',K/'selector_roles_guide.tcl')
 subprocess.run([sys.executable,str(R/'render_roles.py'),str(K),str(dst)],check=True)
 fz=json.load(open(K/'freeze.json'));fz['placement_role_model']=f'role_model_{revision}/summary.json';(K/'freeze.json').write_text(json.dumps(fz,indent=1)+'\n')
 G.stamp_generation_inputs(K,repo)
 fz=json.load(open(K/'freeze.json'));fz['kit_hash']=G.kit_hash(K);(K/'freeze.json').write_text(json.dumps(fz,indent=1)+'\n')
 subprocess.run([sys.executable,str(repo/'tools/die_plan/kit_preflight.py'),'--contract','--plan-dir','/srv/opentallas-scratch2/claude/die-hbm-32/plan/d32q','--out',str(K/f'preflight_candidate_{revision}.json'),str(K)],check=True)
 print('ROLES6_G1_READY_FOR_LOOK',K,flush=True)
