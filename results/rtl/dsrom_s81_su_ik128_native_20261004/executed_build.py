import json,hashlib,subprocess,time,os,sys
from pathlib import Path
root=Path('/srv/opentallas/repos/hubble-dsrom-sun256-9a1af7823')
out=Path('/srv/opentallas-scratch/builds/hubble-dsrom-sun256-ik128-sh11-20261004-r1')
launch=Path(__file__).resolve().parent
original_raw=(launch/'original_terminal.json').read_bytes();original=json.loads(original_raw)
model_raw=(launch/'model_prerequisite.json').read_bytes();model=json.loads(model_raw)
if not model.get('model_commit') or not model.get('model_entry'):
 raise RuntimeError('Peirce unified-model prerequisite missing')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==original['source_commit']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
oldmodel=json.loads((root/'results/uarch/dsrom_sun256_native_prefix_20261004/model.json').read_text())
for p,h in oldmodel['source_sha256'].items():
 assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
cmd=list(original['commands'][0]);assert cmd.count('-GKVT_SH=9')==1
cmd[cmd.index('-GKVT_SH=9')]='-GKVT_SH=11'
cmd[cmd.index('--Mdir')+1]=str(out/'obj')
assert hashlib.sha256(Path(cmd[0]).read_bytes()).hexdigest()==original['verilator_sha256']
# ONLY selected shift changes; path and four make workers are execution choices.
normal=list(cmd);normal[normal.index('-GKVT_SH=11')]='-GKVT_SH=9';normal[normal.index('--Mdir')+1]=original['commands'][0][original['commands'][0].index('--Mdir')+1]
assert normal==original['commands'][0]
out.mkdir(exist_ok=False)
rec=dict(scope='selected IK128 SUN256 KVT_SH11 archive only; not general native KV-stride fix or arithmetic/runtime admission',source_commit=original['source_commit'],supervisor_pid=os.getpid(),parameters=dict(original['parameters'],KVT_SH=11),model_prerequisite=model,model_prerequisite_sha256=hashlib.sha256(model_raw).hexdigest(),original_terminal_sha256=hashlib.sha256(original_raw).hexdigest(),verilator_sha256=original['verilator_sha256'],verilator_version=subprocess.check_output([cmd[0],'--version'],text=True).strip(),commands=[cmd],source_sha256=oldmodel['source_sha256'],stages=[],limits='No time/memory/AS/FSIZE running caps; actual EPYC admit.sh 32GB; four make workers')
rc=1
try:
 for name,argv in [('frontend',cmd),('archive',['make','-C',str(out/'obj'),'-f','VDsromSu256.mk','-j4','OPT_FAST=-O0','OPT_SLOW=-O0','VDsromSu256__ALL.a'])]:
  if name=='archive':rec['commands'].append(argv)
  t=time.monotonic()
  with (out/(name+'.log')).open('w') as f:
   p=subprocess.Popen(argv,cwd=root,stdout=f,stderr=subprocess.STDOUT);rec[name+'_pid']=p.pid
   (out/'start.json').write_text(json.dumps(rec,indent=2)+'\n');rc=p.wait()
  rec['stages'].append(dict(name=name,exit=rc,wall_seconds=time.monotonic()-t))
  if rc:break
 if rc==0:
  rec['artifacts']={}
  for n in ['VDsromSu256__ALL.a','VDsromSu256.h','VDsromSu256__verFiles.dat','VDsromSu256.mk','VDsromSu256_classes.mk']:
   p=out/'obj'/n;rec['artifacts']['obj/'+n]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
  rec['abi_header_byte_identical_to_SH9']=rec['artifacts']['obj/VDsromSu256.h']['sha256']==original['artifacts']['obj/VDsromSu256.h']['sha256']
 rec['verdict']='PASS_SELECTED_IK128_NATIVE_SU_ARCHIVE_ONLY' if rc==0 else 'FAIL_PRESERVED_NO_RETRY'
finally:
 rec['terminal_exit']=rc;(out/'terminal.json').write_text(json.dumps(rec,indent=2)+'\n')
sys.exit(rc)
