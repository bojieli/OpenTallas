#!/usr/bin/env python3
"""Prepare a pinned recovery gate or launch only with a committed exact parent GO."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
REVIEWED='69dedf4afd7e2994de57549df8d0c609403d9050'
RECORD=ROOT/'results/rtl/w17_window_recovery_candidate_prepared_20261002/record.json'
MODEL=ROOT/'results/uarch/w17_window_recovery_candidate_preparation_20261002/model.json'
PACKAGE=ROOT/'rtl/test/w17_window_recovery_candidate_prepared'
BENCH=ROOT/'rtl/test/w17_window_recovery_gate/tb.sv'
STATUS='PARENT_WINDOW_RECOVERY_CONNECTED_SINGLE_GATE_GO'
CAPS={'MemoryMax':4294967296,'MemorySwapMax':0,'CPUAffinity':[30,31],
      'LimitFSIZE':268435456,'LimitCORE':0,'RuntimeMaxSec':180,
      'KillMode':'control-group','KillSignal':9,'OOMPolicy':'stop'}
BUDGET={'compile_jobs_max':2,'compile_steps':5,'connected_compile_seconds_each':30,
        'ghost_compile_seconds':10,'positive_case_seconds_each':4,
        'negative_case_seconds_each':4,'ghost_case_seconds_each':1,
        'declared_compile_total_seconds':130,'declared_runtime_total_seconds':26,
        'supervision_reserve_seconds':24,'service_hardstop_seconds':180,
        'generated_output_total_bytes':268435456,'cycles_per_connected_case':250000,
        'discard_control_watchdog_cycles':4096,'automatic_retries':0}
ENV_BLOCK=('VERILATOR_ROOT','VERILATOR_BIN','VERILATOR_TEST_FLAGS','VERILATOR_RUNNING',
           'MAKEFLAGS','MFLAGS','CC','CXX','CXXFLAGS','CPPFLAGS','LDFLAGS',
           'LD_PRELOAD','LD_LIBRARY_PATH','PERL5OPT','PERL5LIB')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')


def compiler():
    if any(os.environ.get(k) for k in ENV_BLOCK):raise ValueError('compiler environment override')
    wrapper=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator');binary=wrapper.with_name('verilator_bin')
    version=subprocess.check_output([str(wrapper),'--version'],text=True,timeout=5).strip()
    if version!='Verilator 5.050 2026-07-01 rev v5.050':raise ValueError('compiler version mismatch')
    return {'wrapper':str(wrapper),'wrapper_sha256':sha(wrapper),'binary':str(binary),
            'binary_sha256':sha(binary),'version':version,'environment_overrides_absent':list(ENV_BLOCK)}


def source_manifest():
    record=json.loads(RECORD.read_bytes())
    if RECORD.read_bytes()!=git('show',REVIEWED+':'+str(RECORD.relative_to(ROOT))):raise ValueError('reviewed record changed')
    if sha(ROOT/'tools/w17_window_recovery_prepare.py')!=record['generator_sha256']:raise ValueError('mutant/source generator pin')
    if record['selected_aperture']['WIN_STACK']!=2:raise ValueError('stack aperture')
    files=dict(record['prepared_files_sha256']);files[str(BENCH.relative_to(ROOT))]=sha(BENCH)
    files['tools/w17_window_recovery_prepare.py']=record['generator_sha256']
    files['rtl/test/w17_window_recovery_gate/tb.sv.diff']=sha(ROOT/'rtl/test/w17_window_recovery_gate/tb.sv.diff')
    for path,expected in files.items():
        if sha(ROOT/path)!=expected:raise ValueError('prepared source pin mismatch: '+path)
    for path in record['prepared_files_sha256']:
        if (ROOT/path).read_bytes()!=git('show',REVIEWED+':'+path):raise ValueError('69ded file changed')
    for item in record['copy_metadata'].values():
        if hashlib.sha256(git('show',item['origin_commit']+':'+item['origin_path'])).hexdigest()!=item['origin_sha256']:
            raise ValueError('origin provenance')
    # Re-run literal-default check as a read-only parse, never regenerate files.
    import importlib.util
    spec=importlib.util.spec_from_file_location('recovery_pin_prepare',ROOT/'tools/w17_window_recovery_prepare.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    renames={m.split_module(m.read_origin(*v))[2]:m.split_module(m.read_origin(*v))[2]+'_recovery_legacy' for v in m.ORIGINS.values()}
    for f,v in m.ORIGINS.items():
        original=m.read_origin(*v);name=m.split_module(original)[2];text=(PACKAGE/f).read_text()
        a=text.index('module '+name+'_recovery_legacy');b=text.index('endmodule',a)+len('endmodule');restored=text[a:b]
        for old,new in renames.items():restored=re.sub(r'\b'+new+r'\b',old,restored)
        oa=original.index('module ');ob=original.index('endmodule',oa)+len('endmodule')
        if restored!=original[oa:ob]:raise ValueError('legacy inverse mismatch')
    return record,files


def schedule(record):
    sources=[Path(p).name for p in record['future_compile_inputs']['sources']]
    jobs=[]
    def command(label,top,src):
        return ['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--binary','--timing','--assert','--top-module',top,
                '-j','2','-Wno-fatal','--Mdir','{run}/'+label+'/obj']+['{run}/'+label+'/sources/'+p for p in src]
    jobs.append({'label':'baseline','compile_command':command('baseline','tb',sources),
      'compile_seconds':30,'cases':[{'args':['+CASE='+c],'seconds':4,'expected':'PASS','marker':'PREPARED_RECOVERY_CASE_PASS case='+c}
                     for c in ('READ_HELD','WC_INTENT','WS_VISIBLE')]})
    for label,mutation in record['control_mutants'].items():
        jobs.append({'label':label,'compile_command':command(label,'tb',sources),'compile_seconds':30,
          'mutation':mutation,'cases':[{'args':['+CASE='+mutation['case'],'+CONTROL='+label],
            'seconds':4,'expected':'FAIL','marker':mutation['expected_failure']}]})
    label='provider_ghost_assumption'
    jobs.append({'label':label,'compile_command':command(label,'tb_provider_fence_ghost',['tb_provider_fence_ghost.sv']),
      'compile_seconds':10,'cases':[{'args':[],'seconds':1,'expected':'PASS','marker':'CLOSED_PROVIDER_ASSUMPTION_CHECK_ONLY'},
                    {'args':[],'seconds':1,'expected':'FAIL','marker':'FAIL_PROVIDER_FENCE_ASSUMPTION_VIOLATION; NOT_WINDOW_DETECTION'}],
      'ghost_two_configurations':'Use one runtime-selectable plusarg ghost witness, no second compile.'})
    # Original standalone witness is parameter-only. Use the pinned added
    # runtime-control witness in this gate, with the same identity fields.
    return jobs


def composition(record):
    uarch=ROOT/'tools/uarch_model.py'
    return {'unified_tool_sha256':sha(uarch),'basis_model_sha256':sha(MODEL),
      'applicable_designs':['v41_rom','v41_hbm'],'not_applicable_designs':['qwen_rom','qwen_hbm'],
      'dedicated_entry':{'element':'selected_WINDOW_recovery_fence_simulation_candidate','replicas_fixed':1,
        'macs_per_element':0,'ports_per_element':{'request_bits':342,'response_bits':279,'control_forward_bits':3,'control_reverse_bits':3},
        'ports_total':{'request_bits':342,'response_bits':279,'control_forward_bits':3,'control_reverse_bits':3},
        'storage_bits':259,'area_est_um2':638.7244,'area_cap_um2':1287.3632,'latency':0,
        'latency_basis':'Healthy added pipeline stages intended0; fault branch bounded by model assumptions, not token-rate gain.',
        'route_segments_proxy':24},
      'fault_branch':'Nread*(A+S+R)+Nwrite_intent*(A+S+V)+4 control edges; service fairness/readiness/visibility/fence bounds externally required. Fixture introduces finite interference and held-return release.',
      'slot_limitations':'No physical slot/corridor capacity, critical-path/SSFF or PHY provider qualification. Simulated ring assertions/observer IDs excluded from hardware estimate. No automatic evaluate() integration or adoption claimed.',
      'GO_review_required':'Parent explicitly approves unified-model composition and slot limitations; logical ledger alone is not physical signoff.'}


def prepare(out):
    record,files=source_manifest();receipt=compiler();jobs=schedule(record)
    ghost=ROOT/'rtl/test/w17_window_recovery_gate/tb_provider_fence_ghost.sv';files[str(ghost.relative_to(ROOT))]=sha(ghost)
    plan={'schema':'opentallas.window.recovery_connected_gate.v1','reviewed_source_commit':REVIEWED,
      'source_commit':record['source_commit'],'runner_sha256':sha(Path(__file__)),
      'model_sha256':sha(MODEL),'record_sha256':sha(RECORD),'manifest':files,'manifest_sha256':digest(files),
      'compiler':receipt,'jobs':jobs,'command_sha256':digest(jobs),'caps':CAPS,'budget':BUDGET,
      'model_composition':composition(record),'WIN_STACK':2,'OPT_RECOVERY_default':0,
      'scope':'Local connected source fault drain/restart, simulation provider only. No producer-wide cancellation, global reset, physical PHY, fulltoken or QDQ8-based fence credit.',
      'ghost_limitation':'Oracle distinguishes hidden operation0/512, wire fields identical. Hostile post-fence emission violates provider provenance; WINDOW has no detection claim. Uncertified provenance prohibits restart.',
      'visibility_oracle_scope':'Pinned idx schedule h_tcol/last_wr+CWL6250+BURST1024 projected deadline only. Scheduled command times can be retrospective relative to actual dispatch; this is not causal PHY completion. No fixed-floor/ACK-as-visible replacement.',
      'service_provider_admission':False,'physical_drain_admission':False,
      'state':'PREPARED_NOT_COMPILED_NOT_RUN'}
    out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',plan)
    go={'status':STATUS,'plan_sha256':sha(out/'plan.json'),**{k:plan[k] for k in
        ('runner_sha256','model_sha256','record_sha256','manifest_sha256','command_sha256','caps','budget')},
        'reviewed_model_composition_sha256':digest(plan['model_composition']),
        'reviewed_source_diff_budget':True,'reviewed_connected_oracle_and_negative_controls':True}
    write(out/'parent_GO_template.json',go)
    write(out/'preflight_receipt.json',{'verdict':'PASS_SOURCE_PINS_DEFAULT_INVERSE_PLAN_PREPARATION_ONLY',
      'plan_sha256':sha(out/'plan.json'),'no_service_created':True,'no_compile':True,'no_runtime':True})
    return plan


def validate_plan(path):
    plan=json.loads(Path(path).read_bytes());record,files=source_manifest()
    ghost=ROOT/'rtl/test/w17_window_recovery_gate/tb_provider_fence_ghost.sv';files[str(ghost.relative_to(ROOT))]=sha(ghost)
    for key,expected in [('runner_sha256',sha(Path(__file__))),('model_sha256',sha(MODEL)),
                         ('record_sha256',sha(RECORD)),('manifest',files),('manifest_sha256',digest(files)),
                         ('compiler',compiler()),('jobs',schedule(record)),('caps',CAPS),('budget',BUDGET),
                         ('model_composition',composition(record)),('WIN_STACK',2),('service_provider_admission',False),('physical_drain_admission',False)]:
        if plan.get(key)!=expected:raise ValueError('plan mismatch: '+key)
    if plan['command_sha256']!=digest(plan['jobs']):raise ValueError('command digest')
    return plan


def validate_go(go,plan,path):
    expected={'status':STATUS,'plan_sha256':sha(path),**{k:plan[k] for k in
      ('runner_sha256','model_sha256','record_sha256','manifest_sha256','command_sha256','caps','budget')},
      'reviewed_model_composition_sha256':digest(plan['model_composition']),
      'reviewed_source_diff_budget':True,'reviewed_connected_oracle_and_negative_controls':True}
    if go!=expected:raise ValueError('exact committed parent GO required')


def read_go(commit,path):
    if not re.fullmatch('[0-9a-f]{40}',commit or ''):raise ValueError('full40SHA GO commit required')
    return json.loads(git('show',commit+':'+path))


def parse_cpu_set(value):
    ids=[]
    for part in value.split():
        match=re.fullmatch(r'(\d+)(?:-(\d+))?',part)
        if not match:raise ValueError('CPU affinity syntax')
        first=int(match.group(1));last=int(match.group(2) or first)
        if last<first or last-first>4096:raise ValueError('CPU affinity range')
        ids.extend(range(first,last+1))
    return sorted(set(ids))


def caps_receipt(unit):
    fields=['ControlGroup','MemoryMax','MemorySwapMax','CPUAffinity','LimitFSIZE','LimitCORE','RuntimeMaxUSec','KillMode','KillSignal','OOMPolicy']
    raw=subprocess.check_output(['systemctl','--user','show',unit]+['--property='+k for k in fields],text=True)
    got=dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
    for k,v in CAPS.items():
        if k=='RuntimeMaxSec':
            if got.get('RuntimeMaxUSec') not in ('3min','180000000'):raise ValueError('hardstop cap')
        elif k=='CPUAffinity':
            if parse_cpu_set(got.get(k,''))!=v:raise ValueError('CPU cap')
        elif str(got.get(k))!=str(v):raise ValueError('cgroup cap: '+k)
    if sorted(os.sched_getaffinity(0))!=CAPS['CPUAffinity']:raise ValueError('actual affinity')
    if resource.getrlimit(resource.RLIMIT_FSIZE)!=(CAPS['LimitFSIZE'],CAPS['LimitFSIZE']):raise ValueError('actual FSIZE')
    # Validate kernel cgroup values, not only requested systemd properties.
    relative=next(line.split('::',1)[1] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
    cgroup=Path('/sys/fs/cgroup')/relative.lstrip('/')
    if got.get('ControlGroup')!=relative:raise ValueError('worker not in declared aggregate cgroup')
    if (cgroup/'memory.max').read_text().strip()!=str(CAPS['MemoryMax']) or (cgroup/'memory.swap.max').read_text().strip()!='0':raise ValueError('actual aggregate memory/swap cap')
    return {'systemd':got,'kernel_cgroup':str(cgroup),'memory_max':(cgroup/'memory.max').read_text().strip(),
            'swap_max':(cgroup/'memory.swap.max').read_text().strip(),'affinity':sorted(os.sched_getaffinity(0))}


def output_size(out):return sum(p.stat().st_size for p in out.rglob('*') if p.is_file())


def supervised(command,log,seconds,out):
    start=time.monotonic()
    with log.open('x') as stream:
        p=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while p.poll() is None:
                if time.monotonic()-start>seconds or output_size(out)>BUDGET['generated_output_total_bytes']:
                    raise RuntimeError('stage time/generated-output cap; no retry')
                time.sleep(.1)
        except BaseException:
            import signal
            os.killpg(p.pid,signal.SIGKILL);p.wait();raise
    return {'command':command,'returncode':p.returncode,'wall_seconds':time.monotonic()-start,
            'log':str(log),'log_sha256':sha(log)}


def worker(args):
    plan=validate_plan(args.plan)
    if not args.probe:
        go=read_go(args.go_commit,args.go_path);validate_go(go,plan,args.plan)
    out=Path(args.out);receipt=caps_receipt(args.unit);write(out/'caps_before_compile.json',receipt)
    if args.probe:
        write(out/'record.json',{'verdict':'PASS_ACTUAL_CAP_PROBE_NO_RTL_COMPILE_OR_RUNTIME',
          'caps':receipt,'compiler':compiler(),'no_compile':True,'no_runtime':True})
        return 0
    steps=[];status='FAIL_PRESERVED_NO_RETRY'
    try:
        record=json.loads(RECORD.read_bytes())
        # Worker only mutates NEW bounded snapshots after GO; source package is immutable.
        for job in plan['jobs']:
            home=out/job['label'];src=home/'sources';src.mkdir(parents=True,exist_ok=False)
            if job['label']=='provider_ghost_assumption':
                shutil.copyfile(ROOT/'rtl/test/w17_window_recovery_gate/tb_provider_fence_ghost.sv',src/'tb_provider_fence_ghost.sv')
            else:
                for path in record['future_compile_inputs']['sources']:
                    p=Path(path);shutil.copyfile(BENCH if p.name=='tb.sv' else ROOT/p,src/p.name)
                if 'mutation' in job:
                    import importlib.util
                    sp=importlib.util.spec_from_file_location('prep_mutants',ROOT/'tools/w17_window_recovery_prepare.py')
                    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
                    mutation=m.control_mutants()[job['label']];p=src/mutation['file'];s=p.read_text()
                    starts=[match.start() for match in re.finditer(r'\bmodule ',s)];i=starts[2]
                    p.write_text(s[:i]+m.edit(s[i:],mutation['old'],mutation['new']))
            write(home/'snapshot_sha256.json',{p.name:sha(p) for p in src.iterdir()})
            command=[x.format(run=str(out.resolve())) for x in job['compile_command']]
            step=supervised(command,home/'compile.log',job['compile_seconds'],out);steps.append(step)
            if step['returncode']!=0:raise RuntimeError('compile failed; no retry')
            binary=home/'obj'/('Vtb_provider_fence_ghost' if job['label']=='provider_ghost_assumption' else 'Vtb')
            if not binary.is_file():raise RuntimeError('expected binary absent')
            write(home/'binary_receipt.json',{'sha256':sha(binary),'bytes':binary.stat().st_size})
            for index,case in enumerate(job['cases']):
                command=[str(binary.resolve())]+case['args']
                if job['label']=='provider_ghost_assumption' and case['expected']=='FAIL':command+=['+VIOLATE_FENCE']
                step=supervised(command,home/f'case{index}.log',case['seconds'],out);steps.append(step)
                verify_runtime(case,step['returncode'],Path(step['log']).read_text())
            write(out/'partial_steps.json',steps)
        events=Path(receipt['kernel_cgroup'],'memory.events').read_text()
        if any(int(line.split()[1]) for line in events.splitlines() if line.split()[0] in ('oom','oom_kill','oom_group_kill')):
            raise RuntimeError('aggregate memory cap events; no qualification')
        status='PASS_CONNECTED_SELECTED_OWNER_BOOKKEEPING_PROJECTED_VISIBILITY_AND_CONTROLS'
        return 0
    except BaseException as exc:
        write(out/'failure.json',{'error':str(exc),'type':type(exc).__name__,'retry':False})
        return 1
    finally:
        cgroup=Path(receipt['kernel_cgroup'])
        stats={p:(cgroup/p).read_text().strip() for p in ('memory.events','memory.peak')}
        if any(int(line.split()[1]) for line in stats['memory.events'].splitlines() if line.split()[0] in ('oom','oom_kill','oom_group_kill')):
            status='FAIL_CAP_EVENTS_PRESERVED_NO_RETRY'
        write(out/'record.json',{'verdict':status,'aggregate_memory_stats':stats,'plan_sha256':sha(args.plan),'GO_commit':args.go_commit,
          'steps':steps,'source_manifest_sha256':plan['manifest_sha256'],'scope':plan['scope'],
          'ghost_limitation':plan['ghost_limitation'],'visibility_oracle_scope':plan['visibility_oracle_scope'],
          'physical_credit':False,'service_provider_admission':False,'physical_drain_admission':False,'wholeprovider_admission':False})


def verify_runtime(case,code,text):
    if case['expected']=='PASS':
        if code!=0 or case['marker'] not in text or re.search(r'%Error|Assertion failed|FAIL_PROVIDER',text):raise ValueError('positive receipt rejected')
    elif code!=-6 or case['marker'] not in text:raise ValueError('negative missing declared semantic SIGABRT witness')


def claim_go(commit, directory=Path('/tmp')):
    # Consume once before any service launch. Never remove even on failure.
    claim=directory/('w17-window-recovery-GO-consumed-'+commit)
    claim.mkdir(exist_ok=False)
    return claim


def launch(args):
    plan=validate_plan(args.plan)
    if not args.probe:
        go=read_go(args.go_commit,args.go_path);validate_go(go,plan,args.plan)
    if not re.fullmatch(r'w17-recovery-[a-zA-Z0-9_-]+',args.unit or ''):raise ValueError('unique recovery unit name required')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    if not args.probe:
        claim=claim_go(args.go_commit)
        write(claim/'receipt.json',{'plan_sha256':sha(args.plan),'unit':args.unit,'out':str(out.resolve()),'GO_commit':args.go_commit,'no_retry':True})
    props=['MemoryMax=4294967296','MemorySwapMax=0','CPUAffinity=30 31','LimitFSIZE=268435456','LimitCORE=0',
           'RuntimeMaxSec=180','KillMode=control-group','KillSignal=9','OOMPolicy=stop','Nice=10']
    command=['systemd-run','--user','--wait','--pipe','--unit='+args.unit]+['--property='+p for p in props]+[
      '--working-directory='+str(ROOT),sys.executable,str(Path(__file__).resolve()),'--worker','--plan',str(Path(args.plan).resolve()),
      '--out',str(out.resolve()),'--unit',args.unit]
    command += ['--probe'] if args.probe else ['--go-commit',args.go_commit,'--go-path',args.go_path]
    write(out/'launch.json',{'command':command,'plan_sha256':sha(args.plan),'GO_commit':args.go_commit,'mode':'PROBE' if args.probe else 'AUTHORIZED_RUN','retry':False})
    with (out/'service.log').open('x') as f:
        rc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT).returncode
    state=subprocess.check_output(['systemctl','--user','show',args.unit,'--property=ActiveState','--property=MainPID','--property=Result','--property=ExecMainStatus'],text=True)
    write(out/'service_receipt.json',{'returncode':rc,'terminal':state,'record_exists':(out/'record.json').exists()})
    return rc


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare',action='store_true');ap.add_argument('--probe',action='store_true');ap.add_argument('--worker',action='store_true')
    ap.add_argument('--plan');ap.add_argument('--out',required=True);ap.add_argument('--unit');ap.add_argument('--go-commit');ap.add_argument('--go-path');args=ap.parse_args()
    if args.prepare:prepare(Path(args.out));return 0
    if not args.plan:raise ValueError('plan required')
    return worker(args) if args.worker else launch(args)


if __name__=='__main__':raise SystemExit(main())
