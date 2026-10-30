#!/usr/bin/env python3
"""Generate source-only selector-localctrl placement diagnostics, never route."""
import argparse, importlib.util, json, sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--views',required=True);ap.add_argument('--slice',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
repo=Path(a.repo).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
mod='ot_hbm_idx_selector_static_sel';H=repo/'physical/die_plan/hbm_arch_cores'
sp=importlib.util.spec_from_file_location('selector_coregen',H/'gen_core_kit_hbm.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G)
V=json.load(open(a.views));v=next(x for x in V['view_list'] if x['module']==mod)
boxes=[(4.32,4.32,300.024,225.18),(4.32,225.18,300.024,446.04),(300.024,4.32,595.728,225.18),(300.024,225.18,595.728,446.04)]
for tag,td in [('localctrl_affinity_td',True),('localctrl_affinity_notd',False)]:
 kd=out/(v['view'].replace('@','_')+'-'+tag)
 if kd.exists():raise SystemExit(f'refuse existing kit {kd}')
 recipes=G.load_recipes();rk=mod if mod in recipes else next(k for k in v['recipe_keys'] if k in recipes)
 rec=dict(recipes[rk]);rec['params']=dict(rec.get('params',{}),LOCAL_CTRL=1)
 rec['macro_placement']=[]
 for q in range(4):
  for row in range(3):
   m=(2-row) if q%2==0 else row
   rec['macro_placement'].append(dict(inst=f'core.gq[{q}].gm[{m}].mem',macro='ot_sram_1r1w_256x256_m2_r2c2',xy_um=[68.526 if q<2 else 358.830,(27.948 if q%2==0 else 235.308)+row*69.12],orient='MY' if q<2 else 'R0'))
 argv=['gen_core_kit_hbm.py','--views',a.views,'--view',v['view'],'--out',str(out),'--master-slice',a.slice,'--trial','--tag',tag]
 if not td:argv+=['--orfs-var','GPL_TIMING_DRIVEN=0']
 sys.argv=argv
 G.main(recipe_overrides={rk:rec},source_overrides={'rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv':str(repo/'rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv')})
 rows=[]
 for q,b in enumerate(boxes):
  pref=[f'u_fcore.core.gq[{q}].',f'u_fcore.grctrl[{q}].local_copy.',f'u_fcore.core.gthreshold[{q}].local_copy.',f'u_fcore.grst[{q}].']
  pref += [f'u_fcore.core.hist[{k}]' for k in range(q*64,(q+1)*64)]
  pref += [f'u_fcore.core.selected[{q}]',f'u_fcore.core.qfault[{q}]',f'u_fcore.core.selected_v[{q}]']
  pref += [f'u_fcore.core.selected_line[{k}]' for k in range(q*592,(q+1)*592)]
  rows.append('{q%d {%s} %s}'%(q,' '.join('{'+x+'}' for x in pref),' '.join(str(x) for x in b)))
 (kd/'selector_quarter_guide.tcl').write_text('set ::ot_mrg_spec [concat '+' '.join(rows)+']\n'+(H/'macro_reg_guide.tcl').read_text())
 (kd/'selector_quarter_release.tcl').write_text((H/'macro_reg_guide_release.tcl').read_text())
 with (kd/'face_flops.tcl').open('a') as f:f.write('\nsource /work/selector_quarter_guide.tcl\n')
 with (kd/'face_flops_release.tcl').open('a') as f:f.write('\nsource /work/selector_quarter_release.tcl\n')
 (kd/'candidate_settings.json').write_text(json.dumps(dict(parameters=rec['params'],GPL_TIMING_DRIVEN=td,quarter_boxes_um=boxes,placement_only=True,added_cycles=0,added_ff=120,unresolved='parent W input -> E SRAM reach; no CTS/route'),indent=2)+'\n')
 fz=json.load(open(kd/'freeze.json'));fz['candidate_settings']='candidate_settings.json';fz['kit_hash']=G.kit_hash(kd);(kd/'freeze.json').write_text(json.dumps(fz,indent=1)+'\n')
 G.stamp_generation_inputs(kd,repo)
 fz=json.load(open(kd/'freeze.json'));fz['kit_hash']=G.kit_hash(kd);(kd/'freeze.json').write_text(json.dumps(fz,indent=1)+'\n')
 print('CANDIDATE',kd,flush=True)
