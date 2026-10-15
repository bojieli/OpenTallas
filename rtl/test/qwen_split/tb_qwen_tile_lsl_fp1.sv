`timescale 1ns/1ps
module tb_qwen_tile_lsl_fp1;
 reg clk=0,rst_n=0,v_d=0,first_d=0;
 reg [3:0]split_d=0;reg [255:0]w_d=0;reg [127:0]x_d=0;
 always #5 clk=!clk;
 wire [63:0] old_t,t_out;wire [7:0]old_l,lfault;wire old_f,tfault;
 // the DUT's reset pin register releases one edge after rst_n: the golden legacy leaf sees the same released reset
 reg rst_g=0; always @(posedge clk or negedge rst_n) if(!rst_n) rst_g<=0; else rst_g<=1;
 ot_qwen_tile_lsl golden(.clk(clk),.rst_n(rst_g),.v_d(v_d),.first_d(first_d),.split_d(split_d),.w_d(w_d),.x_d(x_d),.t_out(old_t),.lfault(old_l),.tfault(old_f));
 ot_qwen_tile_lsl_fp1 dut(.*);
 reg [8:0] prev_fault=0;integer checks=0,events=0,c=0,j=0;
 wire [8:0] observed={tfault,lfault};
 always @(negedge clk) begin
  if(!rst_n)prev_fault=0;
  else begin
   if(c>80 && t_out!==old_t)$fatal(1,"data arithmetic/order changed cycle%0d",c);
   if(observed!==prev_fault)$fatal(1,"fault pin latency mismatch cycle%0d got%h want%h",c,observed,prev_fault);
   checks=checks+1; if(|{old_f,old_l})events=events+1;
   prev_fault={old_f,old_l};
  end
 end
 initial begin
  repeat(4)@(posedge clk);#1;rst_n=1;
  for(c=0;c<600;c=c+1)begin
   @(posedge clk);#1;
   v_d=(c%8==0 || c%8==1);first_d=(c%16<8);split_d=c%3;
   for(j=0;j<8;j=j+1)w_d[j*32+:32]=(c%13<4)?32'h7f800000:(c%13<7)?32'h7fc00000:$random;
   for(j=0;j<4;j=j+1)x_d[j*32+:32]=(c%17<6)?32'h7f800000:$random;
  end
  v_d=0;repeat(80)@(posedge clk);#1;
  if(events<10 || checks<600)$fatal(1,"missing actual fault activity checks%0d events%0d",checks,events);
  $display("PASS lane fault-pin data exact checks%0d actual_fault_edges%0d, one edge latency",checks,events);$finish;
 end
endmodule
