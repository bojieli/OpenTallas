`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09: KV-die sequencer (die master qkv_seq).  The KV die's end of every per-layer and per-token crossing
// of results/arch/qwen_kv_die_20261009/CONTRACT.md, between the D2D adapter (ot_qkvd_d2d, KV side: RX classes
// CTL / Q / KVN / EMBQ, TX classes RES / EMBD / HCTL) and the KV-die blocks:
//   * the near-HBM attention (ot_qwen_nearhbm_attn_stack_p x 4 + ot_qwen_nearhbm_attn_hub_p): start, T, q beats in;
//     the hub's 64 result beats out to RES (no ready on the hub: a RES credit must be in hand, else a sticky fault);
//   * the new position's K / V rows crossed on KVN are posted on kvw_* to the four KV landings, whose KV merges
//     (ot_qkvd_kv_merge, one slice per row engine) replace the t = T-1 row reads with them and whose HBM write queues
//     store them (credit flow);
//   * the embedding fetch: EMBQ words -> the embedding gateway (emb_req_*), gateway row words -> EMBD;
//   * the host: host-control words (hc_*) -> HCTL; non-ATTN CTL words (token out, CSR responses) -> tok_*.
// Every port is registered at the boundary; every producer->consumer hop is credit flow (no same-cycle ready).
// Word = {tag 16, data 512}.  CTL tag[15:12] op: 1 ATTN {data[13:0] T, [21:16] layer, [63:32] kv base}, 2 TOKEN,
// 3 CSR_RSP.  Q tag[5:0] beat (32 BF16).  KVN tag[2:0] {v, g, half} (64 FP8 E4M3).  RES tag {g, beat[5:0]} (16 FP32).
// MUT (bench only): 2 = Q beats 0 / 1 swapped.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_seq #(
    parameter integer HD  = 128,
    parameter integer R   = 8,                 // row engines per stack
    parameter integer W   = 528,
    parameter integer QD  = 48,                // CTL/Q/KVN/EMBQ input buffers (= credits given to the adapter RX face)
    parameter integer CD  = 4,
    parameter integer KD  = 8,
    parameter integer ED  = 4,
    parameter integer UC0 = 40,                // adapter TX-face credits: RES, EMBD, HCTL (= adapter IBD)
    parameter integer UC1 = 40,
    parameter integer UC2 = 4,
    parameter integer KWC = 4,                 // KV write queue credits
    parameter integer GWC = 4,                 // embedding gateway request credits
    parameter integer GWD = 8,                 // embedding row words buffered from the gateway
    parameter integer HCD = 4,
    parameter integer TKC = 4,                 // host token / CSR-response credits
    parameter integer MUT = 0,
    parameter integer E   = 4 * R
) (
    input  wire              clk,
    input  wire              rst_n,
    // D2D adapter, RX classes (CTL, Q, KVN, EMBQ)
    input  wire [3:0]        c_v,
    input  wire [4*W-1:0]    c_d,
    output reg  [3:0]        c_cr,
    // D2D adapter, TX classes (RES, EMBD, HCTL)
    output wire [2:0]        u_v,
    output wire [3*W-1:0]    u_d,
    input  wire [2:0]        u_cr,
    // near-HBM attention
    output reg               a_start,
    output reg  [13:0]       a_T,
    output reg               a_q_valid,
    output reg  [5:0]        a_q_beat,
    output reg  [511:0]      a_q_data,
    input  wire              a_out_valid,
    input  wire              a_out_g,
    input  wire [5:0]        a_out_beat,
    input  wire [511:0]      a_out_data,
    input  wire              a_hub_fault,      // attention hub fault
    input  wire [3:0]        a_stk_fault,      // stack aggregator faults
    input  wire [3:0]        m_fault,          // KV merge faults (one per landing)
    // KV write (posted to the four landings: their KV merges keep the rows, the HBM write queue stores them)
    output reg               kvw_v,
    output reg  [1:0]        kvw_vg,
    output reg  [13:0]       kvw_t,
    output reg  [5:0]        kvw_layer,
    output reg  [HD*8-1:0]   kvw_d,
    input  wire              kvw_cr,
    // embedding gateway
    output wire              emb_req_v,
    output wire [W-1:0]      emb_req_d,
    input  wire              emb_req_cr,
    input  wire              emb_q_v,
    input  wire [W-1:0]      emb_q_d,
    output wire              emb_q_cr,
    // host interface
    input  wire              hc_v,
    input  wire [W-1:0]      hc_d,
    output wire              hc_cr,
    output wire              tok_v,
    output wire [W-1:0]      tok_d,
    input  wire              tok_cr,
    output reg               fault,
    output reg  [7:0]        fault_cause
);
    // ---- boundary capture of the adapter RX face and the attention / row ports ----
    reg  [3:0]     cv;
    reg  [4*W-1:0] cd;
    reg  [2:0]     ucq;
    reg            ov, og, kwq;
    reg  [5:0]     ob;
    reg  [511:0]   od;
    always @(posedge clk) begin cd <= c_d; ob <= a_out_beat; od <= a_out_data; og <= a_out_g; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 0; ucq <= 0; ov <= 1'b0; kwq <= 1'b0; end
        else begin cv <= c_v; ucq <= u_cr; ov <= a_out_valid; kwq <= kvw_cr; end
    // ---- input buffers (the adapter's die-RX credits) ----
    wire [3:0]     ib_empty, ib_full;
    wire [4*W-1:0] ib_head;
    reg  [3:0]     ib_pop;
    ot_qkvd_fifo #(.W(W), .D(CD)) u_ctl (.clk(clk), .rst_n(rst_n), .push(cv[0]), .din(cd[0*W +: W]), .pop(ib_pop[0]),
        .dout(ib_head[0*W +: W]), .empty(ib_empty[0]), .full(ib_full[0]), .count());
    ot_qkvd_fifo #(.W(W), .D(QD)) u_q (.clk(clk), .rst_n(rst_n), .push(cv[1]), .din(cd[1*W +: W]), .pop(ib_pop[1]),
        .dout(ib_head[1*W +: W]), .empty(ib_empty[1]), .full(ib_full[1]), .count());
    ot_qkvd_fifo #(.W(W), .D(KD)) u_kvn (.clk(clk), .rst_n(rst_n), .push(cv[2]), .din(cd[2*W +: W]), .pop(ib_pop[2]),
        .dout(ib_head[2*W +: W]), .empty(ib_empty[2]), .full(ib_full[2]), .count());
    // EMBQ: straight to the gateway through a credit bridge (its buffer is the adapter's EMBQ credit)
    wire eq_cr, eq_f, ed_f, hc_f, tk_f, tk_icr;
    ot_qkvd_cbridge #(.W(W), .D(ED), .OC(GWC)) u_eq (.clk(clk), .rst_n(rst_n), .in_v(c_v[3]), .in_d(c_d[3*W +: W]),
        .in_cr(eq_cr), .out_v(emb_req_v), .out_d(emb_req_d), .out_cr(emb_req_cr), .fault(eq_f));
    // ---- TX classes: RES (direct, credit-checked), EMBD and HCTL (credit bridges) ----
    reg  [7:0]  uc0;
    reg         rs_v;
    reg [W-1:0] rs_d;
    assign u_v[0] = rs_v;
    assign u_d[0 +: W] = rs_d;
    ot_qkvd_cbridge #(.W(W), .D(GWD), .OC(UC1)) u_ed (.clk(clk), .rst_n(rst_n), .in_v(emb_q_v), .in_d(emb_q_d),
        .in_cr(emb_q_cr), .out_v(u_v[1]), .out_d(u_d[W +: W]), .out_cr(u_cr[1]), .fault(ed_f));
    ot_qkvd_cbridge #(.W(W), .D(HCD), .OC(UC2)) u_hc (.clk(clk), .rst_n(rst_n), .in_v(hc_v), .in_d(hc_d),
        .in_cr(hc_cr), .out_v(u_v[2]), .out_d(u_d[2*W +: W]), .out_cr(u_cr[2]), .fault(hc_f));
    // non-ATTN CTL words -> host (token out / CSR responses)
    reg          tk_in_v;
    reg  [W-1:0] tk_in_d;
    ot_qkvd_cbridge #(.W(W), .D(4), .OC(TKC)) u_tk (.clk(clk), .rst_n(rst_n), .in_v(tk_in_v), .in_d(tk_in_d),
        .in_cr(tk_icr), .out_v(tok_v), .out_d(tok_d), .out_cr(tok_cr), .fault(tk_f));
    reg  [2:0]  tk_c;                       // tok bridge buffer credits
    // ---- layer state ----
    localparam [2:0] S_IDLE = 3'd0, S_KV = 3'd1, S_ST = 3'd2, S_Q = 3'd3, S_RUN = 3'd4;
    reg [2:0]   st;
    reg [5:0]   layer;
    reg [3:0]   kv_n;
    reg [5:0]   q_n;
    reg [6:0]   r_n;
    reg [511:0] kvn [0:7];                  // {v, g, half}
    reg [2:0]   kw_n;                       // KV rows posted
    reg [7:0]   kwc;
    reg         kw_go;
    reg f_res, f_ord, f_row, f_pend, f_kw, f_ib;
    wire [W-1:0] ctl_w = ib_head[0*W +: W];
    wire [W-1:0] q_w   = ib_head[1*W +: W];
    wire [W-1:0] kv_w  = ib_head[2*W +: W];
    always @* begin
        ib_pop = 4'd0;
        if (!ib_empty[0] && ((st == S_IDLE && ctl_w[527:524] == 4'd1) || (ctl_w[527:524] != 4'd1 && tk_c != 0)))
            ib_pop[0] = 1'b1;
        if (st == S_KV && kv_n < 4'd8 && !ib_empty[2]) ib_pop[2] = 1'b1;
        if (st == S_Q && !ib_empty[1]) ib_pop[1] = 1'b1;
    end
    always @(posedge clk) begin
        if (ib_pop[2]) kvn[kv_w[514:512]] <= kv_w[511:0];
        tk_in_d <= ctl_w;
        if (ib_pop[1]) begin
            a_q_beat <= (MUT == 2 && q_w[517:512] < 6'd2) ? (q_w[517:512] ^ 6'd1) : q_w[517:512];
            a_q_data <= q_w[511:0];
        end
        if (ov) rs_d <= {9'd0, og, ob, od};
        if (kw_go) begin
            kvw_vg <= kw_n[1:0];
            kvw_d  <= {kvn[{kw_n[1:0], 1'b1}], kvn[{kw_n[1:0], 1'b0}]};
            kvw_t  <= a_T - 1'b1;
            kvw_layer <= layer;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; layer <= 0; kv_n <= 0; q_n <= 0; r_n <= 0; a_start <= 1'b0; a_T <= 14'd0; a_q_valid <= 1'b0;
            c_cr <= 4'd0; uc0 <= 8'(UC0); rs_v <= 1'b0; tk_in_v <= 1'b0; tk_c <= 3'd4;
            kw_n <= 3'd4; kwc <= 8'(KWC); kw_go <= 1'b0; kvw_v <= 1'b0;
            f_res <= 1'b0; f_ord <= 1'b0; f_kw <= 1'b0; f_ib <= 1'b0; f_row <= 1'b0; f_pend <= 1'b0; fault <= 1'b0; fault_cause <= 8'd0;
        end else begin
            c_cr <= {eq_cr, ib_pop[2:0]};
            a_start <= 1'b0;
            a_q_valid <= ib_pop[1];
            tk_in_v <= ib_pop[0] && ctl_w[527:524] != 4'd1;
            tk_c <= tk_c - ((ib_pop[0] && ctl_w[527:524] != 4'd1) ? 3'd1 : 3'd0) + (tk_icr ? 3'd1 : 3'd0);
            case (st)
                S_IDLE: if (ib_pop[0] && ctl_w[527:524] == 4'd1) begin
                    a_T <= ctl_w[13:0]; layer <= ctl_w[21:16]; kv_n <= 0; q_n <= 0; r_n <= 0; st <= S_KV;
                end
                S_KV: begin
                    if (ib_pop[2]) kv_n <= kv_n + 1'b1;
                    if (kv_n == 4'd8) begin st <= S_ST; a_start <= 1'b1; kw_n <= 3'd0; end
                end
                S_ST: st <= S_Q;           // start leads the first q beat by one cycle (the stack's contract)
                S_Q: begin
                    if (ib_pop[1]) begin
                        if (q_w[517:512] != q_n) f_ord <= 1'b1;
                        q_n <= q_n + 1'b1;
                        if (q_n == 6'd31) st <= S_RUN;
                    end
                end
                S_RUN: if (ov && r_n == 7'd63) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
            if (ov) r_n <= r_n + 1'b1;
            // RES: the hub has no ready, so a credit must be in hand
            rs_v <= ov;
            if (ov && uc0 == 0) f_res <= 1'b1;
            uc0 <= uc0 - (ov ? 8'd1 : 8'd0) + (ucq[0] ? 8'd1 : 8'd0);
            // KV write: post the four rows of the new position, one per credit
            kw_go <= (kw_n < 3'd4) && (kwc != 0) && !kw_go;
            if (kw_go) kw_n <= kw_n + 1'b1;
            kvw_v <= kw_go;
            kwc <= kwc - (kw_go ? 8'd1 : 8'd0) + (kwq ? 8'd1 : 8'd0);
            if (|(ib_full[2:0] & cv[2:0] & ~ib_pop[2:0])) f_ib <= 1'b1;
            if (kwq && kwc == 8'(KWC)) f_kw <= 1'b1;
            fault_cause <= {tk_f, hc_f, ed_f, eq_f, f_kw | f_row | f_pend, f_ord, f_res, f_ib};
            f_row <= f_row | |m_fault; f_pend <= f_pend | a_hub_fault | |a_stk_fault;
            fault <= |{tk_f, hc_f, ed_f, eq_f, f_kw, f_row, f_pend, f_ord, f_res, f_ib};
        end
    end
endmodule
