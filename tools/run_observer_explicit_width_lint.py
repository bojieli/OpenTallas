#!/usr/bin/env python3
"""Explicit-width derivative; same strict warning gate and resource caps.
Opt-in future lint only. Default is plan inspection; GO must pin reviewed plan.

Direct Verilator frontend binary, no Perl wrapper/compiler children, cc/build/make
or simulator. RLIMIT_AS bounds its entire address space more tightly than RSS;
affinity limits all frontend threads to two CPUs. Resource-priced derivative, 64GiB address-space cap, 600s/mode. No sufficiency claim.
Output budget is total stdout
plus stderr across all seven compiler invocations, retained at most 16 MiB. All artifacts use a fresh directory.
"""
import argparse,hashlib,json,math,os,re,resource,selectors,signal,subprocess,time
from pathlib import Path

MEMORY=64*1024**3
import model_observer_frontend_resources as cost
import prepare_observer_explicit_widths as widths
LOG=16*1024**2

def digest(data):return hashlib.sha256(data).hexdigest()
def require_go(plan_bytes,go):
    if set(go)!={'plan_sha256','decision','reviewer','source_ownership_and_guard_provenance_reviewed','resource_caps_reviewed','lint_only_no_live_selection','source_cost_and_calibration_limits_reviewed','explicit_width_mapping_reviewed'}:
        raise ValueError('unexpected GO schema')
    if go['plan_sha256']!=digest(plan_bytes) or go['decision']!='GO' or not isinstance(go['reviewer'],str) or not go['reviewer'].strip():
        raise ValueError('reviewed plan GO missing')
    for key in ('source_ownership_and_guard_provenance_reviewed','resource_caps_reviewed','lint_only_no_live_selection','source_cost_and_calibration_limits_reviewed','explicit_width_mapping_reviewed'):
        if go[key] is not True:raise ValueError('GO review incomplete')

def supervise(argv,cwd,env,log,seconds,memory=MEMORY,log_max=LOG,cpu_count=2):
    """Finite supervisor; tests exercise caps with small Python children only."""
    if not argv or not 0<seconds<=600 or not 0<memory<=MEMORY or not 0<log_max<=LOG or cpu_count!=2:
        raise ValueError('invalid capped invocation')
    cpus=sorted(os.sched_getaffinity(0))[:cpu_count]
    if len(cpus)!=cpu_count:raise ValueError('two CPUs unavailable')
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(memory,memory))
        resource.setrlimit(resource.RLIMIT_CPU,(math.ceil(seconds*cpu_count),math.ceil(seconds*cpu_count)))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_FSIZE,(log_max,log_max))
        os.sched_setaffinity(0,cpus)
    start=time.monotonic();reason=None;written=0;usage=None
    with Path(log).open('xb') as output:
        process=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
        poll=selectors.DefaultSelector();poll.register(process.stdout,selectors.EVENT_READ)
        try:
            while poll.get_map():
                if time.monotonic()-start>=seconds:
                    reason='WALL_CAP';os.killpg(process.pid,signal.SIGKILL);break
                for key,_ in poll.select(min(0.05,max(0,seconds-(time.monotonic()-start)))):
                    chunk=os.read(key.fd,65536)
                    if not chunk:poll.unregister(key.fileobj);continue
                    remaining=log_max-written
                    output.write(chunk[:remaining]);written+=min(len(chunk),remaining)
                    if len(chunk)>remaining:
                        reason='LOG_CAP';os.killpg(process.pid,signal.SIGKILL);break
                if reason:break
            while True:
                pid,status,child_usage=os.wait4(process.pid,os.WNOHANG)
                if pid:
                    code=os.waitstatus_to_exitcode(status);usage=child_usage;process.returncode=code;break
                if time.monotonic()-start>=seconds+2:
                    reason='REAP_PENDING';code=-signal.SIGKILL;break
                if time.monotonic()-start>=seconds:
                    reason=reason or 'WALL_CAP'
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                time.sleep(0.01)
        finally:
            poll.close();process.stdout.close()
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                try:process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:pass
    return dict(argv=argv,child_pid=process.pid,reap_pending=usage is None,returncode=code,cap_reason=reason,seconds=round(time.monotonic()-start,3),peak_rss_kib=usage.ru_maxrss if usage else None,log_bytes=written,log_sha256=digest(Path(log).read_bytes()),limits=dict(address_space_bytes=memory,wall_seconds=seconds,cpu_affinity=cpus,log_bytes=log_max,core_bytes=0),success=code==0 and reason is None)

def validate_plan(plan):
    caps=plan['caps']
    repo=Path(__file__).resolve().parents[1]
    old_bytes=(repo/plan['unchanged_plan_path']).read_bytes()
    if digest(old_bytes)!=plan['unchanged_plan_sha256']:raise ValueError('prior plan pin mismatch')
    old=json.loads(old_bytes)
    if plan['modes']!=widths.expected_modes(repo,old) or plan['tool']!=old['tool'] or plan['source_commit']!=cost.SOURCE:raise ValueError('source/command scope changed')
    for p,s in plan['resource_evidence_sha256'].items():
        if digest((repo/p).read_bytes())!=s:raise ValueError('resource evidence pin mismatch')
    cost.validate_evidence(repo)
    cost.validate_selected_counts(repo)
    widths.validate_inverse_to_real(repo)
    widths.source_field_authority(repo,old)
    if caps!=dict(memory_bytes=MEMORY,cpu_count=2,mode_wall_seconds=600,mutant_wall_seconds=30,version_wall_seconds=5,log_bytes=LOG,max_children=1,serial=True,total_compiler_wall_budget_seconds=1325):raise ValueError('cap contract changed')
    if plan['status']!='STATIC_OWNERSHIP_RESOLVED_AWAIT_PARENT_GO' or len(plan['modes'])!=2:raise ValueError('unready plan')
    for mode in plan['modes']:
        if mode['closure']['ambiguous'] or set(mode['closure']['unresolved'])-mode['guard_resolution'].keys():raise ValueError('unresolved ownership')
        if any(g.get('false') is not True for g in mode['guard_resolution'].values()):raise ValueError('reachable guard')
        argv=mode['argv']
        if argv[0]!=plan['tool']['executable'] or '--lint-only' not in argv or {'--cc','--build','--binary','--bbox-unsup','--bbox-sys'}&set(argv):raise ValueError('not authorized lint')
        if any(str(x) in {'make','g++','clang++'} for x in argv):raise ValueError('build command')
        if not all(mode['parameters'][k]==v for k,v in dict(SUN=256,SUM=64,CL_DEPTH=512,ROM_PHW=6).items()):raise ValueError('undersized hierarchy')

def execute(repo,plan_path,go_path,scratch):
    repo=Path(repo).resolve();plan_bytes=Path(plan_path).read_bytes();plan=json.loads(plan_bytes)
    require_go(plan_bytes,json.loads(Path(go_path).read_bytes()));validate_plan(plan)
    for path,sha in plan['tool']['pins'].items():
        if digest(Path(path).read_bytes())!=sha:raise ValueError('tool pin mismatch')
    for path,sha in plan['preparation_tools'].items():
        if digest((repo/path).read_bytes())!=sha:raise ValueError('runner/preparation pin mismatch')
    # Validate every input BEFORE scratch creation or any compiler invocation.
    all_inputs={}
    for mode in plan['modes']:
        for path,sha in mode['source_sha256'].items():
            candidate=Path(path)
            if candidate.is_absolute() or '..' in candidate.parts:raise ValueError('unsafe source path')
            if path.startswith('rtl/test/v41_runtime/') and 'sim_observe' in path:
                data=(repo/path).read_bytes()
            else:data=subprocess.check_output(['git','show',plan['source_commit']+':'+path],cwd=repo)
            if digest(data)!=sha:raise ValueError('source pin mismatch: '+path)
            if path in all_inputs and all_inputs[path]!=data:raise ValueError('mixed source ownership')
            all_inputs[path]=data
    admission=cost.headroom();cost.admit(admission)
    scratch=Path(scratch).resolve()
    if not str(scratch).startswith('/tmp/'):raise ValueError('fresh /tmp scratch required')
    scratch.mkdir(exist_ok=False)
    (scratch/'resource_admission.json').write_text(json.dumps(admission,indent=2)+'\n')
    env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C',**plan['tool']['environment']}
    results=[]
    version=supervise(plan['tool']['version_command'],scratch,env,scratch/'version.log',5)
    results.append(dict(name='version',**version))
    expected=plan['tool']['metadata_version']
    if not version['success'] or not (scratch/'version.log').read_text(errors='replace').strip().startswith('Verilator '+expected):
        (scratch/'receipt.json').write_text(json.dumps(dict(status='TOOL_VERSION_FAIL',steps=results),indent=2)+'\n');return False
    remaining_log=LOG-version['log_bytes']
    def readmit(name):
        measured=cost.headroom()
        try:cost.admit(measured)
        except ValueError as error:
            (scratch/'receipt.json').write_text(json.dumps(dict(status='RESOURCE_ADMISSION_FAIL',failed_step=name,reason=str(error),headroom=measured,steps=results,plan_sha256=digest(plan_bytes),causal_deadlines='BOUND_MISSING',live_selected=False),indent=2)+'\n')
            return False
        admissions=scratch/'resource_checks.jsonl'
        with admissions.open('a') as f:f.write(json.dumps(dict(step=name,headroom=measured))+'\n')
        return True
    for mode in plan['modes']:
        root=scratch/mode['name'];root.mkdir()
        for path in mode['source_sha256']:
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(all_inputs[path])
        if remaining_log<=0:break
        if not readmit(mode['name']+'/baseline'):return False
        result=supervise(mode['argv'],root,env,root/'baseline.log',600,log_max=remaining_log)
        remaining_log-=result['log_bytes']
        results.append(dict(name=mode['name']+'/baseline',**result))
        # Preserve all warnings; width/reference/parameter messages in observer
        # or Error are blocking despite non-fatal inherited warning policy.
        text=(root/'baseline.log').read_text(errors='replace')
        observer_warning=any(line.startswith('%Warning-') and mode['copy'] in line and any(code in line for code in ('WIDTH','PIN','IMPLICIT','UNDRIVEN')) for line in text.splitlines())
        if not result['success'] or '%Error' in text or observer_warning:break
        for mutation in mode['mutants']:
            mutant_root=root/mutation['name'];mutant_root.mkdir()
            for path in mode['source_sha256']:
                data=all_inputs[path]
                if path==mode['copy']:
                    source=data.decode()
                    if source.count(mutation['find'])!=1:raise ValueError('mutant must alter exactly one source occurrence')
                    data=source.replace(mutation['find'],mutation['replace']).encode()
                target=mutant_root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            if remaining_log<=0:break
            if not readmit(mode['name']+'/'+mutation['name']):return False
            bad=supervise(mode['argv'],mutant_root,env,mutant_root/'mutant.log',30,log_max=remaining_log)
            remaining_log-=bad['log_bytes']
            diagnostic=(mutant_root/'mutant.log').read_text(errors='replace')
            rejected=bad['returncode']!=0 and bad['cap_reason'] is None and mutation['expected_diagnostic'] in diagnostic and '%Error' in diagnostic
            results.append(dict(name=mode['name']+'/'+mutation['name'],expected_compiler_rejection=rejected,**bad))
            if not rejected:break
        else:continue
        break
    passed=len(results)==7 and all(s.get('expected_compiler_rejection',s['success']) for s in results)
    (scratch/'receipt.json').write_text(json.dumps(dict(status='LINT_HIERARCHY_ONLY_PASS' if passed else 'FAIL_RETAINED',plan_sha256=digest(plan_bytes),steps=results,causal_deadlines='BOUND_MISSING',live_selected=False),indent=2)+'\n')
    return passed

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.');ap.add_argument('--plan',required=True);ap.add_argument('--go');ap.add_argument('--scratch');ap.add_argument('--execute',action='store_true');args=ap.parse_args()
    if not args.execute:
        plan=json.loads(Path(args.plan).read_bytes());validate_plan(plan);print('PLAN ONLY; compiler execution requires reviewed GO and --execute')
    else:
        if not args.go or not args.scratch:ap.error('--go and fresh --scratch required')
        raise SystemExit(0 if execute(args.repo,args.plan,args.go,args.scratch) else 1)
