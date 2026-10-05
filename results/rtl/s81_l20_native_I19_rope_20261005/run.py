import sys,json,os,subprocess,time
from pathlib import Path
pc=int(sys.argv[1]);assert pc in (19,23)
base=Path(f'/home/ubuntu/cicero-s81-L20-native-I{pc}-rope-r1');base.mkdir(exist_ok=False);(base/'tmp').mkdir()
binary=Path('/home/ubuntu/arch-s81-I19-I23-rope-caller-r2/minimum_rope')
flag='DSROM_S81_NATIVE_L20_KROPE' if pc==19 else 'DSROM_S81_NATIVE_L20_QROPE'
env=dict(os.environ,DSROM_S81_SIM_ONLY_ROPE_CROM='1',DSROM_S81_MINIMUM_CROM_HEX='/home/ubuntu/arch-s81-I19-I23-rope-caller-r2/rope_yarn1m.hex',TMPDIR=str(base/'tmp'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');env[flag]='1'
env.pop('DSROM_S81_NATIVE_L20_QROPE' if pc==19 else 'DSROM_S81_NATIVE_L20_KROPE',None)
inputs=[f'/home/ubuntu/cicero-s81-L20-native-I15-I17-knorm-r1/runtime/native_L20_I17_rank{r}.u32' if pc==19 else f'/home/ubuntu/cicero-s81-L20-native-I14-r5-produced/native_L20_I14_rank{r}.u32' for r in range(4)]
argv=[str(binary),str(base/'runtime'),'2147483648']+inputs+['/home/ubuntu/cicero-s81-field-four-rank-caller-prep-r2/initial_H_L20_r0.u32']
(base/'runtime.argv.json').write_text(json.dumps(argv,indent=2)+'\n')
(base/'runtime.env.json').write_text(json.dumps({k:env[k] for k in (flag,'DSROM_S81_SIM_ONLY_ROPE_CROM','DSROM_S81_MINIMUM_CROM_HEX','TMPDIR')},indent=2)+'\n')
start=time.monotonic()
with (base/'runtime.log').open('x') as log:
 p=subprocess.Popen(['/home/ubuntu/bin/admit.sh','4','--']+argv,env=env,stdout=log,stderr=subprocess.STDOUT)
 (base/'runtime.pid').write_text(str(p.pid)+'\n');print('RUNTIME',pc,p.pid,flush=True);rc=p.wait()
(base/'terminal.json').write_text(json.dumps({'exit':rc,'argv':argv,'pc':pc,'elapsed_host_seconds':time.monotonic()-start,'source_commit':'abb54528dbb50e00395eec3294e4d705056f1b72','scope':f'Native I{pc} on actual produced carry/fresh VM ACK; I18 coefficient staging and initial prefix SIM_ONLY','full_token':False},indent=2)+'\n')
raise SystemExit(rc)
