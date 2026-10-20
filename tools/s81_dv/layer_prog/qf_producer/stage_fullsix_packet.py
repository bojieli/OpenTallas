#!/usr/bin/env python3
"""Stage immutable full-six inputs only. No elaboration, compile or simulation."""
import hashlib,io,json,subprocess,tarfile
from pathlib import Path
from head_local_contract import ROOT
b=ROOT/'results/rtl/s81_qf_producer_1019/sid6_vehicle'
packet=b/'fullsix_launch_packet'
host='ot-epyc4'
lane='/srv/opentallas-scratch/claude/s81-qf-producer-source-1019'
stage=lane+'/fullsix_frontend_01'
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as tf:
 for f in json.loads((b/'selected_vehicle_build_manifest.json').read_text())['files']:
  data=subprocess.check_output(['git','show',f['ref']+':'+f['path']]);assert hashlib.sha256(data).hexdigest()==f['sha256']
  ti=tarfile.TarInfo('src/'+f['path']);ti.size=len(data);tf.addfile(ti,io.BytesIO(data))
 for p in sorted(packet.iterdir()):
  if p.is_file():tf.add(p,arcname=p.name)
 for n in ['selected_vehicle_image_manifest.json','selected_vehicle_build_manifest.json']:
  tf.add(b/n,arcname=n)
data=buf.getvalue();tmp=Path('/tmp/s81-fullsix-frontprep.tar.gz');tmp.write_bytes(data)
subprocess.run(['scp',str(tmp),host+':'+lane+'/fullsix_frontprep.tar.gz'],check=True)
script=r'''
from pathlib import Path
import json,hashlib,shutil,tarfile
lane=Path('/srv/opentallas-scratch/claude/s81-qf-producer-source-1019');out=lane/'fullsix_frontend_01'
if out.exists():raise SystemExit('REFUSE_EXISTING_RUN_DIR')
out.mkdir()
with tarfile.open(lane/'fullsix_frontprep.tar.gz') as tf:tf.extractall(out,filter='data')
src=lane/'qnorm_source_bundle/retained_component_01';images=out/'images';images.mkdir()
for p in src.glob('*.viamap.hex'):shutil.copyfile(p,images/p.name)
for n in ['source_ctl.txt','expected_xq.mem','expected_reads.mem']:shutil.copyfile(src/n,out/n)
for r in json.load(open(out/'selected_vehicle_image_manifest.json'))['files']:
 p=lane/'selected_vehicle_images_01'/r['path'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 shutil.copyfile(p,images/p.name)
for r in json.load(open(out/'selected_vehicle_build_manifest.json'))['files']:
 assert hashlib.sha256((out/'src'/r['path']).read_bytes()).hexdigest()==r['sha256']
files=[]
for p in sorted(out.rglob('*')):
 if p.is_file():files.append(dict(path=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
(out/'frozen_inputs.json').write_text(json.dumps(dict(scope='Immutable staged inputs only; no frontend/build run',files=files,files_count=len(files),bytes=sum(x['bytes'] for x in files),source_ref='ceaed19c4',original_weight_images_job=3766810,all15_epochs=True,numeric_PASS=None,nativephase=None),indent=2)+'\n')
print('STAGED_NO_BUILD',len(files),sum(x['bytes'] for x in files))
'''
subprocess.run(['ssh',host,'python3 -'],input=script.encode(),check=True)
subprocess.run(['scp',host+':'+stage+'/frozen_inputs.json',str(packet/'frozen_inputs.json')],check=True)
print('Staged immutable inputs at',host+':'+stage,'; no frontend/build launched')
