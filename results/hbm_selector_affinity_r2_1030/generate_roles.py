#!/usr/bin/env python3
"""Fresh current-source selector role trials; never executes physical flow."""
import sys,json,argparse,importlib.util,subprocess,shutil
from pathlib import Path
a=argparse.ArgumentParser();a.add_argument('--repo',required=True);a.add_argument('--views',required=True);a.add_argument('--slice',required=True);a.add_argument('--out',required=True);a=a.parse_args()
repo=Path(a.repo);out=Path(a.out);H=repo/'physical/die_plan/hbm_arch_cores';sys.path.insert(0,str(H))
sp=importlib.util.spec_from_file_location('role_gen',H/'gen_core_kit_hbm.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G)
mod='ot_hbm_idx_selector_static_sel';v=next(v for v in json.load(open(a.views))['view_list'] if v['module']==mod)
here=Path(__file__).resolve().parent
for tag,td in [('roles5_td',True),('roles5_notd',False)]:
 kd=out/(v['view'].replace('@','_')+'-'+tag)
 if kd.exists():raise SystemExit(f'refuse existing kit {kd}')
 recipes=G.load_recipes();rk=mod if mod in recipes else next(k for k in v['recipe_keys'] if k in recipes)
 rec=dict(recipes[rk]);rec['params']=dict(rec.get('params',{}),STRUCT=1,LOCAL_CTRL=1);rec['source_commit']='HEAD'
 rec['files']=list(dict.fromkeys(rec.get('files',[])+['rtl/hbm_accel/index/ot_hbm_idx_selector_compact.sv','rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv']))
 rec['macro_placement']=[]
 for q in range(4):
  for row in range(3):
   m=(2-row) if q%2==0 else row
   rec['macro_placement'].append(dict(inst=f'core.gq[{q}].gm[{m}].mem',macro='ot_sram_1r1w_256x256_m2_r2c2',xy_um=[68.526 if q<2 else 358.830,(27.948 if q%2==0 else 235.308)+row*69.12],orient='MY' if q<2 else 'R0'))
 sys.argv=['gen_core_kit_hbm.py','--views',a.views,'--view',v['view'],'--out',a.out,'--master-slice',a.slice,'--trial','--tag',tag]
 if not td:sys.argv+=['--orfs-var','GPL_TIMING_DRIVEN=0']
 G.main(recipe_overrides={rk:rec},source_overrides={'rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv':str(repo/'rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv')})
 model=kd/'role_model';subprocess.run([sys.executable,str(here/'model_roles.py'),str(kd),str(model)],check=True)
 subprocess.run([sys.executable,str(here/'render_roles.py'),str(kd),str(model)],check=True)
 shutil.copy2(model/'selector_roles_data.tcl',kd/'selector_roles_data.tcl');shutil.copy2(here/'selector_roles_guide.tcl',kd/'selector_roles_guide.tcl')
 shutil.copy2(H/'macro_reg_guide_release.tcl',kd/'selector_roles_release.tcl')
 with (kd/'face_flops.tcl').open('a') as f:f.write('\nsource /work/selector_roles_guide.tcl\n')
 with (kd/'face_flops_release.tcl').open('a') as f:f.write('\nsource /work/selector_roles_release.tcl\n')
 (kd/'candidate_settings.json').write_text(json.dumps(dict(params=rec['params'],GPL_TIMING_DRIVEN=td,placement_only=True,added_cycles=0,added_ff_vs_current_localctrl_candidate=0,unresolved='actual FF+SRAM endpoints/capacity/timing; no CTS or route'),indent=2)+'\n')
 G.stamp_generation_inputs(kd,repo)
 fz=json.load(open(kd/'freeze.json'));fz['candidate_settings']='candidate_settings.json';fz['kit_hash']=G.kit_hash(kd);(kd/'freeze.json').write_text(json.dumps(fz,indent=1)+'\n')
 print('FRESH_ROLE_CANDIDATE',kd,flush=True)
