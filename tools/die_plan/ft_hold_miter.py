#!/usr/bin/env python3
"""Small zero-cycle ft-input delay-cell lockstep miter, with an inverted-cell mutant control."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_hold
import gen_rtl
import schema

def run(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    raw=json.loads((Path(__file__).resolve().parent/'examples/s81_pair/s81_pair_plan.json').read_text())
    raw['clock']['ft_in_hold']='liberty'
    p=schema.Plan(raw)
    cells=ft_hold.module_text(p)
    name=ft_hold.module_name(ft_hold.chain(p)[0])
    mutant=cells.replace('module '+name+' ', 'module '+name+'_mut ').replace('HB3xp67_ASAP7_75t_R u0','BAD_HB u0')
    buf='\n'.join('module '+c+'(input wire A,output wire Y); assign Y=A; endmodule' for c in ft_hold.CELLS)
    tb='''
module BAD_HB(input wire A,output wire Y); assign Y=~A; endmodule
module tb;
reg clk=0,rst_n=0; reg [16:0] d=0;
wire [16:0] h,m; wire [15:0] qg,qn,qm; wire eg,en,em;
always #5 clk=~clk;
NAME #(.W(17)) hold_good(.d(d),.q(h));
NAME_mut #(.W(17)) hold_bad(.d(d),.q(m));
ot_dp_st #(.W(16)) gold(.clk(clk),.rst_n(rst_n),.d(d[15:0]),.ea(d[16]),.q(qg),.eq(eg));
ot_dp_st #(.W(16)) candidate(.clk(clk),.rst_n(rst_n),.d(h[15:0]),.ea(h[16]),.q(qn),.eq(en));
ot_dp_st #(.W(16)) mutant(.clk(clk),.rst_n(rst_n),.d(m[15:0]),.ea(m[16]),.q(qm),.eq(em));
integer i,wrong=0;
initial begin
 for(i=0;i<4096;i=i+1) begin
  @(negedge clk); rst_n=(i%47>2); d={$random};
  @(posedge clk); #1;
  if({qg,eg}!=={qn,en}) $fatal(1,"LOCKSTEP_FAIL cycle %0d",i);
  if({qg,eg}!=={qm,em}) wrong=wrong+1;
 end
 if(wrong==0) $fatal(1,"MUTANT_NOT_CAUGHT");
 $display("LOCKSTEP_PASS cycles=%0d mutant_mismatches=%0d added_cycles=0",i,wrong);
 $finish;
end
endmodule
'''.replace('NAME',name)
    src=out/'miter.sv'; src.write_text(gen_rtl.CELLS+'\n'+cells+'\n'+mutant+'\n'+buf+'\n'+tb)
    subprocess.run(['iverilog','-g2012','-DSYNTHESIS','-s','tb','-o',str(out/'miter.vvp'),str(src)],check=True)
    cp=subprocess.run(['vvp',str(out/'miter.vvp')],text=True,capture_output=True,check=True)
    rec={'verdict':'PASS','lockstep_cycles':4096,'mutant':'first hold cell inverts the data/epoch bus','mutant_caught':'mutant_mismatches=4096' in cp.stdout,'added_cycles':0,'stdout':cp.stdout.strip()}
    if not rec['mutant_caught']:raise RuntimeError(rec)
    (out/'miter.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(cp.stdout.strip())
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
