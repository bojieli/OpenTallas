`timescale 1ps/1ps
module tb_quarter_reset;
reg clk=0;initial forever begin #416 clk=1;#417 clk=0;end
wire[1:0]cp={clk,clk};
reg delivered=0,mutate=0;
wire[0:0]gc,nc;wire[4:0]gg,ng,gt,nt;wire[1:0]gh,nh;
ot_rst_relay #(.REGIONS(1)) gold_ctl(clk,delivered,gc);
ot_rst_delivered3 #(.REGIONS(1)) new_ctl(clk,delivered,nc);
ot_rst_relay #(.REGIONS(5)) gold_glue(clk,gc[0],gg);
ot_rst_delivered3 #(.REGIONS(5)) new_glue(clk,nc[0],ng);
ot_rst_relay #(.REGIONS(5)) gold_tail(clk,gc[0],gt);
ot_rst_delivered3 #(.REGIONS(5)) new_tail(clk,nc[0],nt);
for(genvar r=0;r<2;r=r+1)begin:g_region
 ot_rst_relay #(.REGIONS(1)) gold_hcol(cp[r],gg[0],gh[r]);
 ot_rst_delivered3 #(.REGIONS(1)) new_hcol(cp[r],ng[0],nh[r]);
end
integer checks=0,errors=0;reg[1:0]observed;
task tick;@(negedge clk);#1;endtask
initial begin
 mutate=$test$plusargs("MUT_EARLY");
 repeat(14)tick;
 for(integer phase=0;phase<16;phase=phase+1)begin
  delivered=0;repeat(12+phase%3)tick;
  if({nc,ng,nt,nh}!==0)$fatal(1,"nested timed assertion did not flush");
  delivered=1;
  for(integer e=0;e<14;e=e+1)begin
   tick;checks=checks+1;
   observed=mutate?{2{g_region[0].new_hcol.g_region[0].pipe[1]}}:nh;
   if({nc,ng,nt,observed}!=={gc,gg,gt,gh})begin
    errors=errors+1;if(errors<4)$display("RESET_DATE_MISMATCH phase%0d edge%0d",phase,e);
   end
  end
 end
 $display("QUARTER_DELIVERED_RESET checks%0d errors%0d ctl3 glue6 tail6 hcol9 two_preserved_clocks833",checks,errors);
 if(errors)$fatal(1,"reset/clock date changed");
 $finish;
end
endmodule
