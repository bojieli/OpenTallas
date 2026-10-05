#!/usr/bin/env python3
"""Qwen-only fullgeometry cold build calibration; no DS artifacts or launch."""
import copy,json,hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/hbm_qwen_frontend_r9_20261002'
EXPECTED_ROOT=Path('/home/ubuntu/OpenTallas-hbm-qwen-r9')
GO_SCHEMA='opentallas.H1.Qwen-frontend-r9.GO.v1'
NEW=['tools/prepare_hbm_qwen_frontend_r9.py','tools/run_hbm_qwen_frontend_r9.py','tools/test_hbm_qwen_frontend_r9.py']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def caps_for(target):
 if target!='Qwen':raise ValueError('Qwen-only target required')
 return load(OUT/'model.json')['caps']
RUNNER_CAPS=caps_for('Qwen')
def verify_frame(require_root=True):
 f=load(OUT/'frame.json');p=load(OUT/'original_Qwen_prepared_gate.json');old=OUT/'prior_failure';go=load(old/'GO.json');v=load(old/'verdict.json')
 if require_root and ROOT!=EXPECTED_ROOT:raise ValueError('reviewed Qwen execution root changed')
 if f['execution_root']!=str(EXPECTED_ROOT):raise ValueError('frame root changed')
 if sha(OUT/'original_Qwen_prepared_gate.json')!=f['original_proposal_sha256'] or (old/'proposal.json').read_bytes()!=(OUT/'original_Qwen_prepared_gate.json').read_bytes():raise ValueError('original proposal bytes changed')
 committed=subprocess.check_output(['git','show',f['original_GO_commit']+':'+f['original_GO_record_path']],cwd=ROOT)
 if committed!=(old/'GO.json').read_bytes() or sha(old/'GO.json')!=f['original_GO_sha256'] or sha(old/'verdict.json')!=f['original_verdict_sha256']:raise ValueError('original committed GO/verdict changed')
 if go['source_commit']!=f['original_source_commit'] or v['source_commit']!=f['original_source_commit'] or go['proposal_sha256']!=f['original_proposal_sha256'] or p['source_sha256']!=f['source_sha256'] or p['gate_tool_sha256']!=f['gate_tool_sha256'] or p['verified_toolchain']!=f['verified_toolchain'] or p['commands']!=f['commands'] or v['source_sha256']!=f['source_sha256']:raise ValueError('original source/tool/frame provenance mismatch')
 for bundle in ('source_sha256','gate_tool_sha256'):
  for path,pin in f[bundle].items():
   if sha(ROOT/path)!=pin:raise ValueError('frame source/tool changed: '+path)
 for path,pin in f['verified_toolchain']['files_sha256'].items():
  if sha(path)!=pin:raise ValueError('compiler identity changed: '+path)
 if go['runner_caps']!=p['runner_caps'] or v['proposal_sha256']!=f['original_proposal_sha256'] or v['GO_sha256']!=f['original_GO_sha256']:raise ValueError('original GO/caps provenance mismatch')
 expected=[x.replace('<fresh-output>','/tmp/hbm-qwen-runtime-calibration-parent-20261002-r2') for x in f['commands']['Qwen'][0]['argv']]
 if v['phases'][0]['argv']!=expected:raise ValueError('actual original frontend argv changed')
 if not (old/'service_journal.log').read_text().count('killed by the OOM killer') or 'Result=oom-kill' not in (old/'service_terminal.txt').read_text():raise ValueError('prior OOM evidence missing')
 if v['failure']!='TERMINATED_SIGNAL_15' or len(v['phases'])!=1 or v['phases'][0]['name']!='frontend' or v['phases'][0]['wall_s']>=300:raise ValueError('prior measured frontend failure changed')
 return f

def derive():
 f=verify_frame(False);m=load(OUT/'model.json');cmd=copy.deepcopy(f['commands'])
 for phase in cmd['Qwen']:phase['timeout_s']=m['phase_limits_s'][phase['phase']]
 p=dict(schema='opentallas.H1.Qwen-frontend-r9.prepared.v1',target='Qwen',execution_root=str(EXPECTED_ROOT),source_sha256=f['source_sha256'],gate_tool_sha256=dict(f['gate_tool_sha256']),verified_toolchain=f['verified_toolchain'],commands=cmd,runner_caps=caps_for('Qwen'),frame_sha256=sha(OUT/'frame.json'),resource_model_sha256=sha(OUT/'model.json'),prior_oom_verdict_sha256=f['original_verdict_sha256'],prospective_headroom_sha256=sha(OUT/'prospective_headroom.json'),acceptance='Fresh unchanged NC16 Qwen frontend+cold CXX16+exact thin archive/ELF only. No runtime/numerical/physical/token credit.',DS_binary_reuse=False,partial_generated_artifacts_reused=False)
 p['gate_tool_sha256'].update({path:sha(ROOT/path)for path in NEW})
 p['runner']=dict(path=NEW[1],GO_schema=GO_SCHEMA,argv=['<pinned-python>',NEW[1],'--proposal',str((OUT/'prepared_gate.json').relative_to(ROOT)),'--go','<fresh-Qwen-r9-GO.json>','--go-commit','<fresh-GO-commit>','--out','<fresh-output>'])
 return p

def prepare_target(target):
 caps_for(target);verify_frame(True);return derive()
def review_prepare():return derive()
if __name__=='__main__':
 if sys.argv[1:]!=['--review-only']:raise SystemExit('review-only; no launch')
 data=(json.dumps(review_prepare(),indent=2,sort_keys=True)+'\n').encode();dest=OUT/'prepared_gate.json'
 if dest.exists():assert dest.read_bytes()==data
 else:
  with dest.open('xb')as f:f.write(data)
 print(dest)
