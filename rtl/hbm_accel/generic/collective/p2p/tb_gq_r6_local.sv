`timescale 1ns/1ps
module tb_gq_r6_local;
 reg clk=0,rst_n=1;wire[7:0]old_n,new_n;
 reg[15:0]tl=0,per=1,lps=2;wire[3:0]wrap;
 integer checks=0;reg[31:0]rng=32'h6a09e667;
 ot_rst_relay #(.REGIONS(8)) ref_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(old_n));
 ot_hgi_coll_gq_request_reset dut_rst(.clk(clk),.rst_n(rst_n),.q(new_n));
 for(genvar j=0;j<4;j=j+1)begin:g_w ot_hgi_coll_gq_wrap_local u(.tl(tl),.per(per),.lps(lps),.q(wrap[j]));end
 task check_reset;begin #1;checks=checks+1;if(new_n!==old_n)$fatal(1,"R6_RESET_EQ_FAIL clk%b rst%b old%h new%h",clk,rst_n,old_n,new_n);end endtask
 task step;begin clk=0;#2;clk=1;check_reset();clk=0;#2;end endtask
 initial begin
  // Assert with stopped clock, then compare each of the exact three release edges.
  for(integer e=0;e<64;e=e+1)begin
   clk=0;rst_n=0;check_reset();repeat(3)begin #2;check_reset();end
   rst_n=1;check_reset();step();step();step();step();
   if(new_n!==8'hff)$fatal(1,"R6_RESET_NOT_READY_EDGE3");
   step();clk=1;rst_n=0;check_reset();clk=0;check_reset();
  end
  for(integer n=0;n<10000;n=n+1)begin
   rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
   per=(n<8)?16'(n):rng[15:0];tl=(n%2==0)?per-16'd1:rng[31:16];lps=(n<8)?16'(n%4):rng[31:16];
   #1;checks=checks+1;
   if(wrap!=={4{(tl==per-16'd1)&&(lps>16'd1)}})$fatal(1,"R6_WRAP_EQ_FAIL n%0d",n);
  end
  $display("R6_LOCAL_PASS checks%0d reset64epochs stoppedclock releaseedges3 wrap10000 copies4 added_boot_edges0 added_data_edges0",checks);$finish;
 end
endmodule
