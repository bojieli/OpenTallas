#!/usr/bin/env python3
"""Production SW64 embedding-prefetch + stream-control acceptance gate.
Lane arithmetic is isolated; this is not the whole-SU or whole-token exact gate.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile
from emit_su_accept import emit, BASE
ROOT=Path(__file__).resolve().parents[2]

def run(out):
    rtl=ROOT/'rtl/qwen_sys/redesign_qwen/ot_qfd_su_master_bv_acc.sv'
    source=rtl.read_text()
    assert source==emit(), "successor differs beyond the6 count/interface changes allowed by emitter"
    mutants={
        'premature_go_q':('else if (go_s && s_ready)','else if (go_q)'),
        'ignores_ready':('else if (go_s && s_ready)','else if (go_s)'),
        'wrong_epoch':("if (!rs) accepted_count <= 24'd0;","if (!rs) accepted_count <= accepted_count;"),
        'status_pipeline':('.W(FS), .D(OS), .RESET(1)) u_os','.W(FS), .D(OS+1), .RESET(1)) u_os'),
    }
    paths=[ROOT/'tests/rtl/qwen_seq_boundary/tb_endpoint.sv',rtl,
           ROOT/'rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv',
           ROOT/'rtl/hdc/ot_hdc_vstream.sv',ROOT/'rtl/hdc/ot_hdc_delay.sv']
    sm=(ROOT/'rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv').read_text()
    start=sm.index('module ot_qfd_rst_stn');reset=sm[start:sm.index('endmodule',start)+len('endmodule')]
    cases=[]
    with tempfile.TemporaryDirectory(prefix='qwen-endpoint-accept-') as scratch:
        work=Path(scratch);(work/'rst.sv').write_text(reset)
        runs=[('baseline',i,o,source,True) for i,o in ((0,0),(1,1),(1,2),(2,1),(2,2))]
        for name,(before,after) in mutants.items():
            assert source.count(before)==1
            runs.append((name,1,1,source.replace(before,after),False))
        for name,i,o,text,expected in runs:
            (work/'dut.sv').write_text(text)
            cmd=['iverilog','-g2012','-i','-s','tb_endpoint',f'-Ptb_endpoint.IS={i}',f'-Ptb_endpoint.OS={o}',
                 '-o',str(work/'tb'),str(paths[0]),str(work/'dut.sv')]+list(map(str,paths[2:]))+[str(work/'rst.sv')]
            build=subprocess.run(cmd,capture_output=True,text=True)
            if build.returncode:raise RuntimeError(build.stderr)
            sim=subprocess.run(['vvp',str(work/'tb')],capture_output=True,text=True)
            passed=sim.returncode==0 and 'PASS endpoint' in sim.stdout
            record=dict(case=name,IS=i,OS=o,expected_pass=expected,observed_pass=passed,exit_code=sim.returncode,
                        stdout=sim.stdout,stderr=sim.stderr,source_sha256=hashlib.sha256(text.encode()).hexdigest())
            cases.append(record)
            if passed!=expected:raise RuntimeError(json.dumps(record))
    payload=dict(schema='opentallas.qwen-su-endpoint-accept-gate.v1',verdict='PASS',
        shape='SW64 production, actual embedding-prefetch and vstream acceptance/control FSM',
        isolated='lane arithmetic and lane retirement datapath; fixed3-edge retirement events supplied',
        unsupported_claims=['whole-SU arithmetic exactness','full-token exactness','physical closure'],
        files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[BASE]},cases=cases)
    if out:out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,indent=2)+'\n')
    print('PASS endpoint acceptance:5 pipeline shapes;4 mutants detected; production64-lane control')
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path);run(ap.parse_args().out)
