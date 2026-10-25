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
module ot_hgi_argmax18_value_m #(
    parameter integer OFFSET_W = 25,
    parameter integer LP   = 8,       // lanes a beat (power of two)
    parameter integer IW   = 17,      // index width (vocabulary)
    parameter integer FLAT = 7,       // ot_gpu_fadd latency (the 1.2 GHz SS depth)
    parameter integer FAST = 0,       // 1: 1.2 GHz SS successor: the beat's keys / mask / index / NaN flags are
                                      //    registered before the lane update, and the fault flag is registered:
                                      //    every output one cycle later, values unchanged
    parameter integer STRUCT = 0      // 1 (CLOCK-RESET/argmax 2026-10-25, physical structure only, every output
                                      //    bit-identical on every cycle, 0 added cycles):
                                      //    (a) the FLAT-deep raw-value / mask / index delay line is an in-place ring
                                      //        (FLAT-1 slots + one output register, one-hot slot pointer) instead of a
                                      //        FLAT-stage shift register: no zero-logic flop->flop transfer (the routed
                                      //        argmax_r2 FF hold failures were dval[k]->dval[k+1] pairs on different
                                      //        clock leaves); the pointer is replicated per 16-bit field group;
                                      //    (b) the row-end flag fin (673 loads: level-0 capture enables of every lane)
                                      //        and the per-lane bvalid (lane 5: 135 loads, 441 ps slew) are replicated
                                      //        as kept registers per field group, each copy loading <= ~50 pins.
                                      //    Replicas take the master's next state with the master's reset:
                                      //    copy(t) == master(t) for all t.
) (
    input  wire            clk,
    input  wire            rst_n,
    input wire [OFFSET_W-1:0] global_offset,
    output reg out_range_fault,
    input  wire            in_v,
    input  wire            in_last,
    input  wire            in_bias_en,
    input  wire [LP-1:0]   in_mask,
    input  wire [LP*32-1:0] in_vals,
    input  wire [LP*32-1:0] in_bias,
    output reg             out_v,
    output reg  [IW-1:0]   out_idx,
    output reg             out_nan,     // the row held a NaN (numpy semantics kept; reported)
    output reg [31:0]       out_value,
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
    // delayed raw beat as stage B sees it (in_* FLAT edges ago)
    wire [LP*32-1:0] dl_val;
    wire [LP-1:0]    dl_m;
    wire [IW-1:0]    dl_i;
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
    generate if (STRUCT == 0) begin : g_dshift
        always @(posedge clk) begin
            dval[0] <= in_vals; dm[0] <= in_mask; di[0] <= base;
            for (k = 1; k < FLAT; k = k + 1) begin
                dval[k] <= dval[k-1]; dm[k] <= dm[k-1]; di[k] <= di[k-1];
            end
        end
        assign dl_val = dval[FLAT-1]; assign dl_m = dm[FLAT-1]; assign dl_i = di[FLAT-1];
    end else begin : g_dring
        // ring: slot s is written when ptr[s]; the output register reads the same slot on the same edge (its value
        // was written FLAT-1 edges earlier), so dl_* (t) == in_* (t - FLAT), as the shift register.
        // field groups: 2 per lane (16 value bits each; the lane's mask bit rides with the low half) + 1 for base.
        localparam integer NS = FLAT - 1;
        localparam integer NG = 2 * LP + 1;
        wire [NS-1:0] ptr [0:NG-1];
        genvar gp;
        for (gp = 0; gp < NG; gp = gp + 1) begin : g_ptr
            ot_hgi_argmax18_ring_ptr #(.N(NS)) u_ptr (.clk(clk), .rst_n(rst_n), .q(ptr[gp]));
        end
        for (gp = 0; gp < 2 * LP; gp = gp + 1) begin : g_rv
            localparam integer FW = (gp % 2 == 0) ? 17 : 16;     // low half carries the lane's mask bit
            wire [FW-1:0] din = (gp % 2 == 0) ? {in_mask[gp/2], in_vals[16*gp +: 16]} : in_vals[16*gp +: 16];
            reg  [FW-1:0] slot [0:NS-1];
            reg  [FW-1:0] dout;
            reg  [FW-1:0] rd;
            integer s;
            always @(*) begin
                rd = {FW{1'b0}};
                for (s = 0; s < NS; s = s + 1) rd = rd | ({FW{ptr[gp][s]}} & slot[s]);
            end
            always @(posedge clk) begin
                for (s = 0; s < NS; s = s + 1) if (ptr[gp][s]) slot[s] <= din;
                dout <= rd;
            end
            assign dl_val[16*gp +: 16] = dout[15:0];
            if (gp % 2 == 0) begin : g_m
                assign dl_m[gp/2] = dout[16];
            end
        end
        begin : g_ri
            reg [IW-1:0] slot [0:NS-1];
            reg [IW-1:0] dout;
            reg [IW-1:0] rd;
            integer s;
            always @(*) begin
                rd = {IW{1'b0}};
                for (s = 0; s < NS; s = s + 1) rd = rd | ({IW{ptr[NG-1][s]}} & slot[s]);
            end
            always @(posedge clk) begin
                for (s = 0; s < NS; s = s + 1) if (ptr[NG-1][s]) slot[s] <= base;
                dout <= rd;
            end
            assign dl_i = dout;
        end
    end endgenerate
    wire          a_v    = dv[FLAT-1];
    wire          a_last = dl[FLAT-1];
    wire [LP*32-1:0] a_val = db[FLAT-1] ? sum : dl_val;
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
    reg [31:0] e_bits [0:LP-1];
    reg [LP-1:0] e_m, e_nan;
    reg [IW-1:0] e_base;
    reg          e_v, e_last;
    integer q;
    generate if (FAST == 0) begin : g_e0
        always @(*) begin
            e_v = a_v; e_last = a_last; e_m = dl_m; e_base = dl_i;
            e_nan = nanbeat(a_val, dl_m);
            for (q = 0; q < LP; q = q + 1) begin e_key[q] = okey(a_val[32*q +: 32]); e_bits[q] = a_val[32*q +: 32]; end
        end
    end else begin : g_e1
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin e_v <= 1'b0; e_last <= 1'b0; end
            else begin e_v <= a_v; e_last <= a_last; end
        always @(posedge clk) begin
            e_m <= dl_m; e_base <= dl_i;
            e_nan <= nanbeat(a_val, dl_m);
            for (q = 0; q < LP; q = q + 1) begin e_key[q] <= okey(a_val[32*q +: 32]); e_bits[q] <= a_val[32*q +: 32]; end
        end
    end endgenerate
    reg [32:0]   bk [0:LP-1];
    reg [31:0] bv_bits [0:LP-1];
    reg [IW-1:0] bi [0:LP-1];
    reg [LP-1:0] bvalid;
    reg          fin;
    // bvalid as the lane update reads it: the register itself (STRUCT 0) or kept per-group replicas (STRUCT 1)
    wire [LP-1:0] bv_k, bv_i;                 // key group (bk) / index+bits group (bi, bv_bits)
    wire [LP-1:0] bvalid_d;                   // bvalid next state (exactly the always-block update below)
    wire          fin_d = e_v & e_last;
    wire [2*LP-1:0] fin_c;                    // fin as the level-0 capture of lane e reads it: [2e] bits, [2e+1] key/idx/valid
    genvar gr;
    for (gr = 0; gr < LP; gr = gr + 1) begin : g_bvd
        assign bvalid_d[gr] = !e_v ? bvalid[gr] : e_m[gr] ? ~e_last : e_last ? 1'b0 : bvalid[gr];
    end
    generate if (STRUCT == 0) begin : g_nrep
        assign bv_k = bvalid; assign bv_i = bvalid; assign fin_c = {(2*LP){fin}};
    end else begin : g_rep
        for (gr = 0; gr < LP; gr = gr + 1) begin : g_l
            ot_hgi_argmax18_rep_reg u_bvk (.clk(clk), .rst_n(rst_n), .d(bvalid_d[gr]), .q(bv_k[gr]));
            ot_hgi_argmax18_rep_reg u_bvi (.clk(clk), .rst_n(rst_n), .d(bvalid_d[gr]), .q(bv_i[gr]));
            ot_hgi_argmax18_rep_reg u_fb  (.clk(clk), .rst_n(rst_n), .d(fin_d), .q(fin_c[2*gr]));
            ot_hgi_argmax18_rep_reg u_fk  (.clk(clk), .rst_n(rst_n), .d(fin_d), .q(fin_c[2*gr+1]));
        end
    end endgenerate
    reg          nan_row, nan_acc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bvalid <= 0; fin <= 1'b0; nan_acc <= 1'b0; nan_row <= 1'b0;
        end else begin
            fin <= e_v & e_last;
            if (e_v) begin
                for (k = 0; k < LP; k = k + 1) begin
                    if (e_m[k] && (!bv_k[k] || e_key[k] > bk[k])) bk[k] <= e_key[k];
                    if (e_m[k] && (!bv_i[k] || e_key[k] > bk[k])) begin
                        bi[k] <= e_base + k; bv_bits[k] <= e_bits[k];
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
    reg [31:0] tbits [0:LL][0:LP-1];
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
        for (e = 0; e < LP; e = e + 1) begin
            if (fin_c[2*e]) tbits[0][e] <= bv_bits[e];
            if (fin_c[2*e+1]) begin tk[0][e] <= bk[e]; ti[0][e] <= bi[e]; tvl[0][e] <= seen[e]; end
        end
        if (fin) tnan[0] <= nan_row;
        for (lv = 0; lv < LL; lv = lv + 1) begin
            for (e = 0; e < (LP >> (lv + 1)); e = e + 1) begin
                if (!tvl[lv][2*e+1] || (tvl[lv][2*e] && (tk[lv][2*e] > tk[lv][2*e+1] ||
                    (tk[lv][2*e] == tk[lv][2*e+1] && ti[lv][2*e] < ti[lv][2*e+1])))) begin
                    tbits[lv+1][e] <= tbits[lv][2*e]; tk[lv+1][e] <= tk[lv][2*e]; ti[lv+1][e] <= ti[lv][2*e]; tvl[lv+1][e] <= tvl[lv][2*e];
                end else begin
                    tbits[lv+1][e] <= tbits[lv][2*e+1]; tk[lv+1][e] <= tk[lv][2*e+1]; ti[lv+1][e] <= ti[lv][2*e+1]; tvl[lv+1][e] <= tvl[lv][2*e+1];
                end
            end
            tnan[lv+1] <= tnan[lv];
        end
        out_value <= tbits[LL][0]; out_idx <= (OFFSET_W+1)'(ti[LL][0])+{1'b0,global_offset};
        out_range_fault <= (((OFFSET_W+1)'(ti[LL][0])+{1'b0,global_offset}) >= 26'd262144);
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

// STRUCT = 1 helpers (CLOCK-RESET/argmax 2026-10-25).  keep_hierarchy + keep: each copy keeps its OWN flop through
// Yosys (opt_merge would otherwise fold logically identical registers back into one; face_reg idiom).
(* keep_hierarchy, keep *)
module ot_hgi_argmax18_rep_reg (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule

// one-hot ring pointer, slot 0 after reset, advances every edge (the delay line shifts every edge)
(* keep_hierarchy, keep *)
module ot_hgi_argmax18_ring_ptr #(parameter integer N = 6) (
    input  wire         clk,
    input  wire         rst_n,
    output reg  [N-1:0] q
);
    generate if (N == 1) begin : g_one
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b1; else q <= 1'b1;
    end else begin : g_n
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= {{(N-1){1'b0}}, 1'b1}; else q <= {q[N-2:0], q[N-1]};
    end endgenerate
endmodule
