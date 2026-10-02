#!/usr/bin/env python3
"""Native object shard only. No frontend, whole archive, link or simulator."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import subprocess
import time
import w17_D1_compile_ownership_handoff as ownership

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'sha256:760104a7f8f31f970fb3c1ff5bf91cfa0cb79ace21ada4454b157421df715555'
VINC = '/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def validate(packet):
    if packet.get('node') not in ('local','VM'):raise ValueError('Invalid node')
    if packet.get('owner_quiescent') is not True:raise ValueError('Old owner still active')
    if packet.get('fleet_lease_verified') is not True:raise ValueError('Fleet lease missing')
    if packet.get('runtime_authorized') is not False:raise ValueError('Runtime forbidden')
    if any(packet.get(x) is not None for x in ('wall_limit','per_process_AS','per_file_limit')):raise ValueError('Forbidden resource restriction')
    if packet.get('engine_source')!='4e38326d6f361bc85e660f48c59c355e2bb95274':raise ValueError('Engine pin changed')
    if packet.get('source_head')!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip():raise ValueError('Runner source pin')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT):raise ValueError('Dirty runner source')
    if packet.get('image')!=IMAGE:raise ValueError('Image pin')
    return packet['node']

def make_argv(obj,manifest,node):
    if node not in ('local','VM'):raise ValueError('Invalid node')
    return ['make','-C',str(obj),'-f','Vtb_D1_scope_core.mk','-f',str(manifest),'-j'+('24' if node=='local' else '48'),'CXX=/usr/bin/g++-11','OPT_FAST=-O0','OPT_SLOW=-O0','OPT_GLOBAL=-O0','D1_'+('LOCAL' if node=='local' else 'VM')+'_SHARD']

def docker_argv(out,input_root,manifest):
    argv=['docker','run','--rm','--network','none','--read-only','--user','1000:1000','--cpuset-cpus','0-47','--cpus','48','--memory',str(72*2**30),'--memory-swap',str(72*2**30),'--pids-limit','160','--ulimit','fsize=-1:-1','--name','w17-D1-disjoint-VM-20261002-r1']
    for source,target in [(out/'obj','/work/obj'),(manifest,'/work/shard.mk')]:argv+=['-v',str(source)+':'+target+('' if target=='/work/obj' else ':ro')]
    for rel,target in [('sysroot/usr/include','/usr/include'),('sysroot/usr/lib/gcc/x86_64-linux-gnu/11','/usr/lib/gcc/x86_64-linux-gnu/11'),('sysroot/usr/lib/x86_64-linux-gnu','/usr/lib/x86_64-linux-gnu'),('verilator/include',VINC)]:argv+=['-v',str(input_root/rel)+':'+target+':ro']
    return argv+['-w','/work/obj','--entrypoint','/usr/bin/make',IMAGE]+make_argv('/work/obj','/work/shard.mk','VM')[1:]

def run(packet_path,out):
    packet=json.loads(packet_path.read_text());node=validate(packet)
    if resource.getrlimit(resource.RLIMIT_AS)[0]!=resource.RLIM_INFINITY:raise ValueError('Inherited AS restriction')
    resource.setrlimit(resource.RLIMIT_FSIZE,(-1,-1))
    obj=out/'obj'
    if (out/'start.json').exists():raise ValueError('No duplicate launch')
    expected=json.loads(Path(packet['input_manifest']).read_text())
    for rel,digest in expected.items():
        if sha(obj/rel)!=digest:raise ValueError('Input hash mismatch: '+rel)
    plan=ROOT/'results/uarch/w17_D1_disjoint_compile_handoff_20261002'
    all_targets=ownership.targets((obj/'Vtb_D1_scope_core_classes.mk').read_text())
    local,remote=ownership.assignments(all_targets);selected=local if node=='local' else remote
    manifest=plan/('local_shard.mk' if node=='local' else 'VM_shard.mk')
    if manifest.read_text()!=ownership.shard_makefile(selected,'D1_'+('LOCAL' if node=='local' else 'VM')+'_SHARD'):raise ValueError('Manifest ownership mismatch')
    if shutil.disk_usage(out).free<36*2**30:raise ValueError('Disk headroom')
    # No process time/file/AS deadline, no implicit archive or runtime stage.
    argv=make_argv(obj,manifest,node) if node=='local' else docker_argv(out,Path(packet['verified_input_root']),manifest)
    receipt={'packet_SHA256':sha(packet_path),'runner_SHA256':sha(__file__),'source_head':packet['source_head'],'node':node,'targets':len(selected),'argv':argv,'runtime_authorized':False,'wall_limit':None,'AS_limit':None,'FSIZE':'unlimited','input_hashes_verified':len(expected)}
    (out/'start.json').write_text(json.dumps(receipt,indent=2)+'\n')
    start=time.monotonic()
    with (out/'compile.log').open('wb') as log:
        proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT)
        receipt['owned_PID']=proc.pid;(out/'start.json').write_text(json.dumps(receipt,indent=2)+'\n')
        while proc.poll() is None:
            (out/'progress.json').write_text(json.dumps({'owned_PID':proc.pid,'wall_s':time.monotonic()-start,'object_files_present':len(list(obj.glob('*.o'))),'disk_free_bytes':shutil.disk_usage(out).free,'wall_limit':None})+'\n')
            # Free-space monitoring; caller's capacity reservation is authoritative.
            time.sleep(10)
        status=proc.wait()
    missing=[x for x in selected if not (obj/x).exists()]
    receipt.update(exit_code=status,wall_s=time.monotonic()-start,missing_targets=missing,verdict='PASS_OBJECT_SHARD_ONLY' if status==0 and not missing else 'FAIL_OBJECT_SHARD',log_SHA256=sha(out/'compile.log'),numerical_credit=False,hardware_credit=False)
    (out/'verdict.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if receipt['verdict']=='PASS_OBJECT_SHARD_ONLY' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packet',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.packet,a.out))
