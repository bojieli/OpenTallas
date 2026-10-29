// Smallest tied-zero global-KV capture mechanism: valid-qualified data and
// request timing are compared through reset, clock gating and sparse reads.
module kv_old #(parameter W=2048, D=3)(input clk,rst_n,read,output [W-1:0] q,output valid);
 reg rdq;reg[W-1:0] cap;reg[W-1:0] pipe[0:D-1];reg[D:0] v;integer k;
 always @(posedge clk)begin
  if(!rst_n)begin rdq<=0;v<=0;end else begin rdq<=read;v<={v[D-1:0],rdq};end
  if(rdq)cap<=0;
  pipe[0]<=cap;for(k=1;k<D;k=k+1)pipe[k]<=pipe[k-1];
 end
 assign q=pipe[D-1];assign valid=v[D];
endmodule
module tb;
 reg clk=0,rst_n=0,read=0,gate=1;wire gclk=clk&gate;wire[2047:0]old_q;wire valid;integer n;integer checks=0,caught=0;
 kv_old old(gclk,rst_n,read,old_q,valid);
 always #5 clk=~clk;
 initial begin
 for(n=0;n<12000;n=n+1)begin
  @(negedge clk);if(n==8)rst_n=1;if(n==7000)rst_n=0;if(n==7010)rst_n=1;
  gate=(!rst_n)?1:($urandom_range(0,7)!=0);read=rst_n&&($urandom_range(0,5)==0);
  @(posedge clk);#1;if(gate&&valid)begin
   if(old_q!==2048'd0)$fatal(1,"zero-KV legal-read lockstep mismatch");
   checks=checks+1;if(old_q!==2048'd1)caught=caught+1;
  end
 end
 if(checks<100||caught!=checks)$fatal(1,"mutant escaped or sparse reads not exercised");
 $display("PASS zeroKV valid-qualified lockstep checks=%0d wrong-data mutants=%0d zero added cycles",checks,caught);$finish;
 end
endmodule
