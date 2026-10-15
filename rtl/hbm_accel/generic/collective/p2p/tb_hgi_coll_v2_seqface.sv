`timescale 1ns/1ps
module tb_hgi_coll_v2_seqface;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [1535:0] inst=0;reg [31:0] iteration=0;
 wire [47:0] wr,rd,rx;wire fault;
 ot_hgi_coll_q_static_ctl_v2 #(.NPT(3)) dut(.clk_control(clk),.rst_n(rst_n),.inst(inst),.iteration(iteration),
  .hgi_start(1'b0),.hgi_busy(1'b0),.issue_done(1'b0),.tkm_done(1'b0),.tkm_busy(1'b0),
  .dest_v(16'd0),.rc_v(1'b0),.rc_tag(3'd0),.vm_rr(2056'd0),
  .wr_sequence_pin(wr),.rd_sequence_pin(rd),.rx_sequence_pin(rx),.protocol_fault(fault));
 task word(input [15:0] seq,input [31:0] it,input [7:0] step);
  begin
   @(negedge clk);inst=0;iteration=it;inst[353+:6]=seq[5:0];inst[1415+:10]=seq[15:6];
   inst[374+:6]=seq[5:0];inst[1445+:10]=seq[15:6];
   inst[395+:6]=seq[5:0];inst[1475+:10]=seq[15:6];inst[1407+:8]=step;
  end
 endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  word(16'd63,32'd64,8'd1);@(posedge clk);#1;
  if(wr[15:0]!==127 || rd[15:0]!==127 || rx[15:0]!==127 || fault)$fatal(1,"full sequence registration");
  word(16'd65000,32'd1,8'd255);@(posedge clk);#1;
  if(wr[15:0]!==65255 || fault)$fatal(1,"high sequence metadata");
  word(16'd65535,32'd1,8'd1);@(posedge clk);#1;
  if(wr[15:0]!==0 || fault)$fatal(1,"overflow should wait for reserved consumption");
  word(0,0,0);inst[392]=1;@(posedge clk);#1;
  if(!fault)$fatal(1,"registered overflow consumption must fault");
  $display("HCOLL_V2_SEQFACE PASS full16 iteration arithmetic registered metadata overflow consumption");$finish;
 end
endmodule
