`timescale 1ns/1ps
`default_nettype none
// HC x_wave link receiver (H-NETLIST hceng 0600; inside ot_hbm_hc_eng_static, one per quadrant).
// The hc_<q> residual reader (ot_hgi_hc_residual_vm_static BEATS=4) sends each 8,192-b wave as four 2,048-b beats on
// four consecutive edges (beat index 0..3 on x_beat, word on every beat), beat 3 on the edge the BEATS=1 form sent
// the whole wave. Every input lands in a pin flop; beats 0..2 are held, and the reassembled wave
// {beat3 pin flop, held beats 2..0} is presented with wave_v on the edge beat 3 is in the pin flop -- the same edge
// the BEATS=1 wave sat in the engine's x_wave pin flop, so the compiler wave-landing constant is unchanged (+0).
// STATIC: no ready/credit; the beats of a wave must arrive 0,1,2,3 on consecutive edges with one word, otherwise
// fault (sticky). BEATS=1: the wave is the pin flop itself (the original form, kept for the equivalence bench).
module ot_hbm_hc_xw_rx_static #(
    parameter integer BEATS = 4
)(
    input  wire                    clk, rst_n,
    input  wire                    x_v,
    input  wire [1:0]              x_beat,
    input  wire [9:0]              x_word,
    input  wire [8192/BEATS-1:0]   x_data,
    output wire                    wave_v,
    output wire [9:0]              wave_word,
    output wire [8191:0]           wave,
    output reg                     fault
);
    localparam integer BW = 8192 / BEATS;
    initial if (BEATS != 1 && BEATS != 4) $fatal(1, "BEATS must be 1 or 4");
    // pin flops
    reg v_q; reg [1:0] b_q; reg [9:0] w_q; reg [BW-1:0] d_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) v_q <= 1'b0; else v_q <= x_v;
    always @(posedge clk) begin b_q <= x_beat; w_q <= x_word; d_q <= x_data; end
    generate if (BEATS == 1) begin : g_one
        assign wave_v = v_q; assign wave_word = w_q; assign wave = d_q;
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else if (v_q && b_q != 2'd0) fault <= 1'b1;
    end else begin : g_beats
        reg [3*BW-1:0] hold; reg [1:0] nxt; reg [9:0] hw;
        always @(posedge clk) if (v_q && b_q != 2'd3) begin hold[b_q*BW +: BW] <= d_q; hw <= w_q; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin nxt <= 2'd0; fault <= 1'b0; end
            else begin
                if (v_q) begin
                    if (b_q != nxt || (b_q != 2'd0 && w_q != hw)) fault <= 1'b1;
                    nxt <= b_q + 2'd1;
                end else if (nxt != 2'd0) fault <= 1'b1;           // a wave's beats must be consecutive
            end
        assign wave_v = v_q && b_q == 2'd3;
        assign wave_word = w_q;
        assign wave = {d_q, hold};
    end endgenerate
endmodule
`default_nettype wire
