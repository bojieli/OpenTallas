`timescale 1ns/1ps
// =====================================================================================================================
// qfd_tt_ctlm_dv_wtn -- QW-F16PROG4 10-19: the CTLM-core F16 typed witness face (hard child of qfd_tt_ctlm_dv_gi when
// F16WTN = 1).  Wires + one AND only: every input is pin-registered and every output registered INSIDE the SAFE_PHYS
// controller (qfd_dv_typed_witness_control ENABLE 1 / SAFE_COMPARE 1 / SAFE_SELECT 1 / SAFE_PHYS 1), so the face adds
// 0 edges and the controller's +2 edges (pin + output register) are the whole F16 offset; f16_calr_edges.py hands it
// to the schedule (status visible WTN_OUT_EDGES = 2 edges after the legacy decision edge; no SU / token cycle).
//   pw   [74:0]  {v, addr 10, data 64}: the CTLM TT PW port (PW0 restarts loading; PW400..438 = the 39-word WTN1
//                template, tools/qwen_layerbench/ctlm_image.py --wtn1).
//   auth [82:0]  {begin, all_copies_auth, fusedcap, digest 64, epoch 16} from SYSFACE u_join (qkd_program_commit_join).
//                BEGIN withdraws authentication on the same edge as the join's own ready drop (auth & !begin), so a
//                fresh image can never inherit the old seal; the controller re-seals only after the full template.
//   start [24:0] {v, user 2, stage 6, epoch 16}: the calendar's accepted start; epoch = the context's token identity
//                (token[15:0] of that user at its start); every typed execution event of the context carries it.
//   retire [3:0] {v, user 2, me_xpf_retired}.
//   obs  [37:0]  {observation 16, event stage 6, event epoch 16}.
//   st  [16:0]   {fault, complete_group 4, complete_user 2, group_complete, all_witnesses_complete 4,
//                 context_active 4, template_ready}.
// MUT (bench only): 1 BEGIN does not withdraw auth, 2 start epoch = installed programme epoch (no per-context identity),
//   3 retire user bits swapped.
// =====================================================================================================================
module qfd_tt_ctlm_dv_wtn #(
    parameter integer MUT = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [74:0]  pw,
    input  wire [82:0]  auth,
    input  wire [24:0]  start,
    input  wire [3:0]   retire,
    input  wire [37:0]  obs,
    output wire [16:0]  st
);
    wire        a_begin = auth[82];
    wire        a_all = auth[81] && (a_begin == 1'b0 || MUT == 1);
    wire [15:0] a_epoch = auth[15:0];
    wire [1:0]  r_user = (MUT == 3) ? {retire[1], retire[2]} : retire[2:1];
    wire        tr, gc, fl;
    wire [3:0]  ca, awc, cg;
    wire [1:0]  cu;
    qfd_dv_typed_witness_control #(.ENABLE(1), .SAFE_COMPARE(1), .SAFE_SELECT(1), .SAFE_PHYS(1)) u_ctl (
        .ck(ck), .rst_n(rst_n), .pw_v(pw[74]), .pw_addr(pw[73:64]), .pw_data(pw[63:0]),
        .all_copies_authenticated(a_all), .fusedcap(auth[80]), .installed_digest(auth[79:16]), .installed_epoch(a_epoch),
        .start_v(start[24]), .start_user(start[23:22]), .start_stage(start[21:16]),
        .start_epoch((MUT == 2) ? a_epoch : start[15:0]),
        .retire_v(retire[3]), .retire_user(r_user), .ME_XPF_retired(retire[0]),
        .observation(obs[37:22]), .event_stage(obs[21:16]), .event_epoch(obs[15:0]),
        .template_ready(tr), .context_active(ca), .all_witnesses_complete(awc),
        .group_complete(gc), .complete_user(cu), .complete_group(cg), .fault(fl));
    assign st = {fl, cg, cu, gc, awc, ca, tr};
endmodule
