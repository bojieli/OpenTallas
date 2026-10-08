#!/usr/bin/env python3
"""Minimum full270-bit result transport exactness, reset and negative controls.

This verifies opaque transport, not SEU detection or production consumer guards.
"""
import argparse,hashlib,json,random,subprocess
from pathlib import Path
from hbm_result_relay_model import hbm_result_relay_stage_model,ROOT,PATHS
SOURCE='rtl/hbm_accel/result_relay_stage_20261007/ot_hbm_result_relay_slice.sv'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    model=hbm_result_relay_stage_model();lat=model['balanced_latency_cycles']
    groups=json.loads((ROOT/PATHS).read_text())['result_leaves'][0]['groups']
    rng=random.Random(20261007);history=[0]*lat;stim=[];gold=[]
    for n in range(2048):
        rst=not(n<3 or 333<=n<336 or 1111<=n<1114)
        data=(int(n%7!=0))|((n%4096)<<1)|(rng.getrandbits(256)<<13)|(int(n%31==0)<<269)
        history=history[1:]+[data] if rst else [0]*lat
        stim.append(f'{(int(rst)<<270)|data:068x}')
        gold.append(f'{history[0]:068x}')
    (a.out/'stim.hex').write_text('\n'.join(stim)+'\n');(a.out/'gold.hex').write_text('\n'.join(gold)+'\n')
    records=[]
    for mutant in ('positive','slice_skew','row_miswire','fault_drop','reset_ignored'):
        lines=['module tb;','reg clk=0; always #5 clk=~clk;','reg rst_n=0;reg [269:0] d=0;wire [269:0] q;',
            'reg [270:0] stim[0:2047];reg [269:0] gold[0:2047];integer n;',
            'wire [63:0] bypass_q;ot_hbm_result_relay_slice bypass(.clk(clk),.rst_n(rst_n),.d(d[63:0]),.q(bypass_q));']
        for k,g in enumerate(groups):
            depth=lat-(mutant=='slice_skew' and k==0)
            lines += [f'wire [63:0] pipe{k}[0:{depth}];']
            for bit in range(64):
                if bit<len(g['bit_indices']):
                    idx=g['bit_indices'][bit]
                    src='1\'b0' if mutant=='fault_drop' and idx==269 else f'd[{idx ^ 1 if mutant=="row_miswire" and idx in (2,3) else idx}]'
                    lines += [f'assign pipe{k}[0][{bit}]={src};',f'assign q[{idx}]=pipe{k}[{depth}][{bit}];']
                else:lines += [f'assign pipe{k}[0][{bit}]=1\'b0;']
            reset="1'b1" if mutant=='reset_ignored' else 'rst_n'
            lines += [f'genvar s{k};generate for(s{k}=0;s{k}<{depth};s{k}=s{k}+1)begin:chain{k}',
                f'ot_hbm_result_relay_slice #(.W(64),.ENABLE(1)) stage(.clk(clk),.rst_n({reset}),.d(pipe{k}[s{k}]),.q(pipe{k}[s{k}+1]));end endgenerate']
        lines += ['initial begin','$readmemh("stim.hex",stim);$readmemh("gold.hex",gold);',
            'for(n=0;n<2048;n=n+1)begin @(negedge clk);{rst_n,d}=stim[n];#1;',
            'if(bypass_q!==d[63:0])$fatal(1,"default bypass mismatch");',
            'if(!rst_n && q!==0)$fatal(1,"async reset mismatch at %0d",n);',
            '@(posedge clk);#1;if(q!==gold[n])$fatal(1,"transport mismatch at %0d",n);end',
            '$display("PASS 2048 full270bit frames,3 reset epochs,default bypass");$finish;end','endmodule']
        tb=a.out/f'{mutant}.sv';tb.write_text('\n'.join(lines)+'\n')
        compile=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(a.out/f'{mutant}.vvp'),str(ROOT/SOURCE),str(tb)],capture_output=True,text=True)
        (a.out/f'{mutant}.compile.log').write_text(compile.stdout+compile.stderr)
        if compile.returncode:raise RuntimeError(mutant+' compilation failed')
        sim=subprocess.run(['vvp',f'{mutant}.vvp'],cwd=a.out,capture_output=True,text=True)
        (a.out/f'{mutant}.log').write_text(sim.stdout+sim.stderr)
        ok=sim.returncode==0 if mutant=='positive' else sim.returncode!=0 and ('transport mismatch' in sim.stdout or 'async reset mismatch' in sim.stdout)
        records.append(dict(case=mutant,returncode=sim.returncode,expected_gate=ok))
    rec=dict(status='PASS'if all(r['expected_gate']for r in records)else'FAIL',scope='minimum one full270bit leaf; fault-free transport only, not link/control error protection',
        frames=2048,reset_epochs=3,latency_cycles=lat,physical_slices=6,physical_bits_per_slice=64,cases=records,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [SOURCE,PATHS,'tools/hbm_result_relay_model.py','tools/hbm_result_relay_gate.py']})
    (a.out/'record.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec));return 0 if rec['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
