`timescale 1ns/1ps
// =====================================================================================================================
// qfd_tt_ctlm_dv_lpf_parts -- children of qfd_tt_ctlm_dv_lpf (rtl/qwen_dv/qfd_tt_ctlm_dv_lpf.sv). HF-4 (HARD-FIX 0id, 10-18): qfd_tt_ctlm_dv (HARD_HR = 1, MUT = 0) re-cut as a WIRES-ONLY flat
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
// =====================================================================================================================
module qfd_tt_ctlm_dv_gi #(
    parameter integer LAST_STAGE = 37,
    parameter integer STAGE_ME = 0,
    parameter integer NU = 4,
    parameter integer UVM_STRIDE = 4096,
    parameter integer PIDX_STRIDE = 128,
    parameter integer UTAG_LSB = 6
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [186:0]  dh,
    input  wire [1:0]    dh_user,
    input  wire [106:0]  ss5,
    input  wire [9:0]    ag5,
    input  wire          fab,
    output wire [115:0]  cmd,
    output wire [75:0]   cal_program_obs,
    output wire [68:0]   cal_descriptor_obs,
    output wire          cal_image_ready,
    output reg           emb_start,
    output reg  [17:0]   emb_token,
    output wire          s_start,                // head stage start (u_hr stage_start; NU > 1 see hd_start)
    output wire [5:0]    s_stage,
    output wire [48:0]   st,
    output wire [15:0]   su_obs_o,
    output wire [23:0]   su_acc_o,
    output wire [15:0]   x_oprog,
    output wire [15:0]   x_orows,
    output wire          x_oidle,
    output wire [1:0]    rom_ret_v,              // the two live rom_ret bits {ag stn (fault), ME idle = !ag stn_busy}
    output wire [61:0]   dcs                     // dc inputs: {tok_clr, ss_tokv, ss_tok 18, ss_tval 32, ss_arl, ss_arland,
                                                 //  c_xc, ag_vm, ag_su_busy, ag_any, fab_q, c_fault, start_fault, c_ready}
);
    reg  [186:0] dh_q;
    reg  [106:0] ss_q;
    reg  [9:0]   ag_q;
    reg          fab_q;
    reg  [1:0]   dhu_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin dh_q <= 187'd0; ss_q <= 107'd0; ag_q <= 10'd0; fab_q <= 1'b0; dhu_q <= 2'd0; end
        else begin dh_q <= dh; ss_q <= ss5; ag_q <= ag5; fab_q <= fab; dhu_q <= (NU > 1) ? dh_user : 2'd0; end
    localparam integer UB = (NU > 1) ? $clog2(NU) : 1;
    wire [UB-1:0] s_user = dhu_q[UB-1:0];
    wire        d_start = dh_q[42];
    wire [5:0]  d_stage = dh_q[41:36];
    wire [17:0] s_tok = dh_q[35:18], s_pos = dh_q[17:0];
    wire [15:0] ss_prog = ss_q[60:45], ss_rows = ss_q[44:29];
    wire        ss_arl = ss_q[25], ss_tokv = ss_q[24];
    wire [23:0] ss_tok = ss_q[23:0];
    wire [31:0] ss_tval = ss_q[105:74];
    wire        ss_arland = ss_q[106];
    wire        ag_stn_busy = ag_q[9];
    wire        ag_any = ag_q[8], ag_vm = ag_q[6], ag_stn = ag_q[5], ag_su_busy = ag_q[1];

    wire        c_emb, c_seg, c_su, c_xc, c_run, c_done, c_fault, c_ready;
    wire [11:0] c_base; wire [8:0] c_pidx;
    wire [UB-1:0] c_user, c_done_user; wire [NU-1:0] c_run_u; wire [5:0] c_fcode;
    qfd_dv_cmd_cal_mu #(.MUT(0), .LAST_STAGE(LAST_STAGE), .NU(NU), .UVM_STRIDE(UVM_STRIDE), .PIDX_STRIDE(PIDX_STRIDE),
        .UTAG_LSB(UTAG_LSB), .UFOLD((NU > 1) ? 1 : 0)) u_cal (.ck(ck), .rst_n(rst_n),
        .pw_v(dh_q[118]), .pw_addr(dh_q[117:108]), .pw_data(dh_q[107:44]),
        .dw_v(dh_q[186]), .dw_addr(dh_q[185:183]), .dw_data(dh_q[182:119]),
        .start(d_start), .stage(d_stage), .start_user(s_user), .start_rng(1'b0), .start_first(10'd0), .start_cnt(10'd0), .cmd(cmd), .cmd_user(c_user), .loc_emb(c_emb),
        .loc_seg(c_seg), .loc_base(c_base),
        .su_issue(c_su), .su_pidx(c_pidx), .xc_issue(c_xc), .program_obs(cal_program_obs),
        .descriptor_obs(cal_descriptor_obs), .image_ready(c_ready), .running(c_run), .running_u(c_run_u), .done(c_done),
        .done_user(c_done_user), .fault(c_fault), .fault_code(c_fcode));
    wire        c_u0 = (NU == 1) || (c_user == {UB{1'b0}});
    wire        s_u0 = (NU == 1) || (s_user == {UB{1'b0}});
    assign cal_image_ready = c_ready;

    // head running stage (NU > 1): the hard leaf has ONE loaded stage (ROM relocation).  Latch it on user 0's dh start
    // (as today) and on every LOCAL SEG start with the stage of the SEGMENT's user (per-user stage bank), so each ME
    // segment reads its own user's layer.  A filler's dh start does not touch it.  NU = 1: hd = the dh start / stage.
    reg  [5:0]  stg_b [0:NU-1];
    integer     sg_i;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin for (sg_i = 0; sg_i < NU; sg_i = sg_i + 1) stg_b[sg_i] <= 6'd0; end
        else if (d_start) stg_b[s_user] <= d_stage;
    wire        hd_start = (NU == 1 || 1'b0) ? d_start : ((d_start && s_u0) || c_seg);
    wire [5:0]  hd_stage = (NU == 1 || 1'b0) ? d_stage : ((d_start && s_u0) ? d_stage : stg_b[c_user]);
    assign s_start = hd_start;                   // to u_hr stage_start / stage (the head running stage)
    assign s_stage = hd_stage;
    wire        s_me0 = (STAGE_ME == 0) ? d_start : (d_start && d_stage != 6'd0 && d_stage < LAST_STAGE[5:0]);
    wire        s_me = s_me0 && s_u0;
    reg  [17:0] tok_b [0:NU-1], pos_b [0:NU-1];
    reg         st_h; reg [17:0] st_tok, st_pos; reg [11:0] st_base;
    reg         start_fault;
    integer     ub_i;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            for (ub_i = 0; ub_i < NU; ub_i = ub_i + 1) begin tok_b[ub_i] <= 18'd0; pos_b[ub_i] <= 18'd0; end
            st_h <= 1'b0; st_tok <= 18'd0; st_pos <= 18'd0; st_base <= 12'd0;
            start_fault <= 1'b0; emb_start <= 1'b0; emb_token <= 18'd0;
        end else begin
            if (d_start) begin tok_b[s_user] <= s_tok; pos_b[s_user] <= s_pos; end
            st_h <= s_me | c_seg;
            if (s_me) begin st_tok <= s_tok; st_pos <= s_pos; st_base <= 12'd0; end
            else if (c_seg) begin st_tok <= tok_b[c_user]; st_pos <= pos_b[c_user]; st_base <= c_base; end
            if (s_me && c_seg) start_fault <= 1'b1;
            emb_start <= c_emb; emb_token <= tok_b[c_user];
        end
    assign st = {st_h, st_tok, st_pos, st_base};

    reg  [23:0] su_acc;
    reg  [15:0] su_obs;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin su_acc <= 24'd0; su_obs <= 16'd0; end
        else begin
            if (c_su && c_u0) su_acc <= su_acc + 24'd1;
            su_obs <= {c_su && c_u0, c_su && c_u0, 2'd2, 3'd0, c_pidx};
        end
    assign su_obs_o = su_obs;
    assign su_acc_o = su_acc;
    assign x_oprog = ss_prog;
    assign x_orows = ss_rows;
    assign x_oidle = !ag_su_busy;
    // rom_ret = {ag_stn, 16'd0, 1'b0, 32'd0, 18'd0, 24'd0, 1'b0, !ag_stn_busy, 1'b1}: constants assembled at the head pin
    assign rom_ret_v = {ag_stn, !ag_stn_busy};
    assign dcs = {d_start && d_stage == 6'd0, ss_tokv, ss_tok[17:0], ss_tval, ss_arl, ss_arland,
                  c_xc, ag_vm, ag_su_busy, ag_any, fab_q, c_fault, start_fault, c_ready};
    wire unused = &{1'b0, c_run, c_done, ss_q[73:61], ss_q[28:26], ss_tok[23:18], dh_q[43], c_run_u, c_done_user, c_fcode};
endmodule

module qfd_tt_ctlm_dv_go #(
    parameter integer XPF_TRANSPORT_EDGES = -1
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [74:0]   pw,
    input  wire [48:0]   st,
    input  wire [15:0]   su_obs,
    input  wire [15:0]   me_observe,
    input  wire [55:0]   cp,
    input  wire          me_image_ready,
    input  wire          hr_fault,
    input  wire [61:0]   dcs,
    output wire [72:0]   hr_lo,
    output reg  [55:0]   dc,
    output wire          cf,
    output wire          control_stores_ready
);
    wire        tok_clr = dcs[61], ss_tokv = dcs[60];
    wire [17:0] ss_tok = dcs[59:42];
    wire [31:0] ss_tval = dcs[41:10];
    wire        ss_arl = dcs[9], ss_arland = dcs[8], c_xc = dcs[7], ag_vm = dcs[6], ag_su_busy = dcs[5];
    wire        ag_any = dcs[4], fab_q = dcs[3], c_fault = dcs[2], start_fault = dcs[1], c_ready = dcs[0];
    reg          cp_fault;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) cp_fault <= 1'b0;
        else if (cp[0]) cp_fault <= 1'b1;
    generate if (XPF_TRANSPORT_EDGES < 0) begin : g_unassigned_arm_route
        initial $error("native XPF transport edges require assigned physical route");
    end endgenerate
    wire monitor_rs;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_xpf_reset (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(monitor_rs));
    wire [48:0] monitor_start;
    ot_hdc_delay #(.W(49), .D(1), .RESET(1)) u_xpf_start_face (.clk(ck), .rst_n(monitor_rs), .d(st), .q(monitor_start));
    wire dvm_stage_start = monitor_start[48] && monitor_start[11:0] == 0;
    wire [15:0] monitor_su;
    ot_hdc_delay #(.W(16), .D(1), .RESET(1)) u_xpf_su_face (.clk(ck), .rst_n(monitor_rs), .d(su_obs), .q(monitor_su));
    wire [74:0] monitor_pw;
    ot_hdc_delay #(.W(75), .D(1), .RESET(1)) u_xpf_pw_face (.clk(ck), .rst_n(monitor_rs), .d(pw), .q(monitor_pw));
    wire xpf_loader_fault, xpf_schedule_fault, xpf_active, xpf_loader_ready, xpf_monitor_ready;
    wire cfg_clear, cfg_v, cfg_seal; wire [2:0] cfg_index; wire [187:0] cfg_data;
    wire [3:0] cfg_count; wire [5:0] xpf_stage; wire [31:0] stop_cycle, xpf_cycle;
    wire [71:0] xpf;
    ot_qfd_xpf_dense_pw_loader u_xpf_loader (.clk(ck), .rst_n(monitor_rs), .stage_active(xpf_active),
        .pw_v(monitor_pw[74]), .pw_addr(monitor_pw[73:64]), .pw_data(monitor_pw[63:0]),
        .cfg_clear(cfg_clear), .cfg_v(cfg_v), .cfg_seal(cfg_seal), .cfg_index(cfg_index), .cfg_data(cfg_data),
        .cfg_count(cfg_count), .stage(xpf_stage), .stop_cycle(stop_cycle), .image_ready(xpf_loader_ready),
        .fault(xpf_loader_fault));
    wire [15:0] monitor_me;
    ot_hdc_delay #(.W(16), .D(1), .RESET(1)) u_xpf_me_face (.clk(ck), .rst_n(monitor_rs), .d(me_observe), .q(monitor_me));
    wire xpf_me_event = monitor_me[15];
    wire [11:0] xpf_me_pc = monitor_me[11:0];
    ot_qfd_xpf_static_schedule #(.N(4), .ARM_TRANSPORT_EDGES(XPF_TRANSPORT_EDGES)) u_xpf_schedule (.clk(ck),
        .rst_n(monitor_rs), .cfg_clear(cfg_clear), .cfg_v(cfg_v), .cfg_seal(cfg_seal),
        .cfg_index(cfg_index[1:0]), .cfg_data(cfg_data), .cfg_count(cfg_count[2:0]),
        .start(dvm_stage_start), .stop(xpf_active && xpf_cycle == stop_cycle), .stage(xpf_stage),
        .cp_issue(monitor_me[15] && monitor_me[13:12] == 3), .cp_pc(xpf_me_pc),
        .me_issue(xpf_me_event && monitor_me[13:12] == 1), .me_pc(xpf_me_pc),
        .su_issue(monitor_su[15]), .su_pc(monitor_su[11:0]),
        .xpf(xpf), .image_ready(xpf_monitor_ready), .fault(xpf_schedule_fault), .active(xpf_active), .cycle(xpf_cycle));
    assign control_stores_ready = me_image_ready && c_ready && xpf_loader_ready && xpf_monitor_ready;
    reg hv; reg [72:0] hr_lo_r;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin hv <= 1'b0; hr_lo_r <= 73'd0; end
        else begin hv <= 1'b1; hr_lo_r <= {xpf, hv}; end
    assign hr_lo = hr_lo_r;
    wire core_fault = hr_fault | cp_fault | start_fault | xpf_loader_fault | xpf_schedule_fault;
    reg  tok_seen, xc_busy, arl_d;
    reg  [17:0] ntok;
    reg  [31:0] nval;
    wire        coll_done = ss_arland && ss_arl;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tok_seen <= 1'b0; ntok <= 18'd0; nval <= 32'd0; xc_busy <= 1'b0; arl_d <= 1'b0; dc <= 56'd0; end
        else begin
            arl_d <= ss_arl;
            if (tok_clr) tok_seen <= 1'b0;
            else if (ss_tokv) begin tok_seen <= 1'b1; ntok <= ss_tok; nval <= ss_tval; end
            if (c_xc) xc_busy <= 1'b1; else if (coll_done) xc_busy <= 1'b0;
            dc <= {ag_vm, !ag_su_busy, xc_busy, core_fault, c_fault | ag_any | fab_q, tok_seen, ntok, nval};
        end
    assign cf = core_fault | c_fault;
    wire unused = &{1'b0, arl_d, cfg_index[2], cfg_count[3]};
endmodule

module qfd_tt_ctlm_dv_thru (
    input  wire          ck,                     // region membership only (no state)
    input  wire          rst_n,                  // region membership only (no state)
    input  wire [115:0]  cmd_i,
    input  wire [75:0]   cal_program_obs_i,
    input  wire [68:0]   cal_descriptor_obs_i,
    input  wire          cal_image_ready_i,
    input  wire          emb_start_i,
    input  wire [17:0]   emb_token_i,
    output wire [115:0]  cmd,
    output wire [75:0]   cal_program_obs,
    output wire [68:0]   cal_descriptor_obs,
    output wire          cal_image_ready,
    output wire          emb_start,
    output wire [17:0]   emb_token
);
    assign cmd = cmd_i;
    assign cal_program_obs = cal_program_obs_i;
    assign cal_descriptor_obs = cal_descriptor_obs_i;
    assign cal_image_ready = cal_image_ready_i;
    assign emb_start = emb_start_i;
    assign emb_token = emb_token_i;
    wire unused = &{1'b0, ck, rst_n};
endmodule

