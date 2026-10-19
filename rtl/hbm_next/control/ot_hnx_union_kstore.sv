`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT LH-P3UNITS/UNIONTILE 10-19: quadrant per-cardinality KERNEL STORE (boot-resident, one copy per quadrant).
// Content (UNIONVAR capacity.json): per (layer, c, loop-body record) HGI-1R descriptor, 1,408 b = 5.5 words of 256 b,
// MTP N6 + MU N4 resident: 6,600 words in 7 x 1024 x 256 1R1W macros (linear word address a, macro a[12:10]).
//   loop 1 descriptor (w1 + w3 records = 2 x 1,408 b = 11 words): kref j < 400  -> words 11 j .. 11 j + 10
//   loop 2 descriptor (w2 record, 5.5 words, packed in pairs):  kref j < 503   -> words 4400 + floor(11 j / 2) ..
//                                                                  + 5 (6 words; half = j odd: starts mid-word)
// Every launch (loop 1 / 2) streams its descriptor words to the quadrant's units at one word per edge, KLAT = 6 edges
// after the launch register (K0 address, K1 macro read port, macro read, K3 capture rung beside each macro, K4 kept-select
// AND-OR register in the read channel, K5 output pin register: every wire stage <= ~405 um in the 518 x 432 tile).
// Boot writes go through two KEPT register stages per macro column (W1 beside the pin face, W2 beside the column's write
// faces), so no boot wire crosses the tile in one cycle (boot latency is irrelevant; 3 edges).  Static: a launch while a stream is in flight, an out-of-range kref, or a boot write
// during a stream FAULTS (cfg legality: D1[c] >= 11, D2[c] >= 6 edges; production kernel spans are hundreds).
// Boot writes (idle only) arrive registered from the tile pins; one write per edge (6,600 edges per copy, once).
// KMUT 1 (bench mutant): loop 2 uses the loop-1 address map (no half-word packing) -> wrong descriptor words.
module ot_hnx_uq_kbit (input wire clk, input wire d, output reg q);    // kept select copy (fanout <= 32 each)
    always @(posedge clk) q <= d;
endmodule

module ot_hnx_uq_wreg (input wire clk, input wire [269:0] d, output reg [269:0] q);   // kept boot-write stage (per column)
    always @(posedge clk) q <= d;                                                        // {ce[3:0], addr[9:0], data[255:0]}
endmodule

module ot_hnx_union_kstore #(
    parameter integer KMUT = 0
)(
    input  wire          clk,
    input  wire          rst_n,
    input  wire          bw_v,            // registered boot write (kernel-store words)
    input  wire [12:0]   bw_addr,
    input  wire [255:0]  bw_data,
    input  wire          l_v,             // dispatcher launch register (same edge as the tile's launch outputs)
    input  wire [1:0]    l_loop,
    input  wire [11:0]   l_kref,
    output reg           kw_v,
    output reg           kw_first,
    output reg           kw_half,
    output wire [255:0]  kw_data,
    output reg           kfault
);
    localparam integer NM = 7;
    // ---------------------------------------------------------------- K0: address of the launch's descriptor
    wire [13:0] k11 = {l_kref, 3'b000} + {1'b0, l_kref, 1'b0} + {2'b00, l_kref};     // 11 * kref (< 16384)
    wire        lp2 = (l_loop == 2'd2) && (KMUT != 1);
    wire [13:0] a0  = lp2 ? 14'd4400 + {1'b0, k11[13:1]} : k11;
    wire [3:0]  len = lp2 ? 4'd6 : 4'd11;
    wire        bad = lp2 ? (a0 > 14'd7162) : (k11 > 14'd4389);
    reg  [12:0] ra; reg [3:0] rcnt; reg rhalf, rfirst;
    // ---------------------------------------------------------------- K1: read port of one macro (registered)
    reg  [NM-1:0] rce; reg [9:0] raddr; reg v1, f1, h1; reg [NM-1:0] s1;
    reg  v2, f2, h2, v3, f3, h3, v4, f4, h4; reg [NM-1:0] s2;
    // boot write port: W0 decode register, then two kept stages per column (A = macros 0..3, B = macros 4..6)
    reg  [NM-1:0] wce; reg [9:0] waddr; reg [255:0] wd;
    wire [269:0] wa1, wb1, wa2, wb2;
    ot_hnx_uq_wreg u_wa1 (.clk(clk), .d({wce[3:0], waddr, wd}), .q(wa1));
    ot_hnx_uq_wreg u_wb1 (.clk(clk), .d({1'b0, wce[6:4], waddr, wd}), .q(wb1));
    ot_hnx_uq_wreg u_wa2 (.clk(clk), .d(wa1), .q(wa2));
    ot_hnx_uq_wreg u_wb2 (.clk(clk), .d(wb1), .q(wb2));
    wire [NM-1:0] wce_m = {wb2[268:266], wa2[269:266]};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rcnt <= 4'd0; rce <= {NM{1'b0}}; wce <= {NM{1'b0}}; v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; v4 <= 1'b0; kw_v <= 1'b0; kfault <= 1'b0;
        end else begin
            kfault <= 1'b0;
            // K0
            if (l_v && l_loop != 2'd3) begin
                if (rcnt != 4'd0 || bad) kfault <= 1'b1;
                ra <= a0[12:0]; rcnt <= len; rhalf <= lp2 & k11[0]; rfirst <= 1'b1;
            end else if (rcnt != 4'd0) begin
                ra <= ra + 13'd1; rcnt <= rcnt - 4'd1; rfirst <= 1'b0;
            end
            // K1: one macro read per edge
            rce <= {NM{1'b0}}; v1 <= 1'b0;
            if (rcnt != 4'd0) begin
                rce[ra[12:10]] <= 1'b1; raddr <= ra[9:0];
                v1 <= 1'b1; f1 <= rfirst; h1 <= rhalf & rfirst;
            end
            s1 <= {NM{1'b0}}; if (rcnt != 4'd0) s1[ra[12:10]] <= 1'b1;
            // macro reads on the next edge; K3 capture rung; K4 output register
            v2 <= v1; f2 <= f1; h2 <= h1; s2 <= s1;        // macro read edge
            v3 <= v2; f3 <= f2; h3 <= h2;                    // capture-rung edge
            v4 <= v3; f4 <= f3; h4 <= h3;        // select-OR edge
            kw_v <= v4; kw_first <= f4; kw_half <= h4;       // output pin register edge
            // boot write: idle only
            wce <= {NM{1'b0}};
            if (bw_v) begin
                if (rcnt != 4'd0 || v1 || v2 || v3 || v4 || bw_addr >= 13'd7168) kfault <= 1'b1;
                else wce[bw_addr[12:10]] <= 1'b1;
            end
        end
    always @(posedge clk) if (bw_v) begin waddr <= bw_addr[9:0]; wd <= bw_data; end
    // ---------------------------------------------------------------- macros + capture rungs
    wire [255:0] rd [0:NM-1];
    reg  [255:0] cap [0:NM-1];
    genvar m, l;
    generate for (m = 0; m < NM; m = m + 1) begin : g_m
        hnx_sram_1r1w_1024x256_r43 u_k (
            .clk(clk), .r_ce_in(rce[m]), .r_addr_in(raddr), .rd_out(rd[m]),
            .w_ce_in(wce_m[m]), .w_addr_in(m < 4 ? wa2[265:256] : wb2[265:256]), .wd_in(m < 4 ? wa2[255:0] : wb2[255:0]),
            .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        always @(posedge clk) cap[m] <= rd[m];
    end endgenerate
    // ---------------------------------------------------------------- K4: kept per-lane select copies, AND-OR register
    reg [255:0] kd, ko;
    generate for (l = 0; l < 8; l = l + 1) begin : g_l
        wire [NM-1:0] s3;
        for (m = 0; m < NM; m = m + 1) begin : g_s
            ot_hnx_uq_kbit u_s (.clk(clk), .d(s2[m]), .q(s3[m]));
        end
        integer j;
        always @(posedge clk) begin : g_or
            reg [31:0] o;
            o = 32'd0;
            for (j = 0; j < NM; j = j + 1) o = o | (s3[j] ? cap[j][l*32 +: 32] : 32'd0);
            kd[l*32 +: 32] <= o;
        end
    end endgenerate
    always @(posedge clk) ko <= kd;                  // output pin register
    assign kw_data = ko;
endmodule
`default_nettype wire
