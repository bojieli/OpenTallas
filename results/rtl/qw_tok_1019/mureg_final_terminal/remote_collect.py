import sys,json,pathlib,hashlib,datetime,subprocess
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
