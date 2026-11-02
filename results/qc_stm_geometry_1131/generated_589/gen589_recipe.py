from pathlib import Path
import json,shutil,tarfile,sys,subprocess,time
B=Path('/srv/opentallas-scratch2/claude/codex-qc-stm-count-1131');R=B/'private_gen_589';R.mkdir(exist_ok=False);S=R/'source';S.mkdir();F=Path('/srv/opentallas-scratch2/claude/wt/codex-qc-event-1131');old=B/'private_gen_172'
with tarfile.open(B/'stm_tool589.tgz') as t:t.extractall(S)
for p in (F/'physical').iterdir():
 if not(S/'physical'/p.name).exists():(S/'physical'/p.name).symlink_to(p,target_is_directory=p.is_dir())
for p in (F/'rtl').iterdir():
 if not(S/'rtl'/p.name).exists():(S/'rtl'/p.name).symlink_to(p,target_is_directory=p.is_dir())
(S/'results').symlink_to(F/'results',target_is_directory=True);(R/'overlay').mkdir();shutil.copyfile(B/'type_overlay.json',R/'overlay/type_overlay.json');shutil.copyfile(old/'overlay/native_sink_estimate.json',R/'overlay/native_sink_estimate.json');shutil.copyfile(old/'frozen_sidecar.json',R/'frozen_sidecar.json');p=json.load(open(old/'plan_isolated.json'));T=json.load(open(R/'overlay/type_overlay.json'));T['clock']['sink_bins_file']=str(R/'overlay/native_sink_estimate.json');p['partition_types']['slw_stm_v3']=T
# Preserve original native in-band epoch MSB on all38 isolated data/CTL bundles.
for x in p['ports']:x['epoch']=True
(R/'plan_isolated.json').write_text(json.dumps(p,separators=(',',':'))+'\n');FP=F/'physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json'
for x in FP.parent.iterdir():
 if x.name!='plan_qc52.json' and not(R/x.name).exists():(R/x.name).symlink_to(x,target_is_directory=x.is_dir())
sys.path.insert(0,str(S/'tools/die_plan'));import schema as C
err=C.validate(p);assert not err,err
cmd=['python3',str(S/'tools/die_plan/gen.py'),'phys',str(R/'plan_isolated.json'),'--out',str(R/'phys'),'--types','slw_stm_v3','--rtl-root',str(F),'--kit-rtl','slw_stm_v3='+str(B/'rtl-kit/kit_rtl.f'),'--hold-ff-margin','10','--bound-native-reset','slw_stm_v3']
receipt=dict(command=cmd,tools='58964d6ef',native_source='d90b109213c6949da87b330ef143d96bbe937934',scope='ONE authorized isolatedGEN only; no CAD/synth; exact source13/76homes; native reset opt-in',schema_errors=err,epoch_bundles_preserved=len(p['ports']),start_in=T['clock']['landing_contract']['collector_tree']['start_in'],start=time.time());(R/'gen_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
with open(R/'gen.log','w') as f:rc=subprocess.run(cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT).returncode
receipt.update(exit=rc,end=time.time());(R/'gen_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('GEN589',rc,flush=True)
if rc:sys.exit(rc)
import gen_phys as G,clock_landings as CL
files=[Path(x) for x in (B/'rtl-kit/kit_rtl.f').read_text().splitlines() if x.strip()];slots=G.kit_rtl_land_slots(CL.Landings(json.load(open(FP)),json.load(open(R/'frozen_sidecar.json'))),'slw_stm_v3',files);assert slots==json.load(open(B/'guard_native/land_slots.json'));k=R/'phys/slw_stm_v3';(k/'land_slots.json').write_text(json.dumps(slots,indent=1)+'\n');(R/'native_slot_join.json').write_text(json.dumps({'native_slots':25,'semantic_equal_guarded_native':True,'no_geometry_or_source_clock_fields':True,'source_API':'unmodified kit_rtl_land_slots(originalfullLandings,target,original13files)'},indent=2)+'\n');print('JOIN25 PASS',flush=True)
