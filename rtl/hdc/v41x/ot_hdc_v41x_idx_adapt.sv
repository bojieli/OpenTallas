`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// INDEXER ADAPTER of the re-specified V4.1 decode core (ot_hdc_core_v41x, ME
// slot engine 3): the as-built matrix engine's contract for a KV-sourced op on
// the index keys (me_wsrc = 1, KV base >= cfg_ik_base; tools/hdc_program_v41.py
// Builder.indexer), run on the indexer engine's FP4 block-dot lanes
// (ot_hdc_v41x_q4dot, rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv).
//
// THE OP (Machine.me_lane, class "idx"): for every key row r < n (me_mmode = 1)
// and every index head hh = h*IL + j (h < 2^me_hg, j < IL),
//     S[hh, r] = sum_k q[hh, k] * key[r, k]            k < me_k = 32 (one block)
// q[hh, k] = VM[xbase + h*xcs + j*xjs + k*xks] (BF16-rounded when me_round),
// key[r, k] = KV element of word wbase + t*ts + k*ks, lane l (r = t*16 + l),
// written as lane l of word obase + t*ots + h*ogs + j*ojs.  q and the keys are
// FP4 E2M1 x UE8M0 quantise-dequantised (QDQ4) BF16 values, so every product
// and partial sum is exact in binary32: the sum is the exact block dot rounded
// once -- hdc_golden_v41.dots_q4 at index_head_dim 32 -- in any order (the
// ISA's csum and the as-built sequential sum agree).
//
// WHY ONLY THE DOTS.  ot_hdc_v41x_idx_engine fuses the dots with the ReLU,
// the head weights and the head sum, and emits only the final BF16 score per
// key; the program (unchanged) keeps the per-head scores in the vector memory
// (region S) and runs the ReLU / weight / head sum as the following SU op.
// So this adapter runs the engine's block-dot lane per (head, row) and writes
// S; fusing the SU op in needs a program change (S no longer written).
//
// RE-ENCODING.  Each 32-element block (a head's q, a key row) is re-encoded
// exactly from its BF16 values: scale byte u = Emax - 2 (Emax the largest
// biased exponent of a nonzero element), element code from (E - Emax + 2,
// top mantissa bit).  Every QDQ4 block encodes exactly this way (its largest
// code is >= 0.5 x its scale and all codes share one scale).  An element that
// does not encode (low mantissa bits, a gap of more than 3 binades, a
// subnormal / nonfinite value, or u outside 0..252) FAULTS -- only on a valid
// row / head.
//
// DATAFLOW.  QLOAD: the NH x 32 q elements through the G vector-memory x
// ports.  Per tile of 16 rows: KLOAD 32 KV words (G a cycle), ENC the 16 rows,
// then COMP: HP = G heads a cycle on 16 x HP q4dot lanes (the tile's keys
// stationary, the heads' q broadcast), each head's 16 row dots one masked
// word on write port g.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_adapt #(
    parameter integer W    = 16,
    parameter integer G    = 4,
    parameter integer IL   = 8,
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer MP   = 1,
    parameter integer NHM  = 32            // largest number of heads (2^hg * IL)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [2:0]        i_jsh,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [1:0]        i_hg,
    input  wire [AW-1:0]     i_ogs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    // KV SRAM (G words a cycle)
    output reg               kv_re,
    output reg  [G*AW-1:0]   kv_addr,
    input  wire [G*W*32-1:0] kv_q,
    // vector memory x reads (copy 0's G ports)
    output reg  [MP*G-1:0]   x_re,
    output reg  [MP*G*AW-1:0] x_addr,
    input  wire [MP*G*32-1:0] x_q,
    // result words
    output reg               ov,
    output reg  [MP*G-1:0]   o_we,
    output reg  [MP*G*AW-1:0] o_addr,
    output reg  [MP*G*W-1:0] o_mask,
    output reg  [MP*G*W*32-1:0] o_data,
    output reg               fault
);
    localparam integer HP  = G;                         // heads a cycle (one write port each)
    localparam integer QE  = NHM * 32;                  // q elements
    localparam integer QEW = $clog2(QE);
    localparam [2:0] A_IDLE = 0, A_QLD = 1, A_KLD = 2, A_ENC = 3, A_COMP = 4, A_DRAIN = 5;

    // ---- the block encoder: 32 BF16 values -> {bad, u[7:0], codes[127:0]}
    function automatic [136:0] enc32(input [32*16-1:0] v);
        reg [7:0] emax, e, u;
        reg [6:0] m;
        reg bad, any;
        reg [127:0] c;
        integer i;
        integer d;
        begin
            emax = 8'd0; bad = 1'b0; any = 1'b0; c = 128'd0;
            for (i = 0; i < 32; i = i + 1)
                if (v[16*i +: 15] != 15'd0) begin
                    any = 1'b1;
                    if (v[16*i + 7 +: 8] > emax) emax = v[16*i + 7 +: 8];
                end
            u = any ? emax - 8'd2 : 8'd127;
            if (any && (emax < 8'd2 || emax > 8'd254 || u > 8'd252)) bad = 1'b1;
            for (i = 0; i < 32; i = i + 1) begin
                e = v[16*i + 7 +: 8];
                m = v[16*i +: 7];
                if (v[16*i +: 15] != 15'd0) begin
                    d = e - emax + 2;
                    if (e == 8'd0 || e == 8'd255 || m[5:0] != 6'd0) bad = 1'b1;
                    case (d)
                        2:  c[4*i +: 3] = m[6] ? 3'd7 : 3'd6;
                        1:  c[4*i +: 3] = m[6] ? 3'd5 : 3'd4;
                        0:  c[4*i +: 3] = m[6] ? 3'd3 : 3'd2;
                        -1: begin c[4*i +: 3] = 3'd1; if (m[6]) bad = 1'b1; end
                        default: bad = 1'b1;
                    endcase
                    c[4*i + 3] = v[16*i + 15];
                end
            end
            enc32 = {bad, u, c};
        end
    endfunction
    //: to_bf16 (RNE on the bits) of a binary32 word
    function automatic [15:0] bf16(input [31:0] x);
        bf16 = x[31:16] + ((x[15] && (x[14:0] != 0 || x[16])) ? 16'd1 : 16'd0);
    endfunction

    reg  [2:0]    st;
    reg  [NW-1:0] n, tiles_all, kk;
    reg  [AW-1:0] wbase, ts, ks, xbase, xks, xjs, xcs, ogs, obase, ots, ojs;
    reg  [1:0]    hg;
    reg           rnd, oen;
    reg  [5:0]    nh;                                   // heads: 2^hg * IL
    reg           cfg_bad;
    reg  [QEW:0]  qe;                                   // q element being read
    reg  [NW-1:0] t;                                    // tile
    reg  [3:0]    kd;                                   // KV word group being read (G words)
    reg  [5:0]    hc;                                   // first head of the issuing group
    assign ready = (st == A_IDLE);

    // read tags: stage 1 (address registered), stage 2 (data at the port)
    reg           q1_v, q2_v, k1_v, k2_v;
    reg  [QEW:0]  q1_e, q2_e;
    reg  [3:0]    k1_d, k2_d;
    reg  [15:0]   qv [0:QE-1];                          // q, BF16, element hh*32 + k
    reg  [15:0]   kb [0:W*32-1];                        // key rows, BF16, element l*32 + k
    reg  [W*137-1:0] kenc;                              // the tile's encoded rows
    reg           rd_bad;                               // a q or key element that is not BF16

    // compute pipeline valid / tags (issue -> q4dot inputs -> 3 stages -> write)
    reg  [4:0]    pv;
    reg  [5:0]    ph [0:4];
    reg  [NW-1:0] pt [0:4];
    reg  [HP-1:0] pbad [0:4];                           // q block of the head does not encode

    wire [NW-1:0] qe_hh = qe >> 5;
    wire [AW-1:0] qh = qe_hh >> $clog2(IL);             // h
    wire [AW-1:0] qj = qe_hh & (IL - 1);                // j
    integer g;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= A_IDLE; x_re <= 0; kv_re <= 1'b0; q1_v <= 1'b0; q2_v <= 1'b0; k1_v <= 1'b0; k2_v <= 1'b0;
        end else begin
            x_re <= 0; kv_re <= 1'b0;
            q1_v <= 1'b0; k1_v <= 1'b0;
            q2_v <= q1_v; k2_v <= k1_v;
            case (st)
                A_IDLE: if (go) begin st <= A_QLD; qe <= 0; t <= 0; end
                A_QLD: begin
                    x_re[G-1:0] <= {G{1'b1}};
                    q1_v <= 1'b1;
                    qe <= qe + G;
                    if (qe + G >= {nh, 5'd0}) begin st <= A_KLD; kd <= 0; end
                end
                A_KLD: if (!q1_v && !q2_v) begin          // (the q writes have landed)
                    kv_re <= 1'b1;
                    k1_v <= 1'b1;
                    kd <= kd + 1'b1;
                    if (kd == 32 / G - 1) st <= A_ENC;
                end
                A_ENC: if (!k1_v && !k2_v) begin st <= A_COMP; hc <= 0; end
                A_COMP: begin
                    hc <= hc + HP;
                    if (hc + HP >= nh) st <= A_DRAIN;
                end
                A_DRAIN: if (pv == 0) begin
                    if (t + 1 >= tiles_all) st <= A_IDLE;
                    else begin t <= t + 1'b1; kd <= 0; st <= A_KLD; end
                end
                default: st <= A_IDLE;
            endcase
        end
    end
    always @(posedge clk) begin
        if (st == A_IDLE && go) begin
            n <= i_nout; kk <= i_k; wbase <= i_wbase; ts <= i_ts; ks <= i_ks; xbase <= i_xbase; xks <= i_xks;
            xjs <= i_xjs; xcs <= i_xcs; hg <= i_hg; ogs <= i_ogs; obase <= i_obase; ots <= i_ots; ojs <= i_ojs;
            rnd <= i_round; oen <= i_oen;
            nh <= IL << i_hg;
            tiles_all <= i_tiles * (G >> i_hg);
            //: shapes this adapter does not run: K other than one 32-block, a key that depends on the
            //: head (js != 0 below the jsh shift), the per-row mask mode 0, more heads than provisioned
            cfg_bad <= (i_k != 32) || (i_js != 0 && i_jsh < 3) || !i_mmode || ((IL << i_hg) > NHM) ||
                       (i_hg > 2);
        end
        // q reads: element qe + g = head hh, dim k
        for (g = 0; g < G; g = g + 1)
            x_addr[g*AW +: AW] <= xbase + qh * xcs + qj * xjs + ((qe + g) & 31) * xks;
        q1_e <= qe; q2_e <= q1_e;
        // key reads: dims kd*G + g of tile t
        for (g = 0; g < G; g = g + 1)
            kv_addr[g*AW +: AW] <= wbase + t * ts + (kd * G + g) * ks;
        k1_d <= kd; k2_d <= k1_d;
    end
    integer l;
    reg [31:0] xw;
    always @(posedge clk) begin
        if (q2_v)
            for (g = 0; g < G; g = g + 1) begin
                xw = x_q[32*g +: 32];
                qv[q2_e + g] <= rnd ? bf16(xw) : xw[31:16];
            end
        if (k2_v)
            for (g = 0; g < G; g = g + 1)
                for (l = 0; l < W; l = l + 1)
                    kb[l*32 + k2_d*G + g] <= kv_q[32*(g*W + l) + 16 +: 16];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rd_bad <= 1'b0;
        else if (st == A_IDLE && go) rd_bad <= 1'b0;
        else if (q2_v && !rnd)
            for (g = 0; g < G; g = g + 1)
                if (q2_e + g < {nh, 5'd0} && x_q[32*g +: 16] != 16'd0) rd_bad <= 1'b1;
    end
    // the KV's non-BF16 elements: checked per row at the write (row validity is known there)
    reg  [W-1:0] klow;
    always @(posedge clk) begin
        if (st == A_KLD && kd == 0 && !k2_v) klow <= {W{1'b0}};
        else if (k2_v)
            for (g = 0; g < G; g = g + 1)
                for (l = 0; l < W; l = l + 1)
                    if (kv_q[32*(g*W + l) +: 16] != 16'd0) klow[l] <= 1'b1;
    end

    // ENC: the 16 key rows of the tile
    reg [32*16-1:0] rowv;
    integer kx;
    always @(posedge clk)
        if (st == A_ENC && !k1_v && !k2_v)
            for (l = 0; l < W; l = l + 1) begin
                for (kx = 0; kx < 32; kx = kx + 1) rowv[16*kx +: 16] = kb[l*32 + kx];
                kenc[137*l +: 137] <= enc32(rowv);
            end

    // COMP: heads hc .. hc+HP-1: encode their q blocks into the lanes' input registers
    reg [HP*137-1:0] qenc;
    reg [32*16-1:0]  qrow;
    always @(posedge clk) begin
        for (g = 0; g < HP; g = g + 1) begin
            for (kx = 0; kx < 32; kx = kx + 1) qrow[16*kx +: 16] = qv[(hc + g) * 32 + kx];
            qenc[137*g +: 137] <= enc32(qrow);
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pv <= 5'd0;
        else pv <= {pv[3:0], st == A_COMP};
    end
    integer s;
    always @(posedge clk) begin
        ph[0] <= hc; pt[0] <= t;
        for (s = 1; s < 5; s = s + 1) begin ph[s] <= ph[s-1]; pt[s] <= pt[s-1]; end
        for (g = 0; g < HP; g = g + 1) pbad[1][g] <= qenc[137*g + 136];
        for (s = 2; s < 5; s = s + 1) pbad[s] <= pbad[s-1];
    end

    // the block-dot lanes: lane (g, l) = head hc+g x row l; inputs are qenc (registered at pv[0]) and
    // kenc; the dot leaves 3 cycles later (at pv[3]) -- the q4dot's stage A reads its inputs at pv[1]
    wire [HP*W*32-1:0] dy;
    wire [HP*W-1:0]    dovf;
    genvar gg, gl;
    generate for (gg = 0; gg < HP; gg = gg + 1) begin : g_h
        for (gl = 0; gl < W; gl = gl + 1) begin : g_l
            ot_hdc_v41x_q4dot u_dot (.clk(clk), .a(qenc[137*gg +: 128]), .b(kenc[137*gl +: 128]),
                                     .ua(qenc[137*gg + 128 +: 8]), .ub(kenc[137*gl + 128 +: 8]),
                                     .y(dy[32*(gg*W + gl) +: 32]), .ovf(dovf[gg*W + gl]));
        end
    end endgenerate

    // write: head hh = ph + g = h*IL + j, row t*16 + l
    reg [NW-1:0] hh;
    reg          wfault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we <= 0; ov <= 1'b0; wfault <= 1'b0; end
        else begin
            o_we <= 0; ov <= 1'b0; wfault <= 1'b0;
            if (pv[3]) begin
                ov <= 1'b1;
                for (g = 0; g < HP; g = g + 1)
                    if (ph[3] + g < nh) begin
                        o_we[g] <= oen;
                        for (l = 0; l < W; l = l + 1)
                            if (pt[3] * W + l < n)
                                if (dovf[g*W + l] || pbad[3][g] || kenc[137*l + 136] || klow[l]) wfault <= 1'b1;
                    end
            end
        end
    end
    always @(posedge clk) begin
        for (g = 0; g < HP; g = g + 1) begin
            hh = ph[3] + g;
            o_addr[g*AW +: AW] <= obase + pt[3] * ots + (hh >> $clog2(IL)) * ogs + (hh & (IL - 1)) * ojs;
            for (l = 0; l < W; l = l + 1) begin
                o_mask[g*W + l] <= (pt[3] * W + l < n);
                o_data[32*(g*W + l) +: 32] <= dy[32*(g*W + l) +: 32];
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; end
        else begin
            idle <= (st == A_IDLE) && !go && (pv == 0) && !(|o_we);
            fault <= wfault || (rd_bad && st != A_IDLE) || (cfg_bad && st != A_IDLE);
        end
    end
endmodule
