import hashlib, json, os, shutil, subprocess, time
from pathlib import Path

base=Path('/srv/opentallas-scratch/jobs/arch-qk-su-pv-minimum-20261005')
old=Path('/srv/opentallas-scratch/jobs/arch-i63-minimum-capture-20261005')
deps=base/'deps'; source=base/'source'; headers=base/'headers'
headers.mkdir(exist_ok=True)
subprocess.run(['tar','-xzf',str(base/'headers.tar.gz'),'-C',str(headers)],check=True)
inc=headers/'tools/runtime/dsrom'
# Freeze the accepted-byte PASS endpoint and Cut used in the prior diagnostic.
for name in ['s81_sim_only_attention_endpoint.hpp','s81_minimum_attention_cut.hpp']:
    shutil.copy2(old/'source'/name,inc/name)
fixture=Path('/home/ubuntu/w17work/isa/scratch_s20260930/images/ctx1048576_L20_r0')
fixture.mkdir(parents=True,exist_ok=True)
for name in ['io.h_in.bin','io.pre_in.bin']:
    target=fixture/name; original=deps/name
    if target.exists():
        assert target.read_bytes()==original.read_bytes(), 'existing fixture mismatch'
    else: shutil.copy2(original,target)
inputs=base/'inputs';inputs.mkdir(exist_ok=True)
for name in ['source_kv_beats.u32']:
    shutil.copy2(old/'inputs'/name,inputs/name)
shutil.copy2(deps/'I55.Q_rank0.u32',inputs/'I55.Q_rank0.u32')
shutil.copy2(deps/'io.h_in.bin',inputs/'H.u32')
env=dict(os.environ,DSROM_S81_MINIMUM_SELECTED_DIR=str(deps/'I7'),HDC_V41_ARITH='chunk8',HDC_V41_FUSE='',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
vl=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
includes=['-I'+str(source),'-I'+str(inc),'-I'+str(headers/'rtl/test/v41_runtime'),'-I'+str(deps/'inc4'),'-I'+str(deps/'inc13'),'-I'+str(old/'adapter'),'-isystem',str(vl),'-isystem',str(vl/'vltstd')]
common=['g++','-std=c++17','-O2','-pthread']+includes
commands=[('compile_capture',common+['-c',str(source/'capture.cpp'),'-o',str(base/'capture.o')]),
 ('compile_su_provider',common+['-c',str(inc/'s81_minimum_su256.cpp'),'-o',str(base/'su_provider.o')]),
 ('compile_tags',common+['-c',str(inc/'s81_minimum_source_tags_component.cpp'),'-o',str(base/'tags.o')]),
 ('link',['g++','-O2','-pthread',str(base/'capture.o'),str(base/'su_provider.o'),str(base/'tags.o'),'-Wl,--start-group',str(deps/'VDsromSu256_O2_unique.a'),str(deps/'Vnative_vm__ALL.a'),str(old/'adapter/VDsromAttention__ALL.a'),str(old/'adapter/libverilated.a'),'-Wl,--end-group','-ldl','-lcrypto','-o',str(base/'capture')]),
 ('runtime',['/usr/bin/time','-v',str(base/'capture'),str(inputs),str(base/'captured')])]
pins={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [source,headers,deps,inputs] for p in folder.rglob('*') if p.is_file()}
record=dict(source_commit='738cb3095',scope='One controlled-source rank0 QK -> native SU I61/I62 -> PV; native VM matched ACK, SIM_ONLY arithmetic endpoint; no original accepted-input reconstruction or physical timing claim',estimated_host_peak_bytes=2*1024**3,compiler_workers=1,source_library_input_sha256=pins,stages=[])
(base/'frozen_inputs.json').write_text(json.dumps(record,indent=2)+'\n')
for name,command in commands:
    start=time.monotonic()
    with (base/(name+'.log')).open('w') as f:
        result=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
    record['stages'].append(dict(name=name,command=command,exit=result.returncode,seconds=time.monotonic()-start))
    (base/'progress.json').write_text(json.dumps(record,indent=2)+'\n')
    if result.returncode: break
record['exit']=result.returncode
if result.returncode==0:
    record['captured_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (base/'captured').iterdir() if p.is_file()}
(base/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(result.returncode)
