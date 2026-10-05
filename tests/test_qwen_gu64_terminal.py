"""A complete row set must not hide a late simulator failure."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from rtl_qwen_gu64_pair_gate import verify

MARKER='COMPLETE GU64 rows=16 trailing=160 fault=0'


def fixture(work,tail=MARKER,rc=0,rows=16):
    np.save(work/'expected.npy',np.zeros(16,dtype=np.uint32))
    def sha(p):return hashlib.sha256((work/p).read_bytes()).hexdigest()
    (work/'prepared.json').write_text(json.dumps(dict(
        input_sha256={'expected.npy':sha('expected.npy')},
        qualified_snapshot={'scope':'validator-fixture'},source_sha256={})))
    (work/'sim.vvp').write_text('validator-fixture-not-RTL')
    (work/'compile.log').write_text('')
    (work/'run.log').write_text(''.join(
        f'RESULT {250+i} {i//2} 00000000 {600+i}\n' for i in range(rows))+tail+'\n')
    execution=dict(compile_rc=0,run_rc=rc)
    for key,p in [('prepared_sha256','prepared.json'),('compile_log_sha256','compile.log'),
                  ('run_log_sha256','run.log'),('executable_sha256','sim.vvp')]:
        execution[key]=sha(p)
    (work/'execution.json').write_text(json.dumps(execution))


def test_terminal_validator_accepts_complete_bound_fixture(tmp_path):
    fixture(tmp_path)
    assert verify(tmp_path)['status']=='PASS'


@pytest.mark.parametrize('tail,rc',[
    (MARKER+'\nFATAL: injected after last result',0),
    (MARKER+'\nFATAL: injected after completion',1),
    ('TIMEOUT after all16 rows',0),
    ('',0),
    (MARKER,1),
])
def test_late_fault_timeout_or_truncated_terminal_rejected(tmp_path,tail,rc):
    fixture(tmp_path,tail,rc)
    with pytest.raises(ValueError):verify(tmp_path)


def test_truncated_rows_fail_even_with_completion_marker(tmp_path):
    fixture(tmp_path,rows=15)
    assert verify(tmp_path)['status']=='FAIL'


def test_changed_log_fails_execution_binding(tmp_path):
    fixture(tmp_path)
    with (tmp_path/'run.log').open('a') as f:f.write('FATAL injected\n')
    with pytest.raises(AssertionError):verify(tmp_path)
