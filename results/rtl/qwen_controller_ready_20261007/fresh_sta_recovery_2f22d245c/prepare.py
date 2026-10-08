import pathlib,json,hashlib,shutil
root=pathlib.Path('/srv/opentallas-scratch/claude/controller-sta-recovery-2f22d245c')
original=pathlib.Path('/srv/opentallas-scratch/claude/closure-loop/qfd_ctrl_ready_00-8be556c2e/routes/qfd_ctrl_ready_00_8be556c2e')
base=next((original/'work/orfs/results/asap7').glob('*/base'))
target=root/'orfs/results/asap7'/base.parent.name/'base';target.mkdir(parents=True,exist_ok=False)
inputs=[]
for leaf in ['6_final.odb','6_final.spef','6_final.sdc']:
 source=base/leaf;dest=target/leaf;dest.hardlink_to(source)
 inputs.append({'source':str(source),'private':str(dest),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':source.stat().st_size})
sdc=root/'signoff.sdc';sdc.write_bytes((original/'signoff.sdc').read_bytes())
inputs.append({'source':str(original/'signoff.sdc'),'private':str(sdc),'sha256':hashlib.sha256(sdc.read_bytes()).hexdigest(),'bytes':sdc.stat().st_size})
metrics=next((original/'work/orfs/logs/asap7').glob('*/base/5_2_route.json'));shutil.copyfile(metrics,root/'original_drc_metrics.json')
for f in ['sta.log','status']:shutil.copyfile(original/f,root/('original_'+f))
(root/'inputs.json').write_text(json.dumps({'original':str(original),'inputs':inputs,'metrics_source':str(metrics),'metrics_sha256':hashlib.sha256(metrics.read_bytes()).hexdigest()},indent=2)+'\n')
