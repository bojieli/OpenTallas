#!/usr/bin/env python3
"""Source unchanged cold-CXX repair for measured standard archive FSIZE failure."""
import copy,json,subprocess,sys,os
from pathlib import Path
import prepare_hbm_rf_connected_calibration_r6 as B
import hbm_ds_frontend_reuse as I
ROOT=B.ROOT;OUT=ROOT/'results/uarch/hbm_connected_thin_archive_r7_20261002'
RUNNER_CAPS=B.RUNNER_CAPS;GO_SCHEMA='opentallas.hbm-RF-connected-thin-archive.GO.v1'
NEW=['tools/hbm_cxx_thin_archive_gate_r7.py','tools/run_hbm_rf_connected_thin_archive_r7.py','tools/hbm_ds_frontend_copy_r7.py','tools/prepare_hbm_rf_connected_thin_archive_r7.py','tools/test_hbm_rf_connected_thin_archive_r7.py']
BASE=B.OUT/'runtime_parser_prepared_gate.json';DIAG=ROOT/'results/rtl/hbm_r6_link_failure_owner_20261002_r2/owner_review.json'
def derive(base):
 if B.derive(json.loads(B.BASE.read_text()))!=base:raise ValueError('r6 source/tool/failure identity changed')
 d=json.loads(DIAG.read_text())
 for f,pin in d['raw_pins'].items():
  if I.digest(Path(d['original_output'])/f)!=pin['sha256']:raise ValueError('r2 failure changed: '+f)
 p=copy.deepcopy(base);p['schema']='opentallas.H1.thin-archive-prepared-gate.v1'
 p['gate_tool_sha256'].update({f:I.digest(ROOT/f)for f in NEW})
 for tool in ('/usr/bin/ar','/usr/bin/ranlib'):
  p['verified_toolchain']['files_sha256'][str(Path(tool).resolve())]=I.digest(tool)
 p['prior_r2_failure_sha256']=d['raw_pins']['verdict.json']['sha256']
 p['archive_repair_model']={'diagnosis_path':str(DIAG.relative_to(ROOT)),'diagnosis_sha256':I.digest(DIAG),'observed_DS_CXX_wall_s':d['CXX_end']['wall_s'],'object_count':d['object_count'],'generated_object_bytes':d['generated_object_bytes'],'standard_archive_payload_exceeds_FSIZE':True,'thin_archive':'GNU ar --thin stores references to the exact newly cold-compiled objects; source/generated kit bytes untouched. Full exact archive membership plus linkedELF check required before simulation.','caps_unchanged':True,'no_failed_objects_or_binary_reuse':True,'thin_archive_metadata_bytes':None,'Qwen_CXX_archive_binary_size_time_memory':'Unmeasured; preserve any cap/failure. DS object total is a measured lower bound for standard archive size, not thin/binary size.','no_physical_token_credit':True}
 p['commands']['DS'][0]['argv'][1]=NEW[2]
 for target in ('DS','Qwen'):
  phase=p['commands'][target][1];make=['/usr/bin/make' if x=='make' else x for x in phase['argv']]+['AR=/usr/bin/ar --thin']
  phase['argv']=['<pinned-python>',NEW[0],'--object-root',f'<fresh-output>/{target}/obj','--']+make
 p['runner']['path']=NEW[1];p['runner']['GO_schema']=GO_SCHEMA
 p['runner']['argv']=['<pinned-python>',NEW[1],'--proposal',str((OUT/'prepared_gate.json').relative_to(ROOT)),'--go','<fresh-thin-parent-GO.json>','--go-commit','<fresh-GO-commit>','--out','<fresh-absolute-output>']
 p['resource_plan'].update(archive_repair_model=p['archive_repair_model'],new_runtime_measurements=False,launches=0,GO=False)
 return p
def prepare():return derive(B.prepare())
def review_prepare():
 base=json.loads(BASE.read_text());m=json.loads(B.B.MANIFEST.read_text());worker=Path(m['source_root'])
 env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
 raw=subprocess.check_output([sys.executable,'-B','-c','import json,sys;sys.path.insert(0,"tools");import prepare_hbm_rf_connected_calibration_r6 as P;print(json.dumps(P.prepare(),sort_keys=True))'],cwd=worker,env=env,timeout=30)
 if json.loads(raw)!=base:raise ValueError('r6 originalroot prepare drift')
 return derive(base)
if __name__=='__main__':
 if sys.argv[1:]!=['--review-only']:raise SystemExit('review-only, no execution/admission')
 OUT.mkdir(parents=True,exist_ok=True);data=(json.dumps(review_prepare(),sort_keys=True,indent=2)+'\n').encode();p=OUT/'prepared_gate.json'
 if p.exists():assert p.read_bytes()==data
 else:
  with p.open('xb')as f:f.write(data)
 print(p)
