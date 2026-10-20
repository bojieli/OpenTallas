from pathlib import Path
import json,os,subprocess
B=Path.cwd();rows=json.loads((B/'cases.json').read_text());image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
cmd=['docker','run','--rm','--user',str(os.getuid())+':'+str(os.getgid()),'-v',str(B)+':/stage']
for job in sorted({str(Path(r['orfs_dir']).parents[3]) for r in rows}):cmd+=['-v',job+':'+job+':ro']
cmd+=['--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',image,'-no_init','-exit','-python','/stage/repair_guard.py']
with (B/'repair_guard.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
(B/'repair_execution.json').write_text(json.dumps(dict(command=cmd,returncode=r.returncode),indent=2))
print('PRIVATE_PG_GUARD_RC',r.returncode,flush=True)
raise SystemExit(r.returncode)
