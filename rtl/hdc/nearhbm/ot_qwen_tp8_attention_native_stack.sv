`timescale 1ns/1ps
// Wires-only join of the selected actual ECTL, 86-root native heads, and mapped
// EP/EX/Z stack. Source-profile ages and native clock insertion are separate
// compiler/physical inputs; zero ASTK ages intentionally remain unsealed.
module ot_qwen_tp8_attention_native_stack #(
 parameter integer STACK=0,RL=1,QK_ISSUE_AGE=34,ROW_RETURN_LAT=9,
 parameter integer EXP_START_AGE=0,LMAX_START_AGE=0,Z_START_AGE=0,Z_STRIDE=4
)(
 input wire rst_n,
 input wire ck_astk_c,ck_astk_r,input wire[3:0] ck_astk_z,
 input wire[31:0] ck_astk_x,input wire[7:0] ck_astk_e,
 input wire[23:0] ck_ectl,input wire[2751:0] ck_head,
 input wire[539:0] aq,input wire[35:0] am,output wire[562:0] ap,
 input wire active_layer_parity,
 output wire[135:0] k_request,input wire[8199:0] k_response,
 input wire er_v,input wire[10:0] er_addr,
 output wire er_rsp_v,output wire[10:0] er_rsp_addr,output wire[63:0] er_data,
 output wire[15:0] exp_committed,output wire score_committed,output wire fault
);
 wire[3399:0] so;wire[5071:0] si;wire astk_fault;
 wire[20:0] lt;
 qkd_astk_native_stack_s #(.RL(RL),.STATIC_SCHEDULE(1),
  .EXP_START_AGE(EXP_START_AGE),.LMAX_START_AGE(LMAX_START_AGE),
  .Z_START_AGE(Z_START_AGE),.Z_STRIDE(Z_STRIDE)) u_astk(
  .ck_c(ck_astk_c),.ck_z(ck_astk_z),.ck_x(ck_astk_x),.ck_e(ck_astk_e),.ck_r(ck_astk_r),
  .rst_n(rst_n),.st(2'(STACK)),.aq(aq),.am(am),.ap(ap),.af(astk_fault),.lt(lt),
  .er_v(er_v),.er_addr(er_addr),.er_rsp_v(er_rsp_v),.er_rsp_addr(er_rsp_addr),.er_data(er_data),
  .exp_committed(exp_committed),.score_committed(score_committed),
  .so0(so[0+:425]),.so1(so[425+:425]),.so2(so[850+:425]),.so3(so[1275+:425]),
  .so4(so[1700+:425]),.so5(so[2125+:425]),.so6(so[2550+:425]),.so7(so[2975+:425]),
  .si0(si[0+:634]),.si1(si[634+:634]),.si2(si[1268+:634]),.si3(si[1902+:634]),
  .si4(si[2536+:634]),.si5(si[3170+:634]),.si6(si[3804+:634]),.si7(si[4438+:634]));
 assign fault=astk_fault;
 genvar engine,head;
 generate for(engine=0;engine<8;engine=engine+1)begin:g_engine
  wire[63:0] e;wire[135:0] scores;wire[1558:0] t0,t1;wire[16:0] rq;
  qkd_ectl3_epoch_direct_s #(.STATIC_QK(1),.QK_ISSUE_AGE(QK_ISSUE_AGE),
   .ROW_RETURN_LAT(ROW_RETURN_LAT)) u_ectl(
   .ck(ck_ectl[3*engine+:3]),.rst_n(rst_n),.cfg({3'(engine),2'(STACK)}),
   .e0(e[0+:16]),.e1(e[16+:16]),.e2(e[32+:16]),.e3(e[48+:16]),
   .s0(scores[0+:34]),.s1(scores[34+:34]),.s2(scores[68+:34]),.s3(scores[102+:34]),
   .t0(t0),.t1(t1),.rq(rq),.rs(k_response[1025*engine+:1025]),
   .si(si[634*engine+:634]),.so(so[425*engine+:425]));
  // The actual command's layer parity owns the physical DRAM bank identity.
  // The historical EPOCH1 start-toggle is not a producer of this metadata.
  assign k_request[17*engine+:17]={active_layer_parity,rq[15:0]};
  for(head=0;head<4;head=head+1)begin:g_head
   localparam integer HC=(4*engine+head)*86;
   wire[1558:0] t=(head<2)?t0:t1;
   ot_qkh_head_native_r4 #(.Q_FP32(1)) u_head(
    .ck_front(ck_head[HC+:4]),.ck_score(ck_head[HC+4]),.ck_kt(ck_head[HC+5]),
    .ck_stin(ck_head[HC+6+:16]),.ck_stk(ck_head[HC+22+:16]),
    .ck_nb1(ck_head[HC+38+:16]),.ck_nb2(ck_head[HC+54+:16]),.ck_lane(ck_head[HC+70+:16]),
    .rst_n(rst_n),.c_in(t[3:0]),.row_in(t[1027:4]),.e_in(e[16*head+:16]),
    .lt_in(t[1039:1028]),.hid(2'(head)),.q_valid_in(t[1040]),.q_beat_in(t[1046:1041]),.q_data_in(t[1558:1047]),
    .sc_d(scores[34*head+:32]),.sc_f(scores[34*head+32]),.g_f(scores[34*head+33]),.nb_d());
  end
 end endgenerate
endmodule
