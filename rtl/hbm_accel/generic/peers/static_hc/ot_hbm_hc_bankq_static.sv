`timescale 1ns/1ps
`default_nettype none
// HC quarter-engine BANK TILES of the 3x3 ring (HBM-B-RTL2, plan (b) d4g, 2026-10-17, coordinator decision: the
// quadrant's hc_<q> + the quarter centre fill the ring hole, ot_hbm_hc_qhub_static).  One RTL core, three tile tops:
//   ot_hbm_hc_bankq_static     plain ring bank (positions 1, 3, 4, 5, 7)
//   ot_hbm_hc_bankq_ft_static  edge bank N/S (positions 2, 6) + registered feed of its two ring-corner neighbours
//                              (a corner bank does not touch the hole; die signals do not cross a hardened cluster)
//   ot_hbm_hc_bankq0_static    first bank W (position 0): first = 1, no sum_in/f_in ports (no die ties), and the
//                              chain-exit relay of bank 7 (the DRLY register that sat in the quarter engine centre)
// X WAVE BEATS: a bank takes its OWN 256-b slice of every 2,048-b x_wave beat straight from hc_<q> (chunk m = 8 beat + i:
// xb_d[32 i +: 32] = x_wave[256 i + 32 k +: 32], term k of the bank), not a 1,024-b word from the centre: the centre ->
// bank bus is 259 + 13 b instead of 1,037 b.  The landing reproduces ot_hbm_hc_xw_rx_static bit for bit and edge for
// edge (beat pin flop, beats 0..2 held, {beat 3 flop, held} = the slice of the reassembled wave, registered once more
// = the centre's old b_d register), so a bank directly beside the hole writes on the same edge as the single engine.
// A corner bank (fed through the edge tile's feed register) writes ONE edge later (compiler: wave landing +1).
// The residual low-half check (BF16-valued words) runs per bank on its own slice: wfault (sticky) -> centre fault OR.
// Pin registers: every input lands in a flop, every output is a flop (the bank stage registers its own chain pins).
// CHAIN PIN REGISTERS (HH-9 2026-10-19, default 0 = unchanged): the chain flops above sit INSIDE the hard lane leaves,
// so a leaf 550 um from its face made each bank -> bank hop leaf -> face -> face -> leaf (~1.1 mm, 47247cc08
// FLOORPLAN_MARGIN bank_distance).  CPI 1 lands the chain inputs (descriptor d_*, sum_in, f_in) in flops at the tile
// face; CPO 1 registers the chain outputs (o_*, sum_out, f_out) at the face.  +1 edge each on the bank's chain hop
// (descriptor and partial sums move together, so the bank computes exactly as before, CPI edges later); the centre /
// root add the ring's total (ot_hbm_hc_qeng_static CPR, ot_hbm_hc_qcen_static CHX, ot_hbm_hc_root_static QCHX).
// W (HBM-HC 2026-10-24, default 64 = unchanged, bit for bit): lanes of the bank tile = the hub's W (ot_hbm_hc_qcen_static).
// W 128 = the B2 half-hub bank (ot_hbm_hc_bank_static W 128: 16 lane leaves, 16 weight + 8 x macros): d_nv / o_nv 8 b,
// sum_in / sum_out 4,096 b, write slice j 2 b (4 slices of 32 lanes), bank 0 chain exit s_i / s_o 4,097 b.  The x-wave
// beat landing (256-b slice, 1,024-b assembled word) is width-independent.  TERM (core only) = the chain-terminal bank
// (ot_hbm_hc_bankq_term_static): no forward-descriptor face registers.
module ot_hbm_hc_bankq_core #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0,
    parameter integer W = 64, parameter integer TERM = 0,
    parameter integer NVW = (W == 128) ? 8 : 7, parameter integer JW = (W == 128) ? 2 : 1)(
    input  wire          clk, rst_n, first,
    input  wire          d_v, d_ss, input wire [NVW-1:0] d_nv, input wire [9:0] d_wa, d_xa,
    output wire          o_v, o_ss, output wire [NVW-1:0] o_nv, output wire [9:0] o_wa, o_xa,
    input  wire [W*32-1:0] sum_in, output wire [W*32-1:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, input wire [JW-1:0] j, input wire [9:0] wa,
    output reg           wfault
);
    initial if (!((W == 64 && NVW == 7 && JW == 1) || (W == 128 && NVW == 8 && JW == 2)))
        $fatal(1, "bankq W must be 64 or 128 (NVW / JW are derived)");
    wire [0:0] rc;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rc));
    // beat landing (= ot_hbm_hc_xw_rx_static data path, this bank's slice)
    reg v_q; reg [1:0] b_q; reg [255:0] d_q; reg [767:0] hold; reg [1023:0] asm_q;
    always @(posedge clk or negedge rc[0]) if (!rc[0]) v_q <= 1'b0; else v_q <= xb_v;
    always @(posedge clk) begin
        b_q <= xb_beat; d_q <= xb_d;
        for (integer b = 0; b < 3; b = b + 1) if (v_q && b_q == 2'(b)) hold[b*256 +: 256] <= d_q;   // decoded slots
        asm_q <= {d_q, hold};                                   // = the centre's old b_d slice
    end
    // residual words must be BF16-valued: low half of every binary32 container zero (checked on the write edge)
    reg lb_q, xv_c;
    always @(posedge clk) begin
        lb_q <= 1'b0;
        for (integer m = 0; m < 32; m = m + 1) if (|asm_q[m*32 +: 16]) lb_q <= 1'b1;
    end
    always @(posedge clk or negedge rc[0])
        if (!rc[0]) begin xv_c <= 1'b0; wfault <= 1'b0; end
        else begin xv_c <= xv; if (xv_c && lb_q) wfault <= 1'b1; end
    // chain pin registers (CPI / CPO)
    wire c_v, c_ss, c_f; wire [NVW-1:0] c_nv; wire [9:0] c_wa, c_xa; wire [W*32-1:0] c_s;    // into the stage
    wire q_v, q_ss, q_f; wire [NVW-1:0] q_nv; wire [9:0] q_wa, q_xa; wire [W*32-1:0] q_s;    // out of the stage
    if (CPI != 0) begin : g_cpi
        reg v_r, f_r, ss_r; reg [NVW-1:0] nv_r; reg [9:0] wa_r, xa_r; reg [W*32-1:0] s_r;
        always @(posedge clk or negedge rc[0]) if (!rc[0]) begin v_r <= 1'b0; f_r <= 1'b0; end else begin v_r <= d_v; f_r <= f_in; end
        always @(posedge clk) begin ss_r <= d_ss; nv_r <= d_nv; wa_r <= d_wa; xa_r <= d_xa; s_r <= sum_in; end
        assign {c_v, c_ss, c_nv, c_wa, c_xa, c_s, c_f} = {v_r, ss_r, nv_r, wa_r, xa_r, s_r, f_r};
    end else begin : g_ncpi
        assign {c_v, c_ss, c_nv, c_wa, c_xa, c_s, c_f} = {d_v, d_ss, d_nv, d_wa, d_xa, sum_in, f_in};
    end
    wire q_fm = (TERM != 0 && MUT == 3) ? ~q_f : q_f;   // terminal bench mutant 3: f_out inverted at the face
    if (CPO != 0 && TERM != 0) begin : g_cpot          // terminal: only the partial sums and fault flag leave the tile
        reg f_r; reg [W*32-1:0] s_r;
        always @(posedge clk or negedge rc[0]) if (!rc[0]) f_r <= 1'b0; else f_r <= q_fm;
        always @(posedge clk) s_r <= q_s;
        assign {sum_out, f_out} = {s_r, f_r};
        assign {o_v, o_ss, o_nv, o_wa, o_xa} = {q_v, q_ss, q_nv, q_wa, q_xa};   // no load (terminal top drops them)
    end else if (CPO != 0) begin : g_cpo
        reg v_r, f_r, ss_r; reg [NVW-1:0] nv_r; reg [9:0] wa_r, xa_r; reg [W*32-1:0] s_r;
        always @(posedge clk or negedge rc[0]) if (!rc[0]) begin v_r <= 1'b0; f_r <= 1'b0; end else begin v_r <= q_v; f_r <= q_f; end
        always @(posedge clk) begin ss_r <= q_ss; nv_r <= q_nv; wa_r <= q_wa; xa_r <= q_xa; s_r <= q_s; end
        assign {o_v, o_ss, o_nv, o_wa, o_xa, sum_out, f_out} = {v_r, ss_r, nv_r, wa_r, xa_r, s_r, f_r};
    end else begin : g_ncpo
        assign {o_v, o_ss, o_nv, o_wa, o_xa, sum_out, f_out} = {q_v, q_ss, q_nv, q_wa, q_xa, q_s, q_fm};
    end
    ot_hbm_hc_bank_static #(.W(W), .AW(10), .LM(8), .LA(7), .MUT((TERM != 0 && MUT != 1) ? 0 : MUT), .RST_RELAY(1)) u_b (
        .clk(clk), .rst_n(rst_n), .first(first),
        .d_v(c_v), .d_ss(c_ss), .d_nv(c_nv), .d_wa(c_wa), .d_xa(c_xa), .o_v(q_v), .o_ss(q_ss), .o_nv(q_nv),
        .o_wa(q_wa), .o_xa(q_xa), .sum_in(c_s), .sum_out(q_s), .f_in(c_f), .f_out(q_f),
        .wv(wv), .xv(xv), .j(j), .wa(wa), .wd(asm_q));
endmodule

module ot_hbm_hc_bankq_static #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0,
    parameter integer W = 64, parameter integer NVW = (W == 128) ? 8 : 7, parameter integer JW = (W == 128) ? 2 : 1)(
    input  wire          clk, rst_n,
    input  wire          d_v, d_ss, input wire [NVW-1:0] d_nv, input wire [9:0] d_wa, d_xa,
    output wire          o_v, o_ss, output wire [NVW-1:0] o_nv, output wire [9:0] o_wa, o_xa,
    input  wire [W*32-1:0] sum_in, output wire [W*32-1:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, input wire [JW-1:0] j, input wire [9:0] wa,
    output wire          wfault
);
    ot_hbm_hc_bankq_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO), .W(W)) u_c (.clk(clk), .rst_n(rst_n), .first(1'b0),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv),
        .o_wa(o_wa), .o_xa(o_xa), .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out),
        .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault));
endmodule

// edge bank with the registered feed of two corner banks (a = previous ring position, b = next ring position)
module ot_hbm_hc_bankq_ft_static #(parameter integer MUT = 0,
    parameter integer W = 64, parameter integer NVW = (W == 128) ? 8 : 7, parameter integer JW = (W == 128) ? 2 : 1)(
    input  wire          clk, rst_n,
    input  wire          d_v, d_ss, input wire [NVW-1:0] d_nv, input wire [9:0] d_wa, d_xa,
    output wire          o_v, o_ss, output wire [NVW-1:0] o_nv, output wire [9:0] o_wa, o_xa,
    input  wire [W*32-1:0] sum_in, output wire [W*32-1:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, input wire [JW-1:0] j, input wire [9:0] wa,
    output wire          wfault,
    input  wire          fa_xb_v, input wire [1:0] fa_xb_beat, input wire [255:0] fa_xb_d,
    input  wire          fa_wv, fa_xv, input wire [JW-1:0] fa_j, input wire [9:0] fa_wa,
    output reg           fa_xb_v_o, output reg [1:0] fa_xb_beat_o, output reg [255:0] fa_xb_d_o,
    output reg           fa_wv_o, fa_xv_o, output reg [JW-1:0] fa_j_o, output reg [9:0] fa_wa_o,
    input  wire          fb_xb_v, input wire [1:0] fb_xb_beat, input wire [255:0] fb_xb_d,
    input  wire          fb_wv, fb_xv, input wire [JW-1:0] fb_j, input wire [9:0] fb_wa,
    output reg           fb_xb_v_o, output reg [1:0] fb_xb_beat_o, output reg [255:0] fb_xb_d_o,
    output reg           fb_wv_o, fb_xv_o, output reg [JW-1:0] fb_j_o, output reg [9:0] fb_wa_o,
    // corner reset (a wire through this tile: assert stays asynchronous, the corner's own relay synchronises release)
    // and the corner's residual-check fault (registered back to the centre)
    input  wire          fa_rst_n, fb_rst_n, output wire fa_rst_n_o, fb_rst_n_o,
    input  wire          fa_wfault, fb_wfault, output reg fa_wfault_o, fb_wfault_o
);
    assign fa_rst_n_o = fa_rst_n; assign fb_rst_n_o = fb_rst_n;
    wire [1:0] rf;
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rf));
    always @(posedge clk or negedge rf[0])
        if (!rf[0]) begin fa_xb_v_o <= 1'b0; fa_wv_o <= 1'b0; fa_xv_o <= 1'b0; fa_wfault_o <= 1'b0; end
        else begin fa_xb_v_o <= fa_xb_v; fa_wv_o <= fa_wv; fa_xv_o <= fa_xv; fa_wfault_o <= fa_wfault; end
    always @(posedge clk or negedge rf[1])
        if (!rf[1]) begin fb_xb_v_o <= 1'b0; fb_wv_o <= 1'b0; fb_xv_o <= 1'b0; fb_wfault_o <= 1'b0; end
        else begin fb_xb_v_o <= fb_xb_v; fb_wv_o <= fb_wv; fb_xv_o <= fb_xv; fb_wfault_o <= fb_wfault; end
    always @(posedge clk) begin
        fa_xb_beat_o <= fa_xb_beat; fa_xb_d_o <= fa_xb_d; fa_j_o <= fa_j; fa_wa_o <= fa_wa;
        fb_xb_beat_o <= fb_xb_beat; fb_xb_d_o <= fb_xb_d; fb_j_o <= fb_j; fb_wa_o <= fb_wa;
    end
    ot_hbm_hc_bankq_core #(.MUT(MUT), .W(W)) u_c (.clk(clk), .rst_n(rst_n), .first(1'b0),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv),
        .o_wa(o_wa), .o_xa(o_xa), .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out),
        .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault));
endmodule

// first ring bank: chain start (desc from the centre) + bank 7's chain-exit relay (s_i -> s_o, DRLY registers)
module ot_hbm_hc_bankq0_static #(parameter integer MUT = 0, parameter integer DRLY = 1, parameter integer CPO = 0,
    parameter integer W = 64, parameter integer NVW = (W == 128) ? 8 : 7, parameter integer JW = (W == 128) ? 2 : 1)(
    input  wire          clk, rst_n,
    input  wire          d_v, d_ss, input wire [NVW-1:0] d_nv, input wire [9:0] d_wa, d_xa,
    output wire          o_v, o_ss, output wire [NVW-1:0] o_nv, output wire [9:0] o_wa, o_xa,
    output wire [W*32-1:0] sum_out, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, input wire [JW-1:0] j, input wire [9:0] wa,
    output wire          wfault,
    input  wire [W*32:0] s_i,
    output wire [W*32:0] s_o
);
    initial if (DRLY < 1) $fatal(1, "DRLY >= 1 (the chain exit is registered here)");
    reg [W*32:0] sr [0:DRLY-1];
    always @(posedge clk) begin
        sr[0] <= s_i;
        for (integer i = 1; i < DRLY; i = i + 1) sr[i] <= sr[i-1];
    end
    assign s_o = sr[DRLY-1];
    ot_hbm_hc_bankq_core #(.MUT(MUT), .CPO(CPO), .W(W)) u_c (.clk(clk), .rst_n(rst_n), .first(1'b1),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv),
        .o_wa(o_wa), .o_xa(o_xa), .sum_in({(W*32){1'b0}}), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out),
        .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault));
endmodule

`default_nettype wire
