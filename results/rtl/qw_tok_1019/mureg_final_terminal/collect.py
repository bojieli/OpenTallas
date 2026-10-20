import subprocess,json,hashlib,pathlib,shlex,datetime,re
base=pathlib.Path('/home/ubuntu/artifacts/qw-mureg-final-1019');base.mkdir(parents=True,exist_ok=True)
prefix='results/rtl/qw_tok_1019/mureg_terminal_1402/'
prior=json.loads(subprocess.check_output(['git','-C','/home/ubuntu/OpenTallas','show','b83d7515f:'+prefix+'receipt.json']))
code='''import sys,json,pathlib,hashlib,datetime,subprocess
p=json.load(sys.stdin); root=pathlib.Path('/srv/opentallas-scratch/claude/refill-1225/QWREG'); sha=lambda b:hashlib.sha256(b).hexdigest()
paths={x['path'] for x in p['files']}; c=root/'out/ctlm_nsl12/w/qctlm/cal'; paths.update(str(x) for x in c.glob('*.txt')); paths.add(str(root/'src/rtl/test/qwen_dv/tt_ctlm_cal_bench.py'))
for rr in ['run_all_hroot.sh','run_mu_hroot.sh','run_all_kv.sh','run_mu_kv.sh']:
 paths.add(str(root/'src/rtl/test/mu_qwen_1018'/rr))
for scope in ['amix','adopt_slice']:
 paths.update(str(x) for x in (root/'src/results/rtl/mu_qwen_1018'/scope/'runs').glob('*.out'))
 paths.add(str(root/'src/SOURCE_COMMIT'))
files=[]
for s in sorted(paths):
 q=pathlib.Path(s); b=q.read_bytes(); files.append(dict(path=s,sha256=sha(b),text=b.decode()))
sources={s:sha((root/'src'/s).read_bytes()) for s in p['source_hashes']}
exes={x['path'] for x in p['executables']}; exes.update(str(x) for x in c.glob('obj_*/Vtb'))
ee=[]
for s in sorted(exes):
 q=pathlib.Path(s); b=q.read_bytes(); ee.append(dict(path=s,sha256=sha(b),bytes=len(b),mtime_ns=q.stat().st_mtime_ns))
proc=subprocess.check_output(['ps','-eo','pid,ppid,etime,comm,args'],text=True)
print(json.dumps(dict(collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=p['source_commit'],files=files,source_hashes=sources,executables=ee,processes_matching_runtime=[s for s in proc.splitlines() if str(root) in s and s.split()[3] not in ('python3','ssh','sh') and ('Vtb' in s or 'verilator' in s or 'run_mu_ctlm.sh' in s or 'run_tt_ctlm_dv.sh' in s)])))
'''
r=subprocess.run(['ssh','ot-epyc7','python3 -c '+shlex.quote(code)],input=json.dumps(prior),text=True,capture_output=True,timeout=120,check=True)
(base/'receipt.json').write_text(json.dumps(json.loads(r.stdout),indent=2)+'\n')
(base/'remote_collect.py').write_text(code)
receipt=json.loads(r.stdout)
for f in receipt['files']:
 q=base/'raw'/f['path'].split('/QWREG/',1)[1];q.parent.mkdir(parents=True,exist_ok=True);q.write_text(f['text']);assert hashlib.sha256(q.read_bytes()).hexdigest()==f['sha256']
status=[]
for p in sorted(pathlib.Path('/home/ubuntu/scratch/refill-1225/QWREG/legs').glob('*.log')):
 text=p.read_text();q=base/'client_logs'/p.name;q.parent.mkdir(exist_ok=True);q.write_text(text);m=re.search(r'# ot-run rc=(\d+) (\S+)',text);status.append(dict(leg=p.stem,terminal=bool(m),client_rc=int(m[1]) if m else None,finished_at=m[2] if m else None,client_log_sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
(base/'leg_status.json').write_text(json.dumps(status,indent=2)+'\n')
oldex={x['path']:x['sha256'] for x in prior['executables']}; newex={x['path']:x['sha256'] for x in receipt['executables']}
compare=dict(source_candidate=receipt['source_commit'],sampled_source_files=len(prior['source_hashes']),source_hashes_equal_previous=receipt['source_hashes']==prior['source_hashes'],previous_executables=len(oldex),previous_executable_changed=[s for s,h in oldex.items() if newex.get(s)!=h],new_executables=[x for x in receipt['executables'] if x['path'] not in oldex],terminal_legs=sum(x['terminal'] for x in status),client_exit_zero=sum(x['client_rc']==0 for x in status),client_exit_one=[x['leg'] for x in status if x['client_rc']==1])
(base/'comparison.json').write_text(json.dumps(compare,indent=2)+'\n')
w=[dict(path=x['path'],witness=l) for x in receipt['files'] for l in x['text'].splitlines() if any(s in l for s in ['CTLM_ABI_PASS','CTLM_ABI_FAIL','CTLM_CAL MUT=','QCTLM BENCHES:','MU_CTLM BENCHES:']) and '/src/' not in x['path']]
(base/'final_ctlm_witnesses.json').write_text(json.dumps(w,indent=2)+'\n')
print(json.dumps(compare,indent=2))
