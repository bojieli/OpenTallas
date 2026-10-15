`timescale 1ns/1ps
// Actual legacy 546-bit ring versus five actual-macro local quarters.
module tb_coll_ring_quarters;
parameter integer OFF=55;
reg clk=0;always #5 clk=~clk;
reg rs_n=0;reg[545:0]wd=0;
wire[545:0]legacy_rd,quarter_rd;
ot_coll_static_ring #(.OFF(OFF)) u_legacy(.clk(clk),.mem_ck({4{clk}}),.rs_n(rs_n),.wd(wd),.rd(legacy_rd));
for(genvar q=0;q<5;q=q+1)begin:g_quarter
 localparam integer W=(q==4)?34:128;
 ot_coll_local_ring_quarter #(.OFF(OFF),.W(W),.ID(q))u_dut(
  .ctl_ck(clk),.mem_ck({2{clk}}),.rs_n(rs_n),.wd(wd[128*q+:W]),.rd(quarter_rd[128*q+:W]));
end
function automatic[545:0]pattern(input integer cycle);
 reg[545:0]value;
 begin
  for(integer bitn=0;bitn<546;bitn=bitn+1)
   value[bitn]=1'((32'(cycle)*32'h9e3779b9 ^ 32'(bitn/32)*32'h85ebca6b) >> (bitn%32));
  if(cycle%4==0)begin value=0;value[cycle%546]=1;end
  if(cycle%4==1)begin value='1;value[cycle%546]=0;end
  pattern=value;
 end
endfunction
integer cycle=0,checks=0,known_checks=0,errors=0,data_errors=0,metadata_errors=0,unknown_errors=0,warm=0;
reg started=0;reg[545:0]seen_one=0,seen_zero=0;
always @(posedge clk or negedge rs_n)if(!rs_n)warm<=0;else warm<=warm+1;
always @(negedge clk)begin
 #1;
 if(started&&cycle<6144)begin
  checks=checks+1;
  seen_one=seen_one|wd;seen_zero=seen_zero|~wd;
  if(quarter_rd!==legacy_rd)errors=errors+1;
  if(quarter_rd[511:0]!==legacy_rd[511:0])data_errors=data_errors+1;
  if(quarter_rd[545:512]!==legacy_rd[545:512])metadata_errors=metadata_errors+1;
  if(warm>64)begin
   known_checks=known_checks+1;
   if((^quarter_rd)===1'bx||(^legacy_rd)===1'bx)begin errors=errors+1;unknown_errors=unknown_errors+1;end
  end
 end
end
initial begin
 repeat(8)@(negedge clk);started=1;
 for(cycle=0;cycle<6144;cycle=cycle+1)begin
  rs_n=cycle>=4&&!(cycle>=3000&&cycle<3004);
  wd=pattern(cycle);
  @(negedge clk);
 end
 #2;started=0;
 $display("RING_QUARTERS off=%0d checks=%0d known_checks=%0d errors=%0d data_errors=%0d metadata_errors=%0d unknown_errors=%0d all_bits_one=%0d all_bits_zero=%0d",OFF,checks,known_checks,errors,data_errors,metadata_errors,unknown_errors,(&seen_one),(&seen_zero));
 if(checks!=6144||known_checks<6000||!(&seen_one)||!(&seen_zero))$fatal(1,"incomplete ring stimulus");
 if(errors)$fatal(1,"RING_QUARTERS FAIL");
 $display("RING_QUARTERS PASS");$finish;
end
endmodule
