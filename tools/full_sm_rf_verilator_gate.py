#!/usr/bin/env python3
"""Prepare, or execute ONLY under a fresh parent GO, unchanged full128 RTL.
Preparation queries tool versions/hashes; it never elaborates or compiles RTL.
"""
import argparse
import hashlib
import json
import math
import os
import re
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='2e75bab2efa022f60d98bd8511a3027da56951ce'
VERILATOR=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
VROOT=VERILATOR.parent.parent/'share/verilator'
SOURCES=(
 'rtl/gpu/ot_gpu_full_sm_service.sv','rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_scratch_service.sv',
 'rtl/gpu/ot_gpu_fadd.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv',
 'rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_prefix.sv',
 'rtl/test/full_sm_service/sram_models.sv','rtl/test/full_sm_service/tb_full_service_exact.sv')
STORAGE_SOURCES=(SOURCES[1],SOURCES[2],SOURCES[8],'rtl/test/full_sm_service/tb_storage.sv')
CAPS=dict(cpus=[28,29],memory_bytes=8*1024**3,swap_bytes=0,whole_wall_s=1020,
 verilate_s=300,cxx_build_s=480,actual_sim_s=60,storage_compile_s=30,storage_sim_s=30,
 build_jobs=2,simulation_threads=1,per_file_bytes=1024**3,
 sampled_total_output_bytes=1024**3,output_poll_s=1,kill_grace_s=5,disk_headroom_bytes=2*1024**3)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def query(cmd):return subprocess.check_output(cmd,text=True,stderr=subprocess.STDOUT,timeout=10).strip()
def json_bytes(obj):return (json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)

def commands(run_dir):
    obj=str(Path(run_dir)/'obj')
    return [
      ('verilate',CAPS['verilate_s'],[str(VERILATOR),'--cc','--exe','--main','--timing',
        '--top-module','tb_full_service_exact','--prefix','Vtb_full_service_exact',
        '--Mdir',obj,'--compiler','gcc','--threads','1','-O0','-Wno-fatal',
        '--output-split','20000','--output-split-cfuncs','2000','-CFLAGS','-O0',
        *[str(ROOT/p) for p in SOURCES]]),
      ('cxx_build',CAPS['cxx_build_s'],['/usr/bin/make','-C',obj,'-f','Vtb_full_service_exact.mk',
        '-j2','CXX=/usr/bin/g++','LINK=/usr/bin/g++','OPT_FAST=-O0','OPT_SLOW=-O0',
        'OPT_GLOBAL=-O0']),
      ('actual_sim',CAPS['actual_sim_s'],[obj+'/Vtb_full_service_exact']),
      ('storage_compile',CAPS['storage_compile_s'],['/usr/bin/iverilog','-g2012','-s','tb_storage',
        '-o',str(Path(run_dir)/'storage.vvp'),*[str(ROOT/p) for p in STORAGE_SOURCES]]),
      ('storage_sim',CAPS['storage_sim_s'],['/usr/bin/vvp',str(Path(run_dir)/'storage.vvp')])]

def prepare():
    version=query([str(VERILATOR),'--version'])
    if not version.startswith('Verilator 5.050 '):raise ValueError('requires pinned Verilator5.050')
    pins={p:sha(ROOT/p) for p in dict.fromkeys(SOURCES+STORAGE_SOURCES)}
    for p,h in pins.items():
        old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        if hashlib.sha256(old).hexdigest()!=h:raise ValueError('actual source changed: '+p)
    models=json.loads((ROOT/'results/uarch/full_sm_rf_service_20261002/model_final.json').read_text())
    paths=[VERILATOR,VERILATOR.parent/'verilator_bin',Path('/usr/bin/g++').resolve(),
           Path(query(['/usr/bin/g++','-print-prog-name=cc1plus'])).resolve(),
           Path('/usr/bin/make').resolve(),Path('/usr/bin/iverilog').resolve(),Path('/usr/bin/vvp').resolve()]
    paths += sorted(p for p in (VROOT/'include').rglob('*') if p.is_file())
    paths += [VROOT/'bin/verilator_includer']
    paths=[p for p in paths if p.is_file()]
    widths={}
    for p in SOURCES[4:6]:
        widths[p]=[int(w) for w in re.findall(r'ot_hdc_ksadd_k\s*#\(\.W\((\d+)\)\)',(ROOT/p).read_text())]
    sites=128*sum((w+1)*math.ceil(math.log2(w+1)) for ws in widths.values() for w in ws)
    return dict(schema='opentallas.full-sm-service.verilator-proposal.v1',
      status='PREPARED_FOR_FRESH_PARENT_GO_NOT_RUN',default_enabled=False,build_GO=False,
      actual_RTL_baseline_commit=BASE,source_sha256=pins,runner_sha256=sha(__file__),
      model_pin=dict(path='results/uarch/full_sm_rf_service_20261002/model_final.json',
                     sha256=sha(ROOT/'results/uarch/full_sm_rf_service_20261002/model_final.json')),
      unchanged_hardware=dict(lanes=128,add_instances=128,mul_instances=128,RF_macros=128,scratch_macros=2,
        ALAT=7,proposed_done_cycles=12,proposed_issue_interval_cycles=14,
        token_model_changed=False,area_changed=False,FP_rounding_and_reduction_changed=False,
        routing_and_SSFF_qualified=False),
      elaboration_cost=dict(prefix_widths=widths,replicated_prefix_generate_bit_sites=sites,
        basis='128 lanes times sum((W+1)*clog2(W+1)) of literal ksadd_k widths in actual LAT source; only a prefix-site census, not total AST/RAM/time prediction',
        Icarus_compile_timeout_s=180,Icarus_actual_sim_reached=False,
        Icarus_prefix_elaboration_cost_known=True,Verilator_compile_time_measured=False,
        wall_and_memory_caps_are_budget_not_prediction=True),
      toolchain=dict(verilator_version=version,verilator_path=str(VERILATOR),
        gxx_version=query(['/usr/bin/g++','--version']).splitlines()[0],
        make_version=query(['/usr/bin/make','--version']).splitlines()[0],
        iverilog_version=query(['/usr/bin/iverilog','-V']).splitlines()[0],
        python_version=sys.version,files_sha256={str(p):sha(p) for p in paths}),
      caps=CAPS,commands=[dict(phase=n,wall_s=t,argv=a) for n,t,a in commands('/tmp/full-sm-rf-verilator-parent-<fresh-id>')],
      simulation_scope=dict(actual_FP_modules=True,arithmetic_blackboxes=False,behavioral_FP_substitution=False,
        same_directed_bench=True,SIMD_enable=1,assertion_policy='5.050 assertions enabled by default; no --no-assert; original $fatal checks preserved',SRAM='unchanged functional macro models; not hard-macro corner timing',
        semantics='Verilator two-state simulation; qualified comparisons occur after initialized RF writes. Does not establish four-state X propagation equivalence.',
        nonfatal_warnings='compiler warnings remain in verilate.log; errors/fatals still abort. No blackbox/unresolved-module option.',
        accepted_PASS='actual native executable exits0 and exact original bench PASS marker, plus exhaustive storage PASS'),
      output_caps_scope='FSIZE hard1GiB/file; aggregate1GiB is sampled each1s and fails with process-group termination when exceeded; transient overshoot possible, not a filesystem quota. Reserve2GiB disk headroom.',
      external_parent_requirements=['fresh committed GO binds proposal hash and exact clean run source commit',
        'GO file must byte-match gitshow(--go-commit:admission_record_path), fresh admission required',
        'fresh local CPU28/29,RAM8GiB,swap0,RuntimeMaxSec1020,FSIZE1GiB,OOMPolicy stop cgroup admission',
        'read-only existing failure, fresh run output path outside worktree, separate external monitor',
        'no auto retry, PVE2/3 or remote launch; no compile during preparation'],
      prior_failure=dict(path='/tmp/full-sm-rf-parent-exact-2e75bab2e-r1',verdict='FAIL exit=124',preserved_by_parent=True),
      proposal_qualification='compile-backend alternative only; actual arithmetic, complete token and physical acceptance remain pending')

def validate_go(go,proposal,proposal_path,commit):
    if go.get('schema')!='opentallas.full-sm-service.verilator-GO.v1' or go.get('admitted') is not True:
        raise ValueError('fresh parent GO required')
    if go.get('proposal_sha256')!=sha(proposal_path) or go.get('source_commit')!=commit:
        raise ValueError('GO proposal/source pin mismatch')
    if go.get('caps')!=proposal['caps'] or not go.get('unit'):
        raise ValueError('GO must bind exact caps and named local service')

def validate_cgroup(go):
    cg=next((line.split(':',2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::')),None)
    if not cg or go['unit'] not in cg.split('/'):raise ValueError('runner must be in named parent-admitted cgroup')
    base=Path('/sys/fs/cgroup')/cg.lstrip('/')
    mem=(base/'memory.max').read_text().strip();swap=(base/'memory.swap.max').read_text().strip()
    if mem=='max' or int(mem)>CAPS['memory_bytes'] or int(swap)!=0:raise ValueError('cgroup memory/swap caps mismatch')
    if not set(os.sched_getaffinity(0))<=set(CAPS['cpus']):raise ValueError('CPU affinity exceeds reviewed cores')
    info=dict(x.split('=',1) for x in query(['systemctl','--user','show',go['unit'],
      '--property=RuntimeMaxUSec,LimitFSIZE,OOMPolicy']).splitlines() if '=' in x)
    # systemctl human time output varies; request machine-readable property via
    # systemd's show value is still human-formatted here, so accept exact reviewed1020s forms.
    if info.get('RuntimeMaxUSec') not in ('17min','17min 0s','1020s'):
        raise ValueError('whole runtime cap must be reviewed1020seconds')
    if int(info.get('LimitFSIZE','0'))!=CAPS['per_file_bytes'] or info.get('OOMPolicy')!='stop':
        raise ValueError('FSIZE/OOM policy mismatch')
    return dict(cgroup=cg,memory_max=mem,memory_swap_max=swap,affinity=sorted(os.sched_getaffinity(0)),systemd=info)

def directory_bytes(path):return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())
def terminate_group(proc):
    try:os.killpg(proc.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:proc.wait(timeout=CAPS['kill_grace_s'])
    except subprocess.TimeoutExpired:
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        proc.wait()

def execute(proposal_path,go_path,out,go_commit=None):
    if not go_path or not go_commit:raise ValueError('fresh committed parent GO and --go-commit required; no automatic retry')
    proposal=json.loads(proposal_path.read_text());go=json.loads(go_path.read_text())
    commit=git('rev-parse','HEAD');validate_go(go,proposal,proposal_path,commit)
    record=go.get('admission_record_path','')
    if not record.startswith('results/') or not record.endswith('.json') or '..' in Path(record).parts:
        raise ValueError('GO must name its committed admission record path')
    admitted_commit=git('rev-parse',go_commit+'^{commit}')
    committed_go=subprocess.check_output(['git','show',admitted_commit+':'+record],cwd=ROOT)
    if committed_go!=go_path.read_bytes():raise ValueError('GO differs from committed parent admission')
    if git('status','--porcelain','--untracked-files=normal'):raise ValueError('requires clean pinned worktree')
    if proposal!=prepare():raise ValueError('source/tool/model/caps drift from reviewed proposal')
    if not out.is_absolute() or out.exists() or out.is_relative_to(ROOT):raise ValueError('fresh external absolute output directory required')
    # Avoid compiler selection overrides, including MAKEFLAGS jobserver injection.
    for key in ('VERILATOR_ROOT','VERILATOR_BIN','VERILATOR_FLAGS','MAKEFLAGS','CXX','CC','CFLAGS','CXXFLAGS','LDFLAGS','OPT_FAST','OPT_SLOW','OPT_GLOBAL'):
        value=os.environ.get(key)
        if value and not (key=='VERILATOR_ROOT' and value==str(VROOT)):raise ValueError('unreviewed tool environment: '+key)
    cgroup=validate_cgroup(go)
    disk=os.statvfs(out.parent)
    if disk.f_bavail*disk.f_frsize<CAPS['disk_headroom_bytes']:raise ValueError('insufficient reserved output headroom')
    out.mkdir()
    resource.setrlimit(resource.RLIMIT_FSIZE,(CAPS['per_file_bytes'],CAPS['per_file_bytes']))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    receipt=dict(schema='opentallas.full-sm-service.verilator-run.v1',source_commit=commit,
      proposal_sha256=sha(proposal_path),GO_sha256=sha(go_path),GO_commit=admitted_commit,admission=cgroup,source_sha256=proposal['source_sha256'],
      phases=[],verdict='FAIL_INCOMPLETE',arithmetic_exact_PASS=False,build_GO=False,physical_adoption=False)
    write_new(out/'proposal.json',proposal_path.read_bytes());write_new(out/'GO.json',go_path.read_bytes())
    started=time.monotonic()
    try:
        for name,limit,cmd in commands(out):
            phase=dict(name=name,argv=cmd,wall_limit_s=limit);t=time.monotonic()
            with (out/(name+'.log')).open('xb') as log:
                proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                reason=None
                while proc.poll() is None:
                    if time.monotonic()-t>limit:reason='PHASE_TIMEOUT'
                    elif time.monotonic()-started>CAPS['whole_wall_s']-30:reason='WHOLE_TIMEOUT'
                    elif directory_bytes(out)>CAPS['sampled_total_output_bytes']:reason='OUTPUT_CAP'
                    if reason:terminate_group(proc);break
                    time.sleep(CAPS['output_poll_s'])
                phase.update(exit_code=proc.returncode,wall_s=time.monotonic()-t,termination_reason=reason)
            receipt['phases'].append(phase)
            if reason or proc.returncode:raise RuntimeError(name+' failed: '+str(reason or proc.returncode))
            if directory_bytes(out)>CAPS['sampled_total_output_bytes']:raise RuntimeError('OUTPUT_CAP after '+name)
            if name=='actual_sim':
                if 'PASS full128 SIMD directed RNE/sign/subnormal/refusal;12cycle done;mirrors;leases' not in (out/(name+'.log')).read_text():
                    raise RuntimeError('missing actual full128 exact marker')
                receipt['arithmetic_exact_PASS']=True
            if name=='storage_sim' and 'PASS storage:' not in (out/(name+'.log')).read_text():raise RuntimeError('missing storage exact marker')
        receipt['verdict']='PASS_DIRECTED_FULL128_AND_STORAGE_ONLY'
    except Exception as exc:
        receipt['failure']=str(exc)
    finally:
        receipt['wall_s']=time.monotonic()-started;receipt['output_bytes']=directory_bytes(out)
        binary=out/'obj/Vtb_full_service_exact'
        if binary.exists():receipt['actual_binary_sha256']=sha(binary)
        receipt['logs_sha256']={p.name:sha(p) for p in out.glob('*.log')}
        write_new(out/'verdict.json',json_bytes(receipt))
    if receipt['verdict']!='PASS_DIRECTED_FULL128_AND_STORAGE_ONLY':raise RuntimeError(receipt.get('failure','incomplete'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--run',action='store_true')
    p.add_argument('--proposal',type=Path);p.add_argument('--go',type=Path);p.add_argument('--go-commit');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.prepare==a.run:p.error('select exactly one of --prepare or --run')
    try:
        if a.prepare:write_new(a.out,json_bytes(prepare()));print('PREPARED; no RTL compile or simulation launched')
        elif not a.proposal:p.error('--run requires reviewed --proposal')
        else:execute(a.proposal,a.go,a.out,a.go_commit)
    except Exception as exc:raise SystemExit(str(exc))
if __name__=='__main__':main()
