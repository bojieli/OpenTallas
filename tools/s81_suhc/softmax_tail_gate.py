#!/usr/bin/env python3
"""Exact actual-RTL T=133 physical softmax lane check, including disabled-mask mutant."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import hdc_golden_v41 as V
import hc_gate as H
import su_gate as S

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--physical-wrapper',action='store_true');p.add_argument('--pin-wrapper',type=Path);p.add_argument('--check-pin-age',action='store_true');p.add_argument('--only',choices=['both','positive','mutant'],default='both')
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(1014133)
    x=np.full(144,-np.inf,np.float32);x[:133]=rng.uniform(-20,1,133).astype(np.float32);x[0]=1
    e=np.zeros(144,np.float32);e[:133]=V.exp(V.add(x[:133],np.float32(-1)))
    for n,d in [('scores',x),('expected',e)]:
        (a.out/(n+'.mem')).write_text(''.join(f'{b:08x}\n' for b in d.view(np.uint32)))
    lane=ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv'
    tb=ROOT/'rtl/dsrom_sys/s81_suhc/test/tb_s81_su_softmax_tail.sv'
    wrapper=ROOT/'rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_sm.sv'
    actual_tb=a.out/'tb_actual_tail.sv'
    tbtext=tb.read_text()
    if a.physical_wrapper:
        tbtext=tbtext.replace('ot_s81_su_sml dut(.clk(clk), .rst_in(rst)', 'dsfd_su_t_sml dut(.ck(clk), .rst(rst)')
    if a.check_pin_age:
        assert a.pin_wrapper, '--check-pin-age requires exact --pin-wrapper'
        age = """
    wire b_mxv,b_ev,b_es,b_el;wire[31:0]b_mx,b_e;
    dsfd_su_t_sml__ot_pr_core baseline(.ck(clk),.rst(rst),.sk_en(1'b0),
        .i_cv(cv),.i_nv(7'd9),.i_scale(32'h3f800000),.i_sink(32'd0),
        .i_sv(sv),.i_s(sd),.i_mv(mv),.i_nmb(32'hbf800000),
        .o_mxv(b_mxv),.o_mx(b_mx),.o_ev(b_ev),.o_es(b_es),.o_el(b_el),.o_e(b_e));
    reg[67:0]age0,age1;integer agewarm=0,agechecks=0;
    always @(posedge clk) begin
        age0<={b_mxv,b_mx,b_ev,b_es,b_el,b_e};age1<=age0;
        if(!rst)agewarm<=0;else agewarm<=agewarm+1;
    end
    always @(negedge clk) if(rst && agewarm>8) begin
        agechecks=agechecks+1;
        if(mxv!==age1[67] || ev!==age1[34])begin
            $display("PIN_AGE valid mismatch cycle=%0d",agewarm);bad=bad+1;
        end
        if(mxv && mx!==age1[66:35])begin $display("PIN_AGE mx mismatch");bad=bad+1;end
        if(ev && {es,el,ed}!==age1[33:0])begin $display("PIN_AGE exp mismatch");bad=bad+1;end
    end
"""
        tbtext=tbtext.replace('    reg [31:0] scores',age+'    reg [31:0] scores')
        tbtext=tbtext.replace('$display("TAIL checked=144 bad=%0d",bad);','$display("PIN_AGE exact_edges=2 checked_cycles=%0d",agechecks);\n        $display("TAIL checked=144 bad=%0d",bad);')
    actual_tb.write_text(tbtext)
    if a.pin_wrapper:
        assert a.physical_wrapper, '--pin-wrapper requires --physical-wrapper'
        routed_wrapper=a.pin_wrapper.resolve()
        physical_core=a.out/'physical_core.sv'
        txt=wrapper.read_text();assert txt.count('module dsfd_su_t_sml (')==1
        physical_core.write_text(txt.replace('module dsfd_su_t_sml (','module dsfd_su_t_sml__ot_pr_core ('))
    results=[]
    for mutant in ((False,True) if a.only=='both' else (a.only=='mutant',)):
        src=a.out/('mutant.sv' if mutant else 'lane.sv')
        txt=lane.read_text()
        if mutant:
            assert txt.count("inactive[LA + D_EXP] ? 32'd0 : be")==1
            txt=txt.replace("inactive[LA + D_EXP] ? 32'd0 : be",'be')
        src.write_text(txt)
        obj=a.out/('obj_mut' if mutant else 'obj')
        paths=list(dict.fromkeys(H.FP['rtl']+S.RTL))
        if a.physical_wrapper and not a.pin_wrapper:paths.append(str(wrapper.relative_to(ROOT)))
        cmd=[H.VERILATOR,'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_su_softmax_tail',
             '-Mdir',str(obj),'-j','8',*map(str,[ROOT/s for s in paths]),str(src),str(actual_tb),*([str(physical_core),str(routed_wrapper)] if a.pin_wrapper else [])]
        b=subprocess.run(cmd,capture_output=True,text=True)
        (a.out/('build_mut.log' if mutant else 'build.log')).write_text(b.stdout+b.stderr)
        if b.returncode: raise RuntimeError('build failed: '+str(a.out))
        r=subprocess.run([str(obj/'Vtb_s81_su_softmax_tail')],cwd=a.out,capture_output=True,text=True)
        (a.out/('mutant.log' if mutant else 'run.log')).write_text(r.stdout+r.stderr)
        ok=('TAIL PASS' in r.stdout and r.returncode==0)
        results.append(dict(mutant=mutant,ok=ok,returncode=r.returncode))
        print(results[-1],flush=True)
    record=dict(schema='opentallas.s81_su.tail.v1',results=results,
        dut='dsfd_su_t_sml' if a.physical_wrapper else 'ot_s81_su_sml',positions=133,vector_beats=9,capacity_beats=40,capacity_positions=640,inactive_tail_positions=11,generated_tb_sha256=H.sha(actual_tb),pin_age_exact_checked=a.check_pin_age,pin_registers={'input_edges':1,'output_edges':1,'wrapper_sha256':H.sha(routed_wrapper),'core_sha256':H.sha(physical_core)} if a.pin_wrapper else None,
        status=('pass' if results[0]['ok'] and not results[1]['ok'] else 'fail') if a.only=='both' else ('pass' if results[0]['ok'] else 'fail'),fp='real RTL, no DPI',
        source_sha256={str(s.relative_to(ROOT)):H.sha(s) for s in [lane,tb]+[ROOT/s for s in paths]})
    (a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    return int(record['status']!='pass')
if __name__=='__main__':sys.exit(main())
