`timescale 1ps/1ps
module tb_fwd;
 reg clk=0;always #417 clk=~clk;
 reg rst=0,iv=0;reg[511:0]id=0;wire c1,c2,v1,v2;wire[511:0]d1,d2;
 wire dc,dv;wire[511:0]dd;
 ot_fwd_link_stage #(.ENABLE(1)) a(clk,rst,iv,id,c1,v1,d1);
 ot_fwd_link_stage #(.ENABLE(1)) b(c1,rst,v1,d1,c2,v2,d2);
 ot_fwd_link_stage off(clk,rst,iv,id,dc,dv,dd);
 wire wr,rv,wl,rl,wf,rf;wire[511:0]rd;
 ot_meso_fifo disabled(clk,rst,iv,wr,id,clk,rst,iv,rv,rd,wl,rl,wf,rf);
 integer n=0;reg expected_v=0;reg[511:0]expected=0;
 always @(negedge clk)begin
   #1;if(rst)begin
      if(v1!==iv || (iv && d1!==id))$fatal(1,"first-stage falling capture");
      expected_v=v1;expected=d1;
   end else expected_v=0;
 end
 always @(posedge clk)begin
   #2;
   if(rst && (v2!==expected_v || (v2 && d2!==expected)))$fatal(1,"second-stage generated-clock ordering");
   if(c1!==~clk || c2!==clk)$fatal(1,"forwarded clock polarity");
   if(dc!==0 || dv!==0 || dd!==0 || wr!==0 || rv!==0 || wl!==0 || rl!==0 || wf!==0 || rf!==0)$fatal(1,"default-off not inert");
   n=n+1;rst=n>4;iv=n%3!=0;id={16{32'(n*7919)}};
   if(n==200)begin $display("PASS_FWD_ORDER_AND_DEFAULT_OFF");$finish;end
 end
endmodule
