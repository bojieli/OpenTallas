import hashlib,json,os,subprocess,time
from pathlib import Path
out=Path('/tmp/hbm-qwen-connected-runtime-parent-20261002-r11-r1');worker=Path('/home/ubuntu/OpenTallas-hbm-qwen-runtime-r11');repo=Path(__file__).resolve().parents[1];unit='hbm-qwen-connected-runtime-parent-20261002-r11-r1.service'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
raw=subprocess.check_output(['systemctl','--user','show',unit],text=True);info=dict(x.split('=',1)for x in raw.splitlines()if'='in x)
if int(info.get('MainPID','0')) or info['ActiveState']=='active':raise SystemExit('LIVE: collection refused')
if not(out/'verdict.json').exists():raise SystemExit('Terminal verdict missing: preserve journal separately; do not invent verdict')
v=json.loads((out/'verdict.json').read_text());go=json.loads((out/'GO.json').read_text());dest=repo/'results/rtl/hbm_qwen_r11_terminal_owner_20261002_r1'
if dest.exists():raise SystemExit('immutable terminal archive already exists')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=worker,text=True).strip()==go['source_commit']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=worker,text=True)
assert subprocess.check_output(['git','show',v['GO_commit']+':'+go['admission_record_path']],cwd=worker)==(out/'GO.json').read_bytes()
assert sha(out/'proposal.json')==go['proposal_sha256']
proposal=json.loads((out/'proposal.json').read_text())
for bundle in ('source_sha256','gate_tool_sha256'):
 for name,pin in proposal[bundle].items():assert sha(worker/name)==pin
for bundle in (proposal['verified_toolchain']['files_sha256'],proposal['runtime_libraries_sha256']):
 for name,pin in bundle.items():assert sha(name)==pin
dest.mkdir(parents=True)
inventory=[]
for p in sorted(out.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(out);record=dict(path=str(rel),bytes=p.stat().st_size,sha256=sha(p));inventory.append(record)
 if rel==Path('Qwen/obj/Vconnected'):continue
 q=dest/'raw'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());assert sha(q)==record['sha256']
(dest/'raw_inventory.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n'for x in inventory))
(dest/'systemd.show').write_text(raw)
(dest/'journal.log').write_bytes(subprocess.check_output(['journalctl','--user','-u',unit,'--no-pager']))
import sys
sys.path.insert(0,str(worker/'tools'));import check_hbm_rf_connected_trace as T
try:check=T.check((out/'Qwen/actual_sim.log').read_text());trace_replay=dict(success=True,result=check)
except Exception as e:trace_replay=dict(success=False,error=str(e))
(dest/'independent_trace_replay.json').write_text(json.dumps(trace_replay,indent=2,sort_keys=True)+'\n')
binary=out/'Qwen/obj/Vconnected';qualified=json.loads((worker/'results/uarch/hbm_qwen_runtime_r11_20261002/qualified_binary.json').read_text())
assert sha(binary)==qualified['binary']['sha256']
for rel,h in v.get('logs_sha256',{}).items():assert sha(out/rel)==h
for rel,h in v.get('binary_sha256',{}).items():assert sha(out/rel)==h
for rel,h in v.get('trace_sha256',{}).items():assert sha(out/rel)==h
cgpath=info.get('ControlGroup','')
cg=Path('/sys/fs/cgroup')/cgpath.lstrip('/') if cgpath else None
procs=(cg/'cgroup.procs').read_text().strip()if cg is not None and cg.is_dir()and(cg/'cgroup.procs').exists()else 'service cgroup unavailable after drain; never inspect root cgroup'
review=dict(schema='opentallas.H1.Qwen-runtime-r11.owner-terminal.v1',observed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_commit=go['source_commit'],source_clean=True,GO_commit=v['GO_commit'],verdict=v['verdict'],raw_verdict_sha256=sha(out/'verdict.json'),proposal_sha256=sha(out/'proposal.json'),binary_sha256=sha(binary),systemd={k:info.get(k)for k in ['ActiveState','SubState','MainPID','Result','ExecMainStatus','ExecMainExitTimestamp']},phase_receipts=v['phases'],wall_s=v['wall_s'],memory_terminal_observation=v.get('memory_terminal_observation'),output_bytes=v['output_bytes'],independent_trace_check_PASS=trace_replay['success'],cgroup_procs=procs,numerical_scope='Directed Qwen NC16/128SIMD four connected cases plus reset only; not exhaustive arithmetic or general token/scalar oracle',full_token_credit=False,physical_credit=False,clock_closure_credit=False,job_retirement='Execution terminal; source and qualified ELF retained pending parent archival review. No checkpoint deletion.',no_restart=True)
(dest/'review.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n');print(dest);print(json.dumps(review,indent=2))
