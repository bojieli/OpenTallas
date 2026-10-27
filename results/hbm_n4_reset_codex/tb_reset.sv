`timescale 1ps/1ps
module tb_reset;
reg clk=0; always #5 clk=~clk;
reg delivered=0;wire[3:0]oldq,newq;
ot_rst_relay #(.REGIONS(4)) gold(clk,delivered,oldq);
ot_hnx_fused_delivered_reset #(.REGIONS(4)) dut(clk,delivered,newq);
integer checks=0,errors=0;reg mutate=0;reg[3:0] got;
task tick;@(negedge clk);#1;endtask
task check_release;
 for(integer e=0;e<7;e=e+1)begin
  tick;checks=checks+1;got=mutate?{4{dut.g_region[0].pipe[1]}}:newq;
  if(got!==oldq)begin errors=errors+1;if(errors<4)$display("RESET_DIFFER old=%h new=%h edge%0d",oldq,got,e);end
 end
endtask
initial begin
 mutate=$test$plusargs("MUT_EARLY");
 repeat(6)tick;
 for(integer phase=0;phase<16;phase=phase+1)begin
  delivered=0;repeat(4+phase%3)tick;
  if(newq!==0)$fatal(1,"delivered assertion failed after three timed edges");
  delivered=1;check_release();
 end
 $display("DELIVERED_RESET checks%0d errors%0d release3 assert3 no_async",checks,errors);
 if(errors)$fatal(1,"reset date changed");$finish;
end
endmodule
