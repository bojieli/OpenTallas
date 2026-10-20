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
// MU-QW-DIE 10-19: u_gi takes qfd_tt_ctlm_dv's OPSEG (MU-QW-B1 op-granular filler starts from the op-start leaf, explicit
//   calendar ranges, per-user stage bank on leaf starts, filler result -> its tok / pos bank, dc user-0 gate) and the boot
//   context record (coordinator 0ka: CTX_DW, image DW5 / DW6 -> filler banks on the seal edge).  The leaf
//   qfd_sys_face_mu_dhuser #(OPSEG 1) is g_op.u_leaf in here (its own hard tile, MU-LEAF-KIT), observing dh_q[43:0];
//   op_fault (leaf fault | start collision | bad context record) rides the dcs start_fault bit (both OR into core_fault,
//   as in qfd_tt_ctlm_dv).  OPSEG 0: the leaf inputs are tied 0 and every edge is the previous u_gi.
// =====================================================================================================================
module qfd_tt_ctlm_dv_gi #(
    parameter integer LAST_STAGE = 37,
    parameter integer STAGE_ME = 0,
    parameter integer NU = 4,
    parameter integer UVM_STRIDE = 4096,
    parameter integer PIDX_STRIDE = 128,
    parameter integer UTAG_LSB = 6,
    parameter integer INIT_U0 = 0, INIT_FIRST = -1, INIT_CNT = 0,
    parameter integer OPSEG = 0,
    parameter integer OPSEG_EXPANDED = 0,
    parameter integer OPSEG_PINREG = 0,
    parameter OPSEG_VIAMAP1 = "", OPSEG_VIAMAP2 = "",
    parameter OPSEG_INST1 = "qfd_tt_ctlm_opseg_b1", OPSEG_INST2 = "qfd_tt_ctlm_opseg_b2",
    parameter integer CTX_SRC = 0, FCTX = 0,
    parameter [11:0] NCTX_BASE = 12'h010,
    parameter OPSEG_VIAMAP = ""       ,
    parameter OPSEG_INST = "qfd_tt_ctlm_opseg",
    parameter integer PRIVATE_CALR = 0,          // QW-F16PROG4: 1 = CALR two-ROM calendar + LOCAL4 table-load request lane
    parameter integer F16WTN = 0                 // QW-F16PROG4: 1 = F16 typed witness control (SAFE_PHYS) in the core
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [74:0]   pw,                     // F16WTN: the landed TT PW bundle (same port as u_hr / u_go); else unused
    input  wire [82:0]   f16_auth,               // F16WTN: {begin, all_copies_auth, fusedcap, digest 64, epoch 16} (SYSFACE)
    input  wire [37:0]   f16_obs,                // F16WTN: {observation 16 {v, user 2, slice 4, pc 9}, stage 6, epoch 16}
    output wire [16:0]   f16_st,                 // F16WTN: {fault, group 4, user 2, group_complete, awc 4, active 4, ready}
    output wire [8:0]    treq,                   // PRIVATE_CALR: {valid, stage 6, user 2} registered request lane -> slices
    input  wire [186:0]  dh,
    input  wire [1:0]    dh_user,
    input  wire          init_u0,                  // explicit static admission INIT selector, aligned to DH stage0
    input  wire [128:0]  ctx_x,
    input  wire          mu_fault,
    input  wire [106:0]  ss5,
    input  wire [9:0]    ag5,
    input  wire          fab,
    output wire [115:0]  cmd,
    output wire [1087:0] tl,
    output wire [75:0]   cal_program_obs,
    output wire [68:0]   cal_descriptor_obs,
    output wire          cal_image_ready,
    output reg           emb_start,
    output reg  [17:0]   emb_token,
    output wire          s_start,                // head stage start (u_hr stage_start; NU > 1 see hd_start)
    output wire [5:0]    s_stage,
    output wire [48:0]   st,
    output wire [37:0]   fctx,                   // {context pulse, override hold, tok18, pos18}
    output reg  [1:0]    hu,                     // MU-DQ-D2DUSER: user of the latest head start (-> u_thru native_pos[17:16])
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
    reg init_u0_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) init_u0_q <= 1'b0;
        else init_u0_q <= (INIT_U0 != 0) ? init_u0 : 1'b0;
    initial if (INIT_U0 != 0 && (INIT_FIRST < 0 || INIT_FIRST % 4 != 0 || INIT_CNT < 1 || INIT_CNT > 1023 || INIT_FIRST + INIT_CNT > 1024))
        $error("INIT_U0 requires a source-bound aligned INIT_FIRST/INIT_CNT programme range");
    localparam integer UB = (NU > 1) ? $clog2(NU) : 1;
    localparam integer OPS = (OPSEG != 0 && NU > 1) ? 1 : 0;
    localparam integer NF = (NU > 1) ? NU - 1 : 1;
    wire [UB-1:0] s_user = (OPS != 0) ? {UB{1'b0}} : dhu_q[UB-1:0];
    wire        op_v, op_lfault; wire [1:0] op_user; wire [5:0] op_stage; wire [9:0] op_first, op_cnt;
    generate if (OPS != 0) begin : g_op
        qfd_sys_face_mu_dhuser #(.NU(NU), .OPSEG(1), .EXPANDED(OPSEG_EXPANDED), .PINREG(OPSEG_PINREG), .VIAMAP1(OPSEG_VIAMAP1), .VIAMAP2(OPSEG_VIAMAP2), .INSTANCE1(OPSEG_INST1), .INSTANCE2(OPSEG_INST2), .LAST_STAGE(LAST_STAGE), .VIAMAP(OPSEG_VIAMAP), .INSTANCE(OPSEG_INST))
            u_leaf (.ck(ck), .rst_n(rst_n), .dh_run(dh_q[43:0]), .dh_user(), .res_user(), .mu_fault(op_lfault), .op_v(op_v),
            .op_user(op_user), .op_stage(op_stage), .op_first(op_first), .op_cnt(op_cnt), .op_ff(), .op_fcode());
    end else begin : g_no_op
        assign op_v = 1'b0; assign op_lfault = 1'b0; assign op_user = 2'd0; assign op_stage = 6'd0;
        assign op_first = 10'd0; assign op_cnt = 10'd0;
    end endgenerate
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
    wire [1:0]  ss_tu = ss_q[27:26];                // OPSEG: the user of tok_idx when tok_v (MU-QW-AMIX contract)

    // OPSEG op starts (leaf) and the boot context record (see qfd_tt_ctlm_dv OPSEG)
    wire [127:0] c_ctx_cal; wire c_ctxld_cal;
    reg [128:0] ctx_q;
    reg mu_fault_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin ctx_q <= 129'd0; mu_fault_q <= 1'b0; end
        else begin ctx_q <= (CTX_SRC != 0 && OPS != 0) ? ctx_x : 129'd0; mu_fault_q <= mu_fault; end
    wire x_ld = (CTX_SRC != 0) && (OPS != 0) && ctx_q[128];
    wire [127:0] c_ctx = x_ld ? ctx_q[127:0] : c_ctx_cal;
    wire c_ctxld = c_ctxld_cal || x_ld;
    wire r_fill; wire [UB-1:0] r_wr;
    wire        l_v = (OPS != 0) && op_v;
    wire [UB-1:0] l_user = op_user[UB-1:0];
    wire        l_start = l_v && !d_start;            // the face start wins a collision
    wire        op_coll = l_v && d_start;
    wire [2:0]  ctx_mask = c_ctx[110:108];
    wire        ctx_ok = c_ctx[127:112] == 16'h4D43 && !c_ctx[111] && (({1'b0, ctx_mask} >> (NU - 1)) == 4'd0);
    wire x_hit = x_ld && (c_ctxld_cal || (l_v && !d_start && op_user != 2'd0 && ctx_mask[op_user - 2'd1]) ||
                                  (r_fill && ss_tu != 2'd0 && ctx_mask[ss_tu - 2'd1]));
    wire        ctx_ld = (OPS != 0) && c_ctxld && ctx_ok && !x_hit;
    wire        ctx_bad = (OPS != 0) && c_ctxld && (!ctx_ok || x_hit);
    wire u0_init_start = (INIT_U0 != 0) && init_u0_q && d_start && d_stage == 6'd0 && s_user == {UB{1'b0}};
    wire init_u0_bad = init_u0_q && !u0_init_start;
    reg         op_fault;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) op_fault <= 1'b0;
        else if (((OPS != 0) && op_lfault) || op_coll || ctx_bad || mu_fault_q || ctx_write_fault || init_u0_bad) op_fault <= 1'b1;
    wire        u_start = d_start || l_start;
    wire [5:0]  u_stage = l_start ? op_stage : d_stage;
    wire [UB-1:0] u_user = l_start ? l_user : s_user;

    wire ctx_write_fault;
    wire        c_emb, c_seg, c_su, c_xc, c_run, c_done, c_fault, c_ready;
    wire [11:0] c_base; wire [8:0] c_pidx;
    wire [UB-1:0] c_user, c_done_user; wire [NU-1:0] c_run_u; wire [5:0] c_fcode;
    wire        c_tload; wire [5:0] c_tstage; wire [1:0] c_tuser;
    qfd_dv_cmd_cal_mu #(.MUT(0), .LAST_STAGE(LAST_STAGE), .NU(NU), .UVM_STRIDE(UVM_STRIDE), .PIDX_STRIDE(PIDX_STRIDE),
        .UTAG_LSB(UTAG_LSB), .UFOLD((NU > 1) ? 1 : 0), .CTX_DW(OPS), .TABLE_ROM(PRIVATE_CALR), .CALENDAR_ROM(PRIVATE_CALR))
        u_cal (.ck(ck), .rst_n(rst_n), .table_load(c_tload), .table_stage(c_tstage), .table_user(c_tuser),
        .pw_v(dh_q[118]), .pw_addr(dh_q[117:108]), .pw_data(dh_q[107:44]),
        .dw_v(dh_q[186]), .dw_addr(dh_q[185:183]), .dw_data(dh_q[182:119]),
        .start(u_start), .stage(u_stage), .start_user(u_user), .start_rng(l_start || u0_init_start), .start_first(u0_init_start ? 10'(INIT_FIRST) : op_first), .start_cnt(u0_init_start ? 10'(INIT_CNT) : op_cnt), .cmd(cmd), .tl(tl), .cmd_user(c_user), .loc_emb(c_emb),
        .loc_seg(c_seg), .loc_base(c_base),
        .su_issue(c_su), .su_pidx(c_pidx), .xc_issue(c_xc), .program_obs(cal_program_obs),
        .descriptor_obs(cal_descriptor_obs), .image_ready(c_ready), .running(c_run), .running_u(c_run_u), .done(c_done),
        .done_user(c_done_user), .fault(c_fault), .fault_code(c_fcode), .ctx_dw(c_ctx_cal), .ctx_load(c_ctxld_cal));
    qfd_mu_context_guard #(.NU(NU), .ENABLE(OPS), .MUT(0)) u_ctx_guard (
        .ck(ck), .rst_n(rst_n), .load(ctx_ld), .load_mask(ctx_mask),
        .consume(c_emb || c_seg), .consume_user(c_user),
        .result_write(r_fill), .result_user(r_wr), .fault(ctx_write_fault));
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
        else begin
            if (d_start) stg_b[s_user] <= d_stage;
            else if (l_start) stg_b[l_user] <= op_stage;            // OPSEG: the leaf start's user
        end
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
    assign      r_fill = (OPS != 0) && ss_tokv && ss_tu != 2'd0 && {1'b0, ss_tu} < 3'(NU);   // OPSEG filler result
    assign r_wr = ss_tu[UB-1:0];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            for (ub_i = 0; ub_i < NU; ub_i = ub_i + 1) begin tok_b[ub_i] <= 18'd0; pos_b[ub_i] <= 18'd0; end
            st_h <= 1'b0; st_tok <= 18'd0; st_pos <= 18'd0; st_base <= 12'd0;
            start_fault <= 1'b0; emb_start <= 1'b0; emb_token <= 18'd0;
        end else begin
            if (ctx_ld)
                for (ub_i = 1; ub_i < NU; ub_i = ub_i + 1)
                    if (ctx_mask[ub_i - 1]) begin
                        tok_b[ub_i] <= c_ctx[36 * (ub_i - 1) + 18 +: 18]; pos_b[ub_i] <= c_ctx[36 * (ub_i - 1) +: 18];
                    end
            if (d_start) begin tok_b[s_user] <= s_tok; pos_b[s_user] <= s_pos; end
            if (r_fill) begin tok_b[r_wr] <= ss_tok[17:0]; pos_b[r_wr] <= pos_b[r_wr] + 18'd1; end
            st_h <= s_me | c_seg;
            if (s_me) begin st_tok <= s_tok; st_pos <= s_pos; st_base <= 12'd0; end
            else if (c_seg) begin st_tok <= tok_b[c_user]; st_pos <= pos_b[c_user]; st_base <= c_base; end
            if (s_me && c_seg) start_fault <= 1'b1;
            emb_start <= c_emb; emb_token <= tok_b[c_user];
        end
    assign st = {st_h, st_tok, st_pos, st_base};
    // MU-DQ-D2DUSER (10-19): as qfd_tt_ctlm_dv hu (same edge as st; NU = 1 constant 0)
    always @(posedge ck or negedge rst_n)
        if (!rst_n) hu <= 2'd0;
        else if (s_me) hu <= 2'd0;
        else if (c_seg) hu <= (NU > 1) ? 2'(c_user) : 2'd0;

    // Same core-edge copies as the flat controller; cross as one landed record to u_thru.
    reg [1:0] fcx, fh;
    reg [17:0] f1_tok, f1_pos, ov_tok, ov_pos;
    reg ov;
    wire f0 = (FCTX != 0) && (OPS != 0) && st_h && st_base == NCTX_BASE && hu != 2'd0;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            fcx <= 2'd0; fh <= 2'd0; f1_tok <= 18'd0; f1_pos <= 18'd0;
            ov <= 1'b0; ov_tok <= 18'd0; ov_pos <= 18'd0;
        end else begin
            fcx <= {fcx[0], f0}; fh <= {fh[0], st_h};
            f1_tok <= st_tok; f1_pos <= st_pos;
            if (fh[0]) begin ov <= fcx[0]; if (fcx[0]) begin ov_tok <= f1_tok; ov_pos <= f1_pos; end end
        end
    assign fctx = {fcx[1], ov, ov_tok, ov_pos};
    // ---- QW-F16PROG4 PRIVATE_CALR: the LOCAL4 table-load pulse leaves the core as ONE registered 9-bit request lane
    //      (+1 edge here; die transport and the slice face register are priced in tools/qwen_static_schedule/f16_calr_edges.py)
    generate if (PRIVATE_CALR != 0) begin : g_calr
        reg [8:0] treq_q;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) treq_q <= 9'd0;
            else treq_q <= {c_tload, c_tload ? {c_tstage, c_tuser} : 8'd0};
        assign treq = treq_q;
    end else begin : g_no_calr
        assign treq = 9'd0;
        wire unused_t = &{1'b0, c_tload, c_tstage, c_tuser};
    end endgenerate
    // ---- QW-F16PROG4 F16WTN: typed witness control, SAFE_PHYS (+2 edges on every output, priced in f16_calr_edges.py)
    //      start = the calendar's ACCEPTED start (u_start / u_user / u_stage, face + OPSEG leaf), epoch = the context's
//      token identity (dh token, or the OPSEG user's token bank) -- the typed execution events carry the same field;
    //      retire = calendar per-user completion (c_done / c_done_user) qualified by ME idle (!ag_stn_busy: the ME station
    //      has no outstanding read).  Fault joins start_fault (core_fault -> dc / cf).
    wire        w_fault;
    wire [15:0] u_tokid = l_start ? tok_b[l_user][15:0] : s_tok[15:0];   // the context's token identity at its start
    generate if (F16WTN != 0) begin : g_wtn
        qfd_tt_ctlm_dv_wtn u_wtn (.ck(ck), .rst_n(rst_n), .pw(pw), .auth(f16_auth),
            .start({u_start, 2'(u_user), u_stage, u_tokid}), .retire({c_done, 2'(c_done_user), !ag_stn_busy}), .obs(f16_obs),
            .st(f16_st));
        assign w_fault = f16_st[16];
    end else begin : g_no_wtn
        assign f16_st = 17'd0; assign w_fault = 1'b0;
        wire unused_w = &{1'b0, pw, f16_auth, f16_obs};
    end endgenerate

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
    // OPSEG: dc ntok / nval / tok_seen take user-0 results only; op_fault joins start_fault (both into core_fault)
    assign dcs = {d_start && d_stage == 6'd0, ss_tokv && (OPS == 0 || ss_tu == 2'd0), ss_tok[17:0], ss_tval, ss_arl, ss_arland,
                  c_xc, ag_vm, ag_su_busy, ag_any, fab_q, c_fault, start_fault | op_fault | w_fault, c_ready};
    wire unused = &{1'b0, c_run, c_done, ss_q[73:61], ss_q[28], ss_tok[23:18], dh_q[43], c_run_u, c_done_user, c_fcode, op_user,
                    NF[0]};
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
    input  wire [379:0]  ib_i,                   // QW-DIEFIX 10-19: the head's registered ROM command (cmd380 order)
    output wire [379:0]  ib_hr,                  //   -> hr[452:73] in the slice layout (qfd_dv_hr_pack, zero logic)
    input  wire [37:0]   fctx_i,
    input  wire          lcv_i,
    input  wire [17:0]   ntok_i,
    output wire          layer_context_v,
    output wire [17:0]   native_tok,
    input  wire [1:0]    hu_i,                   // MU-DQ-D2DUSER: u_gi hu (core) -> native_pos[17:16] (one OR, no state;
    input  wire [17:0]   npos_i,                 //   hu_i is 0 at NU = 1)
    input  wire [16:0]   f16_st_i,               // QW-F16PROG4: u_gi F16 status (core) -> f16_st (hr region, like cmd)
    output wire [16:0]   f16_st,
    input  wire [8:0]    treq_i,                 // QW-F16PROG4: u_gi table request lane -> table_req (like cmd)
    output wire [8:0]    table_req,
    output wire [17:0]   native_pos,
    output wire [115:0]  cmd,
    output wire [75:0]   cal_program_obs,
    output wire [68:0]   cal_descriptor_obs,
    output wire          cal_image_ready,
    output wire          emb_start,
    output wire [17:0]   emb_token
);
    assign cmd = cmd_i;
    assign layer_context_v = lcv_i | fctx_i[37];
    assign native_tok = fctx_i[36] ? fctx_i[35:18] : ntok_i;
    assign native_pos = (fctx_i[36] ? {2'b00, fctx_i[15:0]} : npos_i) | {hu_i, 16'd0};
    assign f16_st = f16_st_i;
    assign table_req = treq_i;
    assign cal_program_obs = cal_program_obs_i;
    assign cal_descriptor_obs = cal_descriptor_obs_i;
    assign cal_image_ready = cal_image_ready_i;
    assign emb_start = emb_start_i;
    assign emb_token = emb_token_i;
    qfd_dv_hr_pack #(.ASBUILT(0)) u_hr_pack (.cmd(ib_i), .hr(ib_hr));
    wire unused = &{1'b0, ck, rst_n};
endmodule

