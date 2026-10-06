`timescale 1ns/1ps
// MARGIN fault retirement (six deep, group faults) == original four-deep retirement two cycles later,
// with the original's global arithmetic fault = arithmetic | any group fault.
module tb_fh_margin_retire;
 parameter integer MUT=0;   // 1: drop group faults in the DUT, 2: compare without the +1 offset
 reg clk=0,rst_n=0; always #0.5 clk=~clk;
 reg packet_v; reg [63:0] packet,poison; reg [3:0] af,gf; reg arith;
 wire rv0,rv1,f0,f1,b0,b1; wire [63:0] rp0,rp1,lv0,lv1; wire [3:0] wv0,wv1;
 ot_hdc_v41_fh_fault_retire #(.ENABLE(1),.PACKET_BITS(64)) ref0(.clk(clk),.rst_n(rst_n),.packet_v(packet_v),.packet(packet),
  .poison(poison),.address_fault(af),.arithmetic_fault(arith||(|gf)),.group_fault(4'b0),.retired_v(rv0),.retired_packet(rp0),
  .lane_veto(lv0),.write_veto(wv0),.fault(f0),.busy(b0));
 ot_hdc_v41_fh_fault_retire #(.ENABLE(1),.PACKET_BITS(64),.MARGIN(1)) dut(.clk(clk),.rst_n(rst_n),.packet_v(packet_v),.packet(packet),
  .poison(poison),.address_fault(af),.arithmetic_fault(arith),.group_fault(MUT==1?4'b0:gf),.retired_v(rv1),.retired_packet(rp1),
  .lane_veto(lv1),.write_veto(wv1),.fault(f1),.busy(b1));
 reg [1+64+64+4+1-1:0] q0,q00;
 integer i,seed=7,faults=0,vs=0,gfs=0;
 always @(posedge clk) begin q00<={rv0,rp0,lv0,wv0,f0}; q0<=q00; end
 initial begin
  packet_v=0;packet=0;poison=0;af=0;gf=0;arith=0;
  repeat(3)@(negedge clk); rst_n=1;
  for(i=0;i<4000;i=i+1) begin
   @(negedge clk);
   if(i>10 && (MUT==2 ? {rv1,rp1,lv1,wv1,f1}!=={rv0,rp0,lv0,wv0,f0} : {rv1,rp1,lv1,wv1,f1}!==q0)) $fatal(1,"retire lockstep %0d",i);
   if(rv1) vs=vs+1; if(gf!=0) gfs=gfs+1; if(f1) faults=faults+1;
   // sticky faults: re-arm periodically through reset
   if(i%500==499) begin rst_n=0; @(negedge clk); rst_n=1; end
   packet_v=$random(seed); packet={$random(seed),$random(seed)};
   poison=(($random(seed)&255)==0)?(64'd1<<($random(seed)&63)):0;
   af=(($random(seed)&511)==0)?4'b0001<<($random(seed)&3):0;
   gf=(($random(seed)&15)==0)?4'b0001<<($random(seed)&3):0;
   arith=(($random(seed)&1023)==0);
  end
  if(vs<500||faults<20||gfs<100) $fatal(1,"coverage vs=%0d faults=%0d",vs,faults);
  $display("PASS margin retire == original +2 cycles=4000 retired=%0d faulted=%0d gf=%0d",vs,faults,gfs); $finish;
 end
endmodule
