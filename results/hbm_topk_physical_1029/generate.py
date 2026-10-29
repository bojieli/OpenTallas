#!/usr/bin/env python3
"""Current-plan WPIPE2 TOPK kit candidate; generation only, never launches P&R."""
import argparse,copy,hashlib,importlib.util,json,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
repo=Path(__file__).resolve().parents[2]
f=repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
sys.path.insert(0,str(f.parent));sys.path.insert(0,str(repo/'tools/die_plan'))
sp=importlib.util.spec_from_file_location('hbmkit',f);g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
plan=a.plan.resolve();d=json.load(open(plan/'die_plan.json'));t=d['partition_types']['root'];c=next(q for q in t['hard_cores'] if q['inst']=='u_hb_idx__link')
pins=plan/c['pins_file'];psha=hashlib.sha256(pins.read_bytes()).hexdigest();view='ot_hbm_idx_topk_link_static@'+psha[:12]
a.out.mkdir(parents=True,exist_ok=False)
views=dict(plan=str(plan/'die_plan.json'),view_list=[dict(view=view,module='ot_hbm_idx_topk_link_static',outline_um=c['outline_um'],pins_file=c['pins_file'],pins_sha256=psha,recipe_keys=['ot_hbm_idx_topk_link_static__650.16x500.04'],instances=['root.u_hb_idx__link'],placed=1)])
(a.out/'views.json').write_text(json.dumps(views,indent=2)+'\n')
# Exact current macro geometry; instance naming under generated face shell is handled by the generator.
cm=json.load(open(plan/'core_macros.json'))['cores']['ot_hbm_idx_topk_link_static'];mp=[]
for m in cm['macros']:
 x,y,x1,y1=m['rect_um'];mp.append(dict(k=m['name'],macro=m['master'],origin_um=[x,y],orient=m.get('orient','R0')))
(a.out/'macros.json').write_text(json.dumps(dict(macro_placement=mp),indent=2)+'\n')
sl=json.load(open(repo/'results/hbm_topk_wpipe_1029/slice.json'))
sl['basis']='Current C25c a4b0 plan; exact same outline/macros/center island geometry as prior trial. New WPIPE FF guide/census must be built, no inherited clock capacity.'
sl['instances']=['root.u_hb_idx__link'];sl['frozen']=False
(a.out/'slice.json').write_text(json.dumps(sl,indent=2)+'\n')
r=copy.deepcopy(g.load_recipes()['ot_hbm_idx_topk_link_static__650.16x500.04']);r['params']={'WRITE_PIPE_STAGES':2};r['source']='ROOT-approved default-off WPIPE2 coherent SRAM writer: +2 internal write visibility edges; current-plan trial only.'
r['source_commit']=g.subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();r['read_at_commit']=False
sys.argv=[str(f),'--views',str(a.out/'views.json'),'--view',view,'--out',str(a.out/'kits'),'--corner','TC','--hold-margin','0','--tag','_current_wpipe2','--macro-placement',str(a.out/'macros.json'),'--macro-inst-fmt','u_fcore.{k}','--master-slice',str(a.out),'--trial']
# slice helper find() accepts the module.json filename.
(a.out/'ot_hbm_idx_topk_link_static.json').write_bytes((a.out/'slice.json').read_bytes())
# Install the committed, opt-in logical guides before the standard kit hash is sealed.
original_kit_hash=g.kit_hash
model=json.load(open(repo/'results/hbm_topk_wpipe_1029/model_and_guides.json'))
# Prior native guide wholly overlapped the S0 bank2 guide. Same-area native strip now sits immediately to its west.
model['native_line_r_guide']['rect_um']=[4.32,207.36,25.92,278.64]
def guided_kit_hash(kd):
 kd=Path(kd)
 if not (kd/'topk_write_guides.tcl').exists():
  boxes={'native_line':model['native_line_r_guide']['rect_um']}
  for x in model['new_register_guides']:boxes['s%dr%d'%(x['stage'],x['banks'][0]%4)]=x['rect_um']
  spec=' '.join('{%s} {%s}'%(k,' '.join(map(str,v))) for k,v in boxes.items())
  body=(Path(__file__).parent/'write_guides.tcl').read_text()
  (kd/'topk_write_guides.tcl').write_text('set ::topk_write_boxes [dict create '+spec+']\n'+body)
  for hook,name in [('face_flops.tcl','topk_write_guides.tcl'),('face_flops_release.tcl','macro_reg_guide_release.tcl')]:
   with (kd/hook).open('a') as fd:fd.write('\nsource /work/'+name+'\n')
  import shutil
  shutil.copyfile(repo/'physical/die_plan/hbm_arch_cores/macro_reg_guide_release.tcl',kd/'macro_reg_guide_release.tcl')
 return original_kit_hash(kd)
g.kit_hash=guided_kit_hash
g.main(recipe_overrides={'ot_hbm_idx_topk_link_static__650.16x500.04':r},source_profile=dict(name='topk_wpipe2_current',source_commit=r['source_commit'],parameters=r['params'],added_internal_SRAM_visibility_edges=2,diagnostic_inputs=True))
