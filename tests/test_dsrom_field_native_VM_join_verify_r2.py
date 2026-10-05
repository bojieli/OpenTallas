import hashlib,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_field_native_VM_join_verify_r2 as M

@pytest.mark.parametrize('path',['inputs/__pycache__/native_calendar.cpython-310.pyc','source.pyc','inputs/__pycache__/unexpected.bin'])
def test_generated_cache_never_source(path):
 assert M.generated_cache(path) and M.census({path:'irrelevant'})=={}

@pytest.mark.parametrize('path',['source.py','model.json','inputs/pycache_source.py','inputs/__pycache__suffix/file.json'])
def test_real_source_or_artifact_never_excluded(path):
 assert not M.generated_cache(path) and M.census({path:'hash'})=={path:'hash'}

def test_exact_original_projection_and_two_generated_cache_paths():
 excluded=set()
 for name in ('source_pins.json','manifest.json'):
  old=json.loads((M.OLD/name).read_text());new=json.loads((M.OUT/name).read_text())
  assert new==M.census(old)
  excluded|=set(old)-set(new)
 assert len(excluded)==2 and all(M.generated_cache(p) for p in excluded)

def test_real_payload_change_remains_failure(tmp_path):
 p=tmp_path/'model.json';p.write_bytes(b'old');pins={'model.json':hashlib.sha256(p.read_bytes()).hexdigest()}
 M.check(pins,tmp_path);p.write_bytes(b'changed')
 with pytest.raises(ValueError,match='changed source/artifact'):M.check(pins,tmp_path)

def test_complete_successor_verification_preserves_original_model():
 before=(M.OLD/'model.json').read_bytes();M.verify()
 assert (M.OLD/'model.json').read_bytes()==before
