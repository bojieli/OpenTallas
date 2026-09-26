`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Expert-package end of the MoE dispatch/combine pair.
//
// RECEIVE.  DISPATCH records arrive from a link or the fabric (a multicast
// record reaches every package in its dst_mask).  In flight, the descriptor's
// item_valid field is narrowed to the items this package owns (item dest ==
// SELF); a record with none is dropped whole.  What leaves on `work` is the
// descriptor plus the ACT_FLITS activation flits, for the expert compute:
// every owned item names its expert id, routing weight and rank, and the
// shared expert is item 6 (it is summed unweighted, as the golden does).
//
// RETURN.  The expert compute hands back one result per (token, expert) as
// VEC_FLITS payload flits of BF16 output, with the token's tag, the item's
// rank and the token's home package on the side.  The port prepends one
// RETURN header flit (dst = home) and streams the payload behind it; the
// header costs the link one flit per result and costs no bubble beyond it.
//
// Both directions are cut-through at one flit per cycle through two register
// slices each; there is no handshake FSM.  Latency: two cycles each way.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module ot_rom_moe_expert_port
#(
    parameter integer FLIT_W    = 512,
    parameter integer SELF      = 1,
    parameter integer ACT_FLITS = 3,
    parameter integer VEC_FLITS = 5            // payload flits of a result (the RETURN header's len)
) (
    input  wire              clk,
    input  wire              rst_n,
    // dispatch records in
    input  wire              in_valid,
    output wire              in_ready,
    input  wire [FLIT_W-1:0] in_data,
    input  wire              in_last,
    // owned work out
    output wire              work_valid,
    input  wire              work_ready,
    output wire [FLIT_W-1:0] work_data,
    output wire              work_last,
    // expert results in (payload flits; tag / rank / home read on a result's first flit)
    input  wire              res_valid,
    output wire              res_ready,
    input  wire [FLIT_W-1:0] res_data,
    input  wire              res_last,
    input  wire [7:0]        res_tag,
    input  wire [2:0]        res_rank,
    input  wire [3:0]        res_home,
    // return records out
    output wire              out_valid,
    input  wire              out_ready,
    output wire [FLIT_W-1:0] out_data,
    output wire              out_last,
    output reg  [31:0]       records_in,
    output reg  [31:0]       records_dropped,
    output reg  [31:0]       results_out,
    output reg               fault
);
    localparam integer RF = 1 + ACT_FLITS;
    localparam integer PW = (RF > 2) ? $clog2(RF) : 1;
    localparam [3:0] SELF4 = SELF;
    localparam [7:0] SELF8 = SELF;
    localparam [7:0] RLEN  = VEC_FLITS;

    // -- receive ----------------------------------------------------------------------------
    wire              a_valid, a_last;
    wire [FLIT_W-1:0] a_data;
    wire              b_ready;
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_a (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_data({in_last, in_data}),
        .out_valid(a_valid), .out_ready(b_ready), .out_data({a_last, a_data}));
    reg [PW-1:0] pos;
    reg          drop_r;
    wire         is_desc = (pos == 0);
    reg [N_ITEMS-1:0] owned;
    integer i;
    always @* begin
        for (i = 0; i < N_ITEMS; i = i + 1)
            owned[i] = a_data[H_IVAL + i] && (a_data[H_ITEM + ITEM_W * i + I_DEST +: 4] == SELF4);
    end
    wire drop = is_desc ? (owned == {N_ITEMS{1'b0}}) : drop_r;
    reg [FLIT_W-1:0] w_word;
    always @* begin
        w_word = a_data;
        if (is_desc) w_word[H_IVAL +: N_ITEMS] = owned;
    end
    wire a_fire = a_valid && b_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pos <= 0; drop_r <= 1'b0; records_in <= 32'd0; records_dropped <= 32'd0; fault <= 1'b0;
        end else if (a_fire) begin
            pos <= (pos == ACT_FLITS) ? {PW{1'b0}} : pos + 1'b1;
            if (is_desc) begin
                drop_r <= drop;
                records_in <= records_in + 32'd1;
                if (drop) records_dropped <= records_dropped + 32'd1;
                if (a_data[H_KIND +: 4] != K_DISPATCH) fault <= 1'b1;
            end
            if (a_last && pos != ACT_FLITS) fault <= 1'b1;   // a packet ends only at a record end
        end
    end
    wire b_in_ready;
    assign b_ready = b_in_ready || drop;               // a dropped record drains without a slot
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_b (
        .clk(clk), .rst_n(rst_n), .in_valid(a_valid && !drop), .in_ready(b_in_ready), .in_data({a_last, w_word}),
        .out_valid(work_valid), .out_ready(work_ready), .out_data({work_last, work_data}));

    // -- return --------------------------------------------------------------------------------
    reg body;                                          // 0: the next flit sent is a result's header
    reg [FLIT_W-1:0] hdr;
    always @* begin
        hdr = {FLIT_W{1'b0}};
        hdr[H_KIND +: 4]  = K_RETURN;
        hdr[H_DST +: 8]   = {4'd0, res_home};
        hdr[H_SRC +: 8]   = SELF8;
        hdr[H_LEN +: 8]   = RLEN;
        hdr[H_MASK +: 16] = 16'd1 << res_home;
        hdr[H_TAG +: 8]   = res_tag;
        hdr[H_RANK +: 3]  = res_rank;
    end
    wire c_in_ready;
    wire c_fire = res_valid && c_in_ready;
    assign res_ready = body && c_in_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            body <= 1'b0; results_out <= 32'd0;
        end else if (c_fire) begin
            if (!body) begin
                body <= 1'b1; results_out <= results_out + 32'd1;
            end else if (res_last) body <= 1'b0;
        end
    end
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_c (
        .clk(clk), .rst_n(rst_n), .in_valid(res_valid), .in_ready(c_in_ready),
        .in_data(body ? {res_last, res_data} : {1'b0, hdr}),
        .out_valid(out_valid), .out_ready(out_ready), .out_data({out_last, out_data}));
endmodule
