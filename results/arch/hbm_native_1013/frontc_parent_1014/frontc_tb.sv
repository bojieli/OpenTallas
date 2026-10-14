`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0; integer cyc, j, checked=0, mismatches=0, xbeats=0, requests=0, responses=0, posted_desc=0, posted_ops=0, desc_credit=10, op_credit=10; reg mut_clk=0; reg [31:0] rnd=32'h31415926;
reg[41:0] pending[0:1023]; integer due[0:1023]; integer wp=0,rp=0;
function automatic [31:0] next_rand(input [31:0] a); reg[31:0] b; begin b=a^(a<<13); b=b^(b>>17); next_rand=b^(b<<5);end endfunction
wire [817:0] g_rout_l1,d_rout_l1; reg [817:0] prev_rout_l1=0; integer activity_rout_l1=0;
wire [817:0] g_rout_r1,d_rout_r1; reg [817:0] prev_rout_r1=0; integer activity_rout_r1=0;
wire [817:0] g_rout_l2,d_rout_l2; reg [817:0] prev_rout_l2=0; integer activity_rout_l2=0;
wire [817:0] g_rout_r2,d_rout_r2; reg [817:0] prev_rout_r2=0; integer activity_rout_r2=0;
wire [2068:0] g_bout_l1,d_bout_l1; reg [2068:0] prev_bout_l1=0; integer activity_bout_l1=0;
wire [2068:0] g_bout_r1,d_bout_r1; reg [2068:0] prev_bout_r1=0; integer activity_bout_r1=0;
reg fs_v=0;
reg [46:0] fs_d=0;
wire g_fs_ret,d_fs_ret; reg prev_fs_ret=0; integer activity_fs_ret=0;
reg [2068:0] fx_b=0;
reg fr_rl=0;
wire [817:0] g_fo_row0,d_fo_row0; reg [817:0] prev_fo_row0=0; integer activity_fo_row0=0;
wire [2:0] g_fo_pbz,d_fo_pbz; reg [2:0] prev_fo_pbz=0; integer activity_fo_pbz=0;
reg fd_v=0;
reg [55:0] fd_d=0;
wire g_fd_ret,d_fd_ret; reg prev_fd_ret=0; integer activity_fd_ret=0;
wire g_fq_v,d_fq_v; reg prev_fq_v=0; integer activity_fq_v=0;
wire [41:0] g_fq_d,d_fq_d; reg [41:0] prev_fq_d=0; integer activity_fq_d=0;
reg fq_ret=0;
reg fp_v=0;
reg [1097:0] fp_d=0;
reg fsv=0;
wire [817:0] g_fo_row3,d_fo_row3; reg [817:0] prev_fo_row3=0; integer activity_fo_row3=0;
ot_hbm_accel_smh_front_c u_gold(.clk(clk),.rst_n(rst_n),.rout_l1(g_rout_l1),.rout_r1(g_rout_r1),.rout_l2(g_rout_l2),.rout_r2(g_rout_r2),.bout_l1(g_bout_l1),.bout_r1(g_bout_r1),.fs_v(fs_v),.fs_d(fs_d),.fs_ret(g_fs_ret),.fx_b(fx_b),.fr_rl(fr_rl),.fo_row0(g_fo_row0),.fo_pbz(g_fo_pbz),.fd_v(fd_v),.fd_d(fd_d),.fd_ret(g_fd_ret),.fq_v(g_fq_v),.fq_d(g_fq_d),.fq_ret(fq_ret),.fp_v(fp_v),.fp_d(fp_d),.fsv(fsv),.fo_row3(g_fo_row3));
ot_smh_frontc_native_parent u_dut(.raw_u_bc(clk),.rst_u_bc(rst_n),.raw_u_is(clk),.rst_u_is(rst_n),.raw_u_xl(mut_clk?1'b0:clk),.rst_u_xl(rst_n),.raw_u_tw(clk),.rst_u_tw(rst_n),.raw_u_te(clk),.rst_u_te(rst_n),.raw_u_rw(clk),.rst_u_rw(rst_n),.raw_u_re(clk),.rst_u_re(rst_n),.raw_u_bw(clk),.rst_u_bw(rst_n),.raw_u_be(clk),.rst_u_be(rst_n),.rout_l1(d_rout_l1),.rout_r1(d_rout_r1),.rout_l2(d_rout_l2),.rout_r2(d_rout_r2),.bout_l1(d_bout_l1),.bout_r1(d_bout_r1),.fs_v(fs_v),.fs_d(fs_d),.fs_ret(d_fs_ret),.fx_b(fx_b),.fr_rl(fr_rl),.fo_row0(d_fo_row0),.fo_pbz(d_fo_pbz),.fd_v(fd_v),.fd_d(fd_d),.fd_ret(d_fd_ret),.fq_v(d_fq_v),.fq_d(d_fq_d),.fq_ret(fq_ret),.fp_v(fp_v),.fp_d(fp_d),.fsv(fsv),.fo_row3(d_fo_row3));
initial begin mut_clk=$test$plusargs("MUTCLK"); for(cyc=0;cyc<8192;cyc=cyc+1) begin
clk=0; rst_n=!(cyc<16 || (cyc>=4096 && cyc<4112));
fd_v=0; fs_v=0; fp_v=0; fq_ret=0; fr_rl=g_fo_pbz[1]; fsv=0;
if(!rst_n) begin desc_credit=10;op_credit=10;wp=0;rp=0; end else begin
desc_credit=desc_credit+g_fd_ret;op_credit=op_credit+g_fs_ret;
if(cyc%256==32 && desc_credit>0) begin fd_v=1; fd_d={32'(posted_desc*16),24'd16}; desc_credit=desc_credit-1; posted_desc=posted_desc+1;end
if(cyc%256==36 && op_credit>0) begin fs_v=1;fs_d={13'd8,16'd2,8'd1,1'b0,2'd0,7'd3};op_credit=op_credit-1;posted_ops=posted_ops+1;end
if(g_fq_v) begin if(wp-rp>=1000)$fatal(1,"request queue overflow"); pending[wp%1024]=g_fq_d;due[wp%1024]=cyc+7+(wp%5);wp=wp+1;fq_ret=1;requests=requests+1;end
if(rp<wp && due[rp%1024]<=cyc) begin fp_v=1;for(j=0;j<34;j=j+1)begin rnd=next_rand(rnd);fp_d[j*32+:32]=rnd;end fp_d[1097:1088]=pending[rp%1024][41:32];rp=rp+1;responses=responses+1;end
end
for(j=0;j<64;j=j+1)begin rnd=next_rand(rnd);fx_b[j*32+:32]=rnd;end
fx_b[2067:2048]=20'(cyc);fx_b[2068]=rst_n&&(cyc%7<4);if(fx_b[2068])xbeats=xbeats+1;
#0.4166665;clk=1;#0.200;
if(cyc>32) begin checked=checked+1;
if(g_rout_l1 !== d_rout_l1) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=rout_l1",cyc);end
if(g_rout_l1 !== prev_rout_l1)activity_rout_l1=activity_rout_l1+1;prev_rout_l1=g_rout_l1;
if(g_rout_r1 !== d_rout_r1) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=rout_r1",cyc);end
if(g_rout_r1 !== prev_rout_r1)activity_rout_r1=activity_rout_r1+1;prev_rout_r1=g_rout_r1;
if(g_rout_l2 !== d_rout_l2) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=rout_l2",cyc);end
if(g_rout_l2 !== prev_rout_l2)activity_rout_l2=activity_rout_l2+1;prev_rout_l2=g_rout_l2;
if(g_rout_r2 !== d_rout_r2) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=rout_r2",cyc);end
if(g_rout_r2 !== prev_rout_r2)activity_rout_r2=activity_rout_r2+1;prev_rout_r2=g_rout_r2;
if(g_bout_l1 !== d_bout_l1) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=bout_l1",cyc);end
if(g_bout_l1 !== prev_bout_l1)activity_bout_l1=activity_bout_l1+1;prev_bout_l1=g_bout_l1;
if(g_bout_r1 !== d_bout_r1) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=bout_r1",cyc);end
if(g_bout_r1 !== prev_bout_r1)activity_bout_r1=activity_bout_r1+1;prev_bout_r1=g_bout_r1;
if(g_fs_ret !== d_fs_ret) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=fs_ret",cyc);end
if(g_fs_ret !== prev_fs_ret)activity_fs_ret=activity_fs_ret+1;prev_fs_ret=g_fs_ret;
if(g_fo_row0 !== d_fo_row0) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=fo_row0",cyc);end
if(g_fo_row0 !== prev_fo_row0)activity_fo_row0=activity_fo_row0+1;prev_fo_row0=g_fo_row0;
if(g_fo_pbz !== d_fo_pbz) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=fo_pbz",cyc);end
if(g_fo_pbz !== prev_fo_pbz)activity_fo_pbz=activity_fo_pbz+1;prev_fo_pbz=g_fo_pbz;
if(g_fd_ret !== d_fd_ret) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=fd_ret",cyc);end
if(g_fd_ret !== prev_fd_ret)activity_fd_ret=activity_fd_ret+1;prev_fd_ret=g_fd_ret;
if(g_fq_v !== d_fq_v) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=fq_v",cyc);end
if(g_fq_v !== prev_fq_v)activity_fq_v=activity_fq_v+1;prev_fq_v=g_fq_v;
if(g_fq_d !== d_fq_d) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=fq_d",cyc);end
if(g_fq_d !== prev_fq_d)activity_fq_d=activity_fq_d+1;prev_fq_d=g_fq_d;
if(g_fo_row3 !== d_fo_row3) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port=fo_row3",cyc);end
if(g_fo_row3 !== prev_fo_row3)activity_fo_row3=activity_fo_row3+1;prev_fo_row3=g_fo_row3;
end #0.2166665; end
$display("FRONTC_EXACT checked=%0d mismatches=%0d xbeats=%0d descriptors=%0d ops=%0d requests=%0d responses=%0d",checked,mismatches,xbeats,posted_desc,posted_ops,requests,responses);
$display("FRONTC_ACTIVITY rout_l1 %0d",activity_rout_l1);
$display("FRONTC_ACTIVITY rout_r1 %0d",activity_rout_r1);
$display("FRONTC_ACTIVITY rout_l2 %0d",activity_rout_l2);
$display("FRONTC_ACTIVITY rout_r2 %0d",activity_rout_r2);
$display("FRONTC_ACTIVITY bout_l1 %0d",activity_bout_l1);
$display("FRONTC_ACTIVITY bout_r1 %0d",activity_bout_r1);
$display("FRONTC_ACTIVITY fs_ret %0d",activity_fs_ret);
$display("FRONTC_ACTIVITY fo_row0 %0d",activity_fo_row0);
$display("FRONTC_ACTIVITY fo_pbz %0d",activity_fo_pbz);
$display("FRONTC_ACTIVITY fd_ret %0d",activity_fd_ret);
$display("FRONTC_ACTIVITY fq_v %0d",activity_fq_v);
$display("FRONTC_ACTIVITY fq_d %0d",activity_fq_d);
$display("FRONTC_ACTIVITY fo_row3 %0d",activity_fo_row3);
if(requests<8 || responses<8 || xbeats<100)$fatal(1,"frontC activity insufficient");
if(mismatches!=0)$fatal(1,"frontC literal comparison mismatch");$finish;end endmodule
