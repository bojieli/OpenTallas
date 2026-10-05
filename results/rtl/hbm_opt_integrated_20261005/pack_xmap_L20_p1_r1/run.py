import json,os,subprocess,sys,traceback,hashlib
from pathlib import Path
j=Path(sys.argv[1]).resolve();s=j/'source';identity=json.loads((j/'source_identity.json').read_text())
try:
 for p,h in identity['source_pins'].items():assert hashlib.sha256((s/p).read_bytes()).hexdigest()==h,p
 subprocess.run(['git','init','-q',str(s)],check=True)
 subprocess.run(['git','-C',str(s),'add','--',*identity['source_pins']],check=True)
 subprocess.run(['git','-C',str(s),'-c','gc.auto=0','-c','user.name=Rawls','-c','user.email=rawls@localhost','commit','-qm','Pinned selected combined source snapshot'],check=True)
 argv=[sys.executable,str(s/'tools/hbm_opt_integrated_20261005_pack_xmap.py'),'--job',str(j/'measurement'),'--paired-case',str(j/'paired_case')]
 (j/'driver_command.json').write_text(json.dumps(argv,indent=2)+'\n')
 with (j/'driver.log').open('x') as log:rc=subprocess.run(argv,cwd=s,stdout=log,stderr=subprocess.STDOUT).returncode
 stable=all(hashlib.sha256((s/p).read_bytes()).hexdigest()==h for p,h in identity['source_pins'].items())
 result=j/'measurement/result.json';r=json.loads(result.read_text()) if result.exists() else None
 (j/'terminal.json').write_text(json.dumps(dict(status='pass' if rc==0 and stable and r and r['accepted'] else 'fail',driver_exit=rc,source_stable=stable,result=r,source_main_commit=identity['source_main_commit'],full_token_measured=False,SS_FF_admitted=False),indent=2)+'\n')
except Exception:
 (j/'launcher_failure.txt').write_text(traceback.format_exc());rc=1
 if not (j/'terminal.json').exists():(j/'terminal.json').write_text(json.dumps(dict(status='fail',first_blocker='launcher exception'))+'\n')
(j/'runtime.exit').write_text(str(rc)+'\n')
sys.exit(rc)
