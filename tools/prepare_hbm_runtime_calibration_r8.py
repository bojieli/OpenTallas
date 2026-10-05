#!/usr/bin/env python3
"""Independent DS runtime and Qwen build-only proposals; no launch/admission."""
import copy,json,subprocess,sys,os
from pathlib import Path
import prepare_hbm_rf_connected_thin_archive_r7 as B
import hbm_DS_binary_reuse_r8 as I
ROOT=B.ROOT;OUT=ROOT/'results/uarch/hbm_runtime_calibration_r8_20261002';MODEL=OUT/'model.json';MANIFEST=OUT/'qualified_DS_binary.json';BASE=B.OUT/'prepared_gate.json'
GO_SCHEMA='opentallas.H1.runtime-calibration.GO.v1'
NEW=['tools/model_hbm_runtime_calibration_r8.py','tools/hbm_DS_binary_reuse_r8.py','tools/prepare_hbm_runtime_calibration_r8.py','tools/run_hbm_runtime_calibration_r8.py','tools/test_hbm_runtime_calibration_r8.py']
def caps_for(target):
 m=json.loads(MODEL.read_text())['resource_calendar'][target];caps=dict(B.RUNNER_CAPS)
 caps.update(cpus=m['cpus'],build_jobs=m.get('jobs',1),whole_wall_s=m['whole_s'])
 return caps
RUNNER_CAPS=caps_for('DS')
def derive(base,target):
 if target not in ('DS','Qwen'):raise ValueError('unknown calibration target')
 I.verify(json.loads(MANIFEST.read_text()),require_root=False)
 p=copy.deepcopy(base);p.update(schema='opentallas.H1.runtime-calibration-prepared.v1',target=target,runner_caps=caps_for(target),runtime_model_sha256=I.I.digest(MODEL),qualified_binary_manifest_sha256=I.I.digest(MANIFEST))
 p['gate_tool_sha256'].update({f:I.I.digest(ROOT/f)for f in NEW})
 m=json.loads(MODEL.read_text());p['runtime_model_path']=str(MODEL.relative_to(ROOT));p['qualified_binary_manifest_path']=str(MANIFEST.relative_to(ROOT));p['runtime_phase_limit_s']=m['proposed_DS_simulation_cap_s']
 p['runner']['path']=NEW[3];p['runner']['GO_schema']=GO_SCHEMA
 p['runner']['parent_launch_affinity']='taskset --cpu-list '+('0'if target=='DS'else'8-23')+'; exact kernel mask, no cpu.max claim'
 p['runner']['argv']=['<pinned-python>',NEW[3],'--proposal',str((OUT/(target+'_prepared_gate.json')).relative_to(ROOT)),'--go','<fresh-target-GO.json>','--go-commit','<fresh-GO-commit>','--out','<fresh-output>']
 if target=='DS':
  p['commands']={'DS':[dict(phase='reuse_binary',timeout_s=300,argv=['<pinned-python>',NEW[1],'--manifest',str(MANIFEST.relative_to(ROOT)),'--destination','<fresh-output>/DS/obj/Vconnected','--proposal','<fresh-output>/proposal.json','--go','<fresh-output>/GO.json','--go-commit','<fresh-GO-commit>']),copy.deepcopy(base['commands']['DS'][2]),copy.deepcopy(base['commands']['DS'][3])]}
  p['commands']['DS'][1]['timeout_s']=m['proposed_DS_simulation_cap_s'];p['acceptance']='Qualified complete DS ELF exclusivecopy, actual fullbench4cases+reset markers and trace PASS. DirectedDS only; Qwen not covered.'
 else:
  p['commands']={'Qwen':copy.deepcopy(base['commands']['Qwen'][:2])}
  p['commands']['Qwen'][1]['argv']=list(p['commands']['Qwen'][1]['argv'])
  p['acceptance']='Fresh fullgeometry Qwenfrontend+coldCXX+exactthinarchive/ELFreceipt only. No Qwen runtime or numerical credit.'
 p['caps'].update(proposed_local_CPUs=p['runner_caps']['cpus'],build_jobs=p['runner_caps']['build_jobs'],whole_timeout_s=p['runner_caps']['whole_wall_s'])
 p['resource_plan'].update(caps=p['runner_caps'],independent_targets=True,calendar=m['resource_calendar'],scope=p['acceptance'],model_sha256=p['runtime_model_sha256'],launches=0,GO=False)
 return p
def prepare_target(target):
 I.verify(json.loads(MANIFEST.read_text()),require_root=True)
 return derive(B.prepare(),target)
def review_prepare(target):
 base=json.loads(BASE.read_text());worker=Path(json.loads(MANIFEST.read_text())['source_root']);env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
 raw=subprocess.check_output([sys.executable,'-B','-c','import sys,json;sys.path.insert(0,"tools");import prepare_hbm_rf_connected_thin_archive_r7 as P;print(json.dumps(P.prepare(),sort_keys=True))'],cwd=worker,env=env,timeout=30)
 if json.loads(raw)!=base:raise ValueError('qualified originalroot frame prepare drift')
 return derive(base,target)
if __name__=='__main__':
 if sys.argv[1:]!=['--review-only']:raise SystemExit('review-only; freshGO required, no execution')
 for target in ('DS','Qwen'):
  data=(json.dumps(review_prepare(target),indent=2,sort_keys=True)+'\n').encode();p=OUT/(target+'_prepared_gate.json')
  if p.exists():assert p.read_bytes()==data
  else:
   with p.open('xb')as f:f.write(data)
  print(p)
