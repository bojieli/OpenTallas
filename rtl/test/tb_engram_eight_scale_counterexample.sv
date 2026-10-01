`timescale 1ns/1ps
module tb_engram_eight_scale_counterexample;
 localparam NC=2,NL=1,LANES=32,DW=264,BAW=5;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,in_valid=0;wire in_ready,in_slot;
 reg [7:0] in_row=0;wire [1:0]req_valid;reg[1:0]req_ready=3;
 wire[7:0]req_addr;wire[1:0]req_tag;
 reg[1:0]rsp_valid=0;wire[1:0]rsp_ready;reg[527:0]rsp_data=0;reg[1:0]rsp_tag=0;
 wire wr_en;wire[4:0]wr_addr;wire[511:0]wr_data;wire[1:0]rdy;
 ot_hdc_engram_gather #(.NL(NL),.NC(NC),.ROW_W(4),.AW(4),.OFFSETS(8'b0)) dut
 (.clk(clk),.rst_n(rst_n),.in_valid(in_valid),.in_ready(in_ready),.in_row(in_row),.in_slot(in_slot),
 .req_valid(req_valid),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),
 .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_tag(rsp_tag),
 .wr_en(wr_en),.wr_addr(wr_addr),.wr_data(wr_data),.rdy(rdy),.rel_valid(1'b0),.rel_slot(1'b0));
 reg [7:0] direct_scale=127;wire[15:0] direct_bf16;
 ot_hdc_engram_e4m3_bf16 direct(.code(8'h38),.scale(direct_scale),.bf16(direct_bf16));
 integer bank,beat,lane,writes=0,mismatches=0,control_writes=0;
 integer scales[0:7];reg[15:0]expected[0:7];integer col,b;
 always @(negedge clk)if(rst_n && wr_en)begin
  col=wr_addr[3];b=wr_addr[2:0];
  for(integer j=0;j<32;j=j+1)begin
   if(wr_data[j*16+:16]!==16'h3f80)$fatal(1,"Unexpected legacy output");
   if(col==0 && wr_data[j*16+:16]!==expected[b])mismatches=mismatches+1;
  end
  $display("WRITE column=%0d beat=%0d side_scale=%0d actual=%04h golden=%04h",col,b,col==0?scales[b]:127,wr_data[15:0],col==0?expected[b]:16'h3f80);
  writes=writes+1;if(col==1)control_writes=control_writes+1;
 end
 initial begin
  scales[0]=127;scales[1]=128;scales[2]=126;scales[3]=129;scales[4]=125;scales[5]=130;scales[6]=124;scales[7]=131;
  expected[0]=16'h3f80;expected[1]=16'h4000;expected[2]=16'h3f00;expected[3]=16'h4080;
  expected[4]=16'h3e80;expected[5]=16'h4100;expected[6]=16'h3e00;expected[7]=16'h4180;
  #1;if(direct_bf16!==16'h3f80)$fatal(1,"Decoder baseline");
  direct_scale=128;#1;if(direct_bf16!==16'h4000)$fatal(1,"Decoder scale sensitivity");
  $display("DIRECT code=38 scale127=3f80 scale128=%04h",direct_bf16);
  repeat(3)@(negedge clk);rst_n=1;
  @(negedge clk);in_valid=1;@(negedge clk);in_valid=0;
  repeat(2)@(negedge clk);
  for(bank=0;bank<2;bank=bank+1)begin
   for(beat=0;beat<8;beat=beat+1)begin
    rsp_valid=1<<bank;rsp_data=0;
    for(lane=0;lane<32;lane=lane+1)rsp_data[bank*264+lane*8+:8]=8'h38;
    rsp_data[bank*264+256+:8]=bank==0?scales[beat]:127;
    @(posedge clk);while(!rsp_ready[bank])@(posedge clk);
    @(negedge clk);
   end
   rsp_valid=0;
  end
  repeat(6)@(negedge clk);
  if(writes!=16 || mismatches!=224 || control_writes!=8 || !rdy[0])$fatal(1,"Bad witness completeness w=%0d m=%0d c=%0d rdy=%b",writes,mismatches,control_writes,rdy);
  $display("COUNTEREXAMPLE_CONFIRMED writes=%0d mismatched_BF16_elements=%0d uniform_control_writes=%0d",writes,mismatches,control_writes);$finish;
 end
 initial begin #10000;$fatal(1,"Timeout");end
endmodule
