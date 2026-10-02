import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('fatal_runner',ROOT/'tools/w17_window_recovery_fatal_gate_run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
s2=importlib.util.spec_from_file_location('phase_runner',ROOT/'tools/w17_window_recovery_phase_gate_run.py');old=importlib.util.module_from_spec(s2);s2.loader.exec_module(old)
EVENTS={'max':0,'oom':0,'oom_kill':0,'oom_group_kill':0}
SOURCE='/tmp/window-recovery-phase-single-run-20261002-r1/discard_retirement_omitted/sources'

def case():return m.schedule(json.loads(m.RECORD.read_text()))[1]['cases'][0]
def retained():return (ROOT/'results/rtl/w17_window_recovery_phase_single_run_20261002/discard_retirement_omitted/case0.log').read_text()

def test_retained_log_matches_proposed_rule_only_old_failure_unchanged():
 m.verify_runtime(case(),1,retained(),EVENTS,SOURCE)
 with pytest.raises(ValueError):old.verify_runtime(case(),1,retained())
 assert json.loads((ROOT/'results/rtl/w17_window_recovery_phase_single_run_20261002/record.json').read_text())['verdict']=='FAIL_PRESERVED_NO_RETRY'

@pytest.mark.parametrize('code',[-6,-9,0,2,124,137])
def test_generic_nonzero_or_signal_never_accepted(code):
 with pytest.raises(ValueError):m.verify_runtime(case(),code,retained(),EVENTS,SOURCE)

@pytest.mark.parametrize('mutant',['wrong_marker','wrong_basename','wrong_line','wrong_top','no_trailer','extra_error','extra_fatal','wrong_source_path','generic_error'])
def test_narrow_three_line_semantic_receipt(mutant):
 text=retained()
 if mutant=='wrong_marker':text=text.replace(case()['marker'],'other error')
 elif mutant=='wrong_basename':text=text.replace('tb.sv','other.sv')
 elif mutant=='wrong_line':text=text.replace(':584:',':585:')
 elif mutant=='wrong_top':text=text.replace('in tb:','in another:')
 elif mutant=='no_trailer':text=text.replace('Aborting...\n','')
 elif mutant=='extra_error':text+='%Error: unrelated failure\n'
 elif mutant=='extra_fatal':text='%Fatal: unrelated failure\n'+text
 elif mutant=='wrong_source_path':text=text.replace('/discard_retirement_omitted/sources/','/another/sources/')
 else:text='failed: '+case()['marker']+'\n'
 with pytest.raises(ValueError):m.verify_runtime(case(),1,text,EVENTS,SOURCE)

@pytest.mark.parametrize('field',['max','oom','oom_kill','oom_group_kill'])
def test_cap_event_disqualifies_semantic_fatal(field):
 events=dict(EVENTS);events[field]=1
 with pytest.raises(ValueError):m.verify_runtime(case(),1,retained(),events,SOURCE)

def test_missing_caps_policy_or_source_provenance_rejected():
 with pytest.raises(ValueError):m.verify_runtime(case(),1,retained(),None,SOURCE)
 with pytest.raises(ValueError):m.verify_runtime(case(),1,retained(),EVENTS,None)
 bad=case();bad['fatal_receipt']['returncode']=-6
 with pytest.raises(ValueError):m.verify_runtime(bad,1,retained(),EVENTS,SOURCE)

def test_runtime_source_proof_is_pinned():
 assert m.fatal_policy_pin()==m.FATAL_POLICY_SHA
 policy=json.loads(m.FATAL_POLICY.read_text())
 assert policy['observed_returncode']==1 and not policy['tiny_selfcheck_needed']
 excerpt=json.loads((m.FATAL_POLICY.parent/'source_excerpts.json').read_text())
 assert 'std::exit(1)' in excerpt['runtime_stop_and_fatal']['text']
 assert 'std::abort()' in excerpt['runtime_stop_and_fatal']['text']
 assert 'Verilated::debug(0)' in (m.FATAL_POLICY.parent/'retained_generated_main.cpp').read_text()

def test_commands_mutants_caps_budget_and_closure_unchanged():
 record=json.loads(m.RECORD.read_text());new=m.schedule(record);previous=old.schedule(record)
 for job in new:
  for c in job['cases']:c.pop('fatal_receipt',None)
 assert new==previous and m.CAPS==old.CAPS and m.BUDGET==old.BUDGET


def test_plan_and_pending_GO_reject_previous_authorization(tmp_path):
 p=tmp_path/'plan';plan=m.prepare(p);assert m.validate_plan(p/'plan.json')==plan
 pending=json.loads((p/'parent_GO_template.json').read_text())
 assert pending['status']=='PENDING_NOT_AUTHORIZATION'
 with pytest.raises(ValueError):m.validate_go(pending,plan,p/'plan.json')
 prior=json.loads((ROOT/'results/rtl/w17_window_recovery_phase_single_run_20261002/parent_GO.json').read_text())
 with pytest.raises(ValueError):m.validate_go(prior,plan,p/'plan.json')


def test_fatal_policy_closure_rechecks_caps_and_retains_sources(tmp_path):
 out=tmp_path/'fresh';home=out/'discard_retirement_omitted';src=home/'sources';obj=home/'obj';src.mkdir(parents=True);obj.mkdir()
 (src/'tb.sv').write_text('fixture source');(obj/'Vtb').write_bytes(b'fixture binary')
 m.write(home/'snapshot_sha256.json',{'tb.sv':m.sha(src/'tb.sv')})
 m.write(home/'binary_receipt.json',{'sha256':m.sha(obj/'Vtb'),'bytes':(obj/'Vtb').stat().st_size})
 steps=[]
 for filename,code,text in [('compile',0,'done'),('case0',1,retained().replace(SOURCE,str(src)))]:
  log=home/(filename+'.log');log.write_text(text)
  steps.append({'log':str(log),'log_sha256':m.sha(log),'returncode':code,'cap_events':dict(EVENTS),'runtime_source_directory':str(src)})
 job={'label':'discard_retirement_omitted','cases':[case()]}
 steps[1]['cap_events']['oom']=1
 with pytest.raises(ValueError):m.close_and_reclaim(out,home,job,steps,'plan','go')
 assert obj.exists()
 steps[1]['cap_events']['oom']=0
 closed=m.close_and_reclaim(out,home,job,steps,'plan','go')
 assert not obj.exists() and src.exists() and closed['steps'][1]['returncode']==1

def test_compiled_binary_callpath_evidence_matches_retained_receipt():
 p=m.FATAL_POLICY.parent/'compiled_callpath_receipt.json';r=json.loads(p.read_text())
 assert r['binary_sha256']==json.loads(m.FATAL_POLICY.read_text())['retained_binary']['sha256']
 dis=m.FATAL_POLICY.parent/'retained_binary_vl_fatal_disassembly.log'
 assert m.sha(dis)==r['disassembly_sha256'] and '<exit@plt>' in dis.read_text()
