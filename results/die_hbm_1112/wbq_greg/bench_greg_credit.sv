`timescale 1ns/1ps
// credit-window bench: sink returns one credit D hbm cycles after it SEES a valid beat; counts cycles where a lane has data
// but the root is blocked only by credit (credit==0), for GREG=0 and GREG=1 and CRED, sink delay D.
module bench_credit;
 parameter integer D=2; parameter integer CRED=4;
 reg hbm_clk=0,fifo_clk=0; always #1.5 hbm_clk=~hbm_clk; always #2.5 fifo_clk=~fifo_clk;
 reg stream_rst_n=0,hbm_rst_n=0; reg [1:0] root_id=0; reg reserve_v=0,reserve_bank=0; reg [11:0] reserve_total=0; reg [29:0] reserve_base=0;
 reg fill_start=0,fill_start_bank=0; reg [255:0] wd0,wd1,wd2,wd3; reg [3:0] wd_v=0; reg copy_on=0,copy_bank=0,s_stop=0,h_stop=0;
 wire rr0,rr1,v0,v1; wire [285:0] d0,d1;
 reg [15:0] pipe0=0,pipe1=0; reg gc0=0,gc1=0; integer i;
 // sink: credit pulse D cycles after the valid beat is seen (D>=1)
 always @(posedge hbm_clk) begin
   pipe0 <= {pipe0[14:0], v0}; pipe1 <= {pipe1[14:0], v1};
   gc0 <= pipe0[D-1]; gc1 <= pipe1[D-1];
 end
 ot_wbq_root_s7_grp #(.G(0),.CRED(CRED),.GREG(0)) r0(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd0),.wd1(wd1),.wd2(wd2),.wd3(wd3),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(gc0),.root_ready(rr0),.g_v(v0),.g_d(d0));
 ot_wbq_root_s7_grp #(.G(0),.CRED(CRED),.GREG(1)) r1(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),.fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd0),.wd1(wd1),.wd2(wd2),.wd3(wd3),.wd_v(wd_v),.copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(gc1),.root_ready(rr1),.g_v(v1),.g_d(d1));
 integer blk0=0,blk1=0,snd0=0,snd1=0,last0=0,last1=0,cyc=0; reg chk=0;
 always @(negedge hbm_clk) if(chk) begin
   cyc=cyc+1;
   if(r0.send) begin snd0=snd0+1; last0=cyc; end else if(|r0.ne && r0.credit==0 && !h_stop) blk0=blk0+1;
   if(r1.send) begin snd1=snd1+1; last1=cyc; end else if(|r1.ne && r1.credit==0 && !h_stop) blk1=blk1+1;
 end
 always @(posedge fifo_clk) begin wd0<={8{$urandom}};wd1<={8{$urandom}};wd2<={8{$urandom}};wd3<={8{$urandom}}; end
 initial begin
   repeat(10) @(posedge fifo_clk); stream_rst_n=1; hbm_rst_n=1; repeat(8) @(posedge fifo_clk);
   @(posedge fifo_clk); reserve_v<=1; reserve_bank<=0; reserve_total<=12'd256; reserve_base<=30'd1000; @(posedge fifo_clk); reserve_v<=0;
   @(posedge fifo_clk); fill_start<=1; fill_start_bank<=0; @(posedge fifo_clk); fill_start<=0;
   wd_v<=4'hf; repeat(80) @(posedge fifo_clk); wd_v<=0; repeat(5) @(posedge fifo_clk);
   copy_on<=1; copy_bank<=0; chk=1; repeat(3000) @(posedge hbm_clk);
   $display("CREDIT_BENCH D=%0d CRED=%0d  GREG0: sends=%0d credit_blocked=%0d last_send_cycle=%0d | GREG1: sends=%0d credit_blocked=%0d last_send_cycle=%0d", D, CRED, snd0,blk0,last0,snd1,blk1,last1);
   $finish;
 end
endmodule
