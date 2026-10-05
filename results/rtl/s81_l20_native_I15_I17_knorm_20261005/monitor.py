import json,os,subprocess,time
from pathlib import Path
base=Path('/home/ubuntu/cicero-s81-L20-native-I15-I17-knorm-r1')
while not (base/'terminal.json').exists():time.sleep(30)
t=json.loads((base/'terminal.json').read_text());print('TERMINAL',json.dumps(t),flush=True);print((base/'runtime.log').read_text(),flush=True)
if t['exit']==0:
 env=dict(os.environ,TMPDIR=str(base/'tmp'),PYTHONPATH='/home/ubuntu/dsrom-minimum-token-caller-20261004/tools',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 with (base/'compare.log').open('x') as log:r=subprocess.run(['/home/ubuntu/bin/admit.sh','4','--','python3',str(base/'compare.py')],env=env,stdout=log,stderr=subprocess.STDOUT)
 (base/'compare.exit').write_text(str(r.returncode)+'\n');print('COMPARE',r.returncode,(base/'compare.log').read_text(),flush=True)
