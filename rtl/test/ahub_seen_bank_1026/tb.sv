module tb #(parameter MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg[4:0] rn=0;reg start_b=0;reg[3:0]z_b=0,lm_b=0,done_slot=0,any_b=0;reg[7:0]hh_b=0;reg[15:0]k_b=0;
 wire[511:0]r,d;
 seen_ref u_ref(.*,.q(r));
 seen_dut u_dut(.clk(clk),.rn(MUT ? {rn[4:2],rn[4],rn[0]}:rn),.start_b(start_b),.z_b(z_b),.lm_b(lm_b),.done_slot(done_slot),.any_b(any_b),.hh_b(hh_b),.k_b(k_b),.q(d));
 integer errs=0,checks=0;
 initial begin
  repeat(4)@(negedge clk);
  for(integer c=0;c<12000;c=c+1)begin
   @(negedge clk);
   if(r!==d)errs++;
   checks++;
   rn=5'b11111;
   if(c%197==0)rn[1]=0;
   if(c%239==0)rn[4]=0;
   start_b=(c%53==0);z_b=$urandom;hh_b=$urandom;k_b=$urandom;lm_b=$urandom;done_slot=$urandom;any_b=$urandom;
  end
  $display("RESULT checks=%0d errors=%0d mutant=%0d",checks,errs,MUT);
  if(!MUT && errs!=0)$fatal(1,"lockstep mismatch");
  if(MUT && errs==0)$fatal(1,"reset bank mutant not caught");
  $finish;
 end
endmodule
