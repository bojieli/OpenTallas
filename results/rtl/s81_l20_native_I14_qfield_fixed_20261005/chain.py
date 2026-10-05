import json,os,subprocess,time,sys
from pathlib import Path
rank=int(sys.argv[1]);base=Path('/srv/opentallas-scratch2/jobs/cicero-s81-I14-native-r5');model=Path('/srv/opentallas-scratch2/jobs/arch-s81-I14-fragment-caller-r2');job=base/f'rank{rank}';job.mkdir(exist_ok=False)
env=dict(os.environ,TMPDIR=str(base/'tmp'),PYTHONPATH=str(base/'source/tools'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');env.pop('DSROM_S81_NATIVE_L20_FIELD',None);started=time.monotonic();rc=0
for fragment in (0,1):
 cmd=['/srv/opentallas-scratch/admit.sh','8','--','python3',str(base/'source/tools/dsrom_s81_l20_qfield_run.py'),'--owner',str(base/'source'),'--checkpoint',str(model/'checkpoint/dba1be0a40aa45a94ad051997016db3960a90277'),'--qnorm-run',str(model/'qnorm-r2'),'--rank',str(rank),'--fragment',str(fragment),'--controls',str(model/f'controls-f{fragment}'),'--binary',str(base/f'minimum_qfield_f{fragment}'),'--output',str(job/f'fragment{fragment}')]
 (job/f'fragment{fragment}.argv.json').write_text(json.dumps(cmd,indent=2)+'\n')
 with (job/f'fragment{fragment}.launcher.log').open('w') as log:
  p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT);(job/f'fragment{fragment}.launcher.pid').write_text(str(p.pid)+'\n');print('RANK',rank,'FRAGMENT',fragment,'LAUNCHER',p.pid,flush=True);rc=p.wait()
 if rc:break
(job/'chain-terminal.json').write_text(json.dumps(dict(exit=rc,rank=rank,elapsed_host_seconds=time.monotonic()-started,scope='Native I14 two ordered fragments on actual native I13 QR, entering I0-I6 prefix SIM_ONLY; no fulltoken/timing qualification'),indent=2)+'\n');sys.exit(rc)
