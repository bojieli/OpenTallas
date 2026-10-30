module tb_branch_x;
 integer rank_value, count_value;
 reg [15:0] original_value, fixed_value, mutant_value;
 integer checked=0, mutant_caught=0;
 task check(input integer r,input integer c);
  begin
   rank_value=r;count_value=c;
   original_value=16'h5aa5;fixed_value=16'h5aa5;mutant_value=16'h5aa5;
   if(rank_value>count_value)begin end else original_value=16'h0140;
   if(rank_value>count_value)begin end else fixed_value=16'h0140;
   if(rank_value<=count_value)mutant_value=16'h0140;
   if(original_value!==fixed_value)$fatal(1,"literal branch differs");
   checked=checked+1;
   if(original_value!==mutant_value)mutant_caught=mutant_caught+1;
  end
 endtask
 initial begin
  check(32'd0,32'd0);check(32'd1,32'd0);check(32'd0,32'd1);
  check(32'bx,32'd0);check(32'd1,32'bx);check(32'bx,32'bx);
  check(32'h7fffffff,32'd0);check(-32'd1,32'd0);
  if(mutant_caught!=3)$fatal(1,"X-loss mutant not detected");
  $display("BRANCH_X PASS checked=%0d mismatches=0 X_loss_mutant_caught=%0d",checked,mutant_caught);
  $finish;
 end
endmodule
