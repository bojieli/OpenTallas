`timescale 1ps/1fs
`ifndef MUT
`define MUT 0
`endif
module actual_producer(input clk,input[67:0]ids,output[67:0]hx_w);
reg[67:0]win_n;
generate if(`MUT==0)begin
always @(negedge clk) win_n <= ids;
end else begin
always @(posedge clk) win_n <= ids;
end endgenerate
assign hx_w = win_n;
endmodule
module actual_capture(input ck,input[67:0]in_w,output reg[67:0]w_q);
always @(posedge ck) w_q <= in_w;
endmodule
module tb_half_phase;
reg clk=0;always #416.5 clk=~clk;
reg[67:0]ids=0;reg[67:0]old_win_n=0,old_w_q=0;wire[67:0]hx_w,w_q;
actual_producer p(clk,ids,hx_w);actual_capture c(clk,hx_w,w_q);
always@(negedge clk)old_win_n<=ids;
always@(posedge clk)old_w_q<=old_win_n;
integer t,err=0,checks=0;reg[67:0]lastfall=0;
always@(negedge clk)begin #1;lastfall=hx_w;end
initial begin
 for(t=0;t<2000;t++)begin
  @(posedge clk);#1;
  if(t>2)begin
   checks++;if(w_q!==old_w_q)begin err++;if(err<5)$display("DATA_DIFF %0d",t);end
   if(hx_w!==lastfall)begin err++;if(err<5)$display("PHASE_DIFF %0d",t);end
  end
  #100;ids={ids[66:0],~(ids[67]^ids[65]^ids[63]^ids[60])};
 end
 if(err)begin $display("HALF_PHASE FAIL %0d",err);$fatal(1,"phase");end
 $display("HALF_PHASE PASS checks%0d period833 producerFALL consumerRISE",checks);$finish;
end
endmodule
