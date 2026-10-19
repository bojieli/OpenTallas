`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// QW-COLL 2026-10-19: SAFE regional split of the Qwen TP8 static collective core (ot_coll_tp8_static, B4 native64).
// Both whole-core gates failed the clock rule on ONE glue root over 734x1037 um (TT pin-flop spread 451.7 / 277.3 ps,
// 6628 of 10196 sinks). The core is already bit-sliced in four 128-bit slices (NS = 4, one package fold and one cross
// fold per slice), so it is rebuilt as FIVE hardened LEAF tiles, each with its own small local clock tree:
//   ot_coll_split_q  x4 (one master, hardened once): 128 data bits of every pin record, its P/R ring data (2 x
//                     ot_sram_1r1w2c_128x64 each), its S-ring data (4 x ot_sram_1r1w2c_256x64), its two fold slices as soft
//                     logic, all data muxes.
//   ot_coll_split_c  x1: sequencer, every metadata/token/valid/check/fault, the P metadata ring (1 x 128x64), the R err/last
//                     ring (256 bits: stationary flop ring), the S-ring metadata (2 x 256x64). B4 capacity (128 words) in one native bank column: no bank select.
//                     All SRAM faces <= 3.81 contacts/um (the old 512x128 S macro had 7.4/um, the 32x64 5.95/um).
// Crossings C -> Q are schedule tokens only. Because the schedule is static, C reads every token TWO edges early
// (early taps of its stationary token rings, early S-meta read address) and sends it through a C output register and
// a Q input register: the Q datapath sees each select at its ORIGINAL cycle (0 added data edges).
// Crossings Q -> C are the two fold error bits. pe (package fold) feeds only the sticky fault: +2 diagnostic edges.
// xe (cross fold) is the R-record err bit (ur_rec[513], R ring bit 513, out_err): the whole E stage moves EX = 2 edges
// later (Q delays xr two more edges in a stationary ring, C lands xe in two registers). Reduce output and R send are
// EX = 2 edges later: out_valid reduce = c + 2LU + 2SL + LS + 12 + EX + w (compiler: tools/qwen_coll_tp8_static_bench
// --split). Gather timing, LU and LS are unchanged.
// Every delay line >= 3 deep is a stationary ring (ot_coll_tok_ring), every tile pin is registered (cmd_free is the one
// documented diagnostic exception), reset lands in two stages per tile, fault/fault_code leave registered together
// (+1 diagnostic edge). Negative controls: OT_TP8S_MUT_OWNER/GATHER/RANK/RLAT (as the monolithic core) plus
// OT_COLL_SPLIT_MUT_LEAD (C sends on-time, not early, F selects: Q output select 2 edges late),
// OT_COLL_SPLIT_MUT_EX (Q delays xr one edge less than the E-stage contract), OT_COLL_SPLIT_MUT_RERR (R err bit dropped
// from the C R-meta ring) and OT_COLL_SPLIT_MUT_SBANK (S-ring depth-bank select inverted).
// ---------------------------------------------------------------------------

// Registered copy (a separate kept module per ID: equal-D copies are never merged back by synthesis).
(* keep_hierarchy = 1 *) module ot_csp_rep_reg #(parameter integer W = 1, ID = 0, RST = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output reg [W-1:0] q);
    generate if (RST) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= {W{1'b0}}; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule

// One physical SerDes face metadata/valid register (separate parameterized module per face).
(* keep_hierarchy = 1 *) module ot_csp_sx_reg #(parameter integer W = 34, FACE = 0) (
    input wire clk, input wire rst_n, input wire dv, input wire [W-1:0] data, output reg qv, output reg [W-1:0] qdata);
    (* keep *) wire [W-1:0] face_data = data;
    always @(posedge clk) qdata <= face_data;
    always @(posedge clk or negedge rst_n) if (!rst_n) qv <= 1'b0; else qv <= dv;
endmodule

// Fixed delay D (>= 3) as a STATIONARY ring of D-1 slots + output register (no flop->flop shift chain). Every slot is
// written in turn by a rotating one-hot pointer; the same pointer selects the read (read-before-write), so q = d delayed
// D edges. Optional early tap qe = d delayed DE edges (2 <= DE < D), from a statically rotated copy of the pointer.
// Reset clears slots and outputs (identical to a reset shift chain).
(* keep_hierarchy = 1 *) module ot_coll_tok_ring #(parameter integer W = 1, D = 3, DE = 0, RST = 1, ID = 0) (
    input wire clk, input wire rs_n, input wire [W-1:0] d, output reg [W-1:0] q, output reg [W-1:0] qe);
    localparam integer N = D - 1;
    initial if (D < 3 || (DE != 0 && (DE < 2 || DE >= D))) $error("ot_coll_tok_ring: D >= 3 and 2 <= DE < D");
    reg [N-1:0] p;
    reg [W-1:0] m [0:N-1];
    always @(posedge clk or negedge rs_n) if (!rs_n) p <= {{(N-1){1'b0}}, 1'b1}; else p <= {p[N-2:0], p[N-1]};
    integer i;
    reg [W-1:0] rq, re;
    always @(*) begin
        rq = {W{1'b0}}; re = {W{1'b0}};
        for (i = 0; i < N; i = i + 1) begin
            rq = rq | (m[i] & {W{p[i]}});
            if (DE != 0) re = re | (m[i] & {W{p[(i + DE + N - 1) % N]}});
        end
    end
    generate if (RST) begin : g_r
        always @(posedge clk or negedge rs_n)
            if (!rs_n) begin for (i = 0; i < N; i = i + 1) m[i] <= {W{1'b0}}; q <= {W{1'b0}}; qe <= {W{1'b0}}; end
            else begin for (i = 0; i < N; i = i + 1) if (p[i]) m[i] <= d; q <= rq; qe <= re; end
    end else begin : g_n
        always @(posedge clk) begin for (i = 0; i < N; i = i + 1) if (p[i]) m[i] <= d; q <= rq; qe <= re; end
    end endgenerate
endmodule

// Wide stationary delay = independent <= 10-bit ot_coll_tok_ring chunks (each its own pointer: a pointer bit drives at
// most 10 slot enables + 20 read terms, checklist fanout <= ~32).
module ot_coll_tok_ring_w #(parameter integer W = 1, D = 3, DE = 0, RST = 1, ID = 0) (
    input wire clk, input wire rs_n, input wire [W-1:0] d, output wire [W-1:0] q, output wire [W-1:0] qe);
    localparam integer CW = 10, NC = (W + CW - 1) / CW;
    genvar c;
    generate for (c = 0; c < NC; c = c + 1) begin : g_c
        localparam integer LO = c * CW, CWI = (W - LO < CW) ? W - LO : CW;
        ot_coll_tok_ring #(.W(CWI), .D(D), .DE(DE), .RST(RST), .ID(ID * 64 + c)) u_r (.clk(clk), .rs_n(rs_n),
            .d(d[LO +: CWI]), .q(q[LO +: CWI]), .qe(qe[LO +: CWI]));
    end endgenerate
endmodule

// Fixed-offset delay ring of arbitrary useful width (ot_coll_static_ring semantics: written unconditionally every edge
// at the free-running index, rd valid OFF edges after wd), one 128-row dual-clock native bank per 64 bits
// (ot_sram_1r1w2c_128x64_m1, both clocks = clk, 3.81 contacts/um): B4 capacity 128 words in ONE bank column, so there is
// no bank-select mux. Read row = write row - (OFF - 1), never the written row (1 <= OFF - 1 <= 127).
module ot_coll_nring #(parameter integer OFF = 20, W = 128, ID = 0) (
    input wire clk, input wire rs_n, input wire [W-1:0] wd, output wire [W-1:0] rd);
    localparam integer NB = (W + 63) / 64;
    initial if (OFF < 2 || OFF > 128 || W < 1 || W > 576) $error("ot_coll_nring: 2 <= OFF <= 128, 1 <= W <= 576");
    reg [6:0] wa;
    always @(posedge clk or negedge rs_n) if (!rs_n) wa <= 7'd0; else wa <= wa + 7'd1;
    wire [6:0] ra = wa - 7'(OFF - 1);
    wire [64*NB-1:0] wpad = {{(64*NB-W){1'b0}}, wd};
    wire [64*NB-1:0] rdb;
    genvar b;
    generate for (b = 0; b < NB; b = b + 1) begin : g_b
        ot_sram_1r1w2c_128x64_m1 u_m (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(rdb[b*64 +: 64]),
            .w_ce_in(1'b1), .w_addr_in(wa), .wd_in(wpad[b*64 +: 64]), .w_mask_in({64{1'b1}}));
    end endgenerate
    assign rd = rdb[W-1:0];
endmodule

// 512-row S ring of arbitrary width: two depth banks x ceil(W/64) dual-clock 256x64 natives (2.56 contacts/um). Only the
// addressed depth bank reads (so a read never meets the written row); the bank select is registered with the synchronous
// read and replicated per 32 output bits.
module ot_coll_sring512 #(parameter integer W = 128, ID = 0) (
    input wire clk, input wire [8:0] wa, input wire [8:0] ra, input wire [W-1:0] wd, output wire [W-1:0] rd);
    localparam integer NB = (W + 63) / 64, GW = 32, NG = (W + GW - 1) / GW;
    wire [64*NB-1:0] wpad = {{(64*NB-W){1'b0}}, wd};
    wire [64*NB-1:0] rdb [0:1];
    genvar b, c, gg;
    generate for (b = 0; b < 2; b = b + 1) begin : g_d
        for (c = 0; c < NB; c = c + 1) begin : g_c
            ot_sram_1r1w2c_256x64_m1 u_m (.wclk(clk), .rclk(clk), .r_ce_in(ra[8] == b), .r_addr_in(ra[7:0]),
                .rd_out(rdb[b][c*64 +: 64]), .w_ce_in(wa[8] == b), .w_addr_in(wa[7:0]), .wd_in(wpad[c*64 +: 64]),
                .w_mask_in({64{1'b1}}));
        end
    end endgenerate
    wire [2*NG-1:0] boh;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_g
`ifdef OT_COLL_SPLIT_MUT_SBANK
        wire [1:0] oh_d = {!ra[8], ra[8]};
`else
        wire [1:0] oh_d = {ra[8], !ra[8]};
`endif
        ot_csp_rep_reg #(.W(2), .ID(6000 + ID*64 + gg), .RST(0)) u_oh (.clk(clk), .rst_n(1'b1), .d(oh_d),
            .q(boh[gg*2 +: 2]));
    end endgenerate
    reg [W-1:0] rsel;
    integer kbit;
    always @(*)
        for (kbit = 0; kbit < W; kbit = kbit + 1)
            rsel[kbit] = (rdb[0][kbit] & boh[(kbit / GW)*2]) | (rdb[1][kbit] & boh[(kbit / GW)*2 + 1]);
    assign rd = rsel;
endmodule

// One physical SerDes face data register (separate parameterized module per face and slice: never merged).
(* keep_hierarchy = 1 *) module ot_coll_split_sxd #(parameter integer W = 128, FACE = 0, QI = 0) (
    input wire clk, input wire [W-1:0] data, output reg [W-1:0] qdata);
    (* keep *) wire [W-1:0] face_data = data;
    always @(posedge clk) qdata <= face_data;
endmodule

// ============================ Q: one 128-bit data slice ============================
module ot_coll_split_q #(
    parameter integer LU = 66, LS = 391, ADD_LAT = 7, QI = 0, CQW = 42
) (
    input  wire              clk,           // the slice's one local CTS root (glue, both soft folds, its SRAM natives)
    input  wire              rst_n,
    input  wire [1:0]        pkg_s,
    input  wire              die_ps,
    input  wire [127:0]      in_data,
    output wire [127:0]      up_data,
    input  wire [127:0]      dp_data,
    output wire [127:0]      ur_data,
    input  wire [127:0]      dr_data,
    output wire [127:0]      sx0_data, sx1_data, sx2_data,   // one port per SerDes face (W: 1/2, E: 0)
    input  wire [127:0]      sr0_data, sr1_data, sr2_data,
    output wire [127:0]      out_data,
    // schedule tokens from C, two edges early at C, so each lands here at its original cycle. One pin per landing
    // flop (C drives every copy from its own output register): {tbv x8, red, tcv x4, gd x4, red2, gsel x4 (4b), tfv x4,
    // tfo x4}; gsel = gather output source one-hot {own, port2, port1, port0}.
    input  wire [CQW-1:0]    c_tok,
    output reg               q_pe,          // package-fold error  -> C (fault only)
    output reg               q_xe           // cross-fold error    -> C (R err bit, E stage)
);
    localparam integer EX = 2;
`ifdef OT_TP8S_MUT_RLAT
    localparam integer ROFF = LU + 1;
`else
    localparam integer ROFF = LU + 2;
`endif
    // safe3 (QW-CLUSTER3 2026-10-19): rst_n lands at the face in ONE 2-flop leaf (u_rs: 2 sinks on the port); rs then
    // feeds only reset-leaf / relay inputs: three registered relay copies (ot_csp_rep_reg, async assert with rs, release
    // one edge after rs, exactly like C's u_rsq/u_rsp/u_rss/u_rsr): rs_g (rings, counters, error outs), rs_t0/rs_t1 (the
    // two halves of the token landing register), and the folds' own leaves. No relay drives more than ~32 flops.
    // Folds: skew lines in SRAM rings, constant-zero package sources tied, adder data reset off, own leaf per fold
    // stage (ot_coll_fold_slice DLRING/NLIVE/ADRST/RSTSPLIT).
    wire rs, rs_g, rs_t0, rs_t1, rs_x;
    (* keep_hierarchy *) ot_coll_rst_leaf u_rs (.clk(clk), .arst_n(rst_n), .q(rs));
    ot_csp_rep_reg #(.W(1), .ID(QI*256 + 200), .RST(1)) u_rsg (.clk(clk), .rst_n(rs), .d(1'b1), .q(rs_g));
    ot_csp_rep_reg #(.W(1), .ID(QI*256 + 201), .RST(1)) u_rst0 (.clk(clk), .rst_n(rs), .d(1'b1), .q(rs_t0));
    ot_csp_rep_reg #(.W(1), .ID(QI*256 + 202), .RST(1)) u_rst1 (.clk(clk), .rst_n(rs), .d(1'b1), .q(rs_t1));
    ot_csp_rep_reg #(.W(1), .ID(QI*256 + 203), .RST(1)) u_rsx (.clk(clk), .rst_n(rs), .d(1'b1), .q(rs_x));   // u_xr pointers
    genvar k, j, gq;
    initial if (CQW != 42) $error("ot_coll_split_q: CQW 42");
    // ---- input pin registers: every token pin lands in exactly one flop (each copy <= 32 loads) ----
    wire [CQW-1:0] tok_r;
    ot_csp_rep_reg #(.W(21), .ID(QI*256 + 1), .RST(1)) u_tok (.clk(clk), .rst_n(rs_t0), .d(c_tok[20:0]), .q(tok_r[20:0]));
    ot_csp_rep_reg #(.W(CQW - 21), .ID(QI*256 + 2), .RST(1)) u_tok1 (.clk(clk), .rst_n(rs_t1), .d(c_tok[CQW-1:21]),
        .q(tok_r[CQW-1:21]));
    wire [7:0]  tbv_r = tok_r[41:34];
    wire        red_r = tok_r[33];
    wire [3:0]  tcv_r = tok_r[32:29], gd_r = tok_r[28:25];
    wire        red2_r = tok_r[24];
    wire [15:0] gs_r  = tok_r[23:8];
    wire [3:0]  tfv_r = tok_r[7:4], tfo_r = tok_r[3:0];
    // straps: one pin flop each, then static replicated copies
    reg [1:0] pk_q; reg di_q;
    always @(posedge clk) begin pk_q <= pkg_s; di_q <= die_ps; end
    wire [7:0] di_r;
    generate for (k = 0; k < 8; k = k + 1) begin : g_r8
        ot_csp_rep_reg #(.W(1), .ID(QI*256 + 8 + k), .RST(0)) u_di (.clk(clk), .rst_n(1'b1), .d(di_q), .q(di_r[k]));
    end endgenerate
    // static rank select per (rank, 32-bit group): registered from the registered strap
    wire [63:0] sel_r;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_xs
        wire [1:0] jqs = 2'(gq) - pk_q + 2'd3;
        for (k = 0; k < 4; k = k + 1) begin : g_c
            ot_csp_rep_reg #(.W(4), .ID(QI*256 + 64 + gq*4 + k), .RST(0)) u_sel (.clk(clk), .rst_n(1'b1),
                .d({2'(gq) == pk_q, (2'(gq) != pk_q) && jqs == 2'd2, (2'(gq) != pk_q) && jqs == 2'd1,
                    (2'(gq) != pk_q) && jqs == 2'd0}), .q(sel_r[(gq*4 + k)*4 +: 4]));
        end
    end endgenerate

    // ---- A: producer data pin register, P send, P ring ----
    reg [127:0] ir_q, upd_q;
    always @(posedge clk) begin ir_q <= in_data; upd_q <= ir_q; end
    assign up_data = upd_q;
    wire [127:0] pr_rd;
    ot_coll_nring #(.OFF(LU + 2), .W(128), .ID(QI*4 + 0)) u_pring (.clk(clk), .rs_n(rs_g), .wd(ir_q), .rd(pr_rd));

    // ---- B: peer partial pins, owner order, package fold ----
    reg [127:0] dpr_q;
    always @(posedge clk) dpr_q <= dp_data;
    reg [127:0] lo_q, hi_q;
    generate for (k = 0; k < 8; k = k + 1) begin : g_lohi
        always @(posedge clk) if (tbv_r[k]) begin
            lo_q[k*16 +: 16] <= !di_r[k] ? pr_rd[k*16 +: 16] : dpr_q[k*16 +: 16];
            hi_q[k*16 +: 16] <= !di_r[k] ? dpr_q[k*16 +: 16] : pr_rd[k*16 +: 16];
        end
    end endgenerate
    wire ps_v, ps_e; wire [127:0] ps_sum;
    (* keep_hierarchy *) ot_coll_fold_slice #(.DLRING(1), .NLIVE(2), .ADRST(0), .RSTSPLIT(1)) u_pf (.clk(clk),
        .rst_n(rs), .red_in(red_r),
        .src({256'd0, hi_q, lo_q}), .sum(ps_sum), .v_out(ps_v), .e_out(ps_e));

    // ---- C / W: package word, S ring data write, SerDes data send ----
    reg [127:0] pf_q;
    always @(posedge clk) pf_q <= ps_e ? {4{32'h7fc00000}} : ps_sum;
    always @(posedge clk or negedge rs_g) if (!rs_g) q_pe <= 1'b0; else q_pe <= ps_e & ps_v;
    wire [127:0] w_d;
    generate for (k = 0; k < 4; k = k + 1) begin : g_wd
        assign w_d[k*32 +: 32] = tcv_r[k] ? pf_q[k*32 +: 32] : (gd_r[k] ? hi_q[k*32 +: 32] : lo_q[k*32 +: 32]);
    end endgenerate
    wire [127:0] sx_q [0:2];
    assign sx0_data = sx_q[0]; assign sx1_data = sx_q[1]; assign sx2_data = sx_q[2];
    generate for (j = 0; j < 3; j = j + 1) begin : g_sxo
        (* keep_hierarchy = 1 *) ot_coll_split_sxd #(.W(128), .FACE(j), .QI(QI)) u_face (.clk(clk), .data(w_d),
            .qdata(sx_q[j]));
    end endgenerate
    reg [8:0] cc;
    always @(posedge clk or negedge rs_g) if (!rs_g) cc <= 9'd0; else cc <= cc + 9'd1;
    wire [127:0] td_d;
    ot_coll_sring512 #(.W(128), .ID(QI*4 + 2)) u_sd (.clk(clk), .wa(cc), .ra(cc - 9'(LS + 1)), .wd(w_d), .rd(td_d));

    // ---- D: SerDes data pins, cross fold sources, gather output ----
    reg [127:0] srr_q [0:2];
    generate for (j = 0; j < 3; j = j + 1) begin : g_sri
        always @(posedge clk) srr_q[j] <= (j == 0) ? sr0_data : (j == 1) ? sr1_data : sr2_data;
    end endgenerate
    wire [4*128-1:0] xsrc;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_xsrc
        for (k = 0; k < 4; k = k + 1) begin : g_c
            wire [3:0] s = sel_r[(gq*4 + k)*4 +: 4];
            assign xsrc[gq*128 + k*32 +: 32] = (td_d[k*32 +: 32] & {32{s[3]}}) | (srr_q[2][k*32 +: 32] & {32{s[2]}})
                                             | (srr_q[1][k*32 +: 32] & {32{s[1]}}) | (srr_q[0][k*32 +: 32] & {32{s[0]}});
        end
    end endgenerate
`ifdef OT_TP8S_MUT_RANK
    wire [4*128-1:0] xs = {xsrc[3*128 +: 128], xsrc[1*128 +: 128], xsrc[2*128 +: 128], xsrc[0 +: 128]};
`else
    wire [4*128-1:0] xs = xsrc;
`endif
    wire xs_v, xs_e; wire [127:0] xs_sum;
    (* keep_hierarchy *) ot_coll_fold_slice #(.DLRING(1), .ADRST(0), .RSTSPLIT(1)) u_xf (.clk(clk), .rst_n(rs),
        .red_in(red2_r), .src(xs),
        .sum(xs_sum), .v_out(xs_v), .e_out(xs_e));
    wire [127:0] g_out;
    generate for (k = 0; k < 4; k = k + 1) begin : g_go
        wire [3:0] s = gs_r[k*4 +: 4];
        assign g_out[k*32 +: 32] = (td_d[k*32 +: 32] & {32{s[3]}}) | (srr_q[2][k*32 +: 32] & {32{s[2]}})
                                 | (srr_q[1][k*32 +: 32] & {32{s[1]}}) | (srr_q[0][k*32 +: 32] & {32{s[0]}});
    end endgenerate

    // ---- E (EX = 2 edges later than the monolithic core): cross-fold result, UCIe R data, R ring data ----
    wire [127:0] xr_q, xr_unused;
`ifdef OT_COLL_SPLIT_MUT_EX
    reg [127:0] xr_m1, xr_m2;
    always @(posedge clk) begin xr_m1 <= xs_sum; xr_m2 <= xr_m1; end
    assign xr_q = xr_m2; assign xr_unused = 128'd0;
`else
    ot_coll_tok_ring_w #(.W(128), .D(1 + EX), .RST(0), .ID(QI)) u_xr (.clk(clk), .rs_n(rs_x), .d(xs_sum), .q(xr_q),
        .qe(xr_unused));
`endif
    always @(posedge clk or negedge rs_g) if (!rs_g) q_xe <= 1'b0; else q_xe <= xs_e & xs_v;
    reg [127:0] urd_q;
    always @(posedge clk) urd_q <= xr_q;
    assign ur_data = urd_q;
    wire [127:0] rr_rd;
    ot_coll_nring #(.OFF(ROFF), .W(128), .ID(QI*4 + 1)) u_rring (.clk(clk), .rs_n(rs_g), .wd(xr_q), .rd(rr_rd));

    // ---- F: peer result data pins, merge, output data ----
    reg [127:0] drr_q, od_q;
    always @(posedge clk) drr_q <= dr_data;
    integer kq;
    always @(posedge clk)
        for (kq = 0; kq < 4; kq = kq + 1)
            od_q[kq*32 +: 32] <= tfv_r[kq] ? (tfo_r[kq] ? rr_rd[kq*32 +: 32] : drr_q[kq*32 +: 32]) : g_out[kq*32 +: 32];
    assign out_data = od_q;
endmodule

// ============================ C: control, metadata, checks ============================
module ot_coll_split_c #(
    parameter integer LU = 66, LS = 391, ADD_LAT = 7, GC = 8, NQ = 4, TAGW = 32, CQW = 42
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire [1:0]             pkg_s,
    input  wire                   die_ps,
    input  wire                   cmd_v, cmd_mode,
    input  wire [15:0]            cmd_words,
    input  wire [TAGW-1:0]        cmd_tag,
    input  wire                   in_valid, in_last, in_mode,
    input  wire [TAGW-1:0]        in_tag,
    output wire                   up_valid,
    output wire [TAGW+1:0]        up_meta,      // up_rec[545:512] = {tag, mode, last}
    input  wire                   dp_valid,
    input  wire [TAGW+1:0]        dp_meta,
    output wire                   ur_valid,
    output wire [1:0]             ur_meta,      // ur_rec[513:512] = {err, last}
    input  wire                   dr_valid,
    input  wire [1:0]             dr_meta,
    output wire                   sx0_valid, sx1_valid, sx2_valid,
    output wire [TAGW+1:0]        sx0_meta, sx1_meta, sx2_meta,
    input  wire                   sr0_valid, sr1_valid, sr2_valid,
    input  wire [TAGW+1:0]        sr0_meta, sr1_meta, sr2_meta,
    output wire                   out_valid, out_last,
    output wire [2:0]             out_rank,
    output wire                   out_err,
    output reg                    fault,
    output reg  [4:0]             fault_code,
    output wire                   up_slot, ur_peer_slot,
    output wire                   sx0_peer_slot, sx1_peer_slot, sx2_peer_slot,
    output wire                   cmd_free,     // diagnostic availability predictor (combinational; see README)
    output wire [CQW-1:0]         q0_tok, q1_tok, q2_tok, q3_tok,   // one output register per Q landing flop (c_tok)
    input  wire [NQ-1:0]          q_pe, q_xe
);
    localparam integer SL = 3 * ADD_LAT + 2, MW = TAGW + 2, EX = 2;
    initial if (NQ != 4) $error("ot_coll_split_c: NQ 4");
    wire [2:0] sx_valid; wire [3*MW-1:0] sx_meta; wire [2:0] sx_peer_slot;
    assign {sx2_valid, sx1_valid, sx0_valid} = sx_valid;
    assign {sx2_meta, sx1_meta, sx0_meta} = sx_meta;
    assign {sx2_peer_slot, sx1_peer_slot, sx0_peer_slot} = sx_peer_slot;
    wire [2:0] sr_valid = {sr2_valid, sr1_valid, sr0_valid};
    wire [3*MW-1:0] sr_meta = {sr2_meta, sr1_meta, sr0_meta};
    wire [NQ*CQW-1:0] q_tok;
    assign {q3_tok, q2_tok, q1_tok, q0_tok} = q_tok;
    localparam integer DAB = LU + 2, DBC = SL + 2, TBW = TAGW + 3, DDE = SL + 1 + EX, DEF = LU + 2;
`ifdef OT_TP8S_MUT_RLAT
    localparam integer ROFF = LU + 1;
`else
    localparam integer ROFF = LU + 2;
`endif
    initial if (TAGW != 32 || LU < 2 || LU > 126 || LS < 3 || LS > 509 || GC != 8)
        $error("ot_coll_split_c: TAGW 32, 2 <= LU <= 126, 3 <= LS <= 509, GC 8");

    // ---- reset: one two-stage landing, then same-depth domain copies ----
    wire rs_l, rs_q, rs_p, rs_s, rs_r;
    (* keep_hierarchy *) ot_coll_rst_leaf u_rsl (.clk(clk), .arst_n(rst_n), .q(rs_l));
    ot_csp_rep_reg #(.W(1), .ID(8000), .RST(1)) u_rsq (.clk(clk), .rst_n(rs_l), .d(1'b1), .q(rs_q));
    ot_csp_rep_reg #(.W(1), .ID(8001), .RST(1)) u_rsp (.clk(clk), .rst_n(rs_l), .d(1'b1), .q(rs_p));
    ot_csp_rep_reg #(.W(1), .ID(8002), .RST(1)) u_rss (.clk(clk), .rst_n(rs_l), .d(1'b1), .q(rs_s));
    ot_csp_rep_reg #(.W(1), .ID(8003), .RST(1)) u_rsr (.clk(clk), .rst_n(rs_l), .d(1'b1), .q(rs_r));

    // ---- straps, command pins (the compiler issues one edge ahead, as qfd_io_collective_static) ----
    reg [1:0] pkg_q; reg die_q;
    always @(posedge clk) begin pkg_q <= pkg_s; die_q <= die_ps; end
    wire [1:0] PK = pkg_q;
    wire       DI = die_q;
    reg cv_pin, cm_pin; reg [15:0] cw_pin; reg [TAGW-1:0] ct_pin;
    always @(posedge clk) begin cm_pin <= cmd_mode; cw_pin <= cmd_words; ct_pin <= cmd_tag; end
    always @(posedge clk or negedge rs_l) if (!rs_l) cv_pin <= 1'b0; else cv_pin <= cmd_v;
    reg f_ar, f_md, f_pr, f_ln, f_cf;

    // ---- Q: compiled slot sequencer (unchanged) ----
    reg [15:0] rem, sidx; reg [2:0] cnt; reg s_mode; reg [TAGW-1:0] s_tag;
    wire slot    = (rem != 0) && (cnt == 0);
    wire can_cmd = (rem == 0) || (rem == 16'd1 && cnt == 0);
    wire cmd_bad = cv_pin && (!can_cmd || cw_pin == 0);
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin rem <= 0; sidx <= 0; cnt <= 0; s_mode <= 1'b0; s_tag <= 0; end
        else if (cv_pin && !cmd_bad) begin rem <= cw_pin; sidx <= 0; cnt <= 0; s_mode <= cm_pin; s_tag <= ct_pin; end
        else if (slot) begin rem <= rem - 16'd1; sidx <= sidx + 16'd1; cnt <= s_mode ? 3'(GC - 1) : 3'd0; end
        else if (cnt != 0) cnt <= cnt - 3'd1;
    assign cmd_free = (cv_pin && !cmd_bad) ? (cw_pin <= 1) :
        can_cmd || (rem == 2 && cnt == 0 && !s_mode) || (rem == 1 && cnt == 1);

    // ---- A: producer metadata pins, check, P send metadata, P meta ring ----
    reg iv_q; reg [MW-1:0] ir_m;
    reg ta_v, ta_m, ta_l, ta_p; reg [TAGW-1:0] ta_t;
    always @(posedge clk) ir_m <= {in_tag, in_mode, in_last};
    always @(posedge clk or negedge rs_p)
        if (!rs_p) begin iv_q <= 1'b0; ta_v <= 1'b0; ta_m <= 1'b0; ta_l <= 1'b0; ta_p <= 1'b0; ta_t <= 0; end
        else begin
            iv_q <= in_valid;
            ta_v <= slot; ta_m <= s_mode; ta_l <= (rem == 16'd1); ta_p <= sidx[0]; ta_t <= s_tag;
        end
    wire a_bad = (iv_q != ta_v) || (ta_v && iv_q && (ir_m != {ta_t, ta_m, ta_l}));
    reg upv_q, upc_q; reg [MW-1:0] upm_q;
    always @(posedge clk) upm_q <= ir_m;
    always @(posedge clk or negedge rs_p) if (!rs_p) begin upv_q <= 1'b0; upc_q <= 1'b0; end
        else begin upv_q <= ta_v && iv_q; upc_q <= ta_v; end
    assign up_valid = upv_q; assign up_meta = upm_q; assign up_slot = upc_q;
    wire [MW-1:0] pr_m;
    ot_coll_nring #(.OFF(LU + 2), .W(MW), .ID(60)) u_pmeta (.clk(clk), .rs_n(rs_p), .wd(ir_m), .rd(pr_m));
    // schedule token A -> B (LU + 2 edges) {v, mode, last, parity}; early tap two edges ahead for the Q crossing
    wire [3:0] tb, tb2;
    ot_coll_tok_ring_w #(.W(4), .D(DAB), .DE(DAB - 2), .ID(1)) u_tab (.clk(clk), .rs_n(rs_p),
        .d({ta_v, ta_m, ta_l, ta_p}), .q(tb), .qe(tb2));
    wire tb_v = tb[3], tb_m = tb[2], tb_l = tb[1], tb_p = tb[0];
    wire e2_v = tb2[3], e2_m = tb2[2], e2_p = tb2[0];

    // ---- B: peer partial metadata pins, pairing check, owner ----
    reg dpv_q; reg [MW-1:0] dpm_q;
    always @(posedge clk) dpm_q <= dp_meta;
    always @(posedge clk or negedge rs_p) if (!rs_p) dpv_q <= 1'b0; else dpv_q <= dp_valid;
    wire b_lnk = (dpv_q != tb_v);
    wire b_md  = tb_v && dpv_q && (dpm_q != pr_m);
`ifdef OT_TP8S_MUT_OWNER
    wire own_b  = tb_v && !tb_m && (tb_p == 1'b0);
    wire own_e2 = e2_v && !e2_m && (e2_p == 1'b0);
`else
    wire own_b  = tb_v && !tb_m && (tb_p == DI);
    wire own_e2 = e2_v && !e2_m && (e2_p == DI);
`endif
    reg own_e1;                                            // = own_b one edge ahead (Q red_q lands at own_b + 1)
    always @(posedge clk or negedge rs_p) if (!rs_p) own_e1 <= 1'b0; else own_e1 <= own_e2;
    // reduce token B -> C (SL + 2 edges) {v, own, last, tag}
    wire [TBW-1:0] tc, tc2;
    ot_coll_tok_ring_w #(.W(TBW), .D(DBC), .DE(DBC - 2), .ID(2)) u_tbc (.clk(clk), .rs_n(rs_p),
        .d({tb_v && !tb_m, own_b, tb_l, pr_m[MW-1:2]}), .q(tc), .qe(tc2));
    wire tc_v = tc[TBW-1], tc_o = tc[TBW-2], tc_l = tc[TBW-3];
    wire [TAGW-1:0] tc_t = tc[TAGW-1:0];
    // gather hold run k = 0..7 (on time) and its two-edge-early shadow (same update on the early token tap)
    reg g_run; reg [2:0] g_k; reg g_l; reg [TAGW-1:0] g_t;
    wire g_bad = tb_v && g_run && (g_k != 3'd7);
    always @(posedge clk or negedge rs_p)
        if (!rs_p) begin g_run <= 1'b0; g_k <= 0; g_l <= 1'b0; g_t <= 0; end
        else if (tb_v && tb_m) begin g_run <= 1'b1; g_k <= 0; g_l <= tb_l; g_t <= pr_m[MW-1:2]; end
        else if (g_run) begin g_run <= (g_k != 3'd7); g_k <= g_k + 3'd1; end
    reg sh_run; reg [2:0] sh_k;
    always @(posedge clk or negedge rs_p)
        if (!rs_p) begin sh_run <= 1'b0; sh_k <= 0; end
        else if (e2_v && e2_m) begin sh_run <= 1'b1; sh_k <= 0; end
        else if (sh_run) begin sh_run <= (sh_k != 3'd7); sh_k <= sh_k + 3'd1; end
`ifdef OT_TP8S_MUT_GATHER
    wire g_d = !g_k[2];
    wire gd_e2 = !sh_k[2];
`else
    wire g_d = g_k[2];
    wire gd_e2 = sh_k[2];
`endif
    wire [1:0] g_r = g_k[1:0];

    // ---- C / W: S ring metadata write, SerDes metadata/valid send ----
    reg [NQ-1:0] pe_i; reg pe_q;
    always @(posedge clk or negedge rs_s) if (!rs_s) begin pe_i <= 0; pe_q <= 1'b0; end
        else begin pe_i <= q_pe; pe_q <= |pe_i; end
    wire w_conf = tc_v && g_run;
    wire w_red  = tc_v;
    wire w_v    = tc_v || g_run;
    wire w_mode = !tc_v;
    wire w_od   = w_red ? tc_o : g_d;
    wire [1:0] w_r = w_red ? 2'd0 : g_r;
    wire w_l    = w_red ? tc_l : g_l;
    wire [TAGW-1:0] w_t = w_red ? tc_t : g_t;
    wire w_send = w_red ? (tc_v && tc_o) : (g_run && g_r == PK);
    genvar gj;
    generate for (gj = 0; gj < 3; gj = gj + 1) begin : g_sxo
        (* keep_hierarchy = 1 *) ot_csp_sx_reg #(.W(MW), .FACE(gj)) u_face (.clk(clk), .rst_n(rs_s),
            .dv(w_send), .data({w_t, w_mode, w_l}), .qv(sx_valid[gj]), .qdata(sx_meta[gj*MW +: MW]));
    end endgenerate
    reg [2:0] sxp_q;
    always @(posedge clk or negedge rs_s) if (!rs_s) sxp_q <= 3'b0;
        else sxp_q <= {w_red ? (tc_v && tc_o) : (g_run && g_r == PK + 2'd3),
                       w_red ? (tc_v && tc_o) : (g_run && g_r == PK + 2'd2),
                       w_red ? (tc_v && tc_o) : (g_run && g_r == PK + 2'd1)};
    assign sx_peer_slot = sxp_q;
    // S meta macro {v, rank2, od, mode, last, tag32}; read two edges EARLY (offset LS - 1) for the Q crossing
    reg [8:0] cc;
    always @(posedge clk or negedge rs_s) if (!rs_s) cc <= 9'd0; else cc <= cc + 9'd1;
    wire [37:0] s_rde;
    ot_coll_sring512 #(.W(38), .ID(62)) u_sm (.clk(clk), .wa(cc), .ra(cc - 9'(LS - 1)),
        .wd({w_v, w_r, w_od, w_mode, w_l, w_t}), .rd(s_rde));
    reg [9:0] warm;
    always @(posedge clk or negedge rs_s) if (!rs_s) warm <= 0; else if (warm != 10'(LS + 3)) warm <= warm + 10'd1;
    wire       te2_v = s_rde[37] && (warm >= 10'(LS + 1));       // = td_v two edges ahead
    wire [1:0] e_r   = s_rde[36:35];
    wire       e_od  = s_rde[34], e_m = s_rde[33];
    wire [1:0] e_jr  = e_r - PK + 2'd3;
    wire       e_own = (e_r == PK);
    wire       red2_e2 = te2_v && !e_m && e_od;
    wire [3:0] gsel_e2 = {e_own, !e_own && e_jr == 2'd2, !e_own && e_jr == 2'd1, !e_own && e_jr == 2'd0};
    // on-time D metadata: the early read landed two more edges in C (two stages, not a delay line)
    reg [37:0] sd1, sd2;
    always @(posedge clk or negedge rs_s) if (!rs_s) begin sd1 <= 0; sd2 <= 0; end
        else begin sd1 <= {te2_v, s_rde[36:0]}; sd2 <= sd1; end
    wire       td_v  = sd2[37];
    wire [1:0] td_r  = sd2[36:35];
    wire       td_od = sd2[34], td_m = sd2[33], td_l = sd2[32];
    wire [TAGW-1:0] td_t = sd2[31:0];

    // ---- D: SerDes metadata pins, check ----
    reg [2:0] srv_q; reg [MW-1:0] srm_q [0:2];
    generate for (gj = 0; gj < 3; gj = gj + 1) begin : g_sri
        always @(posedge clk) srm_q[gj] <= sr_meta[gj*MW +: MW];
    end endgenerate
    always @(posedge clk or negedge rs_s) if (!rs_s) srv_q <= 3'b0; else srv_q <= sr_valid;
    wire [1:0] jr = td_r - PK + 2'd3;
    wire [2:0] exp_sr = !td_v ? 3'b000 : !td_m ? (td_od ? 3'b111 : 3'b000)
                      : (td_r == PK) ? 3'b000 : (3'b001 << jr);
    wire d_lnk = (srv_q != exp_sr);
    reg  d_md;
    integer jj;
    always @(*) begin
        d_md = 1'b0;
        for (jj = 0; jj < 3; jj = jj + 1)
            if (exp_sr[jj] && srv_q[jj] && (srm_q[jj] != {td_t, td_m, td_l})) d_md = 1'b1;
    end
    wire gd_v = td_v && td_m;
    // reduce token D -> E (SL + 1 + EX edges) {v, own, last}
    wire [2:0] te, te_unused;
    ot_coll_tok_ring_w #(.W(3), .D(DDE), .ID(3)) u_tde (.clk(clk), .rs_n(rs_r), .d({td_v && !td_m, td_od, td_l}),
        .q(te), .qe(te_unused));
    wire te_v = te[2], te_o = te[1], te_l = te[0];

    // ---- E: cross-fold error landing, UCIe R metadata, R meta ring ----
    reg [NQ-1:0] xe_i; reg xe_q;
    always @(posedge clk or negedge rs_r) if (!rs_r) begin xe_i <= 0; xe_q <= 1'b0; end
        else begin xe_i <= q_xe; xe_q <= |xe_i; end
    wire e_own2 = te_v && te_o;
    reg urv_q, urp_q; reg [1:0] urm_q;
    always @(posedge clk) urm_q <= {xe_q, te_l};
    always @(posedge clk or negedge rs_r) if (!rs_r) begin urv_q <= 1'b0; urp_q <= 1'b0; end
        else begin urv_q <= e_own2; urp_q <= te_v && !te_o; end
    assign ur_valid = urv_q; assign ur_peer_slot = urp_q; assign ur_meta = urm_q;
    wire [1:0] rr_m;
`ifdef OT_COLL_SPLIT_MUT_RERR
    ot_coll_tok_ring_w #(.W(2), .D(ROFF), .ID(5)) u_rmeta (.clk(clk), .rs_n(rs_r), .d({1'b0, te_l}), .q(rr_m), .qe());
`else
    ot_coll_tok_ring_w #(.W(2), .D(ROFF), .ID(5)) u_rmeta (.clk(clk), .rs_n(rs_r), .d({xe_q, te_l}), .q(rr_m), .qe());
`endif
    // token E -> F (LU + 2 edges) {v, own, last}; early tap for the Q output select
    wire [2:0] tf, tf2;
    ot_coll_tok_ring_w #(.W(3), .D(DEF), .DE(DEF - 2), .ID(4)) u_tef (.clk(clk), .rs_n(rs_r), .d({te_v, te_o, te_l}),
        .q(tf), .qe(tf2));
    wire tf_v = tf[2], tf_o = tf[1], tf_l = tf[0];

    // ---- F: peer result metadata pins, output metadata ----
    reg drv_q; reg [1:0] drm_q;
    always @(posedge clk) drm_q <= dr_meta;
    always @(posedge clk or negedge rs_r) if (!rs_r) drv_q <= 1'b0; else drv_q <= dr_valid;
    wire f_lnk = (drv_q != (tf_v && !tf_o));
    wire f_mdx = tf_v && !tf_o && drv_q && (drm_q[0] != tf_l);
    wire rf_e  = tf_o ? rr_m[1] : drm_q[1];
    wire o_conf = tf_v && gd_v;
    reg ov_q, ol_q, oe_q; reg [2:0] or_q;
    always @(posedge clk) begin
        ol_q <= tf_v ? tf_l : (td_l && td_od && td_r == 2'd3);
        or_q <= tf_v ? 3'd0 : {td_od, td_r};
        oe_q <= tf_v ? rf_e : 1'b0;
    end
    always @(posedge clk or negedge rs_r) if (!rs_r) ov_q <= 1'b0; else ov_q <= tf_v || gd_v;
    assign out_valid = ov_q; assign out_last = ol_q; assign out_rank = or_q; assign out_err = oe_q;

    // ---- sticky faults; the complete {fault, fault_code} bundle leaves registered together (+1 diagnostic edge) ----
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin f_ar <= 1'b0; f_md <= 1'b0; f_pr <= 1'b0; f_ln <= 1'b0; f_cf <= 1'b0; end
        else begin
            if (pe_q || (xe_q && e_own2) || (tf_v && rf_e)) f_ar <= 1'b1;
            if (b_md || d_md || f_mdx) f_md <= 1'b1;
            if (a_bad) f_pr <= 1'b1;
            if (b_lnk || d_lnk || f_lnk) f_ln <= 1'b1;
            if (cmd_bad || w_conf || o_conf || g_bad) f_cf <= 1'b1;
        end
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin fault <= 1'b0; fault_code <= 5'd0; end
        else begin fault <= f_cf | f_ln | f_pr | f_md | f_ar; fault_code <= {f_cf, f_ln, f_pr, f_md, f_ar}; end

    // ---- C -> Q crossing: one kept output register per Q (lands in the Q input register at the original cycle) ----
`ifdef OT_COLL_SPLIT_MUT_LEAD
    wire tfv_x = tf_v, tfo_x = tf_o;                      // negative control: on-time F select (2 edges late at Q)
`else
    wire tfv_x = tf2[2], tfo_x = tf2[1];
`endif
    // every copy is its own kept module instance (distinct ID): equal-D copies are never merged back by synthesis
    wire [CQW-1:0] qx = {{8{e2_v}}, own_e1, {4{tc2[TBW-1]}}, {4{gd_e2}}, red2_e2, {4{gsel_e2}}, {4{tfv_x}}, {4{tfo_x}}};
    genvar gi, gb;
    generate for (gi = 0; gi < NQ; gi = gi + 1) begin : g_qo
        for (gb = 0; gb < CQW; gb = gb + 1) begin : g_b
            ot_csp_rep_reg #(.W(1), .ID(9000 + gi*64 + gb), .RST(1)) u_qo (.clk(clk), .rst_n(rs_p), .d(qx[gb]),
                .q(q_tok[gi*CQW + gb]));
        end
    end endgenerate
endmodule

// ============================ core parent: C + 4 Q (no glue logic) ============================
// Port-compatible with qfd_io_collective_static (B4) except the clock entries: one local root per hardened leaf
// (clk = C, clk_q0..3 = Q). The die drives every entry from its regional
// clock with the neighbour-matched boundary (C <-> each Q register hop, TT and FF <= 80 ps).
`ifdef OT_QFDS_LU
`define OT_CSP_LU `OT_QFDS_LU
`else
`define OT_CSP_LU 66
`endif
`ifdef OT_QFDS_LS
`define OT_CSP_LS `OT_QFDS_LS
`else
`define OT_CSP_LS 391
`endif
module qfd_io_collective_split #(parameter integer LU = `OT_CSP_LU, parameter integer LS = `OT_CSP_LS) (
    input  wire          clk,
    input  wire          clk_q0, clk_q1, clk_q2, clk_q3,
    input  wire          rst_n,
    input  wire [1:0]    pkg_s,
    input  wire          die_ps,
    input  wire          cmd_v,
    input  wire          cmd_mode,
    input  wire [15:0]   cmd_words,
    input  wire [31:0]   cmd_tag,
    input  wire          in_valid,
    input  wire [511:0]  in_data,
    input  wire          in_last,
    input  wire          in_mode,
    input  wire [31:0]   in_tag,
    output wire          up_valid,
    output wire [545:0]  up_rec,
    input  wire          dp_valid,
    input  wire [545:0]  dp_rec,
    output wire          ur_valid,
    output wire [513:0]  ur_rec,
    input  wire          dr_valid,
    input  wire [513:0]  dr_rec,
    output wire          sx0_valid, sx1_valid, sx2_valid,
    output wire [545:0]  sx0_rec, sx1_rec, sx2_rec,
    input  wire          sr0_valid, sr1_valid, sr2_valid,
    input  wire [545:0]  sr0_rec, sr1_rec, sr2_rec,
    output wire          out_valid,
    output wire [511:0]  out_data,
    output wire          out_last,
    output wire [2:0]    out_rank,
    output wire          out_err,
    output wire          fault,
    output wire [4:0]    fault_code,
    output wire          up_slot,
    output wire          ur_peer_slot,
    output wire          sx0_peer_slot, sx1_peer_slot, sx2_peer_slot,
    output wire          cmd_free
);
    localparam integer NQ = 4;
    initial if (LU + 2 <= 64 || LU + 2 > 128) $error("qfd_io_collective_split: B4 profile, 65 <= LU + 2 <= 128");
    wire [3:0] cq = {clk_q3, clk_q2, clk_q1, clk_q0};
    localparam integer CQW = 42;
    wire [NQ-1:0] q_pe, q_xe;
    wire [CQW-1:0] q_tok [0:NQ-1];
    wire [33:0] sx_meta [0:2];
    wire [33:0] up_meta; wire [1:0] ur_meta;
    wire [511:0] up_d, ur_d;
    wire [3*512-1:0] sx_d;                  // [face][512]
    ot_coll_split_c #(.LU(LU), .LS(LS)) u_c (.clk(clk), .rst_n(rst_n), .pkg_s(pkg_s), .die_ps(die_ps),
        .cmd_v(cmd_v), .cmd_mode(cmd_mode), .cmd_words(cmd_words), .cmd_tag(cmd_tag),
        .in_valid(in_valid), .in_last(in_last), .in_mode(in_mode), .in_tag(in_tag),
        .up_valid(up_valid), .up_meta(up_meta), .dp_valid(dp_valid), .dp_meta(dp_rec[545:512]),
        .ur_valid(ur_valid), .ur_meta(ur_meta), .dr_valid(dr_valid), .dr_meta(dr_rec[513:512]),
        .sx0_valid(sx0_valid), .sx1_valid(sx1_valid), .sx2_valid(sx2_valid),
        .sx0_meta(sx_meta[0]), .sx1_meta(sx_meta[1]), .sx2_meta(sx_meta[2]),
        .sr0_valid(sr0_valid), .sr1_valid(sr1_valid), .sr2_valid(sr2_valid),
        .sr0_meta(sr0_rec[545:512]), .sr1_meta(sr1_rec[545:512]), .sr2_meta(sr2_rec[545:512]),
        .out_valid(out_valid), .out_last(out_last), .out_rank(out_rank), .out_err(out_err),
        .fault(fault), .fault_code(fault_code), .up_slot(up_slot), .ur_peer_slot(ur_peer_slot),
        .sx0_peer_slot(sx0_peer_slot), .sx1_peer_slot(sx1_peer_slot), .sx2_peer_slot(sx2_peer_slot),
        .cmd_free(cmd_free), .q0_tok(q_tok[0]), .q1_tok(q_tok[1]), .q2_tok(q_tok[2]), .q3_tok(q_tok[3]),
        .q_pe(q_pe), .q_xe(q_xe));
    genvar q;
    generate for (q = 0; q < NQ; q = q + 1) begin : g_q
        ot_coll_split_q #(.LU(LU), .LS(LS), .QI(0)) u_q (.clk(cq[q]),
            .rst_n(rst_n), .pkg_s(pkg_s), .die_ps(die_ps),
            .in_data(in_data[q*128 +: 128]), .up_data(up_d[q*128 +: 128]), .dp_data(dp_rec[q*128 +: 128]),
            .ur_data(ur_d[q*128 +: 128]), .dr_data(dr_rec[q*128 +: 128]),
            .sx0_data(sx_d[q*128 +: 128]), .sx1_data(sx_d[512 + q*128 +: 128]), .sx2_data(sx_d[1024 + q*128 +: 128]),
            .sr0_data(sr0_rec[q*128 +: 128]), .sr1_data(sr1_rec[q*128 +: 128]), .sr2_data(sr2_rec[q*128 +: 128]),
            .out_data(out_data[q*128 +: 128]),
            .c_tok(q_tok[q]), .q_pe(q_pe[q]), .q_xe(q_xe[q]));
    end endgenerate
    assign up_rec  = {up_meta, up_d};
    assign ur_rec  = {ur_meta, ur_d};
    assign sx0_rec = {sx_meta[0], sx_d[0*512 +: 512]};
    assign sx1_rec = {sx_meta[1], sx_d[1*512 +: 512]};
    assign sx2_rec = {sx_meta[2], sx_d[2*512 +: 512]};
endmodule
