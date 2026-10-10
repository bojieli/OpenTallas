`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Logit-row argmax epilogue of the V4.1 HBM comparator's SM (DSpark, default-off build).
//
// The SM's head matvec leaves FP32 logits in its epilogue registers (a TMEM-style
// epilogue, as a GPU's fused GEMM + reduction kernel keeps them); this block reduces a
// row to its argmax without a round trip through shared memory.  Two uses:
//   * verify targets   t_j = argmax(logits_j)                  (in_bias_en = 0);
//   * DSpark's Markov  d_{i+1} = argmax(logits_i + markov(d_i)) (in_bias_en = 1): the
//     bias row is the SM's rank-r Markov head matvec of d_i's embedding, added here
//     with the SM's FP32 RNE adder (ot_gpu_fadd: the golden's add, every zero +0).
//
// EXACT SEMANTICS (numpy.argmax on FP32): the lowest index of the maximum; -0 == +0;
// a NaN is the maximum and the FIRST NaN wins.  Key = {isnan, order(v)}, order the
// sign-flip map of the bits with -0 canonicalised to +0, so "larger key" is exactly
// numpy's ">" and a strictly-greater update keeps the earliest index.
//
// STREAM.  LP lanes a beat: lane j carries index b*LP + j on beat b (in_mask clears
// lanes past the row end).  Each lane keeps its running best (key, index) with a
// strictly-greater update; on the last beat the LP bests reduce through a registered
// log2(LP)-level tree (larger key, then lower index).  Latency from the last beat:
// FLAT (adder or the matching delay) + 1 (lane update) + log2(LP) + 1.
// A row may start on the beat after the previous row's last beat.
// ---------------------------------------------------------------------------
module ot_dshbm_argmax_m #(
    parameter integer LP   = 8,       // lanes a beat (power of two)
    parameter integer IW   = 17,      // index width (vocabulary)
    parameter integer FLAT = 7,       // ot_gpu_fadd latency (the 1.2 GHz SS depth)
    parameter integer FAST = 0        // 1: 1.2 GHz SS successor: the beat's keys / mask / index / NaN flags are
                                      //    registered before the lane update, and the fault flag is registered:
                                      //    every output one cycle later, values unchanged
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            in_v,
    input  wire            in_last,
    input  wire            in_bias_en,
    input  wire [LP-1:0]   in_mask,
    input  wire [LP*32-1:0] in_vals,
    input  wire [LP*32-1:0] in_bias,
    output reg             out_v,
    output reg  [IW-1:0]   out_idx,
    output reg             out_nan,     // the row held a NaN (numpy semantics kept; reported)
    output wire            fault        // an adder fault (overflow to infinity / invalid) on a biased row
                                        // (FAST = 1: one cycle later, with the other outputs)
);
    localparam integer LL = (LP > 1) ? $clog2(LP) : 1;
    // ---- stage A: the bias add (or the matching delay) ----
    wire [LP*32-1:0] sum;
    wire [LP-1:0]    fl;
    genvar g;
    generate
        for (g = 0; g < LP; g = g + 1) begin : g_add
            ot_gpu_fadd #(.LAT(FLAT)) u_add (.clk(clk), .rst_n(rst_n), .v(in_v & in_bias_en & in_mask[g]),
                .a(in_vals[32*g +: 32]), .b(in_bias[32*g +: 32]), .y(sum[32*g +: 32]), .fault(fl[g]));
        end
    endgenerate
    generate if (FAST == 0) begin : g_f0
        assign fault = |fl;
    end else begin : g_f1
        reg fault_r;
        always @(posedge clk or negedge rst_n) if (!rst_n) fault_r <= 1'b0; else fault_r <= |fl;
        assign fault = fault_r;
    end endgenerate
    // delay line for the raw values, the control and the beat's base index
    reg [LP*32-1:0] dval [0:FLAT-1];
    reg [FLAT-1:0]  dv, dl, db;
    reg [LP-1:0]    dm [0:FLAT-1];
    reg [IW-1:0]    di [0:FLAT-1];
    reg [IW-1:0]    base;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dv <= 0; dl <= 0; db <= 0; base <= 0;
        end else begin
            dv <= {dv[FLAT-2:0], in_v};
            dl <= {dl[FLAT-2:0], in_v & in_last};
            db <= {db[FLAT-2:0], in_bias_en};
            if (in_v) base <= in_last ? {IW{1'b0}} : base + LP;
        end
    end
    always @(posedge clk) begin
        dval[0] <= in_vals; dm[0] <= in_mask; di[0] <= base;
        for (k = 1; k < FLAT; k = k + 1) begin
            dval[k] <= dval[k-1]; dm[k] <= dm[k-1]; di[k] <= di[k-1];
        end
    end
    wire          a_v    = dv[FLAT-1];
    wire          a_last = dl[FLAT-1];
    wire [LP*32-1:0] a_val = db[FLAT-1] ? sum : dval[FLAT-1];
    // ---- stage B: per-lane running best ----
    function automatic [32:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) okey = {1'b1, 32'hFFFF_FFFF};
            else begin
                c = (x == 32'h8000_0000) ? 32'd0 : x;
                okey = {1'b0, c[31] ? ~c : (c | 32'h8000_0000)};
            end
        end
    endfunction
    // the beat as the lane update sees it: combinational (FAST = 0) or registered (FAST = 1)
    reg [32:0]   e_key [0:LP-1];
    reg [LP-1:0] e_m, e_nan;
    reg [IW-1:0] e_base;
    reg          e_v, e_last;
    integer q;
    generate if (FAST == 0) begin : g_e0
        always @(*) begin
            e_v = a_v; e_last = a_last; e_m = dm[FLAT-1]; e_base = di[FLAT-1];
            e_nan = nanbeat(a_val, dm[FLAT-1]);
            for (q = 0; q < LP; q = q + 1) e_key[q] = okey(a_val[32*q +: 32]);
        end
    end else begin : g_e1
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin e_v <= 1'b0; e_last <= 1'b0; end
            else begin e_v <= a_v; e_last <= a_last; end
        always @(posedge clk) begin
            e_m <= dm[FLAT-1]; e_base <= di[FLAT-1];
            e_nan <= nanbeat(a_val, dm[FLAT-1]);
            for (q = 0; q < LP; q = q + 1) e_key[q] <= okey(a_val[32*q +: 32]);
        end
    end endgenerate
    reg [32:0]   bk [0:LP-1];
    reg [IW-1:0] bi [0:LP-1];
    reg [LP-1:0] bvalid;
    reg          fin;
    reg          nan_row, nan_acc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bvalid <= 0; fin <= 1'b0; nan_acc <= 1'b0; nan_row <= 1'b0;
        end else begin
            fin <= e_v & e_last;
            if (e_v) begin
                for (k = 0; k < LP; k = k + 1) begin
                    if (e_m[k] && (!bvalid[k] || e_key[k] > bk[k])) begin
                        bk[k] <= e_key[k]; bi[k] <= e_base + k;
                    end
                end
                // a new row starts on the beat after a last beat: lanes restart
                for (k = 0; k < LP; k = k + 1)
                    if (e_m[k]) bvalid[k] <= ~e_last;
                    else if (e_last) bvalid[k] <= 1'b0;
                nan_acc <= e_last ? 1'b0 : (nan_acc | (|e_nan));
                nan_row <= nan_acc | (|e_nan);
            end
        end
    end
    function automatic [LP-1:0] nanbeat(input [LP*32-1:0] v, input [LP-1:0] m);
        integer q;
        begin
            for (q = 0; q < LP; q = q + 1)
                nanbeat[q] = m[q] && v[32*q+30 -: 8] == 8'hFF && v[32*q +: 23] != 0;
        end
    endfunction
    // capture: the cycle after the last beat, bk/bi hold the row's final lane bests
    reg [LL:0]   tv;
    reg [32:0]   tk [0:LL][0:LP-1];
    reg [IW-1:0] ti [0:LL][0:LP-1];
    reg          tvl [0:LL][0:LP-1];
    reg          tnan [0:LL];
    integer lv, e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tv <= 0; out_v <= 1'b0;
        end else begin
            tv <= {tv[LL-1:0], fin};
            out_v <= tv[LL];
        end
    end
    // level 0 = the lane bests; level l+1 = pairwise winners of level l
    always @(posedge clk) begin
        if (fin) begin
            for (e = 0; e < LP; e = e + 1) begin
                tk[0][e] <= bk[e]; ti[0][e] <= bi[e]; tvl[0][e] <= seen[e];
            end
            tnan[0] <= nan_row;
        end
        for (lv = 0; lv < LL; lv = lv + 1) begin
            for (e = 0; e < (LP >> (lv + 1)); e = e + 1) begin
                if (!tvl[lv][2*e+1] || (tvl[lv][2*e] && (tk[lv][2*e] > tk[lv][2*e+1] ||
                    (tk[lv][2*e] == tk[lv][2*e+1] && ti[lv][2*e] < ti[lv][2*e+1])))) begin
                    tk[lv+1][e] <= tk[lv][2*e]; ti[lv+1][e] <= ti[lv][2*e]; tvl[lv+1][e] <= tvl[lv][2*e];
                end else begin
                    tk[lv+1][e] <= tk[lv][2*e+1]; ti[lv+1][e] <= ti[lv][2*e+1]; tvl[lv+1][e] <= tvl[lv][2*e+1];
                end
            end
            tnan[lv+1] <= tnan[lv];
        end
        out_idx <= ti[LL][0];
        out_nan <= tnan[LL];
    end
    // lanes that saw at least one valid value in the row (a lane can be empty on a short row)
    reg [LP-1:0] seen;
    reg          fresh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin seen <= 0; fresh <= 1'b1; end
        else if (e_v) begin
            seen  <= fresh ? e_m : (seen | e_m);
            fresh <= e_last;
        end
    end
endmodule
