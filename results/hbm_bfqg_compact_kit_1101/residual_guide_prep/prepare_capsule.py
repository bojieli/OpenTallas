from pathlib import Path
import hashlib,json,shutil
r=Path('/srv/opentallas-scratch2/claude/codex-bfqg-residual-guides-prep-2350')
original=Path('/srv/opentallas-scratch2/claude/codex-hbm-bfqg-compact-kit-1101/gen/ot_hgi_sm_xload_cl2_bfqg_69d23342c0e5')
k=r/'kit'
if k.exists():raise RuntimeError('refuse existing capsule')
shutil.copytree(original,k)
# Only the new owned copy loses downstream stage products so PLACE starts at actual native2floorplan.
removed=[]
for category in ['results','logs','reports']:
 for base in (k/'run'/category/'asap7').glob('*/base'):
  for p in list(base.iterdir()):
   if p.name.startswith(tuple(f'{i}_' for i in range(3,7))):
    removed.append(str(p.relative_to(k)))
    if p.is_dir():shutil.rmtree(p)
    else:p.unlink()
config=k/'config.mk';before=config.read_text();after=before.replace('export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl','export PRE_GLOBAL_PLACE_TCL = /work/bfqg_residual_pre_place.tcl').replace('export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl','export PRE_DETAIL_PLACE_TCL = /work/bfqg_residual_pre_detail.tcl')
if after==before or after.replace('/work/bfqg_residual_pre_place.tcl','/work/face_flops.tcl').replace('/work/bfqg_residual_pre_detail.tcl','/work/face_flops_release.tcl')!=before:raise RuntimeError('config delta not exact')
config.write_text(after)
files=['bfqg_residual_pre_place.tcl','bfqg_residual_pre_detail.tcl','macro_reg_guide.tcl','macro_reg_guide_release.tcl']
for name in files:shutil.copy2(r/name,k/name)
prov=k/'PROVENANCE.json';shutil.copy2(prov,k/'PROVENANCE.original_generated.json');p=json.loads(prov.read_text());new={name:hashlib.sha256((k/name).read_bytes()).hexdigest() for name in ['config.mk',*files]};p['files'].update(new);p['physical_update']=dict(kind='BFQG_RESIDUAL_GUIDE_PREP_ONLY',source_body_unchanged=True,public_ports_unchanged=True,added_FFs=0,added_cycles=0,config_delta=['PRE_GLOBAL_PLACE_TCL wrapper after original face anchor','PRE_DETAIL_PLACE_TCL wrapper after original face release'],original_generated_provenance='PROVENANCE.original_generated.json');prov.write_text(json.dumps(p,indent=1)+'\n')
receipt=dict(scope='PREP ONLY; NO CAD; ROOT+geometry review before PLACE/GRT',original=str(original),clone=str(k),source_commit=p['provenance']['commit'],model='guide_model.json',new_files_sha256=new,removed_owned_downstream_products=removed,source_RTL_and_SDC='copied unchanged',proof='existing native8650EQ/KEEP1064/reset4 copied; normal cache/preflight required',registration_release=False,source_alias=False,added_FFs=0,added_cycles=0)
(r/'PREP.json').write_text(json.dumps(receipt,indent=1)+'\n');(r/'.keep').write_text('owned native BFQG residual guide PREP; preserve original3193 failure\n');print('BFQG_GUIDE_CAPSULE_PREP',k,'NO_CAD')
