`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_ctrl (stream ds-control, 2026-10-08): the control plane of one DS-ROM S81 die (gap 11 of the T2 coverage
// ledger: package controller, stage guard, link layer, host queue and watchdog had no slot on any S81 die).
// One instance per die, in the die master dsfd_sp_ctrl (layer die), dsfd_sp_ctrl_src (stage-0 / embedding die:
// + host queue and boot gate) or dsfd_sp_ctrl_h (head-root die: + the sampler stop condition).
//
//   inbound message stream (from the collective slab's link lanes: ot_s81ph_link_ep is the reliable link layer --
//   CRC-32, sequence numbers, go-back-N replay, credits -- on every lane, closed in dsfd_coll_lane_w)
//     -> ot_s81_stage_guard (identity / framing / order checks)
//     -> ot_s81_pkg_ctrl (per-user context, HIDDEN payload -> VM slot, SIDE staging, SOURCE scheduling, reduction
//        and stop)
//     -> ot_s81_stage_seq (the stage program: job descriptors to the engine ports, completions, stage done)
//   hop port (ENG_HOP): ot_s81_hop_tx frames the stage hand-off (HIDDEN / SIDE / RESULT) from its job descriptor,
//     reading the VM, onto the outbound message stream (to the collective slab's link lanes);
//   ROLE 1 (SOURCE): ot_s81_host_cq (host command / completion queue with the progress watchdog) serves the SOURCE
//     controller's run configuration and prompt port; launches wait for boot_ok;
//   ROLE 2 (HEAD): ot_s81_stop between the head root's argmax (am_*) and the RESULT framer;
//   every role: ot_dsrom_stall_export (named-blocker snapshot) over the control plane's own stall causes.
// The other engine ports (field / PQ core, SU, HC, collective, scan service, selector, collector, head, embedding,
// Engram) are die nets cmd_* / dn_* to their slabs.  Program memory is loaded through pw_* (the die's cfg path).
// ---------------------------------------------------------------------------
module ot_s81_ctrl #(
    parameter integer ROLE     = 0,          // 0 layer, 1 SOURCE (stage 0), 2 HEAD root
    parameter integer MY_ID    = 0,
    parameter integer FLIT     = 512,
    parameter integer NW       = 21,
    parameter integer MAXU     = 16,
    parameter integer VWA      = 14,
    parameter integer XW       = 640,        // HIDDEN payload flits
    parameter integer RXB      = 0,
    parameter integer TXB      = 2048,
    parameter integer SIDE_TXB = 4096,
    parameter integer SIDE_RXB = 0,
    parameter integer SIDE_BASE= 8192,
    parameter integer SIDE_USH = 6,
    parameter integer NOPS     = 128,
    parameter integer NENG     = 12,
    parameter integer QD       = 8,
    parameter integer ENG_HOP  = 7,
    parameter integer SRC_LO   = 0, SRC_HI = 0, SRC2_LO = 4095, SRC2_HI = 0, GRP_LO = 4095, GRP_HI = 0,
    parameter [15:0]  TYPE_MASK = 16'h000A,
    parameter integer LEN_SIDE_MAX = 64,
    parameter integer PMAX     = 8,
    parameter integer CQ_DEPTH = 64,
    parameter integer WDOG     = 2000000,
    parameter integer STUCK    = 100000,
    parameter integer MUT      = 0,
    parameter integer OPW      = $clog2(NOPS),
    parameter integer ARGW     = 24,
    parameter integer SUW      = 10,
    parameter integer CMDW     = 1 + SUW + 2 * NW + ARGW + OPW,
    parameter integer TAGW     = 1 + OPW
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // cfg path: program memory and static configuration
    input  wire                  pw_v,
    input  wire [OPW-1:0]        pw_a,
    input  wire [4+ARGW-1:0]     pw_d,
    input  wire [OPW:0]          prog_len,
    input  wire [11:0]           cfg_users_static,   // non-SOURCE dies: the user namespace bound
    // inbound / outbound message streams (collective slab link lanes)
    input  wire                  in_valid,
    output wire                  in_ready,
    input  wire [FLIT-1:0]       in_data,
    input  wire                  in_last,
    output wire                  out_valid,
    input  wire                  out_ready,
    output wire [FLIT-1:0]       out_data,
    output wire                  out_last,
    // engine ports (the hop port is internal)
    output wire [NENG-1:0]       cmd_v,
    output wire [NENG*CMDW-1:0]  cmd_d,
    input  wire [NENG-1:0]       dn_v,
    input  wire [NENG*TAGW-1:0]  dn_tag,
    input  wire                  hop_go,             // dataflow: the next hop job's input is in the VM
    // vector memory: payload write port, hop read port
    output wire                  vm_we,
    output wire [VWA-1:0]        vm_waddr,
    output wire [FLIT-1:0]       vm_wdata,
    output wire                  vm_re,
    output wire [VWA-1:0]        vm_raddr,
    input  wire [FLIT-1:0]       vm_rq,
    // HEAD: the head root's argmax of the step
    input  wire                  am_v,
    input  wire [NW-1:0]         am_pos,
    input  wire [NW-1:0]         am_tok,
    input  wire [31:0]           am_val,
    // SOURCE: host command / completion ports, boot gate
    input  wire                  boot_ok,
    input  wire                  hc_valid,
    output wire                  hc_ready,
    input  wire [1:0]            hc_op,
    input  wire [7:0]            hc_tag,
    input  wire [7:0]            hc_user,
    input  wire [NW-1:0]         hc_pos,
    input  wire [NW-1:0]         hc_token,
    output wire                  cpl_valid,
    input  wire                  cpl_ready,
    output wire [2+8+8+NW+NW+32-1:0] cpl_data,
    // status
    output wire                  fault,
    output wire [15:0]           fault_vec,          // {seq, hop, pkg, guard} codes
    output wire                  stuck,
    output wire [15:0]           stuck_snap,
    output wire [31:0]           st_jobs,
    output wire [31:0]           st_tokens
);
    localparam integer SOURCE = (ROLE == 1);
    // ---- guard ----
    wire g_v, g_r, g_l; wire [FLIT-1:0] g_d;
    wire g_f; wire [3:0] g_fc; wire [127:0] g_fh; wire [31:0] g_msgs, g_flits;
    wire [7:0] cfg_users;
    ot_s81_stage_guard #(.FLIT(FLIT), .NW(NW), .MAXU(MAXU), .MY_ID(MY_ID), .SRC_LO(SRC_LO), .SRC_HI(SRC_HI),
        .SRC2_LO(SRC2_LO), .SRC2_HI(SRC2_HI), .GRP_LO(GRP_LO), .GRP_HI(GRP_HI), .TYPE_MASK(TYPE_MASK),
        .LEN_HID(XW), .LEN_SIDE_MAX(LEN_SIDE_MAX)) u_guard (
        .clk(clk), .rst_n(rst_n), .cfg_users(SOURCE ? {4'b0, cfg_users} : cfg_users_static),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(g_v), .out_ready(g_r), .out_data(g_d), .out_last(g_l),
        .fault(g_f), .fault_code(g_fc), .fault_hdr(g_fh), .st_msgs(g_msgs), .st_flits(g_flits));
    // ---- host queue (SOURCE) ----
    wire [NW-1:0] cfg_plen, cfg_glen, cfg_eos_id; wire [NW:0] cfg_maxl; wire cfg_eos_en;
    wire pr_re; wire [7:0] pr_user; wire [NW-1:0] pr_pos, pr_q;
    wire tok_v, tok_stop; wire [7:0] tok_user, users_done; wire [NW-1:0] tok_pos, tok_id;
    wire hq_f, hq_wd, hq_act; wire [3:0] hq_fc; wire [31:0] hq_wc;
    wire [15:0] snap;
    generate if (SOURCE) begin : g_src
        wire [31:0] s1, s2, s3, s4;
        ot_s81_host_cq #(.MAXU(MAXU), .PMAX(PMAX), .NW(NW), .TAGW(8), .CQ_DEPTH(CQ_DEPTH), .CAUSEW(32), .WDOG(WDOG),
                         .UCW(8)) u_hq (
            .clk(clk), .rst_n(rst_n), .cmd_valid(hc_valid), .cmd_ready(hc_ready), .cmd_op(hc_op), .cmd_tag(hc_tag),
            .cmd_user(hc_user), .cmd_pos(hc_pos), .cmd_token(hc_token), .cpl_valid(cpl_valid), .cpl_ready(cpl_ready),
            .cpl_data(cpl_data), .cfg_users(cfg_users), .cfg_prompt_len(cfg_plen), .cfg_gen_len(cfg_glen),
            .cfg_max_len(cfg_maxl), .cfg_eos_en(cfg_eos_en), .cfg_eos_id(cfg_eos_id), .boot_ok(boot_ok),
            .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
            .tok_valid(tok_v), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id), .users_done(users_done),
            .stall_cause({16'd0, snap}), .active(hq_act), .wdog(hq_wd), .wdog_cause(hq_wc), .fault(hq_f), .fault_code(hq_fc),
            .st_tokens(st_tokens), .st_spec_reads(s2), .st_cpl_stall(s3), .st_cq_high(s4));
    end else begin : g_nsrc
        assign hc_ready = 1'b0; assign cpl_valid = 1'b0; assign cpl_data = 0;
        assign cfg_users = 0; assign cfg_plen = 0; assign cfg_glen = 0; assign cfg_maxl = 0; assign cfg_eos_en = 0;
        assign cfg_eos_id = 0; assign pr_q = 0; assign hq_f = 1'b0; assign hq_fc = 0; assign hq_wd = 1'b0;
        assign hq_act = 1'b0; assign st_tokens = 0;
    end endgenerate
    // ---- package controller ----
    wire j_v, j_r, j_done; wire [11:0] j_u; wire [NW-1:0] j_p, j_t;
    wire run_eosen; wire [NW-1:0] run_eos; wire [NW:0] run_maxl;
    wire p_f; wire [3:0] p_fc; wire [31:0] p_jd;
    ot_s81_pkg_ctrl #(.MY_ID(MY_ID), .FLIT(FLIT), .NW(NW), .USER_W(12), .MAXU(MAXU), .VWA(VWA), .RXB(RXB), .RXW(XW),
        .SOURCE(SOURCE), .SIDE_USH(SIDE_USH), .SIDE_BASE(SIDE_BASE), .MUT(MUT)) u_pkg (
        .clk(clk), .rst_n(rst_n), .cfg_users(cfg_users), .cfg_prompt_len(cfg_plen), .cfg_gen_len(cfg_glen),
        .cfg_max_len(cfg_maxl), .cfg_eos_en(cfg_eos_en), .cfg_eos_id(cfg_eos_id), .boot_ok(SOURCE ? boot_ok : 1'b1),
        .in_valid(g_v), .in_ready(g_r), .in_data(g_d), .in_last(g_l),
        .job_v(j_v), .job_rdy(j_r), .job_user(j_u), .job_pos(j_p), .job_tok(j_t), .job_done(j_done),
        .run_eosen(run_eosen), .run_eos(run_eos), .run_maxl(run_maxl),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
        .tok_valid(tok_v), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id), .tok_stop(tok_stop),
        .users_done(users_done), .st_jobs_done(p_jd), .proto_fault(p_f), .fault_code(p_fc));
    // ---- stage program sequencer ----
    wire [NENG-1:0] s_cv; wire [NENG*CMDW-1:0] s_cd; wire [NENG-1:0] s_dv; wire [NENG*TAGW-1:0] s_dt;
    wire s_busy, s_f; wire [3:0] s_fc; wire [31:0] s_cmds, s_cs;
    ot_s81_stage_seq #(.NOPS(NOPS), .NENG(NENG), .ARGW(ARGW), .USER_W(SUW), .NW(NW), .QD(QD)) u_seq (
        .clk(clk), .rst_n(rst_n), .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(prog_len),
        .job_v(j_v), .job_rdy(j_r), .job_user(j_u[SUW-1:0]), .job_pos(j_p), .job_tok(j_t), .job_done(j_done),
        .cmd_v(s_cv), .cmd_d(s_cd), .dn_v(s_dv), .dn_tag(s_dt), .busy(s_busy), .fault(s_f), .fault_code(s_fc),
        .st_jobs(st_jobs), .st_cmds(s_cmds), .st_credit_stall(s_cs));
    // ---- hop port ----
    wire h_dv; wire [OPW:0] h_dt; wire h_f; wire [3:0] h_fc; wire [31:0] h_msgs;
    wire r_v, r_stop; wire [NW-1:0] r_tok; wire [31:0] r_val;
    generate if (ROLE == 2) begin : g_head
        wire [31:0] se, sm;
        ot_s81_stop #(.NW(NW)) u_stop (.clk(clk), .rst_n(rst_n), .am_v(am_v), .am_pos(am_pos), .am_tok(am_tok),
            .am_val(am_val), .run_eosen(run_eosen), .run_eos(run_eos), .run_maxl(run_maxl),
            .res_v(r_v), .res_tok(r_tok), .res_val(r_val), .res_stop(r_stop), .st_eos(se), .st_maxl(sm));
    end else begin : g_nhead
        assign r_v = 1'b0; assign r_tok = 0; assign r_val = 0; assign r_stop = 1'b0;
    end endgenerate
    // the RESULT framer consumes the held sampler result
    reg rh_v; reg [NW-1:0] rh_tok; reg [31:0] rh_val; reg rh_stop;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rh_v <= 1'b0; rh_tok <= 0; rh_val <= 0; rh_stop <= 1'b0; end
        else if (r_v) begin rh_v <= 1'b1; rh_tok <= r_tok; rh_val <= r_val; rh_stop <= r_stop; end
    ot_s81_hop_tx #(.MY_ID(MY_ID), .FLIT(FLIT), .NW(NW), .USER_W(12), .VWA(VWA), .XW(XW), .TXB(TXB),
        .SIDE_TXB(SIDE_TXB), .SIDE_RXB(SIDE_RXB), .CMDW(CMDW), .OPW(OPW), .ARGW(ARGW), .SUW(SUW), .QD(QD)) u_hop (
        .clk(clk), .rst_n(rst_n), .cmd_v(s_cv[ENG_HOP]), .cmd_d(s_cd[ENG_HOP*CMDW +: CMDW]), .dn_v(h_dv), .dn_tag(h_dt),
        .go(hop_go || (ROLE == 2 && r_v)), .res_v(r_v || rh_v || ROLE != 2), .res_tok(r_v ? r_tok : rh_tok),
        .res_val(r_v ? r_val : rh_val), .res_stop(r_v ? r_stop : rh_stop),
        .run_eosen(run_eosen), .run_eos(run_eos), .run_maxl(run_maxl),
        .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
        .fault(h_f), .fault_code(h_fc), .st_msgs(h_msgs));
    genvar e;
    generate for (e = 0; e < NENG; e = e + 1) begin : g_port
        if (e == ENG_HOP) begin : g_hop
            assign cmd_v[e] = 1'b0; assign cmd_d[e*CMDW +: CMDW] = 0;
            assign s_dv[e] = h_dv; assign s_dt[e*TAGW +: TAGW] = h_dt;
        end else begin : g_ext
            assign cmd_v[e] = s_cv[e]; assign cmd_d[e*CMDW +: CMDW] = s_cd[e*CMDW +: CMDW];
            assign s_dv[e] = dn_v[e]; assign s_dt[e*TAGW +: TAGW] = dn_tag[e*TAGW +: TAGW];
        end
    end endgenerate
    // ---- stall export: named blocker of a hang ----
    wire [15:0] cause = {s_f, h_f, p_f, g_f, hq_wd, 3'b0,
                         in_valid && !in_ready, out_valid && !out_ready, s_busy && (s_cs != 0), s_busy,
                         j_v && !j_r, hq_act, rh_v, |s_cv};
    wire progress = (|s_cv) || (|s_dv) || (in_valid && in_ready) || (out_valid && out_ready) || j_done;
    wire [16*32-1:0] scnt; wire [31:0] scyc, idle_run, idle_max, tdrop; wire tv; wire [47:0] tdat;
    ot_dsrom_stall_export #(.NC(16), .STUCK(STUCK), .TRACE_DEPTH(16)) u_stall (
        .clk(clk), .rst_n(rst_n), .active(s_busy || hq_act), .progress(progress), .cause(cause), .cnt(scnt),
        .stuck(stuck), .stuck_snap(snap), .stuck_cycle(scyc), .idle_run(idle_run), .idle_max(idle_max),
        .trace_valid(tv), .trace_ready(1'b1), .trace_data(tdat), .trace_drops(tdrop));
    assign stuck_snap = snap;
    assign fault = s_f || h_f || p_f || g_f || hq_f;
    assign fault_vec = {s_fc, h_fc, p_fc, g_fc};
endmodule
