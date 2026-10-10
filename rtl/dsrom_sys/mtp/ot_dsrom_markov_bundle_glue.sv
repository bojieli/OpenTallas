`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_markov_bundle_glue: the hardened glue element of one dsrom_mtp_head_full340_A bundle (mtp-head-1010 fork MB,
// 2026-10-10).  It is ot_dsrom_markov_head_bundle_x (ot_dsrom_markov_head_full340.sv) with its 5 ot_dsrom_head_elem
// (1 B + 4 A) and 4 ot_dsrom_markov_head_driver children removed: those are separate die macros, and their ports are
// this element's ports.  The closed ot_dsrom_head_bundle_glue (rtl/s81, CUT 1_0111_1011, no Markov join) does NOT
// cover it: the Markov bundle runs CUT 511 + SPLIT9 (SK 11, skews to 77 deep), lands B results per A, and owns the
// 4 -> 1 Markov argmax and the driver start / ready / go / done / fault control.
//
// DESIGN STANDARD (REVIEW_20261009.md), all exact at transaction level:
//  - every input captured in a pin flop, every output launched from a flop (no port -> port path);
//  - the xa/xb lane skew lines (16 lanes x 2 x SK*(j%8) deep, 19,712 flops) and the per-A landing delays
//    ({row, xsa} 4 deep x 4 copies) are ot_hdc_delay_ring rings (one-hot slot write, AND-OR read into an output
//    register: same delay, no zero-logic flop -> flop chain for hold repair);
//  - start and the driver row0 are launched per driver from their own flop (replicated control, one copy per macro);
//  - the B result is captured at its pin; its landing is one stage shorter so A sees B at the original offset.
// Latency against bundle_x (cycles): go/x -> B and A +1 (input pin flops), B result join unchanged relative to A,
// start -> driver +2 (start pin flop + per-driver launch flop; the die delays transaction / embedding by the same 2
// in ot_dsrom_markov_head_full340 HARD=1), driver head_go -> mg_all/mg_any +2, driver done -> bundle done +1,
// start_ready +1 (registered).  The lockstep die contract is unchanged (the die's own go/x tree follows head_go).
// ---------------------------------------------------------------------------
module ot_dsrom_markov_bundle_glue #(
    parameter bit ENABLE = 0,
    parameter integer A_INPUT_STAGES = 4,
    parameter [8:0] CUT = 511, parameter integer SPLIT9 = 1,
    parameter integer SK = 1+CUT[0]+CUT[1]+CUT[2]+CUT[3]+CUT[4]+CUT[5]+CUT[6]+CUT[7]+CUT[8]+SPLIT9,
    parameter integer RING = 1                 // 1: ring delay lines (default for this element); 0: shift lines (A/B check)
) (
    input wire clk, rst_n,
    // die side (bundle_x boundary)
    input wire start, output reg start_ready,
    input wire [16:0] row0,
    input wire embed_valid,
    output reg mg_all, output reg mg_any,
    input wire go, input wire [255:0] xa, xb,
    output reg done, output reg best_valid, output reg [16:0] best_row, output reg [31:0] best_bits,
    output reg fault,
    // B head element
    output wire b_go, output wire [255:0] b_x,
    input wire b_o_v, input wire [31:0] b_o_d, input wire b_fault,
    // 4 A head elements
    output wire [3:0] a_go, output wire [67:0] a_row, output wire [1023:0] a_x,
    output wire [3:0] a_bv, output wire [127:0] a_bd,
    input wire [3:0] a_fault,
    // 4 Markov drivers
    output reg [3:0] d_start, output reg [67:0] d_row0,
    input wire [3:0] d_sr, d_er, d_mg, d_md, d_mhave, d_mf,
    input wire [67:0] d_mr, input wire [127:0] d_mb
);
    // ---- input pin flops
    reg go_q, start_q, ev_q, bo_q, bf_q;
    reg [3:0] af_q, sr_q, er_q, mg_q, md_q, mh_q, mf_q;
    reg [255:0] xa_q, xb_q; reg [31:0] bd_q; reg [16:0] row0_q;
    reg [67:0] mr_q; reg [127:0] mb_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin go_q <= 0; start_q <= 0; ev_q <= 0; bo_q <= 0; bf_q <= 0;
            af_q <= 0; sr_q <= 0; er_q <= 0; mg_q <= 0; md_q <= 0; mh_q <= 0; mf_q <= 0; end
        else begin go_q <= go; start_q <= start; ev_q <= embed_valid; bo_q <= b_o_v; bf_q <= b_fault;
            af_q <= a_fault; sr_q <= d_sr; er_q <= d_er; mg_q <= d_mg; md_q <= d_md; mh_q <= d_mhave; mf_q <= d_mf; end
    always @(posedge clk) begin xa_q <= xa; xb_q <= xb; bd_q <= b_o_d; row0_q <= row0; mr_q <= d_mr; mb_q <= d_mb; end

    // ---- lane skews (x path, +1 for the pin flops on go and x together)
    wire [255:0] xsa, xsb;
    genvar j, q;
    generate for (j = 0; j < 16; j = j + 1) begin : g_sk
        ot_hdc_delay_ring #(.W(16), .D(SK*(j%8)), .RING(RING)) sa (.clk(clk), .rst_n(rst_n), .d(xa_q[16*j+:16]), .q(xsa[16*j+:16]));
        ot_hdc_delay_ring #(.W(16), .D(SK*(j%8)), .RING(RING)) sb (.clk(clk), .rst_n(rst_n), .d(xb_q[16*j+:16]), .q(xsb[16*j+:16]));
    end endgenerate
    assign b_go = go_q; assign b_x = xsb;

    // ---- B result demux (bundle_x bq / bv / held_b on the pin-captured B result)
    reg [1:0] bq; reg [3:0] bv; reg [31:0] held_b;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin bq <= 0; bv <= 0; end
        else begin if (go_q) bq <= 0; else if (bo_q) bq <= bq + 1; bv <= bo_q ? (4'b1 << bq) : 0; end
    always @(posedge clk) if (bo_q) held_b <= bd_q;

    // ---- control (bundle_x: busy / base / accept / reduce) on pin-captured driver status
    reg busy, control_fault; reg [16:0] base;
    wire fault_now = bf_q | (|af_q) | (|mf_q) | control_fault;
    wire rdy_int = ENABLE && !busy && (&sr_q) && !fault;
    wire accept = start_q && rdy_int;

    generate for (q = 0; q < 4; q = q + 1) begin : g_a
        wire [16:0] landed_row = base + 17'd32*q;
        ot_hdc_delay_ring #(.W(1), .D(A_INPUT_STAGES), .RESET(1), .RING(RING)) land_go (
            .clk(clk), .rst_n(rst_n), .d(go_q), .q(a_go[q]));
        ot_hdc_delay_ring #(.W(273), .D(A_INPUT_STAGES), .RING(RING)) land_x (
            .clk(clk), .rst_n(rst_n), .d({landed_row, xsa}), .q({a_row[17*q+:17], a_x[256*q+:256]}));
        // B part: one stage shorter (its pin flop bo_q / bd_q is the missing stage)
        ot_hdc_delay_ring #(.W(1), .D(A_INPUT_STAGES-1), .RESET(1), .RING(RING)) land_bv (
            .clk(clk), .rst_n(rst_n), .d(bv[q]), .q(a_bv[q]));
        ot_hdc_delay_ring #(.W(32), .D(A_INPUT_STAGES-1), .RING(RING)) land_bd (
            .clk(clk), .rst_n(rst_n), .d(held_b), .q(a_bd[32*q+:32]));
    end endgenerate

    function automatic [31:0] key(input [31:0] v);
        reg [31:0] z; begin z = (v[30:0] == 0) ? 0 : v; key = z[31] ? ~z : (z ^ 32'h80000000); end
    endfunction
    function automatic [81:0] pick(input [81:0] u, v);
        begin
            if (!u[81]) pick = v; else if (!v[81]) pick = u;
            else pick = (v[80:49] > u[80:49] || (v[80:49] == u[80:49] && v[48:32] < u[48:32])) ? v : u;
        end
    endfunction
    reg [81:0] c0, c1; wire [81:0] result = pick(c0, c1); reg reduce_valid, reduce_started;
    integer k;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin
        busy <= 0; base <= 0; control_fault <= 0; done <= 0; best_valid <= 0; best_row <= 0; best_bits <= 0;
        reduce_valid <= 0; reduce_started <= 0; c0 <= 0; c1 <= 0; fault <= 0; start_ready <= 0;
        mg_all <= 0; mg_any <= 0; d_start <= 0;
    end else begin
        done <= 0; reduce_valid <= 0;
        fault <= fault_now;
        start_ready <= rdy_int && !accept;
        mg_all <= &mg_q; mg_any <= |mg_q;
        d_start <= {4{accept}};                                       // one launch flop per driver
        if (start_q && !rdy_int) control_fault <= 1;                  // pushed start at a busy bundle
        if (ev_q && !(&er_q)) control_fault <= 1;                     // pushed beat at a not-ready driver
        if ((|mg_q) && !(&mg_q)) control_fault <= 1;
        if (accept) begin busy <= 1; base <= row0_q; reduce_started <= 0; best_valid <= 0; end
        if (busy && (&md_q) && !reduce_started && !fault) begin
            c0 <= pick({mh_q[0], key(mb_q[31:0]), mr_q[16:0], mb_q[31:0]}, {mh_q[1], key(mb_q[63:32]), mr_q[33:17], mb_q[63:32]});
            c1 <= pick({mh_q[2], key(mb_q[95:64]), mr_q[50:34], mb_q[95:64]}, {mh_q[3], key(mb_q[127:96]), mr_q[67:51], mb_q[127:96]});
            reduce_valid <= 1; reduce_started <= 1;
        end
        if (reduce_valid && !fault) begin
            done <= 1; busy <= 0; best_valid <= result[81]; best_row <= result[48:32]; best_bits <= result[31:0];
        end
    end
    // per-driver row0 (static per bundle), launched from its own flop
    always @(posedge clk) for (k = 0; k < 4; k = k + 1) d_row0[17*k+:17] <= row0_q + 17'd32*k;
endmodule
