"""Read-only qualification and exclusive-copy failures; no trained numerical claim."""
import copy,hashlib,json,sys
from pathlib import Path
from importlib.metadata import version
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_trained_byte_provider as B
import qwen_trained_page_continuation as C

def identity_fixture(n,source):
 lock=json.loads((B.ROOT/'compiler/models/qwen3-8b/checkpoint_source.json').read_text())
 paths=['tools/qwen_trained_byte_provider.py','tools/qwen_hbm_complete_executor.py','tools/qwen3_deployment_quality.py','tools/h3_qwen_complete_native.py','compiler/models/qwen3-8b/checkpoint_source.json']
 pins={p:B.sha(B.ROOT/p)for p in paths};pins[paths[0]]=hashlib.sha256(source.encode()).hexdigest()
 return dict(native_sha256=hashlib.sha256(B.canonical(n)).hexdigest(),checkpoint_lock_sha256=B.sha(B.ROOT/paths[-1]),checkpoint_revision=lock['revision'],checkpoint_files_sha256={x['path']:x['sha256']for x in lock['expected_files']if x['path'].endswith('.safetensors')},runtime_package_versions={k:version(k)for k in ('numpy','torch','safetensors')},snapshot='explicit-unit-fixture',source_sha256=pins)

def test_inventory_only_recipe_bridge_preserves_historical_identity():
 n=B.native();source='# explicit prior inventory fixture\n'+(B.ROOT/'tools/qwen_trained_byte_provider.py').read_text();old=identity_fixture(n,source);before=B.canonical(old)
 target=C.check_recipe(old,source,n)
 assert B.canonical(old)==before
 assert target['native_sha256']==old['native_sha256']
 assert target['checkpoint_files_sha256']==old['checkpoint_files_sha256']
 assert target['source_sha256']['tools/qwen_trained_byte_provider.py']!=old['source_sha256']['tools/qwen_trained_byte_provider.py']
 assert target['source_sha256']['tools/qwen_trained_page_continuation.py']==B.sha(B.ROOT/'tools/qwen_trained_page_continuation.py')

@pytest.mark.parametrize('mutant',['codec_function','reader_pin','shard','library','revision','native'])
def test_identity_bridge_rejects_changed_byte_inputs(mutant):
 n=B.native();source=(B.ROOT/'tools/qwen_trained_byte_provider.py').read_text();old=identity_fixture(n,source)
 if mutant=='codec_function':
  source=source.replace('def matrix_rows(reader,d,batch=128):','def matrix_rows(reader,d,batch=127):');old['source_sha256']['tools/qwen_trained_byte_provider.py']=hashlib.sha256(source.encode()).hexdigest()
 elif mutant=='reader_pin':old['source_sha256']['tools/qwen_hbm_complete_executor.py']='0'*64
 elif mutant=='shard':old['checkpoint_files_sha256']['model-00001-of-00005.safetensors']='0'*64
 elif mutant=='library':old['runtime_package_versions']['numpy']='unsupported'
 elif mutant=='revision':old['checkpoint_revision']='unsupported'
 else:old['native_sha256']='0'*64
 with pytest.raises(ValueError):C.check_recipe(old,source,n)

def pages_fixture(tmp_path):
 ref='Qwen.rank0.extent.L0.down.codes';path=tmp_path/(ref.replace('.','_')+'_0.bin');path.write_bytes(b'abcd');record=dict(file=path.name,start=0,bytes=4,sha256=B.sha(path));path.with_suffix('.json').write_bytes(B.canonical(record));return path,record

def test_continuation_inventory_rejects_corruption_or_orphan(tmp_path):
 path,record=pages_fixture(tmp_path);pages,complete=C.page_inventory(tmp_path,B.native());assert len(pages)==1 and complete==[]
 path.write_bytes(b'evil')
 with pytest.raises(ValueError,match='bytes/hash'):C.page_inventory(tmp_path,B.native())
 path.write_bytes(b'abcd');path.with_suffix('.json').unlink()
 with pytest.raises(OSError):C.page_inventory(tmp_path,B.native())

def test_exclusive_copy_and_missing_GO_fail_closed(tmp_path,monkeypatch):
 import qwen_trained_native_run as R
 job=tmp_path/'old';images=job/'images';images.mkdir(parents=True);path,record=pages_fixture(images)
 report=dict(old_job=str(job),pages=[dict(record=record)],verified_page_bytes=4,target_identity={'explicit_fixture':True})
 monkeypatch.setattr(R,'validate_admission',lambda *args:None);monkeypatch.setattr(R,'guard',lambda *args,**kwargs:None);monkeypatch.setattr(C,'qualify',lambda *args:report)
 target=tmp_path/'new'
 with pytest.raises(ValueError,match='source-bound'):C.copy_qualified(report,target,{},'explicit-unit-GO')
 assert not target.exists()
 admission={'historical_page_continuation_sha256':hashlib.sha256(B.canonical(report)).hexdigest()}
 C.copy_qualified(report,target,admission,'explicit-unit-GO');assert (target/path.name).read_bytes()==b'abcd';assert path.read_bytes()==b'abcd'
 with pytest.raises(FileExistsError):C.copy_qualified(report,target,admission,'explicit-unit-GO')
 assert (target/'continuation_receipt.json').is_file()
