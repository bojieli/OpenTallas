module tb;
 reg clk=0, raw=0, parent_start=0; always #5 clk=~clk;
 reg fixed_raw=0, gated=0, old_start=0,new_start=0;
 always @(posedge clk) begin
  fixed_raw<=raw;
  gated<=raw && old_start;
  if(!gated)old_start<=0;else old_start<=parent_start;
  if(!fixed_raw)new_start<=0;else new_start<=parent_start;
 end
 initial begin
  repeat(2)@(negedge clk);raw=1;
  repeat(2)@(negedge clk);parent_start=1;
  repeat(5)@(negedge clk);
  if(new_start!==1 || old_start!==0)$fatal(1,"unexpected reset witness");
  $display("RESET_WITNESS_PASS fixed_start=%0b gated_mutant_start=%0b",new_start,old_start);$finish;
 end
endmodule
