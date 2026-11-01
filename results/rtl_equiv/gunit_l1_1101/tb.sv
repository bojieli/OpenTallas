`timescale 1ns/1ps
module tb;
reg  clk=0;
reg  rst_n=0;
reg [275:0] rn_i=0;
wire [275:0] a_rn_o,b_rn_o;
reg  dl_av=0;
reg [236:0] dl_a=0;
reg  dl_bv=0;
reg [236:0] dl_b=0;
reg  cw_v=0;
reg [7:0] cw_a=0;
reg [255:0] cw_d=0;
reg [3:0] sid_i=0;
wire  a_ct_v,b_ct_v;
wire [169:0] a_ct_b,b_ct_b;
wire  a_fault,b_fault;
wire [275:0] a_rs_o,b_rs_o;
reg [275:0] rs_i=0;
wire  a_rw_st,b_rw_st;
wire  a_rw_v,b_rw_v;
wire  a_rw_l,b_rw_l;
wire [191:0] a_rw_x,b_rw_x;
wire [31:0] a_rw_scale,b_rw_scale;
wire [9:0] a_rw_row,b_rw_row;
wire [4:0] a_rw_lm,b_rw_lm;
wire [15:0] a_rw_sm,b_rw_sm;
wire [3:0] a_sid_o,b_sid_o;
reg  w_v=0;
reg [169:0] w_b=0;
reg  f3=0;
wire [5:0] a_sa_r,b_sa_r;
wire [223:0] a_sa_d,b_sa_d;
wire [5:0] a_sb_r,b_sb_r;
wire [223:0] a_sb_d,b_sb_d;
wire [55:0] a_we,b_we;
wire  a_c_go,b_c_go;
wire  a_c_fw,b_c_fw;
wire  a_c_l,b_c_l;
wire [2:0] a_c_bn,b_c_bn;
wire [19:0] a_c_lvn,b_c_lvn;
wire  a_re,b_re;
wire [3:0] a_ra,b_ra;
wire [7:0] a_bw_e,b_bw_e;
wire [3:0] a_bw_a,b_bw_a;
wire [255:0] a_bw_d,b_bw_d;
reg  i_v=0;
reg [53:0] i_ids=0;
reg  gs_v=0;
reg [191:0] gs_d=0;
reg  fc=0;
always #1 clk=~clk;
dsdv_gunit_l1_ref ref0 (.clk(clk),.rst_n(rst_n),.rn_i(rn_i),.rn_o(a_rn_o),.dl_av(dl_av),.dl_a(dl_a),.dl_bv(dl_bv),.dl_b(dl_b),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.sid_i(sid_i),.ct_v(a_ct_v),.ct_b(a_ct_b),.fault(a_fault),.rs_o(a_rs_o),.rs_i(rs_i),.rw_st(a_rw_st),.rw_v(a_rw_v),.rw_l(a_rw_l),.rw_x(a_rw_x),.rw_scale(a_rw_scale),.rw_row(a_rw_row),.rw_lm(a_rw_lm),.rw_sm(a_rw_sm),.sid_o(a_sid_o),.w_v(w_v),.w_b(w_b),.f3(f3),.sa_r(a_sa_r),.sa_d(a_sa_d),.sb_r(a_sb_r),.sb_d(a_sb_d),.we(a_we),.c_go(a_c_go),.c_fw(a_c_fw),.c_l(a_c_l),.c_bn(a_c_bn),.c_lvn(a_c_lvn),.re(a_re),.ra(a_ra),.bw_e(a_bw_e),.bw_a(a_bw_a),.bw_d(a_bw_d),.i_v(i_v),.i_ids(i_ids),.gs_v(gs_v),.gs_d(gs_d),.fc(fc));
dsdv_gunit_l1 dut (.clk(clk),.rst_n(rst_n),.rn_i(rn_i),.rn_o(b_rn_o),.dl_av(dl_av),.dl_a(dl_a),.dl_bv(dl_bv),.dl_b(dl_b),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.sid_i(sid_i),.ct_v(b_ct_v),.ct_b(b_ct_b),.fault(b_fault),.rs_o(b_rs_o),.rs_i(rs_i),.rw_st(b_rw_st),.rw_v(b_rw_v),.rw_l(b_rw_l),.rw_x(b_rw_x),.rw_scale(b_rw_scale),.rw_row(b_rw_row),.rw_lm(b_rw_lm),.rw_sm(b_rw_sm),.sid_o(b_sid_o),.w_v(w_v),.w_b(w_b),.f3(f3),.sa_r(b_sa_r),.sa_d(b_sa_d),.sb_r(b_sb_r),.sb_d(b_sb_d),.we(b_we),.c_go(b_c_go),.c_fw(b_c_fw),.c_l(b_c_l),.c_bn(b_c_bn),.c_lvn(b_c_lvn),.re(b_re),.ra(b_ra),.bw_e(b_bw_e),.bw_a(b_bw_a),.bw_d(b_bw_d),.i_v(i_v),.i_ids(i_ids),.gs_v(gs_v),.gs_d(gs_d),.fc(fc));
integer cyc;
initial begin
repeat(8) @(negedge clk);rst_n=1;
for(cyc=0;cyc<100000;cyc=cyc+1)begin
@(negedge clk);
rn_i = (276'($urandom) << 0) | (276'($urandom) << 32) | (276'($urandom) << 64) | (276'($urandom) << 96) | (276'($urandom) << 128) | (276'($urandom) << 160) | (276'($urandom) << 192) | (276'($urandom) << 224) | (276'($urandom) << 256);
dl_av = $urandom;
dl_a = (237'($urandom) << 0) | (237'($urandom) << 32) | (237'($urandom) << 64) | (237'($urandom) << 96) | (237'($urandom) << 128) | (237'($urandom) << 160) | (237'($urandom) << 192) | (237'($urandom) << 224);
dl_bv = $urandom;
dl_b = (237'($urandom) << 0) | (237'($urandom) << 32) | (237'($urandom) << 64) | (237'($urandom) << 96) | (237'($urandom) << 128) | (237'($urandom) << 160) | (237'($urandom) << 192) | (237'($urandom) << 224);
cw_v = $urandom;
cw_a = $urandom;
cw_d = (256'($urandom) << 0) | (256'($urandom) << 32) | (256'($urandom) << 64) | (256'($urandom) << 96) | (256'($urandom) << 128) | (256'($urandom) << 160) | (256'($urandom) << 192) | (256'($urandom) << 224);
sid_i = $urandom;
rs_i = (276'($urandom) << 0) | (276'($urandom) << 32) | (276'($urandom) << 64) | (276'($urandom) << 96) | (276'($urandom) << 128) | (276'($urandom) << 160) | (276'($urandom) << 192) | (276'($urandom) << 224) | (276'($urandom) << 256);
w_v = $urandom;
w_b = (170'($urandom) << 0) | (170'($urandom) << 32) | (170'($urandom) << 64) | (170'($urandom) << 96) | (170'($urandom) << 128) | (170'($urandom) << 160);
f3 = $urandom;
i_v = $urandom;
i_ids = (54'($urandom) << 0) | (54'($urandom) << 32);
gs_v = $urandom;
gs_d = (192'($urandom) << 0) | (192'($urandom) << 32) | (192'($urandom) << 64) | (192'($urandom) << 96) | (192'($urandom) << 128) | (192'($urandom) << 160);
fc = $urandom;

 rst_n = (cyc%200>=8);
 cw_v=(cyc%200==12); cw_a=8'h80; cw_d[39:31]=9'(7+((cyc/200)%64)*7);
 dl_av=(cyc%200>=20 && cyc%200<20+(1+(cyc/200)%64));dl_bv=0;
 dl_a[2:0]=3'd5;dl_a[12:3]=10'(cyc%200-20);dl_b[2:0]=3'd5;
 i_v=(cyc%200==110);gs_v=(cyc%200==115);w_v=0;f3=0;fc=0;
 if(cyc>32 && (a_rn_o !== b_rn_o || a_ct_v !== b_ct_v || a_ct_b !== b_ct_b || a_fault !== b_fault || a_rs_o !== b_rs_o || a_rw_st !== b_rw_st || a_rw_v !== b_rw_v || a_rw_l !== b_rw_l || a_rw_x !== b_rw_x || a_rw_scale !== b_rw_scale || a_rw_row !== b_rw_row || a_rw_lm !== b_rw_lm || a_rw_sm !== b_rw_sm || a_sid_o !== b_sid_o || a_sa_r !== b_sa_r || a_sa_d !== b_sa_d || a_sb_r !== b_sb_r || a_sb_d !== b_sb_d || a_we !== b_we || a_c_go !== b_c_go || a_c_fw !== b_c_fw || a_c_l !== b_c_l || a_c_bn !== b_c_bn || a_c_lvn !== b_c_lvn || a_re !== b_re || a_ra !== b_ra || a_bw_e !== b_bw_e || a_bw_a !== b_bw_a || a_bw_d !== b_bw_d)) begin
  $display("LOCKSTEP_FAIL cycle=%0d",cyc);$finish;
 end
 end
 $display("LOCKSTEP_PASS cycles=100000 added_cycles=0");$finish;
end
endmodule
