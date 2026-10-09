// Additive registered external CPRESULT ownership branch.
// Additive native full-context MTP pin boundary with finite accepted-output skid.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// mtp-hbm 2026-10-08: hfd_mtp, the HBM-accelerator die block of the DSpark (V4.1 MTP) control plane.
// ot_dshbm_dspark_top (ctl + accept, spec-state rings, SM-epilogue argmax, router selectors or external
// selections, expert union) behind REGISTERED PINS (REDESIGN_RULES template D, transaction-level exactness):
//   * every plain input is captured by a flop at the pin, every plain output leaves from a flop: +1 cycle each way;
//   * the three valid/ready interfaces (engine command out, spec-state request in, union stream out) go through
//     ot_hfd_mtp_skid: in_ready / out_v / out_d from flops, +1 cycle, no beat lost or duplicated;
//   * the prompt / forced-token read ports are registered both ways: ctl PRL = 2 waits for the read.
// Same commands, tokens, selections, argmax rows and spec-state answers in the same order as the unwrapped top.
// Parameter-free route tops: physical/hbm_mtp/rtl/hfd_mtp_tops.sv.
// ---------------------------------------------------------------------------
module ot_hfd_mtp_core_cp_stop #(
    parameter integer EXTERNAL_AM=0,STOP_EN=0,CNT_W=21,POS_W=20,FORCE_W=23,
    parameter integer B      = 5,
    parameter integer PMAX   = 8,
    parameter integer TW     = 17,
    parameter integer NL     = 40,
    parameter integer NST    = 3,
    parameter integer MAXPOS = 1 << 20,
    parameter integer W      = 128,
    parameter integer WR     = 256,     // MR-7: window ring 256 slots (slot = pos[7:0])
    parameter integer SR     = 10,      // compressor slot ring: max ratio 2 + PMAX
    parameter integer TR     = 16,
    parameter integer NG     = 4,
    parameter integer NSRC   = 4,
    parameter [NSRC*4-1:0] RLOG = 16'h0111,  // MR-8: V4.1 L2 / L8 / L14 ratio 2, L20 ratio 1
    parameter integer CKMAX  = 1 << 20,     // compressed rows per source: 1M positions at ratio 1
    parameter integer AW     = 32,
    parameter integer LP     = 8,
    parameter integer FLAT   = 7,
    parameter integer NEXP   = 384,
    parameter integer KV     = 6,
    parameter integer NDEXP  = 384,
    parameter integer KD     = 6,
    parameter integer RP     = 16,
    parameter integer IW     = 9,
    parameter integer MUT    = 0,
    parameter integer FAST   = 1,
    parameter integer SPECF  = 0,
    parameter integer AMF    = 1,
    parameter integer UNF    = 1,
    parameter integer XSEL   = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               start,
    input  wire [3:0]         cfg_gamma,
    input  wire               cfg_force,
    input  wire [CNT_W-1:0]   cfg_ngen,
    input  wire [CNT_W-1:0]   cfg_plen,
    output reg  [POS_W-1:0]   p_addr,
    input  wire [TW-1:0]      p_tok,
    output reg  [FORCE_W-1:0] f_addr,
    input  wire [TW-1:0]      f_tok,
    output wire               e_v,
    output wire [TW-1:0]      e_tok,
    output wire [POS_W-1:0]   e_idx,
    input wire e_ready,cfg_eos_en,
    input wire [TW-1:0] cfg_eos,
    input wire [POS_W:0] cfg_maxpos,
    output reg [2:0] stop_status,
    output reg                done,
    output wire               cmd_v,
    input  wire               cmd_ready,
    output wire [3:0]         cmd_op,
    output wire [7:0]         cmd_idx,
    output wire [3:0]         cmd_ncol,
    output wire [31:0]        cmd_pos,
    output wire [TW-1:0]      cmd_tok1,
    output wire [PMAX*TW-1:0] cmd_toks,
    input  wire               eng_done,
    input wire cp_am_v,
    input wire [TW-1:0] cp_am_idx,
    input  wire               lg_v,
    input  wire               lg_last,
    input  wire               lg_bias_en,
    input  wire [LP-1:0]      lg_mask,
    input  wire [LP*32-1:0]   lg_vals,
    input  wire [LP*32-1:0]   lg_bias,
    output reg                am_v,
    output reg  [TW-1:0]      am_idx,
    output reg                am_fault,
    input  wire               sr_v,
    output wire               sr_ready,
    input  wire [3:0]         sr_kind,
    input  wire [15:0]        sr_idx,
    input  wire [31:0]        sr_pos,
    output reg                sa_v,
    output reg  [AW-1:0]      sa_addr,
    output reg  [TW-1:0]      sa_tok,
    output reg                sa_pad,
    output reg                sa_last,
    output reg                sa_err,
    output reg  [31:0]        n_committed,
    input  wire               rv_v,
    input  wire               rv_draft,
    input  wire [RP*32-1:0]   rv_vals,
    input  wire               rv_last,
    input  wire [2:0]         rv_col,
    input  wire               x_v,
    input  wire               x_draft,
    input  wire [KV*IW-1:0]   x_ids,
    input  wire [2:0]         x_col,
    output reg                t_v,
    output reg  [KV*IW-1:0]   t_ids,
    output reg  [2:0]         t_col,
    input  wire               u_clr,
    input  wire               u_flush,
    output wire               u_v,
    input  wire               u_ready,
    output wire [IW-1:0]      u_id,
    output wire [PMAX-1:0]    u_mask,
    output wire               u_last,
    output reg                step_v,
    output reg  [2:0]         step_a,
    output reg  [3:0]         step_g,
    output reg  [CNT_W-1:0]   steps,
    output reg  [31:0]        cyc_total,
    output reg  [31:0]        cyc_engine,
    output reg  [31:0]        cyc_markov
);
    // ---- reset: two-flop synchroniser (the die reset is asynchronous) ----
    reg [1:0] rst_s;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rn = rst_s[1];
    // ---- checked CPRESULT pin flops ----
    reg i_cp_am_v;reg [TW-1:0] i_cp_am_idx;
    always @(posedge clk or negedge rn)
      if(!rn)begin i_cp_am_v<=0;i_cp_am_idx<=0;end
      else begin i_cp_am_v<=cp_am_v;i_cp_am_idx<=cp_am_idx;end
    // ---- input pin flops ----
    reg               i_start, i_force, i_eng_done, i_lg_v, i_lg_last, i_lg_bias_en, i_rv_v, i_rv_draft, i_rv_last;
    reg               i_x_v, i_x_draft, i_u_clr, i_u_flush;
    reg [3:0]         i_gamma;
    reg [CNT_W-1:0] i_ngen, i_plen;
    reg i_eos_en;reg [TW-1:0] i_eos;reg [POS_W:0] i_maxpos;
    reg [TW-1:0]      i_p_tok, i_f_tok;
    reg [LP-1:0]      i_lg_mask;
    reg [LP*32-1:0]   i_lg_vals, i_lg_bias;
    reg [RP*32-1:0]   i_rv_vals;
    reg [2:0]         i_rv_col, i_x_col;
    reg [KV*IW-1:0]   i_x_ids;
    always @(posedge clk or negedge rn)
        if (!rn) begin
            i_start <= 1'b0; i_eng_done <= 1'b0; i_lg_v <= 1'b0; i_rv_v <= 1'b0; i_x_v <= 1'b0;
            i_u_clr <= 1'b0; i_u_flush <= 1'b0;
        end else begin
            i_start <= start; i_eng_done <= eng_done; i_lg_v <= lg_v; i_rv_v <= rv_v; i_x_v <= x_v;
            i_u_clr <= u_clr; i_u_flush <= u_flush;
        end
    always @(posedge clk) begin
        i_eos_en<=cfg_eos_en;i_eos<=cfg_eos;i_maxpos<=cfg_maxpos;
        i_force <= cfg_force; i_gamma <= cfg_gamma; i_ngen <= cfg_ngen; i_plen <= cfg_plen;
        i_p_tok <= p_tok; i_f_tok <= f_tok;
        i_lg_last <= lg_last; i_lg_bias_en <= lg_bias_en; i_lg_mask <= lg_mask; i_lg_vals <= lg_vals; i_lg_bias <= lg_bias;
        i_rv_draft <= rv_draft; i_rv_vals <= rv_vals; i_rv_last <= rv_last; i_rv_col <= rv_col;
        i_x_draft <= x_draft; i_x_ids <= x_ids; i_x_col <= x_col;
    end
    // ---- command out / request in / union out: registered valid-ready slices ----
    localparam integer CW = 4 + 8 + 4 + 32 + TW + PMAX * TW;
    wire          c_v, c_ready;
    wire [3:0]    c_op, c_ncol;
    wire [7:0]    c_idx;
    wire [31:0]   c_pos;
    wire [TW-1:0] c_tok1;
    wire [PMAX*TW-1:0] c_toks;
    ot_hfd_mtp_skid #(.W(CW)) u_cmd (.clk(clk), .rst_n(rn), .in_v(c_v), .in_ready(c_ready),
        .in_d({c_op, c_idx, c_ncol, c_pos, c_tok1, c_toks}), .out_v(cmd_v), .out_ready(cmd_ready),
        .out_d({cmd_op, cmd_idx, cmd_ncol, cmd_pos, cmd_tok1, cmd_toks}));
    localparam integer RW = 4 + 16 + 32;
    wire          r_v, r_ready;
    wire [3:0]    r_kind;
    wire [15:0]   r_idx;
    wire [31:0]   r_pos;
    ot_hfd_mtp_skid #(.W(RW)) u_req (.clk(clk), .rst_n(rn), .in_v(sr_v), .in_ready(sr_ready),
        .in_d({sr_kind, sr_idx, sr_pos}), .out_v(r_v), .out_ready(r_ready), .out_d({r_kind, r_idx, r_pos}));
    localparam integer UW = IW + PMAX + 1;
    wire          un_v, un_ready, un_last;
    wire [IW-1:0] un_id;
    wire [PMAX-1:0] un_mask;
    ot_hfd_mtp_skid #(.W(UW)) u_uni (.clk(clk), .rst_n(rn), .in_v(un_v), .in_ready(un_ready),
        .in_d({un_id, un_mask, un_last}), .out_v(u_v), .out_ready(u_ready), .out_d({u_id, u_mask, u_last}));
    // ---- the control plane ----
    wire [POS_W-1:0] w_p_addr,w_e_idx;wire [FORCE_W-1:0] w_f_addr;wire [CNT_W-1:0] w_steps;
    wire [2:0] w_stop_status;wire w_e_ready;
    reg [2:0] pending_emits;
    always @(posedge clk or negedge rn)
        if(!rn) pending_emits<=0;
        else pending_emits<=pending_emits+(w_e_v && w_e_ready)-(e_v && e_ready);
    ot_hfd_mtp_skid #(.W(TW+POS_W)) u_emit(.clk(clk),.rst_n(rn),
        .in_v(w_e_v),.in_ready(w_e_ready),.in_d({w_e_idx,w_e_tok}),
        .out_v(e_v),.out_ready(e_ready),.out_d({e_idx,e_tok}));
    wire          w_e_v, w_done, w_am_v, w_am_fault, w_sa_v, w_sa_pad, w_sa_last, w_sa_err, w_t_v, w_step_v;
    wire [TW-1:0] w_e_tok, w_am_idx, w_sa_tok;
    wire [AW-1:0] w_sa_addr;
    wire [31:0]   w_n, w_ct, w_ce, w_cm;
    wire [KV*IW-1:0] w_t_ids;
    wire [2:0]    w_t_col, w_step_a;
    wire [3:0]    w_step_g;
    ot_dshbm_dspark_top_cp_stop #(.EXTERNAL_AM(EXTERNAL_AM),.STOP_EN(STOP_EN),.CNT_W(CNT_W),.POS_W(POS_W),.FORCE_W(FORCE_W),.B(B), .PMAX(PMAX), .TW(TW), .NL(NL), .NST(NST), .MAXPOS(MAXPOS), .W(W), .WR(WR),
        .SR(SR), .TR(TR), .NG(NG), .NSRC(NSRC), .RLOG(RLOG), .CKMAX(CKMAX), .AW(AW), .LP(LP), .FLAT(FLAT),
        .NEXP(NEXP), .KV(KV), .NDEXP(NDEXP), .KD(KD), .RP(RP), .IW(IW), .MUT(MUT), .ACCEPT_LEAF(0),
        .FAST(FAST), .SPECF(SPECF), .UNF(UNF), .AMF(AMF), .PRL(2), .XSEL(XSEL)) u_top (
        .clk(clk), .rst_n(rn), .start(i_start), .cfg_gamma(i_gamma), .cfg_force(i_force), .cfg_ngen(i_ngen),
        .cfg_plen(i_plen), .p_addr(w_p_addr), .p_tok(i_p_tok), .f_addr(w_f_addr), .f_tok(i_f_tok),
        .e_v(w_e_v), .e_tok(w_e_tok), .e_idx(w_e_idx), .done(w_done),
        .e_ready(w_e_ready),.cfg_eos_en(i_eos_en),.cfg_eos(i_eos),.cfg_maxpos(i_maxpos),.stop_status(w_stop_status),
        .cmd_v(c_v), .cmd_ready(c_ready), .cmd_op(c_op), .cmd_idx(c_idx), .cmd_ncol(c_ncol), .cmd_pos(c_pos),
        .cmd_tok1(c_tok1), .cmd_toks(c_toks), .eng_done(i_eng_done),
        .cp_am_v(i_cp_am_v),.cp_am_idx(i_cp_am_idx),.lg_v(i_lg_v), .lg_last(i_lg_last), .lg_bias_en(i_lg_bias_en), .lg_mask(i_lg_mask), .lg_vals(i_lg_vals),
        .lg_bias(i_lg_bias), .am_v(w_am_v), .am_idx(w_am_idx), .am_fault(w_am_fault),
        .sr_v(r_v), .sr_ready(r_ready), .sr_kind(r_kind), .sr_idx(r_idx), .sr_pos(r_pos),
        .sa_v(w_sa_v), .sa_addr(w_sa_addr), .sa_tok(w_sa_tok), .sa_pad(w_sa_pad), .sa_last(w_sa_last),
        .sa_err(w_sa_err), .n_committed(w_n),
        .rv_v(i_rv_v), .rv_draft(i_rv_draft), .rv_vals(i_rv_vals), .rv_last(i_rv_last), .rv_col(i_rv_col),
        .x_v(i_x_v), .x_draft(i_x_draft), .x_ids(i_x_ids), .x_col(i_x_col),
        .t_v(w_t_v), .t_ids(w_t_ids), .t_col(w_t_col),
        .u_clr(i_u_clr), .u_flush(i_u_flush), .u_v(un_v), .u_ready(un_ready), .u_id(un_id), .u_mask(un_mask),
        .u_last(un_last), .step_v(w_step_v), .step_a(w_step_a), .step_g(w_step_g), .steps(w_steps),
        .cyc_total(w_ct), .cyc_engine(w_ce), .cyc_markov(w_cm));
    // ---- output pin flops ----
    always @(posedge clk or negedge rn)
        if (!rn) begin
            done <= 1'b0; stop_status<=0; am_v <= 1'b0; am_fault <= 1'b0; sa_v <= 1'b0; sa_err <= 1'b0;
            t_v <= 1'b0; step_v <= 1'b0;
        end else begin
            done <= w_done && pending_emits==0; stop_status<=w_stop_status; am_v <= w_am_v; am_fault <= w_am_fault; sa_v <= w_sa_v; sa_err <= w_sa_err;
            t_v <= w_t_v; step_v <= w_step_v;
        end
    always @(posedge clk) begin
        p_addr <= w_p_addr; f_addr <= w_f_addr; am_idx <= w_am_idx;
        sa_addr <= w_sa_addr; sa_tok <= w_sa_tok; sa_pad <= w_sa_pad; sa_last <= w_sa_last; n_committed <= w_n;
        t_ids <= w_t_ids; t_col <= w_t_col; step_a <= w_step_a; step_g <= w_step_g; steps <= w_steps;
        cyc_total <= w_ct; cyc_engine <= w_ce; cyc_markov <= w_cm;
    end
endmodule
