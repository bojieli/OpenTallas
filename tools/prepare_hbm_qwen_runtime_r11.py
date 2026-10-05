#!/usr/bin/env python3
"""Prepare the qualified fullgeometry directed Qwen runtime; never launch."""
import copy,json,sys
from pathlib import Path
import hbm_qwen_binary_reuse_r11 as I
ROOT=I.ROOT;OUT=I.OUT;GO_SCHEMA='opentallas.H1.Qwen-runtime-r11.GO.v1'
NEW=['tools/hbm_qwen_binary_reuse_r11.py','tools/prepare_hbm_qwen_runtime_r11.py','tools/run_hbm_qwen_runtime_r11.py','tools/test_hbm_qwen_runtime_r11.py']
def caps_for(target):
 if target!='Qwen':raise ValueError('Qwen-only target required')
 return I.load(OUT/'model.json')['caps']
RUNNER_CAPS=caps_for('Qwen')
def derive():
 m=I.verify(False);model=I.load(OUT/'model.json')
 p=dict(schema='opentallas.H1.Qwen-runtime-r11.prepared.v1',target='Qwen',execution_root=str(I.EXPECTED_ROOT),runner_caps=caps_for('Qwen'),source_sha256=m['source_sha256'],gate_tool_sha256=copy.deepcopy(m['gate_tool_sha256']),verified_toolchain=m['verified_toolchain'],runtime_libraries_sha256=m['runtime_libraries_sha256'],resource_model_sha256=I.sha(OUT/'model.json'),qualified_binary_manifest_sha256=I.sha(OUT/'qualified_binary.json'),prior_terminal_verdict_sha256=I.sha(OUT/'qualified_build/verdict.json'),prospective_headroom_sha256=I.sha(OUT/'resource_snapshot.json'),parent_review_sha256=m['parent_review_sha256'])
 p['gate_tool_sha256'].update({f:I.sha(ROOT/f)for f in NEW})
 p['commands']={'Qwen':[dict(phase='reuse_binary',timeout_s=model['phases']['reuse_binary'],argv=['<pinned-python>',NEW[0],'--manifest',str((OUT/'qualified_binary.json').relative_to(ROOT)),'--destination','<fresh-output>/Qwen/obj/Vconnected','--proposal','<fresh-output>/proposal.json','--go','<fresh-output>/GO.json','--go-commit','<fresh-GO-commit>']),dict(phase='simulation',timeout_s=model['phases']['simulation'],argv=['<fresh-output>/Qwen/obj/Vconnected']),dict(phase='trace',timeout_s=model['phases']['trace'],argv=['<pinned-python>','tools/check_hbm_rf_connected_trace.py','<fresh-output>/Qwen/actual_sim.log','--out','<fresh-output>/Qwen/trace_verdict.json'])]}
 p['acceptance']=model['scope'];p['progress']='Original binary uses libc stdout; pinned /usr/bin/stdbuf -oL -eL exposes existing progress only; no DUT modification.'
 p['commands']['Qwen'][1]['argv'].insert(0,'/usr/bin/stdbuf');p['commands']['Qwen'][1]['argv'][1:1]=['-oL','-eL']
 # Pin the only deliberately injected buffering library and the wrapper.
 for f in ('/usr/bin/stdbuf','/usr/libexec/coreutils/libstdbuf.so'):p['runtime_libraries_sha256'][f]=I.sha(f)
 p['runner']=dict(path=NEW[2],GO_schema=GO_SCHEMA,argv=['<pinned-python>',NEW[2],'--proposal',str((OUT/'prepared_gate.json').relative_to(ROOT)),'--go','<fresh-r11-GO.json>','--go-commit','<fresh-GO-commit>','--out','<fresh-output>'])
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
