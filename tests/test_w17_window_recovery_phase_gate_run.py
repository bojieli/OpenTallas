import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('phase_runner',ROOT/'tools/w17_window_recovery_phase_gate_run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
s2=importlib.util.spec_from_file_location('original_runner',ROOT/'tools/w17_window_recovery_gate_run.py');old=importlib.util.module_from_spec(s2);s2.loader.exec_module(old)

def fixture(tmp_path):
 out=tmp_path/'fresh';home=out/'baseline';(home/'obj').mkdir(parents=True);(home/'sources').mkdir()
 (home/'obj'/'Vtb').write_bytes(b'qualified binary')
 (home/'obj'/'x.gch').write_bytes(b'generated header')
 (home/'sources'/'tb.sv').write_text('pinned source')
 m.write(home/'snapshot_sha256.json',{'tb.sv':m.sha(home/'sources'/'tb.sv')})
 m.write(home/'binary_receipt.json',{'sha256':m.sha(home/'obj'/'Vtb'),'bytes':(home/'obj'/'Vtb').stat().st_size})
 cases=[{'expected':'PASS','marker':'PASS','args':[],'seconds':4},{'expected':'FAIL','marker':'EXPECTED_FAIL','args':[],'seconds':4}]
 steps=[]
 for name,code,text in [('compile',0,'compiler done'),('case0',0,'PASS'),('case1',-6,'EXPECTED_FAIL')]:
  log=home/(name+'.log');log.write_text(text);steps.append({'returncode':code,'log':str(log),'log_sha256':m.sha(log)})
 job={'label':'baseline','cases':cases};return out,home,job,steps

def test_closure_reclaims_only_new_owned_obj_after_receipts(tmp_path):
 out,home,job,steps=fixture(tmp_path);old_file=tmp_path/'old-failure';old_file.write_text('untouched')
 r=m.close_and_reclaim(out,home,job,steps,'plan','go')
 assert not (home/'obj').exists() and old_file.read_text()=='untouched'
 assert (home/'sources'/'tb.sv').exists() and len(r['generated_files'])==2
 assert len(r['retained_evidence_files'])==5
 assert json.loads((home/'reclamation_receipt.json').read_text())['closed_receipt_sha256']==m.sha(home/'phase_closed.json')
 with pytest.raises(ValueError):m.close_and_reclaim(out,home,job,steps,'plan','go')

@pytest.mark.parametrize('mutant',['missing_case','wrong_failure_marker','wrong_signal','log_changed','binary_changed','source_changed','obj_symlink','wrong_owner','prior_closed'])
def test_no_reclaim_on_unclosed_or_unowned_phase(tmp_path,mutant):
 out,home,job,steps=fixture(tmp_path)
 if mutant=='missing_case':steps.pop()
 elif mutant=='wrong_failure_marker':
  Path(steps[2]['log']).write_text('other error');steps[2]['log_sha256']=m.sha(Path(steps[2]['log']))
 elif mutant=='wrong_signal':steps[2]['returncode']=1
 elif mutant=='log_changed':Path(steps[1]['log']).write_text('PASS modified')
 elif mutant=='binary_changed':(home/'obj'/'Vtb').write_text('different binary')
 elif mutant=='source_changed':(home/'sources'/'tb.sv').write_text('different source')
 elif mutant=='obj_symlink':
  (home/'obj').rename(home/'real_obj');(home/'obj').symlink_to(home/'real_obj',target_is_directory=True)
 elif mutant=='wrong_owner':out=tmp_path/'not_owner'
 elif mutant=='prior_closed':(home/'phase_closed.json').write_text('{}')
 with pytest.raises((ValueError,FileNotFoundError)):m.close_and_reclaim(out,home,job,steps,'plan','go')
 assert (home/'obj').exists()

def test_exact_original_mutant_jobs_caps_and_budget():
 record,_=old.source_manifest()
 assert m.schedule(record)==old.schedule(record)
 assert m.CAPS==old.CAPS and m.BUDGET==old.BUDGET
 assert m.STATUS!=old.STATUS

def test_template_not_authorization_and_old_GO_rejected(tmp_path):
 plan=m.prepare(tmp_path/'prep');path=tmp_path/'prep'/'plan.json'
 pending=json.loads((tmp_path/'prep'/'parent_GO_template.json').read_text())
 assert pending['status']=='PENDING_NOT_AUTHORIZATION'
 with pytest.raises(ValueError):m.validate_go(pending,plan,path)
 original=json.loads((ROOT/'results/rtl/w17_window_recovery_connected_single_run_20261002/parent_GO.json').read_text())
 with pytest.raises(ValueError):m.validate_go(original,plan,path)
 assert m.validate_plan(path)==plan

@pytest.mark.parametrize('bad',['budget','resource','manifest','commands'])
def test_plan_mutants_rejected(tmp_path,bad):
 m.prepare(tmp_path/'prep');path=tmp_path/'prep'/'plan.json';p=json.loads(path.read_text())
 if bad=='budget':p['budget']['generated_output_total_bytes']+=1
 elif bad=='resource':p['output_resource_model_sha256']='0'*64
 elif bad=='manifest':p['manifest_sha256']='0'*64
 else:p['jobs'][0]['compile_command'].append('--different')
 m.write(path,p)
 with pytest.raises(ValueError):m.validate_plan(path)

@pytest.mark.parametrize('field,value',[('MemoryMax','2147483648'),('MemorySwapMax','1'),('CPUAffinity','0 1'),('LimitFSIZE','536870912'),('RuntimeMaxUSec','4min'),('KillMode','process')])
def test_caps_remain_fail_closed(field,value,monkeypatch):
 values={k:' '.join(map(str,v)) if isinstance(v,list) else str(v) for k,v in m.CAPS.items() if k!='RuntimeMaxSec'}
 values.update(ControlGroup='/fake',RuntimeMaxUSec='3min');values[field]=value
 monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**kw:'\n'.join(k+'='+v for k,v in values.items()))
 with pytest.raises(ValueError):m.caps_receipt('w17-recovery-wrongcap')

def test_new_missing_GO_has_no_service_or_output(tmp_path,monkeypatch):
 from types import SimpleNamespace
 monkeypatch.setattr(m,'validate_plan',lambda p:{})
 invoked=[];monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:invoked.append(a))
 args=SimpleNamespace(plan='ignored',probe=False,go_commit=None,go_path='missing',unit='w17-recovery-no-go',out=str(tmp_path/'out'))
 with pytest.raises(ValueError):m.launch(args)
 assert not invoked and not Path(args.out).exists()

def test_cap_before_reclaim_preserves_closed_but_overlimit_obj(tmp_path,monkeypatch):
 out,home,job,steps=fixture(tmp_path)
 monkeypatch.setattr(m,'BUDGET',dict(m.BUDGET,generated_output_total_bytes=1))
 with pytest.raises(RuntimeError,match='closure evidence exceeds'):m.close_and_reclaim(out,home,job,steps,'plan','go')
 assert (home/'obj').is_dir() and (home/'phase_closed.json').is_file()

def test_reused_GO_claim_is_never_removed(tmp_path):
 claim=m.claim_go('a'*40,tmp_path)
 with pytest.raises(FileExistsError):m.claim_go('a'*40,tmp_path)
 assert claim.is_dir()
