#!/usr/bin/env python3
"""Actual flat-vs-partitioned BF RTL at default and production XST values."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
TB=r'''`timescale 1ps/1ps
module tb_bf_xst;
 reg clk=0;always #417 clk=~clk;
 reg rst=0,v=0;reg[255:0]w=0,x=0;reg[2:0]slot=0;
 reg[6:0]tree=0;reg first=1,last=1,final_i=1;
 integer checked[0:3];
 for(genvar g=0;g<4;g++)begin:cases
   localparam integer XS=g==0?0:g-1;
   localparam integer RC=g==0?0:1;
   localparam integer TW=g==0?2:7;
   wire av,bv,af,bf,ae,be,ax,bx;
   wire[31:0]aq,bq;wire[TW-1:0]at,bt;
   ot_v41_bf16_lanes3 #(.XST(XS),.RC(RC),.TRW(TW),.GRADUAL_RNE(RC)) flat
    (.fclk(clk),.rst_pin(rst),.ze_d(1'b1),.v(v),.w(w),.x(x),.slot(slot),
     .first(first),.last(last),.tree(tree[TW-1:0]),.final_i(final_i),
     .ov(av),.oval(aq),.otree(at),.ofinal(af),.oerr(ae),.fault(ax));
   ot_v41_bf16_lanes3_roots #(.XST(XS),.RC(RC),.TRW(TW),.GRADUAL_RNE(RC)) split
    (.leaf_clk({6{clk}}),.fclk(clk),.rst_pin(rst),.ze_d(1'b1),.v(v),.w(w),.x(x),.slot(slot),
     .first(first),.last(last),.tree(tree[TW-1:0]),.final_i(final_i),
     .ov(bv),.oval(bq),.otree(bt),.ofinal(bf),.oerr(be),.fault(bx));
   initial checked[g]=0;
   always @(posedge clk)begin
     #1;
     if(rst)begin
       if(av!==bv)$fatal(1,"DIFF XST=%0d RC=%0d valid",XS,RC);
       if(av)begin
         if({aq,at,af,ae,ax}!=={bq,bt,bf,be,bx})
           $fatal(1,"DIFF XST=%0d RC=%0d actual output",XS,RC);
         checked[g]++;
       end
     end
   end
 end
 initial begin
   repeat(8)@(negedge clk);rst=1;
   for(int n=0;n<600;n++)begin
     @(negedge clk);v=(n%5!=0);slot=3'(n%8);tree=7'(n/8);
     for(int l=0;l<16;l++)begin
       w[16*l+:16]=16'h3f00+16'(n%64+l);
       x[16*l+:16]=16'h3f80+16'(n%31+l);
     end
   end
   @(negedge clk);v=0;
   repeat(200)@(negedge clk);
   for(int g=0;g<4;g++)if(checked[g]<400)$fatal(1,"missing actual outputs case%0d",g);
   $display("PASS BF XST actual flat/partitioned default0 and production0/1/2: %0d/%0d/%0d/%0d outputs",checked[0],checked[1],checked[2],checked[3]);
   $finish;
 end
endmodule
'''


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--mutant',action='store_true')
    p.add_argument('--jobs',type=int,default=8)
    a=p.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=True)
    tb=w/'tb_bf_xst.sv';tb.write_text(TB)
    spec=json.loads((ROOT/'physical/ref_tile_specs/s81_bf_native_1015/lane4_boundary_r2/spec.json').read_text())
    sources=[ROOT/s for s in spec['sources'] if s.startswith('rtl/')]
    sources += [ROOT/'rtl/v41rom/ot_v41_bf16_lanes3_roots.sv',ROOT/'rtl/v41rom/ot_v41_bf_reduce.sv']
    cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--binary','--timing','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','-Wno-MULTIDRIVEN','--top-module','tb_bf_xst','--Mdir',str(w/'obj'),'-j',str(a.jobs)]
    if a.mutant:cmd+=['+define+BF_ROOT_MUTANT_STOP']
    with (w/'build.log').open('w') as f:r=subprocess.run(cmd+list(map(str,sources))+[str(tb)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:raise SystemExit('ERROR: actual BF XST build failed')
    with (w/'run.log').open('w') as f:r=subprocess.run([str(w/'obj/Vtb_bf_xst')],stdout=f,stderr=subprocess.STDOUT)
    log=(w/'run.log').read_text();print(log)
    if a.mutant:
        if r.returncode and 'DIFF XST=' in log:print('MUTANT BF XST root clock stop detected');raise SystemExit(1)
        raise SystemExit('ERROR: actual BF XST mutant was not detected')
    if r.returncode or 'PASS BF XST actual' not in log:raise SystemExit('ERROR: actual BF XST comparison failed')


if __name__=='__main__':main()
