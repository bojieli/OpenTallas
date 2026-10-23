// Explicit STATUS observer ABI v1; legacy source remains unchanged. Payload is meaningful after its real event.
`timescale 1ns/1ps
// =====================================================================================================================
// qfd_sys_face_mu_dhobs -- the Qwen compute die's dh-start USER observer (MU-DQ-DHUSER 10-19, COORD 0kg item 2: NO constant
// strap on qfd_tt_ctlm_dv.dh_user; the die drives it from the MU observer leaf).  One die-level instance (dv_case.py
// 'mu_dhobs') beside the qfd_tt_ctlm_dv dh pins, on the SAME die bus as tt_ctlm.dh (the face's seq_dh, landed hops), so
// dh_user is valid on the edge tt_ctlm's dh pin register samples the h_start it names (the leaf adds zero edges).
//
// Content: qfd_sys_face_mu_dhuser_obs1 #(OPSEG 0) (the k-th-h_start-of-the-period user list, rtl/qwen_split/mu/) unchanged;
// this level only takes the whole 187-b seq_dh = {dh_prog, dh_run} so the die keeps ONE seq_dh bus (one landed relay
// class, qfd_rlyh0/landh 187) and passes dh_run = seq_dh[43:0] to the leaf.  seq_dh[186:44] (dh_prog) is not read.
// The leaf's OPSEG op-start outputs are constant 0 at OPSEG 0 and are not ports here.
//
// Compiled lists (defaults = tools/qwen_static_schedule/mu_opcal.dhobs_lists(compile_frame(16)), checked by
// tools/qwen_split/die_params.py audit and tools/qwen_split/test_dhobs.py):
//   NS 45 h_starts a token period: stages 1..36 (decode layers L0..L35), 8 x 37 (LM-head chunks c0..c7), 0 (token);
//   USER_SEQ = 0: under OPSEG (the release MU die: qfd_tt_ctlm_dv OPSEG 1) the face's T calendar carries the latency
//   user's stage starts only, so every face dh start IS user 0 -- the driven dh_user equals what tt_ctlm assumes (it
//   ignores dh_user for user selection at OPSEG 1; the fillers' op starts come from its in-cluster leaf);
//   STG_SEQ = the stage of every entry: a face h_start whose stage differs raises the sticky mu_fault (the face's T image
//   and the compiled calendar cannot drift apart unnoticed); RES_SEQ = the token block (entry 44).
// =====================================================================================================================
module qfd_sys_face_mu_dhobs_obs1 #(
    parameter integer NU = 4,
    parameter integer NS = 45,
    parameter [64*2-1:0] USER_SEQ = 128'h0,
    parameter [64*6-1:0] STG_SEQ = 384'h9659659659659238a181f79d71b69961759551349140f38d30b289207185103081,
    parameter [63:0]     RES_SEQ = 64'h0000100000000000,
    parameter integer LAST_STAGE = 37,
    parameter integer MUT = 0,                     // bench only: the leaf's MUT (2 = stage check dropped)
    parameter integer DHREG = 1                    // QW-MU 10-20: dh_user leaves a flop (no in->out path), see below
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [186:0] seq_dh,                    // qfd_sys_face seq_dh (die bus shared with qfd_tt_ctlm_dv.dh)
    output wire [1:0]   dh_user,                   // -> qfd_tt_ctlm_dv.dh_user (DHREG 1: one edge after the h_start)
    output wire [46:0]  obs_res,                  // user of the latest RESULT h_start (held)
    output wire         mu_fault                   // sticky: a face h_start off the compiled stage list
);
    wire [1:0] res_user;
    wire [44:0] res_obs;
    assign obs_res={res_obs[44],res_user,res_obs[43:0]};
    wire        op_v, op_ff;
    wire [1:0]  op_user;
    wire [5:0]  op_stage;
    wire [9:0]  op_first, op_cnt;
    wire [3:0]  op_fcode;
    wire [1:0]  dh_user_c;
    // DHREG 1 (QW-MU 10-20, COORD 16:30 10-19 review of kit d1: SAFE-DESIGN items 1/4): the leaf's dh_user (hs ? u_k : hold)
    // is a combinational seq_dh[42] -> dh_user path; DHREG lands it in a 2-b output flop, +1 edge.  Unpriced and harmless:
    // the release ctlm (qfd_tt_ctlm_dv OPSEG 1) ignores dh_user (s_user = 0 at OPS) and with the compiled lists
    // (USER_SEQ 0) dh_user is 0 on every edge.  DHREG 0 = the previous zero-edge observer.
    reg  [1:0]  dh_user_q;
    always @(posedge ck or negedge rst_n) if (!rst_n) dh_user_q <= 2'd0; else dh_user_q <= dh_user_c;
    assign dh_user = (DHREG != 0) ? dh_user_q : dh_user_c;
    qfd_sys_face_mu_dhuser_obs1 #(.NU(NU), .NS(NS), .USER_SEQ(USER_SEQ), .STG_SEQ(STG_SEQ), .RES_SEQ(RES_SEQ), .OPSEG(0),
                             .LAST_STAGE(LAST_STAGE), .MUT(MUT)) u_obs (
        .ck(ck), .rst_n(rst_n), .dh_run(seq_dh[43:0]), .dh_user(dh_user_c), .res_user(res_user), .res_obs(res_obs), .mu_fault(mu_fault),
        .op_v(op_v), .op_user(op_user), .op_stage(op_stage), .op_first(op_first), .op_cnt(op_cnt), .op_ff(op_ff),
        .op_fcode(op_fcode));
endmodule
