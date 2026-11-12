`timescale 1ns/1ps
module ot_sram_1r1w_128x256_m1_r0c0_g256(input wire clk,r_ce_in,input wire [6:0] r_addr_in,output reg [255:0] rd_out,input wire w_ce_in,input wire [6:0] w_addr_in,input wire [255:0] wd_in,input wire w_mask_in);
 reg [255:0] mem[0:127]; integer i; initial for(i=0;i<128;i=i+1) mem[i]={8{32'h1234_0000+i}};
 always @(posedge clk) begin if(w_ce_in) mem[w_addr_in]<=wd_in; if(r_ce_in) rd_out<=mem[r_addr_in]; end
endmodule
module bench;
 parameter integer MUTANT=0; // 0 none, 1: DUT output delayed one cycle too many (checked as shift mismatch), 2: data bit flip
 reg hbm_clk=0,fifo_clk=0; always #1.5 hbm_clk=~hbm_clk; always #2.5 fifo_clk=~fifo_clk;
 reg stream_rst_n=0,hbm_rst_n=0;
 reg [1:0] root_id=0; reg reserve_v=0,reserve_bank=0; reg [11:0] reserve_total=0; reg [29:0] reserve_base=0;
 reg fill_start=0,fill_start_bank=0; reg [255:0] wd0,wd1,wd2,wd3; reg [3:0] wd_v=0;
 reg copy_on=0,copy_bank=0,s_stop=0,h_stop=0,g_credit=0;
 wire r_ready,rv,dv; wire [285:0] rd,dd; wire d_ready;
 ot_wbq_root_s7_grp #(.G(0),.CRED(4),.GREG(0)) ref0(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd0),.wd1(wd1),.wd2(wd2),.wd3(wd3),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit),.root_ready(r_ready),.g_v(rv),.g_d(rd));
 ot_wbq_root_s7_grp #(.G(0),.CRED(4),.GREG(1)) dut0(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd0),.wd1(wd1),.wd2(wd2),.wd3(wd3),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit),.root_ready(d_ready),.g_v(dv),.g_d(dd));
 // reference delayed by one hbm_clk
 reg rv_q0,rv_q1; reg [285:0] rd_q0,rd_q1; always @(posedge hbm_clk) begin rv_q0<=rv; rd_q0<=rd; rv_q1<=rv_q0; rd_q1<=rd_q0; end
 wire rv_q = (MUTANT==1) ? rv_q1 : rv_q0; wire [285:0] rd_q = (MUTANT==1) ? rd_q1 : rd_q0;
 wire [285:0] dd_m = (MUTANT==2) ? (dd ^ 286'd1) : dd;
 integer errs=0, nvalid=0, cyc=0, k;
 // compare just before each hbm_clk edge (values of the previous cycle), after reset released
 reg chk=0;
 always @(negedge hbm_clk) if(chk) begin
   cyc=cyc+1;
   if(dv!==rv_q || dd_m!==rd_q) errs=errs+1;
   if(rv_q) nvalid=nvalid+1;
 end
 always @(posedge fifo_clk) begin wd0<={8{$urandom}};wd1<={8{$urandom}};wd2<={8{$urandom}};wd3<={8{$urandom}}; end
 always @(posedge hbm_clk) begin g_credit <= ($urandom%4!=0); h_stop <= ($urandom%16==0); end
 initial begin
   repeat(10) @(posedge fifo_clk); stream_rst_n=1; hbm_rst_n=1; repeat(8) @(posedge fifo_clk);
   @(posedge fifo_clk); reserve_v<=1; reserve_bank<=0; reserve_total<=12'd256; reserve_base<=30'd1000; @(posedge fifo_clk); reserve_v<=0;
   @(posedge fifo_clk); fill_start<=1; fill_start_bank<=0; @(posedge fifo_clk); fill_start<=0;
   wd_v<=4'hf; repeat(80) @(posedge fifo_clk); wd_v<=0; repeat(5) @(posedge fifo_clk);
   copy_on<=1; copy_bank<=0; chk=1;
   repeat(6000) @(posedge hbm_clk);
   $display("BENCH_RESULT mutant=%0d cycles=%0d valid_beats=%0d errs=%0d", MUTANT, cyc, nvalid, errs);
   $finish;
 end
endmodule
