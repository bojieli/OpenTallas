`timescale 1ns/1ps
module tb_hbm_b2_vm8_sm_sink;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,permit=1;
 reg [191:0] expected_owner=192'h123abcfe9;reg [7:0] sm_mask=8'hff;
 reg tap_v=0;wire tap_ready;reg [2062:0] tap_data=0;reg [191:0] tap_owner;reg [15:0] tap_ticket=0;wire [15:0] tap_ACK_ticket;
 wire tap_ACK_v;wire [191:0] tap_ACK_owner;wire [7:0] xw_en;
 wire [55:0] xw_addr,xw_grp;wire [16383:0] xw_data;wire fault,drained;
 ot_hbm_b2_vm8_sm_sink #(.MUT(MUT)) u(.*);
 integer samples=0,acks=0,t=0;reg [2062:0] golden;
 always @(posedge clk)if(rst_n&&|xw_en)begin
  for(integer s=0;s<8;s=s+1)if(xw_en[s])begin
   if(xw_addr[s*7+:7]!=golden[2061:2055]||xw_grp[s*7+:7]!=golden[2054:2048]||xw_data[s*2048+:2048]!=golden[2047:0])$fatal(1,"native SM sampling mismatch");
  end
  samples=samples+1;
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;tap_owner=expected_owner;
  for(integer n=0;n<1664;n=n+1)begin
   while(!tap_ready)begin @(negedge clk);t=t+1;if(t>20000)$fatal(1,"sink timeout");end
   golden={1'b1,7'(n/13),7'(n%13),2048'b0};
   for(integer b=0;b<64;b=b+1)golden[b*32+:32]=32'h8123ab01+n*67+b;
   if(n%13==12)golden[2047:640]=0;
   tap_data=golden;tap_v=1;@(negedge clk);t=t+1;tap_v=0;
   while(!tap_ACK_v)begin @(negedge clk);t=t+1;if(fault)$fatal(1,"unexpected sink fault");if(t>20000)$fatal(1,"ACK timeout");end
   if(samples!=n+1||tap_ACK_owner!=expected_owner)$fatal(1,"ACK precedes SM sampling / owner mismatch");
   acks=acks+1;@(negedge clk);t=t+1;
  end
  if(acks!=1664||samples!=1664||!drained)$fatal(1,"missing sample / drain");
  // Wrong owner must never write the unbackpressured native SM or ACK.
  tap_owner=expected_owner^192'b1;tap_v=1;@(negedge clk);tap_v=0;
  if(!fault||xw_en!=0||tap_ACK_v)$fatal(1,"wrong owner admitted");
  $display("PASS_SINK boundary fragments=128 beats=1664 cycles=%0d production_memory_gate=OPEN",t);$finish;
 end
endmodule
