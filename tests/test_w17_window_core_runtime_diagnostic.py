"""Artifact binding and diagnostics policy; no inferior/binary execution."""
from pathlib import Path
from types import SimpleNamespace
import sys,json
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_runtime_diagnostic as d
REC=ROOT/'results/uarch/w17_window_core_runtime_diagnostic_preparation_20261002'
PLAN=REC/'plan_r1/plan.json'

def test_plan_exact_retained_full_binary_and_final_scope():
 p=d.validate(PLAN);assert p['artifact']['binary_sha256']==d.EXPECTED_BINARY
 assert p['artifact']['binary_bytes']==105489464 and len(p['artifact']['source_files_sha256'])==163
 assert p['artifact']['geometry']['SUN']==256 and p['artifact']['geometry']['SUM']==64
 assert [len(j['cases']) for j in p['artifact']['final_scope_cases_and_mutants']]==[23,1,1,1,1]
 assert p['budget']['binary_invocations']==1 and p['budget']['compiler_invocations']==0
 assert p['budget']['diagnostic_wall_seconds']==10 and p['caps']['RuntimeMaxSec']==60
 assert p['command'][-1]=='+CUT=ISSUE' and '--args' in p['command']
 assert p['runtime_qualification'] is False

@pytest.mark.parametrize('key,value',[('artifact',{}),('command',[]),('gdb',{}),('observer_sha256','0'*64),('caps',{}),('budget',{})])
def test_changed_binary_scope_tools_caps_refused(tmp_path,key,value):
 p=json.loads(PLAN.read_text());p[key]=value;q=tmp_path/'bad';q.write_text(json.dumps(p))
 with pytest.raises(ValueError):d.validate(q)

@pytest.mark.parametrize('rows,expected',[
 ([], 'NO_MODEL_START_WITNESS'),([{'stage':'CONSTRUCTOR_ENTER'}],'MODEL_CONSTRUCTION_ENTERED_NO_COMPLETION_WITNESS'),([{'stage':'CONSTRUCTOR_ENTER'},{'stage':'EVAL_STEP_ENTER'}],'CONSTRUCTION_FINISHED_INITIALIZATION_IN_PROGRESS'),([{'stage':'DUT_EVAL_ENTER'},{'stage':'NEXT_SIMULATION_SLOT_RETURN','raw_rax_uint64':500}],'DUT_EVALUATION_REACHED')])
def test_progress_classification_conservative(rows,expected):
 assert d.classify(rows)['progress']==expected


def test_missing_GO_before_claim_service(tmp_path,monkeypatch):
 calls=[];monkeypatch.setattr(d.base,'claim_go',lambda *a:calls.append(a))
 a=SimpleNamespace(plan=str(PLAN),out=str(tmp_path/'out'),unit='w17-recovery-runtime-diag-control',go_commit=None,go_path='none')
 assert d.launch(a)==1 and not calls
 assert json.loads((tmp_path/'out/record.json').read_text())['verdict']=='FAIL_CLOSED_NO_DIAGNOSTIC_LAUNCH'
 assert not (tmp_path/'out/launch.json').exists()


def test_no_inferior_state_write_or_existing_pid_attach():
 text=d.OBS.read_text()
 assert 'gdb.execute(\'run\')' in text and 'return False' in text
 for forbidden in ['set variable','attach ','call ','jump ','set $']:
  assert forbidden not in text
 assert 'limit=16' in text and 'self.count>=64' in text
 assert '$rax' in text and "gdb.FinishBreakpoint" in text


def test_wrong_actual_binary_hash_refuses_before_diagnostic(monkeypatch):
 original=d.sha
 monkeypatch.setattr(d,'sha',lambda p:'0'*64 if Path(p)==d.BINARY else original(p))
 with pytest.raises(ValueError,match='compiled binary identity'):d.artifact()
