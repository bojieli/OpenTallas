#!/usr/bin/env python3
"""Build real completed Verilator JSON models; no RTL frontend or simulation.

Output objects stay separate from immutable generated models. The caller brings
an actual successful current-source parent terminal and an optional source-owned
C++ harness; no surrogate stimulus is emitted here.
"""
import argparse, concurrent.futures, fcntl, hashlib, json, os, re, shutil, socket, subprocess, sys, time
from pathlib import Path

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    p.write_text(json.dumps(x,indent=2)+'\n')
def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()

def harness_dependencies(source):
    pins={};pending=[source]
    while pending:
        p=pending.pop().resolve()
        if str(p) in pins:continue
        pins[str(p)]=sha(p)
        for name in re.findall(r'^\s*#include\s+"([^"]+)"',p.read_text(),re.M):
            path=p.parent/name
            if not path.is_file() and re.fullmatch(r'V\w+\.h',name):continue
            pending.append(path)
    return pins

def model_inputs(graph):
    jobs=json.loads(graph.read_text())['submodules'];models=[]
    for job in jobs:
        directory=Path(job['directory']);p=directory/(job['prefix']+'.json')
        m=json.loads(p.read_text())
        if m['version']!=1:raise ValueError('Unsupported generated JSON version')
        options=m['options']
        if any(options.get(k) for k in ('system_c','coverage','trace','trace_fst','trace_saif','trace_vcd')):
            raise ValueError('Unsupported instrumented/SystemC model; use its actual build flow')
        sources=m['sources'];known={'global','classes_fast','classes_slow','support_fast','support_slow','deps'}
        if set(sources)-known:raise ValueError('Unknown generated source category')
        root=Path(m['system']['verilator_root']);include=root/'include'
        runtime=[Path(s) for s in sources['global'] if Path(s).parent==include]
        local=[directory/Path(s).name for kind,paths in sources.items() if kind!='deps' for s in paths if Path(s) not in runtime]
        # Exact retained JSON still names its original directory; generated
        # files are copied byte-for-byte and resolve by their emitted basenames.
        if any(p.parent.resolve()!=directory.resolve() for p in local):
            raise ValueError('Model JSON references another generation directory')
        files={str(p):sha(p) for p in sorted(set(local)|set(directory.glob('*.h'))|set(directory.glob('*.sv')))}
        tool_headers={str(p):sha(p) for p in include.rglob('*') if p.is_file()}
        models.append(dict(job=job,json=str(p),json_sha256=sha(p),sources=list(map(str,local)),
                           runtime=list(map(str,runtime)),include=str(include),options=options,
                           pins=files,tool_pins=tool_headers))
    return models

def flags(model):
    o=model['options']
    return ['-std=c++20','-O1','-fPIC','-pthread','-faligned-new',
            '-DVM_COVERAGE=0','-DVM_SC=0','-DVM_TRACE=0','-DVM_TRACE_FST=0',
            '-DVM_TRACE_VCD=0','-DVM_TRACE_SAIF=0','-DVM_VPI=0',
            '-DVM_TIMING='+str(int(o['use_timing'])),
            '-I'+model['include'],'-I'+str(Path(model['json']).parent),
            '-I'+str(Path(model['include'])/'vltstd'),*model['job'].get('cflags',[])]

def build_one(compiler,source,output,opts,envelope):
    """Retain a finished object only with exact input/tool/flags/header match."""
    record=output.with_suffix('.receipt.json');dep=output.with_suffix('.d')
    contract=dict(source=sha(source),compiler=sha(compiler),flags=opts,envelope=envelope)
    if record.exists():
        old=json.loads(record.read_text())
        if old['contract']!=contract or not output.exists() or sha(output)!=old['object_sha256']:
            raise ValueError('Existing object differs; preserve it and choose a new build output')
        return output
    command=[str(compiler),*opts,'-MMD','-MF',str(dep),'-c',str(source),'-o',str(output)]
    with output.with_suffix('.log').open('w') as log:
        rc=subprocess.call(['/usr/bin/time','-v','-o',str(output.with_suffix('.resources')),*command],stdout=log,stderr=subprocess.STDOUT)
    if rc:raise RuntimeError('Compiler exit '+str(rc)+'; '+str(output.with_suffix('.log')))
    write(record,dict(contract=contract,object_sha256=sha(output),command=command))
    return output

def build(models,out,compiler,archiver,workers,harness=None):
    libraries=[];all_runtime=set();timing=False
    envelope=digest([{k:v for k,v in m.items() if k!='job'} for m in models])
    for m in models:
        prefix=m['job']['prefix'];d=out/prefix;d.mkdir(exist_ok=True)
        opts=flags(m);sources=[Path(s) for s in m['sources']]
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(build_one,compiler,s,d/(s.stem+'.o'),opts,envelope) for s in sources]
            objects=[f.result() for f in futures]
        library=d/(prefix+'.a')
        subprocess.run([str(archiver),'rcs',str(library),*map(str,objects)],check=True)
        libraries.append(library);all_runtime.update(m['runtime']);timing|=m['options']['use_timing']
        write(out/'progress.json',dict(completed_libraries=list(map(str,libraries)),current=prefix))
    if not harness:return dict(libraries={str(p):sha(p) for p in libraries},linked=False)
    # A single runtime compiled with the superset of the real hierarchy options.
    runtime=out/'runtime';runtime.mkdir(exist_ok=True)
    opts=flags(models[-1]);opts=[s for s in opts if not s.startswith('-DVM_TIMING=')]+['-DVM_TIMING='+str(int(timing))]
    all_runtime.add(str(Path(models[-1]['include'])/'verilated_dpi.cpp'))
    if timing:all_runtime.add(str(Path(models[-1]['include'])/'verilated_timing.cpp'))
    objects=[build_one(compiler,Path(s),runtime/(Path(s).stem+'.o'),opts,envelope) for s in sorted(all_runtime)]
    harness_object=build_one(compiler,harness,runtime/'harness.o',opts,digest([envelope,harness_dependencies(harness)]))
    binary=out/'integrated_bench'
    subprocess.run([str(compiler),'-pthread',str(harness_object),'-Wl,--start-group',*map(str,libraries),
                    *map(str,objects),'-Wl,--end-group','-latomic','-o',str(binary)],check=True)
    return dict(libraries={str(p):sha(p) for p in libraries},linked=True,binary=str(binary),binary_sha256=sha(binary),runtime_executed=False)

def capacity(out,a):
    def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    x=cpu();time.sleep(1);y=cpu();delta=[b-a for a,b in zip(x,y)]
    mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
    row=dict(host=socket.gethostname(),load=os.getloadavg()[0],idle=os.cpu_count()*delta[3]/sum(delta),
             available_bytes=mem,disk_free=shutil.disk_usage(out).free)
    write(out/('post_guard.json' if a.admitted else 'pre_guard.json'),row)
    return row['load']<128 and row['idle']>=a.workers and mem>=a.memory_gib*2**30 and row['disk_free']>=a.disk_reserve_bytes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('graph','terminal','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--harness',type=Path);p.add_argument('--workers',type=int,required=True)
    p.add_argument('--memory-gib',type=int,required=True);p.add_argument('--disk-reserve-bytes',type=int,required=True)
    p.add_argument('--host',required=True);p.add_argument('--compiler',type=Path,default=Path(shutil.which('g++') or '/missing'))
    p.add_argument('--archiver',type=Path,default=Path(shutil.which('ar') or '/missing'))
    p.add_argument('--admitted',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
    if min(a.workers,a.memory_gib,a.disk_reserve_bytes)<=0:raise ValueError('Measured inventory reservation required')
    out=a.output.resolve();guard=Path('/srv/opentallas-scratch/admit.sh')
    if socket.gethostname()!=a.host or not guard.is_file() or not str(out).startswith('/srv/opentallas-scratch'):
        raise ValueError('Measured E1/E2 NVMe host and unchanged guard required')
    terminal=json.loads(a.terminal.read_text())
    if terminal['exit'] or not terminal['full_parent_elaborated']:
        raise ValueError('Wait for actual successful current-source parent generation')
    work=a.graph.resolve().parent.parent
    prepared=json.loads((work/'prepared.json').read_text())
    if terminal['source_sha256']!=prepared['source_sha256'] or terminal['parameters']!=prepared['parameters']:
        raise ValueError('Parent terminal differs from actual selected snapshot')
    for rel,h in prepared['source_sha256'].items():
        if sha(work/'src'/rel)!=h:raise ValueError('Current parent source changed '+rel)
    models=model_inputs(a.graph);inputs=dict(graph=sha(a.graph),terminal=sha(a.terminal),
        models=models,compiler=sha(a.compiler),archiver=sha(a.archiver),driver=sha(__file__),
        harness=sha(a.harness) if a.harness else None,workers=a.workers)
    if a.harness:inputs['harness_dependencies']=harness_dependencies(a.harness)
    if set(terminal['completed'])!={m['job']['prefix'] for m in models}:
        raise ValueError('Terminal does not cover this actual generated hierarchy')
    if not a.admitted:out.mkdir(parents=True,exist_ok=True)
    with (out/'build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'terminal.json').exists():raise ValueError('Terminal build exists; no repeat')
        pin=out/'inputs.json'
        if pin.exists() and json.loads(pin.read_text())!=inputs:raise ValueError('Build inputs changed; preserve output')
        if not pin.exists():write(pin,inputs)
        if not capacity(out,a):return 75
        if not a.admitted:
            # Release only this own lock before unchanged guard invokes the sole consumer.
            cmd=[str(guard),str(a.memory_gib),'--',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--admitted']
            with (out/'admission.claim').open('x') as claim:
                claim.write(str(os.getpid())+'\n')
            write(out/'guard_command.json',cmd);fcntl.flock(lock,fcntl.LOCK_UN)
            return subprocess.call(cmd)
        try:result=build(models,out,a.compiler,a.archiver,a.workers,a.harness)
        except Exception as e:
            write(out/'failure.json',dict(error=str(e),completed_objects_preserved=True));raise
        write(out/'terminal.json',dict(exit=0,**result,numerical=False,physical_qualified=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
