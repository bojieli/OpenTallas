`timescale 1ns/1ps
// Opt-in physical replacement leaf; no existing runtime instantiates it.
// One bank = 64 vocabulary rows = 4096 x 512 code bits. Two real ROM macros
// carry payload bits [255:0] and [511:256]; their ten spare bits are unused.
// Upstream starts with two credits; downstream supplies OCRED initial seats.
// A launch reserves a downstream seat BEFORE reading, so delayed responses
// cannot overrun the receiver. A two-edge read cadence gives the real SS ROM
// clk->q two cycles to reach the output capture flop (see bank_capture.sdc).
module ot_qwen_embed_code_bank #(
    parameter integer OCRED = 4
) (
    input wire clk, rst_n,
    input wire i_v,
    input wire [11:0] i_addr,
    output reg i_cr,
    output reg o_v,
    output reg [511:0] o_data,
    input wire o_cr,
    output reg fault
);
    reg iv_q, cr_q;
    reg [11:0] ia_q;
    always @(posedge clk) ia_q <= i_addr;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv_q <= 0; cr_q <= 0; end
        else begin iv_q <= i_v; cr_q <= o_cr; end

    reg [11:0] fifo [0:1];
    reg [1:0] wp, rp;
    wire empty = wp == rp;
    wire full = wp[0] == rp[0] && wp[1] != rp[1];
    localparam integer CW = $clog2(OCRED + 1) + 1;
    reg [CW-1:0] credits;
    reg phase;
    wire launch = !phase && !empty && credits != 0 && !fault;
    reg [11:0] addr_q;
    reg ce_q;
    reg [2:0] valid_pipe;
    // Keep one enable per 32-bit capture lane, avoiding a 512-load enable.
    (* keep = "true", dont_touch = "true" *) reg [15:0] capture_en_q;
    wire [265:0] lo, hi;
    ot_rom_4096x266_m8 u_lo (.clk(clk), .ce_in(ce_q), .addr_in(addr_q), .rd_out(lo));
    ot_rom_4096x266_m8 u_hi (.clk(clk), .ce_in(ce_q), .addr_in(addr_q), .rd_out(hi));

    always @(posedge clk) begin
        if (iv_q && !full && !fault) fifo[wp[0]] <= ia_q;
        if (launch) addr_q <= fifo[rp[0]];
        // Macro launches one edge after launch. Capture is two further
        // edges later, before the next enabled macro update on that edge.
    end
    genvar lane;
    generate for (lane=0; lane<16; lane=lane+1) begin : g_capture
        always @(posedge clk or negedge rst_n)
            if (!rst_n) capture_en_q[lane] <= 0;
            else capture_en_q[lane] <= valid_pipe[1];
        if (lane<8) begin : g_lo
            always @(posedge clk) if (capture_en_q[lane])
                o_data[lane*32+:32] <= lo[lane*32+:32];
        end else begin : g_hi
            always @(posedge clk) if (capture_en_q[lane])
                o_data[lane*32+:32] <= hi[(lane-8)*32+:32];
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; phase <= 0; credits <= OCRED;
            ce_q <= 0; valid_pipe <= 0; o_v <= 0; i_cr <= 0; fault <= 0;
        end else begin
            phase <= ~phase;
            ce_q <= launch;
            valid_pipe <= {valid_pipe[1:0], launch};
            o_v <= valid_pipe[2] && !fault;
            i_cr <= launch;
            if (iv_q && !full && !fault) wp <= wp + 1'b1;
            if (launch) rp <= rp + 1'b1;
            credits <= credits - launch + cr_q;
            if ((iv_q && full) || (credits - launch + cr_q > OCRED)) fault <= 1;
        end
    end
endmodule
