"""Pure, source-enrolled native relink command. Never launches a compiler/runtime."""
import json,hashlib
from pathlib import Path
BASE='results/rtl/w17_PC24_fast_native_trace_preparation_20261002/native_link_plan.json'
EVIDENCE='results/rtl/w17_existing_port_relink_provenance_20261002'
IMAGE='sha256:760104a7f8f31f970fb3c1ff5bf91cfa0cb79ace21ada4454b157421df715555'

def mapped(arg):
    if arg.startswith('-I/'):return '-I/inputs'+arg[2:]
    if arg.startswith('/') and (arg.endswith('.cpp') or arg.endswith('.a')):return '/inputs'+arg
    return arg

def build(root):
    native=json.loads((root/BASE).read_text());argv=[mapped(x) for x in native['argv']];argv[-1]='/output/v41_existing_port_trace'
    inputs={}
    for name in ['archives.json','headers.json','compile_sources.json']:
        d=json.loads((root/EVIDENCE/name).read_text());inputs.update(d)
    pins={p:x['sha256'] for p,x in inputs.items()}
    return dict(source_commit='4e38326d6f361bc85e660f48c59c355e2bb95274',scope='NATIVE_RELINK_ONLY_EXISTING_PUBLIC_DEBUG_PORTS',image=IMAGE,compiler_argv=argv,input_sha256=pins,input_bytes=sum(x['bytes'] for x in inputs.values()),caps=dict(aggregate_memory_GiB=4,AS_GiB=4,CPU=2,wall_seconds=60,log_MiB=2,owned_container_stop_seconds=5,output_GiB=2,disk_live_reserve_GiB=16,live_RAM_reserve_GiB=24),future_container_argv=['docker','run','--rm','--init','--name','FRESH_OWNED_RELINK_NAME','--network','none','--read-only','--cpus','2','--cpuset-cpus','TWO_ADMITTED_HOST_CPUS','--memory','4g','--memory-swap','4g','--ulimit',f'as={4<<30}:{4<<30}','--ulimit',f'fsize={2<<30}:{2<<30}','--pids-limit','64','--tmpfs','/tmp:rw,size=256m','--user','HOST_UID:HOST_GID','--volume','VERIFIED_INPUT_BUNDLE:/inputs:ro','--volume','FRESH_OUTPUT:/output:rw',IMAGE]+argv,runtime_allowed=False,full_frontend_runs=0,owner_cancellation_selected=False,qualified_provider_counts_available=False,execution_allowed=False,supervisor_PID=None,output_handle=None,prerequisites=['fresh independent GO binds planSHA,input manifest,image and native-relink-only scope','verified transport of only enrolled inputs into fresh isolated source-bound bundle','fresh host measured admission and job/thread coordination','bounded supervisor stops named container on first failure/cap without retry','actual execution receipt binds compiler/tool,image,source and input hashes; outputbinary SHA after relink only'])

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    with (root/EVIDENCE/'bounded_relink_plan.json').open('x') as f:f.write(json.dumps(build(root),indent=2)+'\n')
