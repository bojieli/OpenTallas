"""Read-only complete converter receipt and every native image page qualification."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/home/ubuntu/OpenTallas-qwen-trained-native-execution');sys.path.insert(0,str(root/'tools'))
import qwen_trained_byte_provider as B,qwen_bounded_trained_driver as D
job=Path('/home/ubuntu/otjobs/qwen-trained-byte-conversion-pve1-20261002-r2');images=job/'images';go=json.loads((job/'GO.json').read_text());gc=(job/'GO.commit').read_text().strip();terminal=json.loads((job/'terminal.json').read_text())
assert terminal['verdict']=='PASS_COMPLETE_CHECKPOINT_BYTE_PRODUCTION_ONLY' and terminal['exit_code']==0
assert terminal['source_commit']=='4c0828691a61ce30402f5b26044e6ca2aebb45ad' and terminal['GO_commit']==gc=='6f3bb9e8bf793bb118719b75fc8e84468527af30'
assert json.loads(subprocess.check_output(['git','show',gc+':'+go['admission_record_path']],cwd=root))==go
assert B.sha(job/'actual_producer.log')==terminal['producer_log_sha256']
assert B.sha(images/'manifest.json')==terminal['manifest_sha256']
assert terminal['extents']==586 and terminal['image_bytes']==8824912128
n=B.native();back=B.TrainedByteBackend(images,n);D.bind_runtime(n,back);rows=[];seen=set()
for ref,im in back.manifest['images'].items():
 for page in im['segments']:
  p=images/page['file'];assert not p.is_symlink() and p.is_file() and p.stat().st_size==page['bytes'];assert p.name not in seen;seen.add(p.name);assert B.sha(p)==page['sha256'];rows.append(dict(provider_ref=ref,**page))
assert {p.name for p in images.glob('*.bin')}==seen
identity=back.manifest['identity'];snapshot=Path(identity['snapshot']);pins=[]
lock=json.loads((root/'compiler/models/qwen3-8b/checkpoint_source.json').read_text())
for file in lock['expected_files']:
 if not(file['path'].endswith('.safetensors')or file['path']in ('config.json','model.safetensors.index.json')):continue
 p=snapshot/file['path'];assert p.stat().st_size==file['size_bytes'] and B.sha(p)==file['sha256'];pins.append(file)
back.close();report=dict(schema='opentallas.Qwen.complete-trained-images-qualification.v1',PASS=True,job=str(job),images=str(images),source_commit=terminal['source_commit'],GO_commit=gc,terminal_sha256=B.sha(job/'terminal.json'),manifest_sha256=B.sha(images/'manifest.json'),producer_log_sha256=B.sha(job/'actual_producer.log'),checkpoint_files=pins,identity=identity,immutable_extents=586,immutable_image_bytes=8824912128,all_page_hashes_verified=True,pages=rows,scope=dict(full_checkpoint_byte_production_only=True,native_execution=False,actual_RTL=False,physical_credit=False,oracle_callbacks=0),runtime_driver_pin=B.sha(root/'tools/qwen_bounded_trained_driver.py'),runtime_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip())
print(json.dumps(report,sort_keys=True))
