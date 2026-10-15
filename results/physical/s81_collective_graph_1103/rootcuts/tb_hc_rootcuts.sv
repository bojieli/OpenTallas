`timescale 1ns/1ps
module tb_hc_rootcuts;
reg[15:0]clk_lane=0;reg clk_control=0,rst_n=0,reduce_slot=0;reg[3:0]rank_valid=0;reg[2047:0]rank_data=0;reg[31:0]tag=0;reg[15:0]seq=0;reg last=0;reg assemble_slot=0;reg[3:0]word_index=0;reg emit_slot=0;reg[31:0]emit_tag=0;
integer checks=0;integer cycles=0;integer skew=0;
always #50 clk_control=~clk_control;
genvar lane;generate for(lane=0;lane<16;lane=lane+1)begin:C initial begin if($test$plusargs("SKEW")) #(1+lane); else #1; forever begin #49; clk_lane[lane]=~clk_lane[lane]; #1; end end end endgenerate
wire[0:0]g_word_valid,n_word_valid;
wire[511:0]g_word_data,n_word_data;
wire[31:0]g_word_tag,n_word_tag;
wire[15:0]g_word_seq,n_word_seq;
wire[0:0]g_word_last,n_word_last;
wire[0:0]g_word_error,n_word_error;
wire[0:0]g_reduce_fault,n_reduce_fault;
wire[0:0]g_row_valid,n_row_valid;
wire[8191:0]g_row_data,n_row_data;
wire[31:0]g_row_tag,n_row_tag;
wire[0:0]g_assemble_fault,n_assemble_fault;
s81_static_hc_roots_reference g(.clk_lane(clk_lane),.clk_control(clk_control),.rst_n(rst_n),.reduce_slot(reduce_slot),.rank_valid(rank_valid),.rank_data(rank_data),.tag(tag),.seq(seq),.last(last),.assemble_slot(assemble_slot),.word_index(word_index),.emit_slot(emit_slot),.emit_tag(emit_tag),.word_valid(g_word_valid),.word_data(g_word_data),.word_tag(g_word_tag),.word_seq(g_word_seq),.word_last(g_word_last),.word_error(g_word_error),.reduce_fault(g_reduce_fault),.row_valid(g_row_valid),.row_data(g_row_data),.row_tag(g_row_tag),.assemble_fault(g_assemble_fault));
s81_static_hc_roots n(.clk_lane(clk_lane),.clk_control(clk_control),.rst_n(rst_n),.reduce_slot(reduce_slot),.rank_valid(rank_valid),.rank_data(rank_data),.tag(tag),.seq(seq),.last(last),.assemble_slot(assemble_slot),.word_index(word_index),.emit_slot(emit_slot),.emit_tag(emit_tag),.word_valid(n_word_valid),.word_data(n_word_data),.word_tag(n_word_tag),.word_seq(n_word_seq),.word_last(n_word_last),.word_error(n_word_error),.reduce_fault(n_reduce_fault),.row_valid(n_row_valid),.row_data(n_row_data),.row_tag(n_row_tag),.assemble_fault(n_assemble_fault));
always @(negedge clk_control)begin
 cycles=cycles+1;
 if(cycles==4)rst_n=1;
 if(cycles==600)rst_n=0;
 if(cycles==606)rst_n=1;
 if(cycles>12)begin
  reduce_slot=(cycles%24)==0;
  rank_valid=reduce_slot?4'hf:0;
  if(cycles>900 && cycles%37==0)rank_valid=4'h7;
  for(integer i=0;i<64;i=i+1)rank_data[i*32+:32]=32'h3f000000+(i<<12)+cycles;
  tag=32'h12345000+(cycles/384);seq=16'(cycles);last=cycles[4];
  assemble_slot=(cycles%24)==19;word_index=4'(cycles/24);
  emit_slot=(cycles%384)==382;emit_tag=tag;
 end
end
always @(clk_control or clk_lane)begin
 #0.01;
 if(cycles>30)begin
 if(g_word_valid!==n_word_valid)$fatal(1,"HC_ROOTCUT mismatch word_valid cycle%0d",cycles);
 if(g_word_data!==n_word_data)$fatal(1,"HC_ROOTCUT mismatch word_data cycle%0d",cycles);
 if(g_word_tag!==n_word_tag)$fatal(1,"HC_ROOTCUT mismatch word_tag cycle%0d",cycles);
 if(g_word_seq!==n_word_seq)$fatal(1,"HC_ROOTCUT mismatch word_seq cycle%0d",cycles);
 if(g_word_last!==n_word_last)$fatal(1,"HC_ROOTCUT mismatch word_last cycle%0d",cycles);
 if(g_word_error!==n_word_error)$fatal(1,"HC_ROOTCUT mismatch word_error cycle%0d",cycles);
 if(g_reduce_fault!==n_reduce_fault)$fatal(1,"HC_ROOTCUT mismatch reduce_fault cycle%0d",cycles);
 if(g_row_valid!==n_row_valid)$fatal(1,"HC_ROOTCUT mismatch row_valid cycle%0d",cycles);
 if(g_row_data!==n_row_data)$fatal(1,"HC_ROOTCUT mismatch row_data cycle%0d",cycles);
 if(g_row_tag!==n_row_tag)$fatal(1,"HC_ROOTCUT mismatch row_tag cycle%0d",cycles);
 if(g_assemble_fault!==n_assemble_fault)$fatal(1,"HC_ROOTCUT mismatch assemble_fault cycle%0d",cycles);
 checks=checks+1;
 end
end
initial begin #150050; $display("PASS HC_ROOTCUT equivalence cycles=%0d checks=%0d reset_reassert=1",cycles,checks);$finish;end
endmodule
