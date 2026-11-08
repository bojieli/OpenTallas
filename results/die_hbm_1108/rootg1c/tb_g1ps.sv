`timescale 1ns/1ps
// DIE-HBM-92-OPEN/ROOTG1C: old ot_wbq_root_g1 (ot_wbq_root_grp G=1, one 128x256 payload per lane) vs new ot_wbq_root_g1
// (ot_wbq_root_grp_ps, 2 x 128x128 per lane), behavioural SRAM models for both, random stimulus, every output compared
// on every hbm and fifo edge. Define MUT_SWAP to build the mutant (halves swapped on read) the bench must catch.
module tb;
reg fifo_clk=0,hbm_clk=0;always #5 fifo_clk=~fifo_clk;always #7 hbm_clk=~hbm_clk;
reg stream_rst_n=0,hbm_rst_n=0;reg[1:0]root_id=0;
reg reserve_v=0,reserve_bank=0,fill_start=0,fill_start_bank=0;reg[11:0]reserve_total=256;reg[29:0]reserve_base=0;
reg[255:0]wd[0:3];reg[3:0]wd_v=15;reg copy_on=0,copy_bank=0,s_stop=0,h_stop=0;reg g_credit=0;
wire gv0,gv1,rr0,rr1;wire[285:0]gd0,gd1;integer errs=0,checks=0,sends=0,dsends=0;reg active=0;reg[31:0]seed=32'h1d872b41;
function[31:0] rnd;input[31:0]x;begin rnd={x[30:0],x[31]^x[21]^x[1]^x[0]};end endfunction
ot_wbq_root_grp #(.G(1)) u_old(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),
 .reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),
 .fill_start_bank(fill_start_bank),.wd0(wd[0]),.wd1(wd[1]),.wd2(wd[2]),.wd3(wd[3]),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),
 .s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit),.root_ready(rr0),.g_v(gv0),.g_d(gd0));
ot_wbq_root_g1 u_new(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),
 .reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),
 .fill_start_bank(fill_start_bank),.wd0(wd[0]),.wd1(wd[1]),.wd2(wd[2]),.wd3(wd[3]),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),
 .s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit),.root_ready(rr1),.g_v(gv1),.g_d(gd1));
always @(negedge fifo_clk)begin
 if(active)begin seed=rnd(seed);s_stop=seed[4:0]==0;seed=rnd(seed);wd_v=seed[3:0]|{3'b0,seed[7]};
  for(integer i=0;i<4;i=i+1)for(integer j=0;j<8;j=j+1)begin seed=rnd(seed);wd[i][32*j+:32]=seed;end
  checks=checks+1;if(rr0!==rr1)errs=errs+1; end
end
reg [285:0] last_gd=0;
always @(negedge hbm_clk)begin
 if(active)begin
  checks=checks+1;
  if(rr0!==rr1||gv0!==gv1)errs=errs+1;
  if(gv0)begin sends=sends+1;if(gd0!==gd1)errs=errs+1;if(gd0[255:0]!=0 && gd0[255:0]!=last_gd[255:0])dsends=dsends+1;last_gd=gd0;end
  seed=rnd(seed);g_credit=gv0|(seed[2:0]==0);h_stop=seed[6:3]==1;
 end
end
initial begin
 #1;repeat(8)@(negedge fifo_clk);stream_rst_n=1;hbm_rst_n=1;repeat(8)@(negedge fifo_clk);active=1;
 for(integer n=0;n<40;n=n+1)begin
  @(negedge fifo_clk);root_id=n%4;reserve_bank=n%2;fill_start_bank=n%2;copy_bank=n%2;reserve_base=n*1024+n;reserve_total=12'(256-8*(n%3));reserve_v=1;
  @(negedge fifo_clk);reserve_v=0;fill_start=1;
  @(negedge fifo_clk);fill_start=0;
  repeat(90)@(negedge fifo_clk);copy_on=1;
  repeat(700)@(negedge fifo_clk);copy_on=0;
  repeat(20)@(negedge fifo_clk);
 end
 $display("G1PS checks=%0d sends=%0d data_sends=%0d mismatch=%0d",checks,sends,dsends,errs);
 if(sends<1000||dsends<500||errs!=0)$display("FAIL");
 else $display("PASS");
 $finish;
end
endmodule
