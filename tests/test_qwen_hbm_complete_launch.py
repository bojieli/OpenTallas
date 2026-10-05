import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_launch import GIB,admission_ok,runtime_ok,process

def test_fresh_admission_and_runtime_memory_boundaries():
    assert admission_ok(112*GIB,80*GIB)
    assert not admission_ok(112*GIB-1,100*GIB)
    assert not admission_ok(200*GIB,80*GIB-1)
    assert runtime_ok(12*GIB,80*GIB)
    assert not runtime_ok(12*GIB+1,150*GIB)
    assert not runtime_ok(1*GIB,80*GIB-1)

def test_exact_process_identity_contains_start_cwd_rss():
    import os
    identity=process(os.getpid())
    assert identity['pid']==os.getpid() and identity['start_ticks']>0
    assert identity['cwd']==str(Path.cwd()) and identity['rss_bytes']>0
    assert process(2147483647) is None
