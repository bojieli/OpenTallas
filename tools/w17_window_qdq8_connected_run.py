#!/usr/bin/env python3
"""Prepare/probe one GO-bound aggregate-budget connected QDQ8 service."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import w17_window_qdq8_arithmetic_run as caps_lib
import w17_window_epoch9_producer_run as trace_lib

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'results/uarch/w17_window_qdq8_connected_preparation_20261002'
PREPARED=Path('/tmp/window-qdq8-connected-prepared-20261002-r2')
REVIEWED='2a0285f4e0ae15836e19e0882fdc47519c0b51ba'
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
CAPS=caps_lib.CAPS
BUDGET=dict(whole_service_seconds=180,compile_total_seconds=150,compile_count=2,
            case_seconds=5,cases=2,total_case_seconds=10,supervision_reserve_seconds=20)
DEPS=['tools/w17_window_qdq8_arithmetic_run.py','tools/w17_window_epoch9_producer_run.py']
sha=caps_lib.sha;objsha=caps_lib.objsha;write=caps_lib.write;git=caps_lib.git


def provenance():
    model=json.loads((EVIDENCE/'model.json').read_bytes());manifest=json.loads((EVIDENCE/'files_sha256.json').read_bytes())
    assert model['source_commit']==SOURCE
    diffs=[]
    for path,h in model['source_sha256'].items():
        assert hashlib.sha256(git('show',SOURCE+':'+path)).hexdigest()==h and sha(ROOT/path)==h
        diffs.append(dict(path=path,sha256=h,byteidentical=True))
    for key in ('candidate_sha256','dependencies_sha256','fixture_sha256'):
        for path,h in model[key].items():assert sha(ROOT/path)==h
    for path,h in manifest.items():assert sha(EVIDENCE/path)==h and sha(PREPARED/path)==h
    assert sha(EVIDENCE/'files_sha256.json')==sha(PREPARED/'files_sha256.json')
    assert {str(p.relative_to(PREPARED)) for p in PREPARED.rglob('*') if p.is_file()}==set(manifest)|{'files_sha256.json'},'Prior build/tree mutation; no retry'
    assert sha(ROOT/'tools/w17_window_qdq8_connected_model.py')==model['generator_sha256']
    assert model['actual_QE']==dict(AW=30,NW=21,BL=16,IL=8,NBMAX=192,CHUNK8=1,QLB=272,MP=1,mode=1,fp4=0,nb=16,xbase=54720,obase=55232,SEPARATE_ROWS=1,KVT_SH=13,POS_W=21)
    assert [(n,c['pairs'],c['write_requests'],c['cold_rows']) for n,c in model['cases'].items()]==[('retain0',3,32,768),('retain1',5,32,640)]
    assert list(model['preparation']['commands'])==['retain0','retain1']
    assert not any((PREPARED/('obj_'+n)).exists() for n in ('retain0','retain1'))
    return model,manifest,diffs


def prepare(out):
    model,manifest,diffs=provenance();commands=model['preparation']['commands']
    compiler={n:caps_lib.compiler_receipt(c['compile']) for n,c in commands.items()}
    plan=dict(schema='opentallas.window.connected_QDQ8_single_service_plan.v1',reviewed_commit=REVIEWED,
      runner_sha256=sha(Path(__file__)),runner_dependencies_sha256={p:sha(ROOT/p) for p in DEPS},
      model_sha256=sha(EVIDENCE/'model.json'),manifest_sha256=sha(EVIDENCE/'files_sha256.json'),
      prepared_file_sha256=manifest,source_diffs=diffs,compiler=compiler,commands=commands,
      caps=CAPS,budget=BUDGET,healthy_added_guard_cycles=0,
      GO_status='PARENT_QDQ8_CONNECTED_SINGLE_SERVICE_GO',
      scope='Actualfull512QE/32WR/128x17/mux/KARB/backend/QKPVnaturalwrap healthy only. Producerfreeze/cancel and downstream recovery unqualified. No fulltoken/hardware/clock claim.',
      no_retry_no_fallback=True,state='PREPARED_NOT_COMPILED_NOT_RUN_FRESH_GO_REQUIRED')
    out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',plan)
    write(out/'source_diff_receipt.json',dict(verdict='PASS_ORIGINALS_BYTEIDENTICAL',diffs=diffs,candidate_sha256=model['candidate_sha256'],fixture_sha256=model['fixture_sha256']))
    write(out/'compiler_receipt.json',compiler)
    return plan


def validate_plan(path):
    plan=json.loads(path.read_bytes());model,manifest,diffs=provenance()
    assert plan['runner_sha256']==sha(Path(__file__))
    assert plan['runner_dependencies_sha256']=={p:sha(ROOT/p) for p in DEPS}
    assert plan['model_sha256']==sha(EVIDENCE/'model.json') and plan['manifest_sha256']==sha(EVIDENCE/'files_sha256.json')
    assert plan['prepared_file_sha256']==manifest and plan['source_diffs']==diffs
    assert plan['commands']==model['preparation']['commands']
    assert plan['compiler']=={n:caps_lib.compiler_receipt(c['compile']) for n,c in plan['commands'].items()}
    assert plan['caps']==CAPS and plan['budget']==BUDGET and plan['healthy_added_guard_cycles']==0
    return plan,model


def validate_GO(go,plan,path):
    assert go['status']=='PARENT_QDQ8_CONNECTED_SINGLE_SERVICE_GO'
    for k in ('runner_sha256','runner_dependencies_sha256','model_sha256','manifest_sha256','caps','budget','healthy_added_guard_cycles'):assert go[k]==plan[k],k
    assert go['plan_sha256']==sha(path)
    assert go['commands_sha256']==objsha(plan['commands'])


def remaining_compile_budget(used):
    remaining=BUDGET['compile_total_seconds']-used
    assert remaining>0,'Shared compile budget exhausted; no second compile/fallback'
    return remaining


def compare(log,summary,events):
    # Reuse full transport comparator, correcting single regex-group parsing and
    # adapting the declared operation counts/terminal marker. No timing fit.
    src=inspect.getsource(trace_lib.compare)
    edits={
      'actual=[list(map(int,x)) for x in re.findall(pattern,log)]':'actual=[list(map(int,x.groups())) for x in re.finditer(pattern,log)]',
      'PRODUCER_LIFECYCLE_PASS':'QDQ8_CONNECTED_LIFECYCLE_PASS',
      "expected=[summary['retain'],32,32,2176*(1 if summary['retain'] else 2),2176*(1 if summary['retain'] else 2),64,summary['final_epoch']]":
      "expected=[summary['retain'],32,32,summary['read_requests'],summary['read_requests'],summary['total_packed_beats'],summary['final_epoch']]"}
    for old,new in edits.items():assert src.count(old)==1;src=src.replace(old,new)
    ns={};exec(compile(src,'<connected full transport comparison>','exec'),trace_lib.__dict__,ns)
    result=ns['compare'](log,summary,events)
    gold=json.loads((EVIDENCE/'oracle.json').read_bytes())
    pack=lambda a,w:sum(x<<(i*w) for i,x in enumerate(a))
    actual=[[int(a),int(b),int(c),int(d,16),int(e,16)] for a,b,c,d,e in re.findall(r'QE_CAPTURE cycle=(\d+) block=(\d+) address=(\d+) codes=([0-9a-fA-F]+) scale=([0-9a-fA-F]+)',log)]
    expected=[[c,b,55232+32*b,pack(gold[b]['codes'],8),gold[b]['scale']] for b,c in enumerate(summary['QE_capture_cycles'])]
    result['checks']['actual_QE_capture']=dict(exact=actual==expected,actual_count=len(actual),expected_count=len(expected))
    if actual!=expected:result['mismatches'].append(dict(kind='actual_QE_capture',actual=actual,expected=expected))
    wrap=[e for e in events if e['kind']=='reply' and e['tag']&65535==16]
    expected=[[e['cycle'],512] for e in wrap]
    actual=[list(map(int,m.groups())) for m in re.finditer(r'NATURAL_EPOCH_WRAP cycle=(\d+) coldrow=(\d+)',log)]
    result['checks']['natural_wrap']=dict(exact=actual==expected,actual=actual,expected=expected)
    if actual!=expected:result['mismatches'].append(dict(kind='natural_wrap',actual=actual,expected=expected))
    result['verdict']='PASS' if not result['mismatches'] else 'FAIL_PRESERVED_NO_FIT'
    return result


def worker(a):
    out=Path(a.out);start=time.monotonic();used=0.0;cg=None
    record=dict(mode='CAP_PROBE_ONLY' if a.probe else 'CONNECTED_SINGLE_SERVICE',results=[])
    try:
        plan,model=validate_plan(Path(a.plan))
        if not a.probe:
            assert not git('status','--porcelain'),'Clean pinned worktree required'
            assert re.fullmatch('[0-9a-f]{40}',a.go_commit) and a.go_path.startswith('results/rtl/')
            raw=git('show',a.go_commit+':'+a.go_path);validate_GO(json.loads(raw),plan,Path(a.plan));(out/'parent_GO.json').write_bytes(raw)
            record['GO_commit']=a.go_commit
        values,cg,props=caps_lib.cap_values(a.unit)
        caps=dict(actual=values,cgroup=str(cg),properties=props,compiler=plan['compiler'])
        try:caps_lib.validate_caps(values);caps['verdict']='PASS_VERIFIED_BEFORE_COMPILE'
        except AssertionError:caps['verdict']='FAIL_CAPS_NO_COMPILE_NO_FALLBACK';raise
        finally:write(out/'caps_before_compile.json',caps)
        record.update(plan_sha256=sha(a.plan),runner_sha256=sha(Path(__file__)),source_head=git('rev-parse','HEAD').decode().strip(),budget=BUDGET)
        write(out/'in_progress.json',record)
        if a.probe:record['verdict']='PASS_SHARED_CAP_PROBE_NO_BUILD_NO_RUNTIME'
        else:
            for name in ('retain0','retain1'):
                command=plan['commands'][name];item=dict(case=name);record['results'].append(item)
                item['compile']=caps_lib.execute(command['compile'],ROOT,out/(name+'_compile.log'),remaining_compile_budget(used))
                used+=item['compile']['wall_seconds'];record['compile_seconds_used']=used
                write(out/'in_progress.json',record)
                if item['compile']['status']!=0:raise RuntimeError('Compile failure/cap: stop, no retry/fallback')
                binary=Path(command['runtime'][0]);item['binary']=dict(path=str(binary),sha256=sha(binary),bytes=binary.stat().st_size)
                write(out/'in_progress.json',record)
                assert time.monotonic()-start+BUDGET['case_seconds']<180
                item['runtime']=caps_lib.execute(command['runtime'],Path(command['cwd']),out/(name+'_runtime.log'),BUDGET['case_seconds'])
                events=[json.loads(x) for x in (EVIDENCE/(name+'_events.jsonl')).read_text().splitlines()]
                item['comparison']=compare((out/(name+'_runtime.log')).read_text(),model['cases'][name],events)
                write(out/'in_progress.json',record)
                if item['runtime']['status']!=0 or item['comparison']['verdict']!='PASS':raise RuntimeError('Runtime/model mismatch: stop, no retry/fit')
            record['verdict']='PASS_BOUNDED_ACTUAL_QDQ8_CONNECTED_HEALTHY_LIFECYCLE_NATURAL_WRAP'
    except Exception as e:record.update(verdict='FAIL_PRESERVED_NO_FALLBACK_NO_RETRY',error_type=type(e).__name__,error=str(e))
    finally:
        if cg is not None and cg.exists():
            record['aggregate_memory_peak_bytes']=int((cg/'memory.peak').read_text());record['memory_events']=(cg/'memory.events').read_text()
        record['worker_wall_seconds']=time.monotonic()-start;record['compile_seconds_used']=used
        write(out/'record.json',record)
    return 0 if record['verdict'].startswith('PASS') else 1


def launch(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    try:
        plan,model=validate_plan(Path(a.plan))
        if not a.probe:
            assert a.go_commit and a.go_path,'Fresh connected parent GO required'
            assert re.fullmatch('[0-9a-f]{40}',a.go_commit) and a.go_path.startswith('results/rtl/')
            validate_GO(json.loads(git('show',a.go_commit+':'+a.go_path)),plan,Path(a.plan))
            assert not git('status','--porcelain')
        assert subprocess.check_output(['systemctl','--user','show',a.unit,'--property=LoadState'],text=True).strip()=='LoadState=not-found','Unit reuse forbidden'
        write(out/'preflight_receipt.json',dict(verdict='PASS_LAUNCH_PREFLIGHT_NO_COMPILE',plan_sha256=sha(a.plan),probe=a.probe))
    except Exception as e:
        write(out/'preflight_receipt.json',dict(verdict='FAIL_PREFLIGHT_NO_SERVICE_NO_COMPILE_NO_RETRY',error=str(e),error_type=type(e).__name__));return 2
    cmd=['systemd-run','--user','--unit='+a.unit,'--wait','--pipe','--property=MemoryMax=4294967296','--property=MemorySwapMax=0',
      '--property=CPUAffinity=30 31','--property=RuntimeMaxSec=180','--property=KillMode=control-group','--property=KillSignal=SIGKILL',
      '--property=OOMPolicy=kill','--property=LimitFSIZE=268435456','--property=LimitCORE=0','--property=Nice=10',
      '--working-directory='+str(ROOT),sys.executable,str(Path(__file__).resolve()),'--worker','--plan',str(Path(a.plan).resolve()),'--out',str(out.resolve()),'--unit',a.unit]
    if a.probe:cmd+=['--probe']
    else:cmd+=['--go-commit',a.go_commit,'--go-path',a.go_path]
    write(out/'launch.json',dict(command=cmd,plan_sha256=sha(a.plan),no_retry_no_fallback=True))
    with (out/'service.log').open('x') as f:status=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
    terminal=subprocess.check_output(['systemctl','--user','show',a.unit,'--property=MainPID','--property=ActiveState','--property=Result','--property=ExecMainStatus'],text=True)
    write(out/'service_receipt.json',dict(status=status,terminal=terminal,record_exists=(out/'record.json').exists(),caps_exists=(out/'caps_before_compile.json').exists()))
    return status


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare',action='store_true');ap.add_argument('--probe',action='store_true');ap.add_argument('--worker',action='store_true')
    ap.add_argument('--plan');ap.add_argument('--out',required=True);ap.add_argument('--unit');ap.add_argument('--go-commit');ap.add_argument('--go-path');a=ap.parse_args()
    if a.prepare:prepare(Path(a.out));return 0
    assert a.plan and a.unit
    return worker(a) if a.worker else launch(a)
if __name__=='__main__':raise SystemExit(main())
