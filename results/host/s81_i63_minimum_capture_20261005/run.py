import hashlib, json, os, subprocess, time
from pathlib import Path

base=Path('/srv/opentallas-scratch/jobs/arch-i63-minimum-capture-20261005')
repo=Path('/srv/opentallas/repos/arch-i63-minimum-capture-20261005')
src=base/'source'
vl=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
env=dict(os.environ,HDC_V41_ARITH='chunk8',HDC_V41_FUSE='',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
commands=[['python3',str(src/'prepare.py'),str(repo),str(base)],
 ['g++','-std=c++17','-O2','-pthread','-I'+str(src),'-I'+str(base/'adapter'),
  '-isystem',str(vl),'-isystem',str(vl/'vltstd'),str(src/'capture.cpp'),
  str(base/'adapter/VDsromAttention__ALL.a'),str(base/'adapter/libverilated.a'),'-ldl','-o',str(base/'capture')],
 ['/usr/bin/time','-v',str(base/'capture'),str(base/'inputs'),str(base/'captured')]]
receipt=dict(scope='ONE controlled-source I63 PV; SIM_ONLY endpoint, native adapter; no original-run attribution',
 source_commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
 estimated_host_peak_bytes=2*1024**3,compiler_workers=1,stages=[])
for label,cmd in zip(['prepare','compile','capture'],commands):
 start=time.monotonic()
 with (base/(label+'.log')).open('w') as log:
  result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 receipt['stages'].append(dict(name=label,command=cmd,exit=result.returncode,seconds=time.monotonic()-start))
 if result.returncode:break
receipt['exit']=result.returncode
receipt['source_sha256']={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest()
 for directory in [src,base/'adapter'] for p in directory.iterdir() if p.is_file()}
if result.returncode==0:
 receipt['captured_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (base/'captured').iterdir() if p.is_file()}
(base/'terminal.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(result.returncode)
