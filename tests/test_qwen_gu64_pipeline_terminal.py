"""Reject incomplete or unstressed pipeline evidence, independent of RTL."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from rtl_qwen_gu64_pipeline_gate import verify,MARKER


def fixture(work,marker=MARKER,rc=0,bubbles=5,tail='',rows=32):
    np.save(work/'expected.npy',np.zeros(32,dtype=np.uint32))
    def sha(p):return hashlib.sha256((work/p).read_bytes()).hexdigest()
    (work/'prepared.json').write_text(json.dumps(dict(input_sha256={'expected.npy':sha('expected.npy')},
        source_commit='validator-fixture',source_sha256={},qualified_snapshot={})))
    (work/'sim.vvp').write_text('validator-fixture-not-RTL');(work/'compile.log').write_text('')
    lines=[]
    for i in range(rows):
        wave=i//16;row=(250 if wave==0 else 506)+i%16
        lines.append(f'COMMITTED {row} {41+wave} 00000000 {800+i}')
    lines += [f'STATS epoch={e} steps=512 memory_bubbles={bubbles} result_stalls=10 commit_wait_cycles=20 final_cycle=900' for e in [41,42]]
    lines += [marker,tail]
    (work/'run.log').write_text('\n'.join(lines)+'\n')
    execution=dict(compile_rc=0,run_rc=rc)
    for key,p in [('prepared_sha256','prepared.json'),('compile_log_sha256','compile.log'),
                  ('run_log_sha256','run.log'),('executable_sha256','sim.vvp')]:execution[key]=sha(p)
    (work/'execution.json').write_text(json.dumps(execution))


def test_complete_stressed_fixture_passes(tmp_path):
    fixture(tmp_path);assert verify(tmp_path)['status']=='PASS'


@pytest.mark.parametrize('args',[
    {'marker':''},{'rc':1},{'tail':'FATAL after final write'},
    {'tail':'TIMEOUT'},{'bubbles':0},
])
def test_terminal_failures_or_unstressed_schedule_rejected(tmp_path,args):
    fixture(tmp_path,**args)
    with pytest.raises(ValueError):verify(tmp_path)


def test_missing_actual_commit_fails(tmp_path):
    fixture(tmp_path,rows=31);assert verify(tmp_path)['status']=='FAIL'
