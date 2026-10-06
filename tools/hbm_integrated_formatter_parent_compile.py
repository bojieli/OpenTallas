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
# Literal selected Gibbs parameters; standalone snapshot runner has no imports
# from another worktree. Original ALAT5 executor is not rewritten as c12ALAT6.
PARAMS=dict(ENABLE=1,COMBINED_ENABLE=1,W2_RESULT_ENABLE=1,W2_SECTOR_ENABLE=1,
    SU_ENABLE=1,SU_PROVIDER_ADAPTER=1,SU_REGISTERED_OUTPUTS=1,SU_REGISTERED_STATUS=1,
    SU_REGISTERED_BOUNDARY=1,SU_BALANCED_OWNER_BOUNDARY=1,SU_FOUR_COMBINATIONAL_CUTS=1,
    SU_FAST_OWNER_FRONTIER=1,ND=2,NSM=2,NS=2,NPC=2,MEM_WORDS=2097152,VM_AW=21,
    FORMATTER_ENABLE=1,NORMAL_GATHER_ENABLE=1,LOCAL_CP_RESET_ENABLE=1,TW=17,PW=20,IMW=14)
INCLUDES=['rtl/test/tb_hdc_v41x_vec_fields.svh']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files():
    lines=(ROOT/LIST).read_text().splitlines()
    paths=[s.strip() for s in lines if s.strip() and not s.lstrip().startswith(('//','+incdir+'))]
    if len(paths)!=len(set(paths)):raise ValueError('Duplicate source entries')
    for s in paths:
        if Path(s).is_absolute() or '..' in Path(s).parts:raise ValueError('Source paths must be root-relative')
    for s in [BODY,PARENT,'rtl/hbm_accel/index/ot_hbm_accel_index_w15_planemajor_formatter.sv',
              'rtl/chip/ot_w15_coll_dma.sv','rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w15_store.sv']:
        if s not in paths:raise ValueError('Missing actual selected source '+s)
    return paths

def prepare(work,body_pin):
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
    if BODY in pins:
        text=(ROOT/BODY).read_text()
        header=text[text.index(')(\n')+3:text.index('\n);')]
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
    for s in all_files:
        if s in missing:continue
        dst=work/'src'/s;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/s,dst)
    shutil.copyfile(ROOT/LIST,work/'src/files.f')
    runner=work/'runner.py';shutil.copyfile(Path(__file__),runner)
    m=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256=pins,files_f_sha256=sha(ROOT/LIST),runner_sha256=sha(runner),
        binding_sha256=sha(ROOT/'tools/hbm_opt_integrated_20261005_w2_on.py'),
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
        raise ValueError('Heavy full-parent compile only on E2 NVMe through unchanged guard')
    if socket.gethostname()!=a.epyc2_hostname:raise ValueError('Execution host differs from measured E2 identity')
    if not a.tool.is_file():raise FileNotFoundError('Actual Verilator tool missing')
    if (work/'frontend.exit').exists() or (work/'elaboration.log').exists():
        raise FileExistsError('Preserve prior compile; no duplicate/restart')
    receipt=work/('post_guard.json' if a.admitted else 'pre_guard.json')
    if receipt.exists() or (not a.admitted and (work/'guard_command.json').exists()):
        raise FileExistsError('Existing admission/attempt preserved; no duplicate queued consumer')
    snap=capacity(work);write(receipt,snap)
    if not fits(snap,a):print('CAPACITY_REFUSAL no compiler: '+json.dumps(snap));return 75
    if not a.admitted:
        cmd=[str(guard),str(a.memory_gib),'--',sys.executable,str(work/'runner.py'),'--run',
            '--work',str(work),'--tool',str(a.tool.resolve()),'--memory-gib',str(a.memory_gib),
            '--cpu-cores',str(a.cpu_cores),'--disk-reserve-bytes',str(a.disk_reserve_bytes),
            '--epyc2-hostname',a.epyc2_hostname,'--admitted']
        write(work/'guard_command.json',cmd)
        return subprocess.run(cmd).returncode
    tmp=work/'tmp';tmp.mkdir();obj=work/'obj'
    cmd=[str(a.tool.resolve()),'--lint-only','--timing','-Wno-fatal',
         '--top-module','ot_ds_hbm_cluster20_integrated','--Mdir',str(obj),
         *[f'-G{k}={v}' for k,v in m['parameters'].items()],'-f','files.f']
    write(work/'command.json',cmd)
    env=dict(os.environ,TMPDIR=str(tmp))
    with (work/'elaboration.log').open('w') as log:
        rc=subprocess.run(cmd,cwd=work/'src',env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    (work/'frontend.exit').write_text(str(rc)+'\n')
    log=(work/'elaboration.log').read_text()
    dangerous=re.findall(r'%Warning-(LATCH|UNOPTFLAT|SELRANGE|PIN[^:]*|USERERROR):',log)
    write(work/'elaboration.json',dict(frontend_exit=rc,dangerous_diagnostics=dangerous,
        full_parent_elaborated=(rc==0 and not dangerous),parameters=m['parameters'],
        source_sha256=m['source_sha256'],body_owner_sha256=m['body_owner_sha256'],
        numerical=False,physical_qualified=False,adopted=False))
    return rc if rc else (2 if dangerous else 0)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--prepare',action='store_true');g.add_argument('--run',action='store_true')
    p.add_argument('--work',type=Path,required=True);p.add_argument('--body-sha256')
    p.add_argument('--tool',type=Path,default=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
    p.add_argument('--memory-gib',type=int,default=0);p.add_argument('--cpu-cores',type=int,default=0)
    p.add_argument('--disk-reserve-bytes',type=int,default=0);p.add_argument('--epyc2-hostname',default='')
    p.add_argument('--admitted',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    return prepare(a.work.resolve(),a.body_sha256) if a.prepare else run(a)
if __name__=='__main__':raise SystemExit(main())
