#!/usr/bin/env python3
"""Single parent-GO run in verified aggregate systemd cgroup; no fallback/retry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
HEAD_PIN='b0f895dc41cf5f2a2bc43f6ea2c0542e69abfe98'
GO='6d4988055'
GO_PATH='results/rtl/parent_producer_preparation_review_20261002.json'
PRED='results/uarch/w17_window_epoch9_producer_prediction_20261001_attempt3'
CPUS={30,31}


def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def pin_check(prepared):
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    assert subprocess.run(['git','merge-base','--is-ancestor',HEAD_PIN,'HEAD'],cwd=ROOT).returncode==0
    prep=json.loads((prepared/'prepared.json').read_bytes())
    for path,h in prep['snapshot_sha256'].items():assert sha((prepared/path).read_bytes())==h
    pr=(ROOT/PRED/'prediction.json').read_bytes()
    assert sha(pr)==prep['prediction_sha256']
    pred=json.loads(pr)
    for key in ('source_sha256','candidate_sha256','dependency_sha256','prepared_fixture_sha256'):
        for p,h in pred[key].items():assert sha((ROOT/p).read_bytes())==h
    go=json.loads(subprocess.check_output(['git','show',GO+':'+GO_PATH],cwd=ROOT))
    assert go['prediction_sha256']==sha(pr)
    assert go['status']=='PARENT_REVIEW_PASS_BOUNDED_PRODUCER_GO'
    return prep,pred,go


def compare(log,summary,events):
    patterns={
        'block':(r'BLOCK cycle=(\d+) block=(\d+)',('cycle','block')),
        'descriptor':(r'DESCRIPTOR cycle=(\d+) op=(\d+) generation=(\d+) user=(\d+) rows=(\d+)',('cycle','op','generation','user','rows')),
        'write_ack':(r'WRITE_ACK cycle=(\d+) count=(\d+)',('cycle','count')),
        'logical_publish':(r'LOGICAL_PUBLISH cycle=(\d+)',('cycle',)),
        'request':(r'REQUEST cycle=(\d+) pc=(\d+) address=(\d+) tag=(\d+) we=(\d+) strobe=(\d+)',('cycle','pc','address','tag','we','strobe')),
        'reply':(r'REPLY cycle=(\d+) pc=(\d+) address=(\d+) tag=(\d+) op=(\d+)',('cycle','pc','address','tag','op')),
        'column':(r'COLUMN cycle=(\d+) pc=(\d+) tcol_ps=(\d+) address=(\d+) tag=(\d+) we=(\d+)',('cycle','pc','tcol_ps','address','tag','we')),
        'lifecycle_done':(r'LIFECYCLE_DONE cycle=(\d+) op=(\d+) generation=(\d+)',('cycle','op','generation'))}
    checks={};mismatches=[]
    for kind,(pattern,keys) in patterns.items():
        actual=[list(map(int,x)) for x in re.findall(pattern,log)]
        expected=[]
        for e in events:
            if e['kind']!=kind:continue
            row=dict(e)
            if kind=='write_ack':row['count']=len(expected)+1
            expected.append([int(row[k]) for k in keys])
        checks[kind]={'actual_count':len(actual),'predicted_count':len(expected),'exact':actual==expected}
        if actual!=expected:
            first=next((i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y),min(len(actual),len(expected)))
            mismatches.append(dict(kind=kind,first_index=first,actual=actual[first:first+3],predicted=expected[first:first+3]))
    actual_stage=[list(map(int,x)) for x in re.findall(r'STAGE cycle=(\d+) op=(\d+) generation=(\d+) refill=(\d+)',log)]
    expected_stage=[[c,i,i+1,summary['refill_counters'][i]] for i,c in enumerate(summary['staged_samples'])]
    checks['stage']={'actual':actual_stage,'predicted':expected_stage,'exact':actual_stage==expected_stage}
    if actual_stage!=expected_stage:mismatches.append(dict(kind='stage',actual=actual_stage,predicted=expected_stage))
    actual_pc=[list(map(int,x)) for x in re.findall(r'PC_DRAIN pc=(\d+) reads=(\d+) writes=(\d+) refreshes=(\d+) activations=(\d+) q=(\d+) r=(\d+)',log)]
    expected_pc=[[p[k] for k in ('pc','reads','writes','refreshes','activations','q','r')] for p in summary['per_PC']]
    checks['per_PC']={'exact':actual_pc==expected_pc,'actual_count':len(actual_pc)}
    if actual_pc!=expected_pc:mismatches.append(dict(kind='per_PC',actual=actual_pc,predicted=expected_pc))
    marker=re.search(r'PRODUCER_LIFECYCLE_PASS retain=(\d+) writes=(\d+) acks=(\d+) reads=(\d+) replies=(\d+) beats=(\d+) epoch=(\d+)',log)
    expected=[summary['retain'],32,32,2176*(1 if summary['retain'] else 2),2176*(1 if summary['retain'] else 2),64,summary['final_epoch']]
    actual=list(map(int,marker.groups())) if marker else None
    checks['terminal']={'actual':actual,'predicted':expected,'exact':actual==expected}
    if actual!=expected:mismatches.append(dict(kind='terminal',actual=actual,predicted=expected))
    return dict(checks=checks,mismatches=mismatches)


def execute(cmd,log,start):
    remaining=180-(time.monotonic()-start)
    if remaining<=0:return dict(status='WHOLE_RUN_TIME_CAP_NO_EXECUTION',command=cmd)
    with log.open('x') as f:
        begin=time.monotonic()
        try:code=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=remaining).returncode
        except subprocess.TimeoutExpired:code='WHOLE_RUN_TIMEOUT'
    return dict(command=cmd,status=code,wall_seconds=time.monotonic()-begin,log_sha256=sha(log.read_bytes()))


def worker(prepared,out,unit):
    start=time.monotonic();prep,pred,go=pin_check(prepared)
    cg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
    props=subprocess.check_output(['systemctl','--user','show',unit,'--property=RuntimeMaxUSec','--property=KillMode','--property=KillSignal','--property=MemoryMax','--property=MemorySwapMax','--property=CPUAffinity','--property=LimitFSIZE'],text=True)
    caps=dict(cgroup=str(cg),memory_max=(cg/'memory.max').read_text().strip(),swap_max=(cg/'memory.swap.max').read_text().strip(),
        actual_affinity=sorted(os.sched_getaffinity(0)),file_limit=list(resource.getrlimit(resource.RLIMIT_FSIZE)),service_properties=props)
    valid=(caps['memory_max']=='4294967296' and caps['swap_max']=='0' and set(caps['actual_affinity'])==CPUS and caps['file_limit']==[268435456,268435456]
           and 'RuntimeMaxUSec=3min\n' in props and 'KillMode=control-group\n' in props and 'KillSignal=9\n' in props)
    caps['verdict']='PASS_VERIFIED_BEFORE_COMPILE' if valid else 'FAIL_CAPS_NO_COMPILE_NO_FALLBACK'
    write(out/'caps_before_compile.json',caps)
    print(json.dumps({'precompile_caps':caps['verdict'],'cgroup':str(cg)}),flush=True)
    if not valid:return 2
    record=dict(schema='opentallas.window_epoch9.producer_single_cgroup_run.v1',source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        parent_go_commit=subprocess.check_output(['git','rev-parse',GO],cwd=ROOT,text=True).strip(),parent_go_path=GO_PATH,
        prediction_sha256=prep['prediction_sha256'],prepared_manifest_sha256=sha((prepared/'prepared.json').read_bytes()),caps=caps,results=[],
        scope='Two declared prepared retention cases only. No fixture/source/geometry/stimulus change, no epoch force, no7cycleguard, no retry. Model comparison not physical clock/fulltoken or QE arithmetic qualification.')
    write(out/'in_progress.json',record)
    for retain in (0,1):
        case='retain'+str(retain);cmds=prep['commands'][case]
        mdir=prepared/('obj_'+case)
        assert not mdir.exists(),'No retry or existing build directory allowed'
        comp=execute(cmds['compile'],out/(case+'_compile.log'),start)
        item=dict(case=case,compile=comp)
        record['results'].append(item);write(out/'in_progress.json',record)
        if comp['status']==0:
            item['runtime']=execute(cmds['runtime'],out/(case+'_runtime.log'),start)
            name='L0_retain' if retain else 'L0_no_retain'
            eventfile=ROOT/PRED/(name+'_events.jsonl')
            assert sha(eventfile.read_bytes())==pred['event_sha256'][name]
            events=[json.loads(x) for x in eventfile.read_text().splitlines()]
            item['comparison']=compare((out/(case+'_runtime.log')).read_text(),pred['cases'][name],events)
        write(out/'in_progress.json',record)
        print(json.dumps({'case':case,'compile_status':comp['status'],'runtime_status':item.get('runtime',{}).get('status'),'mismatches':item.get('comparison',{}).get('mismatches',[])}),flush=True)
    record['memory_peak_bytes']=int((cg/'memory.peak').read_text())
    record['memory_events']=(cg/'memory.events').read_text()
    record['whole_worker_wall_seconds']=time.monotonic()-start
    good=all(x['compile']['status']==0 and x.get('runtime',{}).get('status')==0 and not x.get('comparison',{}).get('mismatches',['absent']) for x in record['results'])
    record['verdict']='PASS_BOUNDED_ACTUAL_PRODUCER_LIFECYCLE_MODEL_VS_SOURCE' if good else 'FAIL_PRESERVED_NO_RETRY'
    write(out/'record.json',record);print(json.dumps({'verdict':record['verdict'],'peak_bytes':record['memory_peak_bytes'],'seconds':record['whole_worker_wall_seconds']}),flush=True)
    return 0 if good else 1


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepared',required=True);ap.add_argument('--out',required=True);ap.add_argument('--unit',default='w17-epoch9-producer-20261002-r1.service');ap.add_argument('--worker',action='store_true');a=ap.parse_args()
    prepared=Path(a.prepared).resolve();out=Path(a.out).resolve()
    if a.worker:return worker(prepared,out,a.unit)
    prep,pred,go=pin_check(prepared);out.mkdir(exist_ok=False)
    # One service creation and one execution of each prepared case; no retry.
    assert subprocess.run(['systemctl','--user','is-active','--quiet',a.unit]).returncode!=0
    assert all(not(prepared/('obj_retain'+str(i))).exists() for i in (0,1))
    review=subprocess.check_output(['git','show',GO+':'+GO_PATH],cwd=ROOT);(out/'parent_go.json').write_bytes(review)
    cmd=['systemd-run','--user','--unit='+a.unit,'--wait','--pipe',
        '--property=MemoryMax=4294967296','--property=MemorySwapMax=0',
        '--property=CPUAffinity=30 31','--property=RuntimeMaxSec=180',
        '--property=KillMode=control-group','--property=KillSignal=SIGKILL','--property=OOMPolicy=kill',
        '--property=LimitFSIZE=268435456','--property=LimitCORE=0','--property=Nice=10',
        '--working-directory='+str(ROOT),sys.executable,str(Path(__file__).resolve()),'--worker',
        '--prepared',str(prepared),'--out',str(out),'--unit',a.unit]
    write(out/'launch.json',dict(command=cmd,source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),no_fallback=True))
    with (out/'service.log').open('x') as f:status=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
    write(out/'service_receipt.json',dict(returncode=status,record_exists=(out/'record.json').exists(),caps_verified=(out/'caps_before_compile.json').exists(),
        service_state=subprocess.check_output(['systemctl','--user','show',a.unit,'--property=Result','--property=ExecMainStatus','--property=MemoryPeak','--property=ActiveState'],text=True)))
    print((out/'record.json').read_text() if (out/'record.json').exists() else (out/'service.log').read_text())
    return status
if __name__=='__main__':raise SystemExit(main())
