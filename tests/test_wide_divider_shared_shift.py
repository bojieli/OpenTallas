"""Shared shift storage preserves wide divider arithmetic and public cycles."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('simulator',['iverilog','verilator'])
@pytest.mark.parametrize('nb,db,qb,step',[(328,164,163,1),(328,164,163,4),(17,9,17,4),(17,9,24,4),(17,9,7,2)])
def test_shared_storage(tmp_path,simulator,nb,db,qb,step):
    before=tmp_path/'before.sv'
    before.write_text((ROOT/'results/rtl/wide_divider_shared_shift/before.sv').read_text().replace('module ot_wide_div_seq #(','module old_divider #('))
    bench=tmp_path/'tb.sv'
    bench.write_text(r'''
module tb;
localparam N=NB,D=DB,Q=QB,S=STEP;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,start=0;
reg [N-1:0] numerator=0;
reg [D-1:0] denominator=1;
wire busy,done,inexact,rb,rd,ri;
wire [Q-1:0] quotient,rq;
ot_wide_div_seq #(.NUM_BITS(N),.DEN_BITS(D),.QUOT_BITS(Q),.BITS_PER_STEP(S)) dut(
.clk(clk),.rst_n(rst_n),.start(start),.numerator(numerator),.denominator(denominator),.busy(busy),.done(done),.quotient(quotient),.inexact(inexact));
old_divider #(.NUM_BITS(N),.DEN_BITS(D),.QUOT_BITS(Q),.BITS_PER_STEP(S)) old(
.clk(clk),.rst_n(rst_n),.start(start),.numerator(numerator),.denominator(denominator),.busy(rb),.done(rd),.quotient(rq),.inexact(ri));
integer cycles=0,checked=0,aborted=0;
always @(negedge clk)begin
 #0.1;
 if({busy,done,quotient,inexact} !== {rb,rd,rq,ri})$fatal(1,"cycle mismatch %0d",cycles);
 cycles=cycles+1;
end
reg [Q-1:0] expected;
integer t,k;
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(t=0;t<160;t=t+1)begin
  @(negedge clk);
  for(k=0;k<N;k=k+1)numerator[k]=$random;
  for(k=0;k<D;k=k+1)denominator[k]=$random;
  case(t%8)
   0:denominator=1;
   1:numerator=0;
   2:begin numerator={N{1'b1}};denominator={D{1'b1}};end
   3:begin denominator=7;numerator=42;end
  endcase
  if(denominator==0)denominator=1;
  expected=numerator/denominator;
  start=1;@(negedge clk);start=0;
  if(t%11==10)begin
   repeat(2)@(negedge clk);rst_n=0;repeat(2)@(negedge clk);rst_n=1;aborted=aborted+1;
  end else begin
   wait(done);@(negedge clk);
   if(quotient!==expected || inexact !== ((numerator%denominator)!=0))$fatal(1,"arithmetic mismatch");
   checked=checked+1;
  end
 end
 $display("PASS shared divider checked=%0d aborted=%0d",checked,aborted);$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
'''.replace('N=NB,D=DB,Q=QB,S=STEP',f'N={nb},D={db},Q={qb},S={step}'))
    sources=[str(ROOT/'rtl/lib/ot_wide_div_seq.sv'),str(before),str(bench)]
    if simulator=='iverilog':
        cmd=['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),*sources];run=['vvp',str(tmp_path/'sim')]
    else:
        cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-j','2','-Wno-fatal','--top-module','tb','--Mdir',str(tmp_path/'obj'),*sources];run=[str(tmp_path/'obj/Vtb')]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=300);assert p.returncode==0,p.stdout+p.stderr
    p=subprocess.run(run,capture_output=True,text=True,timeout=600);assert p.returncode==0,p.stdout+p.stderr
    assert 'PASS shared divider checked=146 aborted=14' in p.stdout
