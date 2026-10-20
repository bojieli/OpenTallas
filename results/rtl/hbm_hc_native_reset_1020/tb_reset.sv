`timescale 1ns/1ps
module tb_reset;
reg clk=0, runclk=1, rn=1; always #1 if(runclk) clk=~clk;
wire [2:0] oldr,localr; reg [2:0] h2=0;
ot_rst_relay #(.REGIONS(3)) old (.clk(clk),.rst_n_in(rn),.rst_n(oldr));
ot_hbm_hc_tail_reset_local fix0 (.clk(clk),.rst_n_in(rn),.rst_n(localr));
genvar i;generate for(i=0;i<3;i=i+1) begin
always @(posedge clk or negedge oldr[i]) if(!oldr[i]) h2[i]<=0;else h2[i]<=1;
end endgenerate
integer checks=0, epochs=0;reg armed=0;
// Compare settled asynchronous and clock events; independent registers start unknown.
always @(clk or rn or oldr or localr) begin #0.001;
if(armed) begin checks=checks+1;if(oldr!==localr) $fatal(1,"RESET_MISMATCH old=%b local=%b",oldr,localr);end
end
initial begin
#0.23;rn=0;#0.01;armed=1;
for(integer p=0;p<40;p=p+1)begin
  // Stop low: pulses and arbitrary deassert phases cannot release either tree.
  @(negedge clk);runclk=0;rn=0;#0.07;
  if(oldr!==0 || localr!==0 || h2!==0)$fatal(1,"ASYNC_ASSERT");
  rn=1;#0.13;rn=0;#0.031;rn=1;#0.17;
  if(oldr!==0 || localr!==0 || h2!==0)$fatal(1,"STOPPED_RELEASE");
  runclk=1;
  for(integer e=1;e<=5;e=e+1)begin
    @(posedge clk);#0.01;
    if(oldr !== ((e>=3)?3'b111:3'b000))$fatal(1,"LEGACY_EDGE %0d",e);
    if(localr!==oldr)$fatal(1,"LOCAL_EDGE %0d",e);
    if(h2 !== ((e>=4)?3'b111:3'b000))$fatal(1,"H2_EDGE %0d",e);
    checks=checks+3;
  end
  #(0.019*(p+1));rn=0;#0.011;epochs=epochs+1;
end
$display("RESET_PROTOCOL PASS epochs=%0d checks=%0d original_release=3 local_release=3 h2_release=4 stopped_clock_assert=PASS",epochs,checks);$finish;
end
endmodule
