#!/usr/bin/env python3
"""Immutable connected RTL gate; synthetic memory timing is not full-token or clock sign-off."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
FILES=["rtl/gpu/ot_gpu_issue.sv","rtl/gpu/ot_gpu_bulk_copy.sv",
       "rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv",
       "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv",
       "rtl/hbm_accel/epilogue/tb_hbm_accel_clock_loops.sv"]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--origin-commit',help='Full commit of byte-identical git archive deployed to clean run worktree')
    a=ap.parse_args()
    if a.out.exists(): raise SystemExit('Existing verdict retained; choose new run path')
    a.work.mkdir(parents=True,exist_ok=False)
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES+[__file__.replace(str(ROOT)+'/', ''),'tools/hbm_accel_epilogue_model.py','tools/hbm_accel_epilogue_compile.py']}
    r=dict(schema='opentallas.hbm_accel.ha3.clock_gate.v1', origin_commit=a.origin_commit, source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           input_sha256=pins,host=socket.gethostname(),run_pid=os.getpid(),status='FAIL',cases=[],
           exact=dict(scope='Accepted issue identity/order, weights, credit/data hold; synthetic connected SM issue+bulk service',mismatches=0),
           physical=dict(ss_wns_ns=None,ff_wns_ns=None,area_mm2=None,route='NOT_RUN',setup_uncertainty_ps=60,hold_uncertainty_ps=25),
           serial_system_latency='UNMEASURED: no actual SM/RF/HA2 endpoint/CDC/refresh integration',
           arithmetic_golden='NOT_RUN: prior nonfinite and wide-overflow FAILED gates retained',
           composed_gain=None,adopt=False,decision='HOLD: protocol fixture alone cannot authorize adoption',
           price=dict(issue_setup_cycles=1,iteration_cycles=0,bulk_head_fill_cycles=1,initiation_interval=1,source='price_before_rtl.json'),
           simulator=subprocess.check_output(['iverilog','-V'],stderr=subprocess.STDOUT,text=True).splitlines()[0])
    t=time.monotonic()
    try:
        for sram in (0,1):
            binary=a.work/f'sim{sram}'
            cmd=['iverilog','-g2012','-s','tb_hbm_accel_clock_loops',f'-Ptb_hbm_accel_clock_loops.SRAM={sram}','-o',str(binary)]+[str(ROOT/f) for f in FILES]
            build=subprocess.run(cmd,capture_output=True,text=True)
            (a.work/f'build{sram}.log').write_text(build.stdout+build.stderr)
            if build.returncode: raise RuntimeError('Icarus build failed')
            for rows,c,g in ((1,1,1),(2,3,5),(7,3,5),(8,1,1),(9,3,5),(17,3,5),(43,3,5),(384,1,3),(4095,1,1)):
                for gs in (0,1):
                    for stress in (0,1,2) if rows==43 else (1,) if rows>384 else (0,1):
                        name=f'sram{sram}_r{rows}_c{c}_g{g}_gs{gs}_stress{stress}'
                        cmd=[str(binary)]
                        p=subprocess.run(['vvp',*cmd,f'+ROWS={rows}',f'+C={c}',f'+G={g}',f'+GS={gs}',f'+STRESS={stress}'],capture_output=True,text=True)
                        (a.work/f'{name}.log').write_text(p.stdout+p.stderr)
                        traces={n:re.findall(r'^TRACE '+str(n)+r' (.*)$',p.stdout,re.M) for n in (0,1)}
                        done=re.findall(r'DONE enable=(\d) cycles=(\d+) first=(\d+) lines=(\d+) events=(\d+) max_streak=(\d+)',p.stdout)
                        mismatch=sum(x!=y for x,y in zip(traces[0],traces[1]))+abs(len(traces[0])-len(traces[1]))
                        r['exact']['mismatches']+=mismatch
                        case=dict(name=name,returncode=p.returncode,mismatches=mismatch,done={})
                        for n,cycles,first,lines,events,streak in done:
                            case['done'][n]=dict(cycles=int(cycles),first=int(first),lines=int(lines),events=int(events),max_streak=int(streak))
                        r['cases'].append(case)
                        if p.returncode or mismatch or len(done)!=2 or 'PASS connected' not in p.stdout: raise RuntimeError(f'{name}: connected differential failure')
                        b,n=case['done']['0'],case['done']['1']
                        case['delta_cycles']=n['cycles']-b['cycles']
                        case['delta_first_cycles']=n['first']-b['first']
                        case['nominal_delta_ns_at_1p2GHz']=case['delta_cycles']/1.2
                        print(name,case['delta_cycles'],flush=True)
        if pins!={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins}: raise RuntimeError('source drift')
        r['status']='PASS_PROTOCOL_FIXTURE'
        r['exact']['cases']=len(r['cases'])
        r['measured']=dict(cycle_delta_min=min(c['delta_cycles'] for c in r['cases']),cycle_delta_max=max(c['delta_cycles'] for c in r['cases']),
             max_issue_streak=max(c['done']['1']['max_streak'] for c in r['cases']),
             price_delta='Setup/phase costs measured per fixture; full-token composition remains unknown')
    except Exception as e:r['error']=str(e)
    r['elapsed_seconds']=time.monotonic()-t
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(r['status'],r.get('error',''),flush=True)
    return 0 if r['status']=='PASS_PROTOCOL_FIXTURE' else 1


if __name__=='__main__':raise SystemExit(main())
