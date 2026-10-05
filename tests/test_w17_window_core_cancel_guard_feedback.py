"""Source-bound guard ingress and preserved frontend profile; no compiler/build."""
import sys,json,hashlib,itertools
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_guard_feedback_repair as repair
import w17_window_core_cancel_guard_frontend_run as runner
REC=ROOT/repair.REC
PLAN=REC/'frontend_plan_r1/plan.json'

def test_old_loop_has_no_fixed_point_for_guard_error():
 assert repair.fixed_points(0,1,1,0,True)==[]
 assert repair.fixed_points(0,1,1,0,False)==[1]
 # Same Boolean loop also has ambiguous stable states for guardbad/localbad cases.
 for other,drain,guard,bad in itertools.product((0,1),repeat=4):
  fixed=repair.fixed_points(other,drain,guard,bad,False)
  assert fixed==[int(bool(other or drain and guard))]


def test_typed_guard_rejection_is_not_healthy_admission_bug():
 m=json.loads((REC/'feedback_model.json').read_text());w=m['counterexample']['legal_width_metadata_example']
 assert all(0<=w[k]<(1<<21) for k in ('step_pos','blk_abs_row','blk_kvt_row'))
 assert 0<=w['blk_idx']<16 and 0<=w['kvt_base']<1<<30 and 0<=w['first_elem']<1<<30
 assert w['blk_abs_row']!=w['step_pos'] # intended reject; must deterministically freeze
 assert w['first_elem']==w['kvt_base']+w['blk_kvt_row']%16


def test_exact_added_fixture_delta_and_no_design_body_change():
 old=repair.blob(repair.OLD+'/tb.sv').decode();new=(ROOT/repair.OUT/'tb.sv').read_text()
 expected=old.replace('logic  core_rec_fault_inject=0;','wire core_rec_fault_inject;').replace(repair.OLD_INJECT,' // Guard ingress is a continuous raw-intent observer above; no gated-valid feedback.').replace('always_comb begin\n core_coll_busy',repair.INGRESS+'always_comb begin\n core_coll_busy')
 assert new==expected
 assert (ROOT/repair.OUT/'actual_fastpp_core_selected_cone.sv').read_bytes()==repair.blob(repair.OLD+'/actual_fastpp_core_selected_cone.sv')
 m=json.loads(runner.MODEL.read_text());oldmodel=json.loads(repair.blob(repair.OLD_MODEL))
 assert m['future_mutants']==oldmodel['future_mutants'] and m['cases']==oldmodel['cases']
 assert m['accounting']==oldmodel['accounting']


def test_ingress_has_no_gate_suppressed_signal_dependency():
 tb=(ROOT/repair.OUT/'tb.sv').read_text()
 assert repair.OLD_INJECT not in tb
 assert tb.count('assign core_rec_fault_inject = fault_pulse || src_fault || core_guard_fault_raw;')==1
 assert 'core_guard_pending_raw = ('+repair.STATE+" == 2'd3)" in tb
 assert 'wire core_guard_fault_raw = core_guard_pending_raw && guard_bad;' in tb
 assert 'core_rec_fault_inject=' not in tb
 assert 'core_win_blk_v && guard_bad' not in tb
 producer=(ROOT/repair.PRODUCER).read_text()
 assert producer.count('localparam [1:0] EMPTY = 0, FILL = 1, FULL = 2, DRAIN = 3;')==2
 # All raw metadata outputs required by guard are assigned independently of freeze.
 for token in ['assign blk_kvt_base = kvt_base;','assign blk_row = row;','assign blk_kvt_row = kvt_row;','assign blk_idx = rd_idx;','assign blk_first_elem = first_wide[AW-1:0];']:
  assert token in producer


def test_plan_requires_new_frontend_not_old_closure_reuse():
 p=runner.validate(PLAN)
 assert p['prior_closure_reuse'] is False
 assert p['source_geometry']['SUN']==256 and p['source_geometry']['SUM']==64
 assert p['budget']['CXX_compiles']==0 and p['budget']['simulations']==0
 assert p['caps']['MemoryMax']==32*1024**3
 assert p['source_files_sha256'][repair.OUT+'/tb.sv']==runner.sha(ROOT/repair.OUT/'tb.sv')
 assert len(p['negative_campaign_preserved'])==4 and len(p['positive_cases_preserved'])==23

@pytest.mark.parametrize('key,value',[('source_files_sha256',{}),('command',[]),('caps',{}),('runner_sha256','0'*64),('prior_closure_reuse',True)])
def test_changed_plan_refused_before_generation(tmp_path,key,value):
 p=json.loads(PLAN.read_text());p[key]=value;q=tmp_path/'plan';q.write_text(json.dumps(p))
 with pytest.raises(ValueError):runner.validate(q)


def test_missing_GO_no_service_no_claim(tmp_path,monkeypatch):
 called=[];monkeypatch.setattr(runner.base,'claim_go',lambda *a:called.append(a))
 a=SimpleNamespace(out=str(tmp_path/'out'),plan=str(PLAN),unit='w17-recovery-frontend-guard-control',go_commit=None,go_path='none')
 assert runner.launch(a)==1 and not called
 r=json.loads((tmp_path/'out/record.json').read_text())
 assert r['stage']=='GO_validation' and not (tmp_path/'out/launch.json').exists()


def test_remaining_UNOPTFLAT_blocks_readiness_before_inventory(tmp_path,monkeypatch):
 a=SimpleNamespace(out=str(tmp_path/'out'),plan=str(PLAN),unit='w17-recovery-frontend-guard-control',go_commit=None,go_path='none')
 runner.owned_output(a);monkeypatch.setattr(runner,'validate_GO',lambda *a:None);monkeypatch.setattr(runner,'caps_receipt',lambda *a:{'mock':'no real service'})
 def fake(cmd,log,seconds,out):
  Path(log).write_text('%Warning-UNOPTFLAT: rec_stop remains\n')
  return {'command':cmd,'returncode':0,'wall_seconds':.1,'log':str(log),'log_sha256':runner.sha(log)}
 monkeypatch.setattr(runner.base,'supervised',fake)
 assert runner.worker(a)==1
 record=json.loads((tmp_path/'out/record.json').read_text());assert 'UNOPTFLAT remains' in record['error']
 assert not (tmp_path/'out/frontend_closure.json').exists()
