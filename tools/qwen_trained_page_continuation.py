#!/usr/bin/env python3
"""Qualify immutable historical codec pages; exclusive copy requires source-bound GO."""
import argparse,ast,hashlib,json,os,subprocess
from pathlib import Path
from importlib.metadata import version
import qwen_trained_byte_provider as B

def recipe_function(source,name):
 return ast.dump(next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef)and x.name==name),include_attributes=False)

def check_recipe(old,old_provider_source,n):
 """Only producer inventory/control may differ; all byte-producing recipes stay exact."""
 if old['native_sha256']!=hashlib.sha256(B.canonical(n)).hexdigest():raise ValueError('continuation native identity')
 if old['checkpoint_lock_sha256']!=B.sha(B.ROOT/'compiler/models/qwen3-8b/checkpoint_source.json'):raise ValueError('continuation lock identity')
 lock=json.loads((B.ROOT/'compiler/models/qwen3-8b/checkpoint_source.json').read_text())
 if old['checkpoint_revision']!=lock['revision']:raise ValueError('continuation revision identity')
 expected={x['path']:x['sha256']for x in lock['expected_files']if x['path'].endswith('.safetensors')}
 if old['checkpoint_files_sha256']!=expected:raise ValueError('continuation shard identity')
 if old['runtime_package_versions']!={k:version(k)for k in ('numpy','torch','safetensors')}:raise ValueError('continuation codec package identity')
 if hashlib.sha256(old_provider_source.encode()).hexdigest()!=old['source_sha256']['tools/qwen_trained_byte_provider.py']:raise ValueError('continuation historical source identity')
 current=(B.ROOT/'tools/qwen_trained_byte_provider.py').read_text()
 for name in ('matrix_rows','bfbytes'):
  if recipe_function(old_provider_source,name)!=recipe_function(current,name):raise ValueError('continuation byte recipe changed '+name)
 required={'tools/qwen_trained_byte_provider.py','tools/qwen_hbm_complete_executor.py','tools/qwen3_deployment_quality.py','tools/h3_qwen_complete_native.py','compiler/models/qwen3-8b/checkpoint_source.json'}
 if set(old['source_sha256'])!=required:raise ValueError('unsupported historical recipe pin inventory')
 for path,pin in old['source_sha256'].items():
  if path!='tools/qwen_trained_byte_provider.py'and B.sha(B.ROOT/path)!=pin:raise ValueError('continuation source/tool identity '+path)
 target=dict(old);target['source_sha256']={p:B.sha(B.ROOT/p)for p in B.PINS}
 return target

def page_inventory(directory,n):
 directory=Path(directory);ex=B.extents(n);allowed={p[k]for p in B.matrix_inventory(n).values()for k in ('code_ref','scale_ref')if p[k]is not None};pages=[];groups={}
 for path in sorted(directory.glob('*.bin')):
  if path.is_symlink():raise ValueError('continuation page symlink')
  receipt=path.with_suffix('.json')
  if receipt.is_symlink():raise ValueError('continuation receipt symlink')
  record=json.loads(receipt.read_text());matches=[r for r in allowed if path.name==r.replace('.','_')+'_'+str(record['start'])+'.bin']
  if len(matches)!=1 or record['file']!=path.name:raise ValueError('continuation page ownership')
  ref=matches[0]
  if record['bytes']<=0 or record['start']<0 or record['start']+record['bytes']>ex[ref]['bytes']or path.stat().st_size!=record['bytes']or B.sha(path)!=record['sha256']:raise ValueError('continuation page bytes/hash')
  pages.append(dict(provider_ref=ref,record=record,receipt_sha256=B.sha(receipt)));groups.setdefault(ref,[]).append(record)
 extra={p.name for p in directory.glob('*.json')}-{p['record']['file'][:-4]+'.json'for p in pages}-{'producer_identity.json'}
 if extra:raise ValueError('unsupported historical image records')
 complete=[]
 for ref,records in groups.items():
  end=0
  for record in sorted(records,key=lambda p:p['start']):
   if record['start']!=end:raise ValueError('continuation page gap/overlap')
   end+=record['bytes']
  if end==ex[ref]['bytes']:complete.append(ref)
 if not pages:raise ValueError('no qualified continuation pages')
 return pages,sorted(complete)

def qualify(old_job,n=None):
 job=Path(old_job).resolve();images=job/'images';n=B.native()if n is None else n
 old=json.loads((images/'producer_identity.json').read_text());go=json.loads((job/'GO.json').read_text());terminal=json.loads((job/'terminal.json').read_text());run=json.loads((job/'run_start.json').read_text());go_commit=(job/'GO.commit').read_text().strip()
 archived=json.loads(subprocess.check_output(['git','show',go_commit+':'+go['admission_record_path']],cwd=B.ROOT))
 if archived!=go or terminal['source_commit']!=go['source_commit']or run['source_commit']!=go['source_commit']or terminal['GO_commit']!=go_commit or run['GO_commit']!=go_commit or terminal['verdict']!='FAIL_INCOMPLETE'or terminal['exit_code']!=1:raise ValueError('continuation actual failed-run provenance')
 if terminal['producer_log_sha256']!=B.sha(job/'actual_producer.log'):raise ValueError('continuation failed-run log identity')
 old_source=subprocess.check_output(['git','show',go['source_commit']+':tools/qwen_trained_byte_provider.py'],cwd=B.ROOT,text=True)
 for path,pin in old['source_sha256'].items():
  if hashlib.sha256(subprocess.check_output(['git','show',go['source_commit']+':'+path],cwd=B.ROOT)).hexdigest()!=pin or go['source_sha256'].get(path)!=pin:raise ValueError('historical admitted codec pin '+path)
 target=check_recipe(old,old_source,n);pages,complete=page_inventory(images,n)
 return dict(schema='opentallas.Qwen.trained-page-continuation.v1',old_job=str(job),old_source_commit=go['source_commit'],old_GO_commit=go_commit,old_GO_sha256=B.sha(job/'GO.json'),old_terminal_sha256=B.sha(job/'terminal.json'),old_identity_sha256=B.sha(images/'producer_identity.json'),old_identity=old,target_identity=target,pages=pages,complete_extents=complete,verified_page_bytes=sum(p['record']['bytes']for p in pages),matching_byte_recipe=True,matching_checkpoint_native_library_identity=True,source_inventory_change_explicit=True,old_artifacts_mutated=False)

def copy_qualified(report,target,admission,go_commit):
 from qwen_trained_native_run import validate_admission,guard
 validate_admission(admission,go_commit)
 digest=hashlib.sha256(B.canonical(report)).hexdigest()
 if admission.get('historical_page_continuation_sha256')!=digest:raise ValueError('source-bound continuation GO required')
 if qualify(report['old_job'])!=report:raise ValueError('qualified historical pages changed')
 target=Path(target);guard(admission,target,report['verified_page_bytes']);target.mkdir(exist_ok=False)
 images=Path(report['old_job'])/'images'
 for page in report['pages']:
  record=page['record'];source=images/record['file'];h=hashlib.sha256();fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW)
  with os.fdopen(fd,'rb')as reader,(target/record['file']).open('xb')as writer:
   before=os.fstat(reader.fileno())
   for block in iter(lambda:reader.read(8<<20),b''):writer.write(block);h.update(block)
   after=os.fstat(reader.fileno());writer.flush();os.fsync(writer.fileno())
   attrs=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
   if attrs(before)!=attrs(after)or h.hexdigest()!=record['sha256']:raise ValueError('page changed during exclusive continuation copy')
  with(target/source.with_suffix('.json').name).open('xb')as f:f.write(B.canonical(record));f.flush();os.fsync(f.fileno())
 for name,value in [('producer_identity.json',report['target_identity']),('continuation_receipt.json',report)]:
  with(target/name).open('xb')as f:f.write(B.canonical(value));f.flush();os.fsync(f.fileno())
 guard(admission,target)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--old-job',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--copy-to',type=Path);p.add_argument('--admission',type=Path);p.add_argument('--go-commit');a=p.parse_args();report=qualify(a.old_job)
 if a.copy_to:
  if not a.admission or not a.go_commit:p.error('exclusive copy requires fresh admission/GO')
  copy_qualified(report,a.copy_to,json.loads(a.admission.read_text()),a.go_commit)
 else:
  with a.report.open('xb')as f:f.write(B.canonical(report))
 print(json.dumps(dict(pages=len(report['pages']),bytes=report['verified_page_bytes'],copied=bool(a.copy_to))))
