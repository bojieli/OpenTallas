`timescale 1ns/1ps
module tb_query_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,frame_start=0,block_v=0,emit_v=0;
 reg [4:0]block_head=0,emit_head=0;reg[1:0]block_number=0;
 reg [1023:0]block_data=0;reg[15:0]head_weight=0;
 wire ql_v;wire[7:0]ql_head;wire[511:0]ql_codes;wire[31:0]ql_sc;wire[15:0]ql_w;wire fault;
 ot_hbm_idx_query_static dut(.clk(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_bank({4{clk}}),.*);
 reg[1023:0]x[0:127];reg[559:0]gold[0:31];integer errors=0,checked=0;
 always @(negedge clk)begin
  if(ql_v)begin
   checked++;
   if({ql_w,ql_sc,ql_codes}!==gold[ql_head])begin errors++;$display("MISMATCH head%0d",ql_head);end
  end
 end
 initial begin
  $readmemh("query.hex",x);$readmemh("gold.hex",gold);
  repeat(4)@(negedge clk);rst_n=1;frame_start=1;
  @(negedge clk);frame_start=0;
  for(integer b=0;b<128;b=b+1)begin
   block_v=1;block_head=5'(b/4);block_number=2'(b);
   if(MUT==2&&b==127)block_number=2'd2;
   block_data=x[b];if(MUT==1&&b==34)block_data=0;
   head_weight=16'h3f00+16'(b/4);@(negedge clk);
  end
  block_v=0;
  if(MUT!=3)repeat(18)@(negedge clk);
  for(integer h=0;h<32;h=h+1)begin emit_v=1;emit_head=5'((MUT==3)?((h==0)?31:h-1):h);@(negedge clk);end
  emit_v=0;repeat(4)@(negedge clk);
  $display("IDX_QUERY_STATIC MUT%0d checked%0d errors%0d fault%0d",MUT,checked,errors,fault);
  if(errors||fault||checked!=32)$fatal(1,"exact32head static query gate");
  $finish;
 end
endmodule
