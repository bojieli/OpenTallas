import importlib.util,json,shutil
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('review',ROOT/'tools/w17_D1_native_terminal_cost_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_actual_cost_only_receipt():
 r=m.review();assert r['status']=='ACTUAL_NATIVE_PILOT_COST_ONLY_REVIEW_PASS'
 assert r['constructor_seconds']==.031458697 and r['last_retained_completed_evals']==1024
 assert r['service_bound']=='BOUND_MISSING' and not r['hardware_qualification']
 assert r['conditional_idle_rate_forecast']['actual_completion_bound'] is None
 assert r['conditional_idle_rate_forecast']['admitted_budget'] is None
 assert 5000<r['conditional_idle_rate_forecast']['full_fixture_cycle136800_seconds']<5100
 assert r['final_eval_count'] is None and r['inflight_eval_at_kill'].startswith('UNKNOWN')
def reseal(e,name):
 a=m.load(e/'archive_manifest.json');p=e/'raw'/name;a['files'][name]['sha256']=m.sha(p);a['files'][name]['bytes']=p.stat().st_size;(e/'archive_manifest.json').write_text(json.dumps(a))
@pytest.mark.parametrize('case',['false_pass','extra_case','pilot_exit0','CPU0','memory8GB','staleGO','frontend','optimizer_change','driver_eval_change','clock_shrink','nonmonotonic','fake_callback','reset_epoch','false_parser_rate','inventory_drift'])
def test_resealed_invalid_evidence_rejected(tmp_path,case):
 e=tmp_path/'evidence';shutil.copytree(m.E,e);raw=e/'raw';name='receipt.json'
 if case in ['false_pass','extra_case','pilot_exit0','frontend','optimizer_change']:
  r=m.load(raw/name)
  if case=='false_pass':r['status']='DUT_PASS'
  if case=='extra_case':r['steps'].append(r['steps'][-1])
  if case=='pilot_exit0':r['steps'][-1]['returncode']=0
  if case=='frontend':r['steps'][0]['command']=['verilator','--cc']
  if case=='optimizer_change':r['steps'][1]['command'][1]='-O3'
  (raw/name).write_text(json.dumps(r))
 elif case in ['CPU0','memory8GB']:
  name='admission.json';r=m.load(raw/name)
  if case=='CPU0':r['caps']['kernel_affinity']=[0,1]
  else:r['caps']['memory_max']='8589934592'
  (raw/name).write_text(json.dumps(r))
 elif case=='staleGO':
  name='GO.json';r=m.load(raw/name);r['execution_commit']='old';(raw/name).write_text(json.dumps(r))
 elif case=='driver_eval_change':
  name='observed_main.cpp';(raw/name).write_text((raw/name).read_text().replace('topp->eval();','topp->eval(); topp->eval();'))
 elif case in ['clock_shrink','reset_epoch']:
  name='fixture.sv';text=(raw/name).read_text().replace('#0.5','#0.05') if case=='clock_shrink' else (raw/name).read_text().replace('#1.1; rst_n=1;','#0.1; rst_n=1;');(raw/name).write_text(text)
 elif case in ['nonmonotonic','fake_callback']:
  name='pilot.log';text=(raw/name).read_text().replace('simtime=511000','simtime=100') if case=='nonmonotonic' else (raw/name).read_text()+'CONNECTED_WINDOW_PASS\n';(raw/name).write_text(text)
  r=m.load(raw/'receipt.json');r['steps'][-1]['log_sha256']=m.sha(raw/name);(raw/'receipt.json').write_text(json.dumps(r));reseal(e,'receipt.json')
 elif case=='false_parser_rate':
  name='cost_observation.json';r=m.load(raw/name);r['cycles_per_second']=999;(raw/name).write_text(json.dumps(r))
 else:
  name='full_object_inventory.json';r=m.load(raw/name);r[next(iter(r))]['sha256']='0'*64;(raw/name).write_text(json.dumps(r))
 reseal(e,name)
 with pytest.raises(ValueError):m.review(e)
