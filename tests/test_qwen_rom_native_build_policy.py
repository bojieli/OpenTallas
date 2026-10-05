import resource
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_kv_finite_window_gate as gate


def test_unlimited_time_and_file_size_preserve_memory_limit(monkeypatch):
    applied={}
    monkeypatch.setattr(gate.resource,'setrlimit',lambda key,value:applied.update({key:value}))
    gate.limits()
    assert applied[resource.RLIMIT_CPU]==(resource.RLIM_INFINITY,resource.RLIM_INFINITY)
    assert applied[resource.RLIMIT_FSIZE]==(resource.RLIM_INFINITY,resource.RLIM_INFINITY)
    assert applied[resource.RLIMIT_AS]==(2*1024**3,2*1024**3)


def test_aggregate_disk_guard_retains_objects(tmp_path):
    obj=tmp_path/'incremental.o';obj.write_bytes(b'12345678')
    assert gate.disk_guard(tmp_path,aggregate_limit=4,free_reserve=0)=='aggregate workdir disk guard exceeded'
    assert obj.read_bytes()==b'12345678'
    assert gate.disk_guard(tmp_path,aggregate_limit=8,free_reserve=0) is None


def test_free_space_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(gate.shutil,'disk_usage',lambda p:type('Usage',(),{'free':1})())
    assert gate.disk_guard(tmp_path,free_reserve=2)=='filesystem free-space reserve exhausted'
