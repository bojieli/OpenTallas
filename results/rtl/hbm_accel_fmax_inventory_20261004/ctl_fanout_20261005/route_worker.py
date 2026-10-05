import json,os,subprocess,sys,hashlib
from pathlib import Path
job=Path(sys.argv[1]);src=Path(sys.argv[2]);recipe=json.loads((job/'recipe.json').read_text())
os.chdir(src)
assert not subprocess.check_output(['git','status','--porcelain']).strip(), 'source dirty'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==recipe['source_commit']
for p,h in recipe['source_sha256'].items():
 assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
(job/'admitted_meminfo.txt').write_text(Path('/proc/meminfo').read_text())
(job/'admitted_loadavg.txt').write_text(Path('/proc/loadavg').read_text())
(job/'worker.pid').write_text(str(os.getpid())+'\n')
env=os.environ.copy();env.update(recipe['environment'])
with (job/'run.log').open('w') as log:
 proc=subprocess.Popen(recipe['argv'],stdout=log,stderr=subprocess.STDOUT,env=env)
 (job/'driver.pid').write_text(str(proc.pid)+'\n');rc=proc.wait()
(job/'route.exit').write_text(str(rc)+'\n')
corner=None
if (job/'work/orfs/results/asap7').exists():
 with (job/'corner.log').open('w') as log:
  corner=subprocess.call(['python3','tools/w18/corner_sta.py','--orfs-dir',str(job/'work/orfs'),'--output',str(job/'corner_sta.json')],stdout=log,stderr=subprocess.STDOUT,env=env)
 (job/'corner.exit').write_text(str(corner)+'\n')
(job/'exit').write_text(str(rc if rc else (corner if corner is not None else 91))+'\n')
