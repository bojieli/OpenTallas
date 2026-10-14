`timescale 1ns/1ps
module tb_hgi_hc_quarter_link6;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[139:0]dn_i=0;reg[89:0]ck_i=0;reg[258:0]sc_i=0;reg[7:0]fb_i=0;
 wire[139:0]dn_o;wire[89:0]ck_o;wire[258:0]sc_o;wire[7:0]fb_o;
`ifdef LINK_ASSOC_MUT
 ot_hgi_hc_quarter_link6_assoc_mut dut(.*);
`else
 ot_hgi_hc_quarter_link6 dut(.*);
`endif
 reg[496:0]expect_q[0:5];integer i,j,errors=0,checks=0;reg enabled=0;
 always @(posedge clk)begin
  if(enabled)begin
   for(integer k=5;k>0;k=k-1)expect_q[k]=expect_q[k-1];
   expect_q[0]={dn_i,ck_i,sc_i,fb_i};
   #1;checks++;
   if(dn_o[139]!==expect_q[5][496]||ck_o[89:88]!==expect_q[5][356:355]||sc_o[258]!==expect_q[5][266]||fb_o!==expect_q[5][7:0])errors++;
   if(expect_q[5][496]&&dn_o!==expect_q[5][496:357])errors++;
   if((|expect_q[5][356:355])&&ck_o!==expect_q[5][356:267])errors++;
   if(expect_q[5][266]&&sc_o!==expect_q[5][266:8])errors++;
  end
 end
 task initialize;begin
  enabled=0;dn_i=0;ck_i=0;sc_i=0;fb_i=0;
  for(integer k=0;k<6;k=k+1)expect_q[k]=0;
  repeat(3)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);enabled=1;
 end endtask
 task stream(input integer seed);begin
  for(integer n=0;n<32;n=n+1)begin
   @(negedge clk);dn_i={1'b1,11'(n+seed),128'(n*17+seed)};
   ck_i={2'(n%3),44'(n*23+seed),44'(n*31+seed+4)};
   sc_i={1'b1,2'(n%4),256'(n*41+seed)};fb_i=8'(n+seed);
  end
  @(negedge clk);dn_i=0;ck_i=0;sc_i=0;fb_i=0;repeat(8)@(negedge clk);
 end endtask
 initial begin
  initialize();stream(7);
  // Abort live captures; pending valid/status must disappear and no earlier data may reappear after reset.
  @(negedge clk);dn_i='1;ck_i='1;sc_i='1;fb_i='1;repeat(2)@(negedge clk);enabled=0;rst_n=0;#1;
  if(dn_o[139]||(|ck_o[89:88])||sc_o[258]||(|fb_o))errors++;
  initialize();stream(99);
  enabled=0;if(errors==0)$display("HC_QUARTER_LINK PASS checks=%0d",checks);else $display("HC_QUARTER_LINK FAIL errors=%0d checks=%0d",errors,checks);$finish;
 end
endmodule
