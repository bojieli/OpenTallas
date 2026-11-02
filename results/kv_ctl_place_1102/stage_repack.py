"""Stage only: independent PLACE successor from exact qualified floorplan."""
import sys,json,shutil,hashlib
from pathlib import Path
old=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]).resolve();packet=Path(sys.argv[3]).resolve();assert not dest.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(old,dest,ignore=shutil.ignore_patterns('run','__pycache__'))
for section in ['results','reports','logs']:
 root=old/'run'/section
 for p in root.rglob('*'):
  if p.is_file() and p.name.startswith(('1_','2_')):
   q=dest/'run'/section/p.relative_to(root);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
for name in ['ctl_ff_repack.tcl','legalize_repack.json','repack_metric_certificate.json','FF_master_resize.json','ctl_ff_family_preserve.tcl']:
 shutil.copy2(packet/name,dest/name)
(dest/'ctl_repack_pre_gpl.tcl').write_text('source /work/face_flops.tcl\nsource /work/ctl_ff_repack.tcl\nsource /work/ctl_ff_family_preserve.tcl\n')
(dest/'ctl_repack_pre_dpl.tcl').write_text('source /work/face_flops_release.tcl\nsource /work/ctl_ff_repack.tcl\nsource /work/ctl_ff_family_preserve.tcl\n')

(dest/'ctl_repack_pre_resize.tcl').write_text('source /work/max_fanout.tcl\nsource /work/ctl_ff_family_preserve.tcl\n')
cfg=dest/'config.mk';cfg.write_text(cfg.read_text()+'\n# Reviewed state geometry; unchanged source and exact floorplan resume.\nexport PRE_GLOBAL_PLACE_TCL = /work/ctl_repack_pre_gpl.tcl\nexport PRE_DETAIL_PLACE_TCL = /work/ctl_repack_pre_dpl.tcl\nexport PRE_RESIZE_TCL = /work/ctl_repack_pre_resize.tcl\n')
bases=list((dest/'run/results/asap7').glob('*/base'));assert len(bases)==1 and (bases[0]/'2_floorplan.odb').is_file()
assert not list((dest/'run/results').rglob('3*'))
inputs=[p for p in dest.rglob('*') if p.is_file() and (p.is_relative_to(dest/'rtl') or p.is_relative_to(dest/'macros') or p.name in ['pins.json','constraint.sdc','io.tcl','pdn.tcl','core.json','1_synth_odb.v','lec.json'] or (p.is_relative_to(dest/'run/results') and p.name.startswith(('1_','2_'))))]
for p in inputs:assert sha(p)==sha(old/p.relative_to(dest)),p
receipt=dict(schema='opentallas.ctl_zero_cycle_place_repack.v1',scope='ONE PLACE only; no GEN/SYNTH/LEC/CTS/GRT/route/STA',parent=str(old),qualified_floorplan_sha256=sha(bases[0]/'2_floorplan.odb'),unchanged_inputs=[dict(relative=str(p.relative_to(dest)),sha256=sha(p)) for p in inputs],geometry={n:sha(dest/n) for n in ['config.mk','ctl_ff_repack.tcl','ctl_repack_pre_gpl.tcl','ctl_repack_pre_dpl.tcl','ctl_repack_pre_resize.tcl','ctl_ff_family_preserve.tcl']},source_cycles_delta=0,R8_delta=0,FF_inventory=18768,physical_x1_x2_retained=54)
(dest/'repack_source_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('STAGED_ONLY',dest,len(inputs),'unchanged inputs')
