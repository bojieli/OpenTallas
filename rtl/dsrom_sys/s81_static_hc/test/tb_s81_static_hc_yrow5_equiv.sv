`timescale 1ns/1ps
// y_row5 additive-change equivalence: the pre-change assembler (origin/main 289b44007, module renamed
// s81_static_hc_assemble_clocked_base by the check script, no other edit) and the new one run in lockstep on
// the same random calendar stimulus (legal rows, illegal writes/emits, tag mismatches, resets); every
// pre-existing output (row_valid, row_data, row_tag, fault) must be bit- and edge-identical on every cycle.
module tb_s81_static_hc_yrow5_equiv;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,write_slot=0,word_valid=0,word_error=0,emit_slot=0;
 reg[3:0]word_index=0;reg[511:0]word_data=0;reg[31:0]word_tag=0,emit_tag=0;reg[4:0]word_row=0;
 wire rv0,rv1,f0,f1;wire[8191:0]rd0,rd1;wire[31:0]rt0,rt1;wire[4:0]y5;
 s81_static_hc_assemble_clocked_base base(.clk_lane({16{clk}}),.clk_control(clk),.rst_n(rst_n),.write_slot(write_slot),
  .word_index(word_index),.word_valid(word_valid),.word_data(word_data),.word_tag(word_tag),.word_error(word_error),
  .emit_slot(emit_slot),.emit_tag(emit_tag),.row_valid(rv0),.row_data(rd0),.row_tag(rt0),.fault(f0));
 s81_static_hc_assemble_clocked dut(.clk_lane({16{clk}}),.clk_control(clk),.rst_n(rst_n),.write_slot(write_slot),
  .word_index(word_index),.word_valid(word_valid),.word_data(word_data),.word_tag(word_tag),.word_row(word_row),.word_error(word_error),
  .emit_slot(emit_slot),.emit_tag(emit_tag),.row_valid(rv1),.row_data(rd1),.row_tag(rt1),.row_y5(y5),.fault(f1));
 integer seed=32'h5e9,cyc=0,rows=0,i,k,r;
 always @(posedge clk)begin
  #1 cyc=cyc+1;
  if({rv0,rd0,rt0,f0}!=={rv1,rd1,rt1,f1})$fatal(1,"existing output diverged cycle %0d",cyc);
  if(rv1)rows=rows+1;
 end
 initial begin
  repeat(2)@(negedge clk);rst_n=1;
  for(r=0;r<400;r=r+1)begin
   // one row: 16 words in a random order with random idle gaps, then an emit; ~1/8 rows carry an illegal event
   k=$random(seed);
   for(i=0;i<16;i=i+1)begin
    @(negedge clk);write_slot=1;word_valid=1;word_index=(i*7+r)%16;word_data={16{$random(seed)}};
    word_tag=32'h4000+r;word_row=5'(r);word_error=(k%64==1&&i==3);
    if(k%64==2&&i==5)word_tag=32'hdead;
    if(k%64==3&&i==9)word_valid=0;
    @(negedge clk);write_slot=0;word_valid=(k%64==4&&i==2);word_error=0;
    repeat($unsigned($random(seed))%3)@(negedge clk);
   end
   @(negedge clk);emit_slot=1;emit_tag=(k%64==5)?32'hbeef:32'h4000+r;
   @(negedge clk);emit_slot=0;
   if(k%32==6)begin rst_n=0;@(negedge clk);rst_n=1;end
  end
  repeat(4)@(negedge clk);
  if(rows<300)$fatal(1,"too few legal rows %0d",rows);
  $display("PASS y_row5 equivalence: %0d cycles, %0d emitted rows, row_valid/row_data/row_tag/fault identical to base",cyc,rows);
  $finish;
 end
endmodule
