#!/usr/bin/env python3
"""Minimum full64x8 bank correctness gate with negative controls."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/hbm_accel/result_delay_bank_20261007/ot_hbm_result_delay_bank.sv'
TB=RTL.with_name('tb_result_delay_bank.sv')


def run(out):
    source=RTL.read_text()
    cases={'baseline':source,
        'reject_short_latency':source.replace('assign q = pipe[STAGES-1];','assign q = pipe[STAGES-2];'),
        'reject_synchronous_reset':source.replace('posedge clk or negedge rst_n','posedge clk'),
        'reject_data_corruption':source.replace('pipe[0] <= d;','pipe[0] <= d ^ 1;')}
    records={}
    with tempfile.TemporaryDirectory(prefix='hbm-delay-bank-') as tmp:
        for name,text in cases.items():
            p=Path(tmp)/f'{name}.sv';p.write_text(text);exe=Path(tmp)/f'{name}.vvp'
            build=subprocess.run(['iverilog','-g2012','-s','tb_result_delay_bank','-o',str(exe),str(p),str(TB)],capture_output=True,text=True)
            if build.returncode:raise RuntimeError(build.stderr)
            sim=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
            records[name]=dict(returncode=sim.returncode,stdout=sim.stdout,stderr=sim.stderr,
                source_sha256=hashlib.sha256(text.encode()).hexdigest())
    passed=records['baseline']['returncode']==0 and all(v['returncode']!=0 for k,v in records.items() if k!='baseline')
    if not passed:raise RuntimeError(records)
    result=dict(status='COMPONENT_EXACTNESS_PASS_PHYSICAL_OPEN',full_shape=dict(bits=64,stages=8,flop_bits=512),
        baseline_checks=2048,captures=1024,asynchronous_reset_checks=4,
        mutant_rejections=3,selected=False,records=records,
        model_sha256=hashlib.sha256((ROOT/'results/uarch/hbm_result_delay_bank_20261007/model.json').read_bytes()).hexdigest(),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [RTL,TB,Path(__file__)]},
        physical_gate='No technology mapping, fixed BPin view, clock load, full physical placement or SS/FF qualification yet')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],checks=2048,mutants=3)))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True)
    run(ap.parse_args().out)
