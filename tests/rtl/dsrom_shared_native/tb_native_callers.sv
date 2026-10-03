`timescale 1ns/1ps
module tb;
 reg fast_clk=1,slow_clk=1;always #3 fast_clk=~fast_clk;always #4 slow_clk=~slow_clk;
 reg cold_n=0,fast_rst_n=0,slow_rst_n=0,abort_fast=0,abort_slow=0;
 reg [3:0] direct_r_v=0;wire [3:0] direct_r_ready,direct_q_v;
 reg [15:0] direct_r_enable=0;reg [479:0] direct_r_addr=0;reg [659:0] direct_r_context=0;
 reg [3:0] direct_q_ready=15;wire [8191:0] direct_q_data;wire [911:0] direct_q_owner;
 reg [2:0] vx_v=0;wire [2:0] vx_ready,vx_q_v;reg [2:0] vx_q_ready=7;
 reg [11:0] vx_enable=0;reg [359:0] vx_addr=0;reg [494:0] vx_context=0;
 wire [383:0] vx_q_data;wire [95:0] vx_q_cookie;
 reg [2:0] producer_w_v=0;wire [3:0] producer_w_accept,producer_w_visible,producer_w_pending;
 reg [11:0] producer_w_enable=0;reg [359:0] producer_w_addr=0;
 reg [191:0] producer_w_mask=0;reg [6143:0] producer_w_data=0;reg [659:0] producer_w_context=0;
 reg selector_w_v=0;reg [29:0] selector_w_elementaddr=0;reg [31:0] selector_w_mask=0;reg [1023:0] selector_w_data=0;
 reg [127:0] row_en=0;reg [3839:0] row_addr=0;reg [4095:0] row_data=0;
 reg [3:0] coll_en=0;reg [59:0] coll_wordaddr=0;reg [2047:0] coll_data=0;reg [329:0] direct_w_context=0;
 wire [1:0] direct_w_ready,direct_w_visible,direct_w_pending;wire [127:0] row_visible_mask;
 wire fault,quarantined;wire [7:0] debt;
 integer visible=0,rows=0,replies=0,native_row_accepts=0;reg [3:0] finished=0;
 ot_ds_native_seven_caller_service #(.ENABLE(1)) dut(.*);
 always @(posedge fast_clk)if(cold_n)begin
  for(integer c=0;c<3;c=c+1)begin
   if(producer_w_v[c]&&producer_w_accept[c])producer_w_v[c]<=0;
   if(vx_v[c]&&vx_ready[c])vx_v[c]<=0;
   if(vx_q_v[c]&&vx_q_ready[c])begin
    if(vx_q_cookie[c*32+:32]!==32'(101+c))$fatal(1,"caller cookie mismatch");
    if(vx_q_data[c*128+:32]!==32'h3f800000+c)$fatal(1,"caller data mismatch c%0d got%h",c,vx_q_data[c*128+:32]);
    replies<=replies+1;
   end
  end
  if(selector_w_v&&producer_w_accept[3])selector_w_v<=0;
  if(|producer_w_visible)begin visible<=visible+$countones(producer_w_visible);finished<=finished|producer_w_visible;end
  if(|row_visible_mask)begin rows<=rows+$countones(row_visible_mask);row_en<=row_en & ~row_visible_mask;end
  if(dut.native.accept[6])native_row_accepts<=native_row_accepts+1;
  if(fault)$fatal(1,"unexpected source integration fault");
 end
 initial begin
  repeat(4)@(negedge slow_clk);cold_n=1;fast_rst_n=1;slow_rst_n=1;
  @(negedge fast_clk);
  for(integer c=0;c<3;c=c+1)begin
   producer_w_enable[c*4]=1;producer_w_addr[c*120+:30]=4+c;
   producer_w_mask[c*64]=1;producer_w_data[c*2048+:32]=32'h3f800000+c;
   producer_w_context[c*165+:32]=101+c;
  end
  producer_w_v=7;selector_w_v=1;selector_w_elementaddr=31;selector_w_mask=32'hffffffff;
  for(integer l=0;l<32;l=l+1)selector_w_data[l*32+:32]=32'h40000000+l;
  // Keep original row offered through visible ACK; add a distinct new row while pending.
  row_en=1;row_addr[0+:30]=120;row_data[0+:32]=32'h41200000;
  wait(direct_w_pending[0]);@(negedge fast_clk);
  row_en[1]=1;row_addr[30+:30]=121;row_data[32+:32]=32'h41300000;
  wait(finished==15 && rows==2);wait(debt==0);repeat(8)@(negedge fast_clk);
  if(visible!=4 || native_row_accepts!=2 || row_en!=0)$fatal(1,"duplicate source acceptance vis%0d rows%0d accepts%0d",visible,rows,native_row_accepts);
  for(integer c=0;c<3;c=c+1)begin
   vx_enable[c*4]=1;vx_addr[c*120+:30]=(4+c)*16;vx_context[c*165+:32]=101+c;
  end
  vx_v=7;vx_q_ready=0;wait(vx_q_v[0]);repeat(7)@(negedge fast_clk);
  if(vx_q_v!=1 || !dut.arb.outstanding)$fatal(1,"shared reply lock lost");
  vx_q_ready=7;wait(replies==3);wait(debt==0);@(negedge fast_clk);
  // Actual normalized selector data is checked through native plane0's 64-element read.
  direct_r_v=1;direct_r_enable=1;direct_r_addr[0+:30]=0;
  do @(posedge fast_clk);while(!direct_r_ready[0]);@(negedge fast_clk);direct_r_v=0;
  wait(direct_q_v[0]);
  for(integer l=0;l<32;l=l+1)if(direct_q_data[(31+l)*32+:32]!==32'h40000000+l)$fatal(1,"unaligned selector lane %0d",l);
  @(negedge fast_clk);wait(debt==0);
  $display("PASS NATIVE_CALLER_SERVICE actual_macros=256 shared_writers=4 shared_VX=3 visible=4 rows=2 receipt_edge_duplicate=0 selector32_unaligned_exact=1 stalled_reply_lock=1");
  // Accepted request warm reset cannot release or reassign the locked caller.
  @(negedge fast_clk);vx_v=1;do @(posedge fast_clk);while(!vx_ready[0]);
  @(negedge fast_clk);vx_v=0;fast_rst_n=0;abort_fast=1;abort_slow=1;
  repeat(4)@(negedge fast_clk);fast_rst_n=1;abort_fast=0;abort_slow=0;
  repeat(8)@(negedge fast_clk);
  if(!quarantined || !dut.arb.outstanding || vx_ready!=0)$fatal(1,"reset erased ownership");
  $display("PASS NATIVE_CALLER_RESET outstanding_owner_quarantined=1 no_unchecked_retirement=1");$finish;
 end
 initial begin repeat(18000)@(posedge fast_clk);$fatal(1,"directed finite event bound");end
endmodule
