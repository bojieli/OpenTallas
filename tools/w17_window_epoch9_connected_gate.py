#!/usr/bin/env python3
"""Bounded connected candidate test, against an already committed prediction."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
PRED='results/uarch/w17_window_epoch9_timing_prediction_20261001_attempt1/prediction.json'
TRACE='results/uarch/w17_window_epoch9_timing_prediction_20261001_attempt1/credit8_events.jsonl'
BENCH='rtl/test/w17_window_epoch9_connected/tb.sv'
COPIES='rtl/test/w17_window_epoch9_candidate/'


def sha(b):return hashlib.sha256(b).hexdigest()
def limits():
    os.nice(10)
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[-2:]))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(180,180))
    resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024**2,256*1024**2))


def run(cmd,log,remaining):
    begin=time.monotonic()
    with log.open('x') as f:
        try:
            result=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=max(1,remaining),preexec_fn=limits)
            status=result.returncode
        except subprocess.TimeoutExpired:status='WALL_TIMEOUT'
    return dict(command=cmd,status=status,wall_seconds=time.monotonic()-begin,log_sha256=sha(log.read_bytes()))


def compare(log,pred,events):
    errors=[]
    match=re.search(r'CONNECTED_EPOCH9_PASS start=(\d+) staged=(\d+) done=(\d+) refill=(\d+) reads=(\d+) replies=(\d+) beats=(\d+) max_inflight=(\d+)',log)
    metrics=dict(zip(('start','staged','done','refill','reads','replies','beats','max_inflight'),map(int,match.groups()))) if match else None
    if metrics!=pred['arms']['8']['metrics']:errors.append(dict(kind='metrics',expected=pred['arms']['8']['metrics'],actual=metrics))
    traces={}
    for kind,pattern in (
        ('client_request',r'CLIENT_REQUEST cycle=(\d+) addr=([0-9a-f]+) tag=([0-9a-f]+)'),
        ('client_reply',r'CLIENT_REPLY cycle=(\d+) tag=([0-9a-f]+)'),
        ('backend_request',r'BACKEND_REQUEST cycle=(\d+) pc=(\d+) addr=([0-9a-f]+) tag=([0-9a-f]+)'),
        ('backend_reply',r'BACKEND_REPLY cycle=(\d+) pc=(\d+) tag=([0-9a-f]+)')):
        actual=[]
        for fields in re.findall(pattern,log):
            if kind=='client_request':actual.append([int(fields[0]),int(fields[1],16),int(fields[2],16)])
            elif kind=='client_reply':actual.append([int(fields[0]),int(fields[1],16)])
            elif kind=='backend_request':actual.append([int(fields[0]),int(fields[1]),int(fields[2],16),int(fields[3],16)])
            else:actual.append([int(fields[0]),int(fields[1]),int(fields[2],16)])
        expected=[]
        for e in events:
            if e['kind']!=('request' if kind.endswith('request') else 'reply'):continue
            if kind=='client_request':expected.append([e['cycle'],e['address'],e['tag']&65535])
            elif kind=='client_reply':expected.append([e['cycle'],e['tag']&65535])
            elif kind=='backend_request':expected.append([e['cycle'],e['pc'],e['address'],e['tag']])
            else:expected.append([e['cycle'],e['pc'],e['tag']])
        traces[kind]=dict(expected_count=len(expected),actual_count=len(actual),byte_exact_numeric_events=actual==expected)
        if actual!=expected:
            first=next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),min(len(actual),len(expected)))
            errors.append(dict(kind=kind,first_mismatch=first,actual=actual[first:first+2],expected=expected[first:first+2]))
    drains={int(p):(int(rd),int(q),int(r),int(ref),int(act)) for p,rd,q,r,ref,act in re.findall(r'PC_DRAIN pc=(\d+) reads=(\d+) q=(\d+) r=(\d+) refreshes=(\d+) activations=(\d+)',log)}
    for p in pred['arms']['8']['per_PC']:
        expected=(p['reads'],p['q'],p['r'],p['refreshes'],p['activations'])
        if drains.get(p['pc'])!=expected:errors.append(dict(kind='PC'+str(p['pc']),expected=expected,actual=drains.get(p['pc'])))
    return dict(metrics=metrics,event_checks=traces,drained_PC_count=len(drains),mismatches=errors)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);args=ap.parse_args()
    # Require committed clean sources and committed prediction BEFORE compiling.
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    pr=(ROOT/PRED).read_bytes();pred=json.loads(pr)
    assert pred['verdict']=='READY_PREDICTION_BEFORE_CANDIDATE_MEASUREMENT'
    committed=subprocess.check_output(['git','show','HEAD:'+PRED],cwd=ROOT);assert committed==pr
    eraw=(ROOT/TRACE).read_bytes();assert sha(eraw)==pred['event_sha256']['credit8']
    events=[json.loads(x) for x in eraw.decode().splitlines()]
    paths=list(pred['source_sha256'])
    selected=[]
    for p in paths:
        raw=subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT)
        assert sha(raw)==pred['source_sha256'][p] and (ROOT/p).read_bytes()==raw
        cp=COPIES+Path(p).name if Path(p).name in ('ot_chip_v41x_window_attn_source.sv','ot_chip_v41x_window_kv_prefetch.sv') else p
        if cp!=p:assert sha((ROOT/cp).read_bytes())==pred['candidate_added_sha256'][cp]
        selected.append(cp)
    out=Path(args.out).resolve();assert shutil.disk_usage(out.parent).free>1024**3
    out.mkdir(exist_ok=False);snapshot=out/'source';snapshot.mkdir()
    for p in selected:(snapshot/Path(p).name).write_bytes((ROOT/p).read_bytes())
    (snapshot/'tb.sv').write_bytes((ROOT/BENCH).read_bytes())
    baseline=json.loads((ROOT/'results/uarch/w17_window_epoch9_baseline_comparison_20261001/baseline_record.json').read_bytes())
    verilator=baseline['compile']['command'][0]
    cmd=[verilator,'--binary','--timing','--build','-j','2','-Wno-fatal','-Wno-WIDTH','-Wno-PINMISSING','--top-module','tb','-GMEM_MODE=0','--Mdir',str(out/'obj'),*[str(snapshot/Path(p).name) for p in selected],str(snapshot/'tb.sv')]
    record=dict(schema='opentallas.window_epoch9.connected_gate.v1',source_commit=PIN,
        branch_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        prediction_commit=subprocess.check_output(['git','log','-1','--format=%H','--',PRED],cwd=ROOT,text=True).strip(),
        prediction_sha256=sha(pr),event_prediction_sha256=sha(eraw),
        selected_source_sha256={p:sha((ROOT/p).read_bytes()) for p in selected},bench_sha256=sha((ROOT/BENCH).read_bytes()),
        caps=dict(workers=2,address_space_bytes=4*1024**3,total_wall_seconds=180,max_cycles=200000,generated_file_bytes=256*1024**2),
        preflight=pred['preflight'],parent_coordination=dict(thread='01a0f95d-badc-74d3-bde3-f3eb28f089b8',queue_message='01a0f9c8-89f2-7113-845f-9026422df9d1',baseline_fixture_untouched=True),
        scope='Actual idx_hbm timing, same reset/start, explicit LENW4 BEATW4 TAG17 NPC32 REFPB3 CLK_PS1000; MEM_MODE0 fulladdress generated nonpoison2176sectors and128primeAPI rows, no competitors. No actual producer, checkpoint/fulltoken/physicalclock or adoption.',
        prior_negative='Original epoch512 rejection and prior stage-edge model failure retained in separate records; no tune-to-fit.',
        baseline_refill=124368,predicted_candidate_refill=20601)
    begin=time.monotonic();record['compile']=run(cmd,out/'compile.log',180)
    if record['compile']['status']==0:
        record['runtime']=run([str(out/'obj/Vtb')],out/'runtime.log',180-(time.monotonic()-begin))
        record['comparison']=compare((out/'runtime.log').read_text(),pred,events)
        good=record['runtime']['status']==0 and not record['comparison']['mismatches']
    else:good=False
    record['total_wall_seconds']=time.monotonic()-begin
    record['verdict']='PASS_BOUNDED_CONNECTED_MODEL_VS_SOURCE' if good else 'FAIL_PRESERVED_MODEL_OR_FIXTURE_MISMATCH'
    if good:
        record['conditional_refill_saved_cycles']=124368-20601
        record['conditional_refill_reduction_fraction']=(124368-20601)/124368
    (out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(verdict=record['verdict'],comparison=record.get('comparison'),seconds=record['total_wall_seconds']),indent=2))
    return not good
if __name__=='__main__':raise SystemExit(main())
