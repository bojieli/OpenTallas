`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DSpark (V4.1 MTP) control plane of the V4.1 HBM comparator: default-off build top.
//
// Composes the new blocks with the W19 router selector:
//   ot_dshbm_dspark_ctl     the speculative loop (accept through ot_dshbm_accept_port: ot_hdc_accept
//                           or Codex's protected DS MTP accept leaf, ACCEPT_LEAF = 1),
//                            (prefill, draft, Markov chain, verify,
//                           accept, commit = rollback), commands to the SM cluster;
//   ot_dshbm_spec_state     position-indexed state addressing (rings sized for exact
//                           rollback), the token-history ring;
//   ot_dshbm_argmax         the SM epilogue argmax (verify targets; Markov bias add);
//   ot_gpu_router_topk x 2  W19's exact top-K selector: the backbone's top-KV of NEXP
//                           per verify position, the drafter's top-KD of NDEXP per block row;
//   ot_dshbm_expert_union   the union of a pass's per-column selections, ascending by id,
//                           with per-expert column masks -> ot_gpu_expert_fetch (outside).
// Router vectors arrive RP values a beat with their column number; a union flush waits
// until every vector in the selectors has come out.
// Nothing here is instantiated by any existing top: the build is opt-in.
// ---------------------------------------------------------------------------
module ot_dshbm_dspark_top_m #(
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
    parameter integer FAST   = 0,      // 1: the 1.2 GHz SS successors (hbm_accel_fmax_inventory_20261004/ctl):
                                       //    ctl FAST, ot_dshbm_spec_state_f (answers +4 cycles), router top-K
                                       //    ot_gpu_router_topk_f (+1 cycle a select), union FAST (same cycles)
    parameter integer SPECF  = FAST,   // mtp-hbm 2026-10-08: spec-state successor select, separate from FAST
                                       //    (ot_dshbm_spec_state_f owned by stream mtp-exact; 0 = the exact original)
    parameter integer UNF    = FAST,   // union FAST (registered scan; needs NE >= WB = 32, i.e. full shape)
    parameter integer AMF    = 0,      // argmax FAST (registered beat keys, +1 cycle a row; argmax_f1)
    parameter integer PRL    = 0,      // ctl prompt / forced-token read latency (registered host read ports)
    parameter integer XSEL   = 0       // 1: no selectors here: the per-column top-K selections arrive on x_v /
                                       //    x_ids / x_col / x_draft (the die's hfd_router selector), rv_* unused
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
    // external selections (XSEL = 1)
    input  wire               x_v,
    input  wire               x_draft,
    input  wire [KV*IW-1:0]   x_ids,
    input  wire [2:0]         x_col,
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
    ot_dshbm_dspark_ctl_m #(.B(B), .PMAX(PMAX), .TW(TW), .NL(NL), .NST(NST), .MAXPOS(MAXPOS), .MUT(MUT), .ACCEPT_LEAF(ACCEPT_LEAF), .FAST(FAST), .PRL(PRL)) u_ctl (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_gamma(cfg_gamma), .cfg_force(cfg_force),
        .cfg_ngen(cfg_ngen), .cfg_plen(cfg_plen), .p_addr(p_addr), .p_tok(p_tok), .f_addr(f_addr), .f_tok(f_tok),
        .e_v(e_v), .e_tok(e_tok), .e_idx(e_idx), .done(done),
        .cmd_v(cmd_v), .cmd_ready(cmd_ready), .cmd_op(cmd_op), .cmd_idx(cmd_idx), .cmd_ncol(cmd_ncol),
        .cmd_pos(cmd_pos), .cmd_tok1(cmd_tok1), .cmd_toks(cmd_toks), .eng_done(eng_done),
        .am_v(am_v), .am_idx(am_idx), .n(n_committed), .n_set(n_set), .n_val(n_val),
        .tw_v(tw_v), .tw_pos(tw_pos), .tw_tok(tw_tok),
        .step_v(step_v), .step_a(step_a), .step_g(step_g), .steps(steps),
        .cyc_total(cyc_total), .cyc_engine(cyc_engine), .cyc_markov(cyc_markov));
    generate if (SPECF == 0) begin : g_state0
    ot_dshbm_spec_state #(.W(W), .PMAX(PMAX), .WR(WR), .SR(SR), .TR(TR), .NG(NG), .NL(NL), .NST(NST),
        .NSRC(NSRC), .RLOG(RLOG), .CKMAX(CKMAX), .TW(TW), .AW(AW)) u_state (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .n(n_committed),
        .tw_v(tw_v), .tw_pos(tw_pos), .tw_tok(tw_tok),
        .req_v(sr_v), .req_ready(sr_ready), .req_kind(sr_kind), .req_idx(sr_idx), .req_pos(sr_pos),
        .a_v(sa_v), .a_addr(sa_addr), .a_tok(sa_tok), .a_pad(sa_pad), .a_last(sa_last), .a_err(sa_err));
    end else begin : g_state1
    ot_dshbm_spec_state_f #(.W(W), .PMAX(PMAX), .WR(WR), .SR(SR), .TR(TR), .NG(NG), .NL(NL), .NST(NST),
        .NSRC(NSRC), .RLOG(RLOG), .CKMAX(CKMAX), .TW(TW), .AW(AW)) u_state (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .n(n_committed),
        .tw_v(tw_v), .tw_pos(tw_pos), .tw_tok(tw_tok),
        .req_v(sr_v), .req_ready(sr_ready), .req_kind(sr_kind), .req_idx(sr_idx), .req_pos(sr_pos),
        .a_v(sa_v), .a_addr(sa_addr), .a_tok(sa_tok), .a_pad(sa_pad), .a_last(sa_last), .a_err(sa_err));
    end endgenerate
    ot_dshbm_argmax_m #(.LP(LP), .IW(TW), .FLAT(FLAT), .FAST(AMF)) u_am (
        .clk(clk), .rst_n(rst_n), .in_v(lg_v), .in_last(lg_last), .in_bias_en(lg_bias_en), .in_mask(lg_mask),
        .in_vals(lg_vals), .in_bias(lg_bias), .out_v(am_v), .out_idx(am_idx), .out_nan(am_nan), .fault(am_fault));
    // ---- router selectors ----
    wire          tv_v, td_v;
    wire [KV*IW-1:0] tv_ids;
    wire [KD*IW-1:0] td_ids;
    wire          s_v;
    wire [KV*IW-1:0] s_ids;
    wire [2:0]    s_col;
    wire          s_inflight;
    generate if (XSEL != 0) begin : g_xsel
    // selections from outside (the die selector); the producer orders u_flush after the pass's last selection
    assign tv_v = x_v & ~x_draft; assign td_v = x_v & x_draft;
    assign tv_ids = x_ids; assign td_ids = x_ids[KD*IW-1:0];
    assign s_col = x_col; assign s_inflight = 1'b0;
    end else begin : g_isel
    if (FAST == 0) begin : g_sel0
    ot_gpu_router_topk #(.N(NEXP), .P(RP), .K(KV), .IW(IW)) u_tv (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & ~rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(tv_v), .out_ids(tv_ids));
    ot_gpu_router_topk #(.N(NDEXP), .P(RP), .K(KD), .IW(IW)) u_td (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(td_v), .out_ids(td_ids));
    end else begin : g_sel1
    ot_gpu_router_topk_f #(.N(NEXP), .P(RP), .K(KV), .IW(IW)) u_tv (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & ~rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(tv_v), .out_ids(tv_ids));
    ot_gpu_router_topk_f #(.N(NDEXP), .P(RP), .K(KD), .IW(IW)) u_td (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(td_v), .out_ids(td_ids));
    end
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
    assign s_col = cq[cq_r[2:0]];
    assign s_inflight = (cq_w != cq_r) || (rv_v && rv_last);
    end endgenerate
    assign t_v = tv_v | td_v;
    assign t_col = s_col;
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
    wire inflight = s_inflight;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flush_pend <= 1'b0;
        else if (u_flush) flush_pend <= 1'b1;
        else if (flush_pend && !inflight) flush_pend <= 1'b0;
    ot_dshbm_expert_union_m #(.NE(NEXP > NDEXP ? NEXP : NDEXP), .K(KV), .PM(PMAX), .IW(IW), .FAST(UNF)) u_un (
        .clk(clk), .rst_n(rst_n), .clr(u_clr), .add_v(t_v), .add_col(t_col), .add_ids(t_ids), .add_en(t_en),
        .flush(flush_pend && !inflight), .out_v(u_v), .out_ready(u_ready), .out_id(u_id), .out_mask(u_mask),
        .out_last(u_last), .busy(), .count());
endmodule
