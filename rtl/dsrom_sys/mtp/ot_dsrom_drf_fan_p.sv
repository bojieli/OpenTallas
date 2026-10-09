`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_drf_fan (PIN-SAFE variant "p", stream struct-close 2026-10-09; templates C + D; "-cl" line).
// Same module name and ports as rtl/dsrom_sys/mtp/ot_dsrom_drf_fan.sv: a route or bench uses ONE of the two files.
//
// Why (mtp-drf_fan-b-511fa714d-tc, TT -136.2, three classes, all in the 2-entry skid ot_dsrom_mtp_skid):
//   in -> reg  -199 (SS) / -136 (TT): f_civ[0] (input, die-link budget 518 ps) -> push -> 1,026 storage enables.
//   reg -> out -105 (TT): skid read pointer r (one flop) -> 513 output-mux selects (6 buffers) -> t_uod pins.
//   reg -> reg -49 (TT):  rr -> round-robin pick -> 5:1 x 513 merge mux -> u_uo storage.
// Fix, function unchanged:
//   * every port FIFO is ot_sc_pfifo (S 2, G 32): in_valid / out_ready touch only count / pointer flops and
//     per-32-bit registered pointer copies; storage loads the free slot every cycle; out_data is one AND-OR level
//     from flop copies; in_ready / out_valid are flops.  0 cycles vs ot_dsrom_mtp_skid.
//   * the up merge grants from a REGISTERED one-hot select (per-32-bit copies), chosen in an idle cycle between
//     messages: whole messages, round-robin, per-source order kept.  +1 cycle per up message (the idle grant
//     cycle); the down path is unchanged (0 cycles).
// Mutants: OT_DRFFAN_MUT_INTERLEAVE (the grant is re-chosen after every flit and the round-robin pointer moves on
//          every flit, so a message can be interleaved), OT_DRFFAN_MUT_DEST (DEST not rewritten for the child).
// ---------------------------------------------------------------------------
module ot_dsrom_drf_fan #(
    parameter integer FLIT = 512,
    parameter integer N    = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              up_in_valid,  output wire up_in_ready,  input  wire [FLIT:0] up_in_data,
    output wire              up_out_valid, input  wire up_out_ready, output wire [FLIT:0] up_out_data,
    output wire              lo_out_valid, input  wire lo_out_ready, output wire [FLIT:0] lo_out_data,
    input  wire              lo_in_valid,  output wire lo_in_ready,  input  wire [FLIT:0] lo_in_data,
    output wire [N-1:0]      ch_out_valid, input  wire [N-1:0] ch_out_ready, output wire [N*(FLIT+1)-1:0] ch_out_data,
    input  wire [N-1:0]      ch_in_valid,  output wire [N-1:0] ch_in_ready,  input  wire [N*(FLIT+1)-1:0] ch_in_data,
    output reg               fault
);
    localparam integer W = FLIT + 1, M = N + 1;           // merge inputs: 0 = local, 1..N = children
    localparam integer MB = $clog2(M);
    localparam integer G = 32, NG = (W + G - 1) / G;
    reg live; always @(posedge clk) live <= rst_n;

    // ------------------------------------------------ down: route by DEST (unchanged logic, pin-safe FIFOs)
    wire dv; wire [W-1:0] dd; wire dr;
    ot_sc_pfifo #(.W(W), .S(2), .G(G)) u_di (.clk(clk), .rst_n(live), .in_valid(up_in_valid), .in_ready(up_in_ready),
        .in_data(up_in_data), .out_valid(dv), .out_ready(dr), .out_data(dd));
    reg hdr; reg [MB-1:0] cur;
    wire [7:0] dest = dd[7:0];
    wire [MB-1:0] tgt = hdr ? ((dest[3:0] <= N) ? dest[MB-1:0] : {MB{1'b0}}) : cur;
    wire [M-1:0] o_rdy;
    wire [M-1:0] o_v;
    wire [W-1:0] o_d = (hdr && tgt != 0)
`ifndef OT_DRFFAN_MUT_DEST
                       ? {dd[W-1:8], 4'd0, dest[7:4]}
`else
                       ? dd
`endif
                       : dd;
    genvar g, j;
    generate for (g = 0; g < M; g = g + 1) begin : g_o
        assign o_v[g] = dv && tgt == g;
        if (g == 0) begin : g_l
            ot_sc_pfifo #(.W(W), .S(2), .G(G)) u_o (.clk(clk), .rst_n(live), .in_valid(o_v[g]), .in_ready(o_rdy[g]),
                .in_data(o_d), .out_valid(lo_out_valid), .out_ready(lo_out_ready), .out_data(lo_out_data));
        end else begin : g_c
            ot_sc_pfifo #(.W(W), .S(2), .G(G)) u_o (.clk(clk), .rst_n(live), .in_valid(o_v[g]), .in_ready(o_rdy[g]),
                .in_data(o_d), .out_valid(ch_out_valid[g-1]), .out_ready(ch_out_ready[g-1]),
                .out_data(ch_out_data[(g-1)*W +: W]));
        end
    end endgenerate
    assign dr = o_rdy[tgt];
    always @(posedge clk) begin
        if (!live) begin hdr <= 1'b1; cur <= 0; fault <= 1'b0; end
        else if (dv && dr) begin
            hdr <= dd[W-1]; cur <= tgt;
            if (hdr && dest[3:0] > N) fault <= 1'b1;
        end
    end

    // ------------------------------------------------ up: whole-message round-robin merge, registered grant
    wire [M-1:0] iv; wire [M*W-1:0] id; wire [M-1:0] ir;
    generate for (g = 0; g < M; g = g + 1) begin : g_i
        if (g == 0) begin : g_l
            ot_sc_pfifo #(.W(W), .S(2), .G(G)) u_i (.clk(clk), .rst_n(live), .in_valid(lo_in_valid), .in_ready(lo_in_ready),
                .in_data(lo_in_data), .out_valid(iv[g]), .out_ready(ir[g]), .out_data(id[g*W +: W]));
        end else begin : g_c
            ot_sc_pfifo #(.W(W), .S(2), .G(G)) u_i (.clk(clk), .rst_n(live), .in_valid(ch_in_valid[g-1]),
                .in_ready(ch_in_ready[g-1]), .in_data(ch_in_data[(g-1)*W +: W]), .out_valid(iv[g]), .out_ready(ir[g]),
                .out_data(id[g*W +: W]));
        end
    end endgenerate
    reg busy; reg [M-1:0] sel; reg [MB-1:0] rr;           // master copy of the grant (control)
    reg [MB-1:0] pick; reg pick_v;
    integer k;
    always @(*) begin
        pick_v = 1'b0; pick = rr;
        for (k = M - 1; k >= 0; k = k - 1) begin
            if (iv[(rr + k) % M]) begin pick_v = 1'b1; pick = (rr + k) % M; end
        end
    end
    wire u_rdy;
    wire s_v = busy && |(sel & iv);
    wire u_fire = s_v && u_rdy;
    wire [M-1:0] lastv;
    generate for (g = 0; g < M; g = g + 1) begin : g_lv
        assign lastv[g] = id[g*W + W - 1];
    end endgenerate
    wire last = |(sel & lastv);
    generate for (g = 0; g < M; g = g + 1) begin : g_ir
        assign ir[g] = u_fire && sel[g];
    end endgenerate
`ifdef OT_DRFFAN_MUT_INTERLEAVE
    wire end_msg = u_fire;
`else
    wire end_msg = u_fire && last;
`endif
    wire grant = !busy && pick_v;
    wire [M-1:0] sel_nx = grant ? (1 << pick) : (end_msg ? {M{1'b0}} : sel);
    wire busy_nx = grant ? 1'b1 : (end_msg ? 1'b0 : busy);
    integer q;
    always @(posedge clk) begin
        if (!live) begin busy <= 1'b0; sel <= 0; rr <= 0; end
        else begin
            busy <= busy_nx; sel <= sel_nx;
            if (end_msg) for (q = 0; q < M; q = q + 1) if (sel[q]) rr <= (q == M - 1) ? 0 : q + 1;
        end
    end
    // data: per-32-bit registered copies of the one-hot grant -> one AND-OR level into the output FIFO
    wire [W-1:0] u_d;
    generate for (g = 0; g < NG; g = g + 1) begin : g_m
        localparam integer LO = g * G;
        localparam integer GW = (W - LO < G) ? (W - LO) : G;
        wire [M-1:0] sc;
        wire [GW-1:0] acc [0:M];
        assign acc[0] = {GW{1'b0}};
        for (j = 0; j < M; j = j + 1) begin : g_j
            ot_sc_rep_ff #(.RV(1'b0)) u_sc (.clk(clk), .rst_n(live), .d(sel_nx[j]), .q(sc[j]));
            assign acc[j+1] = acc[j] | ({GW{sc[j]}} & id[j*W + LO +: GW]);
        end
        assign u_d[LO +: GW] = acc[M];
    end endgenerate
    ot_sc_pfifo #(.W(W), .S(2), .G(G)) u_uo (.clk(clk), .rst_n(live), .in_valid(s_v), .in_ready(u_rdy),
        .in_data(u_d), .out_valid(up_out_valid), .out_ready(up_out_ready), .out_data(up_out_data));
endmodule
