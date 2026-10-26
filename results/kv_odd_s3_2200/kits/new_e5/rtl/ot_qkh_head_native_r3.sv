`timescale 1ns/1ps
// Native head r3: 83 independent entries = front/ktree/score + 16*(stin/stk/nb1/nb2/lane).
// The former stout's KP path remains D2; its NB D2 becomes two independently placed D1 leaves.
// No data stage or FP32 operation is added, removed, or reordered.
module ot_qkh_head_stk_native #(parameter integer MUT=0) (
  input wire clk,rst_n,
  input wire [31:0] kp_i,input wire kpv_i,gf_i,
  output wire [31:0] kp_o,output wire kpv_o,gf_o);
  wire [0:0] rr;
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst
    (.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  ot_qkh_relay #(.W(32),.D(2)) u_rkd (.clk(clk),.rst_n(rr[0]),
    .d(MUT==5 ? {kp_i[15:0],kp_i[31:16]} : kp_i),.q(kp_o));
  ot_qkh_relay #(.W(2),.D(2),.RST(1)) u_rkv (.clk(clk),.rst_n(rr[0]),.d({kpv_i,gf_i}),.q({kpv_o,gf_o}));
endmodule

// The original NB pipeline has no reset. Keep that behavior; its validity lives in the data protocol.
module ot_qkh_head_nb_native #(parameter integer MUT=0) (
  input wire clk,input wire [63:0] nb_i,output reg [63:0] nb_o);
  always @(posedge clk) nb_o <= MUT==2 ? {nb_i[31:0],nb_i[63:32]} : nb_i;
endmodule

module ot_qkh_head_native_r3 #(
  parameter integer Q_FP32=1,parameter integer MUT=0
)(input wire ck_front,ck_score,ck_kt,
  input wire [15:0] ck_stin,ck_stk,ck_nb1,ck_nb2,ck_lane,
  input wire rst_n,input wire [3:0] c_in,input wire [1023:0] row_in,
  input wire [15:0] e_in,input wire [11:0] lt_in,input wire [1:0] hid,
  input wire q_valid_in,input wire [5:0] q_beat_in,input wire [511:0] q_data_in,
  output wire [31:0] sc_d,output wire sc_f,g_f,output wire [1023:0] nb_d);
  wire [232:0] f_t [0:15];wire pack_fault;
  ot_qkh_head_front_native #(.Q_FP32(Q_FP32),.MUT(MUT)) u_front
    (.clk(ck_front),.rst_n(rst_n),.c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),.hid(hid),
     .q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),
.f_t0(f_t[0]),.f_t1(f_t[1]),.f_t2(f_t[2]),.f_t3(f_t[3])
    ,.f_t4(f_t[4]),.f_t5(f_t[5]),.f_t6(f_t[6]),.f_t7(f_t[7])
    ,.f_t8(f_t[8]),.f_t9(f_t[9]),.f_t10(f_t[10]),.f_t11(f_t[11])
    ,.f_t12(f_t[12]),.f_t13(f_t[13]),.f_t14(f_t[14]),.f_t15(f_t[15])
    ,.pack_fault(pack_fault));
  wire [511:0] kp_t,kp_k;wire [15:0] kpv_t,kpv_k,gf_t,gf_k;
  wire [1023:0] nb_t;wire [15:0] lane_rst_n;
  genvar t;
  generate for(t=0;t<16;t=t+1) begin:g_t
    wire [15:0] cr_o;wire [216:0] dr_o;
    ot_qkh_head_stin_native #(.MUT(MUT)) u_stin
      (.clk(ck_stin[t]),.rst_n(rst_n),.cr_i(f_t[t][232:217]),.dr_i(f_t[t][216:0]),.cr_o(cr_o),.dr_o(dr_o),
       .lane_rst_n(lane_rst_n[t]));
    ot_qkh_head_stk_native #(.MUT(MUT)) u_stk
      (.clk(ck_stk[t]),.rst_n(rst_n),.kp_i(kp_t[32*t +:32]),.kpv_i(kpv_t[t]),.gf_i(gf_t[t]),
       .kp_o(kp_k[32*t +:32]),.kpv_o(kpv_k[t]),.gf_o(gf_k[t]));
    wire [63:0] nb_mid;
    ot_qkh_head_nb_native #(.MUT(MUT)) u_nb1
      (.clk(ck_nb1[t]),.nb_i(nb_t[64*t +:64]),.nb_o(nb_mid));
    ot_qkh_head_nb_native u_nb2
      (.clk(ck_nb2[t]),.nb_i(nb_mid),.nb_o(nb_d[64*t +:64]));
    ot_qkh_lane8 u_l8 (.clk(ck_lane[t]),.rst_n(lane_rst_n[t]),
      .c_in({cr_o[15:13],dr_o[216]}),.row_in(dr_o[215:152]),.e_in(dr_o[151:136]),.lt_in(cr_o[12:1]),
      .hid(dr_o[1:0]),.bsel(2'(t/4)),.q_valid_in(cr_o[0]),.q_beat_in(dr_o[135:130]),.q_data_in(dr_o[129:2]),
      .kp(kp_t[32*t +:32]),.kpv(kpv_t[t]),.nb(nb_t[64*t +:64]),.gf(gf_t[t]));
  end endgenerate
  wire [31:0] sc_k;wire sf_k,gf_kt,kt_rst_n;
  ot_qkh_ktree u_kt (.clk(ck_kt),.rst_n(kt_rst_n),.kp_in(kp_k),.kpv_in(kpv_k[0]),.gf_in(gf_k),
    .sc_d(sc_k),.sc_f(sf_k),.g_f(gf_kt));
  ot_qkh_head_score_native #(.MUT(MUT)) u_score
    (.clk(ck_score),.rst_n(rst_n),.sc_i(sc_k),.sf_i(sf_k),.gf_i(gf_kt),.pack_fault(pack_fault),
     .sc_o(sc_d),.sf_o(sc_f),.gf_o(g_f),.kt_rst_n(kt_rst_n));
endmodule
