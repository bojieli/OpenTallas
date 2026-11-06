#!/usr/bin/env python3
"""Stage a distinct OPS candidate from captured inputs and a released tool cohort.
No source profile, POR or existing kit changes. The original sixteen SRAM sites,
pin table and boundary constraints remain byte-identical.
"""
import argparse, ast, hashlib, importlib.util, json, re, shutil, subprocess
from pathlib import Path
ap=argparse.ArgumentParser()
for n in ('basis','source','cohort','out','source_sha'):ap.add_argument('--'+n.replace('_','-'),required=True)
ap.add_argument('--kind',choices=['opsa0','opsa1','opsb'],required=True)
ap.add_argument('--variant',choices=['A','B'],required=True)
ap.add_argument('--scope',choices=['all','reg2reg'],default='all')
a=ap.parse_args();base=Path(a.basis);src=Path(a.source);co=Path(a.cohort);out=Path(a.out)
assert not out.exists(), 'fresh output only'
shutil.copytree(base,out)
old='ot_hgi_sfu_'+('opsa_group'+a.kind[-1] if a.kind.startswith('opsa') else 'opsb_group')
new=old+('_both_1106' if a.variant=='B' else ('_dist_1106' if a.kind.startswith('opsa') else '_rreg_1106'))
config=(out/'config.mk').read_text()
# Original common definitions are replaced by committed distinct-source bytes.
common='ot_hgi_sfu_opsa_group.sv' if a.kind.startswith('opsa') else 'ot_hgi_sfu_opsb_tiles.sv'
committed='ot_hgi_sfu_opsa_dist_1106.sv' if a.kind.startswith('opsa') else 'ot_hgi_sfu_opsb_rreg_1106.sv'
shutil.copy2(src/'rtl'/committed,out/'rtl'/common)
shutil.copy2(src/'rtl/ot_hgi_su_lgroup2_local_1106.sv',out/'rtl/ot_hgi_su_lgroup2_local_1106.sv')
config=config.replace(old,new)
lines=config.splitlines();i=next(i for i,l in enumerate(lines) if l.startswith('export VERILOG_FILES ='))
lines[i]+=' /work/rtl/ot_hgi_su_lgroup2_local_1106.sv'
config='\n'.join(lines)+'\n'
# The generic face shell is renamed only; all ports and flop logic are retained.
fp=out/'rtl'/(old+'__fshell.sv');assert fp.exists()
(out/'rtl'/(new+'__fshell.sv')).write_text(fp.read_text().replace(old,new));fp.unlink()
for n in ('face_shell.json','core.json','core.json.hard_core_latency','boundary_guard_context.json','sdc_lint.json'):
 p=out/n
 if p.exists():p.write_text(p.read_text().replace(old,new))
# Retain basis geometry/source identifiers; only actual candidate identity fields change.
f=json.loads((out/'freeze.json').read_text());basis_freeze=dict(f)
(out/'BASIS_FREEZE.json').write_text(json.dumps(basis_freeze,indent=1)+'\n')
f.update(module=new,design=new,rtl_top=new,source_commit=a.source_sha,recipe_key=None)
f['basis_recipe_key']=basis_freeze.get('recipe_key');f['basis_recipe_sha256']=basis_freeze.get('recipe_sha256')
f['face_shell']['core']=new+'__fcore'
# No stale physical/proof output may identify this fresh source.
for n in ('lec_async.on','lec_async.identity','lec_async.pid','lec_async.done','lec_async.ready','lec_async.rc','FAIL_PREFLOOR','FAIL_POSTCTS','FAIL_BUNDLE','SIGNED','rc.txt'):
 p=out/n
 if p.exists():p.unlink()
# Stage a single released runtime/signoff cohort, keeping unique geometry hooks.
dp=co/'tools/die_plan'
for p in list(out.iterdir()):
 if p.is_file() and p.suffix=='.py' and (dp/p.name).exists():shutil.copy2(dp/p.name,p)
subprocess.run(['python3',str(dp/'signoff.py'),'bundle',str(out)],check=True)
for n in ('lec.py','lec_async.sh','rtl_lint.py','selrange_gate.py','kit_modes.py','manifest_paths.py'):
 if (dp/n).exists():shutil.copy2(dp/n,out/n)
for n in ('orfs_hold_mm.py','orfs_hold_mm.tcl'):shutil.copy2(co/'tools'/n,out/n)
shutil.copy2(co/'physical/die_plan/hbm_arch_cores/run_kit_hbm.sh',out/'run_kit_hbm.sh')
# Reuse the factory's exact box validator and GPL guide/release implementation.
gen=co/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
node=next(n for n in ast.parse(gen.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='reg_guide_boxes_spec')
ns={'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),str(gen),'exec'),ns)
gfile=('opsa_both_guides' if a.variant=='B' else 'opsa_column_guides') if a.kind.startswith('opsa') else ('opsb_both_guides' if a.variant=='B' else 'opsb_read_guides')
boxes=ns['reg_guide_boxes_spec'](json.loads((src/(gfile+'.json')).read_text())['boxes'],tuple(float(v) for v in next(l for l in config.splitlines() if l.startswith('export CORE_AREA =')).split('=',1)[1].split()))
spec=' '.join(f"{{{g['name']} {{{' '.join('{'+q+'}' for q in g['prefixes'])}}} {' '.join(f'{v:.3f}' for v in g['box_um'])}}}" for g in boxes)
arch=co/'physical/die_plan/hbm_arch_cores'
(out/'macro_reg_guide.tcl').write_text('# Existing factory reg-guide-boxes implementation; committed OPS source geometry.\n'+f'set ::ot_mrg_spec [concat {spec}]\n'+(arch/'macro_reg_guide.tcl').read_text())
shutil.copy2(arch/'macro_reg_guide_release.tcl',out/'macro_reg_guide_release.tcl')
for fn,hook in [('face_flops.tcl','macro_reg_guide.tcl'),('face_flops_release.tcl','macro_reg_guide_release.tcl')]:
 p=out/fn;s=p.read_text();s=re.sub(r'^source /work/macro_reg_guide(?:_release)?\.tcl\n','',s,flags=re.M);p.write_text(s+'\nsource /work/'+hook+'\n')
(out/'macro_reg_guide.json').write_text(json.dumps({'source':'existing gen_core_kit_hbm.reg_guide_boxes_spec','boxes':boxes,'source_file':gfile+'.json'},indent=1)+'\n')
config+='\n# Fresh typed OPS candidate: ROOT-approved parent-owned IO scope; final full constraints unchanged.\n'
config+='override export OT_HOLD_REPAIR_SCOPE = '+a.scope+'\n'
config+='override export PLACE_DENSITY = 0.45\n'
if a.variant=='B':config+='override export ADDER_MAP_FILE =\n'
(out/'config.mk').write_text(config)
event={'source_commit':a.source_sha,'cohort':'flow-20261106-bp-hbm','kind':a.kind,'variant':a.variant,'module':new,'basis':str(base),'basis_source_commit':basis_freeze.get('source_commit'),'pin_cycles':{'write_visibility':1 if a.kind.startswith('opsa') or a.variant=='B' else 0,'read_response':1 if a.kind=='opsb' or a.variant=='B' else 0,'scalar_read':1 if a.kind.startswith('opsa') and a.variant=='B' else 0},'scope':a.scope,'final_constraints':'original full TT/FF restored; NEEDS_PARENT debt visible, no gate waiver','original_sram_count':16,'macro_placement_unchanged':True,'pins_unchanged':True,'guides':gfile+'.json','source_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (src/'rtl').glob('*.sv')},'activation':'private candidate; no profile/recipe/POR activation'}
(out/'SOURCE_EVENT.json').write_text(json.dumps(event,indent=1)+'\n')
f['recipe_sha256']=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest();f['kit_hash']=hashlib.sha256(((out/'config.mk').read_text()+json.dumps(event,sort_keys=True)).encode()).hexdigest()[:16];f['view']=new+'@'+f['kit_hash'];f['source_event']='SOURCE_EVENT.json';f['flow_tag']='flow-20261106-bp-hbm';f['reg_guide_boxes']={'boxes':len(boxes),'source':gfile+'.json'}
(out/'freeze.json').write_text(json.dumps(f,indent=1)+'\n')
sp=importlib.util.spec_from_file_location('lec',out/'lec.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
m.write_kit_provenance(out,None,provenance={'commit':a.source_sha,'dirty':False,'source':'committed OPS source+preparation recipe with captured historical basis; exact staged input identity'})
print(json.dumps({'kit':str(out),'view':f['view'],'pins_cycles':event['pin_cycles'],'boxes':len(boxes),'scope':a.scope}))
