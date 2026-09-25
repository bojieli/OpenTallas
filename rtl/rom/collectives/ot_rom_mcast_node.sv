`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Multicast / all-gather node for KV-source rows.
//
// docs/HDC_DEEPSEEK_V41_OPERATOR_INVENTORY.md section 3: a package boundary
// may not separate a KV source from its consumers without forwarding.  Layers
// 2-7 read layer 2's compressed KV and selection, 8-13 read 8's, 14-19 read
// 14's, and 20-39 read layer 20's compressed KV, index keys and candidate
// mask; on the array 20-39 span many packages, so every token's compressed
// row (plus index key and selection) is MULTICAST from the source layer's
// package to the consumer layers' packages.  On a wafer the four sources are
// tiles that multicast the same way.
//
// One node per package, between the package's upstream link (up), its
// downstream link (dn), its local consumer (loc) and its local source (inj):
//
//   * a record from up whose dst_mask has bit SELF is DELIVERED locally and,
//     with SELF cleared from the mask, FORWARDED downstream if any bit is
//     left -- both copies in the same cycle, cut-through, one flit per cycle;
//   * a record from inj (the KV source) goes downstream with src = SELF and
//     dst_mask = its own mask, or CONSUMERS when it carries none (the
//     consumer-set table of this package's source layer, a parameter ROM);
//   * up and inj share dn by packet-atomic round-robin; the arbitration is
//     decided from registered state in the flit's own cycle (no handshake).
//
// A chain of nodes is the array's layer pipeline: every source reaches all
// of its downstream consumers and each row crosses each link once.  Closing
// the chain into a ring and injecting at every package with dst_mask = all
// others is an ALL-GATHER (each package ends with every package's row).
// On a fabric router with multicast the router replicates instead and a
// package needs only the local delivery half.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module ot_rom_mcast_node
#(
    parameter integer FLIT_W    = 512,
    parameter integer SELF      = 0,
    parameter [15:0]  CONSUMERS = 16'h0000
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              up_valid,
    output wire              up_ready,
    input  wire [FLIT_W-1:0] up_data,
    input  wire              up_last,
    input  wire              inj_valid,
    output wire              inj_ready,
    input  wire [FLIT_W-1:0] inj_data,
    input  wire              inj_last,
    output wire              dn_valid,
    input  wire              dn_ready,
    output wire [FLIT_W-1:0] dn_data,
    output wire              dn_last,
    output wire              loc_valid,
    input  wire              loc_ready,
    output wire [FLIT_W-1:0] loc_data,
    output wire              loc_last,
    output reg  [31:0]       delivered,
    output reg  [31:0]       forwarded,
    output reg  [31:0]       injected
);
    localparam [15:0] SELF_BIT = 16'd1 << SELF;
    localparam [7:0]  SELF8    = SELF;

    // -- input slices ----------------------------------------------------------------------
    wire              u_valid, u_last, i_valid, i_last;
    wire [FLIT_W-1:0] u_data, i_data;
    wire              u_fire, i_fire;
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_su (
        .clk(clk), .rst_n(rst_n), .in_valid(up_valid), .in_ready(up_ready), .in_data({up_last, up_data}),
        .out_valid(u_valid), .out_ready(u_fire), .out_data({u_last, u_data}));
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_si (
        .clk(clk), .rst_n(rst_n), .in_valid(inj_valid), .in_ready(inj_ready), .in_data({inj_last, inj_data}),
        .out_valid(i_valid), .out_ready(i_fire), .out_data({i_last, i_data}));

    // the fabric id a forwarded record carries: its nearest remaining consumer
    // downstream (package ids ascending along the chain, wrapping on a ring), so a
    // router between two nodes routes it as a unicast hop
    function [7:0] next_dst(input [15:0] m);
        integer b;
        begin
            next_dst = 8'd0;
            for (b = 15; b >= 1; b = b - 1) if (m[(SELF + b) % 16]) next_dst = (SELF + b) % 16;
        end
    endfunction
    wire [15:0] i_left = ((i_data[H_MASK +: 16] == 16'd0) ? CONSUMERS : i_data[H_MASK +: 16]) & ~SELF_BIT;

    // -- up: deliver and/or forward ---------------------------------------------------------------
    reg         u_first, u_del_r, u_fwd_r;
    wire [15:0] u_mask  = u_data[H_MASK +: 16];
    wire [15:0] u_left  = u_mask & ~SELF_BIT;
    wire        u_del   = u_first ? u_mask[SELF] : u_del_r;
    wire        u_fwd   = u_first ? (u_left != 16'd0) : u_fwd_r;
    reg [FLIT_W-1:0] u_word;
    always @* begin
        u_word = u_data;
        if (u_first) begin
            u_word[H_MASK +: 16] = u_left;
            u_word[H_DST +: 8]   = next_dst(u_left);
        end
    end

    // -- inj: stamp source and consumer set --------------------------------------------------------
    reg              i_first;
    reg [FLIT_W-1:0] i_word;
    always @* begin
        i_word = i_data;
        if (i_first) begin
            i_word[H_SRC +: 8]   = SELF8;
            i_word[H_MASK +: 16] = i_left;
            i_word[H_DST +: 8]   = next_dst(i_left);
        end
    end

    // -- downstream arbitration: packet-atomic round-robin ----------------------------------------
    wire d_ready, l_ready;
    reg [1:0] owner;                                // 0 free, 1 up, 2 inj
    reg       prio_inj;
    wire up_wants  = u_valid && u_fwd;
    wire g_up  = (owner == 2'd1) || (owner == 2'd0 && up_wants && (!prio_inj || !i_valid));
    wire g_inj = (owner == 2'd2) || (owner == 2'd0 && i_valid && (prio_inj || !up_wants));
    assign u_fire = u_valid && (!u_del || l_ready) && (!u_fwd || (g_up && d_ready));
    assign i_fire = i_valid && g_inj && d_ready && !(u_fire && u_fwd);
    wire d_push = (u_fire && u_fwd) || i_fire;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            u_first <= 1'b1; i_first <= 1'b1; u_del_r <= 1'b0; u_fwd_r <= 1'b0; owner <= 2'd0; prio_inj <= 1'b0;
            delivered <= 32'd0; forwarded <= 32'd0; injected <= 32'd0;
        end else begin
            if (u_fire) begin
                u_first <= u_last;
                if (u_first) begin
                    u_del_r <= u_mask[SELF]; u_fwd_r <= (u_left != 16'd0);
                    if (u_mask[SELF]) delivered <= delivered + 32'd1;
                    if (u_left != 16'd0) forwarded <= forwarded + 32'd1;
                end
                if (u_fwd) begin
                    owner <= u_last ? 2'd0 : 2'd1;
                    if (u_last) prio_inj <= 1'b1;
                end
            end
            if (i_fire) begin
                i_first <= i_last;
                if (i_first) injected <= injected + 32'd1;
                owner <= i_last ? 2'd0 : 2'd2;
                if (i_last) prio_inj <= 1'b0;
            end
        end
    end

    // -- output slices -----------------------------------------------------------------------------
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_sd (
        .clk(clk), .rst_n(rst_n), .in_valid(d_push), .in_ready(d_ready),
        .in_data((u_fire && u_fwd) ? {u_last, u_word} : {i_last, i_word}),
        .out_valid(dn_valid), .out_ready(dn_ready), .out_data({dn_last, dn_data}));
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_sl (
        .clk(clk), .rst_n(rst_n), .in_valid(u_fire && u_del), .in_ready(l_ready), .in_data({u_last, u_data}),
        .out_valid(loc_valid), .out_ready(loc_ready), .out_data({loc_last, loc_data}));
endmodule
