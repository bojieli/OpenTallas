`timescale 1ns/1ps
module tb;
reg fifo_clk=0,hbm_clk=0;always #5 fifo_clk=~fifo_clk;always #7 hbm_clk=~hbm_clk;
reg stream_rst_n=0,hbm_rst_n=0;reg[1:0]root_id=0;
reg reserve_v=0,reserve_bank=0,fill_start=0,fill_start_bank=0;reg[11:0]reserve_total=256;reg[29:0]reserve_base=0;
reg[255:0]wd[0:7];reg[7:0]wd_v=255;reg copy_on=0,copy_bank=0,s_stop=0,h_stop=0;reg[1:0]g_credit=0;
wire[1:0]gv[0:1];wire[571:0]gd[0:1];wire rr[0:1];integer errs=0,checks=0,writes=0,cyc=0;reg active=0;reg[31:0]seed=32'h12345;
function[31:0] rnd;input[31:0]x;begin rnd={x[30:0],x[31]^x[21]^x[1]^x[0]};end endfunction
ot_wbq_root_ref u0(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd[0]),.wd1(wd[1]),.wd2(wd[2]),.wd3(wd[3]),.wd4(wd[4]),.wd5(wd[5]),.wd6(wd[6]),.wd7(wd[7]),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit),.g_v(gv[0]),.g_d(gd[0]),.root_ready(rr[0]));
ot_wbq_root #(.STORE_GROUP4(1)) u1(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd[0]),.wd1(wd[1]),.wd2(wd[2]),.wd3(wd[3]),.wd4(wd[4]),.wd5(wd[5]),.wd6(wd[6]),.wd7(wd[7]),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit),.g_v(gv[1]),.g_d(gd[1]),.root_ready(rr[1]));
always @(negedge fifo_clk)begin
 if(active)begin seed=rnd(seed);s_stop=seed[3:0]==0;for(integer i=0;i<8;i=i+1)begin for(integer j=0;j<8;j=j+1)begin seed=rnd(seed);wd[i][32*j+:32]=seed;end end end
end
always @(negedge hbm_clk)begin
 if(active)begin
  checks=checks+1;cyc=cyc+1;
  if(rr[0]!==rr[1]||gv[0]!==gv[1])errs=errs+1;
  for(integer g=0;g<2;g=g+1)if(gv[0][g])begin writes=writes+1;if(gd[0][286*g+:286]!==gd[1][286*g+:286])errs=errs+1;end
  g_credit=gv[0];h_stop=seed[5:2]==1;
 end
end
initial begin
 #1;stream_rst_n=0;hbm_rst_n=0;repeat(8)@(negedge fifo_clk);stream_rst_n=1;hbm_rst_n=1;repeat(8)@(negedge fifo_clk);active=1;
 for(integer n=0;n<12;n=n+1)begin
  @(negedge fifo_clk);root_id=n%4;reserve_bank=n%2;fill_start_bank=n%2;copy_bank=n%2;reserve_base=n*1024;reserve_total=256;reserve_v=1;
  @(negedge fifo_clk);reserve_v=0;fill_start=1;
  @(negedge fifo_clk);fill_start=0;
  repeat(80)@(negedge fifo_clk);copy_on=1;
  repeat(700)@(negedge fifo_clk);copy_on=0;
  repeat(20)@(negedge fifo_clk);
 end
 $display("ROOT_STORE checks=%0d writes=%0d mismatch=%0d",checks,writes,errs);
 if(writes<100||errs!=0)$fatal(1,"FAIL");$display("PASS");$finish;
end
endmodule
