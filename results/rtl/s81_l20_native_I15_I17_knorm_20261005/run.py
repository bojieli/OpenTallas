import json,os,subprocess,time
from pathlib import Path
base=Path('/home/ubuntu/cicero-s81-L20-native-I15-I17-knorm-r1')
binary=Path('/home/ubuntu/arch-s81-I15-I17-knorm-caller-r1/minimum_knorm')
env=dict(os.environ,DSROM_S81_NATIVE_L20_KNORM='1',DSROM_S81_MINIMUM_CROM_HEX='/home/ubuntu/cicero-s81-l20-attention-remote-r1/staged/tmp/arch-s81-L20-full-field-r1/I7/crom.L20.hex',TMPDIR=str(base/'tmp'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
argv=[str(binary),str(base/'runtime'),'2147483648']+[f'/home/ubuntu/cicero-s81-L20-native-I10-gather-r1/runtime/native_L20_I10_rank{r}.u32' for r in range(4)]+['/home/ubuntu/cicero-s81-field-four-rank-caller-prep-r2/initial_H_L20_r0.u32']
(base/'runtime.argv.json').write_text(json.dumps(argv,indent=2)+'\n')
(base/'runtime.env.json').write_text(json.dumps({k:env[k] for k in ('DSROM_S81_NATIVE_L20_KNORM','DSROM_S81_MINIMUM_CROM_HEX','TMPDIR')},indent=2)+'\n')
start=time.monotonic()
with (base/'runtime.log').open('x') as log:
 p=subprocess.Popen(['/home/ubuntu/bin/admit.sh','4','--']+argv,env=env,stdout=log,stderr=subprocess.STDOUT)
 (base/'runtime.pid').write_text(str(p.pid)+'\n');print('RUNTIME',p.pid,flush=True);rc=p.wait()
(base/'terminal.json').write_text(json.dumps({'exit':rc,'argv':argv,'elapsed_host_seconds':time.monotonic()-start,'source_commit':'81f627d40','scope':'Native I15-I17 allfourranks from actual I10 KVA; initial prefix SIM_ONLY; independent of I14 Q','full_token':False},indent=2)+'\n')
raise SystemExit(rc)
