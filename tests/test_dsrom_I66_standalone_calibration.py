import sys,json,hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_standalone_calibration as S
import dsrom_I66_headroom_launch as L

def test_archives_and_actual_verdicts_are_independently_reproduced():
    v=S.verify()
    assert v['r1_FAIL']['result']=='FAIL'
    assert v['r2_PASS']['result']=='PASS'
    assert v['r2_PASS']['observed_events']==322308

def test_generator_byte_exact_on_archived_source_inputs(tmp_path):
    out=tmp_path/'fresh';S.generate(out)
    target=S.A/'prediction_r2'
    assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}=={str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()}
    assert all(p.read_bytes()==(target/p.relative_to(out)).read_bytes() for p in out.rglob('*') if p.is_file())

@pytest.mark.parametrize('last,nrow',[(19,1),(73,3),(419,576)])
def test_old_NBA_state_is_preserved(last,nrow):
    si,ai,tr=S.completion([dict(edge=last)]*nrow,nrow,10)
    assert (si,ai)==(last+2,last+3)
    assert tr[0]['rows_left_pre']==nrow and not tr[1]['spine_idle_pre']

@pytest.mark.parametrize('kind,edge',[('spine_idle',11),('spine_idle',420),('phase_retire',421)])
def test_actual_journal_premature_completion_mutants_fail(kind,edge):
    ev=S.events('r2_PASS')
    for x in ev:
        if x['kind']==kind:x['edge']=edge
    assert S.compare(S.A/'prediction_r2',ev)['result']=='FAIL'

def test_new_launch_plan_has_estimates_and_no_process_limits(tmp_path):
    binary=tmp_path/'retained';binary.write_bytes(b'example binary identity')
    a=SimpleNamespace(binary=binary,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),images=tmp_path,out=tmp_path/'not_created',cpus=None,execute=False)
    p=L.plan(a)
    assert p['limits_imposed']==[] and not p['execution_requested'] and not a.out.exists()
    text=Path(L.__file__).read_text()
    assert 'setrlimit' not in text and 'MemoryMax=' not in text and 'MemorySwapMax=' not in text and 'RuntimeMaxSec=' not in text and 'timeout=' not in text

def test_no_historical_import_or_fullcore_credit():
    text=Path(S.__file__).read_text()
    assert 'import dsrom_PAR2' not in text and '/home/ubuntu/w17-' not in text
    m=S.load(S.A/'prediction_r2/prediction.json')
    assert not m['full_core_scheduler_or_coll_busy_bound'] and not m['macro_physical_or_PAR2_interdie_credit'] and not m['fulltoken_credit']

def test_legacy_binary_not_relaunched_and_future_host_has_no_guessed_rejection(tmp_path):
    text=(S.A/'host_future_headroom.cpp').read_text()
    assert 'FAIL_preallocation_capacity' not in text and 'object_est>6ull' not in text
    assert 'FAIL_preallocation_capacity' in (S.A/'host_r2.cpp').read_text()
    binary=tmp_path/'binary';binary.write_bytes(b'x')
    a=SimpleNamespace(binary=binary,binary_sha256=hashlib.sha256(b'x').hexdigest(),images=tmp_path,out=tmp_path/'not_created',cpus=None,execute=True,build_receipt=None)
    with pytest.raises(ValueError,match='historical capped binary'):L.main(a)
    assert not a.out.exists()
