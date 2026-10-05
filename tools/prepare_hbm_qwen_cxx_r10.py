#!/usr/bin/env python3
"""One source-identical cold-CXX successor using only qualified complete frontend."""
import copy,json,sys
from pathlib import Path
import hbm_qwen_frontend_reuse_r10 as I
ROOT=I.ROOT;OUT=I.OUT;GO_SCHEMA='opentallas.H1.Qwen-CXX-r10.GO.v1'
NEW=['tools/model_hbm_qwen_cxx_r10.py','tools/hbm_qwen_frontend_reuse_r10.py','tools/prepare_hbm_qwen_cxx_r10.py','tools/run_hbm_qwen_cxx_r10.py','tools/test_hbm_qwen_cxx_r10.py']
def caps_for(target):
 if target!='Qwen':raise ValueError('Qwen-only target required')
 return I.load(OUT/'model.json')['caps']
RUNNER_CAPS=caps_for('Qwen')
def derive():
 m=I.verify(False);old=I.load(OUT/'parent_checkpoint/proposal.json');model=I.load(OUT/'model.json');p=copy.deepcopy(old)
 p.update(schema='opentallas.H1.Qwen-CXX-r10.prepared.v1',execution_root=str(I.EXPECTED_ROOT),runner_caps=caps_for('Qwen'),resource_model_sha256=I.sha(OUT/'model.json'),prior_terminal_verdict_sha256=I.sha(OUT/'parent_checkpoint/verdict.json'),frontend_manifest_sha256=I.sha(OUT/'frontend_manifest.json'),frame_sha256=I.sha(OUT/'frontend_inventory.jsonl'),prospective_headroom_sha256=I.sha(OUT/'resource_snapshot.json'))
 p.pop('prior_oom_verdict_sha256',None)
 p['commands']={'Qwen':[dict(phase='reuse_frontend',timeout_s=300,argv=['<pinned-python>',NEW[1],'--destination','<fresh-output>/Qwen/obj','--proposal','<fresh-output>/proposal.json','--go','<fresh-output>/GO.json','--go-commit','<fresh-GO-commit>']),copy.deepcopy(old['commands']['Qwen'][1])]};p['commands']['Qwen'][1]['timeout_s']=model['CXX_limit_s']
 p['gate_tool_sha256'].update({name:I.sha(ROOT/name)for name in NEW});p['acceptance']='One qualified complete frontend copy, fresh fullgeometry cold CXX16 exactthinarchive+linkedELF only; no partialobjects reused and no runtime/numerical/physical/token credit.'
 p['runner']=dict(path=NEW[3],GO_schema=GO_SCHEMA,argv=['<pinned-python>',NEW[3],'--proposal',str((OUT/'prepared_gate.json').relative_to(ROOT)),'--go','<fresh-Qwen-r10-GO.json>','--go-commit','<fresh-GO-commit>','--out','<fresh-output>'])
 return p

def prepare_target(target):caps_for(target);I.verify(True);return derive()
def review_prepare():return derive()
if __name__=='__main__':
 if sys.argv[1:]!=['--review-only']:raise SystemExit('review-only; no launch')
 data=(json.dumps(review_prepare(),indent=2,sort_keys=True)+'\n').encode();path=OUT/'prepared_gate.json'
 if path.exists():assert path.read_bytes()==data
 else:
  with path.open('xb')as f:f.write(data)
 print(path)
