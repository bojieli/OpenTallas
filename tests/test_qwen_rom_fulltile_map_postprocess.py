import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
import sys
sys.path.insert(0,str(ROOT/'tools'))
p=load('qwen_rom_fulltile_map_postprocess')
def scope():return {'connections':{},'port_directions':{},'parameters':{'TYPE':'module'},'attributes':{'module_src':'pinned.sv:1'}}
def test_only_empty_scope_metadata():assert p.classify_cell('$scopeinfo',scope(),{})=='metadata'
@pytest.mark.parametrize('key,value',[('connections',{'D':[1]}),('port_directions',{'Q':'output'}),('parameters',{'TYPE':'logic'})])
def test_nonmetadata_scope_refused(key,value):
 c=scope();c[key]=value
 with pytest.raises(ValueError):p.classify_cell('$scopeinfo',c,{})
def test_other_unmapped_logic_not_hidden():
 with pytest.raises(ValueError,match='unmapped logic'):p.classify_cell('$unknown',scope(),{})

def test_future_disk_monitor_does_not_terminate_on_arbitrary_thresholds(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from qwen_rom_fulltile_source_map import execute
    import qwen_rom_fulltile_source_map as driver
    class Process:
        returncode=0
        calls=0
        def poll(self):
            self.calls+=1
            return None if self.calls==1 else 0
    monkeypatch.setattr(driver.subprocess,'Popen',lambda *a,**k:Process())
    monkeypatch.setattr(driver.time,'sleep',lambda _:None)
    monkeypatch.setattr(driver.shutil,'disk_usage',lambda _:SimpleNamespace(free=1))
    class File:
        def is_file(self):return True
        def stat(self):return SimpleNamespace(st_size=17*1024**3)
    monkeypatch.setattr(Path,'rglob',lambda *a:[File()])
    execute(['fake-test-only'],tmp_path,tmp_path/'log')
    import json
    j=json.loads((tmp_path/'disk_headroom.jsonl').read_text())
    assert j['workspace_bytes']==17*1024**3 and j['free_disk_bytes']==1
