`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dshbm_mtp_closed_top (mtp-exact 2026-10-08): the DSpark control plane of the HBM accelerator built from the
// CLOSED 1.2 GHz block variants (results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/closure.json),
// connected, for the exactness regression.  Same ports as rtl/gpu/dshbm/ot_dshbm_dspark_top.sv (pinned, unchanged).
//   ctl        ot_dshbm_dspark_ctl FAST = 1                         (ctl_f2,  SS +1.25 / FF +10.1)
//   accept     ot_hdc_accept NSLOT 8 via ot_dshbm_accept_port       (accept_a0, SS +55.3 / FF +14.0)
//   argmax     ot_dshbm_argmax FAST = 1 (source_set successor)      (argmax_f1, SS +42.6 / FF +3.0, +1 cycle a row)
//   union      ot_dshbm_expert_union FAST = 1 (source_set successor)(union_f3, SS +9.5 / FF +10.8, +1 cycle a flush)
//   spec_state ot_dshbm_spec_state_f_token_edge TOKEN_EDGE_FIX = 1  (route1 SS +28.4 / FF +6.9, answers +5 cycles)
//   scratch    ot_gpu_scratch_service CAP2 = 1 (source_set successor)(scratch_c2, SS +80.2 / FF +18.6, read +1 cycle):
//              every engine command's verify-token block (cmd_toks) is written to the SM shared memory and read
//              back before the command is presented (the engine reads its pass tokens there); the write + read
//              cycles are a staging model, not a priced design term.
//   router     ot_gpu_router_topk as built (the registered successor is exact but has no physical closure: Yosys
//              elaboration assertion; recorded as not-closed).
// Opt-in: nothing instantiates it except the mtp-exact HBM bench (tools/mtp_exact_hbm_connected.py).
// ---------------------------------------------------------------------------
module ot_dshbm_mtp_closed_top #(
    parameter integer B      = 5,
    parameter integer PMAX   = 8,
    parameter integer TW     = 17,
    parameter integer NL     = 40,
    parameter integer NST    = 3,
    parameter integer MAXPOS = 128,
    parameter integer W      = 128,
    parameter integer WR     = 136,
    parameter integer SR     = 10,
    parameter integer TR     = 16,
    parameter integer NG     = 4,
    parameter integer NSRC   = 4,
    parameter [NSRC*4-1:0] RLOG = 16'h0111,
    parameter integer CKMAX  = 1 << 16,
    parameter integer AW     = 32,
    parameter integer LP     = 8,
    parameter integer FLAT   = 7,
    parameter integer NEXP   = 12,
    parameter integer KV     = 6,
    parameter integer NDEXP  = 4,
    parameter integer KD     = 3,
    parameter integer RP     = 4,
    parameter integer IW     = 9,
    parameter integer MUT    = 0,
    parameter integer ACCEPT_LEAF = 0,
    parameter integer TOKEN_EDGE_FIX = 1,
    parameter integer SCRATCH = 1
) (
    input  wire               clk,
    input  wire               rst_n,
    // host
    input  wire               start,
    input  wire [3:0]         cfg_gamma,
    input  wire               cfg_force,
    input  wire [15:0]        cfg_ngen,
    input  wire [15:0]        cfg_plen,
    output wire [15:0]        p_addr,
    input  wire [TW-1:0]      p_tok,
    output wire [15:0]        f_addr,
    input  wire [TW-1:0]      f_tok,
    output wire               e_v,
    output wire [TW-1:0]      e_tok,
    output wire [15:0]        e_idx,
    output wire               done,
    // engine commands
    output wire               cmd_v,
    input  wire               cmd_ready,
    output wire [3:0]         cmd_op,
    output wire [7:0]         cmd_idx,
    output wire [3:0]         cmd_ncol,
    output wire [31:0]        cmd_pos,
    output wire [TW-1:0]      cmd_tok1,
    output wire [PMAX*TW-1:0] cmd_toks,
    input  wire               eng_done,
    // logit rows into the epilogue
    input  wire               lg_v,
    input  wire               lg_last,
    input  wire               lg_bias_en,
    input  wire [LP-1:0]      lg_mask,
    input  wire [LP*32-1:0]   lg_vals,
    input  wire [LP*32-1:0]   lg_bias,
    output wire               am_v,
    output wire [TW-1:0]      am_idx,
    output wire               am_fault,
    // spec-state requests
    input  wire               sr_v,
    output wire               sr_ready,
    input  wire [3:0]         sr_kind,
    input  wire [15:0]        sr_idx,
    input  wire [31:0]        sr_pos,
    output wire               sa_v,
    output wire [AW-1:0]      sa_addr,
    output wire [TW-1:0]      sa_tok,
    output wire               sa_pad,
    output wire               sa_last,
    output wire               sa_err,
    output wire [31:0]        n_committed,
    // router vectors
    input  wire               rv_v,
    input  wire               rv_draft,
    input  wire [RP*32-1:0]   rv_vals,
    input  wire               rv_last,
    input  wire [2:0]         rv_col,
    output wire               t_v,
    output wire [KV*IW-1:0]   t_ids,
    output wire [2:0]         t_col,
    // expert union
    input  wire               u_clr,
    input  wire               u_flush,
    output wire               u_v,
    input  wire               u_ready,
    output wire [IW-1:0]      u_id,
    output wire [PMAX-1:0]    u_mask,
    output wire               u_last,
    // observation
    output wire               step_v,
    output wire [2:0]         step_a,
    output wire [3:0]         step_g,
    output wire [15:0]        steps,
    output wire [31:0]        cyc_total,
    output wire [31:0]        cyc_engine,
    output wire [31:0]        cyc_markov
);
    wire        n_set, tw_v;
    wire [31:0] n_val, tw_pos;
    wire [TW-1:0] tw_tok;
    wire        am_nan;
    wire               c_cmd_v, c_cmd_ready;
    wire [PMAX*TW-1:0] c_cmd_toks;
    ot_dshbm_dspark_ctl #(.B(B), .PMAX(PMAX), .TW(TW), .NL(NL), .NST(NST), .MAXPOS(MAXPOS), .MUT(MUT), .ACCEPT_LEAF(ACCEPT_LEAF),
        .FAST(1)) u_ctl (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_gamma(cfg_gamma), .cfg_force(cfg_force),
        .cfg_ngen(cfg_ngen), .cfg_plen(cfg_plen), .p_addr(p_addr), .p_tok(p_tok), .f_addr(f_addr), .f_tok(f_tok),
        .e_v(e_v), .e_tok(e_tok), .e_idx(e_idx), .done(done),
        .cmd_v(c_cmd_v), .cmd_ready(c_cmd_ready), .cmd_op(cmd_op), .cmd_idx(cmd_idx), .cmd_ncol(cmd_ncol),
        .cmd_pos(cmd_pos), .cmd_tok1(cmd_tok1), .cmd_toks(c_cmd_toks), .eng_done(eng_done),
        .am_v(am_v), .am_idx(am_idx), .n(n_committed), .n_set(n_set), .n_val(n_val),
        .tw_v(tw_v), .tw_pos(tw_pos), .tw_tok(tw_tok),
        .step_v(step_v), .step_a(step_a), .step_g(step_g), .steps(steps),
        .cyc_total(cyc_total), .cyc_engine(cyc_engine), .cyc_markov(cyc_markov));
    ot_dshbm_spec_state_f_token_edge #(.TOKEN_EDGE_FIX(TOKEN_EDGE_FIX), .W(W), .PMAX(PMAX), .WR(WR), .SR(SR), .TR(TR), .NG(NG), .NL(NL), .NST(NST),
        .NSRC(NSRC), .RLOG(RLOG), .CKMAX(CKMAX), .TW(TW), .AW(AW)) u_state (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .n(n_committed),
        .tw_v(tw_v), .tw_pos(tw_pos), .tw_tok(tw_tok),
        .req_v(sr_v), .req_ready(sr_ready), .req_kind(sr_kind), .req_idx(sr_idx), .req_pos(sr_pos),
        .a_v(sa_v), .a_addr(sa_addr), .a_tok(sa_tok), .a_pad(sa_pad), .a_last(sa_last), .a_err(sa_err));
    ot_dshbm_argmax #(.LP(LP), .IW(TW), .FLAT(FLAT), .FAST(1)) u_am (
        .clk(clk), .rst_n(rst_n), .in_v(lg_v), .in_last(lg_last), .in_bias_en(lg_bias_en), .in_mask(lg_mask),
        .in_vals(lg_vals), .in_bias(lg_bias), .out_v(am_v), .out_idx(am_idx), .out_nan(am_nan), .fault(am_fault));
    // ---- router selectors ----
    wire          tv_v, td_v;
    wire [KV*IW-1:0] tv_ids;
    wire [KD*IW-1:0] td_ids;
    ot_gpu_router_topk #(.N(NEXP), .P(RP), .K(KV), .IW(IW)) u_tv (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & ~rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(tv_v), .out_ids(tv_ids));
    ot_gpu_router_topk #(.N(NDEXP), .P(RP), .K(KD), .IW(IW)) u_td (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(td_v), .out_ids(td_ids));
    // column numbers in flight (vectors leave each selector in order; one kind at a time)
    reg [2:0] cq [0:7];
    reg [3:0] cq_w, cq_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cq_w <= 0; cq_r <= 0; end
        else begin
            if (rv_v && rv_last) begin cq[cq_w[2:0]] <= rv_col; cq_w <= cq_w + 1; end
            if (tv_v || td_v) cq_r <= cq_r + 1;
        end
    end
    assign t_v = tv_v | td_v;
    assign t_col = cq[cq_r[2:0]];
    genvar gk;
    generate
        for (gk = 0; gk < KV; gk = gk + 1) begin : g_ids
            if (gk < KD) assign t_ids[gk*IW +: IW] = td_v ? td_ids[gk*IW +: IW] : tv_ids[gk*IW +: IW];
            else         assign t_ids[gk*IW +: IW] = td_v ? {IW{1'b0}} : tv_ids[gk*IW +: IW];
        end
    endgenerate
    wire [KV-1:0] t_en = td_v ? {{(KV-KD){1'b0}}, {KD{1'b1}}} : {KV{1'b1}};
    // ---- union ----
    reg flush_pend;
    wire inflight = (cq_w != cq_r) || (rv_v && rv_last);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flush_pend <= 1'b0;
        else if (u_flush) flush_pend <= 1'b1;
        else if (flush_pend && !inflight) flush_pend <= 1'b0;
    // FAST = 1 scans >= 2 words: the routed shape is NE 384 / WB 32 (12 words); a reduced vehicle (NE 12) uses
    // WB 4 (3 words) -- the same successor logic, more word steps per flush.
    localparam integer UNE = NEXP > NDEXP ? NEXP : NDEXP;
    localparam integer UWB = (UNE >= 64) ? 32 : 4;
    ot_dshbm_expert_union #(.NE(UNE), .K(KV), .PM(PMAX), .IW(IW), .WB(UWB), .FAST(1)) u_un (
        .clk(clk), .rst_n(rst_n), .clr(u_clr), .add_v(t_v), .add_col(t_col), .add_ids(t_ids), .add_en(t_en),
        .flush(flush_pend && !inflight), .out_v(u_v), .out_ready(u_ready), .out_id(u_id), .out_mask(u_mask),
        .out_last(u_last), .busy(), .count());
    // ---- command staging through the SM shared memory (scratch_c2) ----
    localparam [2:0] Q_IDLE = 0, Q_WR = 1, Q_WD = 2, Q_RD = 3, Q_RDN = 4, Q_PRES = 5;
    reg  [2:0]   q_s;
    reg  [9:0]   q_a;
    reg  [PMAX*TW-1:0] q_toks;
    wire         m_ready, m_done;
    wire [511:0] m_rdata;
    wire         m_valid = (q_s == Q_WR) || (q_s == Q_RD);
    generate if (SCRATCH) begin : g_scr
        ot_gpu_scratch_service #(.CAP2(1)) u_scr (.clk(clk), .rst_n(rst_n), .valid(m_valid), .write(q_s == Q_WR),
            .ready(m_ready), .addr(q_a), .wdata({{(512 - PMAX*TW){1'b0}}, c_cmd_toks}), .done(m_done),
            .done_ready(1'b1), .rdata(m_rdata));
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin q_s <= Q_IDLE; q_a <= 0; end
            else case (q_s)
                Q_IDLE: if (c_cmd_v) q_s <= Q_WR;
                Q_WR:   if (m_ready) q_s <= Q_WD;
                Q_WD:   if (m_done) q_s <= Q_RD;
                Q_RD:   if (m_ready) q_s <= Q_RDN;
                Q_RDN:  if (m_done) begin q_toks <= m_rdata[PMAX*TW-1:0]; q_s <= Q_PRES; end
                default: if (cmd_ready) begin q_s <= Q_IDLE; q_a <= q_a + 1'b1; end
            endcase
        end
        assign cmd_v = (q_s == Q_PRES);
        assign cmd_toks = q_toks;
        assign c_cmd_ready = cmd_ready && (q_s == Q_PRES);
    end else begin : g_noscr
        assign cmd_v = c_cmd_v; assign cmd_toks = c_cmd_toks; assign c_cmd_ready = cmd_ready;
    end endgenerate
endmodule
