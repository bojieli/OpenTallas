`timescale 1ns/1ps
module tb_s81_ingest_visibility;
 reg ck=0,clk_h=0;always #0.416667 ck=~ck;always #0.53 clk_h=~clk_h;
 reg rst_n=0;reg[7:0] ack_n=0;reg iv=0;reg[63:0] id=0;wire ic,ov;wire[63:0] od;reg oc=0;wire fault;wire[31:0] landed;
 integer actual=0,c=0,received=0,returned=0,issued=0;
 ot_s81_ingest_visibility_fence #(.ENABLE(1)) dut(rst_n,ck,clk_h,ack_n,iv,id,ic,ov,od,oc,fault,landed);
 always @(negedge ck)begin
  ack_n=0;
  if(rst_n)begin c=c+1;if(c>=200&&actual<40&&(c%20)==0)ack_n=5;end
 end
 always @(posedge ck)if(rst_n)actual=actual+ack_n;
 always @(negedge clk_h)begin
  iv=0;oc=ov;
  if(rst_n&&issued<4)begin iv=1;id={8'h01,8'd0,8'(issued+1),8'd0,32'((issued+1)*10)};issued=issued+1;end
 end
 always @(posedge clk_h)begin
  #0.05;
  if(rst_n)begin
   if(fault)$fatal(1,"unexpected fence fault");
   if(landed>actual)$fatal(1,"snapshot fabricated commits");
   if(ic)returned=returned+1;
   if(ov)begin
    if(od[31:0]>actual)$fatal(1,"completion before physical visibility");
    if(od[47:40]!=received+1||od[31:0]!=(received+1)*10)$fatal(1,"completion payload/order mismatch");
    received=received+1;
   end
  end
 end
 initial begin
  repeat(6)@(negedge clk_h);rst_n=1;
  repeat(900)@(negedge clk_h);
  if(actual!=40||received!=4||returned!=4||landed!=40)$fatal(1,"fence did not drain actual%0d recv%0d ret%0d snap%0d",actual,received,returned,landed);
  $display("S81_VISIBILITY PASS physical=%0d fenced=%0d credit_returns=%0d",actual,received,returned);$finish;
 end
endmodule
