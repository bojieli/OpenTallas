import pathlib,json,hashlib
root=pathlib.Path('/srv/opentallas-scratch/claude/embedding-sta-recovery-2f22d245c')
records=[]
for kind,stamp in [('scale','1791392348'),('code','1791392521')]:
 name=f'qfd_embed_{kind}_bank_retained_24bd6a53b'
 original=pathlib.Path(f'/srv/opentallas-scratch/claude/closure-loop/qfd_embed_{kind}_bank_retained-24bd6a53b/routes/{name}.prev_{stamp}')
 base=next((original/'work/orfs/results/asap7').glob('*/base'))
 target=root/kind/'orfs/results/asap7'/base.parent.name/'base';target.mkdir(parents=True,exist_ok=False)
 inputs=[]
 for leaf in ['6_final.odb','6_final.spef','6_final.sdc']:
  source=base/leaf;dest=target/leaf;dest.hardlink_to(source)
  inputs.append({'source':str(source),'private':str(dest),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':source.stat().st_size})
 sdc=root/kind/'signoff.sdc';sdc.write_bytes((original/'signoff.sdc').read_bytes())
 inputs.append({'source':str(original/'signoff.sdc'),'private':str(sdc),'sha256':hashlib.sha256(sdc.read_bytes()).hexdigest(),'bytes':sdc.stat().st_size})
 logs=list((original/'work/orfs/logs/asap7').glob('*/base/5_2_route.json'))
 drc=json.loads(logs[0].read_text());(root/kind/'original_drc_metrics.json').write_bytes(logs[0].read_bytes())
 records.append({'kind':kind,'original':str(original),'original_status':(original/'status').read_text(),'inputs':inputs,'drc_source':str(logs[0]),'drc_sha256':hashlib.sha256(logs[0].read_bytes()).hexdigest()})
(root/'inputs.json').write_text(json.dumps(records,indent=2)+'\n')
