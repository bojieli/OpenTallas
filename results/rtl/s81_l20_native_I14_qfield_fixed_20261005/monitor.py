import json,os,subprocess,time
from pathlib import Path
base=Path('/srv/opentallas-scratch2/jobs/cicero-s81-I14-native-r5');owner=Path('/srv/opentallas-scratch2/jobs/arch-s81-I14-fragment-caller-r2');remaining=set(range(4))
env=dict(os.environ,TMPDIR=str(base/'tmp'),PYTHONPATH=str(base/'source/tools'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
while remaining:
 for rank in sorted(remaining):
  job=base/f'rank{rank}';path=job/'chain-terminal.json'
  if not path.exists():continue
  t=json.loads(path.read_text());print('TERMINAL',rank,json.dumps(t),flush=True)
  for fragment in (0,1):
   log=job/f'fragment{fragment}/runtime.log'
   if log.exists():print(log.read_text(),flush=True)
  if t['exit']==0:
   command=['/srv/opentallas-scratch/admit.sh','8','--','python3',str(base/'compare.py'),'--rank',str(rank)]
   with (job/'compare.log').open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
   (job/'compare.exit').write_text(str(r.returncode)+'\n');print('COMPARE',rank,'EXIT',r.returncode,(job/'compare.log').read_text(),flush=True)
  remaining.remove(rank)
 if remaining:time.sleep(30)
