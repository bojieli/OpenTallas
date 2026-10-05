#!/usr/bin/env python3
"""Bounded unchanged source/mux/arbiter/timed-backend verification, not a token gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
NAMES=['attn_row_merge','window_attn_source','window_kv_prefetch','window_refill_schedule',
       'window_row_codec','window_stage4','window_stream','window_retention','kv_reqmux','kv_rope_reqmux','hbm_karb']
PATHS=['rtl/chip/ot_chip_v41x_'+n+'.sv' for n in NAMES]+['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv']
BENCH='rtl/test/w17_window_connected_baseline/tb.sv'
def digest(b):return hashlib.sha256(b).hexdigest()
def cap():
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
def command(cmd,log,timeout):
    start=time.monotonic()
    with log.open('x') as f:
        p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=cap)
        try:rc=p.wait(timeout=timeout);timed_out=False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);rc=p.wait();timed_out=True
    return dict(command=cmd,returncode=rc,timed_out=timed_out,elapsed_seconds=time.monotonic()-start,
                log=str(log),log_sha256=digest(log.read_bytes()))
def run(out,mode):
    out.mkdir(parents=True,exist_ok=False)
    src=out/'source';src.mkdir()
    pins={}
    for name in PATHS:
        raw=subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)
        p=src/Path(name).name;p.write_bytes(raw);pins[name]=digest(raw)
    manifest=json.loads(subprocess.check_output(['git','show','e72abea5a:results/rtl/w17_connected_token_preparation_20261001/L0_cli_recovery_launch.json'],cwd=ROOT))
    assert all(manifest['source_sha256'][n]==v for n,v in pins.items())
    record=dict(schema='opentallas.window_connected_baseline_verification.v1',source_commit=SOURCE,source_sha256=pins,
                bench_sha256=digest((ROOT/BENCH).read_bytes()),tool_sha256=digest(Path(__file__).read_bytes()),
                status='PREPARED',constraints=dict(compile_workers=2,address_space_bytes=4*1024**3,
                    compile_timeout_seconds=180,simulation_timeout_seconds=180,maximum_cycles=200000),
                geometry=dict(rows=128,sectors_per_row=17,base_sector=262144,user=0,first_row=0,
                    source_credits=1,owner_mux_TAGW=16,backend_TAGW=17,NPC=32,REFPB=3,CLK_PS=1000,
                    MEM_MODE=mode,MEM_WORDS=264320,primed_historical_rows=128),
                composed_model_scope=dict(existing_source=True,stage_payload_bits=540672,
                    source_compat_upper_declared_bits=606718,source_reference='d36550dca:model_r2.json',
                    issue_ports=1,return_ports=1,source_row_scale_barrier=True,source_clock_crossing=False,
                    cold_no_competitors=True,finite_latency_measurement_pending=True),
                limits=['No physical clock qualification','No payload capacity or checkpoint values',
                    'No write/CKV/RoPE/index competitors','No full-token or engine completion qualification',
                    'One source-controlled cold event state, not a universal bound','No credit-eight adoption',
                    'Historical-row fixture primes provenance through source API; no actual producer-write qualification'],
                hardware_admission=False,live_sources_modified=False,headline_rate=None)
    (out/'preflight.json').write_text(json.dumps(record,indent=2)+'\n')
    try:
        exe=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
        cmd=[str(exe),'--binary','--timing','--build','-j','2','-Wno-fatal','-Wno-WIDTH',
             '-Wno-PINMISSING','--top-module','tb',f'-GMEM_MODE={mode}','--Mdir',str(out/'obj'),
             *[str(src/Path(n).name) for n in PATHS],str(ROOT/BENCH)]
        record['compile']=command(cmd,out/'compile.log',180)
        if record['compile']['returncode']:raise RuntimeError('compile failed')
        record['simulation']=command([str(out/'obj/Vtb')],out/'runtime.log',180)
        if record['simulation']['returncode']:raise RuntimeError('simulation failed')
        text=(out/'runtime.log').read_text()
        lines=[s for s in text.splitlines() if s.startswith('CONNECTED_WINDOW_PASS ')]
        if len(lines)!=1:raise RuntimeError('missing single terminal marker')
        metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',lines[0])}
        assert metrics['reads']==metrics['replies']==2176 and metrics['beats']==32 and metrics['max_inflight']==1
        assert metrics['start']<metrics['staged']<metrics['done']
        record.update(status='PASS_BOUNDED_CONNECTED_BASELINE',metrics=metrics)
    except Exception as e:
        record.update(status='FAIL',error=str(e))
    finally:
        (out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',type=int,choices=[0,1],default=0);a=p.parse_args()
    r=run(a.out.resolve(),a.mode);print(r['status']);raise SystemExit(0 if r['status']=='PASS_BOUNDED_CONNECTED_BASELINE' else 1)
