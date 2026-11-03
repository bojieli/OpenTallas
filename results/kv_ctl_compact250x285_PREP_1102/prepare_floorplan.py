"""Prepare a private FP-only capsule from identity-matched GEN and genuine stage1. No EDA."""
from pathlib import Path
import json,hashlib,shutil,re,sys
new,old,packet,out,repo=map(Path,sys.argv[1:6]);assert not out.exists();join=json.load(open(new/'retained_subject_join.json'));assert join['status']=='SOURCE_IDENTITY_MATCHED' and not join['differences'];out.mkdir(parents=True);kit=out/'kit';shutil.copytree(new,kit)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def nickname(k):return re.search(r'export DESIGN_NICKNAME\s*=\s*(\S+)',(k/'config.mk').read_text()).group(1)
a=nickname(old);b=nickname(kit);retained=[]
for section in ['results','logs','reports']:
 src=old/'run'/section/'asap7'/a/'base';dst=kit/'run'/section/'asap7'/b/'base'
 for p in sorted(src.glob('1_*')):
  if not p.is_file():continue
  dst.mkdir(parents=True,exist_ok=True);q=dst/p.name;shutil.copy2(p,q);assert sha(p)==sha(q);retained.append(dict(source=str(p),relative=str(q.relative_to(kit)),sha256=sha(q)))
shutil.copy2(packet/'guard_fp_target.py',kit/'guard_fp_target.py')
base=kit/'run/results/asap7'/b/'base';assert (base/'1_synth.odb').is_file() and not list(base.glob('2_*'))
sys.path[:0]=[str(repo/'tools/die_plan'),str(repo/'physical/die_plan/qwen_kvsys/cores/harden')]
import fully_fixed_macros as F
from macro_sites import static_placement_tcl
sites=json.load(open(packet/'candidate_macro_sites_PREP.json'));assert len(sites)==6
macros=[];contract=[]
for s in sites:
 lef=kit/'macros'/('ctl_sram_1r1w_64x128_p192.lef');macros.append((s['name'],s['master'],str(lef),'',s['x'],s['y'],s['orient']));contract.append(dict(inst=s['name'],physical_inst=s['name'],lef=str(lef),outline_um=[s['width'],s['height']]))
lines=F.install(dict(fully_fixed_macros=True,hard_cores=contract),kit,macros,[4.32,4.32,246.24,280.8],repo)
blocks=[dict(inst=s['name'],master=s['master'],x=s['x'],y=s['y'],orient=s['orient']) for s in sites];(kit/'ctl_macro_place.tcl').write_text(static_placement_tcl(blocks).replace('setPlacementStatus FIRM','setPlacementStatus LOCKED'))
with (kit/'config.mk').open('a') as f:f.write('\n# Reviewed compact current-source six-SRAM physical event; no synthesis-input change.\nexport MACRO_PLACEMENT_TCL = /work/ctl_macro_place.tcl\n'+'\n'.join(lines)+'\n')
inputs={str(p.relative_to(kit)):sha(p) for p in kit.rglob('*') if p.is_file() and (str(p.relative_to(kit)).startswith(('rtl/','macros/')) or p.name in ['config.mk','constraint.sdc','clock_binding.json','make_tracks.tcl','pdn.tcl','ctl_macro_place.tcl','fully_fixed_macros.tcl','fully_fixed_macros.json','guard_fp_target.py'])};inputs.update({r['relative']:r['sha256'] for r in retained})
receipt=dict(status='PREPARED_FP_ONLY_NOT_RUN',source_GEN_kit=str(new),source_GEN_hash=json.load(open(new/'freeze.json'))['kit_hash'],retained_subject_join=join,retained_stage1=retained,unchanged_input_sha256=inputs,scope='ONE native do-floorplan only; no GEN/SYNTH/LEC/PLACE/CTS/GRT',source_FF_count=18768,native_rows_taps_PG='must be measured fresh; no old2*/3* checkpoint copied',source_core_profile_parent_binding='HELD/unadopted')
(kit/'floorplan_source_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('FP_ONLY_CAPSULE_PREPARED',kit,'retained_stage1_files',len(retained),'input_guards',len(inputs))
