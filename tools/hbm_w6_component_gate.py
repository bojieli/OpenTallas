#!/usr/bin/env python3
"""Pinned short local W6 component gate, no wall/FSIZE/AS/memory caps.

This instantiates no caller, CDC queue, RF macro or production drain producer.
It cannot admit the composed parent or establish SS/FF/physical closure.
"""
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
MODEL_DIR=ROOT/'results/uarch/hbm_W6_local_RTL_20261003/model_r1'
PROPOSAL=MODEL_DIR/'component_proposal.json'
RTL=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
     'rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv',
     'rtl/test/w6/tb_w6_fullwidth_fence.sv']
ORDER=['req','host_ack','visible','consumer','child_reverse','parent_reverse',
       'reverse_CDC','drain_req','drain_rsp','retire']

def require(ok,message):
    if not ok: raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def write_new(path,data):
    with Path(path).open('x') as f:
        json.dump(data,f,sort_keys=True,indent=2);f.write('\n')

def verify_trace(log):
    marker=re.findall(r'^PASS_W6_LOCAL_COMPONENT checks=(\d+) accepted=(\d+) raw=71 protected=144 production_alldrain=0 physical=0$',log,re.M)
    require(len(marker)==1,'exact component terminal required')
    require('W6_CHECK_FAIL' not in log and 'FATAL' not in log,'bench assertion failure')
    traces={1:[],2:[],3:[]}
    for case,kind,edge,identity in re.findall(r'^W6_EDGE case=(\d+) kind=(\w+) edge=(\d+) identity=([0-9a-f]{14})$',log,re.M):
        if int(case) in traces: traces[int(case)].append(dict(kind=kind,edge=int(edge),identity=int(identity,16)))
    summaries=[]
    for case,rows in traces.items():
        order=ORDER.copy()
        if case==2: order[1]='simd_ack_retire'
        require([r['kind'] for r in rows]==order,'exact ordered once-only C0/KV chain')
        identities={r['identity'] for r in rows}
        require(len(identities)==1,'full identity constant at every boundary')
        identity=identities.pop()
        expected=(127<<48)|((5 if case==2 else 0)<<45)|(0xfe123456<<13)|((15 if case==1 else 0)<<9)|511
        require(identity==expected,'full PC/client/tag/generation/slot preserved')
        deltas=[b['edge']-a['edge'] for a,b in zip(rows,rows[1:])]
        require(all(d>= (3 if b['kind']=='reverse_CDC' else 2) for d,b in zip(deltas,rows[1:])),'positive modeled boundary edges')
        summaries.append(dict(case=case,identity=identity,handshakes=rows,edge_deltas=deltas,
                              ACK_to_retire_edges=rows[-1]['edge']-rows[1]['edge']))
    require(traces[2][0]['edge']-traces[1][-1]['edge']>=2,'retirement before drained generation wrap')
    require(traces[3][0]['edge']-traces[1][-1]['edge']>=2,'same-client gen15 to0 after matched drain and retirement')
    require(int(marker[0][0])>=400,'mutant and protection assertions covered')
    return dict(verdict='PASS_LOCAL_C0_KV_FULLWIDTH_CONTROL_ONLY',checks=int(marker[0][0]),
                accepted=int(marker[0][1]),paths=summaries,
                numerical_payload=False,production_alldrain=False,physical=False)

def preflight(proposal,source_commit,cpu):
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==source_commit,'exact clean source commit')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'clean pinned worktree')
    require(subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='main','isolated branch')
    for path,digest in proposal['source_sha256'].items(): require(sha(ROOT/path)==digest,'source pin '+path)
    for path,digest in proposal['tool_sha256'].items(): require(sha(path)==digest,'tool pin '+path)
    require(cpu in os.sched_getaffinity(0),'requested CPU allowed by kernel')
    limits={}
    for name,key in [('CPU',resource.RLIMIT_CPU),('FSIZE',resource.RLIMIT_FSIZE),('AS',resource.RLIMIT_AS)]:
        soft,hard=resource.getrlimit(key);require(soft==resource.RLIM_INFINITY and hard==resource.RLIM_INFINITY,'unlimited '+name)
        limits[name]=[soft,hard]
    mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemAvailable','MemTotal')}
    disk=shutil.disk_usage('/tmp')
    # Fair-share short static test; reservations are estimates, never hard limits.
    require(mem['MemAvailable']>proposal['admission']['estimated_memory_bytes'],'measured memory headroom')
    require(disk.free>proposal['admission']['estimated_output_bytes']+proposal['admission']['retained_disk_headroom_bytes'],'measured disk headroom')
    os.sched_setaffinity(0,{cpu}); require(os.sched_getaffinity(0)=={cpu},'kernel affinity enforced')
    os.nice(10)
    return dict(source_commit=source_commit,proposal_sha256=sha(PROPOSAL),source_root=str(ROOT),
                runner_pid=os.getpid(),runner_startticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
                kernel_affinity=sorted(os.sched_getaffinity(0)),inherited_child_affinity=True,
                resource_limits=limits,meminfo=mem,disk_free=disk.free,
                memory_limit_set=False,swap_limit_set=False,wall_deadline=None,
                CPU_time_limit=None,FSIZE_limit=None,AS_limit=None,
                admission='parent authorized short static component simulation, fair-share one CPU; no heavy build',
                schema='W6_COMPONENT_RUNTIME_PREFLIGHT_V1')

def execute(out,source_commit,cpu):
    out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();verdict=dict(verdict='FAIL_INCOMPLETE_LOCAL_COMPONENT',source_commit=source_commit,
                                      production_alldrain=False,physical=False)
    try:
        proposal=json.loads(PROPOSAL.read_text());receipt=preflight(proposal,source_commit,cpu)
        write_new(out/'preflight.json',receipt)
        commands=[('compile',['/usr/bin/iverilog','-g2012','-Wall','-s','tb_w6_fullwidth_fence','-o',str(out/'component.vvp')]+[str(ROOT/p) for p in RTL]),
                  ('simulation',['/usr/bin/vvp',str(out/'component.vvp')])]
        for phase,argv in commands:
            began=time.monotonic()
            with (out/(phase+'.log')).open('xb') as log:
                child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                write_new(out/(phase+'-start.json'),dict(argv=argv,pid=child.pid,source_commit=source_commit,
                           inherited_kernel_affinity=sorted(os.sched_getaffinity(0)),wall_limit=None))
                rc=child.wait()  # No arbitrary elapsed timeout or per-process caps.
            write_new(out/(phase+'-end.json'),dict(returncode=rc,wall_seconds=time.monotonic()-began,
                       log_sha256=sha(out/(phase+'.log'))))
            require(rc==0,phase+' failed; preserve complete raw log')
        checked=verify_trace((out/'simulation.log').read_text());write_new(out/'trace_review.json',checked)
        verdict.update(verdict='PASS_W6_LOCAL_COMPONENT_ONLY',checks=checked['checks'],
                       compiled_binary_sha256=sha(out/'component.vvp'),
                       source_sha256=proposal['source_sha256'],tool_sha256=proposal['tool_sha256'])
    except Exception as exc:
        verdict['failure']=str(exc)
    verdict['wall_seconds']=time.monotonic()-start
    write_new(out/'verdict.json',verdict)
    return 0 if verdict['verdict']=='PASS_W6_LOCAL_COMPONENT_ONLY' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-commit',required=True);p.add_argument('--cpu',type=int,default=2)
    a=p.parse_args();raise SystemExit(execute(a.out,a.source_commit,a.cpu))
