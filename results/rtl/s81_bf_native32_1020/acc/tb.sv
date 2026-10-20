`timescale 1ns/1ps
module coupon #(parameter NCH=16)(input wire clk,output reg done=0);
localparam SW=$clog2(NCH);
reg rst=0,v=0,first=0,last=0;reg[SW-1:0] slot=0;reg[31:0] term=0;reg[7:0] tag=0;
wire[2*NCH-1:0] oh={2{NCH'(1)<<slot}};
wire[1:0] ov,of,fault;wire[31:0] y[0:1];wire[7:0] ot[0:1];
old_chain #(.NCH(NCH),.TW(8),.PD(1)) a(.clk(clk),.rst_pin(rst),.v(v),.slot(slot),.slot_oh(oh),.first(first),.last(last),.term(term),.term_f(1'b0),.tag(tag),.ov(ov[0]),.osum(y[0]),.of(of[0]),.otag(ot[0]),.fault(fault[0]));
ot_v41_chain4_rp #(.NCH(NCH),.TW(8),.PD(1)) b(.clk(clk),.rst_pin(rst),.v(v),.slot(slot),.slot_oh(oh),.first(first),.last(last),.term(term),.term_f(1'b0),.tag(tag),.ov(ov[1]),.osum(y[1]),.of(of[1]),.otag(ot[1]),.fault(fault[1]));
integer outputs=0,f5=0,f6=0;reg[31:0] rng=32'h81109916;
always @(negedge clk) if(rst) begin
 if(a.fwd5[0] && a.v_r) f5++;
 if(a.fwd6[0] && a.v_r) f6++;
 if(ov[0]!==ov[1] || fault[0]!==fault[1]) $fatal(1,"ACC_DIFF valid/fault NCH=%0d",NCH);
 if(ov[0]) begin
  outputs++;
  if({y[0],of[0],ot[0]} !== {y[1],of[1],ot[1]}) $fatal(1,"ACC_DIFF NCH=%0d y=%h/%h tag=%h fwd=%0d/%0d",NCH,y[0],y[1],ot[0],f5,f6);
 end
end
initial begin
 repeat(4) @(negedge clk);rst=1;repeat(4) @(negedge clk);
 for(integer wave=0;wave<64;wave++) begin
  if(wave==47) begin
   for(integer n=0;n<NCH+3;n++) begin
    @(negedge clk);v=1;slot=SW'(n%NCH);first=n<NCH;last=0;term=32'h3f800031;tag=8'h77;
   end
   @(negedge clk);v=0;rst=0;@(negedge clk);rst=1;repeat(4) @(negedge clk);
  end
  for(integer round_i=0;round_i<4;round_i++) for(integer n=0;n<NCH;n++) begin
   @(negedge clk);v=1;slot=SW'(n);first=(round_i==0);last=(round_i==3);tag=8'(wave);
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};term=32'h3f800000|(rng&32'h0003ffff);
  end
  @(negedge clk);v=0;repeat(24) @(negedge clk);
  if(wave==31) begin rst=0;repeat(3) @(negedge clk);rst=1;repeat(4) @(negedge clk);end
 end
 repeat(32) @(negedge clk);
 if(outputs!=64*NCH || fault[0]) $fatal(1,"ACC_COVERAGE NCH=%0d outputs=%0d fault=%b",NCH,outputs,fault);
 $display("ACC_SRAM PASS NCH=%0d outputs=%0d forward5=%0d forward6=%0d",NCH,outputs,f5,f6);done=1;
end
endmodule
module tb;
reg clk=0;always #5 clk=~clk;wire[2:0] done;
coupon #(.NCH(8)) a(clk,done[0]);coupon #(.NCH(9)) b(clk,done[1]);coupon #(.NCH(16)) c(clk,done[2]);
initial begin wait(&done);$finish;end
initial begin #1000000;$fatal(1,"ACC TIMEOUT");end
endmodule
