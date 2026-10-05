#!/usr/bin/env python3
"""Immutable r4 successor: reuse only inventoried successful DS HDL generation."""
import hashlib,json,subprocess,sys,shutil
from pathlib import Path
import prepare_hbm_rf_connected_campaign_r4 as B
import hbm_ds_frontend_reuse as I
import full_sm_rf_verilator_gate as G
ROOT=B.ROOT;OUT=ROOT/'results/uarch/hbm_rf_connected_reuse_r5_20261002';PROPOSAL='prepared_gate.json'
blob=B.blob
RUNNER_CAPS=B.RUNNER_CAPS;MANIFEST=OUT/'DS_frontend_inventory.json';GO_SCHEMA='opentallas.hbm-RF-connected-reuse.GO.v1'
NEW=['tools/hbm_ds_frontend_reuse.py','tools/prepare_hbm_rf_connected_reuse_r5.py','tools/run_hbm_rf_connected_reuse_r5.py','tools/test_hbm_rf_connected_reuse_r5.py']
def prepare():
 old=B.prepare();m=json.loads(MANIFEST.read_text());I.verify_inputs(m)
 if m['source_sha256']!=old['source_sha256']:raise ValueError('reuse source binding changed')
 parent_rev='a206468c1ae989e4c4f539d4e51bd66af0834393';parent_path='results/rtl/hbm_connected_parent_terminal_20261002_r1/parent_review.json'
 parent_raw=subprocess.check_output(['git','show',parent_rev+':'+parent_path],cwd=ROOT);parent=json.loads(parent_raw)
 for f,v in parent['pins'].items():
  if m['prior_receipt_pins'][f]!=v['sha256']:raise ValueError('prior receipt not parent-archived: '+f)
 p=dict(old);p['prior_parent_terminal_binding']={'commit':parent_rev,'path':parent_path,'sha256':hashlib.sha256(parent_raw).hexdigest(),'six_prior_receipt_pins_match':True}
 plan='542b0c5a7e4c732039a11feca07f600dc3e155a1';p['plan_pins']={f:{'commit':plan,'sha256':hashlib.sha256(subprocess.check_output(['git','show',plan+':'+f],cwd=ROOT)).hexdigest()}for f in ['docs/INTEGRATED_PHYSICAL_PLAN.md','TASKS.md']}
 p['task']='H1';p['H2_P1_P2_scope']='Kepler/Archimedes shoreline ownership/PHY/CDC/serviceclock and contextualSSFF remain separate; this directedfixture supplies no clock/physical/tokencredit.'
 p['schema']='opentallas.hbm-RF-connected.reuse-prepared-gate.v1'
 p['gate_tool_sha256']={**old['gate_tool_sha256'],**{f:I.digest(ROOT/f)for f in NEW}}
 p['reuse_inventory_pin']={'path':str(MANIFEST.relative_to(ROOT)),'sha256':I.digest(MANIFEST),'file_count':m['file_count'],'total_bytes':m['total_bytes'],'prior_frontend_GO_commit':m['prior_GO_commit'],'frontend_end_sha256':m['frontend_end_sha256'],'frontend_argv_sha256':m['frontend_argv_sha256'],'frontend_source_bundle_sha256':hashlib.sha256(json.dumps(m['source_sha256'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'frontend_tool_bundle_sha256':hashlib.sha256(json.dumps(m['tool_files_sha256'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'complete_exclusive_copy':True,'unchanged_generated_files':True}
 p['runner']=dict(old['runner']);p['runner']['path']=NEW[2];p['runner']['GO_schema']=GO_SCHEMA
 p['runner']['argv']=['<pinned-python>',NEW[2],'--proposal',str((OUT/PROPOSAL).relative_to(ROOT)),'--go','<fresh-reuse-parent-GO.json>','--go-commit','<fresh-reuse-parent-GO-SHA>','--out','<fresh-absolute-output>']
 p['commands']=json.loads(json.dumps(old['commands']))
 p['commands']['DS'][0]={'phase':'reuse_frontend','timeout_s':300,'argv':['<pinned-python>',NEW[0],'--copy','--manifest',str(MANIFEST.relative_to(ROOT)),'--destination','<fresh-output>/DS/obj','--proposal','<fresh-output>/proposal.json','--go','<fresh-output>/GO.json','--go-commit','<fresh-GO-commit>']}
 for label in ['DS','Qwen']:
  a=p['commands'][label][1]['argv']
  a+=['-B','DEPS=','VM_USER_DIR=','OBJCACHE=','VPATH='+str(G.VROOT/'include')+' '+str(G.VROOT/'include/vltstd'),'PYTHON3='+sys.executable,'PERL=/usr/bin/perl']
 p['verified_toolchain']=json.loads(json.dumps(old['verified_toolchain']))
 for name in ['as','ld','collect2']:
  path=subprocess.check_output(['/usr/bin/g++','-print-prog-name='+name],text=True).strip()
  path=Path(path if '/' in path else shutil.which(path)).resolve()
  p['verified_toolchain']['files_sha256'][str(path)]=I.digest(path)
 p['verified_toolchain']['files_sha256'][str(Path('/usr/bin/perl').resolve())]=I.digest(Path('/usr/bin/perl').resolve())
 p['resource_plan']={**old['resource_plan'],'scope':'Separate reviewed reuse proposal, fresh GO required; all resource caps retained.','DS_frontend_reuse':p['reuse_inventory_pin'],'phase_limits_s':{'DS':{'reuse_frontend':300,'CXX':600,'simulation':180,'trace':30},'Qwen':{'frontend':300,'CXX':600,'simulation':180,'trace':30}},'no_new_DS_HDL_generation':True,'fresh_Qwen_frontend':True,'CXX_time_and_memory_measured':False,'CXX600_is_expected_completion':False,'retained_generated_DS_CXX':'ALL regular generated files copied exclusively to newobject directory and hash checked; no hardlinks, no old artifact edits, no existing objects/binary accepted. Old absolute .d targets excluded via make DEPS=. No generated-code rewriting.','risks':'CXX600s unmeasured budget, not expectedcompletion. Qwen frontend300s/32GiB still unmeasured. DS reusecopy300s includes full pin/stream verification; anyfailure preserved withoutretry.','CXX_flags':'Original -O0 and -DVL_TIME_CONTEXT; explicitmake overrides bound; -B rebuilds everytarget innewtree. DEPS= disables inclusion of oldmetadata dependencyrules. VM_USER_DIR=,explicitVPATH/OBJCACHE= prevent stale source/cache lookup.','inventory_generation':'Read-only SHA256 streaming; 11447files1.791GB; no compile/simulation.'}
 return p
if __name__=='__main__':
 p=OUT/PROPOSAL;data=(json.dumps(prepare(),indent=2,sort_keys=True)+'\n').encode()
 if p.exists():assert p.read_bytes()==data
 else:
  with p.open('xb')as f:f.write(data)
 print(p)
