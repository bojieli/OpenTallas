`timescale 1ns/1ps
// =====================================================================================================================
// qfd_tt_ctlm_dv_lpf -- HF-4 (HARD-FIX 0id, 10-18): qfd_tt_ctlm_dv (HARD_HR = 1, MUT = 0) re-cut as a WIRES-ONLY flat
// parent so tools/landed_parent/lp.py can build the landed cluster (landed-regions-standard-1018).  Pure re-partition of
// the same RTL: every register / edge is the one in qfd_tt_ctlm_dv; the lockstep bench tb_qfd_tt_ctlm_dv_lpf proves
// qfd_tt_ctlm_dv == qfd_tt_ctlm_dv_lpf cycle-exactly on every output (mutants FAIL).
// Children (regions in tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf.json):
//   u_gi   core region (W, beside the calendar's 2 x 64x512 SRAMs): pin registers dh / ss5 / ag5 / fab, the static command
//          calendar qfd_dv_cmd_cal, the ME start / token registers, the SU observation, the embedding start.
//   u_hr   hr region (E): the hard TT head leaf ot_qfd_tt_ctlm_static_hr (h16c / h17, ck_head ~355 ps internal insertion).
//   u_go   hr region: XPF loader + static schedule, cp fault, the hr row register, dc / cf / control_stores_ready.
//          (dc needs the head's faults, so it sits with the head: a core-side dc would make a core -> hr -> core loop.)
//   u_thru hr region: wires only.  It makes every core-driven output (cmd, cal_*, emb_*) cross into the hr region like
//          the head's outputs, so the landed parent has ONE output offset (+3 edges on every output, 0 on every input).
// Every input port is landed from the core region (port_regions), so the die presents all inputs on the flat schedule.
// MU-ADOPT-CTLM 10-19: NU (default 4 = the Qwen ROM 4-user calendar) / dh_user as qfd_tt_ctlm_dv (see its NU header);
//   NU = 1 is the single-user cluster.  dh_user lands from the core region like dh (0 edges).
// MU-QW-DIE 10-19: OPSEG / OPSEG_VIAMAP / OPSEG_INST as qfd_tt_ctlm_dv (MU-QW-B1 op-start leaf + coordinator 0ka boot
//   context record in image DW5 / DW6).  OPSEG 1: the leaf qfd_sys_face_mu_dhuser #(OPSEG 1) sits inside u_gi (core
//   region, g_op.u_leaf; ROM ot_rom_4096x72_m8 inside; its own hard tile per MU-LEAF-KIT), observing u_gi's dh pin
//   register and driving u_gi's calendar op start.  OPSEG 0 (default): no leaf, the previous cluster on every edge.
// =====================================================================================================================
module qfd_tt_ctlm_dv_lpf #(
    parameter integer XPF_TRANSPORT_EDGES = -1,
    parameter integer LAST_STAGE = 37,
    parameter integer STAGE_ME = 0,
    parameter integer NU = 4,                    // MU-ADOPT-CTLM 10-19: Qwen ROM 4 users (qfd_tt_ctlm_dv NU; 1 = single user)
    parameter integer UVM_STRIDE = 4096,         // = tools/qwen_static_schedule/mu_calendar.py DV_UVM_STRIDE
    parameter integer PIDX_STRIDE = 128,         // = DV_PIDX_STRIDE
    parameter integer UTAG_LSB = 6,              // = DV_UTAG_LSB
    parameter integer OPSEG = 0,                 // MU-QW-DIE 10-19: 1 = op-start leaf + boot context (Qwen ROM 4 users)
    parameter string  OPSEG_VIAMAP = "",
    parameter string  OPSEG_INST = "qfd_tt_ctlm_opseg"
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [74:0]   pw,
    input  wire [186:0]  dh,
    input  wire [1:0]    dh_user,                // user of the dh stage start (qfd_sys_face seq_dh_user; tie 0 = user 0)
    input  wire          kok,
    input  wire          kwd,
    input  wire          fab,
    output wire [75:0]   program_obs,
    output wire          control_stores_ready,
    output wire          layer_context_v,
    output wire [17:0]   native_tok,
    output wire [17:0]   native_pos,
    output wire [5:0]    command_stage,
    output wire [75:0]   cal_program_obs,
    output wire [68:0]   cal_descriptor_obs,
    output wire          cal_image_ready,
    output wire [55:0]   dc,
    output wire [379:0]  native_cmd,
    input  wire [94:0]   native_ret,
    output wire [452:0]  hr,
    output wire [115:0]  cmd,
    output wire [1087:0] tl,                     // QLB-C4b slice table words (W5 st_wi), via u_thru like cmd
    input  wire [106:0]  ss5,
    input  wire [9:0]    ag5,
    output wire          emb_start,
    output wire [17:0]   emb_token,
    output wire          cf
);
    wire [115:0] g_cmd;
    wire [1087:0] g_tl;
    wire [75:0]  g_cal_program_obs;
    wire [68:0]  g_cal_descriptor_obs;
    wire         g_cal_image_ready, g_emb_start;
    wire [17:0]  g_emb_token;
    wire         s_start;
    wire [5:0]   s_stage;
    wire [48:0]  st;
    wire [15:0]  su_obs, x_oprog, x_orows;
    wire [23:0]  su_acc;
    wire         x_oidle;
    wire [1:0]   rom_ret_v;
    wire [61:0]  dcs;
    wire [55:0]  cp;
    wire         me_image_ready, hr_fault;
    wire [15:0]  me_observe;
    wire [379:0] ib_q;
    wire [72:0]  hr_lo;
    wire [379:0] ib_hr;
    qfd_tt_ctlm_dv_gi #(.LAST_STAGE(LAST_STAGE), .STAGE_ME(STAGE_ME), .NU(NU), .UVM_STRIDE(UVM_STRIDE),
        .PIDX_STRIDE(PIDX_STRIDE), .UTAG_LSB(UTAG_LSB), .OPSEG(OPSEG), .OPSEG_VIAMAP(OPSEG_VIAMAP), .OPSEG_INST(OPSEG_INST))
        u_gi (.ck(ck), .rst_n(rst_n), .dh(dh), .dh_user(dh_user), .ss5(ss5),
        .ag5(ag5), .fab(fab), .cmd(g_cmd), .tl(g_tl), .cal_program_obs(g_cal_program_obs), .cal_descriptor_obs(g_cal_descriptor_obs),
        .cal_image_ready(g_cal_image_ready), .emb_start(g_emb_start), .emb_token(g_emb_token), .s_start(s_start),
        .s_stage(s_stage), .st(st), .su_obs_o(su_obs), .su_acc_o(su_acc), .x_oprog(x_oprog), .x_orows(x_orows),
        .x_oidle(x_oidle), .rom_ret_v(rom_ret_v), .dcs(dcs));
    ot_qfd_tt_ctlm_static_hr #(.STAGE_ME((STAGE_ME != 0) ? 1 : 0)) u_hr (
        .stage_start(s_start), .stage(s_stage),
        .rom_ret_i({rom_ret_v[1], 16'd0, 1'b0, 32'd0, 18'd0, 24'd0, 1'b0, rom_ret_v[0], 1'b1}), .cp_active(1'b0), .cp(cp), .me_image_ready(me_image_ready), .program_obs(program_obs),
        .layer_context_v(layer_context_v), .native_tok(native_tok), .native_pos(native_pos), .rom_cmd(ib_q),
        .command_stage(command_stage), .native_cmd(native_cmd), .me_observe(me_observe),
        .native_ret(native_ret), .ck_head(ck), .ck_pm0(ck), .ck_pm1(ck), .rst_n(rst_n),
        .h_start(st[48]), .token(st[47:30]), .pos(st[29:12]), .prog_base(st[11:0]),
        .pw_v(pw[74]), .pw_addr(pw[73:64]), .pw_data(pw[63:0]),
        .x_oacc(su_acc), .x_oidle(x_oidle), .x_oprog(x_oprog), .x_orows(x_orows),
        .kv_ok(kok), .kv_write_drained(kwd), .me_mem_ok(1'b1),
        .m_fin_o(), .m_fidx_o(), .m_fval_o(),
        .kvd_v(), .kvd_wbase(), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(), .kvd_jsh(), .kvd_tiles(),
        .kvd_k(), .kvd_nout(), .kvd_kindk(), .kvd_pos(), .me_clk_en(), .c_fault(hr_fault));
    qfd_tt_ctlm_dv_go #(.XPF_TRANSPORT_EDGES(XPF_TRANSPORT_EDGES)) u_go (.ck(ck), .rst_n(rst_n), .pw(pw), .st(st),
        .su_obs(su_obs), .me_observe(me_observe), .cp(cp), .me_image_ready(me_image_ready), .hr_fault(hr_fault),
        .dcs(dcs), .hr_lo(hr_lo), .dc(dc), .cf(cf), .control_stores_ready(control_stores_ready));
    qfd_tt_ctlm_dv_thru u_thru (.ck(ck), .rst_n(rst_n), .cmd_i(g_cmd), .cal_program_obs_i(g_cal_program_obs),
        .cal_descriptor_obs_i(g_cal_descriptor_obs), .cal_image_ready_i(g_cal_image_ready), .emb_start_i(g_emb_start),
        .emb_token_i(g_emb_token), .ib_i(ib_q), .ib_hr(ib_hr), .tl_i(g_tl), .tl(tl), .cmd(cmd), .cal_program_obs(cal_program_obs), .cal_descriptor_obs(cal_descriptor_obs),
        .cal_image_ready(cal_image_ready), .emb_start(emb_start), .emb_token(emb_token));
    // QW-DIEFIX 10-19: hr[452:73] in the slice layout: u_thru's qfd_dv_hr_pack (zero-logic permutation of the registered
    // ib_q; hr_contract.py follows the child port)
    assign hr = {ib_hr, hr_lo};
endmodule
