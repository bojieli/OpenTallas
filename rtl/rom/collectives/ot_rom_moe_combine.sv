`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MoE COMBINE engine of the DeepSeek-V4.1 ROM array: the golden's exact sum,
// whatever order the expert results arrive in.
//
// tools/hdc_golden_v41.Model.moe computes, per output element,
//
//     y = +0;  for id in sorted(chosen): y = add(y, expert_id(x, wgt_id))
//     y = add(y, shared(x));  out = to_bf16(y)
//
// with binary32 adds (RNE, gradual underflow, every zero result +0) on the
// BF16 expert outputs.  Binary32 addition is not associative, so the order is
// part of the result, and across a fabric the results come back in any order
// (hop counts, back-pressure, expert latency).  This engine therefore BUFFERS
// AND REORDERS: every RETURN record names its token slot (tag) and its rank --
// the expert's position in ascending-id order, stamped by
// ot_rom_moe_dispatch; the shared expert is rank NRANK-1 -- and lands in slot
// (tag, rank).  An in-order walker then adds rank 0, 1, ..., NRANK-1 of a
// token, chunk by chunk, through LANES qualified binary32 adders
// (rtl/proto/ot_fp32_add_rne_pipe.sv), starting from +0 exactly as the golden
// does, and rounds the final sum to BF16 by the golden's to_bf16 rule.  The
// result is bit-identical to the golden for every arrival order; nothing is
// ever added out of order.
//
// Pipelining.  Input: one flit per cycle, always accepted (in_ready = 1): the
// home package re-issues a tag only after this engine frees it (tag_free), so
// a slot can never be overwritten.  A chunk may be added as soon as its own
// flit has landed (cut-through: the walker does not wait for a whole vector).
// The walker issues one chunk per cycle.  A chunk of rank r+1 needs rank r's
// sum of the same chunk; two bypasses (the adder output straight back into
// the adder input, and a write-through on the partial-sum read) make that
// sum usable ADD_LAT cycles after issue, so when a vector has at least
// ADD_LAT flits the walker runs a token's ranks back to back with no bubble
// (it finishes one token before it starts another, which keeps per-token
// latency low); shorter vectors fall back to interleaving other tokens'
// ranks round-robin, and a lone token then waits COOL cycles per rank.
// No per-message handshake: a RETURN header is parsed by a flit counter and
// costs its own input cycle only.
//
// ONE-SHOT FIXED-ORDER ALL-REDUCE (IN_W = 32).  The same engine is the
// tensor group's all-reduce of results/roofline/critical_path (four dies of a
// package, "one_shot: every die sums all partials in rank order"): each die
// multicasts its binary32 partial vector as a RETURN record with rank = its
// die index; every die's combine sums ranks 0..NRANK-1 from +0 in that fixed
// order, so all replicas are bit-identical whatever the arrival order.
//
// The output is not back-pressured: one BF16 chunk per cycle when valid,
// out_last on the token's final chunk, together with tag_free.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module ot_rom_moe_combine
#(
    parameter integer FLIT_W    = 512,
    parameter integer TAGS      = 4,              // token slots (power of two)
    parameter integer NRANK     = 7,              // 6 routed + the shared expert
    parameter integer VEC_FLITS = 5,              // flits per expert output vector
    parameter integer ADD_LAT   = 5,              // ot_fp32_add_rne_pipe latency
    // 16: RETURN payloads are BF16 expert outputs (the MoE combine);
    // 32: they are binary32 partial sums (the tensor group's one-shot fixed-order all-reduce)
    parameter integer IN_W      = 16,
    parameter integer OUT_BF16  = 1               // 1: the sum leaves rounded to BF16; 0: binary32
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   in_valid,
    output wire                   in_ready,
    input  wire [FLIT_W-1:0]      in_data,
    input  wire                   in_last,
    output reg                    out_valid,
    output reg  [7:0]             out_tag,
    output reg  [7:0]             out_chunk,
    output reg  [FLIT_W-1:0]      out_data,       // LANES results, BF16 in the low half or binary32
    output reg                    out_last,
    output reg                    tag_free_valid,
    output reg  [7:0]             tag_free,
    output reg  [31:0]            results_in,
    output reg  [31:0]            chunks_issued,
    output reg  [31:0]            walker_waits,   // walker holds a rank whose next flit has not landed
    output reg                    fault
);
    localparam integer LANES = FLIT_W / IN_W;
    localparam integer V     = VEC_FLITS;
    localparam integer NSLOT = TAGS * NRANK * V;
    localparam integer TW    = (TAGS > 1) ? $clog2(TAGS) : 1;
    localparam integer RW    = $clog2(NRANK + 1);
    localparam integer CW    = (V > 1) ? $clog2(V) : 1;
    localparam integer HW    = $clog2(V + 1);
    // issue -> the earliest issue of the same chunk that sees the sum (through the bypasses)
    localparam integer P     = ADD_LAT;
    // a token's next rank may follow its last one directly when the vector covers P
    localparam integer CONT  = (V >= P) ? 1 : 0;
    // otherwise the pick path already spends 3 cycles between a rank's last chunk and the next rank's first
    localparam integer COOL  = (P - V - 2 > 0) ? (P - V - 2) : 0;
    localparam integer KW    = (COOL > 0) ? $clog2(COOL + 1) : 1;

    assign in_ready = 1'b1;
    wire x_err;                                   // an adder refused (nonfinite operand or overflow)

    // -- input: register, parse by a flit counter, write the slot ----------------------------
    reg              i_v, i_last;
    reg [FLIT_W-1:0] i_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i_v <= 1'b0;
        else i_v <= in_valid;
    end
    always @(posedge clk) begin i_d <= in_data; i_last <= in_last; end

    reg [HW-1:0] hpos;                            // 0: header next
    reg          pfault;
    reg [TW-1:0] htag;
    reg [2:0]    hrank;
    reg              w_v;
    reg [$clog2(NSLOT)-1:0] w_addr;
    reg [FLIT_W-1:0] w_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hpos <= 0; htag <= 0; hrank <= 0; w_v <= 1'b0; results_in <= 32'd0; pfault <= 1'b0;
        end else begin
            w_v <= i_v && (hpos != 0);
            if (i_v) begin
                // framing: a header must be a RETURN, `last` must close the record
                if (hpos == 0 && i_d[H_KIND +: 4] != K_RETURN) pfault <= 1'b1;
                if (hpos == 0 && (i_d[H_RANK +: 3] >= NRANK || i_d[H_TAG +: 8] >= TAGS)) pfault <= 1'b1;
                if (i_last && hpos != V) pfault <= 1'b1;   // a packet ends only at a record end
                if (hpos == 0) begin
                    htag <= i_d[H_TAG +: TW]; hrank <= i_d[H_RANK +: 3]; hpos <= 1;
                    results_in <= results_in + 32'd1;
                end else begin
                    hpos <= (hpos == V) ? {HW{1'b0}} : hpos + 1'b1;
                end
            end
        end
    end
    always @(posedge clk) begin
        w_addr <= (htag * NRANK + hrank) * V + (hpos - 1);
        w_d    <= i_d;
    end

    reg [FLIT_W-1:0] slot [0:NSLOT-1];
    always @(posedge clk) if (w_v) slot[w_addr] <= w_d;

    // -- walker: in-order issue per token, round-robin across tokens ----------------------------
    reg [NSLOT-1:0] vbit;                         // flit (tag, rank, chunk) has landed
    reg [RW-1:0]    nr   [0:TAGS-1];               // next rank to add, per tag
    reg [KW-1:0]    cool [0:TAGS-1];
    reg [TAGS-1:0]  cand;                          // registered: tag may start its next rank
    reg             act;
    reg [TW-1:0]    ct;
    reg [2:0]       cr;
    reg [CW-1:0]    cc;
    reg [TW-1:0]    rr;                            // round-robin pointer
    wire [$clog2(NSLOT)-1:0] cur = (ct * NRANK + cr) * V + cc;
    wire fire = act && vbit[cur];
    wire rank_end = fire && (cc == V - 1);
    // pick: first candidate at or after rr
    reg          pick_ok;
    reg [TW-1:0] pick;
    integer k, t;
    always @* begin
        pick_ok = 1'b0; pick = {TW{1'b0}};
        for (k = TAGS - 1; k >= 0; k = k - 1) begin
            t = (rr + k) % TAGS;
            if (cand[t]) begin pick_ok = 1'b1; pick = t; end
        end
    end
    // continue with the same token's next rank when its first flit has landed
    wire cont = (CONT != 0) && rank_end && (cr != NRANK - 1) && vbit[(ct * NRANK + cr + 1) * V];
    wire take = pick_ok && (!act || (rank_end && !cont));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vbit <= {NSLOT{1'b0}}; cand <= {TAGS{1'b0}}; act <= 1'b0; ct <= 0; cr <= 0; cc <= 0; rr <= 0;
            for (k = 0; k < TAGS; k = k + 1) begin nr[k] <= 0; cool[k] <= 0; end
            chunks_issued <= 32'd0; walker_waits <= 32'd0; fault <= 1'b0;
        end else begin
            // landed flits and consumed flits
            if (w_v) begin
                if (vbit[w_addr]) fault <= 1'b1;   // a slot written twice: protocol violation
                vbit[w_addr] <= 1'b1;
            end
            if (fire) begin
                vbit[cur] <= 1'b0;
                chunks_issued <= chunks_issued + 32'd1;
            end
            if (act && !fire) walker_waits <= walker_waits + 32'd1;
            for (k = 0; k < TAGS; k = k + 1)
                if (cool[k] != 0) cool[k] <= cool[k] - 1'b1;
            if (fire) cc <= cc + 1'b1;
            if (rank_end) begin
                nr[ct] <= (cr == NRANK - 1) ? {RW{1'b0}} : nr[ct] + 1'b1;
                cool[ct] <= COOL;
                act <= cont;
                cr  <= cr + 1'b1;
                cc  <= {CW{1'b0}};
            end
            if (take) begin
                act <= 1'b1; ct <= pick; cr <= nr[pick]; cc <= 0; rr <= pick + 1'b1;
            end
            // candidates for the next pick (one cycle stale, which only delays a pick)
            for (k = 0; k < TAGS; k = k + 1)
                cand[k] <= !(act && ct == k) && !(take && pick == k) && (cool[k] == 0)
                           && vbit[(k * NRANK + nr[k]) * V];
            if (x_err || pfault) fault <= 1'b1;
        end
    end

    // -- read the slot and the partial sum ----------------------------------------------------------
    reg              x0_v;
    reg [TW-1:0]     x0_t;
    reg [2:0]        x0_r;
    reg [CW-1:0]     x0_c;
    reg              x1_v, x1_first, x1_last, x1_fwd;
    // the adder's side band (declared here: the read stage looks one stage ahead into it)
    reg          d_v     [0:ADD_LAT-1];
    reg          d_last  [0:ADD_LAT-1];
    reg [TW-1:0] d_t     [0:ADD_LAT-1];
    reg [CW-1:0] d_c     [0:ADD_LAT-1];
    wire [LANES*32-1:0] y;
    wire          y_v;
    wire [TW-1:0] y_t;
    wire [CW-1:0] y_c;
    reg [TW-1:0]     x1_t;
    reg [CW-1:0]     x1_c;
    reg [FLIT_W-1:0] x1_b;
    reg [LANES*32-1:0] x1_a;
    reg [LANES*32-1:0] acc [0:TAGS*V-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin x0_v <= 1'b0; x1_v <= 1'b0; end
        else begin x0_v <= fire; x1_v <= x0_v; end
    end
    always @(posedge clk) begin
        x0_t <= ct; x0_r <= cr; x0_c <= cc;
        x1_t <= x0_t; x1_c <= x0_c;
        x1_first <= (x0_r == 0);
        x1_last  <= (x0_r == NRANK - 1);
        x1_b <= slot[(x0_t * NRANK + x0_r) * V + x0_c];
        // write-through: the sum being written this cycle is the one this read wants
        x1_a <= (y_v && y_t == x0_t && y_c == x0_c) ? y : acc[x0_t * V + x0_c];
        // adder bypass: the sum leaving the adder next cycle is the one this operand wants
        x1_fwd <= d_v[ADD_LAT-2] && d_t[ADD_LAT-2] == x0_t && d_c[ADD_LAT-2] == x0_c;
    end

    // -- LANES binary32 adders ----------------------------------------------------------------------
    wire [LANES*2-1:0]  yerr;
    wire [LANES-1:0]    yv;
    genvar l;
    generate for (l = 0; l < LANES; l = l + 1) begin : g_lane
        wire [31:0] bw;
        if (IN_W == 32) begin : g_f32
            assign bw = x1_b[32 * l +: 32];
        end else begin : g_bf16
            assign bw = {x1_b[16 * l +: 16], 16'd0};
        end
        ot_fp32_add_rne_pipe u_add (
            .clk(clk), .rst_n(rst_n), .valid_in(x1_v),
            .a(x1_first ? 32'd0 : (x1_fwd ? y[32 * l +: 32] : x1_a[32 * l +: 32])),
            .b(bw),
            .y(y[32 * l +: 32]), .err(yerr[2 * l +: 2]), .valid_out(yv[l]));
    end endgenerate
    // the side band rides a matching delay line
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) for (k = 0; k < ADD_LAT; k = k + 1) d_v[k] <= 1'b0;
        else begin
            d_v[0] <= x1_v;
            for (k = 1; k < ADD_LAT; k = k + 1) d_v[k] <= d_v[k-1];
        end
    end
    always @(posedge clk) begin
        d_last[0] <= x1_last; d_t[0] <= x1_t; d_c[0] <= x1_c;
        for (k = 1; k < ADD_LAT; k = k + 1) begin
            d_last[k] <= d_last[k-1]; d_t[k] <= d_t[k-1]; d_c[k] <= d_c[k-1];
        end
    end
    assign        y_v    = yv[0];
    wire          y_last = d_last[ADD_LAT-1];
    assign        y_t    = d_t[ADD_LAT-1];
    assign        y_c    = d_c[ADD_LAT-1];
    assign        x_err  = y_v && (yerr != {LANES*2{1'b0}});

    // -- write back the partial sum; the last rank leaves as BF16 -------------------------------
    always @(posedge clk) if (y_v) acc[y_t * V + y_c] <= y;
    reg [FLIT_W-1:0] bf;
    reg [32:0]       rnd;
    always @* begin
        bf = {FLIT_W{1'b0}};
        for (k = 0; k < LANES; k = k + 1) begin
            // tools/hdc_golden.to_bf16: (b + 0x7FFF + ((b >> 16) & 1)) >> 16
            rnd = {1'b0, y[32 * k +: 32]} + 33'h7FFF + {32'd0, y[32 * k + 16]};
            bf[16 * k +: 16] = rnd[31:16];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0; out_last <= 1'b0; tag_free_valid <= 1'b0;
        end else begin
            out_valid <= y_v && y_last;
            out_last  <= y_v && y_last && (y_c == V - 1);
            tag_free_valid <= y_v && y_last && (y_c == V - 1);
        end
    end
    always @(posedge clk) begin
        out_tag   <= y_t;
        out_chunk <= y_c;
        out_data  <= (OUT_BF16 != 0) ? bf : y[FLIT_W-1:0];
        tag_free  <= y_t;
    end
endmodule
