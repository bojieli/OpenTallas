`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Pipelined on-die mesh link, split at the tile boundary.
//
// A tile's router sits far from three of its four edges (the weight ROM takes
// most of the tile), and ASAP7 buffered wire costs about 0.65 ns per mm
// (results/physical_abi3/asap7/rom/ot_rom_express_link: a 1 mm registered link
// closes at 1,237 MHz, 2 mm at 741 MHz).  A router-to-router hop of one tile
// pitch therefore cannot be one cycle.  The link is pipelined and
// credit-flow-controlled, as the express link and ot_rom_pkg_link are:
//
//   sender tile                                 receiver tile
//   router out --> TX: credit count, STAGES regs --pin--> RX: IN_STAGES regs,
//                                                          DEPTH-flit FIFO,
//                                                          output reg --> router in
//                  <--pin-- credit return (RET_STAGES regs) <--
//
// Every boundary pin is driven by, or captured into, a register, so the
// die-level channel between abutting tiles is a flop-to-flop path.  The TX
// holds at most CREDITS flits in flight and the RX FIFO never overflows when
// CREDITS <= DEPTH; full rate needs CREDITS >= the credit round trip
// (STAGES + IN_STAGES + RET_STAGES + 2 cycles).  RET_STAGES >= 2.
// ---------------------------------------------------------------------------
module ot_chip_mesh_link_tx #(
    parameter integer W       = 512,
    parameter integer STAGES  = 2,
    parameter integer CREDITS = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [W-1:0] in_data,
    input  wire         in_last,
    output wire         ch_valid,
    output wire [W-1:0] ch_data,
    output wire         ch_last,
    input  wire         cr_ret
);
    localparam integer CW = $clog2(CREDITS + 1);
    reg [CW-1:0] credits;
    wire send = in_valid && in_ready;
    assign in_ready = (credits != 0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) credits <= CREDITS;
        else credits <= credits - (send ? 1'b1 : 1'b0) + (cr_ret ? 1'b1 : 1'b0);

    reg         s_v [0:STAGES-1];
    reg         s_l [0:STAGES-1];
    reg [W-1:0] s_d [0:STAGES-1];
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < STAGES; i = i + 1) s_v[i] <= 1'b0;
        end else begin
            s_v[0] <= send;
            for (i = 1; i < STAGES; i = i + 1) s_v[i] <= s_v[i-1];
        end
    end
    always @(posedge clk) begin
        s_d[0] <= in_data; s_l[0] <= in_last;
        for (i = 1; i < STAGES; i = i + 1) begin s_d[i] <= s_d[i-1]; s_l[i] <= s_l[i-1]; end
    end
    assign ch_valid = s_v[STAGES-1];
    assign ch_data  = s_d[STAGES-1];
    assign ch_last  = s_l[STAGES-1];
endmodule

module ot_chip_mesh_link_rx #(
    parameter integer W          = 512,
    parameter integer IN_STAGES  = 2,
    parameter integer RET_STAGES = 2,
    parameter integer DEPTH      = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         ch_valid,
    input  wire [W-1:0] ch_data,
    input  wire         ch_last,
    output wire         out_valid,
    input  wire         out_ready,
    output wire [W-1:0] out_data,
    output wire         out_last,
    output wire         cr_ret,
    output reg          overflow
);
    localparam integer AB = $clog2(DEPTH);
    localparam integer FB = $clog2(DEPTH + 1);
    // input registers: the boundary pin goes straight into a flop, and
    // IN_STAGES registers carry the flit to the FIFO beside the router
    reg         p_v [0:IN_STAGES-1];
    reg         p_l [0:IN_STAGES-1];
    reg [W-1:0] p_d [0:IN_STAGES-1];
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (i = 0; i < IN_STAGES; i = i + 1) p_v[i] <= 1'b0;
        end else begin
            p_v[0] <= ch_valid;
            for (i = 1; i < IN_STAGES; i = i + 1) p_v[i] <= p_v[i-1];
        end
    always @(posedge clk) begin
        p_d[0] <= ch_data; p_l[0] <= ch_last;
        for (i = 1; i < IN_STAGES; i = i + 1) begin p_d[i] <= p_d[i-1]; p_l[i] <= p_l[i-1]; end
    end
    wire         r_v = p_v[IN_STAGES-1];
    wire         r_l = p_l[IN_STAGES-1];
    wire [W-1:0] r_d = p_d[IN_STAGES-1];

    reg [W-1:0] f_d [0:DEPTH-1];
    reg         f_l [0:DEPTH-1];
    reg [AB-1:0] wp, rp;
    reg [FB-1:0] fill;
    reg          o_v, o_l;
    reg [W-1:0]  o_d;
    wire drain = (fill != 0) && (!o_v || out_ready);
    always @(posedge clk) if (r_v) begin f_d[wp] <= r_d; f_l[wp] <= r_l; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; fill <= 0; o_v <= 1'b0; overflow <= 1'b0;
        end else begin
            if (r_v) wp <= (wp == DEPTH - 1) ? {AB{1'b0}} : wp + 1'b1;
            if (drain) rp <= (rp == DEPTH - 1) ? {AB{1'b0}} : rp + 1'b1;
            fill <= fill + (r_v ? 1'b1 : 1'b0) - (drain ? 1'b1 : 1'b0);
            if (r_v && fill == DEPTH && !drain) overflow <= 1'b1;
            if (drain) o_v <= 1'b1;
            else if (out_ready) o_v <= 1'b0;
        end
    end
    always @(posedge clk) if (drain) begin o_d <= f_d[rp]; o_l <= f_l[rp]; end
    assign out_valid = o_v;
    assign out_data  = o_d;
    assign out_last  = o_l;

    // credit return: one pulse per flit leaving the FIFO, through RET_STAGES regs
    reg [RET_STAGES-1:0] ret;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ret <= {RET_STAGES{1'b0}};
        else ret <= {ret[RET_STAGES-2:0], drain};
    assign cr_ret = ret[RET_STAGES-1];
endmodule
