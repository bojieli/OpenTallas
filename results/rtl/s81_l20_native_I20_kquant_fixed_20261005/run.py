import json,os,subprocess,time
from pathlib import Path
base=Path('/home/ubuntu/cicero-s81-L20-native-I20-kquant-r2')
binary=Path('/home/ubuntu/arch-s81-I20-xr-response-fix-r2/minimum_kquant')
env=dict(os.environ,DSROM_S81_NATIVE_L20_KQUANT='1',TMPDIR=str(base/'tmp'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
argv=[str(binary),str(base/'runtime'),'2147483648']+[f'/home/ubuntu/cicero-s81-L20-native-I19-rope-r1/runtime/native_L20_I19_rank{r}.u32' for r in range(4)]+['/home/ubuntu/cicero-s81-field-four-rank-caller-prep-r2/initial_H_L20_r0.u32']
(base/'runtime.argv.json').write_text(json.dumps(argv,indent=2)+'\n')
(base/'runtime.env.json').write_text(json.dumps({k:env[k] for k in ('DSROM_S81_NATIVE_L20_KQUANT','TMPDIR')},indent=2)+'\n')
start=time.monotonic()
with (base/'runtime.log').open('x') as log:
 p=subprocess.Popen(['/home/ubuntu/bin/admit.sh','4','--']+argv,env=env,stdout=log,stderr=subprocess.STDOUT)
 (base/'runtime.pid').write_text(str(p.pid)+'\n');print('RUNTIME',p.pid,flush=True);rc=p.wait()
(base/'terminal.json').write_text(json.dumps({'exit':rc,'argv':argv,'elapsed_host_seconds':time.monotonic()-start,'source_commit':'f5753dda5','caller_source_commit':'74997e5403864b5fbf96585f8c43583ea9312235','scope':'Native I20 allfourranks actual I19 KVN with VM ACK; I18coefficients and initialprefix SIM_ONLY; no WINDOW visibility/fulltoken','full_token':False},indent=2)+'\n')
raise SystemExit(rc)
