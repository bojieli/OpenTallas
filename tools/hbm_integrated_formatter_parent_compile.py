#!/usr/bin/env python3
"""Prepare pinned enabled parent sources, then guarded E2 elaboration only.

Bacon owns formatter RTL; Gibbs owns parent/config. No source emission, numerical
fixture, token simulation, implicit retry, synthesis or physical qualification.
"""
import argparse, hashlib, json, os, re, shutil, socket, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LIST='physical/hbm_die_abstracts_20261006/memory_control/formatter_provider.files.f'
BODY='physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_integrated_formatter_provider.sv'
PARENT='rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv'
SELECTED='results/rtl/hbm_integrated_sfu_provider_join_20261006/selected_parameters.json'
# Literal selected Gibbs parameters; standalone snapshot runner has no imports
# from another worktree. Original ALAT5 executor is not rewritten as c12ALAT6.
PARAMS=dict(ENABLE=1,COMBINED_ENABLE=1,W2_RESULT_ENABLE=1,W2_SECTOR_ENABLE=1,
    SU_ENABLE=1,SU_PROVIDER_ADAPTER=1,SU_REGISTERED_OUTPUTS=1,SU_REGISTERED_STATUS=1,
    SU_REGISTERED_BOUNDARY=1,SU_BALANCED_OWNER_BOUNDARY=1,SU_FOUR_COMBINATIONAL_CUTS=1,
    SU_FAST_OWNER_FRONTIER=1,ND=2,NSM=2,NS=2,NPC=2,MEM_WORDS=2097152,VM_AW=21,
    FORMATTER_ENABLE=1,NORMAL_GATHER_ENABLE=1,LOCAL_CP_RESET_ENABLE=1,TW=17,PW=20,IMW=14,
    SFU_C12_ENABLE=1,SFU_NATIVE_VM_ENABLE=1,NORM_C12_ENABLE=1,
    NORM_KIND=0,NORM_N=64,NORM_D=5120,NORM_RD=0,NORM_AW=24,NORM_PUBLISH_QUANT=1)
INCLUDES=['rtl/test/tb_hdc_v41x_vec_fields.svh',SELECTED]
# Compiler partitions only. Every block is the real selected module body;
# Verilator derives each parameter variant and connects generated leaf wrappers.
# Leave the HBM model inside its partition: init_mem accesses u_model.mem.
HIER_BLOCKS=[
    'ot_hdc_v41x_vec_lane','ot_hdc_v41x_vec','ot_hbm_accel_su_parent_exec',
    'ot_hdc_v41x_exp','ot_hdc_v41x_rsqrt','ot_hdc_v41x_fdiv','ot_hdc_v41x_softplus',
    'ot_dsrom_su_hcpost_lane','ot_dsrom_su_hcpost_group','ot_dsrom_su_hcpost',
    'ot_gpu_simt_fplane','ot_ds_hbm_simt_sm20','ot_gpu_hbm_partition',
    'ot_hbm_selected_c12__ot_hdc_v41x_exp',
    'ot_hbm_selected_c12__ot_hdc_v41x_rsqrt',
    'ot_hbm_selected_c12__ot_hdc_v41x_fdiv',
    'ot_hbm_selected_c12__ot_hdc_v41x_softplus',
    'ot_hbm_selected_c12__ot_hbm_sfu_result_c12',
    'ot_dsrom_su_norm_mix','ot_dsrom_rsqrt','ot_dsrom_su_norm']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files():
    lines=(ROOT/LIST).read_text().splitlines()
    paths=[s.strip() for s in lines if s.strip() and not s.lstrip().startswith(('//','+incdir+'))]
    if len(paths)!=len(set(paths)):raise ValueError('Duplicate source entries')
    for s in paths:
        if Path(s).is_absolute() or '..' in Path(s).parts:raise ValueError('Source paths must be root-relative')
    for s in [BODY,PARENT,'rtl/hbm_accel/index/ot_hbm_accel_index_w15_planemajor_formatter.sv',
              'rtl/chip/ot_w15_coll_dma.sv','rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w15_store.sv',
              'rtl/hbm_accel/integrated_20261006/sfu_c12_selected/14_ot_hdc_fastfp.sv',
              'physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_die_vm_sfu_publication_root.sv']:
        if s not in paths:raise ValueError('Missing actual selected source '+s)
    return paths

def prepare(work,body_pin):
    if json.loads((ROOT/SELECTED).read_text())['parameters']!=PARAMS:
        raise ValueError('Actual Gibbs selected enabled parameters changed; align source runner')
    work.mkdir(parents=True,exist_ok=False)
    paths=files();all_files=paths+INCLUDES
    missing=[s for s in all_files if not (ROOT/s).is_file()]
    pins={s:sha(ROOT/s) for s in all_files if (ROOT/s).is_file()}
    errors=[]
    if BODY in pins:
        if not body_pin:errors.append('Bacon published body SHA required')
        elif pins[BODY]!=body_pin:errors.append('Formatter body differs from owner pin')
    parent=(ROOT/PARENT).read_text()
    if not re.search(r'\.release_token(?:17)?\(gather_release_frame\[d\*73\+36\+:17\]\)',parent):
        errors.append('Actual full TOKEN17 release connection missing')
    if not (('.owner_valid(fmt_lease_valid),.owner_frame(fmt_lease_frame)' in parent) or
            ('.gather_granted(fmt_lease_valid),.gather_frame73(fmt_lease_frame)' in parent)):
        errors.append('Actual retained lease/full73 owner connection missing')
    # Source-only check of the actual named instance against Bacon's real body.
    # Report discrepancies to the respective writers; never synthesize a stub.
    declarations={}
    for path in paths:
        if path in missing:continue
        text=(ROOT/path).read_text()
        for name in re.findall(r'^\s*module\s+(\w+)',text,re.M):
            if name in declarations:errors.append('Duplicate module '+name+': '+declarations[name]+' / '+path)
            declarations[name]=path
    for name in HIER_BLOCKS:
        if name not in declarations:errors.append('Real hierarchy block missing: '+name)
    if BODY in pins:
        text=(ROOT/BODY).read_text()
        header=re.sub(r'//[^\n]*|/\*.*?\*/','',text[text.index(')(\n')+3:text.index('\n);')],flags=re.S)
        declared=set()
        # ANSI declarations can share a direction/type across comma-separated
        # names, or introduce a new direction on that same line.
        for port in header.split(','):
            name=re.search(r'(\w+)\s*$',port)
            if name:declared.add(name.group(1))
        start=parent.index(' u_formatter_provider(')
        instance=parent[start:parent.index(');',start)]
        connected=set(re.findall(r'\.(\w+)\s*\(',instance))
        for name in sorted(connected-declared):errors.append('Parent formatter port absent in Bacon body: '+name)
        for name in sorted(declared-connected):errors.append('Bacon formatter port unconnected by parent: '+name)
    sfu='rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_sfu_provider_join.sv'
    if sfu not in pins:
        errors.append('Actual selected SFUc12 provider join missing')
    elif ' u_sfu_c12(' not in parent or '.ENABLE(SFU_C12_ENABLE)' not in parent or '.NATIVE_VM_PUBLICATION(SFU_NATIVE_VM_ENABLE)' not in parent:
        errors.append('Actual parent SFUc12 instance/enable connection missing')
    else:
        text=(ROOT/sfu).read_text()
        header=re.sub(r'//[^\n]*|/\*.*?\*/','',text[text.index(')(\n')+3:text.index('\n);')],flags=re.S)
        declared={re.search(r'(\w+)\s*$',p).group(1) for p in header.split(',')}
        start=parent.index(' u_sfu_c12(')
        connected=set(re.findall(r'\.(\w+)\s*\(',parent[start:parent.index(');',start)]))
        for name in sorted(connected-declared):errors.append('Parent SFUc12 port absent in Gibbs body: '+name)
        for name in sorted(declared-connected):errors.append('Gibbs SFUc12 port unconnected by parent: '+name)
    native='physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_die_vm_sfu_publication_root.sv'
    if native not in pins or 'if(SFU_NATIVE_VM_ENABLE)begin:g_sfu_native_vm' not in parent:
        errors.append('Actual selected native VM instance missing')
    else:
        text=(ROOT/native).read_text()
        header=re.sub(r'//[^\n]*|/\*.*?\*/','',text[text.index(')(\n')+3:text.index('\n);')],flags=re.S)
        declared={re.search(r'(\w+)\s*$',p).group(1) for p in header.split(',')}
        start=parent.index(' u_vm(')
        connected=set(re.findall(r'\.(\w+)\s*\(',parent[start:parent.index(');',start)]))
        for name in sorted(connected-declared):errors.append('Parent native VM port absent in Bacon body: '+name)
        for name in sorted(declared-connected):errors.append('Bacon native VM port unconnected by parent: '+name)
    for s in all_files:
        if s in missing:continue
        dst=work/'src'/s;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/s,dst)
    shutil.copyfile(ROOT/LIST,work/'src/files.f')
    hier=work/'src/hierarchy.vlt'
    hier.write_text('`verilator_config\n'+''.join(f'hier_block -module "{name}"\n' for name in HIER_BLOCKS))
    runner=work/'runner.py';shutil.copyfile(Path(__file__),runner)
    m=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256=pins,files_f_sha256=sha(ROOT/LIST),runner_sha256=sha(runner),
        binding_sha256=sha(ROOT/'tools/hbm_opt_integrated_20261005_w2_on.py'),
        hierarchy_sha256=sha(hier),hierarchy_blocks={name:declarations.get(name) for name in HIER_BLOCKS},
        compiler_mode='real hierarchical --cc, sequential Verilation, no C++ build/runtime',
        sources=paths,includes=INCLUDES,parameters=PARAMS,body_owner_sha256=body_pin,
        missing=missing,errors=errors,source_ready=not missing and not errors,
        prepared_bytes=sum((ROOT/s).stat().st_size for s in all_files if s not in missing),
        full_parent_elaborated=False,numerical=False,physical_qualified=False,
        source_body_owner='Bacon',parent_config_owner='Gibbs')
    write(work/'prepared.json',m)
    print(json.dumps({k:m[k] for k in ['source_ready','missing','errors','prepared_bytes','parameters']},indent=2))
    return 0 if m['source_ready'] else 2

def verified(work):
    m=json.loads((work/'prepared.json').read_text())
    if not m['source_ready']:raise ValueError('Actual owner-pinned body/source closure not ready; no guard/compiler')
    if m['parameters']!=PARAMS:raise ValueError('Selected enabled parameters changed')
    if sha(work/'src/files.f')!=m['files_f_sha256']:raise ValueError('Source list changed')
    if sha(work/'runner.py')!=m['runner_sha256']:raise ValueError('Runner changed')
    if sha(work/'src/hierarchy.vlt')!=m['hierarchy_sha256']:raise ValueError('Compiler hierarchy changed')
    for s,h in m['source_sha256'].items():
        if sha(work/'src'/s)!=h:raise ValueError('Pinned source changed '+s)
    if m['source_sha256'][BODY]!=m['body_owner_sha256']:raise ValueError('Owner body pin changed')
    return m

def capacity(work):
    def cpu():return [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    a=cpu();time.sleep(1);b=cpu();d=[y-x for x,y in zip(a,b)]
    mem=next(int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),host=socket.gethostname(),
        load=list(os.getloadavg()),idle_cores=os.cpu_count()*d[3]/sum(d),
        available_bytes=mem,disk_free=shutil.disk_usage(work).free)
def fits(m,a):
    return m['load'][0]<128 and m['idle_cores']>=a.cpu_cores and m['available_bytes']>=a.memory_gib*2**30 and m['disk_free']>=a.disk_reserve_bytes

def run(a):
    work=a.work.resolve();m=verified(work)
    # Explicit resource request must reflect the current compiler inventory;
    # these are admission reservations, never AS/CPU/file/wall-time limits.
    if min(a.memory_gib,a.cpu_cores,a.disk_reserve_bytes)<=0:raise ValueError('Actual CPU/RAM/disk reservation required')
    guard=Path('/srv/opentallas-scratch/admit.sh')
    if not guard.is_file() or not str(work).startswith('/srv/opentallas-scratch2/'):
        raise ValueError('Full-parent compile only on E2 NVMe through unchanged guard')
    if socket.gethostname()!=a.epyc2_hostname:raise ValueError('Execution host differs from measured E2 identity')
    if not a.tool.is_file():raise FileNotFoundError('Actual Verilator tool missing')
    stem='hierarchy_plan' if a.plan else 'elaboration'
    if (work/'frontend.exit').exists() or (work/(stem+'.log')).exists():
        raise FileExistsError('Preserve prior compile; no duplicate/restart')
    receipt=work/('post_guard.json' if a.admitted else 'pre_guard.json')
    if receipt.exists() or (not a.admitted and (work/'guard_command.json').exists()):
        raise FileExistsError('Existing admission/attempt preserved; no duplicate queued consumer')
    if not a.admitted:
        with (work/'supervisor.json').open('x') as claim:
            json.dump(dict(pid=os.getpid(),host=socket.gethostname(),memory_gib=a.memory_gib,
                           cpu_cores=a.cpu_cores,disk_reserve_bytes=a.disk_reserve_bytes),claim)
    snap=capacity(work)
    # The sole queued supervisor is light; do not enter the unchanged memory
    # admission guard or launch the compiler while fresh CPU/disk/RAM fails.
    if a.wait_for_capacity and not a.admitted:
        with (work/'capacity_wait.jsonl').open('x') as log:
            while not fits(snap,a):
                log.write(json.dumps(snap)+'\n');log.flush()
                time.sleep(30);snap=capacity(work)
    write(receipt,snap)
    if not fits(snap,a):print('CAPACITY_REFUSAL no compiler: '+json.dumps(snap));return 75
    if not a.admitted:
        cmd=[str(guard),str(a.memory_gib),'--',sys.executable,str(work/'runner.py'),'--plan' if a.plan else '--run',
            '--work',str(work),'--tool',str(a.tool.resolve()),'--memory-gib',str(a.memory_gib),
            '--cpu-cores',str(a.cpu_cores),'--disk-reserve-bytes',str(a.disk_reserve_bytes),
            '--epyc2-hostname',a.epyc2_hostname,'--admitted']
        write(work/'guard_command.json',cmd)
        return subprocess.run(cmd).returncode
    tmp=work/'tmp';tmp.mkdir();obj=work/'obj'
    # --lint-only bypasses hierarchy planning in Verilator5.050. --cc creates
    # and compiles all real leaf models into C++ source; no binary is built/run.
    # One frontend at a time bounds concurrency without process memory caps.
    cmd=[str(a.tool.resolve()),'--cc','--hierarchical','--timing','-Wno-fatal',
         '-Werror-LATCH','--build-jobs','1','--verilate-jobs','1','--hierarchical-threads','1',
         '--top-module','ot_ds_hbm_cluster20_integrated','--Mdir',str(obj),
         *[f'-G{k}={v}' for k,v in m['parameters'].items()],'hierarchy.vlt','-f','files.f']
    if a.plan:
        # --make json writes the real derived block/parameter/dependency graph
        # without invoking child frontends. It is inventory, never proof PASS.
        cmd+=['--make','json']
    write(work/'command.json',cmd)
    env=dict(os.environ,TMPDIR=str(tmp))
    with (work/(stem+'.log')).open('x') as log:
        rc=subprocess.run(['/usr/bin/time','-v','-o',str(work/'resources.log'),*cmd],
                          cwd=work/'src',env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    (work/('plan.exit' if a.plan else 'frontend.exit')).write_text(str(rc)+'\n')
    log=(work/(stem+'.log')).read_text()
    if a.plan:
        write(work/'hierarchy_plan.json',dict(frontend_exit=rc,generated_files=[str(p.relative_to(work)) for p in obj.rglob('*') if p.is_file()],
              parameters=m['parameters'],source_sha256=m['source_sha256'],full_parent_elaborated=False))
        return rc
    dangerous=re.findall(r'%Warning-(LATCH|UNOPTFLAT|SELRANGE|PIN[^:]*|USERERROR):',log)
    leaves=list(obj.glob('*__hierMkArgs.f'))
    hierarchy_complete=bool(leaves) and (obj/'Vot_ds_hbm_cluster20_integrated.h').is_file()
    write(work/'elaboration.json',dict(frontend_exit=rc,dangerous_diagnostics=dangerous,
        hierarchy_models=[p.name for p in leaves],hierarchy_complete=hierarchy_complete,
        full_parent_elaborated=(rc==0 and not dangerous and hierarchy_complete),parameters=m['parameters'],
        source_sha256=m['source_sha256'],body_owner_sha256=m['body_owner_sha256'],
        numerical=False,physical_qualified=False,adopted=False))
    return rc if rc else (2 if dangerous or not hierarchy_complete else 0)

def compile_plan(a):
    """Consume the completed real parameter graph; never flatten/replan it."""
    work=a.work.resolve();m=verified(work)
    out=a.output.resolve()
    graph=work/'obj/Vot_ds_hbm_cluster20_integrated.json'
    jobs=json.loads(graph.read_text())['submodules']
    guard=Path('/srv/opentallas-scratch/admit.sh')
    if socket.gethostname()!=a.epyc2_hostname or not guard.is_file():
        raise ValueError('Measured E2 identity/unchanged guard required')
    if not all(str(p).startswith('/srv/opentallas-scratch2/') for p in (work,out)):
        raise ValueError('Only own E2 NVMe snapshots')
    if min(a.memory_gib,a.cpu_cores,a.disk_reserve_bytes)<=0:
        raise ValueError('Inventory-based admission reservation required')
    if (work/'plan.exit').read_text().strip()!='0':raise ValueError('Real plan failed')
    if not a.admitted:
        out.mkdir(parents=True,exist_ok=False)
        pins={str(graph):sha(graph)}
        for j in jobs:pins[j['verilator_args']]=sha(j['verilator_args'])
        write(out/'inputs.json',dict(plan_sha256=pins,source_sha256=m['source_sha256'],
            driver_sha256=sha(__file__),parameters=m['parameters'],jobs=len(jobs)))
        write(out/'supervisor.json',dict(pid=os.getpid(),host=socket.gethostname(),
              memory_gib=a.memory_gib,cpu_cores=a.cpu_cores))
    inputs=json.loads((out/'inputs.json').read_text())
    for path,h in inputs['plan_sha256'].items():
        if sha(path)!=h:raise ValueError('Derived graph changed '+path)
    if sha(__file__)!=inputs['driver_sha256']:raise ValueError('Compile driver changed')
    snap=capacity(out)
    write(out/('post_guard.json' if a.admitted else 'pre_guard.json'),snap)
    if not fits(snap,a):return 75
    if not a.admitted:
        cmd=[str(guard),str(a.memory_gib),'--',sys.executable,str(Path(__file__).resolve()),
             '--compile-plan','--work',str(work),'--output',str(out),'--tool',str(a.tool.resolve()),
             '--memory-gib',str(a.memory_gib),'--cpu-cores',str(a.cpu_cores),
             '--disk-reserve-bytes',str(a.disk_reserve_bytes),'--epyc2-hostname',a.epyc2_hostname,'--admitted']
        if a.retained_models:cmd+=['--retained-models',str(a.retained_models.resolve())]
        write(out/'guard_command.json',cmd)
        return subprocess.run(cmd).returncode
    completed=[];remaining=list(jobs);rc=0;diagnostics=[]
    if a.retained_models:
        old=a.retained_models.resolve()
        old_inputs=json.loads((old/'inputs.json').read_text())
        if any(old_inputs[k]!=inputs[k] for k in ('plan_sha256','source_sha256','parameters')):
            raise ValueError('Retained models differ from real source/parameter plan')
        for j in list(remaining):
            terminal=old/j['prefix']/'terminal.json'
            if terminal.is_file():
                t=json.loads(terminal.read_text())
                header=Path(j['directory'])/(j['prefix']+'.h')
                if t['exit']==0 and t['real_model_header'] and header.is_file():
                    completed.append(j['prefix']);remaining.remove(j)
                    diagnostics.extend(t['dangerous_diagnostics'])
                    write(out/(j['prefix']+'.retained.json'),dict(terminal=str(terminal),header_sha256=sha(header)))
    while remaining:
        ready=[j for j in remaining if set(j.get('deps',[]))<=set(completed)
               and all(Path(s).is_file() for s in j['sources'])]
        if not ready:raise ValueError('Real dependency wrappers unavailable; no substitute')
        j=ready[0];remaining.remove(j)
        leaf=out/j['prefix'];leaf.mkdir(exist_ok=False)
        cmd=[str(a.tool.resolve()),'--Mdir',j['directory'],'-f',j['verilator_args'],*j['sources']]
        write(leaf/'command.json',cmd)
        write(out/'progress.json',dict(completed=completed,current=j['prefix'],started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
        with (leaf/'frontend.log').open('x') as log:
            proc=subprocess.Popen(['/usr/bin/time','-v','-o',str(leaf/'resources.log'),*cmd],
                cwd=work/'src',stdout=log,stderr=subprocess.STDOUT)
            write(leaf/'process.json',dict(pid=proc.pid,model=j['prefix']))
            rc=proc.wait()
        text=(leaf/'frontend.log').read_text()
        bad=re.findall(r'%Warning-(LATCH|UNOPTFLAT|SELRANGE|PIN[^:]*|USERERROR):',text)
        generated=Path(j['directory'])/(j['prefix']+'.h')
        write(leaf/'terminal.json',dict(exit=rc,dangerous_diagnostics=bad,real_model_header=generated.is_file()))
        diagnostics.extend(bad)
        if rc or not generated.is_file():
            rc=rc or 2;break
        completed.append(j['prefix'])
    write(out/'terminal.json',dict(exit=rc,completed=completed,total=len(jobs),
          dangerous_diagnostics=diagnostics,full_parent_elaborated=rc==0 and not diagnostics and len(completed)==len(jobs),
          source_sha256=m['source_sha256'],parameters=m['parameters'],numerical=False,physical_qualified=False))
    return rc

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--prepare',action='store_true');g.add_argument('--run',action='store_true');g.add_argument('--plan',action='store_true');g.add_argument('--compile-plan',action='store_true')
    p.add_argument('--retained-models',type=Path);p.add_argument('--output',type=Path);p.add_argument('--work',type=Path,required=True);p.add_argument('--body-sha256')
    p.add_argument('--tool',type=Path,default=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
    p.add_argument('--memory-gib',type=int,default=0);p.add_argument('--cpu-cores',type=int,default=0)
    p.add_argument('--disk-reserve-bytes',type=int,default=0);p.add_argument('--epyc2-hostname',default='')
    p.add_argument('--wait-for-capacity',action='store_true')
    p.add_argument('--admitted',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    return prepare(a.work.resolve(),a.body_sha256) if a.prepare else (compile_plan(a) if a.compile_plan else run(a))
if __name__=='__main__':raise SystemExit(main())
