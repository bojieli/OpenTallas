"""Pure source/receipt controls for a not-yet-authorized runtime gate."""
import importlib.util,json,sys,hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_join_run as run
import w17_window_core_cancel_source_prepare as source
PLAN=ROOT/'results/uarch/w17_window_core_cancel_join_preparation_r5_20261002/plan_r5/plan.json'

def test_real_headers_and_inverse_defaults():
 for kind,expected in [('base',213),('fastpp',228)]:
  record,text,original,enabled=source.generate(kind)
  assert record['ports_forwarded']==expected
  a=text.index('module '+record['module']+'_legacy #(')
  b=text.index('\nendmodule',a)+len('\nendmodule')
  assert text[a:b].replace(record['module']+'_legacy',source.NAME,1)==original.rstrip('\n')
  assert 'endmodule' not in original[:source.header_end(original)]

def test_exact_plan_and_finite_cases():
 p=run.validate_plan(PLAN)
 assert len(p['jobs'])==4 and len(p['jobs'][0]['cases'])==23
 assert sum(c['seconds'] for j in p['jobs'] for c in j['cases'])==26
 assert {c['args'][0] for c in p['jobs'][0]['cases']}=={'+CUT=ISSUE','+CUT=GO','+CUT=POISON','+CUT=PREFIX','+CUT=SU_SUFFIX','+CUT=WC','+CUT=WS'}
 assert p['caps']['MemoryMax']==4*1024**3
 assert p['physical_causal_visibility'] is False

@pytest.mark.parametrize('key,value',[('runner_sha256','0'*64),('model_sha256','0'*64),('source_files_sha256',{}),('budget',{}),('jobs',[]),('caps',{})])
def test_plan_changes_rejected_without_service(tmp_path,key,value):
 p=json.loads(PLAN.read_text());p[key]=value;q=tmp_path/'plan.json';q.write_text(json.dumps(p))
 with pytest.raises(ValueError):run.validate_plan(q)

def test_missing_GO_rejects_before_any_service(tmp_path,monkeypatch):
 calls=[];monkeypatch.setattr(run.cap,'claim_go',lambda *a:calls.append(a))
 a=SimpleNamespace(plan=str(PLAN),go_commit=None,go_path='none',unit='w17-recovery-core-test',out=str(tmp_path/'out'))
 with pytest.raises(ValueError,match='fresh committed GO'):run.launch(a)
 assert not calls and not (tmp_path/'out').exists()

def test_wrong_exit_or_marker_rejected():
 c={'expected':'PASS','marker':'ACTUAL_CORE_CANCEL_PASS cut=GO'}
 for rc,text in [(1,c['marker']),(0,'OTHER_PASS'),(0,c['marker']+'\nAssertion failed')]:
  with pytest.raises(ValueError):run.cap.verify_runtime(c,rc,text)

def test_negative_needs_exact_fatal_and_clean_caps():
 p=json.loads(PLAN.read_text());c=p['jobs'][1]['cases'][0]
 events={k:0 for k in ('max','oom','oom_kill','oom_group_kill')}
 site=c['fatal_receipt'];directory=Path('/tmp/owned-fixture/sources')
 text=f"[100] %Fatal: tb.sv:{site['line']}: Assertion failed in tb: {c['marker']}\n%Error: {directory}/tb.sv:{site['line']}: Verilog $stop\nAborting...\n"
 run.cap.verify_runtime(c,1,text,events,str(directory))
 for rc,t,e in [(-6,text,events),(2,text,events),(1,text.replace(c['marker'],'generic fatal'),events),(1,text,None),(1,text,dict(events,oom_kill=1))]:
  with pytest.raises(ValueError):run.cap.verify_runtime(c,rc,t,e,str(directory))

def test_real_source_mutants_unique_selected_cone():
 m=json.loads(run.MODEL.read_text());s=(ROOT/m['runtime_cone_path']).read_text()
 start=s.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
 for mutation in m['future_mutants'].values():
  assert s[start:].count(mutation['old'])==1
  assert run.fatal_site(mutation['failure'])['top']=='tb'
 # All active arithmetic stays source-bound; no behavioral prefix/helper substitutions.
 full=(ROOT/m['core_path']).read_text()
 for comment,end in [('    // the stream unit.','    // X_ROM: a LINQ op'),('    ot_hdc_v41_qe #','    // the XU:')]:
  a=full.index(comment,full.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #('));b=full.index(end,a)
  assert full[a:b] in s[start:]
