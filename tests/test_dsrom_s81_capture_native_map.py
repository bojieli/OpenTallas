import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'jobs/dsrom_s81_capture_native_map_20261004/run.py'
s=importlib.util.spec_from_file_location('job',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_actual_source_selected():
    s,d=m.check_source();assert s['parameters']['ROM_PHW']==10;assert d['retained_return_nodes']==5090
@pytest.mark.parametrize('param,value',[('ENABLE',1),('ROOTS',128),('CAPACITY',1),('VM_AW',19),('VM_ALWAYS_ACCEPT',1)])
def test_exact_parent_parameters(param,value):assert m.PARAMS[param]==value

def test_not_default_off_map():
    text=m.script([Path('/tmp/a'),Path('/tmp/b'),Path('/tmp/c')]);assert '-G ENABLE=1' in text;assert 'check -assert' in text;assert 'abc -g NAND' in text;assert 'flatten' in text

def test_no_timeout_or_memory_cap():
    text=P.read_text();assert 'timeout=' not in text;assert 'setrlimit' not in text
