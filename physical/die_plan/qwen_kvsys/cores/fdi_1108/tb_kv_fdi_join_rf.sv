`timescale 1ns/1ps
module tb_kv_fdi_join_rf;
 localparam integer WA=522, WB=521, DEPTH=16;
 reg clk=0, rst_n=0, av=0,bv=0;
 reg [WA-1:0] ad=0; reg [WB-1:0] bd=0;
 wire rv,cv,mv,m2v; wire [WA+WB-1:0] rd,cd,md,m2d;
 reg expected_v=0; reg [WA+WB-1:0] expected_d;
 integer cycle=0, checked=0, live_mutant=0, control_mutant=0, taga=0,tagb=0;
 ot_fdi_join2 #(.WA(WA),.WB(WB),.DEPTH(DEPTH)) ref0(clk,rst_n,av,ad,bv,bd,rv,rd);
 ot_kv_fdi_join_rf #(.WA(WA),.WB(WB),.DEPTH(DEPTH)) dut(clk,rst_n,av,ad,bv,bd,cv,cd);
 ot_kv_fdi_join_rf #(.WA(WA),.WB(WB),.DEPTH(DEPTH),.MUT(1)) live_bad(clk,rst_n,av,ad,bv,bd,mv,md);
 ot_kv_fdi_join_rf #(.WA(WA),.WB(WB),.DEPTH(DEPTH),.MUT(2)) ctl_bad(clk,rst_n,av,ad,bv,bd,m2v,m2d);
 always #5 clk=~clk;
 always @(posedge clk or negedge rst_n) begin
  if (!rst_n) expected_v <= 0;
  else begin expected_v <= rv; expected_d <= rd; end
 end
 always @(posedge clk) if(rst_n) begin
  if ((av && ref0.an == DEPTH && !ref0.pop) || (bv && ref0.bn == DEPTH && !ref0.pop)) $fatal(1,"baseline overflow");
 end
 always @(negedge clk) if(rst_n && cycle>3) begin
  if(cv !== expected_v) $fatal(1,"valid mismatch cycle%0d cand%b expected%b",cycle,cv,expected_v);
  if(expected_v) begin
   checked=checked+1;
   if(cd !== expected_d) $fatal(1,"all-live-payload mismatch cycle%0d",cycle);
   if(mv !== expected_v || md !== expected_d) live_mutant=live_mutant+1;
  end
  if(m2v !== expected_v || (expected_v && m2d !== expected_d)) control_mutant=control_mutant+1;
 end
 task step(input integer aa,bb);
  integer j;
  begin
   @(negedge clk); #1; cycle=cycle+1;av=(aa!=0);bv=(bb!=0);
   if(aa!=0)begin for(j=0;j<WA;j=j+1)ad[j]=((taga*32'h9e3779b9)>>(j%31))^((j+taga)%3==0);taga=taga+1;end
   if(bb!=0)begin for(j=0;j<WB;j=j+1)bd[j]=((tagb*32'h85ebca6b)>>(j%29))^((j+tagb)%5==0);tagb=tagb+1;end
  end
 endtask
 integer i;
 initial begin
  repeat(4)step(0,0);rst_n=1;
  repeat(8)step(0,0); // empty
  repeat(16)step(1,0); // full A half
  step(0,1); // fill B; A still full, no A overflow
  repeat(256)step(1,1); // full A pop+write collision, sustained pairing
  repeat(16)step(0,1); step(1,0); // drain A then pair the residual B
  repeat(8)step(0,0);
  repeat(16)step(0,1); // full B half, opposite skew
  step(1,0);
  repeat(256)step(1,1);
  repeat(16)step(1,0); step(0,1);
  repeat(8)step(0,0);
  repeat(7)step(1,0);rst_n=0;repeat(4)step(0,0);rst_n=1;
  // deterministic burst/skew patterns: equal totals in each16-cycle epoch.
  for(i=0;i<256;i=i+1)begin step(1,0);step(1,1);step(0,1);step(0,0);end
  repeat(8)step(0,0);
  if(checked<1000 || live_mutant<500 || control_mutant<100)$fatal(1,"coverage checked%0d live_mutant%0d control_mutant%0d",checked,live_mutant,control_mutant);
  $display("PASS full WA522 WB521 DEPTH16 cycles%0d live_words%0d live_mutant%0d control_mutant%0d",cycle,checked,live_mutant,control_mutant);
  $finish;
 end
endmodule
