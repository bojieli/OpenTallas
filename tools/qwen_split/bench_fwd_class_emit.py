#!/usr/bin/env python3
"""Compare generated 2x600 class composition against original 1088-bit RTL.
Run on fleet: python3 tools/qwen_split/bench_fwd_class_emit.py OUT.
"""
import sys
import subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_fwd_class_emit import Composition
import gen_relay_rtl as R
from qwen_split import fwd_class_emit as F

out=Path(sys.argv[1]).resolve(); out.mkdir(parents=True,exist_ok=True)
v,m=Composition().vehicle(1088)
original_station=m['insts'][2].master;original_landing=m['insts'][3].master
v.write_netlist(m,1,out/'original_die.v');R.main(out/'original_die.v',out/'original_wrappers.sv')
F.install(v,m)
v.write_netlist(m,1,out/'die.v');R.main(out/'die.v',out/'wrappers.sv')
if '--mutant' in sys.argv:
    p=out/'die.v'; text=p.read_text()
    a='.q({n_payload__s1[543:0], n_payload__s0[543:0]})'
    b='.q({n_payload__s0[543:0], n_payload__s1[543:0]})'
    assert a in text
    p.write_text(text.replace(a,b,1))
(out/'tb.sv').write_text('''`timescale 1ns/1ps
module source(output reg [1087:0] q=0, output reg ck=0, output reg en=0);
  always #5 ck=~ck;
  integer count=0; integer j;
  always @(posedge ck) begin
    count<=count+1; if(count==15)en<=1;
    for(j=0;j<1088;j=j+1) q[j]<=((count*1664525+j*1013904223) >> (j%23)) & 1;
  end
endmodule
module sink(input wire [1087:0] q, output reg ck=0, output reg rs=0);
  initial begin #1; forever #5 ck=~ck; end
  integer count=0;
  always @(posedge ck) begin count<=count+1; if(count==15)rs<=1; end
endmodule
module tb;
  qfd_die dut();
  wire [1087:0] mid,reference;
  wire epoch,ckf,unused_hi,unused_lo,flt;
  ORIGINAL_STATION original_station
    (.ck(dut.n_cs),.en(dut.n_en),.a(dut.src.q),.b(mid),.eb(epoch),.ck_o(ckf));
  ORIGINAL_LANDING original_landing
    (.ckf(ckf),.ea(epoch),.a(mid),.ck(dut.n_cd),.rs(dut.n_rs),
     .k0(1'b0),.k1(1'b0),.k2(1'b1),.b(reference),.tie_hi(unused_hi),.tie_lo(unused_lo),.fault(flt));
  integer checked=0;
  always @(negedge dut.n_cd) if(dut.dst.count>32) begin
    if(dut.dst.q !== reference) $fatal(1,"CLASS_EQUIV_FAIL cycle=%0d",dut.dst.count);
    checked=checked+1;
    if(checked==1000) begin $display("CLASS_EQUIV_PASS bits=1088 slices=2 class_bits=600 cycles=%0d",checked);$finish;end
  end
  initial begin #20000;$fatal(1,"TIMEOUT");end
endmodule
'''.replace('ORIGINAL_STATION',original_station).replace('ORIGINAL_LANDING',original_landing))
root=Path(__file__).resolve().parents[2]
verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(verilator),'--binary','--timing','-j','1','-Wno-fatal','-Wno-WIDTH','-Wno-MULTIDRIVEN','-Wno-COMBDLY','-Wno-LATCH','-Wno-INITIALDLY','--top-module','tb','-Mdir',str(out/'obj'),'-o','tb',str(out/'tb.sv'),str(out/'die.v'),str(out/'wrappers.sv'),str(out/'original_wrappers.sv'),str(root/'rtl/qwen_split/qfd_fwd_lane.sv'),str(root/'rtl/hdc/ot_hdc_cg.sv')]
r=subprocess.run(cmd,text=True,capture_output=True);(out/'build.log').write_text(r.stdout+r.stderr)
if r.returncode: raise SystemExit(r.returncode)
r=subprocess.run([str(out/'obj/tb')],text=True,capture_output=True);(out/'run.log').write_text(r.stdout+r.stderr); print(r.stdout+r.stderr,end='');raise SystemExit(r.returncode)
