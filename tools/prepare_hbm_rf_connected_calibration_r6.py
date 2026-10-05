#!/usr/bin/env python3
"""Additive H1 calibration proposal. Runtime preserves the original exact ROOT guard."""
import copy,json,subprocess,sys
from pathlib import Path
import prepare_hbm_rf_connected_reuse_r5 as B
import hbm_ds_frontend_reuse as I
ROOT=B.ROOT
OUT=ROOT/'results/uarch/hbm_connected_cxx_calibration_r6_20261002'
GO_SCHEMA='opentallas.hbm-RF-connected-calibration.GO.v1'
RUNNER_CAPS={**B.RUNNER_CAPS,'cpus':list(range(8,24)),'whole_wall_s':4620,'build_jobs':16}
NEW=['tools/model_hbm_connected_cxx_calibration_r6.py','tools/prepare_hbm_rf_connected_calibration_r6.py','tools/run_hbm_rf_connected_calibration_r6.py','tools/hbm_ds_frontend_copy_r6.py','tools/test_hbm_rf_connected_calibration_r6.py']
BASE=ROOT/'results/uarch/hbm_rf_connected_reuse_r5_20261002/prepared_gate.json'
MODEL=OUT/'model.json'
def verify_current(base):
 for bundle in ('source_sha256','gate_tool_sha256'):
  for p,h in base[bundle].items():
   if I.digest(ROOT/p)!=h:raise ValueError('unchanged source/tool pin mismatch: '+p)
 for p,h in base['verified_toolchain']['files_sha256'].items():
  if I.digest(p)!=h:raise ValueError('compiler/tool identity mismatch: '+p)
 if I.digest(ROOT/base['reuse_inventory_pin']['path'])!=base['reuse_inventory_pin']['sha256']:raise ValueError('inventory changed')
def derive(base):
 verify_current(base);model=json.loads(MODEL.read_text())
 for p,h in model['failure_pins'].items():
  if I.digest(Path(model['prior_output'])/p)!=h:raise ValueError('original failure changed: '+p)
 p=copy.deepcopy(base);p['schema']='opentallas.H1.calibration-prepared-gate.v1'
 p['calibration_model_sha256']=I.digest(MODEL);p['prior_failure_sha256']=model['failure_pins']['verdict.json']
 p['calibration_model_path']=str(MODEL.relative_to(ROOT));p['runner_caps']=RUNNER_CAPS
 p['gate_tool_sha256'].update({f:I.digest(ROOT/f)for f in NEW})
 p['caps'].update(build_jobs=16,proposed_local_CPUs=list(range(8,24)),whole_timeout_s=4620)
 p['runner']['parent_launch_affinity']='taskset --cpu-list 8-23; runner verifies exactly16 cores, never cpu.max'
 p['runner']['path']=NEW[2];p['runner']['GO_schema']=GO_SCHEMA
 p['runner']['argv']=['<pinned-python>',NEW[2],'--proposal',str((OUT/'prepared_gate.json').relative_to(ROOT)),'--go','<fresh-calibration-GO.json>','--go-commit','<fresh-GO-commit>','--out','<fresh-absolute-output>']
 p['commands']['DS'][0]['argv'][1]=NEW[3]
 for target in ('DS','Qwen'):
  phase=p['commands'][target][1];phase['timeout_s']=1800
  phase['argv']=['-j16' if x=='-j4' else x for x in phase['argv']]
 p['resource_plan'].update(scope='New mandatory H1 resource calibration; fresh independent review and committed GO required.',caps=RUNNER_CAPS,CPU_enforcement='Exact kernel affinity8-23 inherited and observed descendants verified; no cpu.max/quota/exclusive-core claim.',phase_limits_s={'DS':{'reuse_frontend':300,'CXX':1800,'simulation':180,'trace':30},'Qwen':{'frontend':300,'CXX':1800,'simulation':180,'trace':30}},CXX600_is_expected_completion=False,CXX1800_is_expected_completion=False,CXX_time_and_memory_measured='Prior DS4core600 phase timeout only; new16core and Qwen unknown.',partial_objects_reused=False,prior_failure=model['failure_pins'],model_sha256=I.digest(MODEL),launches=0,GO=False)
 p['resource_plan']['risks']=model['dependency_critical_path']['unknown']+' 1800s is a budget, not an expected completion time; 32GiB Qwen frontend remains unqualified. Preserve every failure, no automatic retry.'
 p['execution_source_root']=json.loads(B.MANIFEST.read_text())['source_root']
 p['review_note']='Preparation replay allowed only via explicit review-only command at recorded frozen worker; live runner still calls exact original ROOT-guarded B.prepare. Parent must establish clean reviewed successor at recorded source_root before fresh GO; e031 worker remains frozen during preparation.'
 return p
def prepare():return derive(B.prepare())
def review_prepare():
 base=json.loads(BASE.read_text());verify_current(base)
 worker=Path(json.loads(B.MANIFEST.read_text())['source_root'])
 code='import json,prepare_hbm_rf_connected_reuse_r5 as P; print(json.dumps(P.prepare(),sort_keys=True))'
 env=__import__('os').environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
 replay=json.loads(subprocess.check_output([sys.executable,'-B','-c',code],cwd=worker/'tools',env=env,text=True))
 if replay!=base:raise ValueError('original-root preparation drift')
 return derive(base)
if __name__=='__main__':
 if sys.argv[1:]!=['--review-only']:raise SystemExit('Use --review-only; no execution/admission occurs')
 data=(json.dumps(review_prepare(),indent=2,sort_keys=True)+'\n').encode();path=OUT/'prepared_gate.json'
 if path.exists():assert path.read_bytes()==data
 else:
  with path.open('xb')as f:f.write(data)
 print(path)
