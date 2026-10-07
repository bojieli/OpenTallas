`timescale 1ns/1ps
// Protected successor: mutable metadata complement checked; fault-free ROM has no ECC.
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
    (* keep="true", dont_touch="true" *) reg iv_q, cr_q, iv_n, cr_n;
    (* keep="true", dont_touch="true" *) reg [11:0] ia_q, ia_n;
    always @(posedge clk) begin ia_q <= i_addr; ia_n <= ~i_addr; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv_q <= 0; cr_q <= 0; iv_n <= 1; cr_n <= 1; end
        else begin iv_q <= i_v; cr_q <= o_cr; iv_n <= ~i_v; cr_n <= ~o_cr; end

    (* keep="true", dont_touch="true" *) reg [11:0] fifo [0:1], fifo_n [0:1];
    (* keep="true", dont_touch="true" *) reg [1:0] wp, rp, wp_n, rp_n;
    wire empty = wp == rp;
    wire full = wp[0] == rp[0] && wp[1] != rp[1];
    localparam integer CW = $clog2(OCRED + 1) + 1;
    (* keep="true", dont_touch="true" *) reg [CW-1:0] credits, credits_n;
    (* keep="true", dont_touch="true" *) reg phase, phase_n;
    wire launch = !phase && !empty && credits != 0 && !fault && !bad;
    (* keep="true", dont_touch="true" *) reg [11:0] addr_q, addr_n;
    (* keep="true", dont_touch="true" *) reg ce_q, ce_n;
    (* keep="true", dont_touch="true" *) reg [3:0] valid_pipe, valid_n;
    reg [511:0] capture_data;
    always @(posedge clk) o_data <= capture_data;
    // Keep one enable per 32-bit capture lane, avoiding a 512-load enable.
    (* keep = "true", dont_touch = "true" *) reg [15:0] capture_en_q;
    wire meta_bad = (iv_n != ~iv_q) || (cr_n != ~cr_q) ||
        (iv_q && ia_n != ~ia_q) || (wp_n != ~wp) || (rp_n != ~rp) ||
        (credits_n != ~credits) || (phase_n != ~phase) ||
        (valid_n != ~valid_pipe) || (ce_n != ~ce_q) ||
        (ce_q && addr_n != ~addr_q) ||
        (!empty && fifo_n[rp[0]] != ~fifo[rp[0]]) ||
        (capture_en_q != {16{valid_pipe[2]}});
    // No circular launch dependency: returned-credit bound is evaluated before
    // launch. A return when credits are full is a protocol fault even if a new
    // request could otherwise consume it on this edge.
    wire bad = meta_bad || (iv_q && full) || (cr_q && credits == OCRED);
    wire [CW-1:0] next_credits = credits - launch + cr_q;
    wire [265:0] lo, hi;
    ot_rom_4096x266_m8 u_lo (.clk(clk), .ce_in(ce_q), .addr_in(addr_q), .rd_out(lo));
    ot_rom_4096x266_m8 u_hi (.clk(clk), .ce_in(ce_q), .addr_in(addr_q), .rd_out(hi));

    always @(posedge clk) begin
        if (iv_q && !full && !fault && !bad) begin fifo[wp[0]] <= ia_q; fifo_n[wp[0]] <= ~ia_q; end
        if (launch) begin addr_q <= fifo[rp[0]]; addr_n <= ~fifo[rp[0]]; end
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
                capture_data[lane*32+:32] <= lo[lane*32+:32];
        end else begin : g_hi
            always @(posedge clk) if (capture_en_q[lane])
                capture_data[lane*32+:32] <= hi[(lane-8)*32+:32];
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; wp_n <= 3; rp <= 0; rp_n <= 3; phase <= 0; phase_n <= 1; credits <= OCRED; credits_n <= ~OCRED;
            ce_q <= 0; ce_n <= 1; valid_pipe <= 0; valid_n <= 15; o_v <= 0; i_cr <= 0; fault <= 0;
        end else begin
            phase <= ~phase; phase_n <= phase;
            ce_q <= launch; ce_n <= ~launch;
            valid_pipe <= {valid_pipe[2:0], launch}; valid_n <= ~{valid_pipe[2:0], launch};
            o_v <= valid_pipe[3] && !fault && !bad;
            i_cr <= launch;
            if (iv_q && !full && !fault && !bad) begin wp <= wp + 1'b1; wp_n <= ~(wp+2'd1); end
            if (launch) begin rp <= rp + 1'b1; rp_n <= ~(rp+2'd1); end
            credits <= next_credits; credits_n <= ~next_credits;
            if (bad) fault <= 1;
        end
    end
endmodule
